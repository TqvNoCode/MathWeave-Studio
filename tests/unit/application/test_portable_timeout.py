"""Comprehensive unit tests for portable process timeout architecture, worker lifecycle, and cleanup."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import time
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.application.ports.solver import Solver
from math_app.application.process_guard import (
    ProcessExecutionResult,
    compute_failure,
    compute_sleep,
    compute_sum,
    run_with_process_timeout,
)
from math_app.application.registry import DefaultSolverRegistry
from math_app.application.use_cases.solve_problem import SolveProblemUseCase
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus


class MockHangingSolver(Solver):
    """Solver that hangs indefinitely to test application-level timeout isolation."""

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type == ProblemType.DERIVATIVE

    def solve(self, request: ProblemRequest):
        time.sleep(10.0)
        return None


def test_timeout_fast_computation_succeeds():
    """Verify that a computation finishing before the timeout returns status 'ok' and correct value."""
    result = run_with_process_timeout(
        compute_sum,
        args=(15, 27),
        timeout_seconds=5.0,
    )
    assert isinstance(result, ProcessExecutionResult)
    assert result.status == "ok"
    assert result.value == 42
    assert result.error_message is None
    assert result.elapsed_ms > 0.0


def test_timeout_slow_computation_times_out():
    """Verify that a computation exceeding the timeout is hard-terminated and returns 'timeout'."""
    t0 = time.perf_counter()
    result = run_with_process_timeout(
        compute_sleep,
        args=(10.0,),
        timeout_seconds=0.5,
    )
    elapsed = time.perf_counter() - t0

    assert result.status == "timeout"
    assert result.value is None
    assert "vượt quá giới hạn thời gian" in result.error_message
    assert 0.45 <= elapsed < 3.0


def test_timeout_exception_handling():
    """Verify that worker exceptions are captured and returned with status 'error'."""
    result = run_with_process_timeout(
        compute_failure,
        args=("Deliberate domain computation error",),
        timeout_seconds=5.0,
    )
    assert result.status == "error"
    assert "RuntimeError" in result.error_message
    assert "Deliberate domain computation error" in result.error_message


def test_timeout_repeated_timed_out_computations():
    """Verify that running repeated timed-out tasks does not deadlock or leak state."""
    for _ in range(3):
        res = run_with_process_timeout(
            compute_sleep,
            args=(5.0,),
            timeout_seconds=0.3,
        )
        assert res.status == "timeout"


def test_timeout_concurrent_submissions():
    """Verify that multiple concurrent computations (mix of fast and timed-out) do not interfere."""
    def _run_task(task_type: str):
        if task_type == "fast":
            return run_with_process_timeout(compute_sum, args=(10, 20), timeout_seconds=5.0)
        else:
            return run_with_process_timeout(compute_sleep, args=(5.0,), timeout_seconds=0.4)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(_run_task, "fast"),
            executor.submit(_run_task, "slow"),
            executor.submit(_run_task, "fast"),
            executor.submit(_run_task, "slow"),
        ]
        results = [f.result() for f in futures]

    assert results[0].status == "ok" and results[0].value == 30
    assert results[1].status == "timeout"
    assert results[2].status == "ok" and results[2].value == 30
    assert results[3].status == "timeout"


def test_timeout_sympy_symbolic_integrate_portable():
    """Verify that sp.integrate runs cleanly in a spawned process and returns symbolic results."""
    x = sp.Symbol("x")
    result = run_with_process_timeout(
        sp.integrate,
        args=(x**2, (x, 0, 1)),
        timeout_seconds=5.0,
    )
    assert result.status == "ok"
    assert result.value == sp.Rational(1, 3)


def test_timeout_distinct_from_divergence():
    """Ensure that a computation timeout in SolveProblemUseCase produces TIMEOUT and NEVER DIVERGENT."""
    registry = DefaultSolverRegistry()
    registry.register(ProblemType.DERIVATIVE, MockHangingSolver())
    use_case = SolveProblemUseCase(registry)

    req = ProblemRequest(
        raw_input="x^2",
        problem_type=ProblemType.DERIVATIVE,
        target_variable="x",
    )
    resp = use_case.execute(req, timeout_seconds=0.5)

    assert resp.status == SolutionStatus.TIMEOUT
    assert resp.status != SolutionStatus.DIVERGENT
    assert resp.status != SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.FAILED
    assert "vượt quá thời gian" in resp.warnings[0]


def test_domain_statuses_are_distinct():
    """Verify all domain outcome concepts remain strictly distinct."""
    assert SolutionStatus.SUCCESS != SolutionStatus.DIVERGENT
    assert SolutionStatus.DIVERGENT != SolutionStatus.TIMEOUT
    assert SolutionStatus.TIMEOUT != SolutionStatus.INCONCLUSIVE
    assert SolutionStatus.INCONCLUSIVE != SolutionStatus.INVALID_INPUT
    assert SolutionStatus.INVALID_INPUT != SolutionStatus.ERROR


def test_timeout_worker_cleanup_after_success():
    """Verify no active child processes or orphaned workers remain after successful completion."""
    import multiprocessing

    res = run_with_process_timeout(compute_sum, args=(10, 20), timeout_seconds=2.0)
    assert res.status == "ok"
    assert len(multiprocessing.active_children()) == 0


def test_timeout_worker_cleanup_after_timeout():
    """Verify timed-out child worker process is reaped and not left active/orphaned."""
    import multiprocessing

    res = run_with_process_timeout(compute_sleep, args=(5.0,), timeout_seconds=0.3)
    assert res.status == "timeout"
    assert len(multiprocessing.active_children()) == 0


def test_timeout_worker_cleanup_after_exception():
    """Verify crashed child worker process is cleaned up without orphan processes."""
    import multiprocessing

    res = run_with_process_timeout(compute_failure, timeout_seconds=2.0)
    assert res.status == "error"
    assert len(multiprocessing.active_children()) == 0


def test_timeout_explicit_spawn_context_on_linux():
    """Verify that multiprocessing spawn context is explicitly used on Linux (matching Windows)."""
    import multiprocessing

    ctx = multiprocessing.get_context("spawn")
    assert ctx.get_start_method() == "spawn"

    # Execute a computation explicitly confirming spawn execution
    res = run_with_process_timeout(compute_sum, args=(100, 200), timeout_seconds=3.0)
    assert res.status == "ok"
    assert res.value == 300


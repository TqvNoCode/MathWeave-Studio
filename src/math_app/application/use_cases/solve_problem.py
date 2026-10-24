"""Use case orchestrating problem routing, solving, and response delivery."""

from __future__ import annotations

from collections.abc import Sequence
import multiprocessing
import time
from typing import Any

from math_app.application.dtos import ProblemRequest, SolutionResponse, VerificationResult
from math_app.application.ports.solver import Solver
from math_app.application.ports.solver_registry import SolverRegistry
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import SolutionStatus, VerificationStatus

DEFAULT_SOLVER_TIMEOUT_SECONDS = 8.0


def _worker_solve_entrypoint(solver: Solver, request: ProblemRequest, conn: Any) -> None:
    """Entry point executed in isolated child process for CPU-bound symbolic computations."""
    try:
        response = solver.solve(request)
        conn.send(("ok", response))
    except InvalidInputError as exc:
        conn.send(("invalid_input", str(exc)))
    except Exception as exc:
        conn.send(("error", str(exc)))
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _execute_in_isolated_process(
    solver: Solver,
    request: ProblemRequest,
    timeout_seconds: float,
) -> SolutionResponse:
    """Execute solver inside an isolated OS process with hard termination on timeout."""
    ctx = multiprocessing.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe()
    p = ctx.Process(
        target=_worker_solve_entrypoint,
        args=(solver, request, child_conn),
        daemon=True,
    )
    t0 = time.perf_counter()
    p.start()
    child_conn.close()

    p.join(timeout=timeout_seconds)

    if p.is_alive():
        # Hard cancellation of hung or CPU-bound computation
        try:
            p.terminate()
            p.join(timeout=1.0)
            if p.is_alive():
                p.kill()
                p.join(timeout=1.0)
        except Exception:
            pass
        finally:
            parent_conn.close()

        elapsed = (time.perf_counter() - t0) * 1000.0
        return SolutionResponse(
            status=SolutionStatus.TIMEOUT,
            verification=VerificationResult(
                status=VerificationStatus.FAILED,
                method="timeout",
                details=f"Thời gian tính toán vượt quá giới hạn an toàn {timeout_seconds}s.",
            ),
            raw_input=request.raw_input,
            canonical_input=request.raw_input.strip(),
            final_result="",
            final_latex="",
            warnings=(
                f"Quá trình giải toán vượt quá thời gian cho phép ({timeout_seconds} giây) và đã bị ngắt an toàn (Computation timed out).",
            ),
            execution_time_ms=elapsed,
        )

    # Process completed within timeout
    elapsed = (time.perf_counter() - t0) * 1000.0
    try:
        if parent_conn.poll():
            status_tag, payload = parent_conn.recv()
            if status_tag == "ok":
                resp: SolutionResponse = payload
                if resp.execution_time_ms <= 0.0:
                    resp = SolutionResponse(
                        status=resp.status,
                        verification=resp.verification,
                        raw_input=resp.raw_input,
                        canonical_input=resp.canonical_input,
                        final_result=resp.final_result,
                        final_latex=resp.final_latex,
                        steps=resp.steps,
                        domain_restrictions=resp.domain_restrictions,
                        warnings=resp.warnings,
                        execution_time_ms=elapsed,
                    )
                return resp
            elif status_tag == "invalid_input":
                return SolutionResponse(
                    status=SolutionStatus.INVALID_INPUT,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="none",
                        details=payload,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=request.raw_input.strip(),
                    final_result="",
                    final_latex="",
                    warnings=(payload,),
                    execution_time_ms=elapsed,
                )
            else:
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="none",
                        details=f"Solver error: {payload}",
                    ),
                    raw_input=request.raw_input,
                    canonical_input=request.raw_input.strip(),
                    final_result="",
                    final_latex="",
                    warnings=(f"Solver encountered an error: {payload}",),
                    execution_time_ms=elapsed,
                )
        else:
            exitcode = p.exitcode
            return SolutionResponse(
                status=SolutionStatus.ERROR,
                verification=VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="worker_crash",
                    details=f"Worker process exited unexpectedly with code {exitcode}.",
                ),
                raw_input=request.raw_input,
                canonical_input=request.raw_input.strip(),
                final_result="",
                final_latex="",
                warnings=(f"Tiến trình tính toán kết thúc đột ngột (Worker crashed with exit code {exitcode}).",),
                execution_time_ms=elapsed,
            )
    finally:
        parent_conn.close()


class SolveProblemUseCase:
    """Orchestrates problem solving via abstract SolverRegistry or solver sequence."""

    def __init__(
        self,
        registry: SolverRegistry | Sequence[Solver],
        default_timeout: float | None = None,
    ) -> None:
        self.default_timeout = default_timeout
        if hasattr(registry, "get"):
            self._registry: SolverRegistry | None = registry
            self._solvers: Sequence[Solver] | None = None
        else:
            self._registry = None
            self._solvers = list(registry)

    def execute(
        self,
        request: ProblemRequest,
        timeout_seconds: float | None = None,
    ) -> SolutionResponse:
        start_time = time.perf_counter()

        cleaned_input = request.raw_input.strip()
        if not cleaned_input:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.INVALID_INPUT,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="none",
                    details="Empty input expression.",
                ),
                raw_input=request.raw_input,
                canonical_input="",
                final_result="",
                final_latex="",
                warnings=("Input expression cannot be empty.",),
                execution_time_ms=elapsed,
            )

        is_matrix_op = request.problem_type.is_matrix
        var_str = request.target_variable.strip()

        if not is_matrix_op:
            # Handle differential prefix (dx, dy, dtheta, dθ)
            if (var_str.startswith("d") or var_str.startswith("d\\")) and len(var_str) > 1:
                prefix_len = 2 if var_str.startswith("d\\") else 1
                cand = var_str[prefix_len:].strip()
                if cand:
                    var_str = cand
            if var_str.startswith("\\"):
                var_str = var_str[1:]
            var_str = {"θ": "theta", "φ": "phi", "ρ": "rho"}.get(var_str, var_str)

            if not var_str or not var_str.isidentifier():
                elapsed = (time.perf_counter() - start_time) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.INVALID_INPUT,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="none",
                        details="Invalid target variable.",
                    ),
                    raw_input=request.raw_input,
                    canonical_input="",
                    final_result="",
                    final_latex="",
                    warnings=(f"Ký hiệu biến '{request.target_variable}' không hợp lệ. Phải là một định danh hợp lệ (Invalid target variable).",),
                    execution_time_ms=elapsed,
                )

            if var_str != request.target_variable:
                request = ProblemRequest(
                    raw_input=request.raw_input,
                    problem_type=request.problem_type,
                    target_variable=var_str,
                    assumptions=request.assumptions,
                    parameters=request.parameters,
                )

        solver: Solver | None = None
        if self._registry is not None:
            candidate = self._registry.get(request.problem_type)
            if candidate is not None and candidate.can_solve(request):
                solver = candidate
        elif self._solvers is not None:
            for candidate in self._solvers:
                if candidate.can_solve(request):
                    solver = candidate
                    break

        if solver is None:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="none",
                    details="No matching solver found.",
                ),
                raw_input=request.raw_input,
                canonical_input=cleaned_input,
                final_result="",
                final_latex="",
                warnings=(f"No registered solver available for problem type '{request.problem_type.value}'.",),
                execution_time_ms=elapsed,
            )

        effective_timeout = timeout_seconds if timeout_seconds is not None else self.default_timeout
        if effective_timeout is not None and effective_timeout > 0:
            return _execute_in_isolated_process(solver, request, effective_timeout)

        try:
            response = solver.solve(request)
            elapsed = (time.perf_counter() - start_time) * 1000.0
            if response.execution_time_ms <= 0.0:
                response = SolutionResponse(
                    status=response.status,
                    verification=response.verification,
                    raw_input=response.raw_input,
                    canonical_input=response.canonical_input,
                    final_result=response.final_result,
                    final_latex=response.final_latex,
                    steps=response.steps,
                    domain_restrictions=response.domain_restrictions,
                    warnings=response.warnings,
                    execution_time_ms=elapsed,
                )
            return response
        except InvalidInputError as exc:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.INVALID_INPUT,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="none",
                    details=str(exc),
                ),
                raw_input=request.raw_input,
                canonical_input=cleaned_input,
                final_result="",
                final_latex="",
                warnings=(str(exc),),
                execution_time_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="none",
                    details=f"Solver error: {exc}",
                ),
                raw_input=request.raw_input,
                canonical_input=cleaned_input,
                final_result="",
                final_latex="",
                warnings=(f"Solver encountered an unexpected error / unexpected failure: {exc}",),
                execution_time_ms=elapsed,
            )

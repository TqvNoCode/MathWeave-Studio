"""Portable, cross-platform process isolation and bounded computation runner.

Provides safe process-based execution compatible with Windows multiprocessing 'spawn'
and Linux, avoiding Unix-only signals (setitimer, SIGALRM) and ensuring reliable
cleanup of OS process handles, pipes, and child workers without orphans.
"""

from __future__ import annotations

from dataclasses import dataclass
import multiprocessing
import time
from typing import Any, Callable


@dataclass(frozen=True)
class ProcessExecutionResult:
    """Outcome of an isolated process execution."""

    status: str  # "ok", "timeout", "error"
    value: Any = None
    error_message: str | None = None
    elapsed_ms: float = 0.0


def compute_sum(a: int, b: int) -> int:
    """Portable arithmetic computation helper for testing and verification."""
    return a + b


def compute_sleep(seconds: float) -> str:
    """Simulate long CPU or I/O bound computation exceeding budget."""
    time.sleep(seconds)
    return "done"


def compute_failure(message: str = "Simulated computation failure") -> None:
    """Simulate an unhandled exception inside a worker."""
    raise RuntimeError(message)


def _process_worker_entrypoint(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any] | None,
    conn: Any,
) -> None:
    """Top-level module worker entrypoint executed in spawned child process."""
    try:
        # Notify parent that process is initialized and computation is beginning
        conn.send(("started", None))
        kw = kwargs if kwargs is not None else {}
        result = func(*args, **kw)
        conn.send(("ok", result))
    except Exception as exc:
        conn.send(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        try:
            conn.close()
        except Exception:
            pass


def run_with_process_timeout(
    func: Callable[..., Any],
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
    timeout_seconds: float = 1.0,
    startup_timeout_seconds: float = 5.0,
) -> ProcessExecutionResult:
    """Execute a callable in an isolated process with a hard computation timeout budget.

    Separates process boot/import latency from pure computation time, ensuring that
    short symbolic budgets (e.g. 1.0s) are not consumed by Python interpreter initialization.

    Args:
        func: Module-level picklable callable.
        args: Positional arguments tuple.
        kwargs: Keyword arguments dict.
        timeout_seconds: Maximum allowed wall-clock seconds for mathematical computation.
        startup_timeout_seconds: Maximum allowed seconds for process spawning and import.

    Returns:
        ProcessExecutionResult containing outcome status, return value, and timing.
    """
    ctx = multiprocessing.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)

    p = ctx.Process(
        target=_process_worker_entrypoint,
        args=(func, args, kwargs, child_conn),
        daemon=False,
    )

    t0 = time.perf_counter()
    p.start()
    child_conn.close()

    # Step 1: Wait for process to spawn and report that computation is starting
    if not parent_conn.poll(startup_timeout_seconds):
        try:
            p.terminate()
            p.join(timeout=0.5)
            if p.is_alive():
                p.kill()
                p.join(timeout=0.5)
        except Exception:
            pass
        finally:
            parent_conn.close()
            try:
                p.close()
            except Exception:
                pass
        return ProcessExecutionResult(
            status="error",
            error_message="Quá trình khởi tạo tiến trình con vượt quá thời gian cho phép.",
            elapsed_ms=(time.perf_counter() - t0) * 1000.0,
        )

    try:
        tag, _ = parent_conn.recv()
    except (EOFError, OSError):
        exitcode = p.exitcode
        parent_conn.close()
        try:
            p.close()
        except Exception:
            pass
        return ProcessExecutionResult(
            status="error",
            error_message=f"Tiến trình con kết thúc đột ngột trước khi bắt đầu (exit code {exitcode}).",
            elapsed_ms=(time.perf_counter() - t0) * 1000.0,
        )

    # Step 2: Bounded computation window
    if not parent_conn.poll(timeout_seconds):
        # Computation exceeded timeout budget!
        try:
            p.terminate()
            p.join(timeout=0.5)
            if p.is_alive():
                p.kill()
                p.join(timeout=0.5)
        except Exception:
            pass
        finally:
            parent_conn.close()
            try:
                p.close()
            except Exception:
                pass
        elapsed = (time.perf_counter() - t0) * 1000.0
        return ProcessExecutionResult(
            status="timeout",
            error_message=f"Quá trình tính toán vượt quá giới hạn thời gian cho phép ({timeout_seconds}s).",
            elapsed_ms=elapsed,
        )

    # Step 3: Computation completed within timeout budget
    elapsed = (time.perf_counter() - t0) * 1000.0
    try:
        try:
            tag, payload = parent_conn.recv()
        except (EOFError, OSError):
            exitcode = p.exitcode
            return ProcessExecutionResult(
                status="error",
                error_message=f"Tiến trình kết thúc đột ngột (Worker exited with code {exitcode}).",
                elapsed_ms=elapsed,
            )

        p.join(timeout=1.0)
        if tag == "ok":
            return ProcessExecutionResult(
                status="ok",
                value=payload,
                elapsed_ms=elapsed,
            )
        else:
            return ProcessExecutionResult(
                status="error",
                error_message=str(payload),
                elapsed_ms=elapsed,
            )
    finally:
        parent_conn.close()
        try:
            p.close()
        except Exception:
            pass

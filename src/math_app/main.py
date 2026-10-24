"""MathWeave Studio application bootstrap and composition root."""

from __future__ import annotations

from nicegui import ui

from math_app import __title__

from math_app.application.registry import DefaultSolverRegistry
from math_app.application.use_cases.solve_problem import SolveProblemUseCase
from math_app.domain.models import ProblemType
from math_app.presentation.app import create_app
from math_app.solvers.algebra.equation_solver import EquationSolver
from math_app.solvers.calculus.differentiation.solver import DerivativeSolver
from math_app.solvers.calculus.geometry.arc_length_solver import ArcLengthSolver
from math_app.solvers.calculus.geometry.surface_area_solver import SurfaceAreaSolver
from math_app.solvers.calculus.geometry.surface_of_revolution_solver import SurfaceOfRevolutionSolver
from math_app.solvers.calculus.integration.solver import IntegralSolver
from math_app.solvers.calculus.integration.line_integral_solver import LineIntegralSolver
from math_app.solvers.calculus.integration.surface_integral_solver import SurfaceIntegralSolver
from math_app.solvers.calculus.integration.triple_integral_solver import TripleIntegralSolver
from math_app.solvers.calculus.limit.solver import LimitSolver
from math_app.solvers.calculus.vector_calculus.divergence_theorem_solver import DivergenceTheoremSolver
from math_app.solvers.calculus.vector_calculus.greens_theorem_solver import GreensTheoremSolver
from math_app.solvers.calculus.vector_calculus.stokes_theorem_solver import StokesTheoremSolver
from math_app.solvers.linear_algebra.solver import MatrixSolver

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080


def build_application() -> SolveProblemUseCase:
    """Wire together solvers, registry, and application use cases."""
    registry = DefaultSolverRegistry()

    # Calculus solvers
    derivative_solver = DerivativeSolver()
    registry.register(ProblemType.DERIVATIVE, derivative_solver)
    registry.register(ProblemType.HIGHER_ORDER_DERIVATIVE, derivative_solver)
    registry.register(ProblemType.PARTIAL_DERIVATIVE, derivative_solver)

    integral_solver = IntegralSolver()
    registry.register(ProblemType.INTEGRAL, integral_solver)
    registry.register(ProblemType.INDEFINITE_INTEGRAL, integral_solver)
    registry.register(ProblemType.DEFINITE_INTEGRAL, integral_solver)

    line_integral_solver = LineIntegralSolver()
    registry.register(ProblemType.LINE_INTEGRAL, line_integral_solver)

    surface_integral_solver = SurfaceIntegralSolver()
    registry.register(ProblemType.SURFACE_INTEGRAL, surface_integral_solver)

    triple_integral_solver = TripleIntegralSolver()
    registry.register(ProblemType.TRIPLE_INTEGRAL, triple_integral_solver)

    # Parametric geometry & surfaces (Phase 4)
    arc_length_solver = ArcLengthSolver()
    registry.register(ProblemType.ARC_LENGTH, arc_length_solver)
    registry.register(ProblemType.PARAMETRIC_CURVE, arc_length_solver)

    surface_area_solver = SurfaceAreaSolver()
    registry.register(ProblemType.SURFACE_AREA, surface_area_solver)

    surface_of_rev_solver = SurfaceOfRevolutionSolver()
    registry.register(ProblemType.SURFACE_OF_REVOLUTION, surface_of_rev_solver)

    # Vector calculus theorems (Phase 5)
    greens_solver = GreensTheoremSolver()
    registry.register(ProblemType.GREENS_THEOREM, greens_solver)

    stokes_solver = StokesTheoremSolver()
    registry.register(ProblemType.STOKES_THEOREM, stokes_solver)

    divergence_solver = DivergenceTheoremSolver()
    registry.register(ProblemType.DIVERGENCE_THEOREM, divergence_solver)

    limit_solver = LimitSolver()
    registry.register(ProblemType.LIMIT, limit_solver)

    equation_solver = EquationSolver()
    registry.register(ProblemType.SOLVE_EQUATION, equation_solver)

    # Linear algebra solver
    matrix_solver = MatrixSolver()
    registry.register(ProblemType.MATRIX_ADD_SUB, matrix_solver)
    registry.register(ProblemType.MATRIX_MULTIPLY, matrix_solver)
    registry.register(ProblemType.MATRIX_TRANSPOSE, matrix_solver)
    registry.register(ProblemType.MATRIX_DETERMINANT, matrix_solver)
    registry.register(ProblemType.MATRIX_INVERSE, matrix_solver)
    registry.register(ProblemType.MATRIX_RANK, matrix_solver)
    registry.register(ProblemType.MATRIX_REF, matrix_solver)
    registry.register(ProblemType.MATRIX_RREF, matrix_solver)
    registry.register(ProblemType.MATRIX_SOLVE_SYSTEM, matrix_solver)

    return SolveProblemUseCase(registry)


def get_available_port(host: str = DEFAULT_HOST, default_port: int = DEFAULT_PORT) -> int:
    """Find an available port starting at default_port or dynamically binding to 0."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, default_port))
            return default_port
        except OSError:
            pass

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def _setup_signal_handlers() -> None:
    """Configure robust, bounded signal handling to prevent shutdown deadlocks."""
    import os
    import signal
    import sys
    from typing import Any

    is_shutting_down = False

    def _handle_signal(signum: int, frame: Any) -> None:
        nonlocal is_shutting_down
        if is_shutting_down:
            # Immediate hard exit on repeated interrupt, preventing 30s timeout hanging
            try:
                sys.stderr.write("\nNhận tín hiệu ngắt lặp lại. Thoát an toàn ngay lập tức...\n")
                sys.stderr.flush()
            except Exception:
                pass
            try:
                from nicegui import run
                run.tear_down()
            except Exception:
                pass
            os._exit(0)

        is_shutting_down = True
        try:
            from nicegui import app
            app.shutdown()
        except Exception:
            try:
                from nicegui import run
                run.tear_down()
            except Exception:
                pass
            os._exit(0)

    try:
        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, _handle_signal)
    except (ValueError, OSError):
        pass


def main() -> None:
    """Application main entrypoint."""
    import os
    import sys

    use_case = build_application()
    create_app(use_case)

    _setup_signal_handlers()

    port = get_available_port(DEFAULT_HOST, DEFAULT_PORT)
    # Allow explicit flag --browser or default to native window when display is available
    use_native = "--browser" not in sys.argv
    if use_native and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        use_native = False

    from nicegui import app
    if use_native:
        app.native.start_args["gui"] = "qt"
        app.native.window_args["resizable"] = True

    try:
        ui.run(
            host=DEFAULT_HOST,
            title=f"{__title__} — Phần mềm Học tập & Nghiên cứu Toán học",
            port=port,
            reload=False,
            native=use_native,
            window_size=(1200, 800) if use_native else None,
            timeout_graceful_shutdown=3.0,
        )
    except KeyboardInterrupt:
        pass
    finally:
        try:
            from nicegui import run
            run.tear_down()
        except Exception:
            pass
        sys.stdout.flush()
        sys.stderr.flush()


if __name__ in {"__main__", "__mp_main__"}:
    main()

"""MathWeave Studio application bootstrap and composition root."""

from __future__ import annotations

import hmac
import os
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from nicegui import app, ui

from math_app import __title__

from math_app.application.registry import DefaultSolverRegistry
from math_app.application.use_cases.solve_problem import SolveProblemUseCase
from math_app.domain.models import ProblemType
from math_app.presentation.app import create_app
from math_app.presentation.startup import (
    HeadlessEnvironmentError,
    NativeBackendError,
    resolve_configured_port,
    resolve_startup_mode,
    validate_and_prepare_native_backend,
)
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
from math_app.solvers.calculus.ode.classical_homogeneous_solver import ODEClassicalHomogeneousSolver
from math_app.solvers.calculus.ode.exact_solver import ODEExactSolver
from math_app.solvers.calculus.ode.integrating_factor_solver import ODEIntegratingFactorSolver
from math_app.solvers.calculus.ode.linear_solver import ODELinearSolver
from math_app.solvers.calculus.ode.reduction_of_order_solver import ODEReductionOfOrderSolver
from math_app.solvers.calculus.ode.second_order_constant_coeff_solver import ODESecondOrderConstantCoeffSolver
from math_app.solvers.calculus.ode.separable_solver import ODESeparableSolver
from math_app.solvers.calculus.ode.wronskian_solver import WronskianSolver
from math_app.solvers.calculus.vector_calculus.divergence_theorem_solver import DivergenceTheoremSolver
from math_app.solvers.calculus.vector_calculus.greens_theorem_solver import GreensTheoremSolver
from math_app.solvers.calculus.vector_calculus.stokes_theorem_solver import StokesTheoremSolver
from math_app.solvers.linear_algebra.solver import MatrixSolver

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080


def get_resource_path(relative_path: str | Path) -> Path:
    """Resolve absolute path to a resource, supporting both development and PyInstaller frozen bundles."""
    import sys
    from pathlib import Path

    rel_p = Path(relative_path)
    if hasattr(sys, "_MEIPASS"):
        candidate = (Path(sys._MEIPASS) / rel_p).resolve()
        if candidate.exists():
            return candidate

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        for candidate_base in (exe_dir, exe_dir / "_internal"):
            candidate = (candidate_base / rel_p).resolve()
            if candidate.exists():
                return candidate

    base_dir = Path(__file__).resolve().parent.parent.parent
    return (base_dir / rel_p).resolve()


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

    # Differential Equations solvers
    ode_linear_solver = ODELinearSolver()
    registry.register(ProblemType.ODE_FIRST_ORDER_LINEAR, ode_linear_solver)

    ode_classical_homog_solver = ODEClassicalHomogeneousSolver()
    registry.register(ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS, ode_classical_homog_solver)

    ode_separable_solver = ODESeparableSolver()
    registry.register(ProblemType.ODE_SEPARABLE, ode_separable_solver)

    ode_exact_solver = ODEExactSolver()
    registry.register(ProblemType.ODE_EXACT, ode_exact_solver)

    ode_integrating_factor_solver = ODEIntegratingFactorSolver()
    registry.register(ProblemType.ODE_INTEGRATING_FACTOR, ode_integrating_factor_solver)

    ode_second_order_solver = ODESecondOrderConstantCoeffSolver()
    registry.register(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, ode_second_order_solver)
    registry.register(ProblemType.ODE_SECOND_ORDER_IVP, ode_second_order_solver)

    ode_reduction_of_order_solver = ODEReductionOfOrderSolver()
    registry.register(ProblemType.ODE_REDUCTION_OF_ORDER, ode_reduction_of_order_solver)

    wronskian_solver = WronskianSolver()
    registry.register(ProblemType.WRONSKIAN, wronskian_solver)

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


def _setup_test_shutdown_endpoint(host: str) -> bool:
    """Configure an authenticated loopback-only shutdown endpoint for automated CI testing.

    Security specifications:
    1. Enabled strictly and exclusively when MATHWEAVE_TEST_SHUTDOWN_TOKEN is present and non-empty in os.environ.
    2. Server must be bound to loopback ('127.0.0.1', 'localhost', '::1'). If not, registration is aborted.
    3. Validates incoming X-Shutdown-Token header using constant-time comparison (hmac.compare_digest).
    4. Token is never logged or exposed.
    5. Requests from non-loopback clients are rejected with HTTP 403.
    6. Unauthenticated or invalid token requests are rejected with HTTP 401.
    7. HTTP 200 response is dispatched before graceful application shutdown begins.
    8. Triggers supported NiceGUI app.shutdown() and Server.instance.should_exit = True.
    """
    token = os.environ.get("MATHWEAVE_TEST_SHUTDOWN_TOKEN")
    if not token or not token.strip():
        return False

    # Loopback safety assertion
    if host not in ("127.0.0.1", "localhost", "::1"):
        return False

    expected_token = token.strip()

    @app.post("/_test/shutdown")
    async def _test_shutdown_endpoint(
        request: Request,
        background_tasks: BackgroundTasks,
        x_shutdown_token: str | None = Header(default=None, alias="X-Shutdown-Token"),
    ) -> JSONResponse:
        # 1. Loopback-only caller verification
        client_host = request.client.host if request.client else ""
        if client_host not in ("127.0.0.1", "::1", "localhost", "testclient"):
            raise HTTPException(status_code=403, detail="Forbidden: loopback access only")

        # 2. Constant-time token verification (never log or expose token value)
        if not x_shutdown_token or not hmac.compare_digest(
            x_shutdown_token.encode("utf-8"), expected_token.encode("utf-8")
        ):
            raise HTTPException(status_code=401, detail="Unauthorized")

        # 3. Schedule graceful shutdown after response transmission
        async def _execute_graceful_shutdown() -> None:
            import asyncio

            await asyncio.sleep(0.05)
            try:
                from nicegui.server import Server

                if hasattr(Server, "instance") and Server.instance is not None:
                    Server.instance.should_exit = True
            except Exception:
                pass
            try:
                app.shutdown()
            except Exception:
                pass

        background_tasks.add_task(_execute_graceful_shutdown)

        return JSONResponse(
            content={
                "status": "shutting_down",
                "message": "Graceful application shutdown initiated.",
            }
        )

    return True


def _setup_signal_handlers() -> None:
    """Configure robust, bounded signal handling to prevent shutdown deadlocks."""
    import os
    import signal
    import sys

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
    import multiprocessing
    import sys

    # In Windows / frozen environment, prevent spawned child workers from executing main
    if multiprocessing.current_process().name != "MainProcess":
        return

    # 1. Resolve startup mode (Native window by default, Browser with --browser)
    try:
        startup_mode = resolve_startup_mode()
    except HeadlessEnvironmentError as exc:
        if sys.stderr is not None:
            try:
                sys.stderr.write(f"\n[ERROR] {exc}\n\n")
                sys.stderr.flush()
            except Exception:
                pass
        sys.exit(1)

    use_native = startup_mode.is_native

    ico_path = get_resource_path("assets/icon.ico")
    png_path = get_resource_path("assets/icon.png")
    favicon_path: str | None = None
    if ico_path.is_file():
        favicon_path = str(ico_path)
    elif png_path.is_file():
        favicon_path = str(png_path)

    # 2. If native mode is active, validate and configure the native backend
    if use_native:
        try:
            validate_and_prepare_native_backend(
                icon_path=png_path if png_path.is_file() else ico_path
            )
        except NativeBackendError as exc:
            if sys.stderr is not None:
                try:
                    sys.stderr.write(f"\n[ERROR] {exc}\n\n")
                    sys.stderr.flush()
                except Exception:
                    pass
            sys.exit(1)

    use_case = build_application()
    create_app(use_case)

    _setup_signal_handlers()
    _setup_test_shutdown_endpoint(DEFAULT_HOST)

    if use_native:
        from nicegui import app, Server

        def _on_native_window_closed(*_args: Any, **_kwargs: Any) -> None:
            """Proactive graceful shutdown coordinator when desktop window closes."""
            try:
                if hasattr(Server, "instance") and Server.instance is not None:
                    Server.instance.should_exit = True
            except Exception:
                pass
            try:
                app.shutdown()
            except Exception:
                pass

        try:
            app.native.on("closed", _on_native_window_closed)
        except Exception:
            pass

    configured_port = resolve_configured_port(sys.argv, os.environ, DEFAULT_PORT)
    port = get_available_port(DEFAULT_HOST, configured_port)

    show_browser = ("--no-show" not in sys.argv) and not use_native

    try:
        ui.run(
            host=DEFAULT_HOST,
            title=f"{__title__} — Phần mềm Học tập & Nghiên cứu Toán học",
            port=port,
            reload=False,
            native=use_native,
            window_size=(1200, 800) if use_native else None,
            favicon=favicon_path,
            show=show_browser,
            timeout_graceful_shutdown=3.0,
        )
    except KeyboardInterrupt:
        pass
    finally:
        # Deterministic teardown sequence:
        # 1. Stop NiceGUI thread/process pools
        try:
            from nicegui import run
            run.tear_down()
        except Exception:
            pass

        # 2. Bounded join for multiprocessing child processes (native window process)
        if use_native:
            try:
                import multiprocessing
                for child in multiprocessing.active_children():
                    try:
                        child.join(timeout=2.0)
                        if child.is_alive():
                            child.terminate()
                            child.join(timeout=1.0)
                    except Exception:
                        pass
            except Exception:
                pass

        # 3. Flush standard streams
        if sys.stdout is not None:
            try:
                sys.stdout.flush()
            except Exception:
                pass
        if sys.stderr is not None:
            try:
                sys.stderr.flush()
            except Exception:
                pass


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()

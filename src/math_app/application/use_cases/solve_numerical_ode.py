"""Application use case orchestrating numerical ODE solving, comparison, and verification."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
import time

from math_app.application.ports.numerical_ode import (
    AnalyticalComparisonProvider,
    NumericalODESolver,
    NumericalODEVerifier,
)
from math_app.domain.numerical_ode import (
    NumericalODEMethod,
    NumericalODERequest,
    NumericalODEResponse,
    NumericalODEStatus,
)


class SolveNumericalODEUseCase:
    """Orchestrates numerical ODE IVP approximation via decoupled solver, comparison, and verifier ports."""

    def __init__(
        self,
        solvers: Sequence[NumericalODESolver],
        verifier: NumericalODEVerifier | None = None,
        analytical_provider: AnalyticalComparisonProvider | None = None,
    ) -> None:
        self._solvers: dict[NumericalODEMethod, NumericalODESolver] = {
            s.method: s for s in solvers
        }
        self._verifier = verifier
        self._analytical_provider = analytical_provider

    def execute(self, request: NumericalODERequest) -> NumericalODEResponse:
        """Execute numerical approximation, optional analytical comparison, and independent verification."""
        t_start = time.perf_counter()

        solver = self._solvers.get(request.method)
        if solver is None:
            return NumericalODEResponse(
                status=NumericalODEStatus.ERROR,
                method=request.method,
                order=request.order,
                raw_equation=request.raw_equation,
                error_message=f"Chưa đăng ký bộ giải số cho phương pháp '{request.method.value}'.",
                warnings=(f"No numerical solver registered for method '{request.method.value}'.",),
                execution_time_ms=(time.perf_counter() - t_start) * 1000.0,
            )

        response = solver.solve(request)

        if response.status == NumericalODEStatus.SUCCESS:
            if request.compute_analytical_comparison and self._analytical_provider is not None:
                try:
                    comparison = self._analytical_provider.compare(request, response)
                except Exception:
                    comparison = None
                if comparison is not None:
                    response = replace(response, analytical_comparison=comparison)

            if self._verifier is not None:
                verification = self._verifier.verify(request, response)
                response = replace(response, verification=verification)

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        return replace(response, execution_time_ms=elapsed_ms)

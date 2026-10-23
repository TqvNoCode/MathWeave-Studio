"""Use case orchestrating problem routing, solving, and response delivery."""

from __future__ import annotations

from collections.abc import Sequence
import time

from math_app.application.dtos import ProblemRequest, SolutionResponse, VerificationResult
from math_app.application.ports.solver import Solver
from math_app.application.ports.solver_registry import SolverRegistry
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import SolutionStatus, VerificationStatus


class SolveProblemUseCase:
    """Orchestrates problem solving via abstract SolverRegistry or solver sequence."""

    def __init__(self, registry: SolverRegistry | Sequence[Solver]) -> None:
        if hasattr(registry, "get"):
            self._registry: SolverRegistry | None = registry
            self._solvers: Sequence[Solver] | None = None
        else:
            self._registry = None
            self._solvers = list(registry)

    def execute(self, request: ProblemRequest) -> SolutionResponse:
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

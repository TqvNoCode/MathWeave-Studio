"""Unit tests for SolveProblemUseCase and SolverRegistry."""

from math_app.application.dtos import (
    ProblemRequest,
    SolutionResponse,
    VerificationResult,
)
from math_app.application.ports.solver import Solver
from math_app.application.registry import DefaultSolverRegistry
from math_app.application.use_cases.solve_problem import SolveProblemUseCase
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus


class DummyDerivativeSolver(Solver):
    """Mock solver for use case orchestration testing."""

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type == ProblemType.DERIVATIVE

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        if "syntax_err" in request.raw_input:
            raise InvalidInputError("Triggered syntax error.")
        if "crash" in request.raw_input:
            raise RuntimeError("Unexpected failure.")

        return SolutionResponse(
            status=SolutionStatus.SUCCESS,
            verification=VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="mock",
                details="Mock verification.",
            ),
            raw_input=request.raw_input,
            canonical_input=request.raw_input,
            final_result="2*x",
            final_latex="2x",
        )


def test_use_case_successful_dispatch():
    registry = DefaultSolverRegistry()
    registry.register(ProblemType.DERIVATIVE, DummyDerivativeSolver())

    use_case = SolveProblemUseCase(registry)
    request = ProblemRequest(
        raw_input="x^2",
        problem_type=ProblemType.DERIVATIVE,
        target_variable="x",
    )
    response = use_case.execute(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.final_result == "2*x"
    assert response.verification.status == VerificationStatus.VERIFIED
    assert response.execution_time_ms >= 0.0


def test_use_case_empty_input():
    registry = DefaultSolverRegistry()
    use_case = SolveProblemUseCase(registry)

    request = ProblemRequest(
        raw_input="   ",
        problem_type=ProblemType.DERIVATIVE,
    )
    response = use_case.execute(request)

    assert response.status == SolutionStatus.INVALID_INPUT
    assert "cannot be empty" in response.warnings[0]


def test_use_case_invalid_variable_identifier():
    registry = DefaultSolverRegistry()
    use_case = SolveProblemUseCase(registry)

    request = ProblemRequest(
        raw_input="x^2",
        problem_type=ProblemType.DERIVATIVE,
        target_variable="123invalid",
    )
    response = use_case.execute(request)

    assert response.status == SolutionStatus.INVALID_INPUT
    assert "Invalid target variable" in response.warnings[0]


def test_use_case_unregistered_problem_type():
    registry = DefaultSolverRegistry()
    use_case = SolveProblemUseCase(registry)

    request = ProblemRequest(
        raw_input="sin(x)",
        problem_type=ProblemType.INTEGRAL,
    )
    response = use_case.execute(request)

    assert response.status == SolutionStatus.CANNOT_SOLVE
    assert "No registered solver" in response.warnings[0]


def test_use_case_handles_solver_invalid_input_error():
    registry = DefaultSolverRegistry()
    registry.register(ProblemType.DERIVATIVE, DummyDerivativeSolver())
    use_case = SolveProblemUseCase(registry)

    request = ProblemRequest(
        raw_input="syntax_err",
        problem_type=ProblemType.DERIVATIVE,
    )
    response = use_case.execute(request)

    assert response.status == SolutionStatus.INVALID_INPUT
    assert "Triggered syntax error" in response.warnings[0]


def test_use_case_handles_unexpected_exception():
    registry = DefaultSolverRegistry()
    registry.register(ProblemType.DERIVATIVE, DummyDerivativeSolver())
    use_case = SolveProblemUseCase(registry)

    request = ProblemRequest(
        raw_input="crash",
        problem_type=ProblemType.DERIVATIVE,
    )
    response = use_case.execute(request)

    assert response.status == SolutionStatus.CANNOT_SOLVE
    assert "unexpected failure" in response.warnings[0]

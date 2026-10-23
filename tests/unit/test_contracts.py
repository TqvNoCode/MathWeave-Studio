"""Unit tests for domain and application contracts and use cases."""

from math_app.application.dtos import (
    ProblemRequest,
    SolutionResponse,
    SolutionStep,
    VerificationResult,
)
from math_app.application.ports.solver import Solver
from math_app.application.use_cases.solve_problem import SolveProblemUseCase
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.domain.step_content import ExpressionStepContent


class MockDerivativeSolver:
    """Mock solver satisfying Solver protocol for testing."""

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type == ProblemType.DERIVATIVE

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        if "error" in request.raw_input:
            raise InvalidInputError("Mock syntax error.")
        if "crash" in request.raw_input:
            raise RuntimeError("Unexpected failure.")

        step = SolutionStep(
            step_number=1,
            rule_name="Power Rule",
            description="Differentiate x^2 to get 2*x",
            content=ExpressionStepContent("x^2", "2*x", "x^2", "2*x"),
        )
        return SolutionResponse(
            status=SolutionStatus.SUCCESS,
            verification=VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="mock",
                details="Mock verification.",
            ),
            raw_input=request.raw_input,
            canonical_input="x**2",
            final_result="2*x",
            final_latex="2x",
            steps=(step,),
        )


def test_solver_protocol_conformance():
    """Verify that MockDerivativeSolver satisfies the runtime-checkable Solver protocol."""
    solver = MockDerivativeSolver()
    assert isinstance(solver, Solver)


def test_solution_step_immutability():
    """Verify SolutionStep is frozen and preserves all fields."""
    step = SolutionStep(
        step_number=1,
        rule_name="Sum Rule",
        description="Split sum of terms",
        content=ExpressionStepContent("x + 1", "d/dx(x) + d/dx(1)", "x + 1", "d/dx(x) + d/dx(1)"),
    )
    assert step.step_number == 1
    assert step.rule_name == "Sum Rule"
    assert step.substeps == ()


def test_solve_problem_use_case_success():
    """SolveProblemUseCase successfully routes to matching solver."""
    use_case = SolveProblemUseCase([MockDerivativeSolver()])
    request = ProblemRequest(
        raw_input="x^2",
        problem_type=ProblemType.DERIVATIVE,
        target_variable="x",
    )
    response = use_case.execute(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.final_result == "2*x"
    assert len(response.steps) == 1
    assert response.steps[0].rule_name == "Power Rule"
    assert response.execution_time_ms >= 0.0


def test_solve_problem_use_case_empty_input():
    """Empty or whitespace input must yield INVALID_INPUT status."""
    use_case = SolveProblemUseCase([MockDerivativeSolver()])
    request = ProblemRequest(
        raw_input="   ",
        problem_type=ProblemType.DERIVATIVE,
    )
    response = use_case.execute(request)
    assert response.status == SolutionStatus.INVALID_INPUT
    assert "cannot be empty" in response.warnings[0]


def test_solve_problem_use_case_invalid_variable():
    """Non-identifier target variable must yield INVALID_INPUT status."""
    use_case = SolveProblemUseCase([MockDerivativeSolver()])
    request = ProblemRequest(
        raw_input="x^2",
        problem_type=ProblemType.DERIVATIVE,
        target_variable="123invalid",
    )
    response = use_case.execute(request)
    assert response.status == SolutionStatus.INVALID_INPUT
    assert "Invalid target variable" in response.warnings[0]


def test_solve_problem_use_case_no_matching_solver():
    """Request with no capable solver returns CANNOT_SOLVE without raising."""
    use_case = SolveProblemUseCase([MockDerivativeSolver()])
    request = ProblemRequest(
        raw_input="sin(x)",
        problem_type=ProblemType.INTEGRAL,
    )
    response = use_case.execute(request)
    assert response.status == SolutionStatus.CANNOT_SOLVE
    assert "No registered solver" in response.warnings[0]


def test_solve_problem_use_case_handles_invalid_input_error():
    """Solver raising InvalidInputError produces INVALID_INPUT response."""
    use_case = SolveProblemUseCase([MockDerivativeSolver()])
    request = ProblemRequest(
        raw_input="error expression",
        problem_type=ProblemType.DERIVATIVE,
    )
    response = use_case.execute(request)
    assert response.status == SolutionStatus.INVALID_INPUT
    assert "Mock syntax error" in response.warnings[0]


def test_solve_problem_use_case_handles_unexpected_exception():
    """Solver raising unexpected exception produces CANNOT_SOLVE response."""
    use_case = SolveProblemUseCase([MockDerivativeSolver()])
    request = ProblemRequest(
        raw_input="crash expression",
        problem_type=ProblemType.DERIVATIVE,
    )
    response = use_case.execute(request)
    assert response.status == SolutionStatus.CANNOT_SOLVE
    assert "unexpected error" in response.warnings[0]

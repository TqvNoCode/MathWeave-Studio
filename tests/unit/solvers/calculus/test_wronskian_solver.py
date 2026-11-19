"""Unit tests for Wronskian determinant and linear independence solver."""

import pytest

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.wronskian_solver import WronskianSolver


@pytest.fixture
def solver() -> WronskianSolver:
    return WronskianSolver()


def test_wronskian_trigonometric(solver: WronskianSolver):
    """Test W(cos(t), sin(t)) = 1."""
    req = ProblemRequest(
        raw_input="cos(t), sin(t)",
        problem_type=ProblemType.WRONSKIAN,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "= 1" in res.final_result
    titles = [s.title for s in res.steps]
    assert any("wronskian" in t.lower() for t in titles)


def test_wronskian_exponential_independent(solver: WronskianSolver):
    """Test W(exp(t), t*exp(t)) = exp(2t) != 0."""
    req = ProblemRequest(
        raw_input="y1 = exp(t), y2 = t*exp(t)",
        problem_type=ProblemType.WRONSKIAN,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(2*t)" in res.final_result


def test_wronskian_linearly_dependent_polynomials(solver: WronskianSolver):
    """Test W(2t, 5t) = 0 => Inconclusive for arbitrary functions without verified ODE."""
    req = ProblemRequest(
        raw_input="2*t, 5*t",
        problem_type=ProblemType.WRONSKIAN,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.UNVERIFIED
    assert res.verification.status == VerificationStatus.UNVERIFIED
    assert "= 0" in res.final_result
    assert any("chưa đủ điều kiện kết luận" in s.description.lower() or "inconclusive" in s.description.lower() for s in res.steps)


def test_wronskian_linearly_dependent_exponentials(solver: WronskianSolver):
    """Test W(exp(t), 3*exp(t)) = 0 => Inconclusive for arbitrary functions without verified ODE."""
    req = ProblemRequest(
        raw_input="exp(t), 3*exp(t)",
        problem_type=ProblemType.WRONSKIAN,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.UNVERIFIED
    assert res.verification.status == VerificationStatus.UNVERIFIED
    assert "= 0" in res.final_result


def test_wronskian_via_parameters(solver: WronskianSolver):
    """Test Wronskian passed via parameters dictionary."""
    req = ProblemRequest(
        raw_input="",
        problem_type=ProblemType.WRONSKIAN,
        target_variable="t",
        parameters={"y1": "1/t", "y2": "sqrt(t)"},
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "t**(3/2)" in res.final_result or "sqrt(t)" in res.final_result


def test_wronskian_empty_input_rejected(solver: WronskianSolver):
    """Test that empty input is rejected with clear error."""
    req = ProblemRequest(
        raw_input="",
        problem_type=ProblemType.WRONSKIAN,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="không được để trống|Cần cung cấp đủ hai hàm số"):
        solver.solve(req)

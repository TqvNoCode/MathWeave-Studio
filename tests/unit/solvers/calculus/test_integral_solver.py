"""Unit tests for calculus integration solver and FTC verification."""

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.integration.solver import IntegralSolver


def test_indefinite_integral_polynomial_power_rule():
    """Textbook Case: int(x^2 dx) = x^3 / 3 + C."""
    solver = IntegralSolver()
    request = ProblemRequest("x^2", ProblemType.INDEFINITE_INTEGRAL, target_variable="x")
    response = solver.solve(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED
    assert "+ C" in response.final_result
    assert any("Power Rule" in s.rule_name or "lũy thừa" in s.rule_name for s in response.steps)

    # Check symbolic derivative matches original
    x = sp.Symbol("x")
    anti_expr = sp.sympify(response.final_result.replace("+ C", "").strip())
    assert sp.simplify(sp.diff(anti_expr, x) - (x ** 2)) == 0


def test_indefinite_integral_trig_linearity():
    """int(3*cos(x) dx) = 3*sin(x) + C."""
    solver = IntegralSolver()
    request = ProblemRequest("3*cos(x)", ProblemType.INDEFINITE_INTEGRAL, target_variable="x")
    response = solver.solve(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED
    assert "+ C" in response.final_result


def test_definite_integral_polynomial():
    """int_0^1 (x^2 dx) = 1/3."""
    solver = IntegralSolver()
    request = ProblemRequest(
        "x^2",
        ProblemType.DEFINITE_INTEGRAL,
        target_variable="x",
        parameters={"lower_bound": "0", "upper_bound": "1"},
    )
    response = solver.solve(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED
    assert response.final_result == "1/3"
    assert response.final_latex == "\\frac{1}{3}"


def test_definite_integral_invalid_bounds():
    """Invalid bounds must raise InvalidInputError."""
    solver = IntegralSolver()
    request = ProblemRequest(
        "x^2",
        ProblemType.DEFINITE_INTEGRAL,
        target_variable="x",
        parameters={"lower_bound": "invalid_syntax++", "upper_bound": "1"},
    )
    with pytest.raises(InvalidInputError):
        solver.solve(request)

"""Golden tests verifying curriculum problem derivations against pedagogical standards."""

import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.differentiation.solver import DerivativeSolver


def test_golden_product_rule_curriculum_case():
    """Textbook Case: f(x) = x^2 * sin(x) -> f'(x) = 2x*sin(x) + x^2*cos(x)."""
    solver = DerivativeSolver()
    request = ProblemRequest("x^2 * sin(x)", ProblemType.DERIVATIVE, target_variable="x")
    response = solver.solve(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED

    # Check that main step is Product Rule
    assert any(s.rule_name == "Product Rule" for s in response.steps)

    # Check symbolic equivalence of final answer
    x = sp.Symbol("x")
    expected = 2 * x * sp.sin(x) + (x ** 2) * sp.cos(x)
    actual = sp.sympify(response.final_result)
    assert sp.simplify(actual - expected) == 0


def test_golden_quotient_rule_curriculum_case():
    """Textbook Case: f(x) = x / (x + 1) -> f'(x) = 1 / (x + 1)^2."""
    solver = DerivativeSolver()
    request = ProblemRequest("x / (x + 1)", ProblemType.DERIVATIVE, target_variable="x")
    response = solver.solve(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED

    assert any(s.rule_name == "Quotient Rule" for s in response.steps)

    x = sp.Symbol("x")
    expected = 1 / ((x + 1) ** 2)
    actual = sp.sympify(response.final_result)
    assert sp.simplify(actual - expected) == 0


def test_golden_chain_rule_curriculum_case():
    """Textbook Case: f(x) = sin(x^2) -> f'(x) = 2x * cos(x^2)."""
    solver = DerivativeSolver()
    request = ProblemRequest("sin(x^2)", ProblemType.DERIVATIVE, target_variable="x")
    response = solver.solve(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED

    assert any(s.rule_name == "Chain Rule" for s in response.steps)

    x = sp.Symbol("x")
    expected = 2 * x * sp.cos(x ** 2)
    actual = sp.sympify(response.final_result)
    assert sp.simplify(actual - expected) == 0


def test_golden_polynomial_linearity_curriculum_case():
    """Textbook Case: f(x) = 3*x^4 - 5*x^2 + 2 -> f'(x) = 12*x^3 - 10*x."""
    solver = DerivativeSolver()
    request = ProblemRequest("3*x^4 - 5*x^2 + 2", ProblemType.DERIVATIVE, target_variable="x")
    response = solver.solve(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED

    x = sp.Symbol("x")
    expected = 12 * (x ** 3) - 10 * x
    actual = sp.sympify(response.final_result)
    assert sp.simplify(actual - expected) == 0

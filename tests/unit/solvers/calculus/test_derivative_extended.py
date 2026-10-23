"""Regression and extended capability tests for differentiation solver."""

import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.differentiation.solver import DerivativeSolver


def test_regression_cos_minus_tan():
    """CRITICAL REGRESSION TEST:

    f(x) = cos(x) - tan(x) -> f'(x) = -sin(x) - sec^2(x).
    Must produce non-empty final result, non-empty latex, valid steps, and honest verification.
    """
    solver = DerivativeSolver()
    request = ProblemRequest("cos(x) - tan(x)", ProblemType.DERIVATIVE, target_variable="x")
    response = solver.solve(request)

    # 1. State must be SUCCESS
    assert response.status == SolutionStatus.SUCCESS

    # 2. Final result must not be blank or empty
    assert response.final_result != ""
    assert response.final_latex != ""

    # 3. Steps must be recorded
    assert len(response.steps) >= 1

    # 4. Independent mathematical verification
    assert response.verification.status == VerificationStatus.VERIFIED

    # 5. Symbolic equivalence: -sin(x) - 1/cos(x)^2 == -sin(x) - sec(x)^2
    x = sp.Symbol("x")
    expected = -sp.sin(x) - (1 / (sp.cos(x) ** 2))
    actual = sp.sympify(response.final_result)
    assert sp.simplify(actual - expected) == 0

    # 6. Domain notes for tan / cos(x) != 0
    assert any("cos" in note or "tan" in note for note in response.domain_restrictions)


def test_higher_order_derivative():
    """Higher-order: f(x) = x^3 -> 1st derivative = 3x^2, 2nd derivative = 6x."""
    solver = DerivativeSolver()

    # Order 1
    req1 = ProblemRequest("x^3", ProblemType.DERIVATIVE, target_variable="x")
    res1 = solver.solve(req1)
    assert res1.final_result == "3*x**2"

    # Order 2
    req2 = ProblemRequest(
        "x^3",
        ProblemType.HIGHER_ORDER_DERIVATIVE,
        target_variable="x",
        parameters={"order": 2},
    )
    res2 = solver.solve(req2)
    assert res2.status == SolutionStatus.SUCCESS
    assert res2.verification.status == VerificationStatus.VERIFIED
    assert res2.final_result == "6*x"


def test_partial_derivative():
    """Partial derivative: d/dx [x^2*y + y^3] = 2*x*y, d/dy [x^2*y + y^3] = x^2 + 3*y^2."""
    solver = DerivativeSolver()

    req_x = ProblemRequest("x^2*y + y^3", ProblemType.PARTIAL_DERIVATIVE, target_variable="x")
    res_x = solver.solve(req_x)
    x, y = sp.symbols("x y")
    assert sp.simplify(sp.sympify(res_x.final_result) - 2 * x * y) == 0

    req_y = ProblemRequest("x^2*y + y^3", ProblemType.PARTIAL_DERIVATIVE, target_variable="y")
    res_y = solver.solve(req_y)
    assert sp.simplify(sp.sympify(res_y.final_result) - (x ** 2 + 3 * (y ** 2))) == 0


def test_differentiation_with_greek_symbols():
    """Variables theta and phi in ASCII and Unicode."""
    solver = DerivativeSolver()

    req_th = ProblemRequest("sin(θ) + cos(θ)", ProblemType.DERIVATIVE, target_variable="θ")
    res_th = solver.solve(req_th)
    assert res_th.status == SolutionStatus.SUCCESS
    th = sp.Symbol("theta")
    assert sp.simplify(sp.sympify(res_th.final_result) - (sp.cos(th) - sp.sin(th))) == 0


def test_exponential_and_logarithm_rules():
    """d/dx [exp(x)] = exp(x), d/dx [ln(x)] = 1/x."""
    solver = DerivativeSolver()

    res_exp = solver.solve(ProblemRequest("exp(x)", ProblemType.DERIVATIVE, target_variable="x"))
    assert res_exp.final_result == "exp(x)"
    assert res_exp.verification.status == VerificationStatus.VERIFIED

    res_ln = solver.solve(ProblemRequest("ln(x)", ProblemType.DERIVATIVE, target_variable="x"))
    assert res_ln.final_result == "1/x"
    assert res_ln.verification.status == VerificationStatus.VERIFIED


def test_differentiation_with_t_and_u():
    """d/dt [t^3] = 3*t^2, d/du [u^2] = 2*u."""
    solver = DerivativeSolver()

    res_t = solver.solve(ProblemRequest("t^3", ProblemType.DERIVATIVE, target_variable="t"))
    assert res_t.final_result == "3*t**2"

    res_u = solver.solve(ProblemRequest("u^2", ProblemType.DERIVATIVE, target_variable="u"))
    assert res_u.final_result == "2*u"


def test_differentiation_with_polar_and_spherical_variables():
    """d/dr [r^2] = 2*r, d/dρ [ρ^3] = 3*ρ^2."""
    solver = DerivativeSolver()

    res_r = solver.solve(ProblemRequest("r^2", ProblemType.DERIVATIVE, target_variable="r"))
    assert res_r.final_result == "2*r"
    assert res_r.verification.status == VerificationStatus.VERIFIED

    res_rho = solver.solve(ProblemRequest("ρ^3", ProblemType.DERIVATIVE, target_variable="ρ"))
    assert "3*rho**2" in res_rho.final_result
    assert res_rho.verification.status == VerificationStatus.VERIFIED

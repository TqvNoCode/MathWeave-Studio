"""Unit tests for Reduction of Order solver for second-order ODEs."""

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.reduction_of_order_solver import ODEReductionOfOrderSolver


@pytest.fixture
def solver() -> ODEReductionOfOrderSolver:
    return ODEReductionOfOrderSolver()


# =========================================================================
# Four Mandatory Reference Examples (Section 6)
# =========================================================================

def test_reference_example_1_euler_cauchy(solver: ODEReductionOfOrderSolver):
    """Example 1: 2*t^2*y'' + 3*t*y' - y = 0 with known solution y1 = 1/t.

    p(t) = 3/(2t)
    u(t) = exp(-int p dt)/y1^2 = t^(1/2)
    v(t) = 2/3 * t^(3/2)
    y2(t) = 2/3 * sqrt(t) (or sqrt(t) up to constant multiple)
    Domain: t > 0 (t = 0 is singular).
    """
    req = ProblemRequest(
        raw_input="2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    # Check that final solution contains 1/t and sqrt(t) or t**(1/2)
    assert "1/t" in res.final_result
    assert "sqrt(t)" in res.final_result or "t**(1/2)" in res.final_result

    # Domain restriction mentions singularity at t = 0
    assert any("t" in dr and ("0" in dr or "kỳ dị" in dr) for dr in res.domain_restrictions)

    # Verification of second solution mathematically
    t = sp.Symbol("t", positive=True)
    y2_cand = sp.sqrt(t)
    dy2 = sp.diff(y2_cand, t)
    d2y2 = sp.diff(dy2, t)
    assert sp.simplify(2 * t**2 * d2y2 + 3 * t * dy2 - y2_cand) == 0

    # Wronskian of 1/t and sqrt(t)
    y1 = 1 / t
    w = sp.simplify(y1 * dy2 - sp.diff(y1, t) * y2_cand)
    assert w != 0


def test_reference_example_2_repeated_root(solver: ODEReductionOfOrderSolver):
    """Example 2: y'' - 2y' + y = 0 with known solution y1 = exp(t).

    Expected: y2 = t*exp(t)
    General: y = (C1 + C2*t)*exp(t).
    """
    req = ProblemRequest(
        raw_input="y'' - 2*y' + y = 0, y1 = exp(t)",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(t)" in res.final_result
    assert "*t" in res.final_result or "t*exp(t)" in res.final_result

    # Steps check
    titles = [s.title for s in res.steps]
    rules = [s.rule_name for s in res.steps]
    assert any("chuẩn tắc" in t.lower() or "chuẩn hóa" in r.lower() for t, r in zip(titles, rules))
    assert any("kiểm chứng" in t.lower() or "kiểm tra" in t.lower() for t in titles)
    assert any("hạ bậc" in t.lower() for t in titles)
    assert any("u = v'" in t.lower() or "cấp 1" in t.lower() for t in titles)


def test_reference_example_3_trigonometric(solver: ODEReductionOfOrderSolver):
    """Example 3: y'' + y = 0 with known solution y1 = cos(t).

    Intermediate contains 1/cos(t)^2 = sec(t)^2.
    Integral gives tan(t).
    y2 = cos(t)*tan(t) = sin(t).
    """
    req = ProblemRequest(
        raw_input="y'' + y = 0, y1 = cos(t)",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "cos(t)" in res.final_result
    assert "sin(t)" in res.final_result


def test_reference_example_4_euler_type(solver: ODEReductionOfOrderSolver):
    """Example 4: y'' - (2/t^2)*y = 0 with known solution y1 = t^2.

    Expected: y2 = -1/(3t) or 1/t.
    Domain: t != 0.
    """
    req = ProblemRequest(
        raw_input="y'' - (2/t^2)*y = 0, y1 = t^2",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "t**2" in res.final_result
    assert "1/t" in res.final_result or "3*t" in res.final_result or "t**(-1)" in res.final_result


# =========================================================================
# Validation and Edge Cases
# =========================================================================

def test_invalid_known_solution_rejected(solver: ODEReductionOfOrderSolver):
    """Verify that an incorrect candidate y1 that does not satisfy the ODE is rejected."""
    req = ProblemRequest(
        raw_input="y'' + y = 0, y1 = exp(t)",  # exp(t) does NOT satisfy y'' + y = 0
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="không thỏa mãn phương trình vi phân ban đầu"):
        solver.solve(req)


def test_missing_known_solution_rejected(solver: ODEReductionOfOrderSolver):
    """Verify that omitting y1 raises clear instructions."""
    req = ProblemRequest(
        raw_input="y'' + y = 0",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="Cần cung cấp nghiệm đã biết y1"):
        solver.solve(req)


def test_reduction_of_order_with_ivp(solver: ODEReductionOfOrderSolver):
    """Verify Reduction of Order with Cauchy initial conditions."""
    req = ProblemRequest(
        raw_input="y'' - 2*y' + y = 0, y1 = exp(t), y(0) = 1, y'(0) = 4",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    expected = (1 + 3 * t) * sp.exp(t)
    res_str = res.final_result.split("=", 1)[1].strip()
    assert sp.simplify(sp.sympify(res_str) - expected) == 0


def test_euler_cauchy_negative_interval_domain_regression():
    """Domain regression for Section 5:

    2t^2*y'' + 3t*y' - y = 0, with y1 = 1/t.
    Verify:
    1. Positive interval (t > 0): y2 = sqrt(t) satisfies ODE and Wronskian != 0.
    2. Negative interval (t < 0): y2 = sqrt(-t) satisfies ODE and Wronskian != 0.
    3. The singularity at t = 0 separates the domain into disconnected intervals.
    """
    # 1. Negative interval: t < 0
    t_neg = sp.Symbol("t", negative=True)
    y1_neg = 1 / t_neg
    y2_neg = sp.sqrt(-t_neg)

    # Check ODE residual for y1 on t < 0: 2*t^2*y1'' + 3*t*y1' - y1 == 0
    dy1 = sp.diff(y1_neg, t_neg)
    d2y1 = sp.diff(dy1, t_neg)
    res_y1 = sp.simplify(2 * t_neg**2 * d2y1 + 3 * t_neg * dy1 - y1_neg)
    assert res_y1 == 0

    # Check ODE residual for y2 on t < 0: 2*t^2*y2'' + 3*t*y2' - y2 == 0
    dy2 = sp.diff(y2_neg, t_neg)
    d2y2 = sp.diff(dy2, t_neg)
    res_y2 = sp.simplify(2 * t_neg**2 * d2y2 + 3 * t_neg * dy2 - y2_neg)
    assert res_y2 == 0

    # Check Wronskian on t < 0: W(y1, y2) = y1*y2' - y1'*y2
    w_neg = sp.simplify(y1_neg * dy2 - dy1 * y2_neg)
    # At t = -1: w_neg(-1) should be 3/2 != 0
    w_at_minus_1 = sp.simplify(w_neg.subs(t_neg, -1))
    assert w_at_minus_1 != 0
    assert w_at_minus_1 == sp.Rational(3, 2)

    # 2. Positive interval: t > 0
    t_pos = sp.Symbol("t", positive=True)
    y1_pos = 1 / t_pos
    y2_pos = sp.sqrt(t_pos)

    # ODE residual for y2 on t > 0
    dy2_p = sp.diff(y2_pos, t_pos)
    d2y2_p = sp.diff(dy2_p, t_pos)
    res_y2_pos = sp.simplify(2 * t_pos**2 * d2y2_p + 3 * t_pos * dy2_p - y2_pos)
    assert res_y2_pos == 0

    # Wronskian on t > 0
    w_pos = sp.simplify(y1_pos * dy2_p - sp.diff(y1_pos, t_pos) * y2_pos)
    w_at_1 = sp.simplify(w_pos.subs(t_pos, 1))
    assert w_at_1 != 0
    assert w_at_1 == sp.Rational(3, 2)

    # 3. Disconnected interval verification: t = 0 is singular
    a_coeff = 2 * t_pos**2
    assert a_coeff.subs(t_pos, 0) == 0


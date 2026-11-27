"""Comprehensive regression and acceptance tests for Nonhomogeneous Euler–Cauchy ODEs."""

from __future__ import annotations

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.euler_cauchy_solver import ODEEulerCauchySolver


@pytest.fixture
def solver() -> ODEEulerCauchySolver:
    return ODEEulerCauchySolver()


def _solve_ec(
    solver: ODEEulerCauchySolver,
    raw_input: str,
    *,
    var_name: str = "t",
    parameters: dict | None = None,
):
    req = ProblemRequest(
        raw_input=raw_input,
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable=var_name,
        parameters=parameters or {},
    )
    return solver.solve(req)


# ==============================================================================
# Required Tests A - H
# ==============================================================================


def test_a_distinct_real_roots_prompt_fixture_and_classic_pair(solver: ODEEulerCauchySolver):
    """Test A: Distinct real roots nonhomogeneous equations (m=1+-sqrt(3) and m=2,-1), yp = -1/2."""
    t_pos = sp.Symbol("t", positive=True)

    # Exact prompt equation: t^2*y'' - t*y' - 2*y = 1, t > 0 -> m^2 - 2m - 2 = 0 (m = 1 +- sqrt(3)), yp = -1/2
    res_prompt = _solve_ec(solver, "t^2*y'' - t*y' - 2*y = 1, t > 0")
    assert res_prompt.status == SolutionStatus.SUCCESS
    assert res_prompt.verification.status == VerificationStatus.VERIFIED
    expr_prompt = res_prompt.branch_solutions[0].expression.subs(sp.Symbol("t"), t_pos)
    c1, c2 = sp.Symbol("C1"), sp.Symbol("C2")
    assert sp.simplify(expr_prompt.subs({c1: 0, c2: 0}) - sp.Rational(-1, 2)) == 0

    # Classic distinct integer indicial pair yc = C1*t^2 + C2*t^(-1): t^2*y'' - 2*y = 1, t > 0
    res_int = _solve_ec(solver, "t^2*y'' - 2*y = 1, t > 0")
    assert res_int.status == SolutionStatus.SUCCESS
    assert res_int.verification.status == VerificationStatus.VERIFIED
    expr_int = res_int.branch_solutions[0].expression.subs(sp.Symbol("t"), t_pos)
    assert sp.simplify(expr_int.subs({c1: 0, c2: 0}) - sp.Rational(-1, 2)) == 0
    expected_int = c1 * t_pos**2 + c2 / t_pos - sp.Rational(1, 2)
    assert sp.simplify(expr_int - expected_int) == 0


def test_b_repeated_root_non_resonant_forcing(solver: ODEEulerCauchySolver):
    """Test B: t^2*y'' - t*y' + y = t^2, t > 0 -> yc = t*(C1 + C2*ln(t)), yp = t^2."""
    t_pos = sp.Symbol("t", positive=True)
    res = _solve_ec(solver, "t^2*y'' - t*y' + y = t^2, t > 0")

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    expr = res.branch_solutions[0].expression.subs(sp.Symbol("t"), t_pos)
    c1, c2 = sp.Symbol("C1"), sp.Symbol("C2")
    assert sp.simplify(expr.subs({c1: 0, c2: 0}) - t_pos**2) == 0
    expected = c1 * t_pos + c2 * t_pos * sp.log(t_pos) + t_pos**2
    assert sp.simplify(expr - expected) == 0


def test_c_repeated_root_resonance(solver: ODEEulerCauchySolver):
    """Test C: t^2*y'' - t*y' + y = t, t > 0 -> yp = 1/2 * t * (ln t)^2."""
    t_pos = sp.Symbol("t", positive=True)
    res = _solve_ec(solver, "t^2*y'' - t*y' + y = t, t > 0")

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    expr = res.branch_solutions[0].expression.subs(sp.Symbol("t"), t_pos)
    c1, c2 = sp.Symbol("C1"), sp.Symbol("C2")
    yp = sp.simplify(expr.subs({c1: 0, c2: 0}))
    assert sp.simplify(yp - sp.Rational(1, 2) * t_pos * sp.log(t_pos) ** 2) == 0


def test_c2_distinct_root_resonance(solver: ODEEulerCauchySolver):
    """Resonance with simple indicial root: t^2*y'' - 2*y = t^2, t > 0 -> yp = (1/3)*t^2*ln(t)."""
    t_pos = sp.Symbol("t", positive=True)
    res = _solve_ec(solver, "t^2*y'' - 2*y = t^2, t > 0")

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    expr = res.branch_solutions[0].expression.subs(sp.Symbol("t"), t_pos)
    c1, c2 = sp.Symbol("C1"), sp.Symbol("C2")
    # Particular solution mod linear comb of {t^2, t^-1} must equal (1/3)*t^2*log(t)
    residual_yp = sp.simplify(expr.subs({c1: 0, c2: 0}) - sp.Rational(1, 3) * t_pos**2 * sp.log(t_pos))
    assert sp.simplify(t_pos**2 * sp.diff(residual_yp, t_pos, 2) - 2 * residual_yp) == 0
    assert residual_yp.has(sp.log) is False


def test_d_complex_conjugate_roots_real_valued(solver: ODEEulerCauchySolver):
    """Test D: t^2*y'' + t*y' + y = 1, t > 0 -> real cos/sin basis and yp = 1 (zero imaginary units)."""
    t_pos = sp.Symbol("t", positive=True)
    res = _solve_ec(solver, "t^2*y'' + t*y' + y = 1, t > 0")

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    expr = res.branch_solutions[0].expression.subs(sp.Symbol("t"), t_pos)
    assert not expr.has(sp.I)
    c1, c2 = sp.Symbol("C1"), sp.Symbol("C2")
    expected = c1 * sp.cos(sp.log(t_pos)) + c2 * sp.sin(sp.log(t_pos)) + 1
    assert sp.simplify(expr - expected) == 0


def test_e_negative_domain_real_valued(solver: ODEEulerCauchySolver):
    """Test E: t < 0 negative domain uses |t| = -t and ln(-t) with zero complex/invalid powers."""
    t_neg = sp.Symbol("t", negative=True)
    c1, c2 = sp.Symbol("C1"), sp.Symbol("C2")

    # Repeated + resonant on t < 0: t^2*y'' - t*y' + y = t, t < 0
    res_res = _solve_ec(solver, "t^2*y'' - t*y' + y = t, t < 0")
    assert res_res.status == SolutionStatus.SUCCESS
    assert res_res.verification.status == VerificationStatus.VERIFIED
    expr_res = res_res.branch_solutions[0].expression
    assert not expr_res.has(sp.I)
    assert expr_res.has(sp.log(-sp.Symbol("t")))
    # At t = -e < 0, numerical evaluation is real and finite
    val = sp.N(expr_res.subs({sp.Symbol("t"): -sp.E, c1: 1, c2: 2}))
    assert abs(complex(val).imag) < 1e-12

    # Complex conjugate roots + forcing on t < 0: t^2*y'' + t*y' + y = t, t < 0
    res_cmp = _solve_ec(solver, "t^2*y'' + t*y' + y = t, t < 0")
    assert res_cmp.status == SolutionStatus.SUCCESS
    assert res_cmp.verification.status == VerificationStatus.VERIFIED
    expr_cmp = res_cmp.branch_solutions[0].expression.subs(sp.Symbol("t"), t_neg)
    assert not expr_cmp.has(sp.I)
    assert sp.simplify(expr_cmp.subs({c1: 0, c2: 0}) - sp.Rational(1, 2) * t_neg) == 0


def test_f_cauchy_ivp_positive_and_negative_domains(solver: ODEEulerCauchySolver):
    """Test F: t^2*y'' - t*y' + y = t^2, y(1) = 0, y'(1) = 0 -> y(t) = t^2 - t - t*ln(t)."""
    res = _solve_ec(solver, "t^2*y'' - t*y' + y = t^2, y(1) = 0, y'(1) = 0")
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t_pos = sp.Symbol("t", positive=True)
    expr = res.branch_solutions[0].expression.subs(sp.Symbol("t"), t_pos)
    expected = t_pos**2 - t_pos - t_pos * sp.log(t_pos)
    assert sp.simplify(expr - expected) == 0
    assert sp.simplify(expr.subs(t_pos, 1)) == 0
    assert sp.simplify(sp.diff(expr, t_pos).subs(t_pos, 1)) == 0

    # Negative-domain Cauchy IVP: y(-1) = 0, y'(-1) = 0 -> y(t) = t^2 + t - t*ln(-t) (satisfies ODE & ICs on t < 0)
    res_neg = _solve_ec(solver, "t^2*y'' - t*y' + y = t^2, y(-1) = 0, y'(-1) = 0")
    assert res_neg.status == SolutionStatus.SUCCESS
    assert res_neg.verification.status == VerificationStatus.VERIFIED
    t_neg = sp.Symbol("t", negative=True)
    expr_neg = res_neg.branch_solutions[0].expression.subs(sp.Symbol("t"), t_neg)
    assert not expr_neg.has(sp.I)
    assert sp.simplify(expr_neg.subs(t_neg, -1)) == 0
    assert sp.simplify(sp.diff(expr_neg, t_neg).subs(t_neg, -1)) == 0


def test_g_singular_initial_point_rejected(solver: ODEEulerCauchySolver):
    """Test G: t0 = 0 singular initial point must fail cleanly without misleading solution."""
    res = _solve_ec(solver, "t^2*y'' - t*y' + y = t^2, y(0) = 0, y'(0) = 0")
    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert res.verification.method == "singular_point_initial_condition"
    assert res.final_result == ""


def test_h_non_elementary_symbolic_forcing_honest_integral_preservation(solver: ODEEulerCauchySolver):
    """Test H: exp(t^2) forcing has no elementary closed form; preserve exact sp.Integral honestly."""
    res = _solve_ec(solver, "t^2*y'' - t*y' + y = exp(t^2), t > 0")
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    expr = res.branch_solutions[0].expression
    assert expr.has(sp.Integral)
    assert not expr.has(sp.I)
    assert any("nguyên hàm sơ cấp" in w.lower() for w in res.warnings)

    # Also test Cauchy IVP with non-elementary forcing (anchored at t0 = 1)
    res_ivp = _solve_ec(solver, "t^2*y'' - t*y' + y = exp(t^2), y(1) = 2, y'(1) = 1")
    assert res_ivp.status == SolutionStatus.SUCCESS
    assert res_ivp.verification.status == VerificationStatus.VERIFIED
    assert res_ivp.branch_solutions[0].expression.has(sp.Integral)


# ==============================================================================
# Additional Symbolic Families, Multi-Branch Domains & Validation Cases
# ==============================================================================


@pytest.mark.parametrize(
    "eq",
    [
        "t^2*y'' - 3*t*y' + 4*y = log(t), t > 0",
        "t^2*y'' - 2*y = sin(log(t)), t > 0",
        "t^2*y'' + 3*t*y' + y = t^3 + 1/t, t > 0",
        "t^2*y'' - t*y' + y = exp(t), t > 0",
    ],
)
def test_diverse_forcing_families(solver: ODEEulerCauchySolver, eq: str):
    """Supported symbolic forcing (log, trig-log, rational, exp) solves and verifies cleanly."""
    res = _solve_ec(solver, eq)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert not res.branch_solutions[0].expression.has(sp.I)


def test_natural_split_domain_without_interval(solver: ODEEulerCauchySolver):
    """General nonhomogeneous Euler–Cauchy without explicit interval returns 2 independent branches (t>0, t<0)."""
    res = _solve_ec(solver, "t^2*y'' - t*y' + y = t^2")
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 2
    # Branch 1 (t > 0) uses C1, C2 and Branch 2 (t < 0) uses C3, C4
    b_pos, b_neg = res.branch_solutions
    assert sp.Symbol("C1") in b_pos.expression.free_symbols
    assert sp.Symbol("C3") in b_neg.expression.free_symbols
    assert not b_pos.expression.has(sp.I)
    assert not b_neg.expression.has(sp.I)


def test_homogeneous_zero_rhs_does_not_trigger_vop(solver: ODEEulerCauchySolver):
    """Equation with g(t) = 0 must remain homogeneous without adding Variation of Parameters steps."""
    res = _solve_ec(solver, "t^2*y'' - t*y' + y = t - t, t > 0")
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert not any(s.rule_name == "Nghiệm riêng biến thiên hằng số" for s in res.steps)


def test_validation_guards_interval_crossing_zero_pole_and_ic_errors(solver: ODEEulerCauchySolver):
    """Cross-zero intervals, poles of g(t) at t0, and missing/mismatched ICs are rejected cleanly."""
    # Interval crossing t=0
    res_cross = _solve_ec(solver, "t^2*y'' - t*y' + y = t^2, -1 < t < 2")
    assert res_cross.status == SolutionStatus.CANNOT_SOLVE
    assert res_cross.verification.method == "singular_point_interval"

    # Initial point at pole of g(t) = 1/(t - 2)
    res_pole = _solve_ec(solver, "t^2*y'' - t*y' + y = 1/(t - 2), y(2) = 1, y'(2) = 0")
    assert res_pole.status == SolutionStatus.INVALID_INPUT

    # Missing second IC
    with pytest.raises(InvalidInputError):
        _solve_ec(solver, "t^2*y'' - t*y' + y = t^2, y(1) = 0")

    # Mismatched IC base points
    with pytest.raises(InvalidInputError):
        _solve_ec(solver, "t^2*y'' - t*y' + y = t^2, y(1) = 0, y'(2) = 0")


def test_pedagogical_steps_distinguish_yc_yp_and_vop_stages(solver: ODEEulerCauchySolver):
    """Steps explicitly derive normalized P, Q, R, u1', u2', u1, u2, y_p, and y = y_c + y_p."""
    res = _solve_ec(solver, "t^2*y'' - t*y' + y = t^2, t > 0")
    rule_names = [s.rule_name for s in res.steps]
    assert "Nhận dạng dạng phương trình Euler–Cauchy" in rule_names
    assert "Nghiệm thuần nhất liên kết" in rule_names
    assert "Chuẩn hóa và phương pháp Biến thiên hằng số" in rule_names
    assert "Đạo hàm hàm biến thiên" in rule_names
    assert "Tích phân hàm biến thiên" in rule_names
    assert "Nghiệm riêng biến thiên hằng số" in rule_names
    assert "Nghiệm tổng quát" in rule_names
    assert "Kiểm chứng độc lập" in rule_names

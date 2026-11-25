"""Comprehensive Unit Test Suite for Second-Order Nonhomogeneous Cauchy Initial Value Problems (IVPs).

Milestone 3 (M3) Testing Suite.
Covers:
- Method A: Undetermined Coefficients IVP (non-resonant, resonant, polynomial, exponential, trigonometric).
- Method B: Variation of Parameters IVP with canonical initial-point-anchored definite integrals.
- Reference tests REF-1 through REF-15.
- Edge cases: Non-unity leading coefficients, repeated roots, complex conjugate roots, variable x, negative t0.
- Domain and singularity validation for initial point t0.
- Rejection of incomplete, mismatched, infinite, or complex initial conditions.
- Zero-regression for homogeneous Cauchy IVPs and general solutions.
"""

from __future__ import annotations

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.nonhomogeneous_ivp import (
    solve_nonhomogeneous_cauchy_system,
    validate_initial_point_against_domain,
)
from math_app.solvers.calculus.ode.second_order_constant_coeff_solver import (
    ODESecondOrderConstantCoeffSolver,
)


@pytest.fixture
def solver() -> ODESecondOrderConstantCoeffSolver:
    return ODESecondOrderConstantCoeffSolver()


def assert_cauchy_ivp_solution(
    res,
    t0_val: sp.Expr | int,
    expected_y0: sp.Expr | int,
    expected_v0: sp.Expr | int,
    a_coeff: sp.Expr | int,
    b_coeff: sp.Expr | int,
    c_coeff: sp.Expr | int,
    forcing_expr: sp.Expr,
    var: sp.Symbol | None = None,
    expected_expr: sp.Expr | None = None,
) -> sp.Expr:
    """Helper to independently verify ODE residual, both Cauchy conditions, and expected form."""
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    if var is None:
        var = sp.Symbol("t")

    sol_expr = sp.sympify(res.final_result.split("=")[1].strip())

    # 1. Exact match against expected closed form if provided
    if expected_expr is not None:
        diff_expected = sp.simplify(sol_expr - expected_expr)
        assert diff_expected == 0

    # 2. Independent ODE residual verification: R(t) = a*y'' + b*y' + c*y - g(t)
    dy = sp.diff(sol_expr, var)
    d2y = sp.diff(dy, var)
    ode_residual = sp.simplify(a_coeff * d2y + b_coeff * dy + c_coeff * sol_expr - forcing_expr)
    if hasattr(ode_residual, "doit"):
        ode_residual = sp.simplify(ode_residual.doit())
    assert ode_residual == 0

    # 3. Independent Cauchy condition verification: y(t0) = y0
    y_at_t0 = sol_expr.subs(var, t0_val)
    if hasattr(y_at_t0, "doit"):
        y_at_t0 = sp.simplify(y_at_t0.doit())
    e0 = sp.simplify(y_at_t0 - expected_y0)
    assert e0 == 0

    # 4. Independent Cauchy condition verification: y'(t0) = v0
    dy_at_t0 = dy.subs(var, t0_val)
    if hasattr(dy_at_t0, "doit"):
        dy_at_t0 = sp.simplify(dy_at_t0.doit())
    e1 = sp.simplify(dy_at_t0 - expected_v0)
    assert e1 == 0

    return sol_expr


# =============================================================================
# 1. Direct Unit Tests for nonhomogeneous_ivp module
# =============================================================================


def test_validate_initial_point_domain_valid():
    """Verify validate_initial_point_against_domain accepts valid interior points."""
    t = sp.Symbol("t")
    # log(t) with t0 = 1 > 0
    ok, err = validate_initial_point_against_domain(sp.Integer(1), sp.log(t), t)
    assert ok is True
    assert err is None

    # 1/t with t0 = 2 != 0
    ok, err = validate_initial_point_against_domain(sp.Integer(2), 1 / t, t)
    assert ok is True
    assert err is None

    # tan(t) with t0 = 0
    ok, err = validate_initial_point_against_domain(sp.Integer(0), sp.tan(t), t)
    assert ok is True
    assert err is None


def test_validate_initial_point_domain_singularities():
    """Verify validate_initial_point_against_domain catches poles and non-real points."""
    t = sp.Symbol("t")
    # log(t) with t0 = 0
    ok, err = validate_initial_point_against_domain(sp.Integer(0), sp.log(t), t)
    assert ok is False
    assert "logarit" in err

    # log(t) with t0 = -1
    ok, err = validate_initial_point_against_domain(sp.Integer(-1), sp.log(t), t)
    assert ok is False
    assert "logarit" in err

    # 1/t with t0 = 0
    ok, err = validate_initial_point_against_domain(sp.Integer(0), 1 / t, t)
    assert ok is False
    assert "mẫu số" in err

    # tan(t) with t0 = pi/2
    ok, err = validate_initial_point_against_domain(sp.pi / 2, sp.tan(t), t)
    assert ok is False
    assert "pole" in err.lower() or "tan/sec" in err

    # Infinite t0
    ok, err = validate_initial_point_against_domain(sp.oo, t, t)
    assert ok is False
    assert "hữu hạn" in err


def test_direct_solve_nonhomogeneous_cauchy_system_uc():
    """Verify direct Cramer solver on elementary UC particular solution."""
    t = sp.Symbol("t")
    y1 = sp.exp(4 * t)
    y2 = sp.exp(-t)
    yp = -sp.Rational(1, 2) * sp.exp(2 * t)
    res = solve_nonhomogeneous_cauchy_system(
        y1=y1,
        y2=y2,
        yp=yp,
        t0=sp.Integer(0),
        y0=sp.Integer(1),
        v0=sp.Integer(0),
        var=t,
        is_anchored_vop=False,
    )
    assert res.is_valid is True
    assert res.c1_value == sp.Rational(1, 2)
    assert res.c2_value == sp.Integer(1)
    expected = sp.Rational(1, 2) * sp.exp(4 * t) + sp.exp(-t) - sp.Rational(1, 2) * sp.exp(2 * t)
    assert sp.simplify(res.y_ivp_solution - expected) == 0


def test_direct_solve_nonhomogeneous_cauchy_system_anchored_vop():
    """Verify direct Cramer solver with canonical anchored VoP conditions."""
    t = sp.Symbol("t")
    s = sp.Symbol("s")
    y1 = sp.cos(t)
    y2 = sp.sin(t)
    # Anchored integrals at t0 = 1
    u1 = -sp.Integral(sp.sin(s) * sp.log(s), (s, 1, t))
    u2 = sp.Integral(sp.cos(s) * sp.log(s), (s, 1, t))
    yp = u1 * y1 + u2 * y2
    res = solve_nonhomogeneous_cauchy_system(
        y1=y1,
        y2=y2,
        yp=yp,
        t0=sp.Integer(1),
        y0=sp.Integer(0),
        v0=sp.Integer(1),
        var=t,
        is_anchored_vop=True,
    )
    assert res.is_valid is True
    assert sp.simplify(res.c1_value - (-sp.sin(1))) == 0
    assert sp.simplify(res.c2_value - sp.cos(1)) == 0


# =============================================================================
# 2. Reference Tests REF-1 through REF-15
# =============================================================================


def test_ref1_undetermined_coefficients_non_resonant_exponential(
    solver: ODESecondOrderConstantCoeffSolver,
):
    """REF-1: y'' - 3y' - 4y = 3*e^(2t), y(0) = 1, y'(0) = 0.

    Expected: y(t) = (1/2)*e^(4t) + e^(-t) - (1/2)*e^(2t).
    """
    req = ProblemRequest(
        raw_input="y'' - 3y' - 4y = 3*exp(2*t), y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    expected = sp.Rational(1, 2) * sp.exp(4 * t) + sp.exp(-t) - sp.Rational(1, 2) * sp.exp(2 * t)
    assert_cauchy_ivp_solution(
        res,
        t0_val=0,
        expected_y0=1,
        expected_v0=0,
        a_coeff=1,
        b_coeff=-3,
        c_coeff=-4,
        forcing_expr=3 * sp.exp(2 * t),
        var=t,
        expected_expr=expected,
    )


def test_ref2_undetermined_coefficients_simple_resonance(
    solver: ODESecondOrderConstantCoeffSolver,
):
    """REF-2: y'' - 3y' - 4y = 3*e^(4t), y(0) = 2, y'(0) = 3.

    Characteristic roots: 4, -1. Resonance with e^(4t) => s=1.
    Y_p = (3/5)*t*e^(4t).
    Expected: y(t) = (22/25)*e^(4t) + (28/25)*e^(-t) + (3/5)*t*e^(4t).
    """
    req = ProblemRequest(
        raw_input="y'' - 3y' - 4y = 3*exp(4*t), y(0) = 2, y'(0) = 3",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    expected = (
        sp.Rational(22, 25) * sp.exp(4 * t)
        + sp.Rational(28, 25) * sp.exp(-t)
        + sp.Rational(3, 5) * t * sp.exp(4 * t)
    )
    assert_cauchy_ivp_solution(
        res,
        t0_val=0,
        expected_y0=2,
        expected_v0=3,
        a_coeff=1,
        b_coeff=-3,
        c_coeff=-4,
        forcing_expr=3 * sp.exp(4 * t),
        var=t,
        expected_expr=expected,
    )


def test_ref3_undetermined_coefficients_polynomial_forcing(
    solver: ODESecondOrderConstantCoeffSolver,
):
    """REF-3: y'' + y' - 2y = 2t, y(0) = 1, y'(0) = 0.

    Characteristic roots: 1, -2.
    Y_p = -t - 1/2.
    Expected: y(t) = (4/3)*e^t + (1/6)*e^(-2t) - t - 1/2.
    """
    req = ProblemRequest(
        raw_input="y'' + y' - 2y = 2*t, y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    expected = (
        sp.Rational(4, 3) * sp.exp(t)
        + sp.Rational(1, 6) * sp.exp(-2 * t)
        - t
        - sp.Rational(1, 2)
    )
    assert_cauchy_ivp_solution(
        res,
        t0_val=0,
        expected_y0=1,
        expected_v0=0,
        a_coeff=1,
        b_coeff=1,
        c_coeff=-2,
        forcing_expr=2 * t,
        var=t,
        expected_expr=expected,
    )


def test_ref4_variation_of_parameters_tangent_forcing(
    solver: ODESecondOrderConstantCoeffSolver,
):
    """REF-4: y'' + y = tan(t), y(0) = 1, y'(0) = 0.

    Anchored VoP at t0 = 0.
    C1 = 1, C2 = 0.
    """
    req = ProblemRequest(
        raw_input="y'' + y = tan(t), y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    assert_cauchy_ivp_solution(
        res,
        t0_val=0,
        expected_y0=1,
        expected_v0=0,
        a_coeff=1,
        b_coeff=0,
        c_coeff=1,
        forcing_expr=sp.tan(t),
        var=t,
    )
    assert any("Biến thiên hằng số" in s.title or "Lagrange" in s.title for s in res.steps)


def test_ref5_variation_of_parameters_logarithmic_forcing(
    solver: ODESecondOrderConstantCoeffSolver,
):
    """REF-5: y'' + y = ln(t), t > 0, y(1) = 0, y'(1) = 1.

    Anchored VoP at t0 = 1.
    C1 = -sin(1), C2 = cos(1).
    """
    req = ProblemRequest(
        raw_input="y'' + y = log(t), y(1) = 0, y'(1) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    assert_cauchy_ivp_solution(
        res,
        t0_val=1,
        expected_y0=0,
        expected_v0=1,
        a_coeff=1,
        b_coeff=0,
        c_coeff=1,
        forcing_expr=sp.log(t),
        var=t,
    )
    assert "log" in res.final_result


def test_ref6_rational_forcing(solver: ODESecondOrderConstantCoeffSolver):
    """REF-6: y'' + y = 1/t, t > 0, y(1) = 2, y'(1) = -1.

    Anchored VoP at t0 = 1.
    """
    req = ProblemRequest(
        raw_input="y'' + y = 1/t, y(1) = 2, y'(1) = -1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    assert_cauchy_ivp_solution(
        res,
        t0_val=1,
        expected_y0=2,
        expected_v0=-1,
        a_coeff=1,
        b_coeff=0,
        c_coeff=1,
        forcing_expr=1 / t,
        var=t,
    )


def test_ref7_radical_forcing_valid_endpoint(solver: ODESecondOrderConstantCoeffSolver):
    """REF-7: y'' + y = sqrt(t), y(0) = 0, y'(0) = 0."""
    req = ProblemRequest(
        raw_input="y'' + y = sqrt(t), y(0) = 0, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    assert_cauchy_ivp_solution(
        res,
        t0_val=0,
        expected_y0=0,
        expected_v0=0,
        a_coeff=1,
        b_coeff=0,
        c_coeff=1,
        forcing_expr=sp.sqrt(t),
        var=t,
    )


def test_ref8_non_elementary_exponential_forcing(solver: ODESecondOrderConstantCoeffSolver):
    """REF-8: y'' + y = exp(t^2), y(0) = 1, y'(0) = 2.

    Non-elementary forcing => exact anchored definite integral.
    """
    req = ProblemRequest(
        raw_input="y'' + y = exp(t**2), y(0) = 1, y'(0) = 2",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    assert_cauchy_ivp_solution(
        res,
        t0_val=0,
        expected_y0=1,
        expected_v0=2,
        a_coeff=1,
        b_coeff=0,
        c_coeff=1,
        forcing_expr=sp.exp(t**2),
        var=t,
    )


def test_ref9_damped_complex_roots(solver: ODESecondOrderConstantCoeffSolver):
    """REF-9: y'' + 2y' + 2y = log(t), y(1) = 1, y'(1) = 0.

    Anchored VoP at t0 = 1.
    C1 = e*(cos(1) - sin(1)), C2 = e*(cos(1) + sin(1)).
    """
    req = ProblemRequest(
        raw_input="y'' + 2*y' + 2*y = log(t), y(1) = 1, y'(1) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    assert_cauchy_ivp_solution(
        res,
        t0_val=1,
        expected_y0=1,
        expected_v0=0,
        a_coeff=1,
        b_coeff=2,
        c_coeff=2,
        forcing_expr=sp.log(t),
        var=t,
    )


def test_ref10_non_unity_leading_coefficient_1(solver: ODESecondOrderConstantCoeffSolver):
    """REF-10a: 2*y'' - 4*y' - 6*y = 4*exp(t), y(0) = 0, y'(0) = 1.

    a = 2. Roots: 3, -1. Y_p = -(1/2)*exp(t).
    Expected: y(t) = (1/2)*exp(3t) - (1/2)*exp(t).
    """
    req = ProblemRequest(
        raw_input="2*y'' - 4*y' - 6*y = 4*exp(t), y(0) = 0, y'(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    expected = sp.Rational(1, 2) * sp.exp(3 * t) - sp.Rational(1, 2) * sp.exp(t)
    assert_cauchy_ivp_solution(
        res,
        t0_val=0,
        expected_y0=0,
        expected_v0=1,
        a_coeff=2,
        b_coeff=-4,
        c_coeff=-6,
        forcing_expr=4 * sp.exp(t),
        var=t,
        expected_expr=expected,
    )


def test_ref10_non_unity_leading_coefficient_2(solver: ODESecondOrderConstantCoeffSolver):
    """REF-10b: 4*y'' + y = 2*cos(t), y(0) = 1, y'(0) = 0.

    Expected: y(t) = (5/3)*cos(t/2) - (2/3)*cos(t).
    """
    req = ProblemRequest(
        raw_input="4*y'' + y = 2*cos(t), y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    expected = sp.Rational(5, 3) * sp.cos(t / 2) - sp.Rational(2, 3) * sp.cos(t)
    assert_cauchy_ivp_solution(
        res,
        t0_val=0,
        expected_y0=1,
        expected_v0=0,
        a_coeff=4,
        b_coeff=0,
        c_coeff=1,
        forcing_expr=2 * sp.cos(t),
        var=t,
        expected_expr=expected,
    )


def test_ref10_negative_leading_coefficient(solver: ODESecondOrderConstantCoeffSolver):
    """REF-10c: -y'' + 2*y' - y = t, y(0) = 0, y'(0) = 0.

    a = -1, repeated root r = 1. Y_p = -t - 2.
    Expected: y(t) = (2 - t)*exp(t) - t - 2.
    """
    req = ProblemRequest(
        raw_input="-y'' + 2*y' - y = t, y(0) = 0, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    expected = (2 - t) * sp.exp(t) - t - 2
    assert_cauchy_ivp_solution(
        res,
        t0_val=0,
        expected_y0=0,
        expected_v0=0,
        a_coeff=-1,
        b_coeff=2,
        c_coeff=-1,
        forcing_expr=t,
        var=t,
        expected_expr=expected,
    )


def test_ref11_mixed_superposition_ivp(solver: ODESecondOrderConstantCoeffSolver):
    """REF-11: y'' - y = exp(t) + t, y(0) = 1, y'(0) = 0.

    Resonant exp(t) + polynomial t.
    C1 = 3/4, C2 = 1/4.
    Expected: y(t) = (3/4)*exp(t) + (1/4)*exp(-t) + (1/2)*t*exp(t) - t.
    """
    req = ProblemRequest(
        raw_input="y'' - y = exp(t) + t, y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    expected = (
        sp.Rational(3, 4) * sp.exp(t)
        + sp.Rational(1, 4) * sp.exp(-t)
        + sp.Rational(1, 2) * t * sp.exp(t)
        - t
    )
    assert_cauchy_ivp_solution(
        res,
        t0_val=0,
        expected_y0=1,
        expected_v0=0,
        a_coeff=1,
        b_coeff=0,
        c_coeff=-1,
        forcing_expr=sp.exp(t) + t,
        var=t,
        expected_expr=expected,
    )


def test_ref12_m1_m2_method_fallback_in_ivp_mode(solver: ODESecondOrderConstantCoeffSolver):
    """REF-12: Verify UC is applied for polynomial/exponential, and VoP for sec(t)."""
    # UC case
    req_uc = ProblemRequest(
        raw_input="y'' + 4*y = 4*t, y(0) = 0, y'(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res_uc = solver.solve(req_uc)
    assert res_uc.status == SolutionStatus.SUCCESS
    assert any("hệ số bất định" in s.title.lower() for s in res_uc.steps)

    # VoP fallback case
    req_vop = ProblemRequest(
        raw_input="y'' + 4*y = sec(2*t), y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res_vop = solver.solve(req_vop)
    assert res_vop.status == SolutionStatus.SUCCESS
    assert any("Biến thiên hằng số" in s.title or "Lagrange" in s.title for s in res_vop.steps)


def test_ref13_invalid_initial_points_domain_violation(
    solver: ODESecondOrderConstantCoeffSolver,
):
    """REF-13: Points violating domain must return CANNOT_SOLVE with clear details."""
    # log(t) with t0 = 0
    req1 = ProblemRequest(
        raw_input="y'' + y = log(t), y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res1 = solver.solve(req1)
    assert res1.status == SolutionStatus.CANNOT_SOLVE
    assert "logarit" in res1.verification.details

    # log(t) with t0 = -2
    req2 = ProblemRequest(
        raw_input="y'' + y = log(t), y(-2) = 1, y'(-2) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res2 = solver.solve(req2)
    assert res2.status == SolutionStatus.CANNOT_SOLVE
    assert "logarit" in res2.verification.details

    # 1/t with t0 = 0
    req3 = ProblemRequest(
        raw_input="y'' + y = 1/t, y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res3 = solver.solve(req3)
    assert res3.status == SolutionStatus.CANNOT_SOLVE
    assert "mẫu số" in res3.verification.details

    # tan(t) with t0 = pi/2
    req4 = ProblemRequest(
        raw_input="y'' + y = tan(t), y(pi/2) = 1, y'(pi/2) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res4 = solver.solve(req4)
    assert res4.status == SolutionStatus.CANNOT_SOLVE
    assert "pole" in res4.verification.details.lower() or "tan/sec" in res4.verification.details


def test_ref14_incomplete_or_mismatched_cauchy_conditions(
    solver: ODESecondOrderConstantCoeffSolver,
):
    """REF-14: Incomplete, mismatched, or singular Cauchy conditions must raise InvalidInputError."""
    # Missing derivative condition
    req_missing_yp = ProblemRequest(
        raw_input="y'' - 4*y = exp(t), y(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="thiếu điều kiện"):
        solver.solve(req_missing_yp)

    # Missing initial value condition
    req_missing_y = ProblemRequest(
        raw_input="y'' - 4*y = exp(t), y'(0) = 2",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="thiếu điều kiện"):
        solver.solve(req_missing_y)

    # Mismatched initial points t0 != t1
    req_mismatch = ProblemRequest(
        raw_input="y'' - 4*y = exp(t), y(0) = 1, y'(1) = 2",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="cùng một điểm"):
        solver.solve(req_mismatch)

    # Complex initial values
    req_complex = ProblemRequest(
        raw_input="y'' - 4*y = exp(t), y(0) = I, y'(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="hữu hạn"):
        solver.solve(req_complex)

    # Infinite initial values
    req_inf = ProblemRequest(
        raw_input="y'' - 4*y = exp(t), y(0) = oo, y'(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="hữu hạn"):
        solver.solve(req_inf)


def test_ref15_homogeneous_ivp_non_regression(solver: ODESecondOrderConstantCoeffSolver):
    """REF-15: Homogeneous Cauchy IVPs must continue to solve and verify with zero regression."""
    # Distinct real roots
    req1 = ProblemRequest(
        raw_input="y'' - 4*y = 0, y(0) = 1, y'(0) = 2",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res1 = solver.solve(req1)
    assert res1.status == SolutionStatus.SUCCESS
    assert res1.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    # y = e^(2t)
    sol1 = sp.sympify(res1.final_result.split("=")[1].strip())
    assert sp.simplify(sol1 - sp.exp(2 * t)) == 0

    # Complex conjugate roots
    req2 = ProblemRequest(
        raw_input="y'' + 4*y = 0, y(0) = 0, y'(0) = 2",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res2 = solver.solve(req2)
    assert res2.status == SolutionStatus.SUCCESS
    assert res2.verification.status == VerificationStatus.VERIFIED
    sol2 = sp.sympify(res2.final_result.split("=")[1].strip())
    assert sp.simplify(sol2 - sp.sin(2 * t)) == 0

    # Repeated real root
    req3 = ProblemRequest(
        raw_input="y'' - 2*y' + y = 0, y(0) = 1, y'(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res3 = solver.solve(req3)
    assert res3.status == SolutionStatus.SUCCESS
    assert res3.verification.status == VerificationStatus.VERIFIED
    sol3 = sp.sympify(res3.final_result.split("=")[1].strip())
    assert sp.simplify(sol3 - sp.exp(t)) == 0


# =============================================================================
# 3. Additional Robustness, Boundary & Structural Tests
# =============================================================================


def test_repeated_root_nonhomogeneous_double_resonance_ivp(
    solver: ODESecondOrderConstantCoeffSolver,
):
    """Repeated root with double resonance forcing: y'' - 2y' + y = exp(t), y(0) = 1, y'(0) = 0.

    r = 1 (mult 2). s = 2 => Y_p = (1/2)*t^2*exp(t).
    y(t) = C1*e^t + C2*t*e^t + (1/2)*t^2*e^t.
    y(0) = C1 = 1.
    y'(0) = C1 + C2 = 0 => C2 = -1.
    y(t) = (1 - t + (1/2)*t^2)*e^t.
    """
    req = ProblemRequest(
        raw_input="y'' - 2*y' + y = exp(t), y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    expected = (1 - t + sp.Rational(1, 2) * t**2) * sp.exp(t)
    sol_expr = sp.sympify(res.final_result.split("=")[1].strip())
    assert sp.simplify(sol_expr - expected) == 0


def test_pure_imaginary_roots_resonant_cosine_ivp(
    solver: ODESecondOrderConstantCoeffSolver,
):
    """Pure imaginary roots with resonant cosine forcing: y'' + 4y = cos(2t), y(0) = 0, y'(0) = 1.

    Roots +/- 2i. Y_p = (1/4)*t*sin(2t).
    y(t) = C1*cos(2t) + C2*sin(2t) + (1/4)*t*sin(2t).
    y(0) = C1 = 0.
    y'(0) = 2*C2 = 1 => C2 = 1/2.
    y(t) = (1/2)*sin(2t) + (1/4)*t*sin(2t).
    """
    req = ProblemRequest(
        raw_input="y'' + 4*y = cos(2*t), y(0) = 0, y'(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    expected = sp.Rational(1, 2) * sp.sin(2 * t) + sp.Rational(1, 4) * t * sp.sin(2 * t)
    sol_expr = sp.sympify(res.final_result.split("=")[1].strip())
    assert sp.simplify(sol_expr - expected) == 0


def test_target_variable_x_ivp(solver: ODESecondOrderConstantCoeffSolver):
    """Verify target variable 'x' works seamlessly for nonhomogeneous IVP."""
    req = ProblemRequest(
        raw_input="y'' - y = exp(x), y(0) = 1, y'(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="x",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "y(x)" in res.final_result

    x = sp.Symbol("x")
    # r = 1, -1. Y_p = (1/2)*x*e^x.
    # y = C1*e^x + C2*e^(-x) + (1/2)*x*e^x.
    # y(0) = C1 + C2 = 1.
    # y'(0) = C1 - C2 + 1/2 = 1 => C1 - C2 = 1/2.
    # 2*C1 = 3/2 => C1 = 3/4, C2 = 1/4.
    expected = (
        sp.Rational(3, 4) * sp.exp(x)
        + sp.Rational(1, 4) * sp.exp(-x)
        + sp.Rational(1, 2) * x * sp.exp(x)
    )
    sol_expr = sp.sympify(res.final_result.split("=")[1].strip())
    assert sp.simplify(sol_expr - expected) == 0


def test_negative_initial_point_t0(solver: ODESecondOrderConstantCoeffSolver):
    """Verify negative initial point t0 = -1 works correctly."""
    req = ProblemRequest(
        raw_input="y'' - y = exp(t), y(-1) = 0, y'(-1) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    sol_expr = sp.sympify(res.final_result.split("=")[1].strip())
    assert sp.simplify(sol_expr.subs(t, -1) - 0) == 0
    assert sp.simplify(sp.diff(sol_expr, t).subs(t, -1) - 1) == 0


def test_fractional_coefficients_ivp(solver: ODESecondOrderConstantCoeffSolver):
    """Verify equation with fractional rational coefficients: y'' + (1/2)*y' - (1/2)*y = exp(t)."""
    req = ProblemRequest(
        raw_input="y'' + 1/2*y' - 1/2*y = exp(t), y(0) = 0, y'(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


def test_derivation_steps_structure_and_substeps(solver: ODESecondOrderConstantCoeffSolver):
    """Inspect pedagogical steps structure for Cauchy system derivation."""
    req = ProblemRequest(
        raw_input="y'' - 3*y' - 4*y = 3*exp(2*t), y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS

    # Verify key derivation steps exist
    rule_names = [s.rule_name for s in res.steps]
    assert "Phương trình đặc trưng" in rule_names
    assert "Dạng nghiệm riêng đề xuất" in rule_names
    assert "Áp dụng điều kiện ban đầu" in rule_names
    assert "Giải hệ xác định hằng số" in rule_names
    assert "Nghiệm duy nhất bài toán Cauchy" in rule_names
    assert "Kiểm chứng nghiệm" in rule_names

    # Check substeps on the Cauchy conditions step
    cauchy_step = next(s for s in res.steps if s.rule_name == "Áp dụng điều kiện ban đầu")
    assert len(cauchy_step.substeps) == 3
    assert any("y(t0)" in ss.rule_name for ss in cauchy_step.substeps)
    assert any("y'(t0)" in ss.rule_name for ss in cauchy_step.substeps)
    assert any("2x2" in ss.rule_name for ss in cauchy_step.substeps)


def test_singular_cauchy_matrix_handling():
    """Verify solve_nonhomogeneous_cauchy_system handles degenerate fundamental sets gracefully."""
    t = sp.Symbol("t")
    # Identical fundamental solutions (linearly dependent, W = 0)
    res = solve_nonhomogeneous_cauchy_system(
        y1=sp.exp(t),
        y2=sp.exp(t),
        yp=sp.Integer(0),
        t0=sp.Integer(0),
        y0=sp.Integer(1),
        v0=sp.Integer(0),
        var=t,
    )
    assert res.is_valid is False
    assert "suy biến" in res.error_reason or "triệt tiêu" in res.error_reason


def test_ref16_undetermined_coefficients_exponential_cosine_forcing_ivp(
    solver: ODESecondOrderConstantCoeffSolver,
):
    """REF-16: y'' + y = exp(t)*cos(t), y(0) = 0, y'(0) = 1."""
    req = ProblemRequest(
        raw_input="y'' + y = exp(t)*cos(t), y(0) = 0, y'(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    expected = (
        (sp.Integer(2) * sp.sin(t) + sp.cos(t)) * sp.exp(t) / 5
        + sp.Integer(2) * sp.sin(t) / 5
        - sp.cos(t) / 5
    )
    assert_cauchy_ivp_solution(
        res,
        t0_val=0,
        expected_y0=0,
        expected_v0=1,
        a_coeff=1,
        b_coeff=0,
        c_coeff=1,
        forcing_expr=sp.exp(t) * sp.cos(t),
        var=t,
        expected_expr=expected,
    )


def test_ref17_cauchy_ivp_with_symbolic_initial_condition_values(
    solver: ODESecondOrderConstantCoeffSolver,
):
    """REF-17: y'' - 4*y = 4*t with symbolic IC values y(0) = y0, y'(0) = v0."""
    req = ProblemRequest(
        raw_input="y'' - 4*y = 4*t, y(0) = y0, y'(0) = v0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert "y0" in res.final_result
    assert "v0" in res.final_result


def test_ref18_cauchy_ivp_with_negative_coefficients(
    solver: ODESecondOrderConstantCoeffSolver,
):
    """REF-18: -2*y'' - 6*y' - 4*y = 4, y(0) = 1, y'(0) = 0."""
    req = ProblemRequest(
        raw_input="-2*y'' - 6*y' - 4*y = 4, y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    expected = 2 * (2 * sp.exp(t) - 1) * sp.exp(-2 * t) - 1
    assert_cauchy_ivp_solution(
        res,
        t0_val=0,
        expected_y0=1,
        expected_v0=0,
        a_coeff=-2,
        b_coeff=-6,
        c_coeff=-4,
        forcing_expr=sp.Integer(4),
        var=t,
        expected_expr=expected,
    )


def test_ref19_anchored_vop_ivp_with_secant_forcing(
    solver: ODESecondOrderConstantCoeffSolver,
):
    """REF-19: y'' + y = sec(t), y(0) = 1, y'(0) = 0."""
    req = ProblemRequest(
        raw_input="y'' + y = sec(t), y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    t = sp.Symbol("t")
    assert_cauchy_ivp_solution(
        res,
        t0_val=0,
        expected_y0=1,
        expected_v0=0,
        a_coeff=1,
        b_coeff=0,
        c_coeff=1,
        forcing_expr=sp.sec(t),
        var=t,
    )


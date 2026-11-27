"""Comprehensive regression test suite for Second-Order Euler–Cauchy ODE Solver.

Covers:
- Section 8.A: Sample textbook equation (distinct real roots)
- Section 8.B: Repeated real root
- Section 8.C: Complex-conjugate roots (pure real representation)
- Section 8.D: Negative domain (real power basis -t > 0)
- Section 8.E: Cauchy IVP (positive and negative domain points)
- Section 8.F: Domain and classification failures
- Section 8.G: Regression of existing solvers and end-to-end application routing
- Section 8.H: Natural domain disconnection with independent branch constants
"""

from __future__ import annotations

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.main import build_application
from math_app.solvers.calculus.ode.euler_cauchy_solver import ODEEulerCauchySolver
from math_app.solvers.calculus.ode.reduction_of_order_solver import ODEReductionOfOrderSolver
from math_app.solvers.calculus.ode.second_order_constant_coeff_solver import ODESecondOrderConstantCoeffSolver


@pytest.fixture
def solver() -> ODEEulerCauchySolver:
    return ODEEulerCauchySolver()


# =========================================================================
# Module A — Sample Textbook Equation (Distinct Real Roots)
# =========================================================================


def test_section_8_a_sample_distinct_real_roots(solver: ODEEulerCauchySolver):
    """Test t^2*y'' + 4*t*y' + 2*y = 0, t > 0.

    Expected indicial polynomial: m^2 + 3m + 2 = 0
    Expected roots: m1 = -1, m2 = -2
    Expected solution: y(t) = C1/t + C2/t^2
    """
    req = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Validate symbolic form contains C1/t and C2/t**2
    assert "C1/t" in res.final_result or "t**(-1)" in res.final_result
    assert "C2/t**2" in res.final_result or "t**(-2)" in res.final_result

    # Pedagogical steps validation
    titles = [s.title for s in res.steps]
    assert any("nhận dạng" in t.lower() or "euler" in t.lower() for t in titles)
    assert any("nghiệm thử" in t.lower() or "lũy thừa" in t.lower() for t in titles)
    assert any("phương trình chỉ số" in t.lower() for t in titles)
    assert any("delta" in t.lower() for t in titles)
    assert any("nghiệm cơ bản" in t.lower() for t in titles)
    assert any("nghiệm tổng quát" in t.lower() for t in titles)
    assert any("kiểm chứng" in t.lower() for t in titles)

    # Verify branch solutions
    assert len(res.branch_solutions) == 1
    assert res.branch_solutions[0].domain_interval == (sp.Integer(0), sp.oo)


def test_sample_distinct_real_roots_x_variable(solver: ODEEulerCauchySolver):
    """Test with independent variable 'x': x^2*y'' + 4*x*y' + 2*y = 0, x > 0."""
    req = ProblemRequest(
        raw_input="x^2*y'' + 4*x*y' + 2*y = 0, x > 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="x",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "1/x" in res.final_result or "x**(-1)" in res.final_result


# =========================================================================
# Module B — Repeated Real Characteristic Root
# =========================================================================


def test_section_8_b_repeated_real_root(solver: ODEEulerCauchySolver):
    """Test t^2*y'' - 3*t*y' + 4*y = 0, t > 0.

    Expected indicial polynomial: m(m-1) - 3m + 4 = m^2 - 4m + 4 = (m-2)^2 = 0
    Expected root: m = 2 (multiplicity 2)
    Expected solution: y(t) = t^2*(C1 + C2*ln(t))
    """
    req = ProblemRequest(
        raw_input="t^2*y'' - 3*t*y' + 4*y = 0, t > 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "t**2" in res.final_result
    assert "log(t)" in res.final_result

    # Step descriptions check
    descriptions = [s.description for s in res.steps]
    assert any("kép" in d.lower() or "nghiệm kép" in d.lower() for d in descriptions)


# =========================================================================
# Module C — Complex-Conjugate Characteristic Roots
# =========================================================================


def test_section_8_c_complex_conjugate_roots(solver: ODEEulerCauchySolver):
    """Test t^2*y'' + t*y' + y = 0, t > 0.

    Expected indicial polynomial: m(m-1) + m + 1 = m^2 + 1 = 0
    Expected roots: alpha = 0, beta = 1
    Expected solution: y(t) = C1*cos(ln(t)) + C2*sin(ln(t))
    Must be strictly real-valued (no imaginary unit I in final result).
    """
    req = ProblemRequest(
        raw_input="t^2*y'' + t*y' + y = 0, t > 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "cos(log(t))" in res.final_result
    assert "sin(log(t))" in res.final_result
    assert "I" not in res.final_result  # Strict real-valued check

    descriptions = [s.description for s in res.steps]
    assert any("euler" in d.lower() for d in descriptions)
    assert any("phức" in d.lower() for d in descriptions)


def test_complex_roots_with_nonzero_real_part(solver: ODEEulerCauchySolver):
    """Test t^2*y'' - t*y' + 5*y = 0, t > 0.

    m(m-1) - m + 5 = m^2 - 2m + 5 = 0
    Roots: 1 +- 2i  =>  alpha = 1, beta = 2
    Expected: t*(C1*cos(2*ln(t)) + C2*sin(2*ln(t)))
    """
    req = ProblemRequest(
        raw_input="t^2*y'' - t*y' + 5*y = 0, t > 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "cos(2*log(t))" in res.final_result
    assert "sin(2*log(t))" in res.final_result
    assert "I" not in res.final_result


# =========================================================================
# Module D — Negative Interval Handling
# =========================================================================


def test_section_8_d_negative_interval_sample_equation(solver: ODEEulerCauchySolver):
    """Test sample equation on t < 0: t^2*y'' + 4*t*y' + 2*y = 0, t < 0.

    Output must use mathematically valid representation on negative domain (-t > 0).
    """
    req = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, t < 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 1
    assert res.branch_solutions[0].domain_interval == (-sp.oo, sp.Integer(0))
    assert "-t" in res.final_result or "t" in res.final_result


def test_negative_interval_repeated_root(solver: ODEEulerCauchySolver):
    """Test repeated root on negative interval t < 0: t^2*y'' - 3*t*y' + 4*y = 0, t < 0.

    Must use log(-t) rather than log(t) to avoid complex logarithm on negative numbers.
    """
    req = ProblemRequest(
        raw_input="t^2*y'' - 3*t*y' + 4*y = 0, t < 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "log(-t)" in res.final_result
    assert "I" not in res.final_result


def test_negative_interval_fractional_power_no_complex(solver: ODEEulerCauchySolver):
    """Test 4*t^2*y'' + y = 0, t < 0.

    Indicial: 4m(m-1) + 1 = 4m^2 - 4m + 1 = (2m - 1)^2 = 0 => m = 1/2.
    For t < 0, sqrt(t) would produce imaginary numbers, but sqrt(-t) is purely real.
    """
    req = ProblemRequest(
        raw_input="4*t^2*y'' + y = 0, t < 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "sqrt(-t)" in res.final_result or "(-t)**(1/2)" in res.final_result
    assert "I" not in res.final_result


# =========================================================================
# Module E — Cauchy Initial Value Problems (IVPs)
# =========================================================================


def test_section_8_e_positive_domain_cauchy_ivp(solver: ODEEulerCauchySolver):
    """Test textbook IVP: t^2*y'' + 4*t*y' + 2*y = 0 with y(1) = 3, y'(1) = 0.

    Expected: y(t) = 6/t - 3/t^2
    """
    req = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, y(1) = 3, y'(1) = 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    # Check particular solution values
    t = sp.Symbol("t")
    # Simplify expression
    sol_expr = sp.sympify(res.final_result.split("=")[-1].strip())
    assert sp.simplify(sol_expr - (6 / t - 3 / (t**2))) == 0

    # Verify initial conditions satisfied
    assert sp.simplify(sol_expr.subs(t, 1) - 3) == 0
    assert sp.simplify(sp.diff(sol_expr, t).subs(t, 1) - 0) == 0

    # Check IVP substeps exist
    ivp_steps = [s for s in res.steps if "điều kiện ban đầu" in s.title.lower() or "cauchy" in s.title.lower()]
    assert len(ivp_steps) >= 1
    assert any(len(s.substeps) > 0 for s in ivp_steps)


def test_negative_domain_cauchy_ivp(solver: ODEEulerCauchySolver):
    """Test Cauchy IVP on negative domain: t^2*y'' + 4*t*y' + 2*y = 0, y(-1) = 3, y'(-1) = 0."""
    req = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, y(-1) = 3, y'(-1) = 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    sol_expr = sp.sympify(res.final_result.split("=")[-1].strip())
    # y(-1) = 3, y'(-1) = 0
    assert sp.simplify(sol_expr.subs(t, -1) - 3) == 0
    assert sp.simplify(sp.diff(sol_expr, t).subs(t, -1) - 0) == 0


def test_cauchy_ivp_repeated_root(solver: ODEEulerCauchySolver):
    """Test Cauchy IVP with repeated root: t^2*y'' - 3*t*y' + 4*y = 0, y(1) = 2, y'(1) = 5."""
    req = ProblemRequest(
        raw_input="t^2*y'' - 3*t*y' + 4*y = 0, y(1) = 2, y'(1) = 5",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    sol_expr = sp.sympify(res.final_result.split("=")[-1].strip())
    # Expected: y(t) = t^2 * (2 + log(t))
    assert sp.simplify(sol_expr - (t**2 * (2 + sp.log(t)))) == 0
    assert sp.simplify(sol_expr.subs(t, 1) - 2) == 0
    assert sp.simplify(sp.diff(sol_expr, t).subs(t, 1) - 5) == 0


def test_cauchy_ivp_complex_roots(solver: ODEEulerCauchySolver):
    """Test Cauchy IVP with complex roots: t^2*y'' + t*y' + y = 0, y(1) = 1, y'(1) = 2."""
    req = ProblemRequest(
        raw_input="t^2*y'' + t*y' + y = 0, y(1) = 1, y'(1) = 2",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    sol_expr = sp.sympify(res.final_result.split("=")[-1].strip())
    # Expected: y(t) = cos(log(t)) + 2*sin(log(t))
    assert sp.simplify(sol_expr - (sp.cos(sp.log(t)) + 2 * sp.sin(sp.log(t)))) == 0


# =========================================================================
# Module F — Domain, Singular-Point, and Classification Failures
# =========================================================================


def test_failure_singular_point_initial_condition_at_zero(solver: ODEEulerCauchySolver):
    """Input at t0 = 0 is a singular point; must return CANNOT_SOLVE without claiming nonexistence."""
    req = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, y(0) = 1, y'(0) = 2",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert "singular_point_initial_condition" in res.verification.method
    assert "kỳ dị" in res.verification.details.lower()


def test_failure_interval_crossing_singular_point_zero(solver: ODEEulerCauchySolver):
    """Interval crossing t = 0 (e.g. t >= 0 or t <= 0) must return CANNOT_SOLVE."""
    req = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, t >= 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert "singular_point_interval" in res.verification.method


def test_failure_not_euler_cauchy_equation(solver: ODEEulerCauchySolver):
    """Constant-coefficient equation y'' + 4*y' + 2*y = 0 must be rejected with CANNOT_SOLVE."""
    req = ProblemRequest(
        raw_input="y'' + 4*y' + 2*y = 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert "mismatch" in res.verification.method or "structure" in res.verification.method


def test_failure_nonhomogeneous_euler_cauchy(solver: ODEEulerCauchySolver):
    """Nonhomogeneous Euler-Cauchy t^2*y'' + 4*t*y' + 2*y = t must be rejected with clear notice."""
    req = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = t",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert "nonhomogeneous" in res.verification.method
    assert "thuần nhất" in res.warnings[0].lower()


def test_failure_zero_leading_coefficient(solver: ODEEulerCauchySolver):
    """Zero coefficient on y'' must raise InvalidInputError."""
    req = ProblemRequest(
        raw_input="0*y'' + 4*t*y' + 2*y = 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="cấp 2"):
        solver.solve(req)


def test_failure_missing_one_cauchy_initial_condition(solver: ODEEulerCauchySolver):
    """Missing one Cauchy condition in IVP mode must raise InvalidInputError."""
    req = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, y(1) = 3",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    with pytest.raises(InvalidInputError, match="thiếu điều kiện ban đầu"):
        solver.solve(req)


def test_failure_mismatched_initial_points(solver: ODEEulerCauchySolver):
    """Mismatched base points y(1) = 3, y'(2) = 0 must raise InvalidInputError."""
    req = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, y(1) = 3, y'(2) = 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    with pytest.raises(InvalidInputError, match="không cùng điểm khởi đầu"):
        solver.solve(req)


def test_failure_general_mode_with_initial_conditions(solver: ODEEulerCauchySolver):
    """General mode with initial conditions must report CANNOT_SOLVE due to mode mismatch."""
    req = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, y(1) = 3, y'(1) = 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "GENERAL"},
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert "problem_mode_mismatch" in res.verification.method


def test_failure_initial_point_outside_requested_interval(solver: ODEEulerCauchySolver):
    """Initial condition at t0 = 1 when interval requested is t < 0 must return CANNOT_SOLVE."""
    req = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, y(1) = 3, y'(1) = 0, t < 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert "domain_mismatch" in res.verification.method


# =========================================================================
# Module G — Regression of Existing Solvers and End-to-End Routing
# =========================================================================


def test_constant_coeff_solver_behavior_unchanged():
    """Verify ODESecondOrderConstantCoeffSolver still solves constant-coeff equation."""
    cc_solver = ODESecondOrderConstantCoeffSolver()
    req = ProblemRequest(
        raw_input="y'' + 5*y' + 6*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = cc_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(-2*t)" in res.final_result or "exp(-3*t)" in res.final_result


def test_constant_coeff_solver_rejects_euler_cauchy():
    """Verify ODESecondOrderConstantCoeffSolver cleanly rejects variable coefficients."""
    cc_solver = ODESecondOrderConstantCoeffSolver()
    req = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = cc_solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE


def test_reduction_of_order_solver_behavior_unchanged():
    """Verify ODEReductionOfOrderSolver still solves 2t^2*y'' + 3t*y' - y = 0, y1 = 1/t."""
    roo_solver = ODEReductionOfOrderSolver()
    req = ProblemRequest(
        raw_input="2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    res = roo_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


def test_end_to_end_routing_build_application():
    """Verify complete application use case routes ODE_EULER_CAUCHY end-to-end."""
    app_use_case = build_application()

    # General solution
    req_gen = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
    )
    res_gen = app_use_case.execute(req_gen)
    assert res_gen.status == SolutionStatus.SUCCESS
    assert res_gen.verification.status == VerificationStatus.VERIFIED

    # Cauchy IVP
    req_ivp = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, y(1) = 3, y'(1) = 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    res_ivp = app_use_case.execute(req_ivp)
    assert res_ivp.status == SolutionStatus.SUCCESS
    assert res_ivp.verification.status == VerificationStatus.VERIFIED
    assert "6/t" in res_ivp.final_result or "6*t**(-1)" in res_ivp.final_result


# =========================================================================
# Module H — Natural Domain Disconnection (Two Branch Solutions)
# =========================================================================


def test_natural_domain_two_branches_independent_constants(solver: ODEEulerCauchySolver):
    """When no interval is provided, natural domain R \\ {0} yields two branches:

    Branch 1: (0, oo) with C1, C2
    Branch 2: (-oo, 0) with independent constants C3, C4.
    """
    req = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 2

    # Branch 1: positive
    b_pos = res.branch_solutions[0]
    assert b_pos.domain_interval == (sp.Integer(0), sp.oo)
    assert b_pos.verification is not None
    assert b_pos.verification.status == VerificationStatus.VERIFIED

    # Branch 2: negative
    b_neg = res.branch_solutions[1]
    assert b_neg.domain_interval == (-sp.oo, sp.Integer(0))
    assert b_neg.verification is not None
    assert b_neg.verification.status == VerificationStatus.VERIFIED


# =========================================================================
# Module I — EC1-R1: Interval Validation & Singular Point Safety
# =========================================================================


@pytest.mark.parametrize(
    ("raw_input", "params", "expected_interval", "expected_left_open", "expected_right_open"),
    [
        ("t^2*y'' + 4*t*y' + 2*y = 0, t > 0", {}, (sp.Integer(0), sp.oo), True, True),
        ("t^2*y'' + 4*t*y' + 2*y = 0, t < 0", {}, (-sp.oo, sp.Integer(0)), True, True),
        ("t^2*y'' + 4*t*y' + 2*y = 0, t > 2", {}, (sp.Integer(2), sp.oo), True, True),
        ("t^2*y'' + 4*t*y' + 2*y = 0, t < -1", {}, (-sp.oo, sp.Integer(-1)), True, True),
        ("t^2*y'' + 4*t*y' + 2*y = 0, 1 < t < 5", {}, (sp.Integer(1), sp.Integer(5)), True, True),
        ("t^2*y'' + 4*t*y' + 2*y = 0, -5 < t < -1", {}, (sp.Integer(-5), sp.Integer(-1)), True, True),
        ("t^2*y'' + 4*t*y' + 2*y = 0, t >= 2", {}, (sp.Integer(2), sp.oo), False, True),
        ("t^2*y'' + 4*t*y' + 2*y = 0, t <= -1", {}, (-sp.oo, sp.Integer(-1)), True, False),
        ("t^2*y'' + 4*t*y' + 2*y = 0, t in (2, 5)", {}, (sp.Integer(2), sp.Integer(5)), True, True),
        ("t^2*y'' + 4*t*y' + 2*y = 0", {"interval": "[1, 4]"}, (sp.Integer(1), sp.Integer(4)), False, False),
        ("t^2*y'' + 4*t*y' + 2*y = 0", {"interval": "(-5, -2]"}, (sp.Integer(-5), sp.Integer(-2)), True, False),
    ],
)
def test_explicit_valid_intervals_preserved_exactly(
    solver: ODEEulerCauchySolver,
    raw_input: str,
    params: dict,
    expected_interval: tuple,
    expected_left_open: bool,
    expected_right_open: bool,
):
    """Explicit connected intervals excluding t = 0 must preserve exact bounds and openness."""
    req = ProblemRequest(
        raw_input=raw_input,
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters=params,
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 1
    branch = res.branch_solutions[0]
    assert branch.domain_interval == expected_interval
    assert branch.left_open is expected_left_open
    assert branch.right_open is expected_right_open


@pytest.mark.parametrize(
    ("raw_input", "params"),
    [
        ("t^2*y'' + 4*t*y' + 2*y = 0, -1 < t < 1", {}),
        ("t^2*y'' + 4*t*y' + 2*y = 0, t >= 0", {}),
        ("t^2*y'' + 4*t*y' + 2*y = 0, t <= 0", {}),
        ("t^2*y'' + 4*t*y' + 2*y = 0, 0 <= t < 3", {}),
        ("t^2*y'' + 4*t*y' + 2*y = 0, -3 < t <= 0", {}),
        ("t^2*y'' + 4*t*y' + 2*y = 0, t > -2", {}),
        ("t^2*y'' + 4*t*y' + 2*y = 0, t < 1", {}),
        ("t^2*y'' + 4*t*y' + 2*y = 0", {"interval": "[0, 2]"}),
        ("t^2*y'' + 4*t*y' + 2*y = 0", {"interval": "(-2, 0]"}),
    ],
)
def test_intervals_containing_or_crossing_zero_rejected(
    solver: ODEEulerCauchySolver,
    raw_input: str,
    params: dict,
):
    """Any connected interval containing t = 0 (interior or boundary) must return CANNOT_SOLVE."""
    req = ProblemRequest(
        raw_input=raw_input,
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters=params,
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert res.verification.method == "singular_point_interval"
    assert not res.branch_solutions


@pytest.mark.parametrize(
    ("raw_input", "params"),
    [
        ("t^2*y'' + 4*t*y' + 2*y = 0, t != 0", {}),
        ("t^2*y'' + 4*t*y' + 2*y = 0", {"interval": "t != 0"}),
        ("t^2*y'' + 4*t*y' + 2*y = 0", {"interval": "(-oo, 0) U (0, oo)"}),
        ("t^2*y'' + 4*t*y' + 2*y = 0", {"interval": "positive_or_invalid"}),
        ("t^2*y'' + 4*t*y' + 2*y = 0", {"interval": "z > 2"}),
        ("t^2*y'' + 4*t*y' + 2*y = 0", {"interval": "5 < t < 1"}),
        ("t^2*y'' + 4*t*y' + 2*y = 0", {"interval": "[0, oo]"}),
    ],
)
def test_unsupported_interval_syntax_never_broadens_to_natural_domain(
    solver: ODEEulerCauchySolver,
    raw_input: str,
    params: dict,
):
    """Unrecognized/unsupported interval syntax must return CANNOT_SOLVE without falling back to R \\ {0}."""
    req = ProblemRequest(
        raw_input=raw_input,
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters=params,
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert res.verification.method == "unsupported_interval_syntax"
    assert len(res.branch_solutions) == 0


def test_cauchy_ivp_respects_explicit_shifted_interval(solver: ODEEulerCauchySolver):
    """IVP with t > 2 rejects t0 = 1 (outside interval) and succeeds for t0 = 3 preserving (2, oo)."""
    req_out = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, y(1) = 3, y'(1) = 0, t > 2",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    res_out = solver.solve(req_out)
    assert res_out.status == SolutionStatus.CANNOT_SOLVE
    assert res_out.verification.method == "initial_condition_domain_mismatch"

    req_in = ProblemRequest(
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, y(3) = 1, y'(3) = 0, t > 2",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    res_in = solver.solve(req_in)
    assert res_in.status == SolutionStatus.SUCCESS
    assert res_in.verification.status == VerificationStatus.VERIFIED
    assert res_in.branch_solutions[0].domain_interval == (sp.Integer(2), sp.oo)


# =========================================================================
# Module J — EC1-R1: Preservation of Original Domain Metadata
# =========================================================================


def test_cancelled_denominator_restriction_preserved_across_modes(solver: ODEEulerCauchySolver):
    """((t - 2)/(t - 2))*t^2*y'' + 4*t*y' + 2*y = 0 must preserve t != 2 despite algebraic simplification."""
    eq = "((t - 2)/(t - 2))*t^2*y'' + 4*t*y' + 2*y = 0"

    # 1. Natural domain splits into 3 intervals: (0, 2), (2, oo), (-oo, 0)
    res_nat = solver.solve(ProblemRequest(raw_input=eq, problem_type=ProblemType.ODE_EULER_CAUCHY, target_variable="t"))
    assert res_nat.status == SolutionStatus.SUCCESS
    assert res_nat.verification.status == VerificationStatus.VERIFIED
    assert len(res_nat.branch_solutions) == 3
    intervals = {b.domain_interval for b in res_nat.branch_solutions}
    assert intervals == {(sp.Integer(0), sp.Integer(2)), (sp.Integer(2), sp.oo), (-sp.oo, sp.Integer(0))}
    assert any("t - 2" in r for r in res_nat.domain_restrictions)
    assert "2" in res_nat.original_domain_latex

    # 2. Interval t > 0 violates t != 2
    res_pos = solver.solve(
        ProblemRequest(raw_input=f"{eq}, t > 0", problem_type=ProblemType.ODE_EULER_CAUCHY, target_variable="t")
    )
    assert res_pos.status == SolutionStatus.CANNOT_SOLVE
    assert res_pos.verification.method == "source_domain_interval_violation"

    # 3. Interval t > 3 is valid subset of normalized domain
    res_gt3 = solver.solve(
        ProblemRequest(raw_input=f"{eq}, t > 3", problem_type=ProblemType.ODE_EULER_CAUCHY, target_variable="t")
    )
    assert res_gt3.status == SolutionStatus.SUCCESS
    assert res_gt3.branch_solutions[0].domain_interval == (sp.Integer(3), sp.oo)

    # 4. IVP at t0 = 2 rejected as INVALID_INPUT
    res_ivp_bad = solver.solve(
        ProblemRequest(
            raw_input=f"{eq}, y(2) = 1, y'(2) = 0",
            problem_type=ProblemType.ODE_EULER_CAUCHY,
            target_variable="t",
            parameters={"problem_mode": "CAUCHY_IVP"},
        )
    )
    assert res_ivp_bad.status == SolutionStatus.INVALID_INPUT
    assert res_ivp_bad.verification.status == VerificationStatus.NOT_APPLICABLE

    # 5. IVP at t0 = 1 uses connected component (0, 2)
    res_ivp_ok = solver.solve(
        ProblemRequest(
            raw_input=f"{eq}, y(1) = 3, y'(1) = 0",
            problem_type=ProblemType.ODE_EULER_CAUCHY,
            target_variable="t",
            parameters={"problem_mode": "CAUCHY_IVP"},
        )
    )
    assert res_ivp_ok.status == SolutionStatus.SUCCESS
    assert res_ivp_ok.branch_solutions[0].domain_interval == (sp.Integer(0), sp.Integer(2))


def test_sqrt_squared_preserves_nonnegative_source_domain(solver: ODEEulerCauchySolver):
    """t^2*y'' + 4*sqrt(t)^2*y' + 2*y = 0 simplifies sqrt(t)^2 -> t, but must preserve t >= 0."""
    eq = "t^2*y'' + 4*sqrt(t)^2*y' + 2*y = 0"

    res_nat = solver.solve(ProblemRequest(raw_input=eq, problem_type=ProblemType.ODE_EULER_CAUCHY, target_variable="t"))
    assert res_nat.status == SolutionStatus.SUCCESS
    assert res_nat.original_domain_latex == r"[0, +\infty)"
    assert res_nat.normalized_domain_latex == r"(0, +\infty)"
    assert len(res_nat.branch_solutions) == 1
    assert res_nat.branch_solutions[0].domain_interval == (sp.Integer(0), sp.oo)
    assert any(">= 0" in r for r in res_nat.domain_restrictions)

    res_neg = solver.solve(
        ProblemRequest(raw_input=f"{eq}, t < 0", problem_type=ProblemType.ODE_EULER_CAUCHY, target_variable="t")
    )
    assert res_neg.status == SolutionStatus.CANNOT_SOLVE
    assert res_neg.verification.method == "source_domain_interval_violation"

    res_ivp_neg = solver.solve(
        ProblemRequest(
            raw_input=f"{eq}, y(-1) = 3, y'(-1) = 0",
            problem_type=ProblemType.ODE_EULER_CAUCHY,
            target_variable="t",
            parameters={"problem_mode": "CAUCHY_IVP"},
        )
    )
    assert res_ivp_neg.status == SolutionStatus.INVALID_INPUT


def test_canceled_logarithm_preserves_positive_source_domain(solver: ODEEulerCauchySolver):
    """(log(t) - log(t) + t^2)*y'' + 4*t*y' + 2*y = 0 must preserve t > 0."""
    eq = "(log(t) - log(t) + t^2)*y'' + 4*t*y' + 2*y = 0"

    res_neg = solver.solve(
        ProblemRequest(raw_input=f"{eq}, t < 0", problem_type=ProblemType.ODE_EULER_CAUCHY, target_variable="t")
    )
    assert res_neg.status == SolutionStatus.CANNOT_SOLVE
    assert res_neg.verification.method == "source_domain_interval_violation"

    res_ivp_neg = solver.solve(
        ProblemRequest(
            raw_input=f"{eq}, y(-1) = 3, y'(-1) = 0",
            problem_type=ProblemType.ODE_EULER_CAUCHY,
            target_variable="t",
            parameters={"problem_mode": "CAUCHY_IVP"},
        )
    )
    assert res_ivp_neg.status == SolutionStatus.INVALID_INPUT


# =========================================================================
# Module K — EC1-R1: Conservative Classification & Cauchy Input Hardening
# =========================================================================


def test_conservative_rejection_of_unresolved_coefficients_and_complex(solver: ODEEulerCauchySolver):
    """Free parameters, complex coefficients, and unverified is_real=None coefficients are conservatively rejected."""
    res_param = solver.solve(
        ProblemRequest(
            raw_input="k*t^2*y'' + 4*t*y' + 2*y = 0",
            problem_type=ProblemType.ODE_EULER_CAUCHY,
            target_variable="t",
        )
    )
    assert res_param.status == SolutionStatus.CANNOT_SOLVE
    assert res_param.verification.method == "euler_cauchy_unresolved_parameter"

    res_complex = solver.solve(
        ProblemRequest(
            raw_input="sqrt(-1)*t^2*y'' + 4*t*y' + 2*y = 0",
            problem_type=ProblemType.ODE_EULER_CAUCHY,
            target_variable="t",
        )
    )
    assert res_complex.status == SolutionStatus.CANNOT_SOLVE
    assert res_complex.verification.method == "euler_cauchy_complex_coefficient"


def test_unverified_is_real_none_coefficient_and_unresolved_discriminant(
    solver: ODEEulerCauchySolver,
    monkeypatch: pytest.MonkeyPatch,
):
    """Never treat is_real is None as real, and never approximate unresolved discriminant."""
    from math_app.input.ode_parser import parse_second_order_ode_input

    real_parsed = parse_second_order_ode_input("t^2*y'' + 4*t*y' + 2*y = 0", target_variable="t")
    opaque_coeff = sp.Function("opaque_c")()
    patched_parsed = type(real_parsed)(
        **{
            **real_parsed.__dict__,
            "c_coeff": opaque_coeff,
        }
    )
    monkeypatch.setattr(
        "math_app.solvers.calculus.ode.euler_cauchy_solver.parse_second_order_ode_input",
        lambda *args, **kwargs: patched_parsed,
    )
    res_opaque = solver.solve(
        ProblemRequest(
            raw_input="t^2*y'' + 4*t*y' + 2*y = 0",
            problem_type=ProblemType.ODE_EULER_CAUCHY,
            target_variable="t",
        )
    )
    assert res_opaque.status == SolutionStatus.CANNOT_SOLVE
    assert res_opaque.verification.status == VerificationStatus.UNVERIFIED
    assert res_opaque.verification.method == "euler_cauchy_unverified_coefficient"

    orig_simplify = sp.simplify
    fake_delta = sp.Symbol("delta_unresolved", real=True, finite=True)
    assert fake_delta.is_positive is None
    assert fake_delta.is_zero is None
    assert fake_delta.is_negative is None

    parsed_distinct = parse_second_order_ode_input("t^2*y'' + 5*t*y' + 2*y = 0", target_variable="t")
    monkeypatch.setattr(
        "math_app.solvers.calculus.ode.euler_cauchy_solver.parse_second_order_ode_input",
        lambda *args, **kwargs: parsed_distinct,
    )
    monkeypatch.setattr(
        "math_app.solvers.calculus.ode.euler_cauchy_solver.sp.simplify",
        lambda expr, *a, **kw: fake_delta if expr == sp.Integer(8) else orig_simplify(expr, *a, **kw),
    )
    res_delta = solver.solve(
        ProblemRequest(
            raw_input="t^2*y'' + 5*t*y' + 2*y = 0",
            problem_type=ProblemType.ODE_EULER_CAUCHY,
            target_variable="t",
        )
    )
    assert res_delta.status == SolutionStatus.CANNOT_SOLVE
    assert res_delta.verification.status == VerificationStatus.UNVERIFIED
    assert res_delta.verification.method == "indicial_discriminant_unresolved"


@pytest.mark.parametrize(
    "raw_input",
    [
        "t^2*y'' + 4*t*y' + 2*y = 0, y(a) = 3, y'(a) = 0",
        "t^2*y'' + 4*t*y' + 2*y = 0, y(1) = k, y'(1) = 0",
        "t^2*y'' + 4*t*y' + 2*y = 0, y(1) = 3, y'(1) = b",
    ],
)
def test_unresolved_symbolic_cauchy_inputs_fail_closed_without_typeerror(
    solver: ODEEulerCauchySolver,
    raw_input: str,
):
    """Symbolic t0, y0, or v0 must fail closed as UNVERIFIED without raising TypeError."""
    req = ProblemRequest(
        raw_input=raw_input,
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.UNVERIFIED
    assert res.verification.status == VerificationStatus.UNVERIFIED


@pytest.mark.parametrize(
    "raw_input",
    [
        "t^2*y'' + 4*t*y' + 2*y = 0, y(I) = 1, y'(I) = 0",
        "t^2*y'' + 4*t*y' + 2*y = 0, y(1) = acos(2), y'(1) = 0",
        "t^2*y'' + 4*t*y' + 2*y = 0, y(1) = 1, y'(1) = I",
    ],
)
def test_nonreal_cauchy_inputs_raise_invalid_input_error(
    solver: ODEEulerCauchySolver,
    raw_input: str,
):
    """Non-real t0, y0, or v0 must raise InvalidInputError."""
    req = ProblemRequest(
        raw_input=raw_input,
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    with pytest.raises(InvalidInputError):
        solver.solve(req)


# =========================================================================
# Module L — EC1-R1: Fundamental System Wronskian Verification Gate
# =========================================================================


@pytest.mark.parametrize(
    ("raw_eq", "interval"),
    [
        ("t^2*y'' + 4*t*y' + 2*y = 0", "t > 0"),
        ("t^2*y'' + 4*t*y' + 2*y = 0", "t < 0"),
        ("t^2*y'' - 3*t*y' + 4*y = 0", "t > 2"),
        ("t^2*y'' - 3*t*y' + 4*y = 0", "t < -1"),
        ("t^2*y'' + t*y' + y = 0", "t > 0"),
        ("t^2*y'' + t*y' + y = 0", "t < 0"),
    ],
)
def test_all_three_root_cases_pass_fundamental_system_wronskian_gate(
    solver: ODEEulerCauchySolver,
    raw_eq: str,
    interval: str,
):
    """All three characteristic-root cases on positive & negative intervals must verify W != 0."""
    res = solver.solve(
        ProblemRequest(
            raw_input=f"{raw_eq}, {interval}",
            problem_type=ProblemType.ODE_EULER_CAUCHY,
            target_variable="t",
        )
    )
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "W(y1, y2)" in res.verification.details


def test_ode_verifier_fundamental_system_gate_direct():
    """Verify ODEVerifier.verify_fundamental_system catches dependent, vanishing, and parametric pairs."""
    from math_app.verification.calculus.ode_verifier import ODEVerifier

    verifier = ODEVerifier()
    t = sp.Symbol("t")
    k = sp.Symbol("k")

    # 1. All 3 root cases on positive and negative intervals
    for iv in ((sp.Integer(0), sp.oo), (-sp.oo, sp.Integer(0))):
        base = -t if iv[1] == 0 else t
        for y1, y2 in (
            (base ** (-1), base ** (-2)),
            (base**2, base**2 * sp.log(base)),
            (base * sp.cos(2 * sp.log(base)), base * sp.sin(2 * sp.log(base))),
        ):
            w_expr, w_res = verifier.verify_fundamental_system(y1, y2, t, domain_interval=iv)
            assert w_res.status == VerificationStatus.VERIFIED, f"Failed for {y1}, {y2} on {iv}: {w_res}"
            assert w_expr != 0

    # 2. Linearly dependent functions -> FAILED
    w_zero, res_dep = verifier.verify_fundamental_system(t, 2 * t, t, domain_interval=(sp.Integer(0), sp.oo))
    assert w_zero == 0
    assert res_dep.status == VerificationStatus.FAILED

    # 3. Wronskian vanishing inside interval (-1, 2): W(t, t^2) = t^2 vanishes at t = 0
    _, res_vanish = verifier.verify_fundamental_system(
        t, t**2, t, domain_interval=(sp.Integer(-1), sp.Integer(2))
    )
    assert res_vanish.status == VerificationStatus.FAILED

    # 4. Unresolved parametric pair -> UNVERIFIED
    _, res_param = verifier.verify_fundamental_system(t, k * t**2, t, domain_interval=(sp.Integer(1), sp.oo))
    assert res_param.status == VerificationStatus.UNVERIFIED


def test_solver_returns_unverified_when_fundamental_system_gate_unverified(
    solver: ODEEulerCauchySolver,
    monkeypatch: pytest.MonkeyPatch,
):
    """If Wronskian independence gate returns UNVERIFIED, solver must return UNVERIFIED."""
    from math_app.application.dtos import VerificationResult

    monkeypatch.setattr(
        solver.verifier,
        "verify_fundamental_system",
        lambda *args, **kwargs: (
            sp.Symbol("W_unknown"),
            VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="fundamental_system_wronskian_unverified",
                details="Mocked Wronskian independence inconclusive.",
            ),
        ),
    )

    res = solver.solve(
        ProblemRequest(
            raw_input="t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
            problem_type=ProblemType.ODE_EULER_CAUCHY,
            target_variable="t",
        )
    )
    assert res.status == SolutionStatus.UNVERIFIED
    assert res.verification.status == VerificationStatus.UNVERIFIED


# =========================================================================
# Module M — EC1-R1: Mocked Verifier Status Propagation to Steps & UI Flow
# =========================================================================


@pytest.mark.parametrize(
    ("mock_status", "expected_sol_status", "expected_completed", "expected_badge_color"),
    [
        (VerificationStatus.VERIFIED, SolutionStatus.SUCCESS, True, "emerald-7"),
        (VerificationStatus.UNVERIFIED, SolutionStatus.UNVERIFIED, False, "amber-7"),
        (VerificationStatus.FAILED, SolutionStatus.DISCREPANCY_DETECTED, False, "rose-7"),
    ],
)
def test_mocked_verifier_status_propagates_to_steps_and_pedagogical_flow(
    solver: ODEEulerCauchySolver,
    monkeypatch: pytest.MonkeyPatch,
    mock_status: VerificationStatus,
    expected_sol_status: SolutionStatus,
    expected_completed: bool,
    expected_badge_color: str,
):
    """Solver steps and pedagogical Stage 4 must faithfully reflect VERIFIED / UNVERIFIED / FAILED."""
    from math_app.application.dtos import VerificationResult
    from math_app.presentation.components.ode_pedagogical_enhancer import enhance_ode_solution_flow

    monkeypatch.setattr(
        solver.verifier,
        "verify_second_order",
        lambda *args, **kwargs: VerificationResult(
            status=mock_status,
            method=f"mocked_{mock_status.value}",
            details=f"Mocked verification outcome: {mock_status.value}.",
        ),
    )

    res = solver.solve(
        ProblemRequest(
            raw_input="t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
            problem_type=ProblemType.ODE_EULER_CAUCHY,
            target_variable="t",
        )
    )
    assert res.status == expected_sol_status
    assert res.verification.status == mock_status

    final_step = res.steps[-1]
    if mock_status == VerificationStatus.VERIFIED:
        assert "VERIFIED" in final_step.content.latex_after
        assert r"\equiv 0" in final_step.content.latex_after
    else:
        assert "VERIFIED)" not in final_step.content.latex_after
        assert r"\equiv 0" not in final_step.content.latex_after
        assert "R(t) = 0" not in final_step.content.expression_after
        assert mock_status.value.upper() in final_step.content.latex_after
        assert all(r"\equiv 0" not in sub.content.latex_after for sub in final_step.substeps)

    stages = enhance_ode_solution_flow(res, ProblemType.ODE_EULER_CAUCHY, "t")
    assert len(stages) == 4
    stg4 = stages[3]
    assert stg4.is_completed is expected_completed
    assert stg4.badge_color == expected_badge_color
    if mock_status == VerificationStatus.VERIFIED:
        assert r"\equiv 0" in stg4.summary_latex
        assert "VERIFIED" in stg4.steps[-1].intermediate_result
    else:
        assert r"\equiv 0" not in stg4.summary_latex
        assert mock_status.value.upper() in stg4.summary_latex
        assert mock_status.value.upper() in stg4.steps[-1].intermediate_result

"""Unit tests for Second-Order Nonhomogeneous ODEs via the Method of Variation of Parameters (Lagrange).

Covers:
- Mandatory Reference Problems (REF-1 to REF-7):
  - REF-1: Tangent forcing (y'' + y = tan(t))
  - REF-2: Logarithmic forcing (y'' + y = ln(t))
  - REF-3: Rational forcing (y'' + y = 1/t)
  - REF-4: Radical forcing (y'' + y = sqrt(t))
  - REF-5: Exponential non-elementary candidate (y'' + y = exp(t^2))
  - REF-6: Damped equation with complex roots (y'' + 2y' + 2y = ln(t))
  - REF-7: Fallback preservation (UC preserved, unsupported falls back, parameter failures not masked)
- Secant, Cosecant, Cotangent forcing cases
- Repeated characteristic roots (y'' - 2y' + y = exp(t)/t)
- Distinct real roots with logistic/rational-exponential forcing (y'' - y = 1/(exp(t) + 1))
- Non-unity leading coefficient a != 1 (2*y'' + 2*y = 2*tan(t))
- Sign invariance under swapped LHS/RHS (tan(t) = y'' + y vs y'' + y - tan(t) = 0)
- Target variable variation (x instead of t)
- Nonhomogeneous IVP safety gate (deferred to M3) for both full and partial initial conditions
- Exact vs. unevaluated integral representations
- Domain restrictions and singularity tracking (ln(t) -> t > 0, 1/t -> t != 0)
- Independent mathematical verification guarantees: R(t) = a*y'' + b*y' + c*y - g(t) == 0
"""

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.second_order_constant_coeff_solver import ODESecondOrderConstantCoeffSolver
from math_app.solvers.calculus.ode.variation_of_parameters import (
    extract_domain_restrictions_from_expr,
    solve_variation_of_parameters,
)
from math_app.verification.calculus.ode_verifier import ODEVerifier


@pytest.fixture
def solver() -> ODESecondOrderConstantCoeffSolver:
    return ODESecondOrderConstantCoeffSolver(verifier=ODEVerifier())


def _verify_residual(
    sol_expr: sp.Expr,
    a_val: float | int,
    b_val: float | int,
    c_val: float | int,
    g_val: sp.Expr,
    var: sp.Symbol,
) -> bool:
    """Helper to independently evaluate residual R(t) = a*y'' + b*y' + c*y - g(t)."""
    dy = sp.diff(sol_expr, var)
    d2y = sp.diff(dy, var)
    lhs = a_val * d2y + b_val * dy + c_val * sol_expr
    residual = sp.simplify(lhs - g_val)
    if residual != 0:
        residual = sp.simplify(sp.trigsimp(sp.expand(residual)))
    if residual != 0 and hasattr(residual, "doit"):
        residual = sp.simplify(residual.doit())
    return bool(residual == 0)


# =============================================================================
# 1. Low-level Variation of Parameters Module Unit Tests
# =============================================================================


def test_vop_direct_tangent():
    t = sp.Symbol("t")
    y1 = sp.cos(t)
    y2 = sp.sin(t)
    g = sp.tan(t)
    res = solve_variation_of_parameters(sp.Integer(1), sp.Integer(0), sp.Integer(1), g, y1, y2, t)
    assert res.is_supported is True
    assert res.is_integral_form is False
    assert res.wronskian == 1
    assert _verify_residual(res.particular_solution, 1, 0, 1, g, t)


def test_vop_linearly_dependent_fundamental_solutions_rejected():
    t = sp.Symbol("t")
    y1 = sp.exp(t)
    y2 = 2 * sp.exp(t)  # Linearly dependent!
    g = sp.tan(t)
    res = solve_variation_of_parameters(sp.Integer(1), sp.Integer(0), sp.Integer(1), g, y1, y2, t)
    assert res.is_supported is False
    assert "wronskian" in res.unsupported_reason.lower()


def test_domain_restriction_detection():
    t = sp.Symbol("t")
    restrs1 = extract_domain_restrictions_from_expr(sp.log(t), t)
    assert "t > 0" in restrs1

    restrs2 = extract_domain_restrictions_from_expr(1 / t, t)
    assert "t != 0" in restrs2

    restrs3 = extract_domain_restrictions_from_expr(sp.tan(t), t)
    assert any("pi/2" in r for r in restrs3)


# =============================================================================
# 2. Mandatory Reference Problems (REF-1 to REF-7)
# =============================================================================


def test_ref1_tangent_forcing(solver: ODESecondOrderConstantCoeffSolver):
    """REF-1: y'' + y = tan(t) -> W = 1, solved via Variation of Parameters."""
    t = sp.Symbol("t")
    req = ProblemRequest(
        raw_input="y'' + y = tan(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    rule_names = [s.rule_name for s in res.steps]
    assert "Phương pháp Biến thiên hằng số" in rule_names
    assert "Định thức Wronskian" in rule_names
    assert "Đạo hàm hàm biến thiên" in rule_names
    assert "Tích phân hàm biến thiên" in rule_names
    assert "Kiểm chứng nghiệm" in rule_names

    # Independent residual verification
    res_sol = sp.sympify(res.final_result.split("=", 1)[1].strip())
    residual = sp.simplify(sp.diff(res_sol, t, 2) + res_sol - sp.tan(t))
    assert residual == 0


def test_ref2_logarithmic_forcing(solver: ODESecondOrderConstantCoeffSolver):
    """REF-2: y'' + y = ln(t), t > 0 -> exact closed form with Ci(t) and Si(t)."""
    t = sp.Symbol("t")
    req = ProblemRequest(
        raw_input="y'' + y = ln(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert any("t > 0" in r for r in res.domain_restrictions)

    # 1. Verify mathematical structure of steps
    step_dict = {s.rule_name: s for s in res.steps}
    assert "Đạo hàm hàm biến thiên" in step_dict
    assert "Tích phân hàm biến thiên" in step_dict
    assert "Nghiệm riêng biến thiên hằng số" in step_dict
    assert "Tổng hợp nghiệm tổng quát" in step_dict

    # 2. Assert auxiliary derivatives: u1' = -sin(t)*ln(t), u2' = cos(t)*ln(t)
    deriv_step = step_dict["Đạo hàm hàm biến thiên"]
    assert "u1' = -log(t)*sin(t)" in deriv_step.content.expression_after
    assert "u2' = log(t)*cos(t)" in deriv_step.content.expression_after

    # 3. Assert antiderivatives: u1 = cos(t)*ln(t) - Ci(t), u2 = sin(t)*ln(t) - Si(t)
    int_step = step_dict["Tích phân hàm biến thiên"]
    assert "u1 = log(t)*cos(t) - Ci(t)" in int_step.content.expression_after
    assert "u2 = log(t)*sin(t) - Si(t)" in int_step.content.expression_after

    # Differentiate antiderivatives independently to verify they reproduce integrands
    u1_computed = sp.cos(t) * sp.log(t) - sp.Ci(t)
    u2_computed = sp.sin(t) * sp.log(t) - sp.Si(t)
    assert sp.simplify(sp.diff(u1_computed, t) - (-sp.sin(t) * sp.log(t))) == 0
    assert sp.simplify(sp.diff(u2_computed, t) - (sp.cos(t) * sp.log(t))) == 0

    # 4. Assert particular solution: Yp(t) = ln(t) - cos(t)*Ci(t) - sin(t)*Si(t)
    yp_step = step_dict["Nghiệm riêng biến thiên hằng số"]
    assert "log(t)" in yp_step.content.expression_after
    assert "Ci(t)" in yp_step.content.expression_after
    assert "Si(t)" in yp_step.content.expression_after

    yp_expected = sp.log(t) - sp.cos(t) * sp.Ci(t) - sp.sin(t) * sp.Si(t)
    yp_from_u = sp.simplify(u1_computed * sp.cos(t) + u2_computed * sp.sin(t))
    assert sp.simplify(yp_from_u - yp_expected) == 0

    # Assert particular-solution residual is identically zero: Yp'' + Yp - ln(t) == 0
    d_yp = sp.diff(yp_expected, t)
    d2_yp = sp.diff(d_yp, t)
    residual_yp = sp.simplify(d2_yp + yp_expected - sp.log(t))
    assert residual_yp == 0

    # 5. Assert complete general solution: y = C1*cos(t) + C2*sin(t) + Yp
    c1 = sp.Symbol("C1")
    c2 = sp.Symbol("C2")
    y_expected = c1 * sp.cos(t) + c2 * sp.sin(t) + yp_expected
    res_sol_expr = sp.sympify(res.final_result.split("=", 1)[1].strip())
    assert sp.simplify(res_sol_expr - y_expected) == 0

    # Complete ODE residual check
    d_y = sp.diff(y_expected, t)
    d2_y = sp.diff(d_y, t)
    res_ode = sp.simplify(d2_y + y_expected - sp.log(t))
    assert res_ode == 0

    # 6. Prove that the erroneous expression from the report draft fails verification
    yp_erroneous = sp.cos(t) * sp.Ci(t) - sp.sin(t) * sp.Si(t)
    d2_err = sp.diff(yp_erroneous, t, 2)
    res_err = sp.simplify(d2_err + yp_erroneous - sp.log(t))
    assert res_err != 0
    assert sp.simplify(res_err - (-sp.log(t) - 3 * sp.sin(2 * t) / t - sp.cos(2 * t) / t**2)) == 0


def test_ref3_rational_forcing(solver: ODESecondOrderConstantCoeffSolver):
    """REF-3: y'' + y = 1/t -> W = 1, u1' = -sin(t)/t, u2' = cos(t)/t."""
    t = sp.Symbol("t")
    req = ProblemRequest(
        raw_input="y'' + y = 1/t",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert any("t != 0" in r or "t khác 0" in r for r in res.domain_restrictions)

    # Independent residual verification: y'' + y - 1/t == 0
    res_sol = sp.sympify(res.final_result.split("=", 1)[1].strip())
    residual = sp.simplify(sp.diff(res_sol, t, 2) + res_sol - 1 / t)
    assert residual == 0

    # Verify antiderivative consistency: d/dt Si(t) = sin(t)/t, d/dt Ci(t) = cos(t)/t
    assert sp.simplify(sp.diff(-sp.Si(t), t) - (-sp.sin(t) / t)) == 0
    assert sp.simplify(sp.diff(sp.Ci(t), t) - (sp.cos(t) / t)) == 0


def test_ref4_radical_forcing(solver: ODESecondOrderConstantCoeffSolver):
    """REF-4: y'' + y = sqrt(t), t >= 0."""
    req = ProblemRequest(
        raw_input="y'' + y = sqrt(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert any("t >= 0" in r for r in res.domain_restrictions)


def test_ref5_exponential_non_elementary_candidate(solver: ODESecondOrderConstantCoeffSolver):
    """REF-5: y'' + y = exp(t^2) -> exact unevaluated integral representation."""
    req = ProblemRequest(
        raw_input="y'' + y = exp(t^2)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert any("tích phân chính xác" in w.lower() for w in res.warnings)


def test_ref6_damped_equation_with_logarithmic_forcing(solver: ODESecondOrderConstantCoeffSolver):
    """REF-6: y'' + 2y' + 2y = ln(t) -> complex roots r = -1 +- i, W = exp(-2t)."""
    req = ProblemRequest(
        raw_input="y'' + 2*y' + 2*y = ln(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


def test_ref7_fallback_preservation_undetermined_coefficients_retained(solver: ODESecondOrderConstantCoeffSolver):
    """REF-7A: Equation solvable by Undetermined Coefficients continues to use UC without invoking VoP."""
    req = ProblemRequest(
        raw_input="y'' - 3*y' - 4*y = 3*exp(2*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    rule_names = [s.rule_name for s in res.steps]
    # Should use Undetermined Coefficients rule names, not VoP
    assert "Dạng nghiệm riêng đề xuất" in rule_names
    assert "Phương pháp Biến thiên hằng số" not in rule_names


def test_ref7_fallback_preservation_polynomial_retained(solver: ODESecondOrderConstantCoeffSolver):
    """REF-7B: Polynomial forcing equation continues to use UC."""
    req = ProblemRequest(
        raw_input="y'' + 4*y = 8",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    rule_names = [s.rule_name for s in res.steps]
    assert "Dạng nghiệm riêng đề xuất" in rule_names
    assert "Phương pháp Biến thiên hằng số" not in rule_names


def test_ref7_fallback_preservation_parameter_failure_not_masked(solver: ODESecondOrderConstantCoeffSolver):
    """REF-7C: Symbolic parameter failure in UC is not masked by silently routing to VoP."""
    req = ProblemRequest(
        raw_input="y'' - y = exp(k*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert any("tham số" in w.lower() or "cộng hưởng" in w.lower() for w in res.warnings)


# =============================================================================
# 3. Trigonometric and Special Function Forcing
# =============================================================================


def test_secant_forcing(solver: ODESecondOrderConstantCoeffSolver):
    """y'' + 4*y = sec(2t) -> exact closed form Yp = t*sin(2t)/2 + cos(2t)*ln(cos(2t))/4."""
    req = ProblemRequest(
        raw_input="y'' + 4*y = sec(2*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = t * sp.sin(2 * t) / 2 + sp.cos(2 * t) * sp.log(sp.cos(2 * t)) / 4
    assert _verify_residual(yp, 1, 0, 4, sp.sec(2 * t), t)


def test_secant_forcing_frequency_one(solver: ODESecondOrderConstantCoeffSolver):
    """y'' + y = sec(t) -> exact closed form Yp = t*sin(t) + cos(t)*ln(cos(t))."""
    req = ProblemRequest(
        raw_input="y'' + y = sec(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


def test_cotangent_forcing(solver: ODESecondOrderConstantCoeffSolver):
    """y'' + y = cot(t)."""
    req = ProblemRequest(
        raw_input="y'' + y = cot(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


def test_cosecant_forcing(solver: ODESecondOrderConstantCoeffSolver):
    """y'' + y = csc(t)."""
    req = ProblemRequest(
        raw_input="y'' + y = csc(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


# =============================================================================
# 4. Repeated and Distinct Roots Equations
# =============================================================================


def test_repeated_root_with_rational_exponential(solver: ODESecondOrderConstantCoeffSolver):
    """y'' - 2y' + y = exp(t)/t, t > 0.

    Roots: r = 1 (repeated), y1 = exp(t), y2 = t*exp(t), W = exp(2t).
    u1' = -1 -> u1 = -t.
    u2' = 1/t -> u2 = ln(t).
    Yp = -t*exp(t) + t*exp(t)*ln(t).
    """
    req = ProblemRequest(
        raw_input="y'' - 2*y' + y = exp(t)/t",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = -t * sp.exp(t) + t * sp.exp(t) * sp.log(t)
    assert _verify_residual(yp, 1, -2, 1, sp.exp(t) / t, t)


def test_distinct_real_roots_with_logistic_forcing(solver: ODESecondOrderConstantCoeffSolver):
    """y'' - y = 1/(exp(t) + 1). Distinct real roots r = 1, -1."""
    req = ProblemRequest(
        raw_input="y'' - y = 1/(exp(t) + 1)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


# =============================================================================
# 5. Non-Unity Leading Coefficient a != 1
# =============================================================================


def test_non_unity_leading_coefficient(solver: ODESecondOrderConstantCoeffSolver):
    """2*y'' + 2*y = 2*tan(t) -> a = 2, g(t) = 2*tan(t), f(t) = tan(t)."""
    req = ProblemRequest(
        raw_input="2*y'' + 2*y = 2*tan(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


def test_negative_leading_coefficient(solver: ODESecondOrderConstantCoeffSolver):
    """-y'' - y = -tan(t) -> equivalent to y'' + y = tan(t)."""
    req = ProblemRequest(
        raw_input="-y'' - y = -tan(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


# =============================================================================
# 6. Sign Invariance Under Swapped Sides
# =============================================================================


def test_sign_invariance_swapped_sides_tan(solver: ODESecondOrderConstantCoeffSolver):
    """Verify tan(t) = y'' + y produces verified solution mathematically equivalent to y'' + y = tan(t)."""
    req_std = ProblemRequest(raw_input="y'' + y = tan(t)", problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, target_variable="t")
    req_swapped = ProblemRequest(raw_input="tan(t) = y'' + y", problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, target_variable="t")
    req_zero = ProblemRequest(raw_input="y'' + y - tan(t) = 0", problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, target_variable="t")

    res_std = solver.solve(req_std)
    res_swapped = solver.solve(req_swapped)
    res_zero = solver.solve(req_zero)

    assert res_std.status == SolutionStatus.SUCCESS
    assert res_swapped.status == SolutionStatus.SUCCESS
    assert res_zero.status == SolutionStatus.SUCCESS
    assert res_std.verification.status == VerificationStatus.VERIFIED
    assert res_swapped.verification.status == VerificationStatus.VERIFIED
    assert res_zero.verification.status == VerificationStatus.VERIFIED


# =============================================================================
# 7. Target Variable Variation
# =============================================================================


def test_target_variable_x_with_variation_of_parameters(solver: ODESecondOrderConstantCoeffSolver):
    """Verify that solver correctly respects target variable 'x' instead of default 't'."""
    req = ProblemRequest(
        raw_input="y'' + y = tan(x)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="x",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "x" in res.final_result
    assert "t" not in res.final_result


# =============================================================================
# 8. Defensive Gating: Nonhomogeneous IVP Deferred to M3
# =============================================================================


def test_vop_nonhomogeneous_ivp_solved_in_m3(solver: ODESecondOrderConstantCoeffSolver):
    """Full Cauchy IVP for nonhomogeneous equation with tan(t) is solved and verified in M3."""
    req = ProblemRequest(
        raw_input="y'' + y = tan(t), y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


def test_vop_nonhomogeneous_partial_ivp_rejected(solver: ODESecondOrderConstantCoeffSolver):
    """Partial IVP for nonhomogeneous equation with tan(t) raises InvalidInputError."""
    req = ProblemRequest(
        raw_input="y'' + y = tan(t), y(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="không hoàn chỉnh"):
        solver.solve(req)


# =============================================================================
# 9. Pedagogical Derivation Structure for Variation of Parameters
# =============================================================================


def test_pedagogical_derivation_steps_for_vop(solver: ODESecondOrderConstantCoeffSolver):
    """Verify that the generated SolutionStep sequence for VoP contains all required steps."""
    req = ProblemRequest(
        raw_input="y'' + y = tan(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS

    # Check strictly monotonic step numbers
    step_nums = [s.step_number for s in res.steps]
    assert step_nums == list(range(1, len(res.steps) + 1))

    # Check rule names exist
    rule_names = [s.rule_name for s in res.steps]
    assert "Phương trình đặc trưng" in rule_names
    assert "Nghiệm phức liên hợp" in rule_names
    assert "Hệ nghiệm cơ bản" in rule_names
    assert "Phương pháp Biến thiên hằng số" in rule_names
    assert "Định thức Wronskian" in rule_names
    assert "Dạng nghiệm riêng Lagrange" in rule_names
    assert "Hệ phương trình phụ trợ Lagrange" in rule_names
    assert "Đạo hàm hàm biến thiên" in rule_names
    assert "Tích phân hàm biến thiên" in rule_names
    assert "Nghiệm riêng biến thiên hằng số" in rule_names
    assert "Tổng hợp nghiệm tổng quát" in rule_names
    assert "Kiểm chứng nghiệm" in rule_names

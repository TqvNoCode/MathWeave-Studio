"""Comprehensive mathematical regression tests for ODE Reliability Remediation Round 4.

Focus: Homogeneous First-Order & Second-Order ODEs, Picard-Lindelöf Uniqueness,
Domain-Aware Initial Point Validation, Periodic Equilibria Families, and Solver Architecture.
"""

from __future__ import annotations

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.exact_solver import ODEExactSolver
from math_app.solvers.calculus.ode.linear_solver import ODELinearSolver
from math_app.solvers.calculus.ode.reduction_of_order_solver import ODEReductionOfOrderSolver
from math_app.solvers.calculus.ode.second_order_constant_coeff_solver import (
    ODESecondOrderConstantCoeffSolver,
)
from math_app.solvers.calculus.ode.separable_solver import ODESeparableSolver
from math_app.solvers.calculus.ode.wronskian_solver import WronskianSolver
from math_app.verification.calculus.ode_verifier import ODEVerifier


@pytest.fixture
def sep_solver() -> ODESeparableSolver:
    return ODESeparableSolver()


@pytest.fixture
def linear_solver() -> ODELinearSolver:
    return ODELinearSolver()


@pytest.fixture
def exact_solver() -> ODEExactSolver:
    return ODEExactSolver()


@pytest.fixture
def second_order_solver() -> ODESecondOrderConstantCoeffSolver:
    return ODESecondOrderConstantCoeffSolver()


@pytest.fixture
def reduction_solver() -> ODEReductionOfOrderSolver:
    return ODEReductionOfOrderSolver()


@pytest.fixture
def wronskian_solver() -> WronskianSolver:
    return WronskianSolver()


@pytest.fixture
def verifier() -> ODEVerifier:
    return ODEVerifier()


# =============================================================================
# Group 1: Picard-Lindelöf Uniqueness & Lipschitz Violations
# =============================================================================

def test_r4_01_sqrt_y_ivp_lipschitz_violation(sep_solver: ODESeparableSolver):
    """y' = sqrt(y), y(0) = 0: Lipschitz condition violated at y=0.

    Must NOT claim Picard-Lindelöf uniqueness; must warn about non-uniqueness.
    """
    req = ProblemRequest(
        raw_input="y' = sqrt(y), y(0) = 0",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.verification.method == "equilibrium_ivp_nonunique"
    assert any("Lipschitz" in w or "KHÔNG DUY NHẤT" in w for w in res.warnings)
    assert "Picard" not in res.verification.method


def test_r4_02_y_cube_ivp_picard_lindelof_unique(sep_solver: ODESeparableSolver):
    """y' = y^3, y(0) = 0: dg/dy = 3y^2 is bounded at y=0.

    Must cite Picard-Lindelöf unique equilibrium.
    """
    req = ProblemRequest(
        raw_input="y' = y^3, y(0) = 0",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.verification.method == "equilibrium_ivp_picard_lindelof_unique"
    assert "Picard–Lindelöf" in res.verification.details or "Picard-Lindelöf" in res.verification.details


def test_r4_03_logistic_ivp_picard_lindelof_unique(sep_solver: ODESeparableSolver):
    """y' = y*(1 - y), y(0) = 0: dg/dy = 1 - 2y is smooth at y=0.

    Must cite Picard-Lindelöf unique equilibrium.
    """
    req = ProblemRequest(
        raw_input="y' = y*(1 - y), y(0) = 0",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.verification.method == "equilibrium_ivp_picard_lindelof_unique"


# =============================================================================
# Group 2: Invalid Initial Point Rejections
# =============================================================================

def test_r4_04_reciprocal_y_zero_ivp_rejected(sep_solver: ODESeparableSolver):
    """y' = 1/y, y(0) = 0: undefined at initial point.

    Must return INVALID_INPUT and NOT_APPLICABLE, never VERIFIED.
    """
    req = ProblemRequest(
        raw_input="y' = 1/y, y(0) = 0",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.INVALID_INPUT
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert res.verification.method == "initial_point_domain_validation"


def test_r4_05_linear_singular_ivp_rejected(linear_solver: ODELinearSolver):
    """x*y' + 2*y = 0, y(0) = 1: p(x) = 2/x has singularity at x=0.

    Must return INVALID_INPUT and NOT_APPLICABLE.
    """
    req = ProblemRequest(
        raw_input="x*y' + 2*y = 0, y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.INVALID_INPUT
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert res.verification.method == "initial_point_domain_validation"


def test_r4_06_exact_singular_ivp_rejected(exact_solver: ODEExactSolver):
    """Exact ODE where (x0, y0) is outside the domain of M or N (division by zero)."""
    req = ProblemRequest(
        raw_input="(1/x + y) dx + (x + 1/y) dy = 0, y(0) = 1",
        problem_type=ProblemType.ODE_EXACT,
        target_variable="x",
    )
    res = exact_solver.solve(req)

    assert res.status == SolutionStatus.INVALID_INPUT
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert res.verification.method == "initial_point_domain_validation"


# =============================================================================
# Group 3: Complete Periodic Equilibrium Families
# =============================================================================

def test_r4_07_sin_y_periodic_family(sep_solver: ODESeparableSolver):
    """y' = sin(y): general solution contains periodic family y = n*pi."""
    req = ProblemRequest(
        raw_input="y' = sin(y)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "n*pi" in res.final_result


def test_r4_08_sin_2y_periodic_family(sep_solver: ODESeparableSolver):
    """y' = sin(2*y): periodic family y = n*pi/2."""
    req = ProblemRequest(
        raw_input="y' = sin(2*y)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "n*pi / 2" in res.final_result or "n*pi/2" in res.final_result


def test_r4_09_sin_neg3y_periodic_family(sep_solver: ODESeparableSolver):
    """y' = sin(-3*y): periodic family uses absolute value |a| = 3: y = n*pi/3."""
    req = ProblemRequest(
        raw_input="y' = sin(-3*y)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "n*pi / 3" in res.final_result or "n*pi/3" in res.final_result


def test_r4_10_cos_y_periodic_family(sep_solver: ODESeparableSolver):
    """y' = cos(y): periodic family y = pi/2 + n*pi."""
    req = ProblemRequest(
        raw_input="y' = cos(y)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "pi/2 + n*pi" in res.final_result or "pi / 2 + n*pi" in res.final_result


def test_r4_11_cos_2y_periodic_family(sep_solver: ODESeparableSolver):
    """y' = cos(2*y): periodic family y = (2*n + 1)*pi/4."""
    req = ProblemRequest(
        raw_input="y' = cos(2*y)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "(2*n + 1)*pi / 4" in res.final_result or "pi / 4" in res.final_result


def test_r4_12_cos_neg3y_periodic_family(sep_solver: ODESeparableSolver):
    """y' = cos(-3*y): periodic family uses absolute value 2*|a| = 6: y = (2*n + 1)*pi/6."""
    req = ProblemRequest(
        raw_input="y' = cos(-3*y)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "(2*n + 1)*pi / 6" in res.final_result or "pi / 6" in res.final_result


# =============================================================================
# Group 4: First-Order Homogeneous Linear & Exact Solvers
# =============================================================================

def test_r4_13_linear_homogeneous_general(linear_solver: ODELinearSolver):
    """y' + 2*y = 0: general solution y(x) = C*exp(-2*x)."""
    req = ProblemRequest(
        raw_input="y' + 2*y = 0",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(-2*x)" in res.final_result or "exp(-2*t)" in res.final_result


def test_r4_14_linear_homogeneous_ivp(linear_solver: ODELinearSolver):
    """y' + 2*y = 0, y(0) = 5: particular solution y(x) = 5*exp(-2*x)."""
    req = ProblemRequest(
        raw_input="y' + 2*y = 0, y(0) = 5",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "5*exp(-2*x)" in res.final_result


def test_r4_15_exact_homogeneous(exact_solver: ODEExactSolver):
    """(2*x + y) dx + (x + 2*y) dy = 0: exact equation."""
    req = ProblemRequest(
        raw_input="(2*x + y) dx + (x + 2*y) dy = 0",
        problem_type=ProblemType.ODE_EXACT,
        target_variable="x",
    )
    res = exact_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "x**2 + x*y + y**2 = C" in res.final_result or "x**2 + y*x + y**2 = C" in res.final_result


def test_r4_16_non_exact_rejected(exact_solver: ODEExactSolver):
    """(2*x + y) dx + (2*x + 2*y) dy = 0: dM/dy = 1 != dN/dx = 2."""
    req = ProblemRequest(
        raw_input="(2*x + y) dx + (2*x + 2*y) dy = 0",
        problem_type=ProblemType.ODE_EXACT,
        target_variable="x",
    )
    res = exact_solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert res.verification.method == "exactness_condition_failed"


# =============================================================================
# Group 5: Second-Order Constant Coefficients Homogeneous
# =============================================================================

def test_r4_17_second_order_distinct_real_roots(second_order_solver: ODESecondOrderConstantCoeffSolver):
    """y'' - 5*y' + 6*y = 0: distinct real roots r1=2, r2=3."""
    req = ProblemRequest(
        raw_input="y'' - 5*y' + 6*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = second_order_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(2*t)" in res.final_result and "exp(3*t)" in res.final_result


def test_r4_18_second_order_repeated_root(second_order_solver: ODESecondOrderConstantCoeffSolver):
    """y'' - 4*y' + 4*y = 0: repeated real root r=2."""
    req = ProblemRequest(
        raw_input="y'' - 4*y' + 4*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = second_order_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(2*t)" in res.final_result


def test_r4_19_second_order_complex_roots(second_order_solver: ODESecondOrderConstantCoeffSolver):
    """y'' + 4*y = 0: purely imaginary roots r = +/- 2i."""
    req = ProblemRequest(
        raw_input="y'' + 4*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = second_order_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "cos(2*t)" in res.final_result and "sin(2*t)" in res.final_result


def test_r4_20_second_order_cauchy_ivp(second_order_solver: ODESecondOrderConstantCoeffSolver):
    """y'' + 4*y = 0, y(0) = 1, y'(0) = 2: unique Cauchy solution y(t) = cos(2*t) + sin(2*t)."""
    req = ProblemRequest(
        raw_input="y'' + 4*y = 0, y(0) = 1, y'(0) = 2",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = second_order_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "sin(2*t + pi/4)" in res.final_result or "cos(2*t) + sin(2*t)" in res.final_result or "sin(2*t) + cos(2*t)" in res.final_result


def test_r4_21_second_order_incomplete_ivp_rejected(second_order_solver: ODESecondOrderConstantCoeffSolver):
    """Second-order ODE with only y(0)=1 (missing y'(0)) must be rejected."""
    req = ProblemRequest(
        raw_input="y'' + 4*y = 0, y(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="không hoàn chỉnh"):
        second_order_solver.solve(req)


def test_r4_22_second_order_mismatched_base_points_rejected(second_order_solver: ODESecondOrderConstantCoeffSolver):
    """y(0) = 1, y'(1) = 2: mismatched base points t0 != t1 must be rejected."""
    req = ProblemRequest(
        raw_input="y'' + 4*y = 0, y(0) = 1, y'(1) = 2",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="cùng một điểm"):
        second_order_solver.solve(req)


def test_r4_23_second_order_non_real_ivp_rejected(second_order_solver: ODESecondOrderConstantCoeffSolver):
    """Non-real or infinite initial value must be rejected."""
    req = ProblemRequest(
        raw_input="y'' + 4*y = 0, y(0) = zoo, y'(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="Ký hiệu không xác định|số thực hữu hạn"):
        second_order_solver.solve(req)


# =============================================================================
# Group 6: Reduction of Order & Wronskian
# =============================================================================

def test_r4_24_reduction_of_order_valid_y1(reduction_solver: ODEReductionOfOrderSolver):
    """t^2*y'' - 2*t*y' + 2*y = 0, y1 = t: y2 = t^2, W(t, t^2) = t^2 != 0."""
    req = ProblemRequest(
        raw_input="t^2*y'' - 2*t*y' + 2*y = 0, y1 = t",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    res = reduction_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "t**2" in res.final_result or "t^2" in res.final_latex


def test_r4_25_reduction_of_order_invalid_y1_rejected(reduction_solver: ODEReductionOfOrderSolver):
    """Supplied y1 = t^3 does not satisfy the ODE; must be rejected with InvalidInputError."""
    req = ProblemRequest(
        raw_input="t^2*y'' - 2*t*y' + 2*y = 0, y1 = t^3",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="không thỏa mãn phương trình vi phân"):
        reduction_solver.solve(req)


def test_r4_26_reduction_of_order_incomplete_ivp_rejected(reduction_solver: ODEReductionOfOrderSolver):
    """Incomplete IVP (only y(1)=1 provided) must be rejected with InvalidInputError."""
    req = ProblemRequest(
        raw_input="t^2*y'' - 2*t*y' + 2*y = 0, y1 = t, y(1) = 1",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="không hoàn chỉnh"):
        reduction_solver.solve(req)


def test_r4_27_reduction_of_order_singular_base_point_rejected(reduction_solver: ODEReductionOfOrderSolver):
    """Base point t0 = 0 is singular (a(0)=0 and y1(0)=0); must be rejected."""
    req = ProblemRequest(
        raw_input="t^2*y'' - 2*t*y' + 2*y = 0, y1 = t, y(0) = 0, y'(0) = 1",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="điểm kỳ dị"):
        reduction_solver.solve(req)


def test_r4_28_wronskian_linearly_independent(wronskian_solver: WronskianSolver):
    """y1 = cos(t), y2 = sin(t): W = 1 != 0, linearly independent."""
    req = ProblemRequest(
        raw_input="W(cos(t), sin(t))",
        problem_type=ProblemType.WRONSKIAN,
        target_variable="t",
    )
    res = wronskian_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "W(y1, y2)(t) = 1" in res.final_result


def test_r4_29_wronskian_peano_inconclusive(wronskian_solver: WronskianSolver):
    """Arbitrary functions with W == 0 (e.g. t^2 and 2*t^2) must be inconclusive without ODE context."""
    req = ProblemRequest(
        raw_input="W(t^2, 2*t^2)",
        problem_type=ProblemType.WRONSKIAN,
        target_variable="t",
    )
    res = wronskian_solver.solve(req)

    assert res.status == SolutionStatus.UNVERIFIED
    assert res.verification.status == VerificationStatus.UNVERIFIED
    assert res.verification.method == "wronskian_zero_inconclusive_arbitrary_functions"


def test_r4_30_wronskian_abel_ode_solutions(verifier: ODEVerifier):
    """Solutions of a common linear 2nd-order ODE with continuous coefficients satisfy Abel's theorem."""
    t = sp.Symbol("t", real=True)
    y1 = sp.exp(t)
    y2 = 2 * sp.exp(t)
    # Both satisfy y'' - y' = 0 (a=1, b=-1, c=0)
    w_expr, verif = verifier.verify_wronskian(y1, y2, t, ode_coeffs=(sp.Integer(1), sp.Integer(-1), sp.Integer(0)))

    assert w_expr == 0
    assert verif.status == VerificationStatus.VERIFIED
    assert verif.method == "wronskian_zero_ode_solutions_dependent_verified"


# =============================================================================
# Group 7: Classical Degree-0 Homogeneous Recognition
# =============================================================================

def test_r4_31_classical_homogeneous_recognition(sep_solver: ODESeparableSolver):
    """y' = (y + x)/x: classical homogeneous y' = F(y/x).

    Must return CANNOT_SOLVE with warning noting that homogeneous substitution
    y = vx is an unsupported method in this milestone.
    """
    req = ProblemRequest(
        raw_input="y' = (y + x)/x",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert any("thuần nhất bậc 0" in w for w in res.warnings)

"""UX3.7.3.4.3 — Comprehensive Adversarial Verification Suite.

Validates:
1. P0 — Elimination of arbitrary integration constant assignment (Tests A through H).
2. P1 — Degenerate singular Cauchy ODE classification and smooth extension.
3. Higher-order zeros of leading coefficients.
4. Original equation residual verification.
5. Domain completeness propagation.
"""

from __future__ import annotations

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.linear_solver import ODELinearSolver
from math_app.verification.calculus.ode_verifier import (
    ODEVerifier,
    verify_singular_extension,
)


class MockBranch:
    """Mock branch solution container for isolated singular extension tests."""

    def __init__(
        self,
        expr: sp.Expr,
        integration_constant: sp.Symbol | None = None,
        domain_interval: tuple[sp.Expr, sp.Expr] | None = None,
        branch_identity: str = "MockBranch",
    ):
        self.expression = expr
        self.integration_constant = integration_constant
        self.domain_interval = domain_interval
        self.branch_identity = branch_identity
        self.extension_status = None
        self.extension_details = None
        self.initial_condition_status = None
        self.real_root_restrictions = ()
        self.denominator_exclusions = ()
        self.domain_restrictions = ()
        self.left_open = True
        self.right_open = True
        self.domain_set = None
        self.singular_exclusions = ()
        self.solution_str = str(expr)
        self.solution_latex = f"y(t) = {expr}"
        self.interval_notation_latex = "I"


@pytest.fixture
def linear_solver() -> ODELinearSolver:
    return ODELinearSolver()


@pytest.fixture
def ode_verifier() -> ODEVerifier:
    return ODEVerifier()


# =========================================================================
# Section 2: P0 Mandatory Tests A through H (Integration Constant Integrity)
# =========================================================================

def test_p0_case_a_unprescribed_derivative_requires_conditional_c1():
    """Case A: y_- = C1*t + t^2, y_+ = t^2, y(0)=0.

    Continuity holds for all C1.
    y'_-(0) = C1, y'_+(0) = 0.
    C1 extension requires C1 = 0.
    Must return CONDITIONAL_EXTENSION (never unrestricted C1_EXTENSION_VERIFIED).
    """
    t = sp.Symbol("t", real=True)
    C1 = sp.Symbol("C1", real=True)
    b_left = MockBranch(C1 * t + t**2, integration_constant=C1)
    b_right = MockBranch(t**2)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=sp.Integer(0),
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "C1 = 0" in details
    assert status != VerificationStatus.C1_EXTENSION_VERIFIED


def test_p0_case_b_prescribed_derivative_zero_selects_constant():
    """Case B: Same example with deriv_at_point=0.

    Both value y(0)=0 and derivative y'(0)=0 are prescribed by IVP.
    Solves C1=0 and confirms C1_EXTENSION_VERIFIED under selected C1=0.
    """
    t = sp.Symbol("t", real=True)
    C1 = sp.Symbol("C1", real=True)
    b_left = MockBranch(C1 * t + t**2, integration_constant=C1)
    b_right = MockBranch(t**2)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=sp.Integer(0),
        deriv_at_point=sp.Integer(0),
        variable=t,
    )

    assert status == VerificationStatus.C1_EXTENSION_VERIFIED
    assert "C1 = 0" in details


def test_p0_case_c_prescribed_derivative_mismatch():
    """Case C: Same example with deriv_at_point=1.

    y'_+(0) = 0 != 1. Right branch cannot satisfy required derivative 1.
    Must return CONTINUITY_VERIFIED, never C1_EXTENSION_VERIFIED.
    """
    t = sp.Symbol("t", real=True)
    C1 = sp.Symbol("C1", real=True)
    b_left = MockBranch(C1 * t + t**2, integration_constant=C1)
    b_right = MockBranch(t**2)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=sp.Integer(0),
        deriv_at_point=sp.Integer(1),
        variable=t,
    )

    assert status == VerificationStatus.CONTINUITY_VERIFIED
    assert status != VerificationStatus.C1_EXTENSION_VERIFIED


def test_p0_case_d_two_free_constants_different_constraints():
    """Case D: y_- = C1 + C2*t + t^2, y_+ = t + t^2, y(0)=0.

    Continuity at 0: C1 = 0.
    Differentiability at 0: y'_-(0) = C2, y'_+(0) = 1 => C2 = 1.
    Must solve both constraints {C1=0, C2=1} and return CONDITIONAL_EXTENSION.
    """
    t = sp.Symbol("t", real=True)
    C1, C2 = sp.symbols("C1 C2", real=True)
    b_left = MockBranch(C1 + C2 * t + t**2, integration_constant=C1)
    b_right = MockBranch(t + t**2)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=sp.Integer(0),
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "C1 = 0" in details
    assert "C2 = 1" in details


def test_p0_case_e_constant_absent_from_value_present_in_derivative():
    """Case E: Constant absent from value limit but present in derivative limit.

    y_- = C1*t + t^3, y_+ = 2*t + t^3, y(0)=0.
    lim y_- = 0, lim y_+ = 0 (C1 absent).
    lim y'_- = C1, lim y'_+ = 2 (C1 present).
    Requires C1 = 2 for C1 extension.
    """
    t = sp.Symbol("t", real=True)
    C1 = sp.Symbol("C1", real=True)
    b_left = MockBranch(C1 * t + t**3, integration_constant=C1)
    b_right = MockBranch(2 * t + t**3)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=sp.Integer(0),
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "C1 = 2" in details


def test_p0_case_f_multiple_real_solutions():
    """Case F: Multiple real solutions for integration constant.

    y_- = C1^2*t + t^2, y_+ = 4*t + t^2, y(0)=0.
    lim y'_- = C1^2, lim y'_+ = 4 => C1 = +-2.
    Both real roots must be preserved.
    """
    t = sp.Symbol("t", real=True)
    C1 = sp.Symbol("C1", real=True)
    b_left = MockBranch(C1**2 * t + t**2, integration_constant=C1)
    b_right = MockBranch(4 * t + t**2)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=sp.Integer(0),
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "-2" in details and "2" in details


def test_p0_case_g_no_real_solution_for_derivative():
    """Case G: No real solution for derivative compatibility.

    y_- = C1^2*t + t^2, y_+ = -1*t + t^2, y(0)=0.
    lim y'_- = C1^2, lim y'_+ = -1 => C1^2 = -1 (no real solution).
    Must return CONTINUITY_VERIFIED, never C1_EXTENSION_VERIFIED.
    """
    t = sp.Symbol("t", real=True)
    C1 = sp.Symbol("C1", real=True)
    b_left = MockBranch(C1**2 * t + t**2, integration_constant=C1)
    b_right = MockBranch(-1 * t + t**2)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=sp.Integer(0),
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONTINUITY_VERIFIED
    assert status != VerificationStatus.C1_EXTENSION_VERIFIED


def test_p0_case_h_symbolically_unresolved_derivative():
    """Case H: Symbolically unresolved derivative compatibility.

    If limit evaluation encounters unevaluated integrals or limits,
    must return UNVERIFIED (or CONTINUITY_VERIFIED), never C1_EXTENSION_VERIFIED.
    """
    t = sp.Symbol("t", real=True)
    s = sp.Symbol("s", real=True)
    uneval_int = sp.Integral(sp.exp(-s**2), (s, 0, t))
    b_left = MockBranch(uneval_int)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=sp.Integer(0),
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.UNVERIFIED
    assert status != VerificationStatus.C1_EXTENSION_VERIFIED


# =========================================================================
# Section 3: P1 Mandatory Regression Cases (Degenerate Singular Cauchy)
# =========================================================================

def test_p1_degenerate_t_yp_plus_t_y_eq_t_with_ic_5(linear_solver: ODELinearSolver):
    """Mandatory counterexample: t*y' + t*y = t, y(0) = 5.

    Normalized equation: y' + y = 1 => y(t) = 1 + C*exp(-t).
    y(0) = 5 => 1 + C = 5 => C = 4 => y(t) = 1 + 4*exp(-t).
    y'(0) = -4.
    Original ODE residual: t*(-4*exp(-t)) + t*(1 + 4*exp(-t)) = t == t (identically 0).
    Expected: SUCCESS, C1_EXTENSION_VERIFIED.
    """
    req = ProblemRequest(
        raw_input="t*y' + t*y = t, y(0) = 5",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "1 + 4*exp(-t)" in res.final_result or "4*exp(-t) + 1" in res.final_result
    assert res.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED

    # Independent residual verification against unnormalized ODE
    t = sp.Symbol("t", real=True)
    sol = 1 + 4 * sp.exp(-t)
    residual = sp.simplify(t * sp.diff(sol, t) + t * sol - t)
    assert residual == 0


def test_p1_degenerate_t_yp_plus_2t_y_eq_2t_with_ic_3(linear_solver: ODELinearSolver):
    """Mandatory case: t*y' + 2*t*y = 2*t, y(0) = 3.

    Normalized equation: y' + 2*y = 2 => y(t) = 1 + C*exp(-2*t).
    y(0) = 3 => 1 + C = 3 => C = 2 => y(t) = 1 + 2*exp(-2*t).
    Expected: SUCCESS, C1_EXTENSION_VERIFIED.
    """
    req = ProblemRequest(
        raw_input="t*y' + 2*t*y = 2*t, y(0) = 3",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "1 + 2*exp(-2*t)" in res.final_result or "2*exp(-2*t) + 1" in res.final_result
    assert res.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED

    # Independent residual verification
    t = sp.Symbol("t", real=True)
    sol = 1 + 2 * sp.exp(-2 * t)
    residual = sp.simplify(t * sp.diff(sol, t) + 2 * t * sol - 2 * t)
    assert residual == 0


def test_p1_degenerate_t_yp_eq_t_with_ic_5(linear_solver: ODELinearSolver):
    """Mandatory case: t*y' = t, y(0) = 5.

    Normalized equation: y' = 1 => y(t) = t + 5.
    Expected: SUCCESS, C1_EXTENSION_VERIFIED.
    """
    req = ProblemRequest(
        raw_input="t*y' = t, y(0) = 5",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "t + 5" in res.final_result
    assert res.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED


def test_p1_degenerate_t_yp_eq_0_with_ic_7(linear_solver: ODELinearSolver):
    """Mandatory case: t*y' = 0, y(0) = 7.

    Normalized equation: y' = 0 => y(t) = 7.
    Expected: SUCCESS, C1_EXTENSION_VERIFIED.
    """
    req = ProblemRequest(
        raw_input="t*y' = 0, y(0) = 7",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "7" in res.final_result
    assert res.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED


def test_p1_degenerate_t2_yp_eq_t2_with_ic_5(linear_solver: ODELinearSolver):
    """Mandatory case: Higher-order zero t^2*y' = t^2, y(0) = 5.

    A(t) = t^2 has a second-order zero at t=0.
    Normalized equation: y' = 1 => y(t) = t + 5.
    Expected: SUCCESS, C1_EXTENSION_VERIFIED.
    """
    req = ProblemRequest(
        raw_input="t^2*y' = t^2, y(0) = 5",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "t + 5" in res.final_result
    assert res.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED


def test_p1_contradiction_t_yp_eq_1_with_ic_5(linear_solver: ODELinearSolver):
    """Mandatory case: t*y' = 1, y(0) = 5.

    At t=0: 0*y'(0) = 1 => 0 = 1 (contradiction).
    Expected: INVALID_INPUT.
    """
    req = ProblemRequest(
        raw_input="t*y' = 1, y(0) = 5",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.INVALID_INPUT
    assert "0 = 1" in res.verification.details or "mâu thuẫn" in res.verification.details.lower()


def test_p1_contradiction_t_yp_plus_y_eq_0_with_ic_1(linear_solver: ODELinearSolver):
    """Mandatory case: t*y' + y = 0, y(0) = 1.

    At t=0: 0*y'(0) + 1*y(0) = 0 => y(0) = 0.
    Given y(0) = 1 != 0 => algebraic contradiction.
    Expected: INVALID_INPUT.
    """
    req = ProblemRequest(
        raw_input="t*y' + y = 0, y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.INVALID_INPUT
    assert "mâu thuẫn" in res.verification.details.lower() or "0" in res.verification.details


def test_p1_singular_benchmark_incompatible(linear_solver: ODELinearSolver):
    """Mandatory case: Singular Cauchy IVP with no classical extension.

    (t-3)*y' + ln(t)*y = 2*t, y(3) = 1.
    Required y(3) = 6/ln(3) != 1.
    Expected: INVALID_INPUT.
    """
    req = ProblemRequest(
        raw_input="(t-3)*y' + ln(t)*y = 2*t, y(3) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.INVALID_INPUT


def test_p1_singular_benchmark_compatible_non_unique(linear_solver: ODELinearSolver):
    """Mandatory case: Singular Cauchy IVP with non-unique extensions.

    (t-3)*y' + ln(t)*y = 2*t, y(3) = 6/ln(3).
    Compatible algebraic condition, but unverified globally / conditional extension.
    Expected: Not ordinary SUCCESS without proof, status UNVERIFIED or CONDITIONAL_EXTENSION.
    """
    req = ProblemRequest(
        raw_input="(t-3)*y' + ln(t)*y = 2*t, y(3) = 6/ln(3)",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = linear_solver.solve(req)

    assert res.verification.status in (
        VerificationStatus.UNVERIFIED,
        VerificationStatus.CONDITIONAL_EXTENSION,
        VerificationStatus.PARTIALLY_VERIFIED,
    )
    assert res.verification.status != VerificationStatus.VERIFIED


# =========================================================================
# Section 6: Additional Adversarial Mathematical Tests
# =========================================================================

def test_adversarial_cubic_leading_coeff_zero(linear_solver: ODELinearSolver):
    """Higher-order zero: t^3*y' = t^3, y(0) = 2.

    Normalized equation: y' = 1 => y(t) = t + 2.
    Expected: SUCCESS, C1_EXTENSION_VERIFIED.
    """
    req = ProblemRequest(
        raw_input="t^3*y' = t^3, y(0) = 2",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "t + 2" in res.final_result
    assert res.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED


def test_adversarial_constant_free_smooth_match():
    """Constant-free branches that smoothly match across singular point.

    y_- = t^2, y_+ = t^2 at ts = 0, y(0) = 0.
    lim y_- = 0, lim y_+ = 0.
    lim y'_- = 0, lim y'_+ = 0.
    Must return C1_EXTENSION_VERIFIED.
    """
    t = sp.Symbol("t", real=True)
    b_left = MockBranch(t**2)
    b_right = MockBranch(t**2)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=sp.Integer(0),
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.C1_EXTENSION_VERIFIED


# =========================================================================
# Section 7: UX3.7.3.4.4 Mandatory Targeted Regression Tests
# =========================================================================

# -------------------------------------------------------------------------
# Defect 1: P0 — Elimination of Arbitrary Integration Constant Assignment
# -------------------------------------------------------------------------

def test_ux3_7_3_4_4_defect1_case_a_c_minus_2_over_t():
    """Case A: y_-(t) = (C - 2)/t + t, y_+(t) = t.

    Pole cancellation requires C = 2.
    Under C = 2, extension is continuous and C1 differentiable (lim y' = 1).
    Expected constraint: C = 2.
    Must return CONDITIONAL_EXTENSION preserving C = 2 without arbitrary assignment.
    """
    t = sp.Symbol("t", real=True)
    C = sp.Symbol("C", real=True)
    b_left = MockBranch((C - 2) / t + t, integration_constant=C)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "C = 2" in details
    assert "C = 0" not in details


def test_ux3_7_3_4_4_defect1_case_b_c_squared_minus_1_over_t():
    """Case B: y_-(t) = (C^2 - 1)/t + t, y_+(t) = t.

    Pole cancellation requires C^2 - 1 = 0 => C in {-1, 1}.
    Both real solutions must be preserved in details without arbitrary zero assignment.
    """
    t = sp.Symbol("t", real=True)
    C = sp.Symbol("C", real=True)
    b_left = MockBranch((C**2 - 1) / t + t, integration_constant=C)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "-1" in details and "1" in details


def test_ux3_7_3_4_4_defect1_case_c_c_over_t():
    """Case C: y_-(t) = C/t + t, y_+(t) = t.

    Pole cancellation requires C = 0.
    Expected constraint: C = 0.
    Must be derived mathematically from Laurent pole cancellation, not guessed.
    """
    t = sp.Symbol("t", real=True)
    C = sp.Symbol("C", real=True)
    b_left = MockBranch(C / t + t, integration_constant=C)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "C = 0" in details


def test_ux3_7_3_4_4_defect1_case_d_no_real_solution_pole():
    """Case D: y_-(t) = (C^2 + 1)/t + t, y_+(t) = t.

    C^2 + 1 = 0 has no real solution.
    Expected: report FAILED only when symbolic incompatibility is established.
    """
    t = sp.Symbol("t", real=True)
    C = sp.Symbol("C", real=True)
    b_left = MockBranch((C**2 + 1) / t + t, integration_constant=C)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.FAILED
    assert "không tồn tại giá trị thực" in details.lower() or "vô nghiệm thực" in details.lower() or "không hữu hạn" in details.lower()


def test_ux3_7_3_4_4_defect1_case_e_unresolved_symbolic_limit():
    """Case E: An unresolved symbolic limit.

    Expected: remain UNVERIFIED. Never guess.
    """
    t = sp.Symbol("t", real=True)
    f = sp.Function("f")
    b_left = MockBranch(f(t) / t + t)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.UNVERIFIED
    assert "chưa thể tính" in details.lower() or "không thể tính" in details.lower()


# -------------------------------------------------------------------------
# Defect 2: P0 — Fix Degenerate Homogeneous Cauchy Classification
# -------------------------------------------------------------------------

def test_ux3_7_3_4_4_defect2_mandatory_counterexample(linear_solver: ODELinearSolver):
    """Mandatory counterexample: x*y' + 2*x*y = 0, y(0) = 1.

    Correct solution: y(x) = exp(-2*x).
    Leading coefficient vanishes at x=0, but equation is homogeneous with removable singularity.
    Expected behavior:
    - Solver must NOT automatically return INVALID_INPUT.
    - Check the original unnormalized differential equation.
    - Verify the initial condition y(0) = 1.
    - Verify solution is continuously differentiable through x=0.
    - Verify original equation residual is identically zero.
    """
    req = ProblemRequest(
        raw_input="x*y' + 2*x*y = 0, y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "exp(-2*x)" in res.final_result or "e^{- 2 x}" in res.final_latex
    assert res.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED

    # 1. Verify original unnormalized differential equation residual identically zero
    x = sp.Symbol("x", real=True)
    sol = sp.exp(-2 * x)
    orig_residual = sp.simplify(x * sp.diff(sol, x) + 2 * x * sol - 0)
    assert orig_residual == 0

    # 2. Verify initial condition
    assert sol.subs(x, 0) == 1

    # 3. Verify continuous differentiability through x=0
    d_sol = sp.diff(sol, x)
    lim_left = sp.limit(d_sol, x, 0, dir="-")
    lim_right = sp.limit(d_sol, x, 0, dir="+")
    assert lim_left == -2
    assert lim_right == -2
    assert lim_left == lim_right


def test_ux3_7_3_4_4_defect2_incompatible_x_yp_eq_1(linear_solver: ODELinearSolver):
    """Genuinely incompatible case: x*y' = 1, y(0) = 5.

    At x=0: 0*y'(0) = 1 => 0 = 1 (algebraic contradiction).
    Must preserve rejection with INVALID_INPUT.
    """
    req = ProblemRequest(
        raw_input="x*y' = 1, y(0) = 5",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.INVALID_INPUT
    assert "0 = 1" in res.verification.details or "mâu thuẫn" in res.verification.details.lower()


def test_ux3_7_3_4_4_defect2_incompatible_x_yp_plus_y_eq_0(linear_solver: ODELinearSolver):
    """Genuinely incompatible case: x*y' + y = 0, y(0) = 1.

    At x=0: 0*y'(0) + 1*y(0) = 0 => y(0) = 0.
    Given y(0) = 1 != 0 => algebraic contradiction.
    Must preserve rejection with INVALID_INPUT.
    """
    req = ProblemRequest(
        raw_input="x*y' + y = 0, y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.INVALID_INPUT
    assert "mâu thuẫn" in res.verification.details.lower() or "0" in res.verification.details


# =========================================================================
# Section 5: UX3.7.3.4.5 — Final Mathematical Verification Soundness Tests
# =========================================================================

# -------------------------------------------------------------------------
# P0-A: Correct Singular Cauchy Limit Classification
# -------------------------------------------------------------------------

def test_ux3_7_3_4_5_p0_a_case_a_removable_singularity_c1_extension(linear_solver: ODELinearSolver):
    """P0-A Case A: Valid removable singularity x*y' + 2*x*y = 0, y(0) = 1.

    Expected:
    - SUCCESS
    - y(x) = exp(-2*x)
    - C1 extension verified.
    """
    req = ProblemRequest(
        raw_input="x*y' + 2*x*y = 0, y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "exp(-2*x)" in res.final_result or "e^{- 2 x}" in res.final_latex
    assert res.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED


def test_ux3_7_3_4_5_p0_a_case_b_unequal_onesided_normalized_coefficients(linear_solver: ODELinearSolver):
    """P0-A Case B: Unequal one-sided normalized coefficients: x*y' + abs(x)*y = 0, y(0) = 1.

    p(x) = abs(x)/x:
      lim_{x -> 0^-} p(x) = -1
      lim_{x -> 0^+} p(x) = 1
    Unequal one-sided limits => derivative cannot match => no C1 extension possible.
    Expected:
    - Must NOT claim C1 extension.
    - Must correctly detect derivative incompatibility or return UNVERIFIED.
    """
    req = ProblemRequest(
        raw_input="x*y' + abs(x)*y = 0, y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.UNVERIFIED
    assert res.verification.status == VerificationStatus.UNVERIFIED
    assert res.verification.status != VerificationStatus.C1_EXTENSION_VERIFIED
    assert "không trùng khớp" in res.verification.details or "không khớp" in res.verification.details or "lim p" in res.verification.details


def test_ux3_7_3_4_5_p0_a_case_c_oscillatory_normalized_coefficient(linear_solver: ODELinearSolver):
    """P0-A Case C: Oscillatory normalized coefficient: x*y' + x*sin(1/x)*y = 0, y(0) = 1.

    p(x) = x*sin(1/x)/x = sin(1/x):
      lim_{x -> 0} sin(1/x) = AccumBounds(-1, 1) (oscillatory, non-convergent).
    Expected:
    - Must NOT classify the coefficient limit as an ordinary finite limit.
    - Must NOT claim C1 extension.
    - Return UNVERIFIED when symbolic continuation cannot be established.
    """
    req = ProblemRequest(
        raw_input="x*y' + x*sin(1/x)*y = 0, y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.UNVERIFIED
    assert res.verification.status == VerificationStatus.UNVERIFIED
    assert res.verification.status != VerificationStatus.C1_EXTENSION_VERIFIED
    assert "dao động" in res.verification.details.lower() or "accumbounds" in res.verification.details.lower() or "không xác định" in res.verification.details.lower()


# -------------------------------------------------------------------------
# P0-B: Make Original-Equation Residual Verification Fail-Closed
# -------------------------------------------------------------------------

def test_ux3_7_3_4_5_p0_b_residual_nonzero_fails_closed(linear_solver: ODELinearSolver, monkeypatch):
    """P0-B: Nonzero residual must produce FAILED or DISCREPANCY_DETECTED."""
    import math_app.solvers.calculus.ode.linear_solver as ls_mod

    # Patch differentiation of final_sol during residual check to simulate an incorrect solution
    orig_diff = ls_mod.sp.diff
    def mock_diff(expr, *args, **kwargs):
        if str(expr) == "exp(-2*x)":
            return sp.Integer(0)
        return orig_diff(expr, *args, **kwargs)

    monkeypatch.setattr(ls_mod.sp, "diff", mock_diff)

    req = ProblemRequest(
        raw_input="x*y' + 2*x*y = 0, y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.DISCREPANCY_DETECTED
    assert res.verification.status == VerificationStatus.FAILED


def test_ux3_7_3_4_5_p0_b_residual_exception_fails_closed(linear_solver: ODELinearSolver, monkeypatch):
    """P0-B: Exceptions during substitution, differentiation, or simplification produce UNVERIFIED."""
    import math_app.solvers.calculus.ode.linear_solver as ls_mod

    orig_diff = ls_mod.sp.diff
    def mock_diff(expr, *args, **kwargs):
        if str(expr) == "exp(-2*x)":
            raise RuntimeError("Symbolic differentiation engine failure during residual check")
        return orig_diff(expr, *args, **kwargs)

    monkeypatch.setattr(ls_mod.sp, "diff", mock_diff)

    req = ProblemRequest(
        raw_input="x*y' + 2*x*y = 0, y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.UNVERIFIED
    assert res.verification.status == VerificationStatus.UNVERIFIED
    assert "Symbolic differentiation engine failure" in res.verification.details or "Lỗi trong quá trình tính toán phần dư" in res.verification.details


# -------------------------------------------------------------------------
# P1-C: Complete Real Integration-Constant Solution Sets
# -------------------------------------------------------------------------

def test_ux3_7_3_4_5_p1_c_mandatory_periodic_family_sin_c():
    """P1-C: Mandatory example: y_-(t) = sin(C)/t + t, y_+(t) = t.

    Cancellation condition: sin(C) = 0.
    Complete real solution set: C in Union(ImageSet(2*k*pi), ImageSet(2*k*pi + pi)) = {k*pi | k in Z}.
    Expected:
    - CONDITIONAL_EXTENSION
    - Complete symbolic solution set preserved (never truncated to {0, pi}).
    - Mentions k*pi / Integers / ImageSet / Union.
    """
    t = sp.Symbol("t", real=True)
    C = sp.Symbol("C", real=True)
    b_left = MockBranch(sp.sin(C) / t + t, integration_constant=C)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    # Must preserve complete real solution set: contains k*pi and Integers/Union/ImageSet
    assert "k*pi" in details or "ImageSet" in details or "Union" in details
    assert "Integers" in details or "ℤ" in details or "pi" in details
    # Must NOT claim that only C=0 or C=pi is the iff condition
    assert "ràng buộc: C = 0 hoặc C = pi." not in details


def test_ux3_7_3_4_5_p1_c_periodic_family_cos_c():
    """P1-C: Periodic family: y_-(t) = cos(C)/t + t, y_+(t) = t.

    Cancellation condition: cos(C) = 0 => C in {pi/2 + k*pi}.
    Expected: CONDITIONAL_EXTENSION with complete symbolic set preserved.
    """
    t = sp.Symbol("t", real=True)
    C = sp.Symbol("C", real=True)
    b_left = MockBranch(sp.cos(C) / t + t, integration_constant=C)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "ImageSet" in details or "Union" in details or "pi" in details


def test_ux3_7_3_4_5_p1_c_unresolved_condition_set():
    """P1-C: Unresolved symbolic solving: y_-(t) = (exp(C) + sin(C))/t + t, y_+(t) = t.

    Cancellation condition: exp(C) + sin(C) = 0 => ConditionSet in SymPy solveset.
    Expected:
    - UNVERIFIED (Never guess or truncate).
    """
    t = sp.Symbol("t", real=True)
    C = sp.Symbol("C", real=True)
    b_left = MockBranch((sp.exp(C) + sp.sin(C)) / t + t, integration_constant=C)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.UNVERIFIED
    assert "chưa thể" in details.lower() or "không thể xác định tập nghiệm" in details.lower() or "conditionset" in details.lower()


def test_ux3_7_3_4_5_p1_c_proven_empty_set():
    """P1-C: Proven empty solution set: y_-(t) = (exp(C))/t + t, y_+(t) = t.

    Cancellation condition: exp(C) = 0 => EmptySet in Reals.
    Expected:
    - FAILED (Distinguished from unresolved).
    """
    t = sp.Symbol("t", real=True)
    C = sp.Symbol("C", real=True)
    b_left = MockBranch(sp.exp(C) / t + t, integration_constant=C)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.FAILED
    assert "không tồn tại giá trị thực" in details.lower() or "vô nghiệm thực" in details.lower()


# =========================================================================
# Section 6: UX3.7.3.4.6 — Final Symbolic Solution-Set & Realness Tests
# =========================================================================

# -------------------------------------------------------------------------
# P0: Fix representative-sample verification of infinite solution families
# -------------------------------------------------------------------------

def test_ux3_7_3_4_6_p0_mandatory_counterexample_sin_c_over_t_plus_c_plus_1_t():
    """P0 Mandatory Counterexample: y_-(t) = sin(C)/t + (C + 1)*t, y_+(t) = t.

    Pole cancellation requires C = k*pi (k in Z).
    Derivative compatibility requires C + 1 = 1 => C = 0 ONLY.
    Expected:
    - Do NOT report entire family C = k*pi as valid.
    - Determine actual compatible subset C = {0}.
    - Return CONDITIONAL_EXTENSION with C = 0 only.
    """
    t = sp.Symbol("t", real=True)
    C = sp.Symbol("C", real=True)
    b_left = MockBranch(sp.sin(C) / t + (C + 1) * t, integration_constant=C)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "C = 0" in details
    assert "k*pi" not in details
    assert "ImageSet" not in details
    assert "Union" not in details
    assert "pi" not in details


def test_ux3_7_3_4_6_p0_periodic_subset_filtering_even_multiples():
    """P0: Derivative compatibility selects proper infinite subset of periodic pole family.

    y_-(t) = sin(C)/t + cos(C)*t, y_+(t) = t.
    Pole cancellation: C in {2*k*pi} U {2*k*pi + pi}.
    Derivative check eliminates 2*k*pi + pi (since cos(2*k*pi + pi) = -1 != 1),
    preserving the complete even periodic subset C = 2*k*pi (k in Integers).
    """
    t = sp.Symbol("t", real=True)
    C = sp.Symbol("C", real=True)
    b_left = MockBranch(sp.sin(C) / t + sp.cos(C) * t, integration_constant=C)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "2*pi*k" in details or "2*k*pi" in details
    assert "Integers" in details
    assert "2*pi*k + pi" not in details and "2*k*pi + pi" not in details


def test_ux3_7_3_4_6_p0_valid_complete_periodic_family_universal_c1():
    """P0: Valid complete periodic family where every member satisfies C1 compatibility.

    y_-(t) = sin(C)/t + cos(2*C)*t, y_+(t) = t.
    Pole cancellation: C = k*pi (k in Z).
    For EVERY C = k*pi, cos(2*k*pi) = 1 identically, so y'_-(0) = 1 = y'_+(0).
    Must return CONDITIONAL_EXTENSION preserving complete C = k*pi family.
    """
    t = sp.Symbol("t", real=True)
    C = sp.Symbol("C", real=True)
    b_left = MockBranch(sp.sin(C) / t + sp.cos(2 * C) * t, integration_constant=C)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "k*pi" in details or "Union" in details
    assert "ImageSet" in details
    assert "Integers" in details


# -------------------------------------------------------------------------
# P1: Complete multi-constant solving and unresolved vs proven empty distinction
# -------------------------------------------------------------------------

def test_ux3_7_3_4_6_p1_multi_constant_coupled_linear_affine_family():
    """P1: Coupled multi-constant affine family preserved completely without truncation.

    y_-(t) = (C1 + C2 - 1)/t + (C1 + C2)*t, y_+(t) = t.
    Requires C1 + C2 = 1 => C1 = 1 - C2 for any C2 in Reals.
    """
    t = sp.Symbol("t", real=True)
    C1, C2 = sp.symbols("C1 C2", real=True)
    b_left = MockBranch((C1 + C2 - 1) / t + (C1 + C2) * t, integration_constant=C1)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "C1 = 1 - C2" in details
    assert "C2 in Reals" in details


def test_ux3_7_3_4_6_p1_multi_constant_coupled_polynomial_groebner():
    """P1: Coupled polynomial system across constants yields complete finite solution set.

    y_-(t) = (C1^2 + C2^2 - 5)/t^2 + (C1 - C2 - 1)/t + t, y_+(t) = t.
    System: C1^2 + C2^2 = 5, C1 - C2 = 1 => {(C1=-1, C2=-2), (C1=2, C2=1)}.
    """
    t = sp.Symbol("t", real=True)
    C1, C2 = sp.symbols("C1 C2", real=True)
    b_left = MockBranch((C1**2 + C2**2 - 5) / t**2 + (C1 - C2 - 1) / t + t, integration_constant=C1)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "C1 = -1" in details and "C2 = -2" in details
    assert "C1 = 2" in details and "C2 = 1" in details


def test_ux3_7_3_4_6_p1_multi_constant_periodic_and_algebraic_complete():
    """P1: Multiple constants combining periodic set in C1 and algebraic condition in C2.

    y_-(t) = sin(C1)/t + (C2 - 2)*t, y_+(t) = t.
    Complete real solutions: (C1 = 2*pi*k, C2 = 3) or (C1 = pi*(2*k + 1), C2 = 3), k in Integers.
    """
    t = sp.Symbol("t", real=True)
    C1, C2 = sp.symbols("C1 C2", real=True)
    b_left = MockBranch(sp.sin(C1) / t + (C2 - 2) * t, integration_constant=C1)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "C2 = 3" in details
    assert "Integers" in details
    assert "2*pi*k" in details


def test_ux3_7_3_4_6_p1_multi_constant_proven_empty_polynomial():
    """P1: Coupled polynomial system proven empty via Groebner reports FAILED."""
    t = sp.Symbol("t", real=True)
    C1, C2 = sp.symbols("C1 C2", real=True)
    b_left = MockBranch((C1**2 + C2**2 - 1) / t**2 + (C1 - C2 - 2) / t + t, integration_constant=C1)
    b_right = MockBranch(t)

    status, _ = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.FAILED


def test_ux3_7_3_4_6_p1_multi_constant_unresolved_solution_set():
    """P1: Coupled multi-constant transcendental system returns UNVERIFIED, never FAILED."""
    t = sp.Symbol("t", real=True)
    C1, C2 = sp.symbols("C1 C2", real=True)
    b_left = MockBranch((sp.exp(C1) + sp.sin(C2)) / t + t, integration_constant=C1)
    b_right = MockBranch(t)

    status, details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.UNVERIFIED
    assert status != VerificationStatus.FAILED
    assert status != VerificationStatus.CONDITIONAL_EXTENSION
    assert "chưa" in details.lower() or "không thể" in details.lower()


def test_ux3_7_3_4_6_p1_partial_resolved_plus_unresolved_stays_unverified():
    """P1: Never report CONDITIONAL_EXTENSION if another branch or constant remains unresolved."""
    t = sp.Symbol("t", real=True)
    C1, C2 = sp.symbols("C1 C2", real=True)
    b_left = MockBranch((C1**2 - 1) / t + t, integration_constant=C1)
    b_right = MockBranch((sp.exp(C2) + sp.sin(C2)) / t + t, integration_constant=C2)

    status, _ = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    assert status == VerificationStatus.UNVERIFIED
    assert status != VerificationStatus.CONDITIONAL_EXTENSION


def test_ux3_7_3_4_6_p1_no_candidates_without_proven_empty_is_unverified(monkeypatch):
    """P1: A solver returning no candidates without proving empty set must return UNVERIFIED, not FAILED."""
    import math_app.verification.calculus.ode_verifier as verifier_mod

    t = sp.Symbol("t", real=True)
    C, C1, C2 = sp.symbols("C C1 C2", real=True)

    # 1. Natural transcendental equation C - cos(C) = 0 has real root (~0.739) yet yields ConditionSet
    b_left_nat = MockBranch((C - sp.cos(C)) / t + t, integration_constant=C)
    b_right_nat = MockBranch(t)
    status_nat, _ = verify_singular_extension(
        branch_left=b_left_nat,
        branch_right=b_right_nat,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )
    assert status_nat == VerificationStatus.UNVERIFIED
    assert status_nat != VerificationStatus.FAILED

    # 2. Defensive check: even if solver returns empty branch list without 'empty' outcome, fail closed to UNVERIFIED
    monkeypatch.setattr(
        verifier_mod,
        "_solve_real_constraint_system",
        lambda *args, **kwargs: ("resolved", [], ""),
    )
    b_left_mk = MockBranch((C1 + C2) / t + t, integration_constant=C1)
    b_right_mk = MockBranch(t)
    status_mk, _ = verify_singular_extension(
        branch_left=b_left_mk,
        branch_right=b_right_mk,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )
    assert status_mk == VerificationStatus.UNVERIFIED
    assert status_mk != VerificationStatus.FAILED


# -------------------------------------------------------------------------
# P2: Tighten finite-real limit classification
# -------------------------------------------------------------------------

def test_ux3_7_3_4_6_p2_is_finite_real_limit_classification():
    """P2: Validate _is_finite_real_limit rejects unknown realness while accepting valid real params."""
    from math_app.solvers.calculus.ode.linear_solver import _is_finite_real_limit

    a_unknown = sp.Symbol("a")
    a_real = sp.Symbol("a", real=True)

    # Reject unknown realness (is_real is None)
    assert a_unknown.is_real is None
    assert _is_finite_real_limit(a_unknown) is False
    assert _is_finite_real_limit(sp.sqrt(a_real)) is False  # is_real is None for unconstrained real a
    assert _is_finite_real_limit(sp.tan(a_real)) is False   # singular points / is_real is None

    # Reject explicit non-finite / undefined / unresolved values
    assert _is_finite_real_limit(None) is False
    assert _is_finite_real_limit(sp.AccumBounds(-1, 1)) is False
    assert _is_finite_real_limit(sp.Limit(sp.sin(a_real) / a_real, a_real, 0)) is False
    assert _is_finite_real_limit(sp.oo) is False
    assert _is_finite_real_limit(-sp.oo) is False
    assert _is_finite_real_limit(sp.zoo) is False
    assert _is_finite_real_limit(sp.nan) is False
    assert _is_finite_real_limit(1 + sp.I) is False
    assert _is_finite_real_limit(sp.Function("f", real=True)(a_real)) is False

    # Accept determinate finite real numbers and genuinely real symbolic parameters
    assert _is_finite_real_limit(sp.Integer(-2)) is True
    assert _is_finite_real_limit(sp.Rational(3, 5)) is True
    assert _is_finite_real_limit(a_real) is True
    assert _is_finite_real_limit(sp.sin(a_real) + sp.exp(a_real)) is True

    # Real symbolic object where SymPy/attribute leaves is_finite=None while is_real=True must NOT be rejected
    class RealSymbolicWithUnknownFinite:
        is_real = True
        is_finite = None

    assert _is_finite_real_limit(RealSymbolicWithUnknownFinite()) is True

    # Explicit non-finite attribute must still be rejected even if is_real=True
    class NonFiniteReal:
        is_real = True
        is_finite = False

    assert _is_finite_real_limit(NonFiniteReal()) is False


def test_ux3_7_3_4_6_p2_unknown_realness_in_singular_cauchy_ode_is_unverified(linear_solver: ODELinearSolver):
    """P2: Singular Cauchy ODE with unassumed symbolic coefficient a (is_real=None) stays UNVERIFIED."""
    req = ProblemRequest(
        raw_input="x*y' + a*x*y = 0, y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.UNVERIFIED
    assert res.verification.status == VerificationStatus.UNVERIFIED
    assert res.verification.status != VerificationStatus.C1_EXTENSION_VERIFIED


# =========================================================================
# Section 7: UX3.7.3.4.7 — Parameter-Dependent Rank Degeneracy Tests
# =========================================================================

def test_ux3_7_3_4_7_mandatory_counterexample_constraint_solver():
    """UX3.7.3.4.7 Mandatory Counterexample in _solve_real_constraint_system():

    a*C1 + C2 = 1 and C1 + C2 = 2 with real parameter a (a = 1 makes system inconsistent).
    Must NOT claim C1 = -1/(a - 1), C2 = (2*a - 1)/(a - 1) is valid for every real a.
    Also verifies rank-drop without denominators ([a*C1, C1 + C2 - 1]) and minor
    cancellation ([a*C1 + C2 - 1, C1 + a*C2 - 1]) remain unresolved.
    """
    from math_app.verification.calculus.ode_verifier import _solve_real_constraint_system

    a = sp.Symbol("a", real=True)
    C1, C2 = sp.symbols("C1 C2", real=True)

    out, branches, _ = _solve_real_constraint_system(
        [a * C1 + C2 - 1, C1 + C2 - 2],
        [C1, C2],
    )
    assert out == "unresolved"
    assert branches == []

    # Even if a*C1 + C2 - 1 = 0 has a*C1 = 0 where no parameter appears in linsolve denominator (0, 1),
    # a = 0 drops rank and yields 1D solution space (1 - C2, C2). Must remain unresolved.
    out_nodem, branches_nodem, _ = _solve_real_constraint_system(
        [a * C1, C1 + C2 - 1],
        [C1, C2],
    )
    assert out_nodem == "unresolved"
    assert branches_nodem == []

    # Even when Cramer's formula cancels (a - 1) out of the denominator leaving 1/(a + 1),
    # det(A) = a^2 - 1 drops rank at both a = -1 and a = 1. Must remain unresolved.
    out_cancel, branches_cancel, _ = _solve_real_constraint_system(
        [a * C1 + C2 - 1, C1 + a * C2 - 1],
        [C1, C2],
    )
    assert out_cancel == "unresolved"
    assert branches_cancel == []


def test_ux3_7_3_4_7_full_singular_extension_counterexample_unverified():
    """UX3.7.3.4.7 Full Singular-Extension Regression:

    y_left = (a*C1 + C2 - 1)/t**2 + (C1 + C2 - 2)/t + t, y_right = t with real a.
    Must return UNVERIFIED and never C1_EXTENSION_VERIFIED or incomplete CONDITIONAL_EXTENSION.
    """
    t = sp.Symbol("t", real=True)
    a = sp.Symbol("a", real=True)
    C1, C2 = sp.symbols("C1 C2", real=True)

    y_left = (a * C1 + C2 - 1) / t**2 + (C1 + C2 - 2) / t + t
    b_left = MockBranch(y_left, integration_constant=C1)
    b_right = MockBranch(t)

    status_unprescribed, _ = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )
    assert status_unprescribed == VerificationStatus.UNVERIFIED
    assert status_unprescribed != VerificationStatus.C1_EXTENSION_VERIFIED
    assert status_unprescribed != VerificationStatus.CONDITIONAL_EXTENSION

    status_prescribed, _ = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=sp.Integer(0),
        deriv_at_point=sp.Integer(1),
        variable=t,
    )
    assert status_prescribed == VerificationStatus.UNVERIFIED
    assert status_prescribed != VerificationStatus.C1_EXTENSION_VERIFIED


def test_ux3_7_3_4_7_known_nonzero_parameter_handled_soundly():
    """UX3.7.3.4.7 Known Nonzero Coefficient:

    When determinant/minor and denominators are explicitly proven nonzero over the parameter domain,
    linear constraint solving and singular extension remain resolved; when nonzero a != 0 still
    permits another exceptional root (e.g. a = 1), it conservatively stays unresolved.
    """
    from math_app.verification.calculus.ode_verifier import _solve_real_constraint_system

    t = sp.Symbol("t", real=True)
    a_nz = sp.Symbol("a", real=True, nonzero=True)
    k_pos = sp.Symbol("k", positive=True)
    C1, C2 = sp.symbols("C1 C2", real=True)

    # 1. det(A) = 2*a_nz is proven nonzero -> exact solution C1 = 1/a_nz, C2 = 1
    out_nz, brs_nz, _ = _solve_real_constraint_system(
        [a_nz * C1 - C2, a_nz * C1 + C2 - 2],
        [C1, C2],
    )
    assert out_nz == "resolved"
    assert len(brs_nz) == 1
    assert sp.simplify(brs_nz[0].assignments[C1] - 1 / a_nz) == 0
    assert sp.simplify(brs_nz[0].assignments[C2] - 1) == 0

    # 2. a_nz != 0 STILL allows a = 1 in a*C1 + C2 = 1, C1 + C2 = 2 -> must NOT trust a != 0 as a - 1 != 0
    out_exc, brs_exc, _ = _solve_real_constraint_system(
        [a_nz * C1 + C2 - 1, C1 + C2 - 2],
        [C1, C2],
    )
    assert out_exc == "unresolved"
    assert brs_exc == []

    # 3. Positive shifted parameter k_pos > 0 => det(A) = k_pos > 0 is proven nonzero in full singular extension
    y_left_k = ((1 + k_pos) * C1 + C2 - 1) / t**2 + (C1 + C2 - 2) / t + t
    b_left_k = MockBranch(y_left_k, integration_constant=C1)
    b_right_k = MockBranch(t)
    status_k, details_k = verify_singular_extension(
        branch_left=b_left_k,
        branch_right=b_right_k,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )
    assert status_k == VerificationStatus.CONDITIONAL_EXTENSION
    assert "-1/k" in details_k


def test_ux3_7_3_4_7_ordinary_linear_systems_regression():
    """UX3.7.3.4.7 Ordinary Linear Systems:

    Ensure numeric-coefficient affine families (C1 + C2 = 1) and unique linear systems
    continue to resolve completely without regression.
    """
    from math_app.verification.calculus.ode_verifier import _solve_real_constraint_system

    C1, C2 = sp.symbols("C1 C2", real=True)

    out_aff, brs_aff, _ = _solve_real_constraint_system([C1 + C2 - 1], [C1, C2])
    assert out_aff == "resolved"
    assert len(brs_aff) == 1
    assert len(brs_aff[0].param_domains) == 1
    assert sp.simplify(brs_aff[0].assignments[C1] + brs_aff[0].assignments[C2] - 1) == 0

    out_uniq, brs_uniq, _ = _solve_real_constraint_system([C1 + C2 - 1, C1 - C2 - 1], [C1, C2])
    assert out_uniq == "resolved"
    assert len(brs_uniq) == 1
    assert brs_uniq[0].param_domains == {}
    assert brs_uniq[0].assignments[C1] == 1
    assert brs_uniq[0].assignments[C2] == 0




"""UX3.7.3.4.2 Acceptance Test Suite — Singular Extension Integrity & Genuine Acceptance.

Covers:
- P0: Fix false C1 extension verification with two free constants.
- P0: Mandatory negative controls (Cases A through H).
- P1: Degenerate singular Cauchy IVP handling (underdetermined vs contradictory).
- P1: Domain completeness propagation constraints.
- P0: Benchmark equation regression preservation.
"""

from __future__ import annotations

import pytest
import sympy as sp

from math_app.application.dtos import BranchSolution, ProblemRequest
from math_app.domain.models import (
    DomainCompleteness,
    ProblemType,
    SolutionStatus,
    VerificationStatus,
)
from math_app.solvers.calculus.ode.domain_analyzer import DomainAnalysisResult
from math_app.solvers.calculus.ode.linear_solver import ODELinearSolver
from math_app.verification.calculus.ode_verifier import (
    ODEVerifier,
    verify_singular_extension,
)


@pytest.fixture
def verifier() -> ODEVerifier:
    return ODEVerifier()


@pytest.fixture
def linear_solver() -> ODELinearSolver:
    return ODELinearSolver()


# ==============================================================================
# SECTION 1: MANDATORY NEGATIVE CONTROLS (CASES A - H)
# ==============================================================================


def test_case_a_two_free_constants_no_prescribed_value():
    """Case A: Two free constants, no prescribed point value.

    y_-(t) = C1 + t (t < 0)
    y_+(t) = C2 + t (t > 0)
    At t = 0: lim- = C1, lim+ = C2.
    Continuity requires C1 = C2.
    Equal derivatives (1 = 1) alone MUST NOT prove global C1 extension.
    The unrestricted family must return CONDITIONAL_EXTENSION and overall PARTIALLY_VERIFIED.
    """
    t = sp.Symbol("t", real=True)
    c1 = sp.Symbol("C1", real=True)
    c2 = sp.Symbol("C2", real=True)

    b_left = BranchSolution(
        expression=c1 + t,
        solution_str=f"{c1} + {t}",
        solution_latex=f"{c1} + {t}",
        branch_identity="Branch 1: (-oo, 0)",
        integration_constant=c1,
        domain_interval=(-sp.oo, sp.Integer(0)),
    )
    b_right = BranchSolution(
        expression=c2 + t,
        solution_str=f"{c2} + {t}",
        solution_latex=f"{c2} + {t}",
        branch_identity="Branch 2: (0, oo)",
        integration_constant=c2,
        domain_interval=(sp.Integer(0), sp.oo),
    )

    ext_status, ext_details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        deriv_at_point=None,
        variable=t,
    )

    # Must be CONDITIONAL_EXTENSION, never C1_EXTENSION_VERIFIED!
    assert ext_status == VerificationStatus.CONDITIONAL_EXTENSION
    assert "C1 = C2" in ext_details or "C2 = C1" in ext_details

    # Branch-aware aggregation must not promote this to C1_EXTENSION_VERIFIED or VERIFIED
    v = ODEVerifier()
    branches, overall_res = v.verify_branch_solutions(
        branches=(b_left, b_right),
        variable=t,
        p_expr=sp.Integer(0),
        g_expr=sp.Integer(1),
        singular_points=(sp.Integer(0),),
    )
    assert overall_res.status == VerificationStatus.PARTIALLY_VERIFIED
    assert overall_res.status != VerificationStatus.C1_EXTENSION_VERIFIED
    assert overall_res.status != VerificationStatus.VERIFIED


def test_case_b_two_free_constants_with_prescribed_point_value():
    """Case B: Two free constants with prescribed point value.

    y_-(t) = C1 + t
    y_+(t) = C2 + t
    y(0) = 0.
    Expected: C1 = 0, C2 = 0.
    Both constants are uniquely determined, matching value and derivative (1 = 1).
    Verifier must return C1_EXTENSION_VERIFIED with recorded constants C1 = 0, C2 = 0.
    """
    t = sp.Symbol("t", real=True)
    c1 = sp.Symbol("C1", real=True)
    c2 = sp.Symbol("C2", real=True)

    b_left = BranchSolution(
        expression=c1 + t,
        solution_str=f"{c1} + {t}",
        solution_latex=f"{c1} + {t}",
        branch_identity="Branch 1: (-oo, 0)",
        integration_constant=c1,
        domain_interval=(-sp.oo, sp.Integer(0)),
    )
    b_right = BranchSolution(
        expression=c2 + t,
        solution_str=f"{c2} + {t}",
        solution_latex=f"{c2} + {t}",
        branch_identity="Branch 2: (0, oo)",
        integration_constant=c2,
        domain_interval=(sp.Integer(0), sp.oo),
    )

    ext_status, ext_details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=sp.Integer(0),
        deriv_at_point=sp.Integer(1),
        variable=t,
    )

    assert ext_status == VerificationStatus.C1_EXTENSION_VERIFIED
    assert "C1 = 0" in ext_details
    assert "C2 = 0" in ext_details


def test_case_c_value_compatibility_but_derivative_incompatibility():
    """Case C: Value compatibility but derivative incompatibility.

    y_-(t) = C1 + t, y_+(t) = C2 + 2*t
    y(0) = 0.
    Values can match with C1 = 0, C2 = 0, but derivative limits are 1 and 2 (mismatch).
    Expected: CONTINUITY_VERIFIED, never C1_EXTENSION_VERIFIED.
    """
    t = sp.Symbol("t", real=True)
    c1 = sp.Symbol("C1", real=True)
    c2 = sp.Symbol("C2", real=True)

    b_left = BranchSolution(
        expression=c1 + t,
        solution_str=f"{c1} + {t}",
        solution_latex=f"{c1} + {t}",
        branch_identity="Branch 1",
        integration_constant=c1,
        domain_interval=(-sp.oo, sp.Integer(0)),
    )
    b_right = BranchSolution(
        expression=c2 + 2 * t,
        solution_str=f"{c2} + 2*{t}",
        solution_latex=f"{c2} + 2*{t}",
        branch_identity="Branch 2",
        integration_constant=c2,
        domain_interval=(sp.Integer(0), sp.oo),
    )

    ext_status, ext_details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=sp.Integer(0),
        deriv_at_point=None,
        variable=t,
    )

    assert ext_status == VerificationStatus.CONTINUITY_VERIFIED
    assert ext_status != VerificationStatus.C1_EXTENSION_VERIFIED
    assert "đạo hàm một phía không khớp" in ext_details


def test_case_d_value_mismatch_independent_of_constants():
    """Case D: Value mismatch independent of constants (explicit jump discontinuity).

    y_-(t) = t + 1, y_+(t) = t + 2
    lim- = 1, lim+ = 2.
    Expected: FAILED.
    """
    t = sp.Symbol("t", real=True)
    b_left = BranchSolution(
        expression=t + 1,
        solution_str=f"{t} + 1",
        solution_latex=f"{t} + 1",
        branch_identity="Branch 1",
        domain_interval=(-sp.oo, sp.Integer(0)),
    )
    b_right = BranchSolution(
        expression=t + 2,
        solution_str=f"{t} + 2",
        solution_latex=f"{t} + 2",
        branch_identity="Branch 2",
        domain_interval=(sp.Integer(0), sp.oo),
    )

    ext_status, ext_details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        variable=t,
    )

    assert ext_status == VerificationStatus.FAILED
    assert "Mâu thuẫn giới hạn hai phía" in ext_details


def test_case_e_two_independent_constants_with_no_possible_common_value():
    """Case E: Two independent branch constants with no possible common value.

    y_-(t) = C1^2 + 1 + t
    y_+(t) = -C2^2 - 1 + t
    lim- = C1^2 + 1 >= 1.
    lim+ = -C2^2 - 1 <= -1.
    Equation C1^2 + C2^2 + 2 = 0 has no real solution.
    Expected: FAILED.
    """
    t = sp.Symbol("t", real=True)
    c1 = sp.Symbol("C1", real=True)
    c2 = sp.Symbol("C2", real=True)

    b_left = BranchSolution(
        expression=c1**2 + 1 + t,
        solution_str="C1^2 + 1 + t",
        solution_latex="C_1^2 + 1 + t",
        branch_identity="Branch 1",
        integration_constant=c1,
        domain_interval=(-sp.oo, sp.Integer(0)),
    )
    b_right = BranchSolution(
        expression=-c2**2 - 1 + t,
        solution_str="-C2^2 - 1 + t",
        solution_latex="-C_2^2 - 1 + t",
        branch_identity="Branch 2",
        integration_constant=c2,
        domain_interval=(sp.Integer(0), sp.oo),
    )

    ext_status, ext_details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=None,
        variable=t,
    )

    assert ext_status == VerificationStatus.FAILED
    assert "vô nghiệm thực" in ext_details or "Mâu thuẫn" in ext_details


def test_case_f_symbolically_unresolved_compatibility_equations():
    """Case F: Symbolically unresolved limit expressions.

    When limits contain unevaluated sp.Limit, return UNVERIFIED.
    """
    t = sp.Symbol("t", real=True)
    # Using an expression that SymPy leaves as unevaluated Limit
    dummy_limit_expr = sp.Limit(sp.sin(1 / t), t, 0)
    b_left = BranchSolution(
        expression=dummy_limit_expr,
        solution_str="Limit(sin(1/t), t, 0)",
        solution_latex="\\lim_{t\\to 0}\\sin(1/t)",
        branch_identity="Branch 1",
        domain_interval=(-sp.oo, sp.Integer(0)),
    )
    b_right = BranchSolution(
        expression=sp.Integer(0),
        solution_str="0",
        solution_latex="0",
        branch_identity="Branch 2",
        domain_interval=(sp.Integer(0), sp.oo),
    )

    ext_status, ext_details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        variable=t,
    )

    assert ext_status == VerificationStatus.UNVERIFIED


def test_case_g_valid_c1_extension():
    """Case G: Valid C1 extension proven after constant selection.

    y_-(t) = C1 + t^2
    y_+(t) = C2 + t^2
    y(0) = 0.
    C1 = 0, C2 = 0 -> y(t) = t^2.
    y'(t) = 2*t -> y'(0) = 0.
    Expected: C1_EXTENSION_VERIFIED.
    """
    t = sp.Symbol("t", real=True)
    c1 = sp.Symbol("C1", real=True)
    c2 = sp.Symbol("C2", real=True)

    b_left = BranchSolution(
        expression=c1 + t**2,
        solution_str=f"{c1} + t^2",
        solution_latex=f"{c1} + t^2",
        branch_identity="Branch 1",
        integration_constant=c1,
        domain_interval=(-sp.oo, sp.Integer(0)),
    )
    b_right = BranchSolution(
        expression=c2 + t**2,
        solution_str=f"{c2} + t^2",
        solution_latex=f"{c2} + t^2",
        branch_identity="Branch 2",
        integration_constant=c2,
        domain_interval=(sp.Integer(0), sp.oo),
    )

    ext_status, ext_details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(0),
        value_at_point=sp.Integer(0),
        deriv_at_point=sp.Integer(0),
        variable=t,
    )

    assert ext_status == VerificationStatus.C1_EXTENSION_VERIFIED
    assert "C1 = 0" in ext_details
    assert "C2 = 0" in ext_details


def test_case_h_non_elementary_unevaluated_integrals():
    """Case H: Non-elementary unevaluated integrals.

    Expected: UNVERIFIED, never C1_EXTENSION_VERIFIED.
    """
    t = sp.Symbol("t", real=True)
    u = sp.Symbol("u", real=True)
    uneval_int = sp.Integral(sp.log(u) / (u - 3), (u, 1, t))

    b_left = BranchSolution(
        expression=uneval_int,
        solution_str="Integral",
        solution_latex="\\int",
        branch_identity="Branch 1",
        domain_interval=(sp.Integer(0), sp.Integer(3)),
    )
    b_right = BranchSolution(
        expression=t,
        solution_str="t",
        solution_latex="t",
        branch_identity="Branch 2",
        domain_interval=(sp.Integer(3), sp.oo),
    )

    ext_status, ext_details = verify_singular_extension(
        branch_left=b_left,
        branch_right=b_right,
        singular_point=sp.Integer(3),
        variable=t,
    )

    assert ext_status == VerificationStatus.UNVERIFIED
    assert "nguyên hàm sơ cấp" in ext_details


# ==============================================================================
# SECTION 2: DEGENERATE SINGULAR CAUCHY CONDITIONS (P1)
# ==============================================================================


def test_degenerate_cauchy_t_yp_eq_t_with_ic_5(linear_solver: ODELinearSolver):
    """Equation: t*y' = t, y(0) = 5.

    At t = 0: a1(0) = 0, b0(0) = 0, r(0) = 0 (underdetermined 0 = 0).
    Normalized branches on (-oo, 0) and (0, oo) satisfy y' = 1 -> y(t) = t + C.
    Matching lim_{t->0} y(t) = 5 uniquely determines C1 = 5, C2 = 5 -> y(t) = t + 5.
    y'(t) = 1 everywhere -> C1 smooth extension everywhere on R.
    Must return SolutionStatus.SUCCESS and C1_EXTENSION_VERIFIED.
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="t*y' = t, y(0) = 5",
        target_variable="t",
    )
    resp = linear_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED
    assert "t + 5" in resp.final_result


def test_degenerate_cauchy_t_yp_eq_t_with_ic_1(linear_solver: ODELinearSolver):
    """Equation: t*y' = t, y(0) = 1 -> y(t) = t + 1."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="t*y' = t, y(0) = 1",
        target_variable="t",
    )
    resp = linear_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED
    assert "t + 1" in resp.final_result


def test_degenerate_cauchy_t_yp_eq_0_with_ic_7(linear_solver: ODELinearSolver):
    """Equation: t*y' = 0, y(0) = 7 -> y(t) = 7."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="t*y' = 0, y(0) = 7",
        target_variable="t",
    )
    resp = linear_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED
    assert "7" in resp.final_result


def test_singular_contradiction_t_yp_eq_1_with_ic(linear_solver: ODELinearSolver):
    """Equation: t*y' = 1, y(0) = 5.

    At t = 0: a1(0) = 0, b0(0) = 0, r(0) = 1.
    Equation gives 0 = 1 (contradiction).
    Must return INVALID_INPUT.
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="t*y' = 1, y(0) = 5",
        target_variable="t",
    )
    resp = linear_solver.solve(req)

    assert resp.status == SolutionStatus.INVALID_INPUT
    assert resp.verification.status == VerificationStatus.NOT_APPLICABLE


def test_singular_pole_equation_rejected(linear_solver: ODELinearSolver):
    """Equation: t*y' + y = 0, y(0) = 1.

    At t = 0: a1(0) = 0, b0(0) = 1, r(0) = 0 -> required y(0) = 0.
    Given y(0) = 1 != 0 -> contradiction.
    Must return INVALID_INPUT.
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="t*y' + y = 0, y(0) = 1",
        target_variable="t",
    )
    resp = linear_solver.solve(req)

    assert resp.status == SolutionStatus.INVALID_INPUT
    assert "mâu thuẫn" in resp.verification.details.lower() or "không tồn tại nghiệm" in resp.verification.details.lower()


# ==============================================================================
# SECTION 3: DOMAIN COMPLETENESS CONSTRAINTS (P1)
# ==============================================================================


def test_domain_completeness_unknown_caps_verification():
    """When domain completeness is UNKNOWN, verification must never be global VERIFIED."""
    da = DomainAnalysisResult(
        original_domain=sp.Reals,
        normalized_domain=sp.Reals,
        connected_intervals=(sp.Interval(-sp.oo, sp.oo),),
        singular_points=(),
        denominator_zeros=(),
        original_domain_latex="\\mathbb{R}",
        normalized_domain_latex="\\mathbb{R}",
        domain_restrictions=(),
        completeness=DomainCompleteness.UNKNOWN,
    )
    from math_app.solvers.calculus.ode.domain_analyzer import ODEDomainAnalyzer

    solver = ODELinearSolver()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ODEDomainAnalyzer, "analyze_first_order_ode", lambda *args, **kwargs: da)
        req = ProblemRequest(
            problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
            raw_input="y' + t*y = 0",
            target_variable="t",
        )
        resp = solver.solve(req)
        assert resp.verification.status == VerificationStatus.PARTIALLY_VERIFIED
        assert resp.verification.status != VerificationStatus.VERIFIED


# ==============================================================================
# SECTION 4: BENCHMARK EQUATION REGRESSION
# ==============================================================================


def test_singular_cauchy_benchmark_compatible_is_unverified(linear_solver: ODELinearSolver):
    """Benchmark: (t-3)*y' + ln(t)*y = 2*t, y(3) = 6/ln(3).

    Algebraically compatible at t = 3, but integrating factor cannot be anchored at 3
    and unevaluated integrals prevent analytic C1 proof.
    Must return UNVERIFIED (never SUCCESS).
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="(t-3)*y' + ln(t)*y = 2*t, y(3) = 6/ln(3)",
        target_variable="t",
    )
    resp = linear_solver.solve(req)

    assert resp.status == SolutionStatus.UNVERIFIED
    assert resp.verification.status == VerificationStatus.UNVERIFIED
    assert resp.status != SolutionStatus.SUCCESS


def test_singular_cauchy_benchmark_incompatible_is_invalid(linear_solver: ODELinearSolver):
    """Benchmark: (t-3)*y' + ln(t)*y = 2*t, y(3) = 1.

    Incompatible at singular point (1 != 6/ln(3)).
    Must return INVALID_INPUT.
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="(t-3)*y' + ln(t)*y = 2*t, y(3) = 1",
        target_variable="t",
    )
    resp = linear_solver.solve(req)

    assert resp.status == SolutionStatus.INVALID_INPUT

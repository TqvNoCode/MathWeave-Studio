"""UX3.7.3.4.1 — FINAL MATHEMATICAL INTEGRITY & REPRODUCIBLE ACCEPTANCE TEST SUITE

Tests:
Group A: Regular Cauchy IVP (Left branch t0=1, Right branch t0=4, Independent constants, Anchoring)
Group B: Singular Cauchy IVP (Incompatible rejection, Compatible analysis, No anchored pole integral, Piecewise consistency, UNVERIFIED status)
Group C: Branch Verification Aggregation & Real Constant Compatibility (Continuity vs C1, Point limit conflicts, Global status)
Group D: Exact Domain Analysis (1/sin(sin(t)), 1/cos(sin(t)), tan(sin(t)), cot(sin(t)), 1/sin(t^2), 1/(sin(t)+cos(t)), Mixed sets, ConditionSet, Unknown denominators)
Group E: Verification Architecture Negative Controls & Stale Warning Audit
"""

from __future__ import annotations

import sympy as sp

from math_app.application.dtos import BranchSolution, ProblemRequest
from math_app.domain.models import (
    DomainCompleteness,
    ProblemType,
    SolutionStatus,
    VerificationStatus,
)
from math_app.solvers.calculus.ode.domain_analyzer import (
    _decompose_set_components,
    extract_expression_domain_with_completeness,
    format_set_latex,
)
from math_app.solvers.calculus.ode.linear_solver import ODELinearSolver
from math_app.verification.calculus.ode_verifier import (
    ODEVerifier,
    is_point_in_interval_interior,
    verify_singular_extension,
)


# ==============================================================================
# GROUP A: REGULAR CAUCHY IVP ON DISCONNECTED DOMAINS
# ==============================================================================

class TestGroupARegularCauchyIVP:
    """Rigorous end-to-end integration tests for regular Cauchy IVP on disconnected branches."""

    def test_left_branch_ivp_t0_1(self) -> None:
        """Left branch Cauchy IVP: (t - 3)*y' + ln(t)*y = 2*t, y(1) = 0.
        Verifies:
        - Target branch (0, 3) is selected.
        - Initial condition y(1) = 0 is satisfied.
        - Right branch (3, +oo) remains independent with free C_2.
        - Integration constant metadata is NOT incorrectly set equal to y0.
        - Response status is SUCCESS with PARTIALLY_VERIFIED (branch verified).
        """
        solver = ODELinearSolver()
        req = ProblemRequest(
            raw_input="(t - 3)*y' + ln(t)*y = 2*t, y(1) = 0",
            problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
            target_variable="t",
        )
        resp = solver.solve(req)
        assert resp.status == SolutionStatus.SUCCESS
        assert len(resp.branch_solutions) == 2

        b1, b2 = resp.branch_solutions[0], resp.branch_solutions[1]
        assert b1.domain_interval == (0, 3)
        assert b2.domain_interval == (3, sp.oo)

        # Branch 1 is anchored and determined
        assert "Cauchy" in str(b1.initial_condition_status)
        assert b1.verification is not None
        assert b1.verification.status == VerificationStatus.VERIFIED

        # Branch 2 remains independent
        assert "Chưa xác định" in str(b2.initial_condition_status)
        assert b2.integration_constant_val is None
        assert b2.verification is not None
        assert b2.verification.status == VerificationStatus.VERIFIED

        # Overall verification is PARTIALLY_VERIFIED on disconnected domain
        assert resp.verification.status == VerificationStatus.PARTIALLY_VERIFIED
        assert "I_1" in resp.final_latex or "(0, 3)" in resp.final_latex

    def test_right_branch_ivp_t0_4_nonzero_y0(self) -> None:
        """Right branch Cauchy IVP: (t - 3)*y' + ln(t)*y = 2*t, y(4) = 5.
        Verifies:
        - Target branch (3, +oo) is selected.
        - Left branch (0, 3) remains independent with free C_1.
        - Nonzero initial value y(4) = 5 does NOT cause integration_constant_val == 5.
        - Piecewise solution is consistent across display and branch metadata.
        """
        solver = ODELinearSolver()
        req = ProblemRequest(
            raw_input="(t - 3)*y' + ln(t)*y = 2*t, y(4) = 5",
            problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
            target_variable="t",
        )
        resp = solver.solve(req)
        assert resp.status == SolutionStatus.SUCCESS
        assert len(resp.branch_solutions) == 2

        b1, b2 = resp.branch_solutions[0], resp.branch_solutions[1]
        assert b1.domain_interval == (0, 3)
        assert b2.domain_interval == (3, sp.oo)

        # Left branch remains independent
        assert "Chưa xác định" in str(b1.initial_condition_status)
        assert b1.integration_constant_val is None

        # Right branch is anchored
        assert "Cauchy" in str(b2.initial_condition_status)
        # CRUCIAL REGRESSION: integration constant metadata is NOT incorrectly set equal to y0 (= 5)
        assert b2.integration_constant_val != 5
        assert b2.integration_constant_val is None
        assert b2.verification is not None
        assert b2.verification.status == VerificationStatus.VERIFIED

        # Consistency: final_latex corresponds to branches
        assert "begin{cases}" in resp.final_latex
        assert "(3, +\\infty)" in resp.final_latex or "(3, +\\infty" in resp.final_latex

    def test_exact_symbolic_branch_membership(self) -> None:
        """Point interior check must handle symbolic endpoints, open/closed boundaries, and infinities."""
        # Inside (0, 3)
        assert is_point_in_interval_interior(sp.Integer(1), sp.Integer(0), sp.Integer(3)) is True
        assert is_point_in_interval_interior(sp.sqrt(2), sp.Integer(0), sp.Integer(3)) is True

        # Boundary singular points MUST NOT be inside
        assert is_point_in_interval_interior(sp.Integer(0), sp.Integer(0), sp.Integer(3)) is False
        assert is_point_in_interval_interior(sp.Integer(3), sp.Integer(0), sp.Integer(3)) is False
        assert is_point_in_interval_interior(sp.Integer(3), sp.Integer(3), sp.oo) is False

        # Outside (0, 3)
        assert is_point_in_interval_interior(sp.Integer(4), sp.Integer(0), sp.Integer(3)) is False
        assert is_point_in_interval_interior(sp.Integer(-1), sp.Integer(0), sp.Integer(3)) is False

        # Inside (3, +oo)
        assert is_point_in_interval_interior(sp.Integer(4), sp.Integer(3), sp.oo) is True
        assert is_point_in_interval_interior(sp.Integer(100), sp.Integer(3), sp.oo) is True


# ==============================================================================
# GROUP B: SINGULAR CAUCHY IVP (t0 = 3)
# ==============================================================================

class TestGroupBSingularCauchyIVP:
    """Verifies that IVP at the singular point t0 = 3 rejects contradictions, accepts compatible values,
    and returns UNVERIFIED without false SUCCESS or invalid anchored integrals."""

    def test_singular_cauchy_contradiction_rejected(self) -> None:
        """At t0 = 3, (3-3)y'(3) + ln(3)y(3) = 6 => y(3) = 6/ln(3).
        With y(3) = 1, must return INVALID_INPUT and FAILED verification."""
        solver = ODELinearSolver()
        req = ProblemRequest(
            raw_input="(t - 3)*y' + ln(t)*y = 2*t, y(3) = 1",
            problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
            target_variable="t",
        )
        resp = solver.solve(req)
        assert resp.status == SolutionStatus.INVALID_INPUT
        assert resp.verification.status in (VerificationStatus.FAILED, VerificationStatus.NOT_APPLICABLE)
        assert resp.verification.method in ("singular_cauchy_contradiction", "initial_point_domain_validation")
        assert "điểm kỳ dị" in resp.warnings[0].lower()

    def test_singular_cauchy_compatible_value_unverified_status(self) -> None:
        """At t0 = 3, with compatible y(3) = 6/ln(3):
        - Must NOT return SolutionStatus.SUCCESS (since continuation is unproven).
        - Must return SolutionStatus.UNVERIFIED.
        - Must NOT anchor an integral across t0 = 3 (no pole integral exp(int_3^t ln(u)/(u-3) du)).
        - Must preserve both branches I_1 and I_2 with independent constants.
        - Displayed solution must match branch_solutions piecewise cases.
        """
        solver = ODELinearSolver()
        req = ProblemRequest(
            raw_input="(t - 3)*y' + ln(t)*y = 2*t, y(3) = 6/ln(3)",
            problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
            target_variable="t",
        )
        resp = solver.solve(req)

        # Gate 4: Compatible singular initial value NOT falsely accepted as complete solution
        assert resp.status == SolutionStatus.UNVERIFIED
        assert resp.verification.status == VerificationStatus.UNVERIFIED

        # Preserves 2 independent branches
        assert len(resp.branch_solutions) == 2
        b1, b2 = resp.branch_solutions[0], resp.branch_solutions[1]
        assert b1.domain_interval == (0, 3)
        assert b2.domain_interval == (3, sp.oo)
        assert "điểm kỳ dị" in str(b1.initial_condition_status)
        assert "điểm kỳ dị" in str(b2.initial_condition_status)

        # Consistency: final_latex and final_result correspond to piecewise branches
        assert "begin{cases}" in resp.final_latex
        assert "I_1" in resp.final_latex or "(0, 3)" in resp.final_latex
        assert "I_2" in resp.final_latex or "(3, +\\infty)" in resp.final_latex
        assert "6/log(3)" in resp.final_result or "6/ln(3)" in resp.final_result or "điểm kỳ dị" in resp.final_result

        # Pedagogical steps document singular compatibility and derivative condition
        step_rules = [s.rule_name for s in resp.steps]
        assert any("kỳ dị" in r for r in step_rules)


# ==============================================================================
# GROUP C: BRANCH VERIFICATION AGGREGATION & NEGATIVE CONTROLS
# ==============================================================================

class TestGroupCBranchVerificationAggregation:
    """Verifies authoritative aggregation rules for verify_branch_solutions and singular extensions."""

    def test_control_1_residuals_zero_extension_unresolved(self) -> None:
        """Both branch residuals are zero, but singular extension is unresolved.
        Overall status must be PARTIALLY_VERIFIED (never VERIFIED)."""
        t = sp.Symbol("t", real=True)
        s = sp.Symbol("s", real=True)
        # Branches satisfying y' = sin(t)/t with unevaluated integral
        b1 = BranchSolution(
            expression=sp.Integral(sp.sin(s) / s, (s, 1, t)),
            solution_str="b1",
            solution_latex="b1",
            branch_identity="I_1",
            domain_interval=(0, 3),
        )
        b2 = BranchSolution(
            expression=sp.Integral(sp.sin(s) / s, (s, 1, t)),
            solution_str="b2",
            solution_latex="b2",
            branch_identity="I_2",
            domain_interval=(3, sp.oo),
        )

        verifier = ODEVerifier()
        branches_out, overall_res = verifier.verify_branch_solutions(
            branches=(b1, b2),
            variable=t,
            p_expr=sp.Integer(0),
            g_expr=sp.sin(t) / t,
            singular_points=(sp.Integer(3),),
        )
        assert overall_res.status == VerificationStatus.PARTIALLY_VERIFIED
        assert overall_res.status != VerificationStatus.VERIFIED

    def test_control_2_residuals_zero_point_limits_conflict(self) -> None:
        """Both branch residuals are zero, but their limits at the singular point conflict.
        Overall status must be FAILED."""
        t = sp.Symbol("t", real=True)
        # Solution to y' = 0 on (-oo, 0) and (0, oo)
        # Left limit = 1, Right limit = 2
        b1 = BranchSolution(
            expression=sp.Integer(1),
            solution_str="1",
            solution_latex="1",
            branch_identity="I_1",
            domain_interval=(-sp.oo, 0),
        )
        b2 = BranchSolution(
            expression=sp.Integer(2),
            solution_str="2",
            solution_latex="2",
            branch_identity="I_2",
            domain_interval=(0, sp.oo),
        )

        ext_status, ext_details = verify_singular_extension(
            branch_left=b1,
            branch_right=b2,
            singular_point=sp.Integer(0),
            value_at_point=sp.Integer(0),
            deriv_at_point=sp.Integer(0),
            variable=t,
        )
        assert ext_status == VerificationStatus.FAILED
        assert "không trùng khớp" in ext_details

        verifier = ODEVerifier()
        _, overall_res = verifier.verify_branch_solutions(
            branches=(b1, b2),
            variable=t,
            p_expr=sp.Integer(0),
            g_expr=sp.Integer(0),
            singular_points=(sp.Integer(0),),
        )
        assert overall_res.status == VerificationStatus.FAILED

    def test_control_3_value_limits_match_derivative_limits_conflict(self) -> None:
        """Continuous across singularity (C0) but derivative limits do not match (not C1).
        Overall status must be CONTINUITY_VERIFIED."""
        t = sp.Symbol("t", real=True)
        # y(t) = -t for t < 0, y(t) = t for t > 0 satisfies y' - (1/t)y = 0 on both branches
        # lim y(t) = 0 from both sides. But dy/dt- = -1 != dy/dt+ = 1.
        b1 = BranchSolution(
            expression=-t,
            solution_str="-t",
            solution_latex="-t",
            branch_identity="I_1",
            domain_interval=(-sp.oo, 0),
        )
        b2 = BranchSolution(
            expression=t,
            solution_str="t",
            solution_latex="t",
            branch_identity="I_2",
            domain_interval=(0, sp.oo),
        )

        ext_status, ext_details = verify_singular_extension(
            branch_left=b1,
            branch_right=b2,
            singular_point=sp.Integer(0),
            value_at_point=sp.Integer(0),
            deriv_at_point=sp.Integer(0),
            variable=t,
        )
        assert ext_status == VerificationStatus.CONTINUITY_VERIFIED
        assert "Không thể mở rộng khả vi C¹" in ext_details

        verifier = ODEVerifier()
        _, overall_res = verifier.verify_branch_solutions(
            branches=(b1, b2),
            variable=t,
            p_expr=-1 / t,
            g_expr=sp.Integer(0),
            singular_points=(sp.Integer(0),),
        )
        assert overall_res.status == VerificationStatus.CONTINUITY_VERIFIED

    def test_control_4_both_values_and_derivatives_match(self) -> None:
        """Smooth C1 connection across singular point: y(t) = t^2.
        Overall status must be C1_EXTENSION_VERIFIED."""
        t = sp.Symbol("t", real=True)
        b1 = BranchSolution(
            expression=t**2,
            solution_str="t^2",
            solution_latex="t^2",
            branch_identity="I_1",
            domain_interval=(-sp.oo, 0),
        )
        b2 = BranchSolution(
            expression=t**2,
            solution_str="t^2",
            solution_latex="t^2",
            branch_identity="I_2",
            domain_interval=(0, sp.oo),
        )

        verifier = ODEVerifier()
        _, overall_res = verifier.verify_branch_solutions(
            branches=(b1, b2),
            variable=t,
            p_expr=sp.Integer(0),
            g_expr=2 * t,
            singular_points=(sp.Integer(0),),
        )
        assert overall_res.status == VerificationStatus.C1_EXTENSION_VERIFIED

    def test_control_5_one_branch_nonzero_residual(self) -> None:
        """One branch satisfies the ODE, other has wrong solution. Must be FAILED."""
        t = sp.Symbol("t", real=True)
        b1 = BranchSolution(
            expression=t**2,
            solution_str="t^2",
            solution_latex="t^2",
            branch_identity="I_1",
            domain_interval=(-sp.oo, 0),
        )
        b2 = BranchSolution(
            expression=t**3,  # Wrong solution for y' = 2t
            solution_str="t^3",
            solution_latex="t^3",
            branch_identity="I_2",
            domain_interval=(0, sp.oo),
        )

        verifier = ODEVerifier()
        _, overall_res = verifier.verify_branch_solutions(
            branches=(b1, b2),
            variable=t,
            p_expr=sp.Integer(0),
            g_expr=2 * t,
            singular_points=(sp.Integer(0),),
        )
        assert overall_res.status == VerificationStatus.FAILED

    def test_control_6_branch_incorrect_initial_condition(self) -> None:
        """Branch has incorrect initial condition. Must be FAILED."""
        t = sp.Symbol("t", real=True)
        b1 = BranchSolution(
            expression=t**2,  # y(1) = 1, but IC claims y(1) = 99
            solution_str="t^2",
            solution_latex="t^2",
            branch_identity="I_1",
            domain_interval=(0, 3),
        )
        verifier = ODEVerifier()
        _, overall_res = verifier.verify_branch_solutions(
            branches=(b1,),
            variable=t,
            p_expr=sp.Integer(0),
            g_expr=2 * t,
            initial_condition=(sp.Integer(1), sp.Integer(99)),
        )
        assert overall_res.status == VerificationStatus.FAILED

    def test_control_7_regular_connected_solution_verified(self) -> None:
        """Standard regular ODE with no singular points: y' + 2y = 4, y(0) = 2.
        Must be VERIFIED."""
        t = sp.Symbol("t", real=True)
        sol = sp.Integer(2)  # y(t) = 2 satisfies y' + 2y = 4 and y(0) = 2
        verifier = ODEVerifier()
        res = verifier.verify_explicit(
            solution=sol,
            variable=t,
            p_expr=sp.Integer(2),
            g_expr=sp.Integer(4),
            initial_condition=(sp.Integer(0), sp.Integer(2)),
        )
        assert res.status == VerificationStatus.VERIFIED


# ==============================================================================
# GROUP D: DOMAIN ANALYSIS & COMPLETENESS
# ==============================================================================

class TestGroupDDomainAnalysisCompleteness:
    """Rigorous evaluation of domain completeness, ConditionSet, and mixed set handling."""

    def test_domain_1_over_sin_sin_t(self) -> None:
        """1/sin(sin(t)) has periodic zeros at t = k*pi.
        solveset returns ConditionSet; completeness must be PARTIAL (roots 0, pi found, not EXACT)."""
        t = sp.Symbol("t", real=True)
        dom, comp = extract_expression_domain_with_completeness(1 / sp.sin(sp.sin(t)), t)
        assert comp == DomainCompleteness.PARTIAL
        assert comp != DomainCompleteness.EXACT
        assert 0 not in dom

    def test_domain_1_over_cos_sin_t(self) -> None:
        """1/cos(sin(t)): |sin(t)| <= 1 < pi/2, so cos(sin(t)) > 0 everywhere.
        solveset returns ConditionSet, solve() returns [].
        Per rule 5.1 & 5.2: solve returning [] must NOT return EXACT; must return UNKNOWN."""
        t = sp.Symbol("t", real=True)
        dom, comp = extract_expression_domain_with_completeness(1 / sp.cos(sp.sin(t)), t)
        assert comp == DomainCompleteness.UNKNOWN
        assert comp != DomainCompleteness.EXACT

    def test_domain_tan_sin_t(self) -> None:
        """tan(sin(t)) requires cos(sin(t)) != 0.
        Must return UNKNOWN, not EXACT."""
        t = sp.Symbol("t", real=True)
        dom, comp = extract_expression_domain_with_completeness(sp.tan(sp.sin(t)), t)
        assert comp == DomainCompleteness.UNKNOWN
        assert comp != DomainCompleteness.EXACT

    def test_domain_cot_sin_t(self) -> None:
        """cot(sin(t)) requires sin(sin(t)) != 0.
        Must return PARTIAL, not EXACT."""
        t = sp.Symbol("t", real=True)
        dom, comp = extract_expression_domain_with_completeness(sp.cot(sp.sin(t)), t)
        assert comp == DomainCompleteness.PARTIAL
        assert comp != DomainCompleteness.EXACT

    def test_domain_1_over_sin_t_squared(self) -> None:
        """1/sin(t^2) is solved via ImageSet union with completeness EXACT."""
        t = sp.Symbol("t", real=True)
        dom, comp = extract_expression_domain_with_completeness(1 / sp.sin(t**2), t)
        assert comp == DomainCompleteness.EXACT
        assert 0 not in dom

    def test_domain_1_over_sin_plus_cos(self) -> None:
        """1/(sin(t) + cos(t)) is solved via ImageSet union with completeness EXACT."""
        t = sp.Symbol("t", real=True)
        dom, comp = extract_expression_domain_with_completeness(1 / (sp.sin(t) + sp.cos(t)), t)
        assert comp == DomainCompleteness.EXACT

    def test_mixed_interval_and_finiteset_preservation(self) -> None:
        """(0, 1) U {2} must preserve the interval (0, 1) AND the isolated point {2}."""
        s = sp.Union(sp.Interval.open(0, 1), sp.FiniteSet(2))
        intervals, isolated, other = _decompose_set_components(s)
        assert len(intervals) == 1
        assert intervals[0] == sp.Interval.open(0, 1)
        assert isolated == [sp.Integer(2)]
        assert other == []

        ltx = format_set_latex(s)
        assert "(0, 1)" in ltx
        assert "\\{2\\}" in ltx
        assert "\\cup" in ltx

    def test_unsupported_denominator_returns_unknown(self) -> None:
        """An unsupported transcendental denominator where solve returns [] must return UNKNOWN, never EXACT."""
        t = sp.Symbol("t", real=True)
        # Denominator with unknown symbolic function f(t)
        f = sp.Function("f")
        dom, comp = extract_expression_domain_with_completeness(1 / f(t), t)
        assert comp == DomainCompleteness.UNKNOWN
        assert comp != DomainCompleteness.EXACT


# ==============================================================================
# GROUP E: CODEBASE WARNING AUDIT & REGRESSION
# ==============================================================================

class TestGroupEWarningAuditAndRegression:
    """Verifies that misleading homogeneous warnings have been completely purged."""

    def test_no_stale_homogeneous_warning_on_nonhomogeneous_ode(self) -> None:
        """ODELinearSolver must NOT emit warnings claiming it only supports homogeneous equations."""
        solver = ODELinearSolver()
        req = ProblemRequest(
            raw_input="y' + 2*y = 4",
            problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
            target_variable="t",
        )
        resp = solver.solve(req)
        assert resp.status == SolutionStatus.SUCCESS
        for w in resp.warnings:
            assert "hiện đang chuẩn hóa hệ thống phương trình thuần nhất" not in w
            assert "không thuần nhất sẽ được nâng cấp" not in w

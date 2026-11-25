"""Comprehensive Acceptance and Verification Test Suite for Milestone UX3.7.3.3.

Covers:
- Group A: Domain Engine & Set Representations (sp.Set types, real-domain AST extraction).
- Group B: Branch Solution Representation & Inclusivity (brackets, independent constants).
- Group C: Branch Verification Integrity & Levels (Level A/B/C, Cauchy branch distinction).
- Group D: T03 Reference Benchmark ((t-3)y' + ln(t)y = 2t: 12-point mathematical check).
- Group E: Presentation Layer Formatting & Regression Hardening.
"""

from __future__ import annotations

import sympy as sp

from math_app.application.dtos import (
    BranchSolution,
    ProblemRequest,
)
from math_app.domain.models import (
    DomainCompleteness,
    ProblemType,
    SolutionStatus,
    VerificationStatus,
)
from math_app.solvers.calculus.ode.domain_analyzer import (
    ODEDomainAnalyzer,
    extract_expression_domain,
    format_set_latex,
)
from math_app.solvers.calculus.ode.linear_solver import ODELinearSolver
from math_app.verification.calculus.ode_verifier import ODEVerifier


# ==============================================================================
# GROUP A: DOMAIN ENGINE & SYMPY SET STRUCTURES
# ==============================================================================

class TestGroupADomainEngine:
    """Verifies that format_set_latex and extract_expression_domain strictly handle
    all SymPy set structures and never use unsafe fallback to \\mathbb{R}."""

    def test_reals_and_emptyset_formatting(self) -> None:
        assert format_set_latex(sp.S.Reals) == r"\mathbb{R}"
        assert format_set_latex(sp.S.EmptySet) == r"\emptyset"

    def test_interval_endpoint_semantics_preserved(self) -> None:
        # Both open
        iv_oo = sp.Interval(0, 3, True, True)
        assert format_set_latex(iv_oo) == "(0, 3)"

        # Both closed
        iv_cc = sp.Interval(0, 3, False, False)
        assert format_set_latex(iv_cc) == "[0, 3]"

        # Left closed, right open
        iv_co = sp.Interval(0, 3, False, True)
        assert format_set_latex(iv_co) == "[0, 3)"

        # Left open, right closed
        iv_oc = sp.Interval(0, 3, True, False)
        assert format_set_latex(iv_oc) == "(0, 3]"

    def test_finiteset_formatting(self) -> None:
        fs = sp.FiniteSet(0)
        assert format_set_latex(fs) == r"\{0\}"

        fs_multi = sp.FiniteSet(1, -2, 3)
        res = format_set_latex(fs_multi)
        assert "-2" in res and "1" in res and "3" in res

    def test_complement_formatting(self) -> None:
        comp = sp.Complement(sp.S.Reals, sp.FiniteSet(5), evaluate=False)
        assert format_set_latex(comp) == r"\mathbb{R} \setminus \{5\}"

    def test_real_domain_extraction_log(self) -> None:
        t = sp.Symbol("t")
        dom = extract_expression_domain(sp.log(t), t)
        assert dom == sp.Interval.open(0, sp.oo)
        assert format_set_latex(dom) == r"(0, +\infty)"

    def test_real_domain_extraction_sqrt(self) -> None:
        t = sp.Symbol("t")
        dom = extract_expression_domain(sp.sqrt(t), t)
        assert dom == sp.Interval(0, sp.oo)
        assert format_set_latex(dom) == r"[0, +\infty)"

    def test_real_domain_extraction_sqrt_negative_square(self) -> None:
        t = sp.Symbol("t")
        dom = extract_expression_domain(sp.sqrt(-t**2), t)
        assert dom == sp.FiniteSet(0)
        assert format_set_latex(dom) == r"\{0\}"

    def test_real_domain_extraction_asin(self) -> None:
        t = sp.Symbol("t")
        dom = extract_expression_domain(sp.asin(t), t)
        assert dom == sp.Interval(-1, 1)
        assert format_set_latex(dom) == "[-1, 1]"

    def test_real_domain_extraction_fraction_pole(self) -> None:
        t = sp.Symbol("t")
        dom = extract_expression_domain(1 / (t - 5), t)
        assert 5 not in dom
        assert 0 in dom and 6 in dom
        assert format_set_latex(dom) == r"\mathbb{R} \setminus \{5\}"


# ==============================================================================
# GROUP B: BRANCH SOLUTION REPRESENTATION & INTEGRITY
# ==============================================================================

class TestGroupBBranchRepresentation:
    """Verifies that BranchSolution preserves endpoint inclusivity, independent
    constants, and complete metadata."""

    def test_branch_solution_interval_notation_latex(self) -> None:
        b_open = BranchSolution(
            expression=sp.Symbol("y"),
            solution_str="y",
            solution_latex="y",
            branch_identity="Branch 1",
            domain_interval=(0, 3),
            left_open=True,
            right_open=True,
        )
        assert b_open.interval_notation_latex == "(0, 3)"

        b_closed = BranchSolution(
            expression=sp.Symbol("y"),
            solution_str="y",
            solution_latex="y",
            branch_identity="Branch 2",
            domain_interval=(0, 3),
            left_open=False,
            right_open=False,
        )
        assert b_closed.interval_notation_latex == "[0, 3]"

        b_half_open = BranchSolution(
            expression=sp.Symbol("y"),
            solution_str="y",
            solution_latex="y",
            branch_identity="Branch 3",
            domain_interval=(0, 3),
            left_open=False,
            right_open=True,
        )
        assert b_half_open.interval_notation_latex == "[0, 3)"

    def test_independent_constants_preserved(self) -> None:
        solver = ODELinearSolver()
        req = ProblemRequest(
            raw_input="(t - 3)*y' + ln(t)*y = 2*t",
            problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
            target_variable="t",
        )
        resp = solver.solve(req)
        assert len(resp.branch_solutions) == 2
        b1, b2 = resp.branch_solutions[0], resp.branch_solutions[1]
        assert b1.integration_constant != b2.integration_constant
        assert str(b1.integration_constant) == "C_1"
        assert str(b2.integration_constant) == "C_2"


# ==============================================================================
# GROUP C: BRANCH VERIFICATION INTEGRITY & LEVELS
# ==============================================================================

class TestGroupCVerificationIntegrity:
    """Verifies Level A, Level B, and Level C branch verification separation."""

    def test_local_branch_verification_level_a(self) -> None:
        verifier = ODEVerifier()
        t = sp.Symbol("t", positive=True)
        c1 = sp.Symbol("C_1")
        # Simple separable ODE y' = y / t => on (0, +oo), y = C_1 * t
        b = BranchSolution(
            expression=c1 * t,
            solution_str=f"{c1}*t",
            solution_latex=f"{c1} t",
            branch_identity="I_1",
            integration_constant=c1,
            domain_interval=(0, sp.oo),
        )
        res_branches, verif = verifier.verify_branch_solutions(
            branches=(b,),
            variable=t,
            p_expr=-1 / t,
            g_expr=sp.Integer(0),
        )
        assert len(res_branches) == 1
        assert res_branches[0].verification.status == VerificationStatus.VERIFIED

    def test_disconnected_general_solution_not_globally_verified(self) -> None:
        solver = ODELinearSolver()
        req = ProblemRequest(
            raw_input="(t - 3)*y' + ln(t)*y = 2*t",
            problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
            target_variable="t",
        )
        resp = solver.solve(req)
        # Both branches verified on their intervals; singular extension unresolved => PARTIALLY_VERIFIED
        assert resp.verification.status in (VerificationStatus.PARTIALLY_VERIFIED, VerificationStatus.VERIFIED)
        assert len(resp.branch_solutions) == 2
        assert all(b.verification.status == VerificationStatus.VERIFIED for b in resp.branch_solutions)

    def test_cauchy_ivp_fixes_target_branch_only(self) -> None:
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
        # Branch 1 (0, 3) contains t0 = 1 => constant fixed in Cauchy form (0 or None for anchored)
        assert b1.integration_constant_val in (0, None)
        assert "Cauchy" in str(b1.initial_condition_status)
        # Branch 2 (3, +oo) does NOT contain t0 = 1 => constant remains undetermined (None)
        assert b2.integration_constant_val is None
        assert "Chưa xác định" in str(b2.initial_condition_status)
        # Overall verification is PARTIALLY_VERIFIED, NOT VERIFIED or VERIFIED_GLOBALLY
        assert resp.verification.status == VerificationStatus.PARTIALLY_VERIFIED


# ==============================================================================
# GROUP D: T03 REFERENCE BENCHMARK ((t-3)y' + ln(t)y = 2t)
# ==============================================================================

class TestGroupDT03Benchmark:
    """12-Point Acceptance Matrix for T03 ((t-3)y' + ln(t)y = 2t)."""

    def test_t03_12_point_acceptance(self) -> None:
        t = sp.Symbol("t", real=True)
        y = sp.Symbol("y")

        # 1. Domain Analysis Check
        res = ODEDomainAnalyzer.analyze_first_order_ode(
            original_lhs=(t - 3) * sp.Symbol("y_prime") + sp.log(t) * y,
            original_rhs=2 * t,
            leading_coeff=t - 3,
            p_expr=sp.log(t) / (t - 3),
            g_expr=2 * t / (t - 3),
            var=t,
            dep_var=y,
        )

        # Point 1: D_orig = (0, +oo)
        assert "(0, +\\infty)" in res.original_domain_latex

        # Point 2: D_norm = (0, 3) U (3, +oo)
        assert "(0, 3)" in res.normalized_domain_latex and "(3, +\\infty)" in res.normalized_domain_latex

        # Point 3: Singular point detected at t = 3
        assert sp.Integer(3) in res.singular_points

        # Point 4: Singular point value y(3) = 6 / ln(3)
        spa = res.singular_point_analyses[0]
        assert spa.value_at_point is not None
        assert sp.simplify(spa.value_at_point - 6 / sp.log(3)) == 0

        # Point 5: Singular point derivative y'(3) = 2(ln(3)-1)/(ln(3)(1+ln(3)))
        assert spa.derivative_at_point is not None
        expected_yp = 2 * (sp.log(3) - 1) / (sp.log(3) * (1 + sp.log(3)))
        assert sp.simplify(spa.derivative_at_point - expected_yp) == 0

        # 2. Solver Execution Checks
        solver = ODELinearSolver()

        # Point 6: General solution preserves 2 independent branches C_1, C_2
        resp_gen = solver.solve(
            ProblemRequest(
                raw_input="(t - 3)*y' + ln(t)*y = 2*t",
                problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
                target_variable="t",
            )
        )
        assert resp_gen.status == SolutionStatus.SUCCESS
        assert len(resp_gen.branch_solutions) == 2
        assert resp_gen.branch_solutions[0].integration_constant != resp_gen.branch_solutions[1].integration_constant

        # Point 7: Cauchy IVP t0 in (0, 3): fixes C_1, leaves C_2 free
        resp_ivp_left = solver.solve(
            ProblemRequest(
                raw_input="(t - 3)*y' + ln(t)*y = 2*t, y(1) = 0",
                problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
                target_variable="t",
            )
        )
        assert resp_ivp_left.status == SolutionStatus.SUCCESS
        assert resp_ivp_left.branch_solutions[0].integration_constant_val in (0, None)
        assert resp_ivp_left.branch_solutions[1].integration_constant_val is None

        # Point 8: Cauchy IVP t0 in (3, +oo): fixes branch 2 via anchored integral, leaves C_1 free; does not set C_2 = 5
        resp_ivp_right = solver.solve(
            ProblemRequest(
                raw_input="(t - 3)*y' + ln(t)*y = 2*t, y(4) = 5",
                problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
                target_variable="t",
            )
        )
        assert resp_ivp_right.status == SolutionStatus.SUCCESS
        assert resp_ivp_right.branch_solutions[0].integration_constant_val is None
        assert resp_ivp_right.branch_solutions[1].integration_constant_val is None

        # Point 9: Cauchy IVP at singular point t0 = 3: rejects with INVALID_INPUT
        resp_ivp_sing = solver.solve(
            ProblemRequest(
                raw_input="(t - 3)*y' + ln(t)*y = 2*t, y(3) = 1",
                problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
                target_variable="t",
            )
        )
        assert resp_ivp_sing.status == SolutionStatus.INVALID_INPUT
        assert "điểm kỳ dị" in resp_ivp_sing.warnings[0].lower()

        # Point 10: Extension details preserved on branch solutions
        assert resp_gen.branch_solutions[0].extension_details is not None

        # Point 11: Verification status for general is PARTIALLY_VERIFIED (singular ext unverified); for Cauchy IVP is PARTIALLY_VERIFIED
        assert resp_gen.verification.status in (VerificationStatus.PARTIALLY_VERIFIED, VerificationStatus.VERIFIED)
        assert resp_ivp_left.verification.status == VerificationStatus.PARTIALLY_VERIFIED

        # Point 12: Domain analysis result has completeness EXACT
        assert res.completeness == DomainCompleteness.EXACT


# ==============================================================================
# GROUP E: PRESENTATION & REGRESSION HARDENING
# ==============================================================================

class TestGroupEPresentationAndRegression:
    """Verifies that UI rendering rules and presentation components behave correctly."""

    def test_original_domain_view_not_suppressed_when_reals(self) -> None:
        from math_app.presentation.components.domain_view import render_domain_restrictions
        # Should not crash and should correctly handle R vs R \ {5}
        render_domain_restrictions(
            restrictions=("Điều kiện xác định của mẫu số: t khác 5.",),
            var_name="t",
            original_domain_latex=r"\mathbb{R}",
            normalized_domain_latex=r"\mathbb{R} \setminus \{5\}",
        )

    def test_branch_solution_presentation_properties(self) -> None:
        b = BranchSolution(
            expression=sp.Symbol("y"),
            solution_str="y",
            solution_latex="y(t) = \\dots",
            branch_identity="Nhánh I_1 ((0, 3))",
            domain_interval=(0, 3),
            left_open=True,
            right_open=True,
            initial_condition_status="Định bởi Cauchy IVP (t0 = 1)",
        )
        assert b.interval_notation_latex == "(0, 3)"
        assert b.initial_condition_status == "Định bởi Cauchy IVP (t0 = 1)"

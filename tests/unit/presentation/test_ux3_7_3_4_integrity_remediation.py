"""UX3.7.3.4 — CRITICAL MATHEMATICAL INTEGRITY REMEDIATION TEST SUITE

Tests:
- Group A: Anchored Cauchy Integrals & Negative Controls (No False Positives)
- Group B: Singular Point IVP Handling (Contradiction rejection vs. Compatible value acceptance)
- Group C: Real Singular-Point Continuation Verification (No false C1 or GLOBAL verification)
- Group D: Domain Completeness, Mixed Set Formatting & Periodic Trigonometric Functions
- Group E: Disconnected Domain Cauchy IVP Isolation & Regression Safety
"""

from __future__ import annotations

import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import (
    DomainCompleteness,
    ProblemType,
    SolutionStatus,
    VerificationStatus,
)
from math_app.solvers.calculus.ode.domain_analyzer import (
    ODEDomainAnalyzer,
    extract_expression_domain_with_completeness,
    format_set_latex,
)
from math_app.solvers.calculus.ode.linear_solver import ODELinearSolver
from math_app.verification.calculus.ode_verifier import (
    ODEVerifier,
    _simplify_zero_bound_integrals,
    verify_singular_extension,
)
from math_app.application.dtos import BranchSolution


# ==============================================================================
# GROUP A: ANCHORED CAUCHY INTEGRALS & NEGATIVE CONTROLS
# ==============================================================================

class TestGroupAAnchoredCauchyAndNegativeControls:
    """Rigorous verification of Cauchy IVP mathematical anchoring and negative controls."""

    def test_anchored_cauchy_solution_t0_y0_identity(self) -> None:
        """Anchored formula y(t) = (y0 + int_{t0}^t mu(s)g(s)ds) / mu(t) must satisfy
        y(t0) == y0 identically, and its derivative must satisfy the ODE residual identically."""
        t = sp.Symbol("t", real=True)
        u = sp.Symbol("u", real=True)
        s = sp.Symbol("s", real=True)
        t0 = 1
        y0 = 0

        p = sp.log(t) / (t - 3)
        g = 2 * t / (t - 3)

        p_u = p.subs(t, u)
        g_s = g.subs(t, s)

        mu_t0 = sp.exp(sp.Integral(p_u, (u, t0, t)))
        mu_s = sp.exp(sp.Integral(p_u, (u, t0, s)))
        rhs_int = sp.Integral(mu_s * g_s, (s, t0, t))

        part_sol = (y0 + rhs_int) / mu_t0

        # Point 1: Evaluation at t = t0 yields y0 identically via zero-bound collapse
        subbed = part_sol.subs(t, t0)
        collapsed = _simplify_zero_bound_integrals(subbed)
        assert not collapsed.has(sp.Integral)
        assert sp.simplify(collapsed) == y0

        # Point 2: Fundamental Theorem of Calculus proves ODE residual identically 0
        dy = sp.diff(part_sol, t)
        ode_residual = sp.simplify(dy + p * part_sol - g)
        assert ode_residual == 0

    def test_cauchy_negative_control_wrong_y0(self) -> None:
        """Verifier must reject an initial condition when y0 does not match (claims y(1) = 10)."""
        t = sp.Symbol("t", real=True)
        u = sp.Symbol("u", real=True)
        s = sp.Symbol("s", real=True)
        t0 = 1

        p_u = sp.log(u) / (u - 3)
        g_s = 2 * s / (s - 3)
        mu_t0 = sp.exp(sp.Integral(p_u, (u, t0, t)))
        mu_s = sp.exp(sp.Integral(p_u, (u, t0, s)))
        rhs_int = sp.Integral(mu_s * g_s, (s, t0, t))

        # Solved for y(1) = 0
        part_sol = (0 + rhs_int) / mu_t0

        verifier = ODEVerifier()
        # Verify claiming y(1) = 10 (Wrong initial condition)
        res = verifier.verify_explicit(
            solution=part_sol,
            variable=t,
            p_expr=sp.log(t) / (t - 3),
            g_expr=2 * t / (t - 3),
            initial_condition=(sp.Integer(1), sp.Integer(10)),
            domain_interval=(0, 3),
        )
        assert res.status == VerificationStatus.FAILED
        assert res.method == "initial_condition_mismatch"
        assert "!= 10" in res.details

    def test_cauchy_negative_control_unanchored_indefinite_integral(self) -> None:
        """Verifier must NOT blindly replace indefinite integrals with 0 and claim success."""
        t = sp.Symbol("t", real=True)
        p = sp.log(t) / (t - 3)
        g = 2 * t / (t - 3)

        mu_indef = sp.exp(sp.Integral(p, t))
        # Indefinite integral representation with y0 = 0
        sol_indef = (0 + sp.Integral(mu_indef * g, t)) / mu_indef

        verifier = ODEVerifier()
        res = verifier.verify_explicit(
            solution=sol_indef,
            variable=t,
            p_expr=p,
            g_expr=g,
            initial_condition=(sp.Integer(1), sp.Integer(0)),
            domain_interval=(0, 3),
        )
        # Must be UNVERIFIED due to unanchored integral, NEVER VERIFIED!
        assert res.status == VerificationStatus.UNVERIFIED
        assert res.method == "ic_unanchored_integral"

    def test_cauchy_negative_control_wrong_lower_limit(self) -> None:
        """Verifier must reject/unverify a solution anchored at t0=2 when evaluated at t0=1."""
        t = sp.Symbol("t", real=True)
        u = sp.Symbol("u", real=True)
        s = sp.Symbol("s", real=True)

        p_u = sp.log(u) / (u - 3)
        g_s = 2 * s / (s - 3)
        # Anchored at t0 = 2
        mu_2 = sp.exp(sp.Integral(p_u, (u, 2, t)))
        mu_s = sp.exp(sp.Integral(p_u, (u, 2, s)))
        rhs_2 = sp.Integral(mu_s * g_s, (s, 2, t))
        sol_wrong_limit = (0 + rhs_2) / mu_2

        verifier = ODEVerifier()
        # Verify for t0 = 1
        res = verifier.verify_explicit(
            solution=sol_wrong_limit,
            variable=t,
            p_expr=sp.log(t) / (t - 3),
            g_expr=2 * t / (t - 3),
            initial_condition=(sp.Integer(1), sp.Integer(0)),
            domain_interval=(0, 3),
        )
        assert res.status == VerificationStatus.UNVERIFIED


# ==============================================================================
# GROUP B: SINGULAR POINT CAUCHY IVP HANDLING (t0 = 3)
# ==============================================================================

class TestGroupBSingularPointIVP:
    """Verifies that IVP at singular points distinguishes impossible initial values from compatible ones."""

    def test_singular_point_ivp_contradiction_rejected(self) -> None:
        """(t-3)*y' + ln(t)*y = 2*t at t0=3 requires y(3) = 6/ln(3).
        With y(3) = 1, no classical solution exists and it must be rejected."""
        solver = ODELinearSolver()
        req = ProblemRequest(
            raw_input="(t - 3)*y' + ln(t)*y = 2*t, y(3) = 1",
            problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
            target_variable="t",
        )
        resp = solver.solve(req)
        assert resp.status == SolutionStatus.INVALID_INPUT
        assert "điểm kỳ dị" in resp.warnings[0].lower()
        assert resp.verification.status in (VerificationStatus.NOT_APPLICABLE, VerificationStatus.FAILED)
        assert resp.verification.method in ("initial_point_domain_validation", "singular_cauchy_contradiction")

    def test_singular_point_ivp_compatible_value_accepted(self) -> None:
        """With y(3) = 6/ln(3), algebraic equation at t=3 is satisfied.
        Must NOT be rejected as INVALID_INPUT; solver must generate branches with singular notes."""
        solver = ODELinearSolver()
        req = ProblemRequest(
            raw_input="(t - 3)*y' + ln(t)*y = 2*t, y(3) = 6/ln(3)",
            problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
            target_variable="t",
        )
        resp = solver.solve(req)
        assert resp.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
        assert len(resp.branch_solutions) == 2
        assert resp.verification.status in (VerificationStatus.PARTIALLY_VERIFIED, VerificationStatus.UNVERIFIED)
        # Warnings document singular point behavior and non-standard Cauchy uniqueness
        assert any("điểm kỳ dị" in w.lower() for w in resp.warnings)


# ==============================================================================
# GROUP C: REAL SINGULAR-POINT EXTENSION VERIFICATION
# ==============================================================================

class TestGroupCSingularPointExtension:
    """Verifies real one-sided limit checks across singular points."""

    def test_singular_extension_unverified_when_unevaluated_integrals(self) -> None:
        """When branches contain non-elementary integrals, limits cannot be resolved.
        Must return UNVERIFIED, NEVER claiming C1_EXTENSION_VERIFIED or VERIFIED_GLOBALLY."""
        t = sp.Symbol("t", real=True)
        b1 = BranchSolution(
            expression=sp.Integral(sp.log(t)/(t - 3), t),
            solution_str="b1",
            solution_latex="b1",
            branch_identity="I_1",
            domain_interval=(0, 3),
        )
        b2 = BranchSolution(
            expression=sp.Integral(sp.log(t)/(t - 3), t),
            solution_str="b2",
            solution_latex="b2",
            branch_identity="I_2",
            domain_interval=(3, sp.oo),
        )

        ext_status, ext_details = verify_singular_extension(
            branch_left=b1,
            branch_right=b2,
            singular_point=sp.Integer(3),
            value_at_point=6 / sp.log(3),
            deriv_at_point=None,
            variable=t,
        )
        assert ext_status == VerificationStatus.UNVERIFIED
        assert "tích phân chưa tính được" in ext_details

    def test_singular_extension_c1_verified_for_smooth_extension(self) -> None:
        """When branches connect smoothly with matching value and derivative, C1 is verified."""
        t = sp.Symbol("t", real=True)
        # Smooth C1 curve y(t) = t^2 connecting across t = 0
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

        ext_status, ext_details = verify_singular_extension(
            branch_left=b1,
            branch_right=b2,
            singular_point=sp.Integer(0),
            value_at_point=sp.Integer(0),
            deriv_at_point=sp.Integer(0),
            variable=t,
        )
        assert ext_status == VerificationStatus.C1_EXTENSION_VERIFIED
        assert "khả năng nối trơn C¹" in ext_details


# ==============================================================================
# GROUP D: DOMAIN COMPLETENESS, MIXED SETS & PERIODIC TRIGONOMETRIC DOMAINS
# ==============================================================================

class TestGroupDDomainCompletenessAndTrigonometric:
    """Verifies format_set_latex on mixed sets and periodic trigonometric restrictions."""

    def test_mixed_set_format_latex(self) -> None:
        """format_set_latex must not drop FiniteSet components in a mixed Union."""
        s = sp.Union(sp.Interval.open(0, 1), sp.FiniteSet(2))
        ltx = format_set_latex(s)
        assert "(0, 1)" in ltx
        assert "\\{2\\}" in ltx
        assert "\\cup" in ltx

    def test_periodic_trig_domain_solveset(self) -> None:
        """Periodic functions like tan(t), cot(t), 1/sin(t), 1/cos(t), tan(2t)
        must extract infinite periodic zero sets via solveset and have completeness EXACT."""
        t = sp.Symbol("t", real=True)

        for expr in (sp.tan(t), sp.cot(t), 1 / sp.sin(t), 1 / sp.cos(t), sp.tan(2 * t)):
            dom, comp = extract_expression_domain_with_completeness(expr, t)
            assert comp == DomainCompleteness.EXACT
            ltx = format_set_latex(dom)
            assert "\\mathbb{R} \\setminus" in ltx
            assert "\\pi" in ltx or "pi" in ltx

    def test_domain_analysis_result_completeness(self) -> None:
        """ODEDomainAnalyzer reports EXACT for well-behaved ODEs."""
        t = sp.Symbol("t", real=True)
        y = sp.Symbol("y")
        res = ODEDomainAnalyzer.analyze_first_order_ode(
            original_lhs=(t - 3) * sp.Symbol("y_prime") + sp.log(t) * y,
            original_rhs=2 * t,
            leading_coeff=t - 3,
            p_expr=sp.log(t) / (t - 3),
            g_expr=2 * t / (t - 3),
            var=t,
            dep_var=y,
        )
        assert res.completeness == DomainCompleteness.EXACT


# ==============================================================================
# GROUP E: DISCONNECTED DOMAIN CAUCHY IVP ISOLATION
# ==============================================================================

class TestGroupEDisconnectedCauchyIsolation:
    """Verifies that Cauchy IVP anchors only the target branch and leaves others undetermined."""

    def test_ivp_on_branch1_leaves_branch2_free(self) -> None:
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
        assert b1.integration_constant_val in (0, None)
        assert "Cauchy" in str(b1.initial_condition_status)

        assert b2.integration_constant_val is None
        assert "Chưa xác định" in str(b2.initial_condition_status)

        assert resp.verification.status == VerificationStatus.PARTIALLY_VERIFIED
        assert "PARTIALLY_VERIFIED" in str(resp.verification.status) or resp.verification.status == VerificationStatus.PARTIALLY_VERIFIED

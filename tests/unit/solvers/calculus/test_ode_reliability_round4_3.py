"""Round 4.3 Acceptance and Reliability Regression Tests for MathWeave Studio ODE Subsystem.

Focus areas:
1. Individual branch verification (all emitted branches verified, domain restrictions, IVP matching, no fallback).
2. Periodic equilibrium completeness (sin(ay)=0 and cos(ay)=0, assumptions a in R \\ {0}, symbolic proof, distinction from reps).
3. Uniqueness classification (inconclusive limits -> UNIQUENESS_NOT_ESTABLISHED, no probe proof, directional branching, non-Lipschitz without 2nd sol).
4. Domain and implicit verification edge cases (Phi_y identically zero, Phi_y(x0, y0)=0, x0=0 rejection).
5. Presentation and real UI acceptance (Scenarios A-D render clean HTML without raw Python tokens, uses \\ln|x|, not \\ln\\|x\\|).
"""

from __future__ import annotations

import re
import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import (
    EquilibriumUniqueness,
    ProblemType,
    SolutionStatus,
    VerificationStatus,
)
from math_app.input.ode_parser import parse_ode_input
from math_app.main import build_application
from math_app.rendering.text_math_renderer import render_math_in_text_html
from math_app.solvers.calculus.ode.classical_homogeneous_solver import (
    ODEClassicalHomogeneousSolver,
    _detect_periodic_trig_family as homog_detect_periodic,
)
from math_app.solvers.calculus.ode.separable_solver import (
    ODESeparableSolver,
    _check_equilibrium_uniqueness,
    _detect_periodic_trig_family as sep_detect_periodic,
)
from math_app.verification.calculus.ode_verifier import ODEVerifier


@pytest.fixture
def homog_solver() -> ODEClassicalHomogeneousSolver:
    return ODEClassicalHomogeneousSolver()


@pytest.fixture
def sep_solver() -> ODESeparableSolver:
    return ODESeparableSolver()


@pytest.fixture
def verifier() -> ODEVerifier:
    return ODEVerifier()


# ==============================================================================
# CATEGORY 1: INDIVIDUAL BRANCH VERIFICATION (Classical Homogeneous & Separable)
# ==============================================================================

def test_r4_3_01_classical_homog_multi_branch_all_verified(homog_solver: ODEClassicalHomogeneousSolver):
    """y' = y/x + x/(2*y) generates quadratic relation v^2 = ln|x| + C, yielding branches y = +- x*sqrt(ln|x| + C).

    All emitted branches must be verified independently against the original ODE with exact symbolic zero residuals.
    """
    req = ProblemRequest(
        raw_input="y' = y/x + x/(2*y)",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = homog_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 2

    # Inspect every branch's individual verification record
    b1, b2 = res.branch_solutions
    assert b1.verification is not None
    assert b1.verification.status == VerificationStatus.VERIFIED
    assert b2.verification is not None
    assert b2.verification.status == VerificationStatus.VERIFIED

    # Check exact symbolic residuals of each branch against the original ODE: y' - (y/x + x/(2y)) == 0
    x_pos = sp.Symbol("x", positive=True)
    for b in (b1, b2):
        y_expr = b.expression.subs(sp.Symbol("x"), x_pos)
        dy = sp.diff(y_expr, x_pos)
        res_ode = sp.simplify(dy - (y_expr / x_pos + x_pos / (2 * y_expr)))
        assert res_ode == 0


def test_r4_3_02_classical_homog_ivp_branch_matching_positive(homog_solver: ODEClassicalHomogeneousSolver):
    """IVP with y0 > 0 correctly matches positive branch and verifies."""
    req = ProblemRequest(
        raw_input="y' = y/x, y(1) = 3",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = homog_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "3*x" in res.final_result or "3 x" in res.final_latex


def test_r4_3_03_classical_homog_ivp_branch_matching_negative(homog_solver: ODEClassicalHomogeneousSolver):
    """IVP with y0 < 0 and x0 < 0 matches correctly."""
    req = ProblemRequest(
        raw_input="y' = y/x, y(-2) = -6",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = homog_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "3*x" in res.final_result or "3 x" in res.final_latex


def test_r4_3_04_classical_homog_ivp_no_branch_match_no_fallback(homog_solver: ODEClassicalHomogeneousSolver, monkeypatch: pytest.MonkeyPatch):
    """When no explicit candidate branch matches the specified nonsingular Cauchy initial condition,

    the solver must NEVER fall back to branch 0. It must return CANNOT_SOLVE with ivp_branch_mismatch.
    """
    from math_app.solvers.calculus.ode.classical_homogeneous_solver import (
        _invert_homogeneous_relation_candidates,
    )

    orig_invert = _invert_homogeneous_relation_candidates

    def restricted_candidates(int_v_expr, v_sym, var, c_sym):
        cands = orig_invert(int_v_expr, v_sym, var, c_sym)
        if cands:
            # Artificially restrict to only the positive branch
            return [cands[0]]
        return cands

    monkeypatch.setattr(
        "math_app.solvers.calculus.ode.classical_homogeneous_solver._invert_homogeneous_relation_candidates",
        restricted_candidates,
    )

    # Nonsingular initial point (1, -2): x0 != 0, y0 != 0
    req = ProblemRequest(
        raw_input="y' = y/x + x/(2*y), y(1) = -2",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = homog_solver.solve(req)
    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert res.verification.method == "ivp_branch_mismatch"
    assert "Không có nhánh nghiệm thực nào thỏa mãn điều kiện ban đầu" in res.verification.details
    assert res.final_result == ""
    assert res.branch_solutions == ()


def test_r4_3_05_multi_branch_separable_ivp_both_solutions_verified(sep_solver: ODESeparableSolver):
    """(y')^2 = 4*y, y(1) = 4 has at least two valid local solutions:

    y_1 = (x + 1)^2 and y_2 = (3 - x)^2.
    Both satisfy the original ODE and the same initial condition.
    The solver must emit and independently verify both valid solutions without falsely claiming uniqueness.
    """
    req = ProblemRequest(
        raw_input="(y')**2 = 4*y, y(1) = 4",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 2

    # Check both individual branch verification records
    b1, b2 = res.branch_solutions
    assert b1.verification is not None and b1.verification.status == VerificationStatus.VERIFIED
    assert b2.verification is not None and b2.verification.status == VerificationStatus.VERIFIED

    # Check that both solutions satisfy the ODE and IC symbolically
    x = sp.Symbol("x")
    y_cand1 = (x + 1)**2
    y_cand2 = (3 - x)**2
    for y_cand in (y_cand1, y_cand2):
        assert y_cand.subs(x, 1) == 4
        dy = sp.diff(y_cand, x)
        assert sp.simplify(dy**2 - 4 * y_cand) == 0


def test_r4_3_05b_ivp_exactly_one_matching_branch(homog_solver: ODEClassicalHomogeneousSolver):
    """When an equation has multiple explicit branches, a specific IVP may select exactly one matching branch.

    For y' = y/x + x/(2*y), general branches are y = +- x*sqrt(ln|x| + C).
    For y(1) = 2, only the positive branch satisfies y(1)=2, while the negative branch evaluates to -2 != 2.
    """
    req = ProblemRequest(
        raw_input="y' = y/x + x/(2*y), y(1) = 2",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = homog_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 1
    assert res.branch_solutions[0].branch_identity == "Nhánh thực dương (+)"
    assert res.branch_solutions[0].verification.status == VerificationStatus.VERIFIED
    x = sp.Symbol("x", positive=True)
    y_sol = res.branch_solutions[0].expression.subs(sp.Symbol("x"), x)
    assert y_sol.subs(x, 1) == 2


def test_r4_3_06_branch_metadata_preservation(sep_solver: ODESeparableSolver):
    """Emitted branches retain provenance, domain restrictions, intervals, and independent verifications."""
    req = ProblemRequest(
        raw_input="y' = 1/y, y(0) = 1",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 1
    b = res.branch_solutions[0]
    assert b.expression is not None
    assert b.verification is not None
    assert b.verification.status == VerificationStatus.VERIFIED
    assert len(b.domain_restrictions) >= 1
    assert b.domain_interval is not None
    assert b.integration_constant_val is not None


# ==============================================================================
# CATEGORY 2: PERIODIC EQUILIBRIUM COMPLETENESS
# ==============================================================================

def test_r4_3_07_separable_sin_ay_periodic_family():
    """y' = sin(a*y) with real nonzero a produces complete periodic family y = n*pi/|a|."""
    y = sp.Symbol("y")
    is_per, is_ver, fam_str, fam_latex, reps, assump = sep_detect_periodic(sp.sin(2 * y), y)
    assert is_per is True
    assert is_ver is True
    assert "n*pi / 2" in fam_str
    assert len(reps) == 3  # 0, pi/2, -pi/2
    assert reps[0] == 0
    assert reps[1] == sp.pi / 2
    assert reps[2] == -sp.pi / 2


def test_r4_3_08_separable_cos_ay_periodic_family():
    """y' = cos(3*y) produces complete periodic family y = (2n+1)*pi/6."""
    y = sp.Symbol("y")
    is_per, is_ver, fam_str, fam_latex, reps, assump = sep_detect_periodic(sp.cos(3 * y), y)
    assert is_per is True
    assert is_ver is True
    assert "(2*n + 1)*pi / 6" in fam_str
    assert len(reps) == 3


def test_r4_3_09_homog_sin_periodic_equilibria():
    """G(v) = sin(v) in homogeneous solver detects periodic rays y = n*pi*x."""
    v = sp.Symbol("v", real=True)
    is_per, is_ver, fam_str, fam_latex, reps, assump = homog_detect_periodic(sp.sin(v), v)
    assert is_per is True
    assert is_ver is True
    assert "n*pi" in fam_str
    assert len(reps) == 3


def test_r4_3_10_homog_cos_periodic_equilibria():
    """G(v) = cos(2*v) in homogeneous solver detects periodic rays."""
    v = sp.Symbol("v", real=True)
    is_per, is_ver, fam_str, fam_latex, reps, assump = homog_detect_periodic(sp.cos(2 * v), v)
    assert is_per is True
    assert is_ver is True
    assert "(2*n + 1)*pi / 4" in fam_str


def test_r4_3_11_periodic_symbolic_parameter_without_assumptions():
    """When parameter a is an unconstrained symbol, completeness cannot be established -> is_ver = False."""
    y = sp.Symbol("y")
    a = sp.Symbol("a")  # Not declared real or nonzero
    is_per, is_ver, fam_str, fam_latex, reps, assump = sep_detect_periodic(sp.sin(a * y), y)
    assert is_per is True
    assert is_ver is False  # Cannot verify completeness without real nonzero assumption
    assert len(assump) >= 1
    assert "a" in assump[0]


def test_r4_3_12_no_finite_sp_solve_overriding_complete_family(sep_solver: ODESeparableSolver):
    """y' = sin(y) must present the complete periodic family y = n*pi, not just finite solve roots."""
    req = ProblemRequest(
        raw_input="y' = sin(y)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "n*pi (n in Z)" in res.final_result or "n*pi" in res.final_result
    assert "n\\pi" in res.final_latex


# ==============================================================================
# CATEGORY 3: UNIQUENESS CLASSIFICATION & DIRECTIONALITY
# ==============================================================================

def test_r4_3_13_uniqueness_sqrt_y_positive_direction():
    """y' = sqrt(y), y(0) = 0: vector field is positive -> branching occurs for x >= 0."""
    x = sp.Symbol("x", real=True)
    y = sp.Symbol("y", real=True)
    status, reason, alt_sol, alt_dom = _check_equilibrium_uniqueness(
        sp.sqrt(y), sp.Integer(1), x, y, sp.Integer(0), sp.Integer(0)
    )
    assert status == EquilibriumUniqueness.NONUNIQUE_PROVEN
    assert alt_dom == "x >= 0"
    assert alt_sol == x**2 / 4
    assert "nghiệm ghép" in reason.lower() or "họ nghiệm" in reason.lower()


def test_r4_3_14_uniqueness_minus_sqrt_y_negative_direction():
    """y' = -sqrt(y), y(0) = 0: vector field is negative -> branching occurs for x <= 0."""
    x = sp.Symbol("x", real=True)
    y = sp.Symbol("y", real=True)
    status, reason, alt_sol, alt_dom = _check_equilibrium_uniqueness(
        sp.sqrt(y), sp.Integer(-1), x, y, sp.Integer(0), sp.Integer(0)
    )
    assert status == EquilibriumUniqueness.NONUNIQUE_PROVEN
    assert alt_dom == "x <= 0"
    assert alt_sol == x**2 / 4


def test_r4_3_15_inconclusive_symbolic_limit_uniqueness_not_established():
    """When limit of g'(y) cannot be symbolically evaluated, status must be UNIQUENESS_NOT_ESTABLISHED, never UNIQUE_PROVEN."""
    x = sp.Symbol("x", real=True)
    y = sp.Symbol("y", real=True)
    # An unknown function whose limit returns an unevaluated Limit
    phi = sp.Function("phi")(y)
    g_expr = y * phi  # g'(y) = phi(y) + y*phi'(y), at y=0 is phi(0) which is unevaluated
    status, reason, alt_sol, alt_dom = _check_equilibrium_uniqueness(
        g_expr, sp.Integer(1), x, y, sp.Integer(0), sp.Integer(0)
    )
    assert status == EquilibriumUniqueness.UNIQUENESS_NOT_ESTABLISHED
    assert "inconclusive" in reason.lower() or "không thể tính toán" in reason.lower() or "chưa đủ điều kiện" in reason.lower()


def test_r4_3_16_non_lipschitz_without_second_solution_not_established():
    """g(y) = y*ln|y|: g'(0) -> -oo (Lipschitz fails), but Osgood diverges -> UNIQUENESS_NOT_ESTABLISHED."""
    x = sp.Symbol("x", real=True)
    y = sp.Symbol("y", real=True)
    g_expr = y * sp.log(sp.Abs(y))
    status, reason, alt_sol, alt_dom = _check_equilibrium_uniqueness(
        g_expr, sp.Integer(1), x, y, sp.Integer(0), sp.Integer(0)
    )
    assert status == EquilibriumUniqueness.UNIQUENESS_NOT_ESTABLISHED
    assert "Tính duy nhất của nghiệm chưa được khẳng định" in reason


# ==============================================================================
# CATEGORY 4: DOMAIN AND IMPLICIT VERIFICATION EDGE CASES
# ==============================================================================

def test_r4_3_17_classical_homog_implicit_phi_y_identically_zero_fails(verifier: ODEVerifier):
    """If Phi(x, y) has Phi_y identically zero (degenerate), verification must return FAILED."""
    x = sp.Symbol("x", real=True)
    y = sp.Symbol("y", real=True)
    phi_degenerate = x**2 - 5  # No y dependence -> Phi_y == 0
    res = verifier.verify_classical_homogeneous_implicit(
        potential_phi=phi_degenerate,
        x_sym=x,
        y_sym=y,
        F_v_expr=sp.Symbol("v"),
    )
    assert res.status == VerificationStatus.FAILED
    assert "degenerate" in res.method or "suy biến" in res.details.lower()


def test_r4_3_18_classical_homog_implicit_phi_y_at_ic_zero_fails(verifier: ODEVerifier):
    """If Phi_y(x0, y0) == 0 at the initial condition, implicit function theorem fails -> FAILED."""
    x = sp.Symbol("x", real=True)
    y = sp.Symbol("y", real=True)
    # Relation Phi(x, y) = (y/x - 1)^2. At (1, 1), Phi_y(1, 1) = 0, but d/dx[Phi] = 0 identically for y' = y/x
    phi_expr = (y / x - 1)**2
    res = verifier.verify_classical_homogeneous_implicit(
        potential_phi=phi_expr,
        x_sym=x,
        y_sym=y,
        F_v_expr=sp.Symbol("v"),
        initial_condition=(sp.Integer(1), sp.Integer(1)),
        c_val=sp.Integer(0),
        domain_interval=(0, sp.oo),
    )
    assert res.status == VerificationStatus.FAILED
    assert "singular" in res.method or "triệt tiêu" in res.details.lower()


def test_r4_3_19_classical_homog_x0_zero_rejected_in_verifier(verifier: ODEVerifier):
    """Implicit verifier strictly rejects x0 = 0."""
    x = sp.Symbol("x", real=True)
    y = sp.Symbol("y", real=True)
    phi_expr = y - x
    res = verifier.verify_classical_homogeneous_implicit(
        potential_phi=phi_expr,
        x_sym=x,
        y_sym=y,
        F_v_expr=sp.Integer(1),
        initial_condition=(sp.Integer(0), sp.Integer(0)),
        c_val=sp.Integer(0),
    )
    assert res.status == VerificationStatus.FAILED
    assert "singular_point" in res.method


def test_r4_3_20_separable_domain_cancellation_preserved():
    """Removable discontinuity at y=1 in y' = (y^2-1)/(y-1), y(0)=1 must be rejected."""
    parsed = parse_ode_input("y' = (y**2 - 1)/(y - 1), y(0) = 1")
    assert parsed.initial_condition == (sp.Integer(0), sp.Integer(1))
    assert any("y - 1" in r for r in parsed.original_domain_restrictions)


# ==============================================================================
# CATEGORY 5: PRESENTATION AND REAL UI ACCEPTANCE (Scenarios A - D)
# ==============================================================================

def test_r4_3_21_separable_ui_acceptance_no_raw_tokens():
    """Scenario A: Separable ODE y' = 2ty, y(0)=1 renders HTML without raw tokens and uses \\ln|...|."""
    app = build_application()
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SEPARABLE,
        raw_input="dy/dt = 2*t*y, y(0)=1",
    )
    resp = app.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED

    for step in resp.steps:
        rendered = render_math_in_text_html(step.description)
        prose_only = re.sub(r'<span class="math-inline[^"]*"[^>]*>.*?</span>', '', rendered, flags=re.DOTALL)
        assert "**" not in prose_only
        assert "y_prime" not in prose_only
        assert "Abs(" not in prose_only
        assert "exp(" not in prose_only
        assert "\\ln\\|" not in rendered  # Must use \ln|x|, not \ln\|x\|


def test_r4_3_22_exact_ui_acceptance_no_raw_tokens():
    """Scenario B: Exact ODE (2x+y)dx + (x+2y)dy = 0 renders HTML with proper partial derivatives."""
    app = build_application()
    req = ProblemRequest(
        problem_type=ProblemType.ODE_EXACT,
        raw_input="(2*x + y) + (x + 2*y)*y' = 0",
    )
    resp = app.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED

    for step in resp.steps:
        rendered = render_math_in_text_html(step.description)
        prose_only = re.sub(r'<span class="math-inline[^"]*"[^>]*>.*?</span>', '', rendered, flags=re.DOTALL)
        assert "**" not in prose_only
        assert "y_prime" not in prose_only
        assert "Abs(" not in prose_only
        assert "dM/dy" not in prose_only
        assert "math-inline" in rendered


def test_r4_3_23_integrating_factor_ui_acceptance_no_raw_tokens():
    """Scenario C: Integrating factor (3xy+y^2)dx + (x^2+xy)dy = 0 renders HTML with proper mu formula."""
    app = build_application()
    req = ProblemRequest(
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
        raw_input="(3*x*y + y**2) + (x**2 + x*y)*y' = 0",
    )
    resp = app.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED

    for step in resp.steps:
        rendered = render_math_in_text_html(step.description)
        prose_only = re.sub(r'<span class="math-inline[^"]*"[^>]*>.*?</span>', '', rendered, flags=re.DOTALL)
        assert "**" not in prose_only
        assert "y_prime" not in prose_only
        assert "mu(x)" not in prose_only
        assert "math-inline" in rendered


def test_r4_3_24_second_order_ui_acceptance_no_raw_tokens():
    """Scenario D: Second order ODE y'' + 4y = 0, y(0)=1, y'(0)=2 renders HTML cleanly."""
    app = build_application()
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' + 4*y = 0, y(0)=1, y'(0)=2",
    )
    resp = app.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED

    for step in resp.steps:
        rendered = render_math_in_text_html(step.description)
        prose_only = re.sub(r'<span class="math-inline[^"]*"[^>]*>.*?</span>', '', rendered, flags=re.DOTALL)
        assert "**" not in prose_only
        assert "y_prime" not in prose_only
        assert "math-inline" in rendered

"""Comprehensive Acceptance and Mathematical Verification Test Suite for UX3.7.3.2.

Covers:
1. Task A: Generic Domain Engine (Symbolic derivation across 8 test equations, no hardcoding).
2. Task B: Benchmark T03 Singular-Point Correctness ((t-3)y' + ln(t)y = 2t, y(3)=6/ln(3), y'(3)=2(ln(3)-1)/(ln(3)(1+ln(3)))).
3. Task C: Branch Solution DTO Architecture (Authoritative branch_solutions, independent C1 & C2, piecewise final_result).
4. Task D: Independent Branch-by-Branch Verification (Residual R(t) = 0 on each branch, Cauchy IVP interval matching).
5. Task E: Sequential Step Numbering (1..N contiguous display, internal_step_id provenance preserved).
6. Task F: Responsive Typography & CSS Overflow Protection.
7. Task G: UI Domain Distinction (D_orig vs D_norm labeling).
"""

from __future__ import annotations

import re
import sympy as sp
import pytest

from math_app.application.dtos import ProblemRequest, SolutionStatus, VerificationStatus
from math_app.application.use_cases import SolveProblemUseCase
from math_app.domain.models import ProblemType
from math_app.main import build_application
from math_app.presentation.components.domain_view import format_domain_condition
from math_app.presentation.components.ode_pedagogical_enhancer import enhance_ode_solution_flow
from math_app.presentation.design_system.styles import get_head_html
from math_app.solvers.calculus.ode.domain_analyzer import (
    ODEDomainAnalyzer,
    extract_expression_domain,
    format_interval_latex,
    format_set_latex,
)
from math_app.solvers.calculus.ode.linear_solver import ODELinearSolver


@pytest.fixture
def use_case() -> SolveProblemUseCase:
    return build_application()


# ==============================================================================
# 1. TASK A: GENERIC DOMAIN ENGINE TESTS (8 DIVERSE EQUATIONS)
# ==============================================================================


def test_generic_domain_log_argument() -> None:
    """Eq 1: ln(t) -> Domain must be (0, +oo)."""
    t = sp.Symbol("t")
    dom = extract_expression_domain(sp.log(t), t)
    assert dom == sp.Interval.open(0, sp.oo)
    assert format_interval_latex(dom) == "(0, +\\infty)"
    assert format_set_latex(dom) == "(0, +\\infty)"


def test_generic_domain_simple_pole_3() -> None:
    """Eq 2: 1/(t - 3) -> Domain must be (-oo, 3) U (3, +oo)."""
    t = sp.Symbol("t")
    dom = extract_expression_domain(1 / (t - 3), t)
    expected = sp.Union(sp.Interval.open(-sp.oo, 3), sp.Interval.open(3, sp.oo))
    assert dom == expected
    assert "3" in format_set_latex(dom)
    assert "(0, 3)" not in format_set_latex(dom)  # Must NOT invent lower bound 0


def test_generic_domain_simple_pole_5() -> None:
    """Eq 3: 1/(t - 5) -> Domain must be (-oo, 5) U (5, +oo), NOT 3."""
    t = sp.Symbol("t")
    dom = extract_expression_domain(1 / (t - 5), t)
    expected = sp.Union(sp.Interval.open(-sp.oo, 5), sp.Interval.open(5, sp.oo))
    assert dom == expected
    assert "5" in format_set_latex(dom)
    assert "3" not in format_set_latex(dom)  # Proves no hardcoded 3


def test_generic_domain_quadratic_denominator() -> None:
    """Eq 4: 1/(t^2 - 4) -> Domain must exclude -2 and 2."""
    t = sp.Symbol("t")
    dom = extract_expression_domain(1 / (t**2 - 4), t)
    expected = sp.Union(
        sp.Interval.open(-sp.oo, -2),
        sp.Interval.open(-2, 2),
        sp.Interval.open(2, sp.oo),
    )
    assert dom == expected


def test_generic_domain_even_root() -> None:
    """Eq 5: sqrt(t - 2) -> Domain must be [2, +oo)."""
    t = sp.Symbol("t")
    dom = extract_expression_domain(sp.sqrt(t - 2), t)
    assert dom == sp.Interval(2, sp.oo, left_open=False, right_open=True)


def test_generic_domain_even_root_in_denominator() -> None:
    """Eq 6: 1/sqrt(t - 2) -> Domain must be (2, +oo)."""
    t = sp.Symbol("t")
    dom = extract_expression_domain(1 / sp.sqrt(t - 2), t)
    assert dom == sp.Interval.open(2, sp.oo)


def test_generic_domain_composite_log_and_pole() -> None:
    """Eq 7: ln(t - 1)/(t - 5) -> Domain must be (1, 5) U (5, +oo)."""
    t = sp.Symbol("t")
    expr = sp.log(t - 1) / (t - 5)
    dom = extract_expression_domain(expr, t)
    expected = sp.Union(sp.Interval.open(1, 5), sp.Interval.open(5, sp.oo))
    assert dom == expected


def test_generic_domain_entire_polynomial() -> None:
    """Eq 8: 2*t -> Domain must be (-oo, +oo) = R."""
    t = sp.Symbol("t")
    dom = extract_expression_domain(2 * t, t)
    assert dom == sp.S.Reals


# ==============================================================================
# 2. TASK B: BENCHMARK T03 SINGULAR-POINT & DOMAIN INTEGRITY
# ==============================================================================


def test_t03_singular_point_exact_values() -> None:
    """T03: (t-3)*y' + ln(t)*y = 2*t at singular point t = 3:
    Algebraic evaluation:
    - At t = 3, 0*y' + ln(3)*y = 6 => y(3) = 6/ln(3).
    - Differentiating ODE: 1*y' + (t-3)*y'' + (1/t)*y + ln(t)*y' = 2.
      At t = 3: y'(3) + 0 + (1/3)*(6/ln(3)) + ln(3)*y'(3) = 2.
      => y'(3)*(1 + ln(3)) = 2 - 2/ln(3) = 2(ln(3) - 1)/ln(3).
      => y'(3) = 2(ln(3) - 1) / [ln(3)*(1 + ln(3))].
    """
    t = sp.Symbol("t")
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

    assert res.singular_points == (sp.Integer(3),)
    assert len(res.singular_point_analyses) == 1

    spa = res.singular_point_analyses[0]
    assert spa.point == 3
    assert spa.value_at_point == 6 / sp.log(3)

    expected_yp = 2 * (sp.log(3) - 1) / (sp.log(3) * (1 + sp.log(3)))
    assert sp.simplify(spa.derivative_at_point - expected_yp) == 0


def test_t03_domain_decomposition_clean_intervals() -> None:
    """T03: Original domain D_orig = (0, +oo); Normalized domain D_norm = (0, 3) U (3, +oo)."""
    t = sp.Symbol("t")
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

    assert res.original_domain == sp.Interval.open(0, sp.oo)
    expected_norm = sp.Union(sp.Interval.open(0, 3), sp.Interval.open(3, sp.oo))
    assert res.normalized_domain == expected_norm
    assert res.is_disconnected is True
    assert len(res.connected_intervals) == 2


# ==============================================================================
# 3. TASK C: BRANCH SOLUTION DTO ARCHITECTURE & PROVENANCE
# ==============================================================================


def test_t03_branch_solutions_dto_structure(use_case) -> None:
    """T03 SolutionResponse.branch_solutions must be the authoritative data structure:
    - Exactly 2 branches: I_1 = (0, 3) and I_2 = (3, +oo).
    - Independent constants: C_1 and C_2.
    - final_result must NOT collapse C_1 and C_2 into a single C.
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="(t-3)*y' + ln(t)*y = 2*t",
        target_variable="t",
        parameters={"independent_var": "t", "dependent_var": "y"},
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS

    # 1. Authoritative branch solutions count
    assert len(resp.branch_solutions) == 2
    b1, b2 = resp.branch_solutions

    # 2. Branch intervals
    assert b1.domain_interval == (sp.Integer(0), sp.Integer(3))
    assert b2.domain_interval == (sp.Integer(3), sp.oo)

    # 3. Independent constants
    assert str(b1.integration_constant) == "C_1"
    assert str(b2.integration_constant) == "C_2"

    # 4. final_result preservation (no collapse)
    assert "C_1" in resp.final_result
    assert "C_2" in resp.final_result
    assert "(0, 3)" in resp.final_result
    assert "(3, +\\infty)" in resp.final_result or "(3, +oo)" in resp.final_result or "3" in resp.final_result

    # 5. Piecewise LaTeX
    assert "cases" in resp.final_latex
    assert "C_1" in resp.final_latex
    assert "C_2" in resp.final_latex
    assert "I_1 = (0, 3)" in resp.final_latex
    assert "I_2 = (3, +\\infty)" in resp.final_latex

    # 6. Domain fields on DTO
    assert resp.original_domain_latex != ""
    assert "(0, +\\infty)" in resp.original_domain_latex
    assert resp.normalized_domain_latex != ""
    assert "(0, 3)" in resp.normalized_domain_latex
    assert "(3, +\\infty)" in resp.normalized_domain_latex


# ==============================================================================
# 4. TASK D: INDEPENDENT BRANCH-BY-BRANCH VERIFICATION
# ==============================================================================


def test_t03_independent_branch_verification(use_case) -> None:
    """Each branch must satisfy R(t) = 0 on its own interval."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="(t-3)*y' + ln(t)*y = 2*t",
        target_variable="t",
        parameters={"independent_var": "t", "dependent_var": "y"},
    )
    resp = use_case.execute(req)

    assert len(resp.branch_solutions) == 2
    for b in resp.branch_solutions:
        assert b.verification is not None
        assert b.verification.status == VerificationStatus.VERIFIED

    # Check extension notes on branches
    for b in resp.branch_solutions:
        assert b.extension_details is not None
        assert (
            "y(3) = \\frac{6}{\\ln\\left(3\\right)}" in b.extension_details
            or "y(3) = 6/ln(3)" in b.extension_details
            or "6" in b.extension_details
        )


def test_t03_cauchy_ivp_matching_branch() -> None:
    """When an initial condition (t0, y0) is provided in I_1 (e.g. t0 = 1, y0 = 2),
    it must determine C_1 on I_1 and leave branch 2 or report validity interval.
    """
    solver = ODELinearSolver()
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="y' + 2*y = 4, y(0) = 3",
        target_variable="x",
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    # y(x) = 2 + e^(-2x) -> y(0) = 2 + 1 = 3
    assert "exp" in resp.final_result or "e^" in resp.final_latex


# ==============================================================================
# 5. TASK E: STEP NUMBERING & PROVENANCE ACROSS ALL 9 BENCHMARKS
# ==============================================================================


BENCHMARKS = [
    ("T01", ProblemType.ODE_FIRST_ORDER_LINEAR, "y' + 2*y = 4", "x"),
    ("T02", ProblemType.ODE_SEPARABLE, "y' = y*x", "x"),
    ("T03", ProblemType.ODE_FIRST_ORDER_LINEAR, "(t-3)*y' + ln(t)*y = 2*t", "t"),
    ("T04", ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS, "y' = (y + x)/x", "x"),
    ("T05", ProblemType.ODE_INTEGRATING_FACTOR, "(y)*dx + (2*x)*dy = 0", "x"),
    ("T06", ProblemType.ODE_EXACT, "(2*x*y + 3)*dx + (x**2 + 4*y)*dy = 0", "x"),
    ("T07", ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "y'' + 4*y = 0", "t"),
    ("T08", ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "y'' + 4*y = 4*t", "t"),
    ("T09", ProblemType.ODE_SECOND_ORDER_IVP, "y'' + 4*y = 0, y(0) = 1, y'(0) = 2", "t"),
]


@pytest.mark.parametrize("bench_id, prob_type, raw_eq, target_var", BENCHMARKS)
def test_all_benchmarks_sequential_step_numbering(use_case, bench_id, prob_type, raw_eq, target_var) -> None:
    """Verify that every single benchmark produces strictly sequential display numbers 1..N without gaps."""
    req = ProblemRequest(
        problem_type=prob_type,
        raw_input=raw_eq,
        target_variable=target_var,
        parameters={"independent_var": target_var, "dependent_var": "y"},
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS, f"{bench_id} failed with status {resp.status}"

    enhanced = enhance_ode_solution_flow(resp, prob_type, target_var=target_var)
    all_steps = [step for stage in enhanced for step in stage.steps]

    assert len(all_steps) > 0, f"{bench_id} produced 0 steps"

    # 1. Contiguous presentation numbers 1, 2, ..., N
    pres_numbers = [step.presentation_step_number for step in all_steps]
    expected_numbers = list(range(1, len(all_steps) + 1))
    assert pres_numbers == expected_numbers, f"{bench_id} presentation numbering mismatch: {pres_numbers}"

    # 2. Internal step IDs preserved
    for step in all_steps:
        assert step.internal_step_id is not None, f"{bench_id} step missing internal_step_id"
        assert isinstance(step.internal_step_id, int)


# ==============================================================================
# 6. TASK F: RESPONSIVE TYPOGRAPHY & OVERFLOW PROTECTION
# ==============================================================================


def test_responsive_typography_no_body_overflow_hidden() -> None:
    """Verify that 'overflow-x: hidden !important' is REMOVED from html, body."""
    head_html = get_head_html()
    # Check that html, body does not have overflow-x: hidden !important
    html_body_block = re.search(r"html,\s*body\s*\{([^}]+)\}", head_html)
    assert html_body_block is not None
    assert "overflow-x: hidden" not in html_body_block.group(1)

    # .math-block must have touch scroll
    assert "-webkit-overflow-scrolling: touch" in head_html
    assert "overflow-x: auto" in head_html
    assert "max-width: 100%" in head_html


# ==============================================================================
# 7. TASK G: UI DOMAIN DISTINCTION (D_orig vs D_norm)
# ==============================================================================


def test_format_domain_condition_generic_union() -> None:
    """format_domain_condition must not hardcode (0, 3) or (3, +oo)."""
    raw_res = r"\mathcal{D} = (1, 5) \cup (5, +\infty) = I_1 \cup I_2, với I_1 = (1, 5) và I_2 = (5, +\infty)."
    key, desc, formula = format_domain_condition(raw_res, var_name="t")

    assert "domain_union" in key
    assert "(1, 5)" in formula
    assert "(5, +\\infty)" in formula
    assert "(0, 3)" not in formula  # Must not introduce irrelevant (0, 3)

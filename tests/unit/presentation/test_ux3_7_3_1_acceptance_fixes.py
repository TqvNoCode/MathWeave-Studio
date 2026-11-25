"""Unit and acceptance test suite for UX3.7.3.1: Final Polish & Acceptance Fixes.

Covers:
1. Task A: Solution step numbering consistency across all ODE types (contiguous 1..N,
   no gaps, internal step IDs preserved, no grouped 'Step 2 & Step 6' labels).
2. Task B: T03 Disconnected Domain presentation (explicit domain union D = (0, 3) U (3, +inf) = I1 U I2,
   piecewise solution format with independent constants C1 and C2, conditional division by t-3).
3. Task C: Responsive mathematical typography rules (CSS tokens, media queries, math-block touch scroll).
"""

from __future__ import annotations

import pytest

from math_app.application.dtos import ProblemRequest, SolutionStatus, VerificationStatus
from math_app.application.use_cases import SolveProblemUseCase
from math_app.domain.models import ProblemType
from math_app.main import build_application
from math_app.presentation.components.domain_view import format_domain_condition
from math_app.presentation.components.ode_pedagogical_enhancer import enhance_ode_solution_flow
from math_app.presentation.design_system.styles import get_head_html
from math_app.solvers.calculus.ode.exact_solver import ODEExactSolver
from math_app.solvers.calculus.ode.integrating_factor_solver import ODEIntegratingFactorSolver


@pytest.fixture
def use_case() -> SolveProblemUseCase:
    return build_application()


# ==============================================================================
# 1. TASK A: STEP NUMBERING TESTS (CONTIGUOUS 1..N, NO GAPS)
# ==============================================================================


def test_t06_exact_ode_sequential_step_numbering() -> None:
    """T06: Exact ODE must present strictly contiguous presentation step numbers 1..6.

    Pedagogical flow:
    - Stage 1: Step 1 (Identify M and N)
    - Stage 2: Step 2 (Exactness test dM/dy == dN/dx)
    - Stage 3: Step 3 (Integrate M), Step 4 (Find h(y)), Step 5 (Construct potential F = C)
    - Stage 4: Step 6 (Independent verification)
    """
    solver = ODEExactSolver()
    req = ProblemRequest(
        problem_type=ProblemType.ODE_EXACT,
        raw_input="(2*x*y + 3)*dx + (x**2 + 4*y)*dy = 0",
        target_variable="x",
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS

    enhanced = enhance_ode_solution_flow(resp, ProblemType.ODE_EXACT, target_var="x")
    assert len(enhanced) == 4

    all_steps = [step for stage in enhanced for step in stage.steps]
    assert len(all_steps) == 6

    # Verify contiguous presentation numbers 1, 2, 3, 4, 5, 6
    pres_numbers = [step.presentation_step_number for step in all_steps]
    assert pres_numbers == [1, 2, 3, 4, 5, 6]

    # Verify no gaps
    for idx, num in enumerate(pres_numbers, start=1):
        assert num == idx

    # Verify pedagogical ordering across stages
    stg1_steps = enhanced[0].steps
    assert len(stg1_steps) == 1
    assert stg1_steps[0].presentation_step_number == 1
    assert "Nhận dạng" in stg1_steps[0].title or "M" in stg1_steps[0].title

    stg2_steps = enhanced[1].steps
    assert len(stg2_steps) == 1
    assert stg2_steps[0].presentation_step_number == 2
    assert "toàn phần" in stg2_steps[0].title.lower() or "exactness" in stg2_steps[0].title.lower()

    stg3_steps = enhanced[2].steps
    assert len(stg3_steps) == 3
    assert stg3_steps[0].presentation_step_number == 3
    assert "Tích phân" in stg3_steps[0].title
    assert stg3_steps[1].presentation_step_number == 4
    assert "h(y)" in stg3_steps[1].title or "hàm số phụ" in stg3_steps[1].title
    assert stg3_steps[2].presentation_step_number == 5
    assert "hàm thế" in stg3_steps[2].title

    stg4_steps = enhanced[3].steps
    assert len(stg4_steps) == 1
    assert stg4_steps[0].presentation_step_number == 6
    assert "Kiểm chứng" in stg4_steps[0].title


def test_t06_internal_step_id_preservation() -> None:
    """Internal solver step IDs must be preserved for debugging/logging while presentation uses contiguous IDs."""
    solver = ODEExactSolver()
    req = ProblemRequest(
        problem_type=ProblemType.ODE_EXACT,
        raw_input="(2*x*y + 3)*dx + (x**2 + 4*y)*dy = 0",
        target_variable="x",
    )
    resp = solver.solve(req)
    enhanced = enhance_ode_solution_flow(resp, ProblemType.ODE_EXACT, target_var="x")

    all_steps = [step for stage in enhanced for step in stage.steps]
    for step in all_steps:
        # internal_step_id must not be None
        assert step.internal_step_id is not None
        assert isinstance(step.internal_step_id, int)
        # presentation_step_number must be contiguous 1..N
        assert step.presentation_step_number == step.display_step_number


def test_t05_integrating_factor_sequential_step_numbering() -> None:
    """T05: Integrating Factor ODE must have contiguous step numbering without dropping any steps."""
    solver = ODEIntegratingFactorSolver()
    req = ProblemRequest(
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
        raw_input="(y)*dx + (2*x)*dy = 0",
        target_variable="x",
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS

    enhanced = enhance_ode_solution_flow(resp, ProblemType.ODE_INTEGRATING_FACTOR, target_var="x")
    all_steps = [step for stage in enhanced for step in stage.steps]
    pres_numbers = [step.presentation_step_number for step in all_steps]

    # Must be contiguous 1, 2, ..., N
    expected = list(range(1, len(all_steps) + 1))
    assert pres_numbers == expected

    # Step finding h(y) must be included
    titles = [s.title for s in all_steps]
    assert any("h(" in t or "hàm số phụ" in t for t in titles)


def test_t01_linear_ode_contiguous_numbering(use_case) -> None:
    """T01: Linear ODE y' + 2y = 4 must have strictly contiguous presentation numbering."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="y' + 2*y = 4",
        target_variable="x",
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS

    enhanced = enhance_ode_solution_flow(resp, ProblemType.ODE_FIRST_ORDER_LINEAR, target_var="x")
    all_steps = [step for stage in enhanced for step in stage.steps]
    pres_numbers = [step.presentation_step_number for step in all_steps]
    assert pres_numbers == list(range(1, len(all_steps) + 1))


def test_t02_separable_ode_contiguous_numbering(use_case) -> None:
    """T02: Separable ODE y' = y*x must have strictly contiguous presentation numbering."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SEPARABLE,
        raw_input="y' = y*x",
        target_variable="x",
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS

    enhanced = enhance_ode_solution_flow(resp, ProblemType.ODE_SEPARABLE, target_var="x")
    all_steps = [step for stage in enhanced for step in stage.steps]
    pres_numbers = [step.presentation_step_number for step in all_steps]
    assert pres_numbers == list(range(1, len(all_steps) + 1))


def test_t07_second_order_homogeneous_contiguous_numbering(use_case) -> None:
    """T07: y'' + 4y = 0 must have strictly contiguous presentation numbering."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' + 4*y = 0",
        target_variable="t",
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS

    enhanced = enhance_ode_solution_flow(resp, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, target_var="t")
    all_steps = [step for stage in enhanced for step in stage.steps]
    pres_numbers = [step.presentation_step_number for step in all_steps]
    assert pres_numbers == list(range(1, len(all_steps) + 1))


def test_t08_second_order_nonhomogeneous_contiguous_numbering(use_case) -> None:
    """T08: y'' + 4y = 4t must have strictly contiguous presentation numbering."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' + 4*y = 4*t",
        target_variable="t",
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS

    enhanced = enhance_ode_solution_flow(resp, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, target_var="t")
    all_steps = [step for stage in enhanced for step in stage.steps]
    pres_numbers = [step.presentation_step_number for step in all_steps]
    assert pres_numbers == list(range(1, len(all_steps) + 1))


# ==============================================================================
# 2. TASK B: T03 DISCONNECTED DOMAIN PRESENTATION TESTS
# ==============================================================================


def test_t03_domain_union_presentation(use_case) -> None:
    """T03: (t-3)*y' + ln(t)*y = 2*t
    - Explicit domain union: D = (0, 3) U (3, +inf) = I1 U I2.
    - No ambiguous 'I1 = (0, 3) hoặc I2 = (3, +inf)'.
    - Piecewise solution format with independent C1 on I1 and C2 on I2.
    - Clear explanation of division by (t-3) requiring t != 3.
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="(t-3)*y' + ln(t)*y = 2*t",
        target_variable="t",
        parameters={"independent_var": "t", "dependent_var": "y"},
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status in (VerificationStatus.PARTIALLY_VERIFIED, VerificationStatus.VERIFIED)

    # 1. Domain restrictions check
    domain_full = " ".join(resp.domain_restrictions)
    assert r"\mathcal{D} = (0, 3) \cup (3, +\infty)" in domain_full or "(0, 3) \\cup (3, +\\infty)" in domain_full
    assert "I_1 = (0, 3)" in domain_full
    assert "I_2 = (3, +\\infty)" in domain_full
    assert "hoặc" not in domain_full  # Reject ambiguous 'hoặc'

    # 2. Step 1: Explain division by (t - 3) with condition t != 3
    step1 = resp.steps[0]
    assert "t - 3" in step1.description or "(t - 3)" in step1.description
    assert "\\ne 0" in step1.description or "khác 0" in step1.description

    # 3. Step 6: General solution with piecewise C1, C2 and non-elementary integrating factor
    step6 = [s for s in resp.steps if s.rule_name == "Rút ra nghiệm tổng quát"][0]
    assert "cases" in step6.content.latex_after
    assert "C_1" in step6.content.latex_after
    assert "C_2" in step6.content.latex_after
    assert "I_1 = (0, 3)" in step6.content.latex_after
    assert "I_2 = (3, +\\infty)" in step6.content.latex_after
    assert "\\mu(t)" in step6.content.latex_after
    assert "độc lập" in step6.description


def test_t03_domain_view_formatting() -> None:
    """Verify that domain_view.format_domain_condition formats domain union cleanly."""
    raw_res = r"Miền xác định của phương trình gồm hai khoảng liên thông rời rạc: \mathcal{D} = (0, 3) \cup (3, +\infty) = I_1 \cup I_2, với I_1 = (0, 3) và I_2 = (3, +\infty)."
    key, desc, formula = format_domain_condition(raw_res, var_name="t")

    assert "domain_union" in key
    assert "Miền xác định" in desc
    assert r"\mathcal{D} = (0, 3) \cup (3, +\infty) = I_1 \cup I_2" in formula
    assert "I_1 = (0, 3)" in formula
    assert "I_2 = (3, +\\infty)" in formula


def test_domain_view_logarithm_argument_extraction() -> None:
    """Verify that domain_view formats logarithm argument nicely (e.g. t > 0 instead of generic u(t) > 0)."""
    raw_res = "Điều kiện xác định của hàm logarit: t > 0."
    key, desc, formula = format_domain_condition(raw_res, var_name="t")

    assert "ln" in key
    assert "logarit" in desc.lower()
    assert "t > 0" in formula


# ==============================================================================
# 3. TASK C: RESPONSIVE MATHEMATICAL TYPOGRAPHY TESTS
# ==============================================================================


def test_responsive_typography_css_tokens() -> None:
    """Verify that get_head_html includes responsive typography rules for mobile and tablet."""
    head_html = get_head_html()

    # Touch scrolling and overflow protection on .math-block
    assert "-webkit-overflow-scrolling: touch" in head_html
    assert "overflow-x: auto" in head_html

    # Mobile media query (<=640px)
    assert "@media (max-width: 640px)" in head_html

    # Tablet media query (<=768px)
    assert "@media (max-width: 768px)" in head_html

    # Prose text word wrap protection
    assert ".prose-text" in head_html
    assert "overflow-wrap: break-word" in head_html

    # Inline math max-width protection
    assert ".math-inline" in head_html
    assert "max-width: 100%" in head_html

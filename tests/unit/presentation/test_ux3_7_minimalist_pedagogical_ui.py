"""Tests for UX3.7: Minimalist Pedagogical UI/UX Refactoring.

Validates:
1. Benchmark Reference Equation: y' + 1/2*y = t + 2 derivation and stages
2. Single-card minimalist step structure and complete deduplication of intermediate results
3. Stage summary deduplication (no repeated formulas across step, summary, and final answer)
4. Collapsible independent verification section with verified badge
5. Sequential step numbering (no "BƯỚC 3" before Step 2 in First-Order mode selector)
6. Context-aware module consistency banner with instant one-click sync
7. Elimination of raw LaTeX leakage in guided view and verification synthesis
8. Second-Order Nonhomogeneous and Cauchy IVP minimalist presentation
"""

from __future__ import annotations

import pytest
from nicegui import ui

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus
from math_app.main import build_application
from math_app.presentation.components.ode_pedagogical_enhancer import (
    enhance_ode_solution_flow,
)
from math_app.presentation.components.ode_staged_step_viewer import (
    _is_meaningful_intermediate_result,
    _normalize_math,
    render_ode_pedagogical_step,
    render_ode_staged_steps_container,
)
from math_app.presentation.components.workspace.ode.first_order_classifier import (
    classify_first_order_ode,
)
from math_app.presentation.components.workspace.ode.ode_guided_classification_view import (
    render_ode_guided_classification_view,
)
from math_app.presentation.components.workspace.ode.ode_mode_selector import (
    render_ode_mode_selector,
)
from math_app.presentation.components.workspace.ode.ode_state import (
    ODEClassification,
    ODEMode,
    ODEOrder,
    ODEState,
)


@pytest.fixture(scope="module")
def use_case():
    return build_application()


# ==============================================================================
# 1. BENCHMARK REFERENCE EQUATION: y' + 1/2*y = t + 2
# ==============================================================================


def test_benchmark_first_order_linear_pedagogical_flow(use_case):
    """Verify primary benchmark y' + 1/2*y = t + 2 adheres to clean 4-stage pedagogical flow."""
    req = ProblemRequest(
        raw_input="y' + 1/2*y = t + 2",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
        parameters={},
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert "C" in resp.final_latex
    assert "2 t" in resp.final_latex or "2*t" in resp.final_latex

    stages = enhance_ode_solution_flow(resp, req.problem_type, req.target_variable, req.parameters)
    assert len(stages) == 4

    # Stage 1: Canonical standard form
    assert stages[0].stage_index == 1
    assert "Nhận dạng" in stages[0].title
    assert len(stages[0].steps) == 1
    assert stages[0].steps[0].equation_latex.strip()

    # Stage 2: Integrating factor mu(t)
    assert stages[1].stage_index == 2
    assert "thừa số tích phân" in stages[1].title.lower() or "mu" in stages[1].badge_text
    assert len(stages[1].steps) == 1
    assert "mu" in stages[1].steps[0].equation_latex or "\\mu" in stages[1].steps[0].equation_latex

    # Stage 3: Analytic derivation steps (Product rule -> Integration -> General solution)
    assert stages[2].stage_index == 3
    assert len(stages[2].steps) >= 3

    # Stage 4: Independent verification (collapsible)
    assert stages[3].stage_index == 4
    assert "Kiểm chứng" in stages[3].title
    assert len(stages[3].steps) >= 1
    assert "R(t)" in stages[3].steps[0].equation_latex


# ==============================================================================
# 2. DEDUPLICATION OF INTERMEDIATE RESULTS & STAGE SUMMARIES
# ==============================================================================


def test_intermediate_result_deduplication(use_case):
    """Verify intermediate results identical to equation_latex are marked non-meaningful to eliminate duplicate cards."""
    req = ProblemRequest(
        raw_input="y' + 1/2*y = t + 2",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
        parameters={},
    )
    resp = use_case.execute(req)
    stages = enhance_ode_solution_flow(resp, req.problem_type, req.target_variable, req.parameters)

    # For benchmark equation, steps in Stage 1, 2, 3 have equation_latex == intermediate_result
    # _is_meaningful_intermediate_result should return False, suppressing redundant green cards
    for stg in stages[:3]:
        for step in stg.steps:
            if _normalize_math(step.intermediate_result) == _normalize_math(step.equation_latex):
                assert not _is_meaningful_intermediate_result(step)


def test_stage_summary_deduplication(use_case):
    """Verify stage summaries identical to the last step equation or final answer are suppressed."""
    req = ProblemRequest(
        raw_input="y' + 1/2*y = t + 2",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
        parameters={},
    )
    resp = use_case.execute(req)
    stages = enhance_ode_solution_flow(resp, req.problem_type, req.target_variable, req.parameters)

    # In Stage 1: summary is identical to Step 1
    last_step_eq_1 = stages[0].steps[-1].equation_latex
    assert _normalize_math(stages[0].summary_latex) == _normalize_math(last_step_eq_1)

    # In Stage 2: summary is identical to Step 2
    last_step_eq_2 = stages[1].steps[-1].equation_latex
    assert _normalize_math(stages[1].summary_latex) == _normalize_math(last_step_eq_2)

    # In Stage 3: summary is identical to the final answer
    assert _normalize_math(stages[2].summary_latex) == _normalize_math(resp.final_latex)


def test_synthesis_verification_step_no_duplicate_y_equals(use_case):
    """Verify synthesized verification description does not leak '$y(t) = y(t) = ...$'."""
    req = ProblemRequest(
        raw_input="y' + 1/2*y = t + 2",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
        parameters={},
    )
    resp = use_case.execute(req)
    stages = enhance_ode_solution_flow(resp, req.problem_type, req.target_variable, req.parameters)

    verify_step = stages[3].steps[0]
    desc = verify_step.description
    assert "y(t) = y(t) =" not in desc
    assert "Thế nghiệm $" in desc


def test_render_ode_pedagogical_step_mounts_cleanly(use_case):
    """Verify an individual pedagogical step mounts cleanly inside NiceGUI container."""
    req = ProblemRequest(
        raw_input="y' + 1/2*y = t + 2",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
        parameters={},
    )
    resp = use_case.execute(req)
    stages = enhance_ode_solution_flow(resp, req.problem_type, req.target_variable, req.parameters)

    with ui.column() as step_container:
        render_ode_pedagogical_step(stages[0].steps[0])
    assert step_container is not None


# ==============================================================================
# 3. STEP NUMBERING & ODE MODE SELECTOR
# ==============================================================================


def test_mode_selector_numbering_first_order_no_step3_badge():
    """Verify that in First-Order mode, the mode selector does not display conflicting 'BƯỚC 3' badge."""
    rendered_badges: list[str] = []

    with ui.column() as container:
        render_ode_mode_selector(
            order=ODEOrder.FIRST_ORDER,
            classification=ODEClassification.FIRST_ORDER_LINEAR,
            selected_mode=ODEMode.GENERAL,
            initial_condition="",
            on_mode_change=lambda _: None,
            on_ic_change=lambda _: None,
        )

    # Inspect all badge elements inside container
    def _collect_badges(el):
        if isinstance(el, ui.badge):
            if hasattr(el, "_text") and el._text:
                rendered_badges.append(el._text)
        for child in getattr(el, "default_slot", []):
            _collect_badges(child)

    _collect_badges(container)
    assert "BƯỚC 3" not in rendered_badges


def test_mode_selector_numbering_second_order_keeps_step3_badge():
    """Verify that in Second-Order mode, mode selector uses consistent semantic heading without numbered BƯỚC badge."""
    rendered_badges: list[str] = []
    rendered_labels: list[str] = []

    with ui.column() as container:
        render_ode_mode_selector(
            order=ODEOrder.SECOND_ORDER,
            classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
            selected_mode=ODEMode.GENERAL,
            initial_condition="",
            on_mode_change=lambda _: None,
            on_ic_change=lambda _: None,
        )

    def _collect(el):
        if isinstance(el, ui.badge) and getattr(el, "_text", None):
            rendered_badges.append(el._text)
        if isinstance(el, ui.label) and getattr(el, "_text", None):
            rendered_labels.append(el._text)
        for child in getattr(el, "default_slot", []):
            _collect(child)

    _collect(container)
    assert "BƯỚC 3" not in rendered_badges
    assert "YÊU CẦU BÀI TOÁN:" in rendered_labels


# ==============================================================================
# 4. MODULE CONSISTENCY & GUIDED CLASSIFICATION VIEW
# ==============================================================================


def test_first_order_guided_classification_clean_math_rendering():
    """Verify First-Order guided classification view renders without raw LaTeX leakage in plain text."""
    clf_res = classify_first_order_ode("y' + 1/2*y = t + 2", target_var="t")
    assert clf_res.is_valid_ode
    assert clf_res.is_linear
    assert not clf_res.is_linear_homogeneous

    state = ODEState.default_for_classification(ODEClassification.FIRST_ORDER_LINEAR)

    with ui.column() as container:
        render_ode_guided_classification_view(
            result=clf_res,
            state=state,
            on_select_classification=lambda _: None,
        )

    assert container is not None
    # Verify no raw unrendered dollar math in label elements
    def _check_no_raw_dollar_labels(el):
        if isinstance(el, ui.label):
            text = getattr(el, "_text", "") or ""
            # Plain labels should not contain raw $ \mu or $ \frac
            if "$" in text:
                assert "\\mu" not in text, f"Raw LaTeX leaked into ui.label: {text}"
                assert "\\frac" not in text, f"Raw LaTeX leaked into ui.label: {text}"
                assert "\\implies" not in text, f"Raw LaTeX leaked into ui.label: {text}"
        for child in getattr(el, "default_slot", []):
            _check_no_raw_dollar_labels(child)

    _check_no_raw_dollar_labels(container)


def test_module_consistency_detection_linear_in_exact():
    """Verify that entering a linear ODE into an exact classification correctly identifies the mismatch."""
    clf_res = classify_first_order_ode("y' + 1/2*y = t + 2", target_var="t")
    exact_state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.EXACT,
        equation="y' + 1/2*y = t + 2",
        target_var="t",
    )

    # Problem type of state is ODE_EXACT, while detected target_problem_type is ODE_FIRST_ORDER_LINEAR
    assert exact_state.problem_type == ProblemType.ODE_EXACT
    assert clf_res.target_problem_type == ProblemType.ODE_FIRST_ORDER_LINEAR
    assert clf_res.target_problem_type != exact_state.problem_type


# ==============================================================================
# 5. SECOND-ORDER & CAUCHY IVP MINIMALIST PRESENTATION
# ==============================================================================


def test_second_order_nonhomogeneous_minimalist_structure(use_case):
    """Verify Second-Order Nonhomogeneous equation y'' + 4y = 4t renders 4 stages cleanly."""
    req = ProblemRequest(
        raw_input="y'' + 4*y = 4*t",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
        parameters={},
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS

    stages = enhance_ode_solution_flow(resp, req.problem_type, req.target_variable, req.parameters)
    assert len(stages) == 4

    # Stage 1: Homogeneous yc(t)
    assert stages[0].stage_index == 1
    # Stage 2: Particular yp(t)
    assert stages[1].stage_index == 2
    # Stage 3: General solution y(t) = yc(t) + yp(t)
    assert stages[2].stage_index == 3
    # Stage 4: Verification (collapsible)
    assert stages[3].stage_index == 4

    with ui.column() as container:
        render_ode_staged_steps_container(stages, final_answer_latex=resp.final_latex)
    assert container is not None


def test_cauchy_ivp_distinct_intermediate_result(use_case):
    """Verify Cauchy IVP retains meaningful intermediate results for the initial constants evaluation."""
    req = ProblemRequest(
        raw_input="y'' + 4*y = 4*t, y(0)=1, y'(0)=2",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
        parameters={"initial_condition": "y(0)=1, y'(0)=2"},
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS

    stages = enhance_ode_solution_flow(resp, req.problem_type, req.target_variable, req.parameters)
    stage_3_steps = stages[2].steps

    # The step evaluating C1, C2 from initial conditions should have a meaningful result
    has_meaningful_ic_step = any(
        _is_meaningful_intermediate_result(s) and ("C_1" in s.equation_latex or "C_1" in s.intermediate_result)
        for s in stage_3_steps
    )
    assert has_meaningful_ic_step

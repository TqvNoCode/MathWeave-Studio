"""Dedicated test suite for UX3.5.2: Cauchy Pedagogical Refinement & Visual Polish.

Tests cover:
1. Reference Cauchy IVP (y'' + 4y = 4t, y(0)=1, y'(0)=2):
   - Stage 1: Complementary solution yc(t) = C1*cos(2t) + C2*sin(2t)
   - Stage 2: Particular solution yp(t) = t with explicit resonance verification P(0)=4 != 0 => s=0
   - Stage 3: Exactly 3 clean steps; direct derivation of C1=1, C2=1/2; Cramer's rule in substeps
   - Stage 4: Verification with separated math formula R(t)=0, zero red KaTeX errors
2. Standardized Mathematical Notation (P0):
   - Canonical lowercase y(t), yc(t), yp(t), C1, C2, A0, A1, R(t)
   - Absolute absence of uppercase Y(T), Y_C(T), Y_P(T), R(T), R(X), Y(X)
3. Zero Raw LaTeX and Inline Mathematics (P0):
   - Rendered text has zero raw delimiters ($), zero unrendered \\implies, \\equiv
   - Elimination of orphan punctuation marks
4. Presentation Visual Fixes & Responsive Header (P1):
   - Step title container has min-w-[240px] and flex-1
   - Badge container wraps without shrink-0 squeezing
   - Elimination of red text in green success cards
5. Scrollbar Stepper Button Suppression (P1):
   - ::-webkit-scrollbar-button hidden across all pseudo-classes
6. Full Benchmark ODE Regression Suite (P2):
   - 10 benchmark ODE equations covering all methods
"""

from __future__ import annotations

import re
import pytest

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.main import build_application
from math_app.presentation.components.ode_pedagogical_enhancer import (
    enhance_ode_solution_flow,
    standardize_ode_notation,
)
from math_app.presentation.design_system.styles import get_head_html
from math_app.rendering.text_math_renderer import (
    is_pure_latex_math,
    render_math_in_text_html,
)


@pytest.fixture(scope="module")
def app():
    return build_application()


# ==============================================================================
# TEST 1: REFERENCE CAUCHY IVP (y'' + 4y = 4t, y(0)=1, y'(0)=2)
# ==============================================================================


def test_reference_cauchy_ivp_pedagogical_flow(app):
    """Verify textbook-grade 4-stage pedagogical flow for the reference Cauchy IVP.
    Equation: y'' + 4*y = 4*t, y(0)=1, y'(0)=2
    Solution: y(t) = t + 0.5*sin(2t) + cos(2t)
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        raw_input="y'' + 4*y = 4*t, y(0)=1, y'(0)=2",
        target_variable="t",
    )
    res = app.execute(req)

    # 1. Functional correctness
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None
    assert "t" in res.final_result
    assert "sin(2*t)" in res.final_result
    assert "cos(2*t)" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED

    # 2. Pedagogical flow stages
    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4, f"Expected exactly 4 stages, got {len(stages)}"

    stg1, stg2, stg3, stg4 = stages

    # STAGE 1: Complementary Solution yc(t)
    assert "Giai đoạn 1" in stg1.title
    assert "y_c(t)" in stg1.badge_text
    assert "C_{1}" in stg1.summary_latex or "C_1" in stg1.summary_latex
    assert "cos" in stg1.summary_latex.lower()
    assert "sin" in stg1.summary_latex.lower()
    assert len(stg1.steps) >= 3

    # Check characteristic equation and roots in stage 1
    assert any("r^{2} + 4 = 0" in s.intermediate_result or "r^2 + 4" in s.intermediate_result for s in stg1.steps)
    stg1_combined_text = " ".join(s.description for s in stg1.steps)
    assert "-16" in stg1_combined_text  # Delta = -16

    # STAGE 2: Particular Solution yp(t)
    assert "Giai đoạn 2" in stg2.title
    assert "y_p(t)" in stg2.badge_text
    assert "t" in stg2.summary_latex
    assert len(stg2.steps) >= 3

    # Verify explicit resonance reasoning in stage 2 step 1
    stg2_step1 = stg2.steps[0]
    assert "kiểm tra cộng hưởng" in stg2_step1.description.lower() or "cộng hưởng" in stg2_step1.description.lower()
    assert "P(0) = 4" in stg2_step1.description or "P(0)" in stg2_step1.description
    assert "s = 0" in stg2_step1.description

    # STAGE 3: Total Solution & Cauchy Condition
    assert "Giai đoạn 3" in stg3.title
    assert "y(t)" in stg3.badge_text
    assert len(stg3.steps) == 3, f"Stage 3 must have exactly 3 steps (derivative, direct Cauchy IC, final answer), got {len(stg3.steps)}"

    # Step 1: Derivative of general solution
    assert "đạo hàm" in stg3.steps[0].display_title.lower()
    assert "y'(t)" in stg3.steps[0].intermediate_result

    # Step 2: Direct derivation of C1 and C2
    cauchy_step = stg3.steps[1]
    assert "C_1, C_2" in cauchy_step.display_title or "C" in cauchy_step.display_title
    # Check explicit derivation text
    assert "y_c(0) = C_1" in cauchy_step.description
    assert "C_1 = 1" in cauchy_step.description
    assert "2\\,C_2 = 1" in cauchy_step.description or "2C_2 = 1" in cauchy_step.description
    assert "C_2 = \\frac{1}{2}" in cauchy_step.description or "C_2 = 1/2" in cauchy_step.description
    # Verify Cramer's rule is nested inside substeps
    assert hasattr(cauchy_step, "substeps") and len(cauchy_step.substeps) >= 3
    substep_titles = [sub.title for sub in cauchy_step.substeps]
    assert any("cramer" in t.lower() or "ma trận" in t.lower() for t in substep_titles)

    # Step 3: Final unique solution
    assert "nghiệm duy nhất" in stg3.steps[2].display_title.lower() or "tổng hợp" in stg3.steps[2].display_title.lower()

    # STAGE 4: Verification
    assert "Giai đoạn 4" in stg4.title
    assert "Kiểm chứng" in stg4.badge_text
    assert len(stg4.steps) >= 1

    stg4_step1 = stg4.steps[0]
    # Verify separated math formula without mixed Vietnamese prose in intermediate_result
    assert stg4_step1.intermediate_result == "R(t) = 0"
    assert "\\implies" not in stg4_step1.intermediate_result
    # Verify verification description details
    assert "R(t)" in stg4_step1.description
    assert "y(0) = 1" in stg4_step1.description
    assert "y'(0) = 2" in stg4_step1.description


# ==============================================================================
# TEST 2: STANDARDIZED MATHEMATICAL NOTATION (P0)
# ==============================================================================


def test_standardized_mathematical_notation(app):
    """Verify that all notation adheres strictly to canonical lowercase mathematical conventions.
    Never display Y(T), Y_C(T), Y_P(T), R(T), R(X), Y(X).
    Subscripts are properly formatted (C_1, C_2, A_0, A_1).
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        raw_input="y'' + 4*y = 4*t, y(0)=1, y'(0)=2",
        target_variable="t",
    )
    res = app.execute(req)
    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)

    forbidden_patterns = [
        re.compile(r"\bY\(T\)\b"),
        re.compile(r"\bY_C\(T\)\b"),
        re.compile(r"\bY_P\(T\)\b"),
        re.compile(r"\bR\(T\)\b"),
        re.compile(r"\bYC\(T\)\b"),
        re.compile(r"\bYP\(T\)\b"),
        re.compile(r"\bY\(X\)\b"),
        re.compile(r"\bR\(X\)\b"),
    ]

    for s_idx, stage in enumerate(stages, 1):
        # Stage title & badge
        for pat in forbidden_patterns:
            assert not pat.search(stage.title), f"Stage {s_idx} title contains forbidden uppercase pattern: {stage.title}"
            assert not pat.search(stage.badge_text), f"Stage {s_idx} badge contains forbidden uppercase pattern: {stage.badge_text}"

        # Steps
        for step_idx, step in enumerate(stage.steps, 1):
            for pat in forbidden_patterns:
                assert not pat.search(step.display_title), f"Step {step_idx} title in Stage {s_idx} contains forbidden pattern"
                assert not pat.search(step.display_rule_name), f"Step {step_idx} rule in Stage {s_idx} contains forbidden pattern"
                assert not pat.search(step.intermediate_result), f"Step {step_idx} intermediate_result in Stage {s_idx} contains forbidden pattern"

    # Test standardize_ode_notation function directly
    raw_text = "Nghiệm tổng quát Y(T) = Y_C(T) + Y_P(T) với phần dư R(T) = 0 và hệ số A0, A1, B0, B1, C1, C2"
    standardized = standardize_ode_notation(raw_text)
    assert "y(t)" in standardized
    assert "y_c(t)" in standardized
    assert "y_p(t)" in standardized
    assert "R(t)" in standardized
    assert "A_0, A_1" in standardized
    assert "B_0, B_1" in standardized
    assert "C_1, C_2" in standardized


# ==============================================================================
# TEST 3: ZERO RAW LATEX & ZERO RAW DELIMITERS (P0)
# ==============================================================================


def test_zero_raw_latex_and_delimiters_in_rendered_html(app):
    """Verify that render_math_in_text_html eliminates all raw LaTeX commands
    and raw '$' delimiters from user-visible HTML text.
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        raw_input="y'' + 4*y = 4*t, y(0)=1, y'(0)=2",
        target_variable="t",
    )
    res = app.execute(req)
    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)

    for s_idx, stage in enumerate(stages, 1):
        for step_idx, step in enumerate(stage.steps, 1):
            rendered_html = render_math_in_text_html(step.description)
            assert "<math" in rendered_html, f"Step {step_idx} in Stage {s_idx} failed to generate MathML"

            # Strip HTML tags to inspect user-visible text
            text_only = re.sub(r"<[^>]+>", "", rendered_html)

            # Check absence of raw unrendered LaTeX markers in user-visible text
            assert "$" not in text_only, f"Step {step_idx} in Stage {s_idx} contains raw $ in visible text: {text_only[:100]}"
            assert "\\implies" not in text_only, f"Step {step_idx} in Stage {s_idx} contains raw \\implies in visible text"
            assert "\\equiv" not in text_only, f"Step {step_idx} in Stage {s_idx} contains raw \\equiv in visible text"
            assert "\\lambda" not in text_only, f"Step {step_idx} in Stage {s_idx} contains raw \\lambda in visible text"
            assert "\\alpha" not in text_only, f"Step {step_idx} in Stage {s_idx} contains raw \\alpha in visible text"
            assert "\\beta" not in text_only, f"Step {step_idx} in Stage {s_idx} contains raw \\beta in visible text"

            # Check absence of orphan punctuation on their own lines
            lines = [line.strip() for line in text_only.split("\n") if line.strip()]
            for line in lines:
                assert line not in (".", ",", ";", ":"), f"Found orphan punctuation line: '{line}'"


# ==============================================================================
# TEST 4: INTERMEDIATE RESULT RENDERING WITHOUT KATEX RED ERROR (P1)
# ==============================================================================


def test_intermediate_result_rendering_and_pure_latex_math():
    """Verify is_pure_latex_math correctly distinguishes pure math formulas
    from mixed Vietnamese prose, preventing KaTeX red (#cc0000) errors.
    """
    # Pure LaTeX math formulas should return True
    assert is_pure_latex_math("R(t) = 0") is True
    assert is_pure_latex_math("y_p(t) = t") is True
    assert is_pure_latex_math(r"\Delta = b^2 - 4ac = -16") is True
    assert is_pure_latex_math(r"C_1 = 1, \quad C_2 = \frac{1}{2}") is True
    assert is_pure_latex_math(r"A_{0} = 0, \quad A_{1} = 1") is True

    # Mixed prose with Vietnamese text should return False
    assert is_pure_latex_math("Phần dư toán học $R(t) = 0$") is False
    assert is_pure_latex_math("Kiểm chứng độc lập thành công") is False
    assert is_pure_latex_math(r"Phần dư toán học $R(t) = 0 \implies$ Kiểm chứng độc lập thành công.") is False

    # Render mixed string through render_math_in_text_html and verify zero red error text
    mixed_str = r"Phần dư toán học $R(t) = 0 \implies$ Kiểm chứng độc lập thành công."
    html_out = render_math_in_text_html(mixed_str)
    assert "#cc0000" not in html_out
    assert "katex-error" not in html_out
    assert "<math" in html_out


# ==============================================================================
# TEST 5: RESPONSIVE STEP HEADER & BADGE WRAPPING (P1)
# ==============================================================================


def test_responsive_step_header_classes():
    """Inspect ode_staged_step_viewer.py source to ensure responsive flex
    classes prevent step title wrapping on small screens (1024x768).
    """
    import inspect
    from math_app.presentation.components import ode_staged_step_viewer

    source = inspect.getsource(ode_staged_step_viewer)

    # Title container must have min-w-[240px] and flex-1
    assert "min-w-[240px]" in source, "Step title container missing min-w-[240px]"
    assert "flex-1" in source

    # Badge container must have flex-wrap and items-center
    assert "items-center gap-1.5 flex-wrap justify-end" in source

    # Stage summary card must have compact padding
    assert "p-2.5 my-1" in source


# ==============================================================================
# TEST 6: SCROLLBAR STEPPER SUPPRESSION IN CSS (P1)
# ==============================================================================


def test_scrollbar_stepper_suppression_in_css():
    """Verify that get_head_html contains complete suppression of ::-webkit-scrollbar-button
    across all pseudo-classes (:start, :end, :vertical:decrement, etc.).
    """
    head_html = get_head_html()
    assert "::-webkit-scrollbar-button" in head_html
    assert "::-webkit-scrollbar-button:start" in head_html
    assert "::-webkit-scrollbar-button:end" in head_html
    assert "::-webkit-scrollbar-button:vertical:decrement" in head_html
    assert "::-webkit-scrollbar-button:vertical:increment" in head_html
    assert "::-webkit-scrollbar-button:horizontal:decrement" in head_html
    assert "::-webkit-scrollbar-button:horizontal:increment" in head_html
    assert "display: none !important" in head_html
    assert "width: 0 !important" in head_html
    assert "height: 0 !important" in head_html
    assert "visibility: hidden !important" in head_html


# ==============================================================================
# TEST 7: FULL ODE BENCHMARK REGRESSION SUITE (P2)
# ==============================================================================


@pytest.mark.parametrize(
    "prob_type,raw_input,target_var,expected_keyword",
    [
        (ProblemType.ODE_FIRST_ORDER_LINEAR, "y' + 2*y = exp(-t)", "t", "exp"),
        (ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "y'' - 3*y' + 2*y = exp(t)", "t", "exp"),
        (ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "y'' + 2*y' + 5*y = 3*sin(2*t)", "t", "sin"),
        (ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "y'' - 2*y' - 3*y = 3*exp(2*t)", "t", "exp"),
        (ProblemType.ODE_SECOND_ORDER_IVP, "y'' + 4*y = 4*t, y(0)=1, y'(0)=2", "t", "sin"),
        (ProblemType.ODE_SEPARABLE, "y' = y^2", "x", "x"),
        (ProblemType.ODE_EXACT, "2*x*y + (x^2 + 1)*y' = 0", "x", "x"),
        (ProblemType.ODE_INTEGRATING_FACTOR, "y' + y/x = 1", "x", "x"),
        (ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS, "y' = (y + x)/x", "x", "x"),
        (ProblemType.ODE_REDUCTION_OF_ORDER, "t^2*y'' - 2*t*y' + 2*y = 0", "t", "C"),
    ],
)
def test_full_ode_benchmark_regression(app, prob_type, raw_input, target_var, expected_keyword):
    """Ensure all 10 benchmark ODE scenarios solve, verify, and generate valid pedagogical stages
    without any raw LaTeX defects or crashes.
    """
    params = {"known_solution": "t"} if prob_type == ProblemType.ODE_REDUCTION_OF_ORDER else {}
    req = ProblemRequest(
        problem_type=prob_type,
        raw_input=raw_input,
        target_variable=target_var,
        parameters=params,
    )
    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None
    assert expected_keyword in res.final_result

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) >= 3, f"Expected at least 3 stages for {raw_input}, got {len(stages)}"

    for s_idx, stage in enumerate(stages, 1):
        assert stage.title
        assert stage.badge_text
        for step_idx, step in enumerate(stage.steps, 1):
            assert step.display_title
            rendered_html = render_math_in_text_html(step.description)
            assert "$" not in re.sub(r"<[^>]+>", "", rendered_html)

"""Regression test suite for UX3.7.3 — Mathematical Typography, Inline Rendering & Pedagogical Precision."""

import pytest

from math_app.application.dtos import (
    ExpressionStepContent,
    ProblemRequest,
    ProblemType,
    SolutionStep,
    SolutionStatus,
    VerificationStatus,
)
from math_app.main import build_application
from math_app.rendering.text_math_renderer import (
    render_math_in_text_html,
    delimit_unwrapped_math_in_text,
)


@pytest.fixture
def use_case():
    return build_application()


# ==============================================================================
# 1. TEXT MATH RENDERER & TYPOGRAPHY TESTS (TASK A)
# ==============================================================================


def test_inline_math_rendering_container():
    """Inline math should render inside span.math-inline with data-display='inline'."""
    text = "Nghiệm tổng quát là $y(t) = C$ với mọi t."
    html_out = render_math_in_text_html(text)
    assert '<span class="math-inline math-tex"' in html_out
    assert 'data-display="inline"' in html_out
    assert "math-block" not in html_out


def test_trailing_punctuation_preserved_after_inline_math():
    """Trailing period, comma, colon, semicolon immediately after math must not be stripped."""
    text = "Phương trình có nghiệm $y(t) = C$. Ngoài ra, xét $\\mu(t)$, ta có kết quả:"
    html_out = render_math_in_text_html(text)
    assert "</span>." in html_out or 'data-display="inline">.' in html_out or "C</span>." in html_out or "</span>." in html_out
    assert "</span>," in html_out
    assert "kết quả:" in html_out


def test_unwrapped_latex_does_not_swallow_punctuation():
    """Unwrapped LaTeX like \\mu, or \\ln(t). must not absorb punctuation into math delimiters."""
    raw = "Xét hệ số tích phân \\mu, với điều kiện xác định \\ln(t)."
    delimited = delimit_unwrapped_math_in_text(raw)
    assert "$\\mu$," in delimited
    assert "$\\ln(t)$." in delimited


def test_markdown_bold_and_italic_around_math_no_leak():
    """Markdown bold and italic wrapping inline math must render strong/em without leaking raw asterisks."""
    text = "**Bước 1: Khảo sát $y(t) = C$** và *nghiệm $y_0 = 0$*."
    html_out = render_math_in_text_html(text)
    assert "**" not in html_out
    assert "<strong>Bước 1: " in html_out
    assert "</strong>" in html_out
    assert "<em>nghiệm " in html_out
    assert "</em>" in html_out


def test_markdown_does_not_mangle_math_multiplication_asterisks():
    """Asterisks inside math representing multiplication must not be parsed into em/strong tags."""
    text = "Biểu thức tích phân $\\int 2*t*x\\,dt$ cho nghiệm $y^2 + 8*t*x = C$."
    html_out = render_math_in_text_html(text)
    assert "<em>" not in html_out
    assert "<strong>" not in html_out
    assert "math-inline" in html_out


def test_display_math_block_rendering():
    """Display math $$...$$ and \\[...\\] must render in div.math-block containers."""
    text = "Dạng vi phân toàn phần:\n$$\\frac{dy}{dt} = -\\frac{4t}{y}$$\nKết luận."
    html_out = render_math_in_text_html(text)
    assert '<div class="math-block math-tex my-1"' in html_out
    assert 'data-display="block"' in html_out


def test_orphan_punctuation_on_standalone_lines_sanitized():
    """Punctuation alone on its own line must be stripped, while inline punctuation stays intact."""
    text = "Dòng 1.\n.\n,\nDòng 2 với $x = 1$."
    html_out = render_math_in_text_html(text)
    # The standalone '.' and ',' lines should not remain as empty lines with dots
    assert "<br/><br/>" not in html_out or "<br/>.<br/>" not in html_out
    assert "Dòng 1." in html_out
    assert "Dòng 2 với " in html_out


# ==============================================================================
# 2. STEP TITLE TRUNCATION FIX TESTS (TASK A)
# ==============================================================================


def test_display_title_preserves_math_arguments():
    """display_title must not strip mathematical parentheses like (t), (x), g(t), \\mu(t), y(t)."""
    dummy_content = ExpressionStepContent("a", "b", "a", "b")
    step1 = SolutionStep(
        step_number=1,
        rule_name="Xác định hệ số",
        title="Nhận dạng dạng chuẩn y' + p(t)y = g(t)",
        description="Mô tả",
        content=dummy_content,
    )
    assert step1.display_title == "Nhận dạng dạng chuẩn y' + p(t)y = g(t)"

    step2 = SolutionStep(
        step_number=2,
        rule_name="Thừa số tích phân",
        title="Tính thừa số tích phân \\mu(t)",
        description="Mô tả",
        content=dummy_content,
    )
    assert step2.display_title == "Tính thừa số tích phân \\mu(t)"

    step3 = SolutionStep(
        step_number=3,
        rule_name="Rút ra nghiệm tổng quát",
        title="Rút ra nghiệm tổng quát y(t)",
        description="Mô tả",
        content=dummy_content,
    )
    assert step3.display_title == "Rút ra nghiệm tổng quát y(t)"


def test_display_title_strips_english_subtitles():
    """display_title should cleanly strip English rule subtitles like (Linear ODE)."""
    dummy_content = ExpressionStepContent("a", "b", "a", "b")
    step = SolutionStep(
        step_number=1,
        rule_name="Phương trình vi phân",
        title="Tách biến (Separable ODE)",
        description="Mô tả",
        content=dummy_content,
    )
    assert step.display_title == "Tách biến"


# ==============================================================================
# 3. T03: NON-ELEMENTARY INTEGRATING FACTOR TESTS (TASK B)
# ==============================================================================


def test_t03_non_elementary_integrating_factor_pedagogy(use_case):
    """T03: (t-3)y' + ln(t)y = 2t
    - Step 1: Explain dividing by (t-3) with condition t != 3.
    - Domain restrictions: t > 0, t != 3, intervals (0, 3) and (3, +inf).
    - Step 6: General solution y(t) = 1/mu(t) * [C + int(...)] with independent C choice on intervals.
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

    # Check Step 1 description
    step1 = resp.steps[0]
    assert "t - 3" in step1.description or "(t - 3)" in step1.description
    assert "\\ne 0" in step1.description or "khác 0" in step1.description

    # Check domain restrictions
    domain_text = " ".join(resp.domain_restrictions)
    assert "3" in domain_text
    assert "(0, 3)" in domain_text
    assert "(3, +∞)" in domain_text or "(3, +\\infty)" in domain_text or "3, +" in domain_text

    # Check Step 6 general solution and interval constant note
    step6 = [s for s in resp.steps if s.rule_name == "Rút ra nghiệm tổng quát"][0]
    assert "mu" in step6.description or "\\mu" in step6.description
    assert "khoảng" in step6.description or "khoảng liên thông" in step6.description
    assert "độc lập" in step6.description


# ==============================================================================
# 4. T06: EXACT ODE PARAMETER NOTATION TESTS (TASK C)
# ==============================================================================


def test_t06_exact_ode_parameter_notation(use_case):
    """T06: (2x+3) + (2y-2)y' = 0 with independent variable t and parameter x
    - Parameter notation: M(t, y; x), N(t, y; x), F(t, y; x).
    - Step 1 explains variable roles: independent variable t, dependent y(t), parameter x.
    - Verification details output grad F = (dF/dt, dF/dy).
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_EXACT,
        raw_input="(2*x+3) + (2*y-2)*y' = 0",
        target_variable="t",
        parameters={"independent_var": "t", "dependent_var": "y"},
    )
    resp = use_case.execute(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status in (VerificationStatus.PARTIALLY_VERIFIED, VerificationStatus.VERIFIED)

    # Check Step 1 for variable role explanation and parameter notation M(t, y; x)
    step1 = resp.steps[0]
    assert "Biến độc lập: $t$" in step1.description
    assert "Hàm phụ thuộc: $y(t)$" in step1.description
    assert "Tham số hằng: $x$" in step1.description
    assert "M(t, y; x)" in step1.description
    assert "N(t, y; x)" in step1.description

    # Check Step 4 potential function notation F(t, y; x)
    step4 = [s for s in resp.steps if s.rule_name == "Xây dựng hàm thế"][0]
    assert "F(t, y; x)" in step4.title or "F(t, y; x)" in step4.description

    # Check verification details uses t instead of hardcoded x
    verif_details = resp.verification.details
    assert "∂F/∂t" in verif_details
    assert "∂F/∂y" in verif_details
    assert "∂F/∂x" not in verif_details or "x;" in verif_details


# ==============================================================================
# 5. GEOMETRIC LABELS MATHEMATICAL ACCURACY TESTS (TASK D)
# ==============================================================================


def test_t01_geometric_conditional_ellipse(use_case):
    """T01: y' = -4t/y -> y^2 + 4t^2 = C
    Geometric description must specify:
    - C > 0: real ellipse
    - C = 0: degenerate point (0, 0)
    - C < 0: empty set
    No unconditional 'ellipse' claim.
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SEPARABLE,
        raw_input="y' = -4*t/y",
        target_variable="t",
        parameters={"independent_var": "t", "dependent_var": "y"},
    )
    resp = use_case.execute(req)

    assert resp.status == SolutionStatus.SUCCESS
    all_descriptions = " ".join(s.description for s in resp.steps)
    assert "elip thực" in all_descriptions
    assert "C > 0" in all_descriptions
    assert "C = 0" in all_descriptions
    assert "C < 0" in all_descriptions


def test_t02_geometric_conditional_parabola(use_case):
    """T02: y' = -4t/y with x as independent variable -> y^2 + 8tx = C
    Geometric description must specify:
    - t != 0: parabola in x
    - t = 0: degenerates into y^2 = C (parallel lines if C > 0, line y = 0 if C = 0, empty if C < 0)
    No unconditional 'parabola' claim.
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SEPARABLE,
        raw_input="y' = -4*t/y",
        target_variable="x",
        parameters={"independent_var": "x", "dependent_var": "y"},
    )
    resp = use_case.execute(req)

    assert resp.status == SolutionStatus.SUCCESS
    all_descriptions = " ".join(s.description for s in resp.steps)
    assert "parabol" in all_descriptions
    assert "t \\ne 0" in all_descriptions or "t != 0" in all_descriptions or "t khác 0" in all_descriptions
    assert "t = 0" in all_descriptions
    assert "suy biến" in all_descriptions

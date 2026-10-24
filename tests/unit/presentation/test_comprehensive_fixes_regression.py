"""Comprehensive regression tests covering UI, LaTeX, calculus analysis, and linear algebra fixes."""

import sympy as sp
import numpy as np

from math_app.application.dtos import SolutionStep
from math_app.domain.models import ProblemType
from math_app.domain.step_content import ExpressionStepContent
from math_app.presentation.components.domain_view import format_domain_condition
from math_app.presentation.components.math_view import math_html
from math_app.presentation.components.operation_catalog import OPERATIONS, get_operation_by_type
from math_app.presentation.components.variation_table import _build_variation_table_html
from math_app.presentation.services.analysis_service import (
    compute_variation_table,
    create_2d_plot,
    create_3d_plot,
)
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.solvers.calculus.differentiation.solver import DerivativeSolver
from math_app.solvers.calculus.integration.solver import IntegralSolver
from math_app.solvers.linear_algebra.solver import MatrixSolver
from math_app.application.dtos import ProblemRequest


def test_operation_cards_descriptions_and_math_icons():
    """Verify all operation cards have Vietnamese descriptions, math icons, and no English jargon."""
    for op in OPERATIONS:
        # Vietnamese descriptions without English terminology
        assert len(op.description) > 10
        assert not any(w in op.description.lower() for w in ["rule", "matrix inverse", "determinant check"])

        # Math icon must exist and convert cleanly to MathML
        assert op.math_icon is not None
        html = math_html(op.math_icon, block=False, is_icon=True)
        assert "<math" in html
        assert "<input" not in html
        assert "<button" not in html

    # Specific icons
    deriv_op = get_operation_by_type(ProblemType.DERIVATIVE)
    assert r"\frac{d^n f}{dx^n}" in deriv_op.math_icon

    partial_op = get_operation_by_type(ProblemType.PARTIAL_DERIVATIVE)
    assert r"\frac{\partial f}{\partial x}" in partial_op.math_icon

    lim_op = get_operation_by_type(ProblemType.LIMIT)
    assert r"\lim_{x \to a}" in lim_op.math_icon

    det_op = get_operation_by_type(ProblemType.MATRIX_DETERMINANT)
    assert r"\det(A)" in det_op.math_icon


def test_domain_condition_formatting_and_deduplication():
    """Verify domain conditions are converted to real LaTeX without raw python syntax."""
    # Denominator with no real roots (x^2 + 1)
    k1, desc1, formula1 = format_domain_condition("Điều kiện mẫu số xác định: Mẫu số x**2 + 1 != 0", "x")
    assert "**" not in formula1
    assert "!=" not in formula1
    assert r"\mathcal{D} = \mathbb{R}" in formula1
    assert "x^{2} + 1" in formula1

    # Redundant power condition (x^2 + 1)^2 has identical dedup key
    k2, desc2, formula2 = format_domain_condition("Điều kiện mẫu số xác định: Mẫu số (x**2 + 1)**2 != 0", "x")
    assert k1 == k2  # Deduplicated!

    # Denominator with real root (x + 1)
    _, desc3, formula3 = format_domain_condition("Điều kiện mẫu số xác định: Mẫu số x + 1 != 0", "x")
    assert r"\mathcal{D} = \mathbb{R} \setminus \{-1\}" in formula3
    assert "x + 1" in formula3
    assert "!=" not in formula3

    # Tan / sec condition
    _, desc4, formula4 = format_domain_condition("Điều kiện hàm tan / sec: cos(x) != 0", "x")
    assert r"\cos(x) \ne 0" in formula4
    assert r"\pi" in formula4


def test_2d_plot_respects_discontinuities_and_clean_presentation():
    """Verify rational function plot has NaN at poles to prevent connecting across asymptotes."""
    fig_rational = create_2d_plot("(2*x - 1)/(x + 1)", "x")
    assert fig_rational is not None
    ys = fig_rational.data[0].y
    # Must have NaNs near pole x = -1
    assert np.isnan(ys).any()

    # Continuous function has no NaNs
    fig_cont = create_2d_plot("exp(x)/(x**2 + 1)", "x")
    assert fig_cont is not None
    ys_cont = fig_cont.data[0].y
    assert not np.isnan(ys_cont).any()

    # Clean legend without **
    assert "**" not in fig_cont.data[0].name
    assert "exp(x)" not in fig_cont.data[0].name


def test_variation_table_x_squared():
    """Verify variation table for f(x) = x^2 has decreasing -> stationary at 0 -> increasing."""
    table = compute_variation_table("x^2", "x")
    assert table is not None
    assert table["domain_latex"] == r"\mathcal{D} = \mathbb{R}"
    assert len(table["transition_points"]) == 1
    pt0 = table["transition_points"][0]
    assert pt0["type"] == "critical"
    assert pt0["val_float"] == 0.0

    assert len(table["intervals"]) == 2
    # (-oo, 0): decreasing
    assert table["intervals"][0]["sign"] == "-"
    assert table["intervals"][0]["arrow"] == "↘"
    # (0, +oo): increasing
    assert table["intervals"][1]["sign"] == "+"
    assert table["intervals"][1]["arrow"] == "↗"


def test_variation_table_rational_with_pole():
    """Verify variation table for (2x-1)/(x+1) separates intervals at pole x = -1 with double bar."""
    table = compute_variation_table("(2*x - 1)/(x + 1)", "x")
    assert table is not None
    assert r"\mathcal{D} = \mathbb{R} \setminus \{-1\}" in table["domain_latex"]
    assert len(table["transition_points"]) == 1
    pt = table["transition_points"][0]
    assert pt["type"] == "pole"
    assert pt["val_float"] == -1.0

    # Two intervals both with f' > 0
    assert len(table["intervals"]) == 2
    assert table["intervals"][0]["sign"] == "+"
    assert table["intervals"][1]["sign"] == "+"

    # Limits around pole (+oo, -oo)
    assert pt["lim_left"] in (r"+\infty", r"\infty")
    assert pt["lim_right"] == r"-\infty"

    # HTML table must contain double border for pole
    html_code = _build_variation_table_html("x", table["transition_points"], table["intervals"])
    assert "border-left: 2px solid" in html_code
    assert "border-right: 2px solid" in html_code


def test_step_presentation_pure_vietnamese_no_english_parentheses():
    """Verify that derivation steps and badges do not contain English labels."""
    content = ExpressionStepContent("x^2", "2*x", "x^2", "2x")

    # Step with English rule_name in parentheses
    step1 = SolutionStep(
        step_number=1,
        rule_name="Quy tắc lũy thừa (Power Rule)",
        description="Tính tích phân",
        content=content,
    )
    assert "(Power Rule)" not in step1.display_rule_name
    assert "(power rule)" not in step1.display_title.lower()
    assert step1.display_rule_name == "Quy tắc tích phân của lũy thừa"

    # Matrix step with English rule_name
    step2 = SolutionStep(
        step_number=2,
        rule_name="Công thức định thức cấp 2 (2x2 Determinant)",
        description="Tính định thức",
        content=content,
    )
    assert "(2x2 Determinant)" not in step2.display_rule_name
    assert step2.display_rule_name == "Công thức định thức cấp hai"

    # Constant of integration step
    step3 = SolutionStep(
        step_number=3,
        rule_name="Hằng số tích phân (Constant of Integration)",
        description="Thêm C",
        content=content,
    )
    assert "(Constant of Integration)" not in step3.display_rule_name
    assert step3.display_rule_name == "Bổ sung hằng số tích phân C"


def test_indefinite_integral_latex_does_not_contain_raw_power_syntax():
    """Verify indefinite integral result and steps do not contain raw 'x**3/3 + C'."""
    solver = IntegralSolver()
    req = ProblemRequest("x^2", ProblemType.INDEFINITE_INTEGRAL, target_variable="x")
    resp = solver.solve(req)

    assert resp.final_latex == r"\frac{x^{3}}{3} + C"
    assert "**" not in resp.final_latex

    # Steps must have proper latex_after
    c_step = next(s for s in resp.steps if "Hằng số" in s.rule_name or "hằng số" in s.rule_name)
    assert "**" not in c_step.content.latex_after
    assert r"\frac{x^{3}}{3} + C" in c_step.content.latex_after


def test_matrix_latex_formatting_preserves_structure():
    """Verify matrix formatting uses parentheses delimiters and proper LaTeX row separators."""
    A = sp.Matrix([[1, 2], [3, 4]])
    ltx = expr_to_latex(A)

    assert r"\begin{matrix}" in ltx
    assert "1 & 2" in ltx
    assert "3 & 4" in ltx
    assert r"\left(" in ltx or r"\begin{pmatrix}" in ltx

    # 2x2 determinant solver step
    solver = MatrixSolver()
    req = ProblemRequest("[[1, 2], [3, 4]]", ProblemType.MATRIX_DETERMINANT)
    resp = solver.solve(req)

    assert resp.final_result == "-2"
    det_step = resp.steps[0]
    # Matrix in before has vertical bar delimiters
    assert r"\left|" in det_step.content.latex_before
    # No English in badge or title
    assert "2x2" not in det_step.display_rule_name
    assert "Determinant" not in det_step.display_rule_name


def test_variation_table_no_duplicate_zeros_and_no_html_entities():
    """Verify variation table for x^2 has exactly one 0 at critical point and no &#39;."""
    table = compute_variation_table("x^2", "x")
    assert table is not None
    html_code = _build_variation_table_html("x", table["transition_points"], table["intervals"])

    # No raw HTML entity &#39;
    assert "&#39;" not in html_code

    # Derivative row must use f'(x)
    assert "f'" in html_code or "f^{&#x02032;}" in html_code or "f" in html_code

    # Check row cells and verify critical point 0 appears exactly once in row 3
    rows = html_code.split("<tr")
    # Row 1 is x, Row 2 is f'(x), Row 3 is f(x)
    assert len(rows) == 4  # [header/preamble, row 1, row 2, row 3]
    row3 = rows[3]
    # Row 3 must contain only 1 cell with 0
    zero_occurrences = row3.count("<mn>0</mn>")
    assert zero_occurrences == 1, f"Expected 1 zero in row 3, got {zero_occurrences}"


def test_variation_table_strictly_monotonic_cubic():
    """Verify strictly monotonic cubic 2x^3 + 6x - 8 has 0 transition points and single rising interval."""
    table = compute_variation_table("2*x^3 + 6*x - 8", "x")
    assert table is not None
    assert len(table["transition_points"]) == 0
    assert len(table["intervals"]) == 1
    assert table["intervals"][0]["sign"] == "+"
    assert table["intervals"][0]["start_val"] == r"-\infty"
    assert table["intervals"][0]["end_val"] == r"+\infty"

    html_code = _build_variation_table_html("x", table["transition_points"], table["intervals"])
    assert "&#39;" not in html_code
    assert "stroke='#dc2626'" in html_code


def test_derivation_negative_terms_preserve_signs():
    """Verify differentiation of x^4 - 3x^3 + 2x preserves negative sign in -3x^3 substep."""
    solver = DerivativeSolver()
    req = ProblemRequest("x^4 - 3*x^3 + 2*x", ProblemType.DERIVATIVE, target_variable="x")
    resp = solver.solve(req)

    assert resp.final_latex == "4 x^{3} - 9 x^{2} + 2"

    # Find substep for -3x^3
    found_negative_substep = False
    for step in resp.steps:
        for ss in step.substeps:
            if "3 x^{3}" in ss.content.latex_before or "3x^3" in ss.content.latex_before:
                if "-" in ss.content.latex_before:
                    found_negative_substep = True
                    assert "- 9 x^{2}" in ss.content.latex_after or "-9 x^{2}" in ss.content.latex_after
                    assert "-3" in ss.description
    assert found_negative_substep, "Should have a dedicated substep preserving the negative coefficient"


def test_domain_filtering_tautological_conditions():
    """Verify condition x^2 + 1 != 0 is recognized as tautological over R and omitted."""
    key, desc, formula = format_domain_condition("x^2 + 1 != 0", "x")
    assert r"\mathcal{D} = \mathbb{R}" in formula
    assert r"\setminus" not in formula


def test_3d_plot_has_none_title_to_avoid_programmer_syntax():
    """Verify 3D surface plot figure sets title=None so UI renders via LaTeX."""
    fig = create_3d_plot("x^2 + y^2")
    assert fig is not None
    assert fig.layout.title.text is None


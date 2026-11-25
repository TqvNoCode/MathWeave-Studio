"""Unit and regression tests for equation rendering bugfix:
Proper LaTeX representation of exponents, derivatives, signs, and clean MathML rendering.
"""

from __future__ import annotations

import pytest
import sympy as sp
from nicegui import Client, ui

from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType
from math_app.input.ode_parser import parse_second_order_ode_input
from math_app.input.parser import parse_safe_expression
from math_app.presentation.components.math_view import math_html, ui_math
from math_app.presentation.components.problem_statement import format_problem_statement_latex
from math_app.rendering.latex.formatter import expr_to_latex


def test_case_1_polynomial_forcing():
    """1. Polynomial forcing: 3*t^2."""
    raw = "y'' - 3*y' - 4*y = 3*t^2"
    parsed = parse_second_order_ode_input(raw, target_variable="t")
    t = sp.Symbol("t")
    assert sp.simplify(parsed.rhs_expr - 3 * t**2) == 0

    stmt = format_problem_statement_latex(raw, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "t")
    assert r"\frac{d^2y}{dt^2}" in stmt
    assert r"- 3\frac{dy}{dt}" in stmt
    assert "- 4y" in stmt
    assert "= 3 t^{2}" in stmt or "= 3 t^2" in stmt
    assert "*" not in stmt

    html_out = math_html(stmt)
    assert "<msup><mi>t</mi><mn>2</mn></msup>" in html_out or "<msup><mi>t</mi>" in html_out
    assert "&#x0002A;" not in html_out


def test_case_2_exponential_forcing_canonical():
    """2. Exponential forcing: 3*exp(2*t)."""
    raw = "y'' - 3*y' - 4*y = 3*exp(2*t)"
    parsed = parse_second_order_ode_input(raw, target_variable="t")
    t = sp.Symbol("t")
    assert sp.simplify(parsed.rhs_expr - 3 * sp.exp(2 * t)) == 0

    stmt = format_problem_statement_latex(raw, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "t")
    assert r"\frac{d^2y}{dt^2} - 3\frac{dy}{dt} - 4y = 3 e^{2 t}" == stmt
    assert "*" not in stmt

    html_out = math_html(stmt)
    # Exponent is structurally an <msup> with base e and exponent 2t
    assert "<msup><mi>e</mi>" in html_out
    assert "&#x0002A;" not in html_out


def test_case_3_trigonometric_forcing():
    """3. Trigonometric forcing: sin(2*t)."""
    raw = "y'' + 4*y = sin(2*t)"
    parsed = parse_second_order_ode_input(raw, target_variable="t")
    t = sp.Symbol("t")
    assert sp.simplify(parsed.rhs_expr - sp.sin(2 * t)) == 0

    stmt = format_problem_statement_latex(raw, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "t")
    assert r"\frac{d^2y}{dt^2} + 4y = \sin{\left(2 t \right)}" == stmt
    assert "*" not in stmt

    html_out = math_html(stmt)
    assert "<mi>sin</mi>" in html_out
    assert "&#x0002A;" not in html_out


def test_case_4_negative_exponential_forcing():
    """4. Negative exponential: -5*exp(-3*t)."""
    raw = "y'' + 2*y' + y = -5*exp(-3*t)"
    parsed = parse_second_order_ode_input(raw, target_variable="t")
    t = sp.Symbol("t")
    assert sp.simplify(parsed.rhs_expr - (-5 * sp.exp(-3 * t))) == 0

    stmt = format_problem_statement_latex(raw, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "t")
    assert stmt == r"\frac{d^2y}{dt^2} + 2\frac{dy}{dt} + y = - 5 e^{- 3 t}"
    assert "*" not in stmt

    html_out = math_html(stmt)
    assert "<msup><mi>e</mi>" in html_out
    assert "&#x0002A;" not in html_out


def test_case_5_resonance_forcing():
    """5. Resonance forcing: t*exp(t)."""
    raw = "y'' - 2*y' + y = t*exp(t)"
    parsed = parse_second_order_ode_input(raw, target_variable="t")
    t = sp.Symbol("t")
    assert sp.simplify(parsed.rhs_expr - t * sp.exp(t)) == 0

    stmt = format_problem_statement_latex(raw, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "t")
    assert r"\frac{d^2y}{dt^2} - 2\frac{dy}{dt} + y = t e^{t}" == stmt
    assert "*" not in stmt

    html_out = math_html(stmt)
    assert "<msup><mi>e</mi><mrow><mi>t</mi></mrow></msup>" in html_out
    assert "&#x0002A;" not in html_out


def test_case_6_fractional_coefficient():
    """6. Fractional coefficients: (1/2)*y'' + y' - 3*y = 0."""
    raw = "(1/2)*y'' + y' - 3*y = 0"
    parsed = parse_second_order_ode_input(raw, target_variable="t")
    assert parsed.a_coeff == sp.Rational(1, 2)
    assert parsed.b_coeff == 1
    assert parsed.c_coeff == -3

    stmt = format_problem_statement_latex(raw, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "t")
    assert r"\frac{1}{2}\frac{d^2y}{dt^2} + \frac{dy}{dt} - 3y = 0" == stmt
    assert "*" not in stmt

    html_out = math_html(stmt)
    assert "<mfrac><mrow><mn>1</mn></mrow><mrow><mn>2</mn></mrow></mfrac>" in html_out
    assert "&#x0002A;" not in html_out


def test_case_7_homogeneous_equations():
    """7. Homogeneous equations: y'' + 4y = 0 and y'' - 3y' - 4y = 0."""
    raw1 = "y'' + 4*y = 0"
    stmt1 = format_problem_statement_latex(raw1, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "t")
    assert stmt1 == r"\frac{d^2y}{dt^2} + 4y = 0"

    raw2 = "y'' - 3*y' - 4*y = 0"
    stmt2 = format_problem_statement_latex(raw2, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "t")
    assert stmt2 == r"\frac{d^2y}{dt^2} - 3\frac{dy}{dt} - 4y = 0"


def test_case_8_equations_containing_parentheses():
    """8. Equations containing parentheses: (3*t + 1)*exp(2*t)."""
    raw = "y'' - 3*y' - 4*y = (3*t + 1)*exp(2*t)"
    parsed = parse_second_order_ode_input(raw, target_variable="t")
    t = sp.Symbol("t")
    assert sp.simplify(parsed.rhs_expr - (3 * t + 1) * sp.exp(2 * t)) == 0

    stmt = format_problem_statement_latex(raw, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "t")
    assert r"\left(3 t + 1\right) e^{2 t}" in stmt
    assert "*" not in stmt

    html_out = math_html(stmt)
    assert "<msup><mi>e</mi>" in html_out
    assert "&#x0002A;" not in html_out


def test_case_9_supported_and_unsupported_e_syntax():
    """9. Both supported and unsupported e exponent syntax."""
    # 9a. Supported: 3*e^(2*t) produces exact same mathematical expression and clean LaTeX
    raw_e = "y'' - 3*y' - 4*y = 3*e^(2*t)"
    parsed_e = parse_second_order_ode_input(raw_e, target_variable="t")
    t = sp.Symbol("t")
    assert sp.simplify(parsed_e.rhs_expr - 3 * sp.exp(2 * t)) == 0

    stmt_e = format_problem_statement_latex(raw_e, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "t")
    assert stmt_e == r"\frac{d^2y}{dt^2} - 3\frac{dy}{dt} - 4y = 3 e^{2 t}"
    assert "*" not in stmt_e
    assert "e(" not in stmt_e  # Exponent must NOT be rendered as baseline parentheses

    html_e = math_html(stmt_e)
    assert "<msup><mi>e</mi>" in html_e
    assert "&#x0002A;" not in html_e

    # 9b. Supported: e^t and e**(2*t)
    expr_simple = parse_safe_expression("e^t", target_variable="t")
    assert expr_to_latex(expr_simple) == "e^{t}"

    expr_starstar = parse_safe_expression("e**(2*t)", target_variable="t")
    assert expr_to_latex(expr_starstar) == "e^{2 t}"

    # 9c. Unsupported syntax: e used as a function name e(2*t)
    with pytest.raises(InvalidInputError) as exc_fn:
        parse_safe_expression("3*e(2*t)", target_variable="t")
    assert "Hàm không xác định 'e'" in str(exc_fn.value)

    # 9d. Unsupported syntax: trailing caret operator e^
    with pytest.raises(InvalidInputError) as exc_caret:
        parse_safe_expression("3*e^", target_variable="t")
    assert "Lỗi cú pháp" in str(exc_caret.value)

    # 9e. Unsupported syntax: unclosed bracket e^(2*t
    with pytest.raises(InvalidInputError) as exc_bracket:
        parse_safe_expression("3*e^(2*t", target_variable="t")
    assert "Dấu ngoặc" in str(exc_bracket.value)


def test_ui_math_rendering_in_client():
    """Verify actual NiceGUI Client DOM rendering for reported equation."""
    client = Client(ui.page("/test_eq_render"))
    with client:
        stmt = format_problem_statement_latex(
            "y'' - 3*y' - 4*y = 3*e^(2*t)",
            ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
            "t",
        )
        el = ui_math(stmt, block=True)

    # Inspect generated inner HTML content
    html_content = el._props.get("innerHTML", "")
    assert "<msup><mi>e</mi>" in html_content
    assert "&#x0002A;" not in html_content
    assert "data-tex" in html_content
    assert "3 e^{2 t}" in html_content or "3\\,e^{2\\,t}" in html_content

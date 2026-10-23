"""Unit tests for LaTeX rendering formatter."""

import sympy as sp

from math_app.rendering.latex.formatter import derivative_step_to_latex, expr_to_latex


def test_expr_to_latex_powers_and_functions():
    x = sp.Symbol("x")
    expr = (x ** 2) * sp.sin(x)
    latex_str = expr_to_latex(expr)
    assert "x^{2}" in latex_str or "x^2" in latex_str
    assert r"\sin" in latex_str


def test_expr_to_latex_from_string():
    latex_str = expr_to_latex("x**2 + 1")
    assert "x^{2}" in latex_str or "x^2" in latex_str


def test_derivative_step_to_latex():
    before_latex, after_latex = derivative_step_to_latex("x**2", "2*x")
    assert "x^{2}" in before_latex or "x^2" in before_latex
    assert "2 x" in after_latex or "2" in after_latex

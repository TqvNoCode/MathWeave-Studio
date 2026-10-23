"""Canonical LaTeX formatter for mathematical expressions."""

from __future__ import annotations

import sympy as sp


def expr_to_latex(expr: sp.Expr | str) -> str:
    """Convert a SymPy expression or mathematical string into canonical LaTeX."""
    if isinstance(expr, str):
        cleaned = expr.strip()
        # Handle integration constant "+ C" or "- C"
        if cleaned.endswith(" + C"):
            prefix = cleaned[:-4].strip()
            return f"{expr_to_latex(prefix)} + C"
        if cleaned.endswith(" - C"):
            prefix = cleaned[:-4].strip()
            return f"{expr_to_latex(prefix)} - C"
        try:
            from math_app.input.parser import parse_safe_expression
            expr = parse_safe_expression(cleaned, evaluate=False)
        except Exception:
            return cleaned

    if isinstance(expr, sp.MatrixBase):
        return sp.latex(expr, mat_delim="(")

    return sp.latex(expr)


def derivative_step_to_latex(operator_expr: str, result_expr: str) -> tuple[str, str]:
    """Format an unevaluated derivative step and its resulting derivative into LaTeX."""
    return expr_to_latex(operator_expr), expr_to_latex(result_expr)

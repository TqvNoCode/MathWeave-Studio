"""Canonical LaTeX formatter for mathematical expressions."""

from __future__ import annotations

import html
import re
import sympy as sp


def normalize_latex(latex_str: str) -> str:
    """Normalize LaTeX string to ensure full compatibility with MathML renderer.

    - Unescapes raw HTML entities (e.g. &#39; to ')
    - Normalizes unicode infinity to LaTeX infinity
    - Converts programmer exponents (**) to LaTeX (^)
    - Standardizes coefficient-variable spacing using thin mathematical space (\\,)
    - Replaces \\begin{aligned} ... \\end{aligned} with \\begin{align*} ... \\end{align*}
    - Encloses un-environmented '&' alignment sequences inside an align* environment
    """
    s = latex_str.strip()
    if not s:
        return ""

    # Unescape HTML entities if any were passed in
    s = html.unescape(s)

    # Normalize unicode infinity symbols to LaTeX commands
    s = s.replace("-∞", r"-\infty").replace("+∞", r"+\infty").replace("∞", r"\infty")

    # Normalize programmer syntax if present in displayed math strings
    s = re.sub(r"\*\*(\d+)", r"^{\1}", s)
    s = re.sub(r"\*\*([a-zA-Z])", r"^{\1}", s)

    # Standardize coefficient-variable spacing with thin space \,
    # Only applies to numeric coefficients followed by single variables, Greek commands, or radicals
    # e.g., 4 x^3 -> 4\,x^3, -9 x^2 -> -9\,x^2, 6x -> 6\,x, 2\sqrt{33} -> 2\,\sqrt{33}
    s = re.sub(
        r"(?<![a-zA-Z\\])"
        r"(\d+(?:\.\d+)?)"
        r"(?:\s*|\\,)*"
        r"(?<!\\)"
        r"([a-zA-Z](?![a-zA-Z])|"
        r"\\(?:alpha|beta|gamma|delta|epsilon|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega|sqrt))",
        r"\1\\,\2",
        s,
    )

    # Standardize radical followed by variable: \sqrt{33} t -> \sqrt{33}\,t
    s = re.sub(
        r"(\\sqrt\{[^}]+\})\s*([a-zA-Z](?![a-zA-Z]))",
        r"\1\\,\2",
        s,
    )

    # Convert aligned environments to align* (which latex2mathml natively maps to <mtable>)
    s = re.sub(r"\\begin\{aligned\}", r"\\begin{align*}", s)
    s = re.sub(r"\\end\{aligned\}", r"\\end{align*}", s)

    # If the string contains alignment marker '&' or line breaks '\\\\' and is not already wrapped
    # in an align/matrix/cases environment, wrap it in align*
    has_amp = "&" in s
    is_wrapped = any(
        env in s
        for env in (
            r"\begin{align",
            r"\begin{matrix",
            r"\begin{pmatrix",
            r"\begin{bmatrix",
            r"\begin{vmatrix",
            r"\begin{array",
            r"\begin{cases",
            r"\begin{split",
        )
    )
    if has_amp and not is_wrapped:
        s = f"\\begin{{align*}}\n{s}\n\\end{{align*}}"

    return s


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


def format_quadratic_root_latex(a: sp.Expr, b: sp.Expr, delta: sp.Expr, sign: int) -> str:
    """Format quadratic formula root r = (-b +- sqrt(delta)) / (2a) into textbook LaTeX."""
    sqrt_delta = sp.sqrt(delta)
    if sqrt_delta.is_rational:
        val = sp.simplify((-b + sign * sqrt_delta) / (2 * a))
        return expr_to_latex(val)

    val = sp.simplify((-b + sign * sqrt_delta) / (2 * a))
    num, denom = val.as_numer_denom()
    if denom == 1:
        return expr_to_latex(num)
    elif denom == -1:
        return expr_to_latex(-num)

    num_ltx = expr_to_latex(num)
    # If num_ltx is "- \sqrt{D} - C", reorder to "-C - \sqrt{D}" for standard pedagogical presentation
    m = re.match(r"^-\s*(\\sqrt\{[^}]+\})\s*-\s*(.+)$", num_ltx)
    if m:
        num_ltx = f"-{m.group(2)} - {m.group(1)}"

    denom_ltx = expr_to_latex(denom)
    if denom > 0:
        return f"\\frac{{{num_ltx}}}{{{denom_ltx}}}"
    else:
        neg_num = expr_to_latex(-num)
        pos_den = expr_to_latex(-denom)
        return f"-\\frac{{{neg_num}}}{{{pos_den}}}"


def derivative_step_to_latex(operator_expr: str, result_expr: str) -> tuple[str, str]:
    """Format an unevaluated derivative step and its resulting derivative into LaTeX."""
    return expr_to_latex(operator_expr), expr_to_latex(result_expr)

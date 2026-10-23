"""Math rendering component using native MathML with robust fallback."""

from __future__ import annotations

import html
import re
import latex2mathml.converter
from nicegui import ui


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
    # Only applies to numeric coefficients followed by single variables or Greek commands
    # e.g., 4 x^3 -> 4\,x^3, -9 x^2 -> -9\,x^2, 6x -> 6\,x
    s = re.sub(
        r"(?<![a-zA-Z\\])"
        r"(\d+(?:\.\d+)?)"
        r"(?:\s*|\\,)*"
        r"(?<!\\)"
        r"([a-zA-Z](?![a-zA-Z])|"
        r"\\(?:alpha|beta|gamma|delta|epsilon|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega))",
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


def math_html(latex_str: str, block: bool = False, is_icon: bool = False) -> str:
    """Convert LaTeX string to styled MathML HTML snippet without scrollbar artifacts."""
    if not latex_str or not latex_str.strip():
        return ""

    normalized = normalize_latex(latex_str)

    try:
        mathml = latex2mathml.converter.convert(normalized, display="block" if block else "inline")
        if is_icon:
            cls = "math-icon math-container select-none pointer-events-none"
        else:
            cls = "math-block" if block else "math-container"
        return f'<div class="{cls}">{mathml}</div>'
    except Exception:
        # Fallback to styled mathematical font span
        tag = "div" if block else "span"
        cls = (
            "math-fallback font-serif text-blue-900 tracking-wide select-none"
            if is_icon
            else "math-fallback font-serif text-blue-900 tracking-wide"
        )
        return f'<{tag} class="{cls}">{normalized}</{tag}>'


def ui_math(latex_str: str, block: bool = False, classes: str = "", is_icon: bool = False) -> ui.html:
    """Render a LaTeX mathematical formula inside a NiceGUI HTML element."""
    html_content = math_html(latex_str, block=block, is_icon=is_icon)
    element = ui.html(html_content)
    if classes:
        element.classes(classes)
    return element

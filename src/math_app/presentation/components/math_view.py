"""Math rendering component using native MathML with robust fallback."""

from __future__ import annotations

from nicegui import ui

from math_app.rendering.text_math_renderer import (
    convert_latex_to_mathml,
    render_math_in_text_html,
)


def math_html(latex_str: str, block: bool = False, is_icon: bool = False) -> str:
    """Convert LaTeX string to styled MathML HTML snippet without scrollbar artifacts."""
    return convert_latex_to_mathml(latex_str, block=block, is_icon=is_icon)


def ui_math(latex_str: str, block: bool = False, classes: str = "", is_icon: bool = False) -> ui.html:
    """Render a LaTeX mathematical formula inside a NiceGUI HTML element."""
    html_content = math_html(latex_str, block=block, is_icon=is_icon)
    element = ui.html(html_content)
    if classes:
        element.classes(classes)
    return element


def ui_math_text(text: str, classes: str = "") -> ui.html:
    """Render explanatory prose containing inline ($...$) or block ($$...$$) mathematical expressions into NiceGUI."""
    html_content = render_math_in_text_html(text)
    element = ui.html(html_content)
    if classes:
        element.classes(classes)
    return element

"""Presentation UI components."""

from math_app.presentation.components.footer import AUTHOR_CREDIT, render_footer
from math_app.presentation.components.input_bar import render_input_bar
from math_app.presentation.components.step_viewer import render_step, render_steps_container
from math_app.presentation.components.verification_badge import render_verification_badge

__all__ = [
    "AUTHOR_CREDIT",
    "render_footer",
    "render_input_bar",
    "render_step",
    "render_steps_container",
    "render_verification_badge",
]

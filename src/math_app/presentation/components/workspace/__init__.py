"""Workspace components for MathWeave Studio Screen B."""

from math_app.presentation.components.workspace.matrix_helper import render_matrix_helper_panel
from math_app.presentation.components.workspace.variable_selector import (
    get_variable_pool_for_operation,
    render_adaptive_variable_selector,
)

__all__ = [
    "get_variable_pool_for_operation",
    "render_adaptive_variable_selector",
    "render_matrix_helper_panel",
]

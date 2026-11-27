"""Shared UI primitive components for MathWeave Studio."""

from math_app.presentation.components.shared.action_labels import (
    PrimaryActionSpec,
    get_primary_action_spec,
)
from math_app.presentation.components.shared.example_chips import render_example_chips
from math_app.presentation.components.shared.feedback_cards import (
    render_empty_state_card,
    render_feedback_card,
    render_loading_card,
)
from math_app.presentation.components.shared.primary_button import primary_button
from math_app.presentation.components.shared.section_card import section_card
from math_app.presentation.components.shared.status_badge import status_badge
from math_app.presentation.components.shared.workspace_header import render_workspace_header

__all__ = [
    "PrimaryActionSpec",
    "get_primary_action_spec",
    "primary_button",
    "render_empty_state_card",
    "render_example_chips",
    "render_feedback_card",
    "render_loading_card",
    "render_workspace_header",
    "section_card",
    "status_badge",
]

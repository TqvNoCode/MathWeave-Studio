"""Reusable section card container with consistent border and shadow tokens."""

from __future__ import annotations

from nicegui import ui

from math_app.presentation.design_system.tokens import ELEVATION, RADIUS


def section_card(classes: str = "") -> ui.card:
    """Create a standard styled card container using centralized design tokens."""
    base_classes = (
        f"p-4 md:p-5 border border-slate-200 {RADIUS.LG} bg-white {ELEVATION.SM} w-full transition-all"
    )
    combined = f"{base_classes} {classes}".strip() if classes else base_classes
    return ui.card().classes(combined)

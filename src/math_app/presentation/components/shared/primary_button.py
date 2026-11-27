"""Reusable primary action button with standard tokens and hover transitions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from nicegui import ui

from math_app.presentation.design_system.tokens import ELEVATION, INTERACTION, RADIUS


def primary_button(
    text: str,
    icon: str | None = None,
    on_click: Callable[..., Any] | None = None,
    classes: str = "",
    aria_label: str | None = None,
) -> ui.button:
    """Create a standardized primary action button using Academic Blue tokens."""
    base_classes = (
        f"bg-blue-600 !bg-blue-600 hover:!bg-blue-700 text-white !text-white font-bold px-5 py-2.5 min-h-[40px] "
        f"{RADIUS.LG} {ELEVATION.SM} hover:{ELEVATION.MD} transition-all cursor-pointer {INTERACTION.FOCUS_RING}"
    )
    combined = f"{base_classes} {classes}".strip() if classes else base_classes
    btn = ui.button(text, icon=icon, on_click=on_click, color=None).props("unelevated no-caps")
    if aria_label:
        btn.props(f'aria-label="{aria_label}"')
    return btn.classes(combined)

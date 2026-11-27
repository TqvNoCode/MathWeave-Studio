"""Reusable status badge with WCAG AAA accessible color tokens."""

from __future__ import annotations

from nicegui import ui

from math_app.presentation.design_system.tokens import RADIUS, SEMANTIC


def status_badge(
    text: str,
    variant: str = "neutral",
    tooltip: str | None = None,
    classes: str = "",
) -> ui.badge:
    """Create a high-contrast status badge using semantic design tokens.

    Variants:
    - 'success': Verified / Valid results (Emerald, >8:1 contrast)
    - 'warning': Caution / Incomplete conditions (Amber, >8:1 contrast)
    - 'error': Failed / Inconsistent state (Red, >9:1 contrast)
    - 'info': Informational / Mode details (Blue, >8:1 contrast)
    - 'neutral': Default / Metadata (Slate, >9:1 contrast)
    """
    variant_lower = variant.lower()
    if variant_lower in ("success", "positive", "verified"):
        token = SEMANTIC.SUCCESS
    elif variant_lower in ("warning", "caution", "amber"):
        token = SEMANTIC.WARNING
    elif variant_lower in ("error", "negative", "failed"):
        token = SEMANTIC.ERROR
    elif variant_lower in ("info", "blue"):
        token = SEMANTIC.INFO
    else:
        token = SEMANTIC.NEUTRAL

    base_classes = (
        f"text-xs px-2.5 py-1 font-semibold {RADIUS.FULL} border inline-flex items-center gap-1 "
        "whitespace-normal max-w-full leading-snug text-left"
    )
    style = f"background-color: {token.bg}; border-color: {token.border}; color: {token.text};"
    combined_classes = f"{base_classes} {classes}".strip() if classes else base_classes

    badge = ui.badge(text, color=None).classes(combined_classes).style(style)
    if tooltip:
        with badge:
            ui.tooltip(tooltip)
    return badge

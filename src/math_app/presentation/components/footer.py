"""Shared application footer component for MathWeave Studio."""

from __future__ import annotations

from nicegui import ui

AUTHOR_CREDIT = "© 2026 by TQV"


def render_footer() -> ui.row:
    """Render a subtle, accessible footer containing author credit aligned at the bottom right.

    The footer follows page content naturally in the layout flow rather than acting
    as a fixed overlay, ensuring it never covers calculation results, plots, or buttons.
    """
    with ui.row().classes(
        "w-full items-center justify-end pt-4 pb-2 border-t border-slate-200/70 mt-auto"
    ) as footer_row:
        ui.label(AUTHOR_CREDIT).classes(
            "text-xs text-slate-500 font-medium tracking-wide select-none"
        )
    return footer_row

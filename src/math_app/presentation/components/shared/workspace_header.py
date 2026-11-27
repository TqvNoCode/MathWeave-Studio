"""Shared unified workspace identity header component."""

from __future__ import annotations

from nicegui import ui

from math_app.presentation.components.math_view import ui_math
from math_app.presentation.components.shared.status_badge import status_badge


def render_workspace_header(
    title: str,
    description: str,
    badge_text: str,
    math_icon: str | None = None,
    icon: str | None = None,
    badge_variant: str = "info",
) -> ui.row:
    """Render a standardized responsive workspace card header.

    Ensures consistent icon box sizing, readable wrapping of Vietnamese
    descriptions across mobile/desktop screens, and aligned domain/order badges.
    """
    with ui.row().classes(
        "flex-col sm:flex-row items-start sm:items-center justify-between w-full pb-3 border-b border-slate-100 gap-2.5 sm:gap-3 min-w-0"
    ) as header_row:
        with ui.row().classes("items-start sm:items-center gap-3 w-full sm:flex-1 min-w-0 flex-nowrap"):
            if math_icon:
                with ui.row().classes(
                    "px-2.5 sm:px-3 py-1.5 min-w-[2.75rem] sm:min-w-[3rem] max-w-[11rem] rounded-lg bg-blue-50 text-blue-800 items-center justify-center math-scroll-box shadow-xs shrink-0"
                ):
                    ui_math(
                        math_icon,
                        block=False,
                        classes="math-icon text-sm sm:text-base font-bold select-none pointer-events-none",
                        is_icon=True,
                    )
            elif icon:
                ui.icon(icon, size="1.4rem").classes("text-blue-600 shrink-0 mt-0.5 sm:mt-0")

            with ui.column().classes("gap-0.5 flex-1 min-w-0"):
                ui.label(title).classes("text-base md:text-lg font-bold text-slate-900 leading-snug break-words")
                ui.label(description).classes("text-xs text-slate-600 leading-relaxed break-words")

        status_badge(badge_text, variant=badge_variant, classes="shrink-0")

    return header_row

"""Sticky navigation bar component for workspace Screen B."""

from __future__ import annotations

from collections.abc import Callable
from nicegui import ui

from math_app.presentation.components.back_button import render_back_button


def render_sticky_nav_bar(
    title: str,
    domain: str,
    on_back: Callable[[], None],
    math_icon: str | None = None,
    icon: str | None = None,
    on_title_ready: Callable[[Callable[[str], None]], None] | None = None,
) -> ui.row:
    """Render compact, high-contrast sticky navigation bar with back action and synced title.

    Avoids repeating the workspace header's full math-icon badge and domain pill so
    top navigation stays lightweight while preserving context during vertical scroll.
    """
    with ui.row().classes(
        "w-full items-center justify-between bg-white px-3 py-2 rounded-xl border border-slate-200 shadow-sm sticky top-0 z-30 transition-all flex-wrap gap-2 min-w-0"
    ) as nav_row:
        with ui.row().classes("items-center gap-2 sm:gap-3 min-w-0 flex-1"):
            render_back_button(on_click=on_back)
            ui.separator().props("vertical").classes("hidden sm:block")

            with ui.row().classes("items-center gap-2 min-w-0 flex-1"):
                if icon:
                    ui.icon(icon, size="1.15rem").classes("text-blue-600 shrink-0 hidden sm:inline-flex")
                title_lbl = ui.label(title).classes(
                    "font-semibold text-slate-800 text-xs sm:text-sm break-words min-w-0"
                )
                if on_title_ready is not None:
                    on_title_ready(title_lbl.set_text)

        ui.label(domain).classes("text-[11px] font-medium text-slate-500 hidden md:inline-block shrink-0")

    return nav_row

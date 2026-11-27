"""Application Header component for MathWeave Studio."""

from __future__ import annotations

from collections.abc import Callable
from nicegui import ui

from math_app import __title__, __version__
from math_app.presentation.design_system.tokens import TYPOGRAPHY


def render_app_header(on_about_click: Callable[[], None]) -> ui.row:
    """Render the centralized application header with identity, version badge, and about action."""
    with ui.row().classes(
        "items-center justify-between w-full border-b border-slate-200 pb-3.5 md:pb-4 flex-wrap gap-3 min-w-0"
    ) as header_row:
        # Left branding block
        with ui.row().classes("items-center gap-3 min-w-0 flex-1"):
            with ui.avatar(icon="functions", color="primary", text_color="white").classes("shadow-sm shrink-0"):
                pass
            with ui.column().classes("gap-0 min-w-0 flex-1"):
                ui.label(__title__).classes(TYPOGRAPHY.APP_TITLE)
                ui.label("Phần mềm Hỗ trợ Học tập & Nghiên cứu Toán học Chuyên sâu").classes(
                    f"{TYPOGRAPHY.APP_SUBTITLE} break-words"
                )

        # Right actions block: Semantic accessible version button (About action)
        with ui.row().classes("items-center gap-2"):
            with ui.button(
                f"MVP · v{__version__}",
                on_click=on_about_click,
                color=None,
            ).props("no-caps flat dense").classes(
                "text-xs px-2.5 py-0.5 rounded-full bg-slate-700 text-white hover:bg-slate-600 transition-colors "
                "font-mono font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 "
                "focus-visible:ring-offset-2 cursor-pointer shadow-none"
            ).props('aria-label="Thông tin ứng dụng MathWeave Studio (About)"'):
                ui.tooltip("Thông tin ứng dụng (About)")

    return header_row

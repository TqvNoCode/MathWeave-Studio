"""Sticky navigation bar component for workspace Screen B."""

from __future__ import annotations

from collections.abc import Callable
from nicegui import ui

from math_app.presentation.components.back_button import render_back_button
from math_app.presentation.components.math_view import ui_math


def render_sticky_nav_bar(
    title: str,
    domain: str,
    on_back: Callable[[], None],
    math_icon: str | None = None,
    icon: str | None = None,
) -> ui.row:
    """Render high-contrast sticky navigation bar with back action, title, and domain badge."""
    with ui.row().classes(
        "w-full items-center justify-between bg-white p-3 rounded-xl border border-slate-200 shadow-sm sticky top-0 z-30 transition-all"
    ) as nav_row:
        with ui.row().classes("items-center gap-3"):
            render_back_button(on_click=on_back)
            ui.separator().props("vertical")

            with ui.row().classes("items-center gap-2"):
                if math_icon:
                    with ui.row().classes(
                        "px-3 py-1.5 min-w-[3rem] rounded-lg bg-blue-50 text-blue-800 items-center justify-center overflow-visible"
                    ):
                        ui_math(
                            math_icon,
                            block=False,
                            classes="math-icon text-base font-bold select-none pointer-events-none",
                            is_icon=True,
                        )
                elif icon:
                    ui.icon(icon, size="1.3rem").classes("text-blue-600")

                ui.label(title).classes("font-bold text-slate-900 text-sm md:text-base")

        # Accessible domain badge
        ui.badge(domain, color="blue-1").classes(
            "text-blue-900 font-semibold text-xs px-2.5 py-1 rounded-full hidden sm:inline-flex border border-blue-200"
        )

    return nav_row

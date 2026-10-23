"""High-contrast, accessible back-navigation component for MathWeave Studio."""

from __future__ import annotations

from collections.abc import Callable
from nicegui import ui


def render_back_button(on_click: Callable[[], None]) -> ui.button:
    """Render a high-contrast, accessible back button that returns to the operation catalog."""
    btn = (
        ui.button("Chọn dạng toán khác", icon="arrow_back", on_click=on_click)
        .props("outline color=primary no-caps")
        .classes(
            "bg-white text-blue-700 font-semibold text-xs md:text-sm px-3.5 py-1.5 rounded-xl shadow-xs "
            "hover:bg-blue-50 transition-all cursor-pointer flex items-center gap-1.5"
        )
    )
    return btn

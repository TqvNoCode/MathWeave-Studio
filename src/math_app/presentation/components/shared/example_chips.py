"""Accessible, high-contrast wrapping example chip group component."""

from __future__ import annotations

import html
from collections.abc import Callable, Sequence
from nicegui import ui

from math_app.presentation.design_system.tokens import INTERACTION


def render_example_chips(
    examples: Sequence[tuple[str, str]],
    on_select: Callable[[str], None],
    label: str = "Ví dụ mẫu:",
) -> ui.row | None:
    """Render high-contrast, mobile-wrapping example chips with keyboard focus support.

    Uses ``color=None`` + explicit ``INTERACTION.CHIP_SURFACE`` styling so Quasar
    never falls back to low-contrast dark text on blue chip backgrounds.
    """
    if not examples:
        return None

    with ui.row().classes("items-center gap-2 pt-1 flex-wrap w-full min-w-0") as chip_row:
        ui.label(label).classes("text-xs text-slate-600 font-semibold shrink-0")
        for chip_label, chip_value in examples:
            aria = html.escape(f"{label} {chip_label}", quote=True)
            chip = (
                ui.chip(
                    chip_label,
                    color=None,
                    on_click=lambda _=None, val=chip_value: on_select(val),
                )
                .props(f'outline clickable tabindex="0" role="button" aria-label="{aria}"')
                .classes(
                    f"mw-example-chip cursor-pointer text-xs px-2.5 py-1 rounded-full font-mono transition-colors "
                    f"{INTERACTION.CHIP_SURFACE} {INTERACTION.FOCUS_RING}"
                )
            )
            chip.on("keydown.enter", lambda _=None, val=chip_value: on_select(val))
            chip.on("keydown.space.prevent", lambda _=None, val=chip_value: on_select(val))
    return chip_row

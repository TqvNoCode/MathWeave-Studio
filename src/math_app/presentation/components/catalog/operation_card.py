"""Operation card presentation component for the Screen A catalog."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from nicegui import ui

from math_app.presentation.components.math_view import ui_math
from math_app.presentation.components.operation_catalog import OperationDef


def render_operation_card(
    op: OperationDef,
    on_select: Callable[[OperationDef], None],
) -> ui.card:
    """Render an individual interactive operation card for the catalog grid.

    Ensures full accessibility via mouse click, keyboard Enter, keyboard Space,
    visible focus ring, role="button", and accessible ARIA label.
    """
    def _handle_select(e: Any = None, selected_op: OperationDef = op) -> None:
        if e is not None:
            args = getattr(e, "args", None)
            if isinstance(args, dict) and args.get("repeat"):
                return
        on_select(selected_op)

    card = (
        ui.card()
        .classes(
            "p-4 border border-slate-200 hover:border-blue-500 hover:shadow-md transition-all "
            "cursor-pointer rounded-xl bg-white flex flex-col justify-between group h-full "
            "focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus:border-blue-500"
        )
        .props(f'tabindex="0" role="button" aria-label="Chọn dạng toán {op.title}: {op.description}"')
        .on("click", _handle_select)
        .on("keydown.enter", _handle_select)
        .on("keydown.space.prevent", _handle_select)
    )

    with card:
        with ui.column().classes("gap-2.5 w-full flex-grow"):
            # Header Row: Icon (Left) + Title (Immediately beside icon) + Navigation Arrow (Far right)
            with ui.row().classes("items-center justify-between w-full gap-2.5"):
                with ui.row().classes("items-center gap-2.5 flex-1 min-w-0"):
                    if op.math_icon:
                        with ui.row().classes(
                            "min-w-[3.25rem] h-12 px-2 shrink-0 rounded-lg bg-blue-50 text-blue-700 items-center justify-center "
                            "group-hover:bg-blue-600 group-hover:text-white transition-colors overflow-visible"
                        ):
                            ui_math(
                                op.math_icon,
                                block=False,
                                classes="math-icon font-bold select-none pointer-events-none",
                                is_icon=True,
                            )
                    else:
                        with ui.avatar(
                            icon=op.icon,
                            color="blue-50",
                            text_color="blue-700",
                            size="md",
                        ).classes(
                            "shrink-0 group-hover:bg-blue-600 group-hover:text-white transition-colors"
                        ):
                            pass

                    ui.label(op.title).classes(
                        "font-bold text-slate-800 text-sm md:text-base group-hover:text-blue-700 leading-snug flex-1 break-words"
                    )

                ui.icon("arrow_forward", size="1.2rem").classes(
                    "text-slate-300 group-hover:text-blue-600 transition-colors shrink-0 self-center"
                )

            # Description below header
            ui.label(op.description).classes("text-xs text-slate-500 leading-relaxed mt-0.5")

        # Action label aligned bottom-right
        with ui.row().classes("w-full justify-end items-center pt-2 text-xs"):
            ui.label("Chọn →").classes(
                "text-blue-600 font-semibold group-hover:translate-x-0.5 transition-transform shrink-0"
            )

    return card

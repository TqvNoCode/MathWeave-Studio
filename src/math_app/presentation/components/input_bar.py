"""Input bar component for formula entry and quick examples."""

from __future__ import annotations

from collections.abc import Callable
from nicegui import ui


def render_input_bar(on_solve: Callable[[str, str], None]) -> tuple[ui.input, ui.input]:
    """Render the formula input bar and preset example chips.

    Returns:
        tuple[ui.input, ui.input]: The expression input and variable input controls.
    """
    with ui.card().classes("w-full p-4 shadow-sm border rounded-lg bg-white"):
        with ui.row().classes("w-full items-center gap-4"):
            expr_input = ui.input(
                label="Biểu thức toán học f(x)",
                placeholder="Ví dụ: x^2 * sin(x)",
                value="x^2 * sin(x)",
            ).classes("flex-grow text-lg")

            var_input = ui.input(
                label="Biến số",
                value="x",
            ).classes("w-24 text-lg")

            ui.button(
                "Tính đạo hàm",
                icon="calculate",
                color="primary",
                on_click=lambda: on_solve(expr_input.value, var_input.value),
            ).classes("px-6 py-2 text-base")

            expr_input.on("keydown.enter", lambda: on_solve(expr_input.value, var_input.value))

        with ui.row().classes("items-center gap-2 mt-2"):
            ui.label("Ví dụ mẫu:").classes("text-xs text-slate-500 font-medium")

            examples = [
                ("Quy tắc tích", "x^2 * sin(x)"),
                ("Quy tắc thương", "x / (x + 1)"),
                ("Quy tắc hàm hợp", "sin(x^2)"),
                ("Tổng & Lũy thừa", "3*x^4 - 2*x^2 + 5*x - 7"),
                ("Lượng giác", "cos(x) - tan(x)"),
            ]

            def make_setter(val: str):
                return lambda: expr_input.set_value(val)

            for label, val in examples:
                ui.chip(label, on_click=make_setter(val)).classes("cursor-pointer hover:bg-blue-100 text-xs")

    return expr_input, var_input

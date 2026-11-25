"""Order selector component for ODE workspace (First-Order vs Second-Order)."""

from __future__ import annotations

from typing import Callable
from nicegui import ui

from math_app.presentation.components.math_view import ui_math
from math_app.presentation.components.workspace.ode.ode_state import ODEOrder


def render_ode_order_selector(
    selected_order: ODEOrder,
    on_change: Callable[[ODEOrder], None],
) -> None:
    """Render Step 1: ODE Order Selection with Academic Blue styling."""
    with ui.column().classes("w-full gap-2"):
        with ui.row().classes("items-center gap-2"):
            ui.badge("BƯỚC 1", color="primary").classes("text-xs font-bold")
            ui.label("CHỌN CẤP PHƯƠNG TRÌNH VI PHÂN:").classes(
                "text-xs font-bold text-slate-700 uppercase tracking-wider"
            )

        with ui.row().classes("grid grid-cols-1 md:grid-cols-2 gap-3.5 w-full"):
            # Option 1: First-Order
            is_fo = selected_order == ODEOrder.FIRST_ORDER
            fo_cls = (
                "border-2 border-blue-600 bg-blue-50/70 shadow-xs"
                if is_fo
                else "border border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50 cursor-pointer"
            )
            with ui.card().classes(f"p-4 rounded-xl transition-all {fo_cls}") as c_fo:
                c_fo.on("click", lambda e=None: on_change(ODEOrder.FIRST_ORDER))
                c_fo.props('tabindex="0" role="button"')
                c_fo.on("keydown.enter", lambda e=None: on_change(ODEOrder.FIRST_ORDER))
                c_fo.on("keydown.space", lambda e=None: on_change(ODEOrder.FIRST_ORDER))

                with ui.row().classes("items-center justify-between w-full"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon(
                            "check_circle" if is_fo else "radio_button_unchecked",
                            color="primary" if is_fo else "grey-5",
                            size="1.25rem",
                        )
                        ui.label("Phương trình vi phân cấp 1").classes(
                            f"text-sm font-bold {'text-blue-950' if is_fo else 'text-slate-800'}"
                        )
                    ui.badge("Cấp 1", color="blue-7" if is_fo else "grey-6").classes("text-xs")

                ui_math(r"y' = f(t, y) \quad \text{hoặc} \quad M\,dx + N\,dy = 0", block=True, classes="my-1 text-slate-800")
                ui.label(
                    "Bao gồm phương trình tuyến tính cấp 1, tách biến, vi phân toàn phần, thừa số tích phân và thuần nhất cấp 1."
                ).classes("text-xs text-slate-500 leading-snug")

            # Option 2: Second-Order
            is_so = selected_order == ODEOrder.SECOND_ORDER
            so_cls = (
                "border-2 border-blue-600 bg-blue-50/70 shadow-xs"
                if is_so
                else "border border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50 cursor-pointer"
            )
            with ui.card().classes(f"p-4 rounded-xl transition-all {so_cls}") as c_so:
                c_so.on("click", lambda e=None: on_change(ODEOrder.SECOND_ORDER))
                c_so.props('tabindex="0" role="button"')
                c_so.on("keydown.enter", lambda e=None: on_change(ODEOrder.SECOND_ORDER))
                c_so.on("keydown.space", lambda e=None: on_change(ODEOrder.SECOND_ORDER))

                with ui.row().classes("items-center justify-between w-full"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon(
                            "check_circle" if is_so else "radio_button_unchecked",
                            color="primary" if is_so else "grey-5",
                            size="1.25rem",
                        )
                        ui.label("Phương trình vi phân cấp 2").classes(
                            f"text-sm font-bold {'text-blue-950' if is_so else 'text-slate-800'}"
                        )
                    ui.badge("Cấp 2", color="blue-7" if is_so else "grey-6").classes("text-xs")

                ui_math(r"a\,y'' + b\,y' + c\,y = g(t)", block=True, classes="my-1 text-slate-800")
                ui.label(
                    "Bao gồm phương trình thuần nhất, không thuần nhất (Hệ số bất định, Biến thiên hằng số), bài toán Cauchy và định thức Wronskian."
                ).classes("text-xs text-slate-500 leading-snug")

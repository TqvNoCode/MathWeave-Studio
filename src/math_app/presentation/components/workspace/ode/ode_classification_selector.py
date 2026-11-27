"""Classification selector component for ODE workspace."""

from __future__ import annotations

from typing import Any, Callable
from nicegui import ui

from math_app.presentation.components.math_view import ui_math, ui_math_text
from math_app.presentation.components.workspace.ode.ode_state import (
    ODEClassification,
    ODEOrder,
)
from math_app.presentation.design_system.tokens import INTERACTION


def render_ode_classification_selector(
    order: ODEOrder,
    selected_classification: ODEClassification,
    on_change: Callable[[ODEClassification], None],
    show_heading: bool = True,
) -> None:
    """Render manual equation classification override controls with Academic Blue styling."""
    with ui.column().classes("w-full gap-2.5 mt-1 min-w-0"):
        if show_heading:
            with ui.row().classes("items-center justify-between w-full"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("tune", size="1.1rem").classes("text-blue-600")
                    ui.label("PHÂN LOẠI PHƯƠNG TRÌNH (TÙY CHỌN THỦ CÔNG):").classes(
                        "text-xs font-bold text-slate-700 uppercase tracking-wider"
                    )

        if order == ODEOrder.FIRST_ORDER:
            # First-order classifications
            fo_options = [
                (ODEClassification.FIRST_ORDER_LINEAR, "Tuyến tính cấp 1", "y' + p(t)y = g(t)"),
                (ODEClassification.SEPARABLE, "Tách biến", "dy/g(y) = f(t)dt"),
                (ODEClassification.EXACT, "Vi phân toàn phần", "M dx + N dy = 0"),
                (ODEClassification.INTEGRATING_FACTOR, "Thừa số tích phân", "μ(x), μ(y)"),
                (ODEClassification.FIRST_ORDER_HOMOGENEOUS, "Thuần nhất cấp 1", "y' = F(y/x)"),
            ]
            with ui.row().classes("items-center gap-2 flex-wrap w-full"):
                for classification, title, subtitle in fo_options:
                    is_active = selected_classification == classification
                    btn_cls = (
                        "bg-blue-600 text-white font-bold shadow-xs border border-blue-600"
                        if is_active
                        else "bg-white text-slate-700 hover:bg-blue-50 hover:text-blue-700 border border-slate-200"
                    )
                    with ui.button(
                        title,
                        on_click=lambda _, c=classification: on_change(c),
                    ).props(f"{'unelevated' if is_active else 'outline'} no-caps").classes(
                        f"text-xs md:text-sm h-9 px-3 rounded-lg {btn_cls} transition-all font-semibold"
                    ):
                        ui.tooltip(subtitle)

        else:
            # Second-order primary classifications with named handlers for full backward test parity
            is_homo = selected_classification == ODEClassification.SECOND_ORDER_HOMOGENEOUS
            is_nonhomo = selected_classification == ODEClassification.SECOND_ORDER_NONHOMOGENEOUS
            is_euler = selected_classification == ODEClassification.EULER_CAUCHY

            def on_select_homo(_: Any = None) -> None:
                on_change(ODEClassification.SECOND_ORDER_HOMOGENEOUS)

            def on_select_nonhomo(_: Any = None) -> None:
                on_change(ODEClassification.SECOND_ORDER_NONHOMOGENEOUS)

            def on_select_euler(_: Any = None) -> None:
                on_change(ODEClassification.EULER_CAUCHY)

            with ui.row().classes("grid grid-cols-1 md:grid-cols-3 gap-3.5 w-full min-w-0"):
                # Option A: Homogeneous Card
                card_homo_cls = (
                    "border-2 border-blue-600 bg-blue-50/70 shadow-xs"
                    if is_homo
                    else "border border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50 cursor-pointer"
                )
                with ui.card().classes(f"p-4 rounded-xl transition-all h-full flex flex-col justify-between gap-2 {card_homo_cls} {INTERACTION.FOCUS_RING}") as c_homo:
                    c_homo.on("click", on_select_homo)
                    c_homo.props('tabindex="0" role="button" aria-label="Chọn dạng phương trình vi phân cấp 2 thuần nhất"')
                    c_homo.on("keydown.enter", on_select_homo)
                    c_homo.on("keydown.space", on_select_homo)
                    with ui.column().classes("w-full gap-1.5"):
                        with ui.row().classes("items-center justify-between w-full gap-2"):
                            with ui.row().classes("items-center gap-2 min-w-0 flex-1"):
                                ui.icon(
                                    "check_circle" if is_homo else "radio_button_unchecked",
                                    color="primary" if is_homo else "grey-5",
                                    size="1.25rem",
                                ).classes("shrink-0")
                                ui.label("Phương trình thuần nhất").classes(
                                    f"text-sm font-bold {'text-blue-950' if is_homo else 'text-slate-800'}"
                                )
                            ui.badge("g(t) = 0", color="blue-7" if is_homo else "grey-6").classes("text-xs shrink-0")
                        ui_math(r"a\,y'' + b\,y' + c\,y = 0", block=True, classes="my-1 text-slate-800")
                        ui.label(
                            "Nghiệm tổng quát y(t) = yc(t) được xác định qua phương trình đặc trưng ar² + br + c = 0."
                        ).classes("text-xs text-slate-600 leading-snug")
                    ui.button(
                        "Thuần nhất",
                        icon="check_circle" if is_homo else "radio_button_unchecked",
                        on_click=on_select_homo,
                    ).props("unelevated dense no-caps" if is_homo else "outline dense no-caps").classes(
                        f"mt-auto text-xs font-semibold w-full {INTERACTION.FOCUS_RING}"
                    )

                # Option B: Nonhomogeneous Card
                card_nonhomo_cls = (
                    "border-2 border-blue-600 bg-blue-50/70 shadow-xs"
                    if is_nonhomo
                    else "border border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50 cursor-pointer"
                )
                with ui.card().classes(f"p-4 rounded-xl transition-all h-full flex flex-col justify-between gap-2 {card_nonhomo_cls} {INTERACTION.FOCUS_RING}") as c_nonhomo:
                    c_nonhomo.on("click", on_select_nonhomo)
                    c_nonhomo.props('tabindex="0" role="button" aria-label="Chọn dạng phương trình vi phân cấp 2 không thuần nhất"')
                    c_nonhomo.on("keydown.enter", on_select_nonhomo)
                    c_nonhomo.on("keydown.space", on_select_nonhomo)
                    with ui.column().classes("w-full gap-1.5"):
                        with ui.row().classes("items-center justify-between w-full gap-2"):
                            with ui.row().classes("items-center gap-2 min-w-0 flex-1"):
                                ui.icon(
                                    "check_circle" if is_nonhomo else "radio_button_unchecked",
                                    color="primary" if is_nonhomo else "grey-5",
                                    size="1.25rem",
                                ).classes("shrink-0")
                                ui.label("Phương trình không thuần nhất").classes(
                                    f"text-sm font-bold {'text-blue-950' if is_nonhomo else 'text-slate-800'}"
                                )
                            ui.badge("g(t) ≢ 0", color="blue-7" if is_nonhomo else "grey-6").classes("text-xs shrink-0")
                        ui_math(r"a\,y'' + b\,y' + c\,y = g(t)", block=True, classes="my-1 text-slate-800")
                        ui.label(
                            "Nghiệm y(t) = yc(t) + Yp(t) giải bằng Hệ số bất định hoặc Biến thiên hằng số (Lagrange)."
                        ).classes("text-xs text-slate-600 leading-snug")
                    ui.button(
                        "Không thuần nhất",
                        icon="check_circle" if is_nonhomo else "radio_button_unchecked",
                        on_click=on_select_nonhomo,
                    ).props("unelevated dense no-caps" if is_nonhomo else "outline dense no-caps").classes(
                        f"mt-auto text-xs font-semibold w-full {INTERACTION.FOCUS_RING}"
                    )

                # Option C: Euler-Cauchy Card
                card_euler_cls = (
                    "border-2 border-blue-600 bg-blue-50/70 shadow-xs"
                    if is_euler
                    else "border border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50 cursor-pointer"
                )
                with ui.card().classes(f"p-4 rounded-xl transition-all h-full flex flex-col justify-between gap-2 {card_euler_cls} {INTERACTION.FOCUS_RING}") as c_euler:
                    c_euler.on("click", on_select_euler)
                    c_euler.props('tabindex="0" role="button" aria-label="Chọn dạng phương trình vi phân Euler-Cauchy"')
                    c_euler.on("keydown.enter", on_select_euler)
                    c_euler.on("keydown.space", on_select_euler)
                    with ui.column().classes("w-full gap-1.5"):
                        with ui.row().classes("items-center justify-between w-full gap-2"):
                            with ui.row().classes("items-center gap-2 min-w-0 flex-1"):
                                ui.icon(
                                    "check_circle" if is_euler else "radio_button_unchecked",
                                    color="primary" if is_euler else "grey-5",
                                    size="1.25rem",
                                ).classes("shrink-0")
                                ui.label("Euler–Cauchy").classes(
                                    f"text-sm font-bold {'text-blue-950' if is_euler else 'text-slate-800'}"
                                )
                            ui.badge("At²y''", color="blue-7" if is_euler else "grey-6").classes("text-xs shrink-0")
                        ui_math(r"A\,t^2y'' + B\,ty' + C\,y = g(t)", block=True, classes="my-1 text-slate-800")
                        ui_math_text(
                            "Đưa về phương trình chỉ số $Am(m-1)+Bm+C=0$; dùng Biến thiên hằng số khi $g(t) \\neq 0$.",
                            classes="text-xs text-slate-600 leading-snug",
                        )
                    ui.button(
                        "Euler–Cauchy",
                        icon="check_circle" if is_euler else "radio_button_unchecked",
                        on_click=on_select_euler,
                    ).props("unelevated dense no-caps" if is_euler else "outline dense no-caps").classes(
                        f"mt-auto text-xs font-semibold w-full {INTERACTION.FOCUS_RING}"
                    )

            # Advanced second-order tools row
            with ui.row().classes("items-center gap-2 flex-wrap pt-1"):
                ui.label("Công cụ nâng cao:").classes("text-xs text-slate-400 font-semibold self-center")
                so_advanced = [
                    (ODEClassification.REDUCTION_OF_ORDER, "Hạ bậc nghiệm", "Tìm y₂(t) = v(t)y₁(t)"),
                    (ODEClassification.WRONSKIAN, "Định thức Wronskian", "W(y₁, y₂) kiểm tra ĐLTT"),
                ]
                for classification, title, tooltip_text in so_advanced:
                    is_active = selected_classification == classification
                    adv_cls = (
                        "bg-blue-600 text-white font-bold shadow-xs border border-blue-600"
                        if is_active
                        else "bg-slate-50 text-slate-700 hover:bg-blue-50 hover:text-blue-700 border border-slate-200"
                    )
                    with ui.button(
                        title,
                        on_click=lambda _, c=classification: on_change(c),
                    ).props(f"{'unelevated' if is_active else 'outline'} no-caps").classes(
                        f"text-xs h-8 px-3 rounded-lg {adv_cls} transition-all font-medium"
                    ):
                        ui.tooltip(tooltip_text)


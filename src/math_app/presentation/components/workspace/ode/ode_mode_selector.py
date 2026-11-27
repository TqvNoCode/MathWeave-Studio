"""Problem mode selector component for ODE workspace (General Solution vs Cauchy IVP)."""

from __future__ import annotations

from typing import Any, Callable
from nicegui import ui

from math_app.presentation.components.workspace.ode.ode_state import (
    ODEClassification,
    ODEMode,
    ODEOrder,
)
from math_app.presentation.design_system.tokens import INTERACTION


def render_ode_mode_selector(
    order: ODEOrder,
    classification: ODEClassification,
    selected_mode: ODEMode,
    initial_condition: str,
    on_mode_change: Callable[[ODEMode], None],
    on_ic_change: Callable[[str], None],
    on_ic_input_created: Callable[[ui.input], None] | None = None,
) -> None:
    """Render Step 3: Problem Mode selection with Academic Blue styling and contextual inputs."""
    # Advanced tools do not require general vs IVP mode selection
    if classification.is_advanced_tool:
        return

    is_gen = selected_mode == ODEMode.GENERAL
    is_ivp = selected_mode == ODEMode.CAUCHY_IVP

    with ui.column().classes("w-full gap-2 mt-1 min-w-0"):
        with ui.row().classes("items-center justify-between w-full"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("tune", size="1.1rem").classes("text-blue-600")
                ui.label("YÊU CẦU BÀI TOÁN:").classes(
                    "text-xs font-bold text-slate-700 uppercase tracking-wider"
                )

        # Mode Selection Buttons
        with ui.row().classes("gap-3 flex-wrap items-center"):
            gen_cls = (
                "!bg-blue-600 hover:!bg-blue-700 !text-white font-bold shadow-xs border border-blue-600"
                if is_gen
                else "!bg-white !text-slate-700 hover:!bg-blue-50 hover:!text-blue-700 border border-slate-300"
            )
            ivp_cls = (
                "!bg-blue-600 hover:!bg-blue-700 !text-white font-bold shadow-xs border border-blue-600"
                if is_ivp
                else "!bg-white !text-slate-700 hover:!bg-blue-50 hover:!text-blue-700 border border-slate-300"
            )

            gen_tooltip = (
                "Tìm nghiệm tổng quát chứa hằng số tích phân C"
                if order == ODEOrder.FIRST_ORDER
                else "Tìm nghiệm tổng quát chứa các hằng số tích phân C₁, C₂"
            )
            ivp_tooltip = (
                "Tìm nghiệm xác định duy nhất thỏa mãn điều kiện ban đầu y(t₀) = y₀"
                if order == ODEOrder.FIRST_ORDER
                else "Tìm nghiệm xác định duy nhất thỏa mãn cả hai điều kiện ban đầu y(t₀) = y₀ và y'(t₀) = v₀"
            )

            with ui.button("Tìm nghiệm tổng quát", icon="functions", on_click=lambda: on_mode_change(ODEMode.GENERAL), color=None).props(
                "unelevated no-caps"
            ).classes(f"text-xs md:text-sm min-h-[40px] px-4 rounded-lg {gen_cls} transition-all font-semibold {INTERACTION.FOCUS_RING}"):
                ui.tooltip(gen_tooltip)

            with ui.button("Bài toán Cauchy (IVP)", icon="alt_route", on_click=lambda: on_mode_change(ODEMode.CAUCHY_IVP), color=None).props(
                "unelevated no-caps"
            ).classes(f"text-xs md:text-sm min-h-[40px] px-4 rounded-lg {ivp_cls} transition-all font-semibold {INTERACTION.FOCUS_RING}"):
                ui.tooltip(ivp_tooltip)

        # Contextual Cauchy Initial Condition Inputs (only displayed when IVP mode is active)
        if is_ivp:
            with ui.column().classes("w-full gap-2 p-3.5 bg-blue-50/70 border border-blue-200 rounded-xl mt-1"):
                clear_btn_ref: list[Any] = [None]
                ic_input_ref: list[Any] = [None]

                def _set_clear_btn_state(has_val: bool) -> None:
                    btn = clear_btn_ref[0]
                    if btn is None:
                        return
                    if has_val:
                        btn.enable()
                        btn.classes(
                            add="border border-rose-300 !text-slate-700 hover:!bg-rose-50 hover:!text-rose-700 bg-white font-medium cursor-pointer shadow-2xs",
                            remove="border-slate-300 !text-slate-400 bg-slate-50 cursor-not-allowed opacity-60",
                        )
                    else:
                        btn.disable()
                        btn.classes(
                            add="border border-slate-300 !text-slate-400 bg-slate-50 cursor-not-allowed opacity-60",
                            remove="border-rose-300 !text-slate-700 hover:!bg-rose-50 hover:!text-rose-700 bg-white font-medium cursor-pointer shadow-2xs",
                        )

                with ui.row().classes("items-center justify-between w-full"):
                    ic_title = (
                        "Điều kiện ban đầu y(t₀) = y₀:"
                        if order == ODEOrder.FIRST_ORDER
                        else "Điều kiện ban đầu Cauchy: y(t₀) = y₀, y'(t₀) = v₀:"
                    )
                    ui.label(ic_title).classes("text-xs font-bold text-blue-950 uppercase tracking-wider")

                    def clear_ic(_: Any = None) -> None:
                        on_ic_change("")
                        if ic_input_ref[0] is not None:
                            ic_input_ref[0].set_value("")
                        _set_clear_btn_state(False)

                    has_init_ic = bool(initial_condition and initial_condition.strip())
                    btn_cls = (
                        "border border-rose-300 !text-slate-700 hover:!bg-rose-50 hover:!text-rose-700 bg-white font-medium cursor-pointer shadow-2xs"
                        if has_init_ic
                        else "border border-slate-300 !text-slate-400 bg-slate-50 cursor-not-allowed opacity-60"
                    )
                    clear_btn = (
                        ui.button("Xóa điều kiện", icon="delete_outline", on_click=clear_ic, color=None)
                        .props("unelevated dense no-caps")
                        .classes(f"text-xs px-2.5 py-1 rounded-lg transition-all {btn_cls}")
                    )
                    if not has_init_ic:
                        clear_btn.disable()
                    clear_btn_ref[0] = clear_btn

                ic_placeholder = (
                    "Ví dụ: y(0) = 1 (hoặc có thể viết trực tiếp trong phương trình)"
                    if order == ODEOrder.FIRST_ORDER
                    else "Ví dụ: y(0) = 1, y'(0) = 0"
                )
                ic_label = (
                    "Điều kiện ban đầu Cauchy: y(t0) = y0, y'(t0) = v0"
                    if order == ODEOrder.SECOND_ORDER
                    else "Điều kiện ban đầu"
                )
                ic_input = ui.input(
                    label=ic_label,
                    placeholder=ic_placeholder,
                    value=initial_condition,
                ).classes("w-full text-base font-mono bg-white rounded-lg")
                ic_input_ref[0] = ic_input
                if on_ic_input_created is not None:
                    on_ic_input_created(ic_input)

                def _on_input_change(e: Any) -> None:
                    val = (e.value or "").strip()
                    _set_clear_btn_state(bool(val))
                    on_ic_change(e.value or "")

                ic_input.on_value_change(_on_input_change)

                hint_text = (
                    "📌 Cung cấp điều kiện ban đầu y(t₀) = y₀ tại điểm t₀ hữu hạn để xác định hằng số C."
                    if order == ODEOrder.FIRST_ORDER
                    else "📌 Lưu ý: Để giải bài toán Cauchy cấp 2, cần cung cấp đủ cả hai điều kiện y(t₀) = y₀ và y'(t₀) = v₀ tại cùng một điểm t₀ hữu hạn."
                )
                ui.label(hint_text).classes("text-xs text-blue-800")

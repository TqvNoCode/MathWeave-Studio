"""Shared helpers and reusable form skeleton for order-specific Explicit Euler UI panels."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable

from nicegui import ui

from math_app.domain.numerical_ode import (
    NumericalODEMethod,
    NumericalODEOrder,
    NumericalODERequest,
    NumericalODEResponse,
)
from math_app.presentation.components.shared import (
    primary_button,
    render_example_chips,
    render_feedback_card,
    render_loading_card,
)
from math_app.presentation.components.workspace.ode.numerical_result_view import (
    render_numerical_euler_result,
)
from math_app.presentation.components.workspace.ode.ode_state import ODEOrder


@dataclass(frozen=True)
class EulerPanelConfig:
    """Order-specific configuration for rendering an Explicit Euler input workflow."""

    order: NumericalODEOrder
    banner_text: str
    equation_label: str
    equation_placeholder: str
    default_equation: str
    default_indep_var: str
    default_t0: str
    default_y0: str
    default_v0: str
    default_t_end: str
    default_step_size: str
    ivp_section_heading: str
    y0_label: str
    examples_label: str
    examples: tuple[tuple[str, tuple[str, str, str, str, str, str, str]], ...]
    cta_text: str
    cta_aria_label: str
    reset_aria_label: str


def render_order_specific_euler_form(
    config: EulerPanelConfig,
    numerical_use_case: Any,
    results_container: ui.column,
    on_switch_order: Callable[[ODEOrder], None] | None = None,
) -> None:
    """Render an Explicit Euler input panel locked to a single ODE order (no cross-order selector)."""
    is_second = config.order == NumericalODEOrder.SECOND_ORDER
    form_state: dict[str, Any] = {
        "equation": config.default_equation,
        "indep_var": config.default_indep_var,
        "t0": config.default_t0,
        "y0": config.default_y0,
        "v0": config.default_v0,
        "t_end": config.default_t_end,
        "step_size": config.default_step_size,
        "compare_exact": True,
        "run_token": 0,
        "is_running": False,
    }

    panel_box = ui.column().classes("w-full gap-4 min-w-0")

    def _invalidate_stale_results() -> None:
        form_state["run_token"] += 1
        results_container.clear()

    def _render_form() -> None:
        panel_box.clear()
        with panel_box:
            # Concise beginner-oriented guidance banner
            with ui.row().classes(
                "w-full items-start gap-2.5 p-3 rounded-xl bg-blue-50/70 border border-blue-200 text-xs text-blue-950"
            ):
                ui.icon("info", size="1.15rem").classes("text-blue-700 shrink-0 mt-0.5")
                ui.label(config.banner_text).classes("leading-relaxed font-medium")

            # Main Equation & Independent Variable
            with ui.row().classes("w-full items-start gap-3 flex-wrap min-w-0"):
                eq_inp = (
                    ui.input(
                        label=config.equation_label,
                        placeholder=config.equation_placeholder,
                        value=form_state["equation"],
                    )
                    .classes("flex-1 min-w-[220px] w-full text-base font-mono")
                    .props("clearable")
                )
                var_inp = ui.input(
                    label="Biến độc lập",
                    value=form_state["indep_var"],
                ).classes("w-full sm:w-28 text-base font-mono")

            # Dedicated Initial-Value & Step-Size Configuration
            grid_cls = (
                "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 w-full"
                if is_second
                else "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 w-full"
            )
            with ui.column().classes(
                "w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl gap-3 min-w-0"
            ):
                ui.label(config.ivp_section_heading).classes(
                    "text-xs font-bold text-slate-700 uppercase tracking-wider"
                )
                with ui.element("div").classes(grid_cls):
                    t0_inp = ui.input(
                        label="Điểm bắt đầu t₀",
                        value=form_state["t0"],
                    ).classes("w-full font-mono bg-white rounded")
                    y0_inp = ui.input(
                        label=config.y0_label,
                        value=form_state["y0"],
                    ).classes("w-full font-mono bg-white rounded")

                    v0_inp: Any = None
                    if is_second:
                        v0_inp = ui.input(
                            label="Đạo hàm ban đầu v₀ = y'(t₀)",
                            value=form_state["v0"],
                        ).classes("w-full font-mono bg-white rounded")

                    t_end_inp = ui.input(
                        label="Điểm kết thúc T",
                        value=form_state["t_end"],
                    ).classes("w-full font-mono bg-white rounded")
                    h_inp = ui.input(
                        label="Bước nhảy h (> 0)",
                        value=form_state["step_size"],
                    ).classes("w-full font-mono bg-white rounded")

                compare_cb = ui.checkbox(
                    "Đối chiếu nghiệm giải tích chính xác (khi hệ thống hỗ trợ)",
                    value=form_state["compare_exact"],
                ).classes("text-xs font-medium text-slate-700")

            # Curated Example Chips
            chip_pairs = [(lbl, lbl) for lbl, _ in config.examples]
            payload_by_label = {lbl: vals for lbl, vals in config.examples}

            def _apply_example(selected_lbl: str) -> None:
                vals = payload_by_label.get(selected_lbl)
                if not vals:
                    return
                eq_v, var_v, t0_v, y0_v, v0_v, tend_v, h_v = vals
                form_state["equation"] = eq_v
                form_state["indep_var"] = var_v
                form_state["t0"] = t0_v
                form_state["y0"] = y0_v
                form_state["v0"] = v0_v
                form_state["t_end"] = tend_v
                form_state["step_size"] = h_v
                eq_inp.set_value(eq_v)
                var_inp.set_value(var_v)
                t0_inp.set_value(t0_v)
                y0_inp.set_value(y0_v)
                if v0_inp is not None:
                    v0_inp.set_value(v0_v)
                t_end_inp.set_value(tend_v)
                h_inp.set_value(h_v)
                _invalidate_stale_results()

            render_example_chips(chip_pairs, on_select=_apply_example, label=config.examples_label)

            # Action Controls
            solve_btn_ref: list[Any] = [None]

            async def handle_solve() -> None:
                if form_state["is_running"]:
                    return
                if numerical_use_case is None:
                    results_container.clear()
                    with results_container:
                        render_feedback_card(
                            title="Chưa cấu hình bộ giải số",
                            messages=["Không tìm thấy SolveNumericalODEUseCase trong phiên ứng dụng hiện tại."],
                            variant="error",
                        )
                    return

                form_state["is_running"] = True
                form_state["run_token"] += 1
                my_token = form_state["run_token"]
                if solve_btn_ref[0] is not None:
                    solve_btn_ref[0].disable()

                try:
                    results_container.clear()
                    with results_container:
                        render_loading_card(
                            "Đang tính xấp xỉ Explicit Euler, phân tích sai số và kiểm chứng độc lập..."
                        )

                    req = NumericalODERequest(
                        raw_equation=str(form_state["equation"]),
                        order=config.order,
                        independent_var=str(form_state["indep_var"]).strip() or "t",
                        dependent_var="y",
                        t0=str(form_state["t0"]),
                        y0=str(form_state["y0"]),
                        t_end=str(form_state["t_end"]),
                        step_size=str(form_state["step_size"]),
                        v0=str(form_state["v0"]) if is_second else None,
                        method=NumericalODEMethod.EXPLICIT_EULER,
                        compute_analytical_comparison=bool(form_state["compare_exact"]),
                    )

                    resp: NumericalODEResponse = await asyncio.to_thread(numerical_use_case.execute, req)
                    if my_token != form_state["run_token"]:
                        return

                    results_container.clear()
                    with results_container:
                        render_numerical_euler_result(resp, on_switch_order=on_switch_order)
                except Exception as exc:
                    if my_token == form_state["run_token"]:
                        results_container.clear()
                        with results_container:
                            render_feedback_card(
                                title="Lỗi thực thi bộ giải số",
                                messages=[f"Lỗi hệ thống: {exc}"],
                                variant="error",
                            )
                finally:
                    form_state["is_running"] = False
                    if solve_btn_ref[0] is not None:
                        solve_btn_ref[0].enable()

            def _bind_field(ctrl: Any, key: str) -> None:
                if ctrl is None:
                    return

                def _on_chg(e: Any) -> None:
                    form_state[key] = e.value if e.value is not None else ""
                    _invalidate_stale_results()

                ctrl.on_value_change(_on_chg)
                ctrl.on("keydown.enter", handle_solve)

            def _handle_reset() -> None:
                form_state["equation"] = config.default_equation
                form_state["indep_var"] = config.default_indep_var
                form_state["t0"] = config.default_t0
                form_state["y0"] = config.default_y0
                form_state["v0"] = config.default_v0
                form_state["t_end"] = config.default_t_end
                form_state["step_size"] = config.default_step_size
                form_state["compare_exact"] = True
                _invalidate_stale_results()
                _render_form()

            _bind_field(eq_inp, "equation")
            _bind_field(var_inp, "indep_var")
            _bind_field(t0_inp, "t0")
            _bind_field(y0_inp, "y0")
            _bind_field(v0_inp, "v0")
            _bind_field(t_end_inp, "t_end")
            _bind_field(h_inp, "step_size")
            compare_cb.on_value_change(
                lambda e: (form_state.__setitem__("compare_exact", bool(e.value)), _invalidate_stale_results())
            )

            with ui.row().classes(
                "w-full items-center justify-between pt-3 border-t border-slate-100 flex-wrap gap-2"
            ):
                ui.button("Nhập lại", icon="refresh", on_click=_handle_reset).props(
                    f'flat dense no-caps aria-label="{config.reset_aria_label}"'
                ).classes(
                    "text-xs text-slate-600 font-semibold hover:text-slate-900 rounded-lg px-2 py-1"
                )

                solve_btn = primary_button(
                    text=config.cta_text,
                    icon="calculate",
                    aria_label=config.cta_aria_label,
                )
                solve_btn_ref[0] = solve_btn
                solve_btn.on_click(handle_solve)

    _render_form()

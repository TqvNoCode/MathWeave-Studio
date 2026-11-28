"""Interactive input panel for Explicit Euler numerical ODE approximation."""

from __future__ import annotations

import asyncio
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

_NUMERICAL_DEFAULTS: dict[NumericalODEOrder, dict[str, Any]] = {
    NumericalODEOrder.FIRST_ORDER: {
        "equation": "y' = y",
        "indep_var": "t",
        "t0": "0",
        "y0": "1",
        "v0": "",
        "t_end": "1",
        "step_size": "0.1",
        "examples": (
            ("Tăng trưởng mũ: y' = y, y(0)=1, T=1, h=0.1", ("y' = y", "t", "0", "1", "", "1", "0.1")),
            ("Suy giảm mũ: y' = -2y, y(0)=1, T=1, h=0.2", ("y' = -2*y", "t", "0", "1", "", "1", "0.2")),
            ("Không thuần nhất: y' = t + y, y(0)=1, T=0.5, h=0.1", ("y' = t + y", "t", "0", "1", "", "0.5", "0.1")),
            ("Tích phân lùi: y' = -y, y(1)=1, T=0, h=0.2", ("y' = -y", "t", "1", "1", "", "0", "0.2")),
        ),
    },
    NumericalODEOrder.SECOND_ORDER: {
        "equation": "y'' = -y",
        "indep_var": "t",
        "t0": "0",
        "y0": "0",
        "v0": "1",
        "t_end": "3.14",
        "step_size": "0.1",
        "examples": (
            ("Dao động điều hòa: y'' = -y, y(0)=0, y'(0)=1", ("y'' = -y", "t", "0", "0", "1", "3.14", "0.1")),
            ("Vận tốc không đổi: y'' = 0, y(0)=2, y'(0)=3", ("y'' = 0", "t", "0", "2", "3", "2", "0.5")),
            ("Không thuần nhất: y'' + y = t, y(0)=1, y'(0)=0", ("y'' + y = t", "t", "0", "1", "0", "1", "0.1")),
            ("Euler–Cauchy (t > 0): t^2y'' - ty' + y = t^2", ("t^2*y'' - t*y' + y = t^2", "t", "1", "0", "0", "2", "0.1")),
        ),
    },
}


def render_numerical_euler_panel(
    initial_order: ODEOrder,
    numerical_use_case: Any,
    results_container: ui.column,
    on_order_sync: Callable[[ODEOrder], None] | None = None,
) -> None:
    """Render the Explicit Euler numerical IVP workspace panel inside ODE workspace."""
    num_order = (
        NumericalODEOrder.FIRST_ORDER
        if initial_order == ODEOrder.FIRST_ORDER
        else NumericalODEOrder.SECOND_ORDER
    )
    defaults = _NUMERICAL_DEFAULTS[num_order]
    form_state: dict[str, Any] = {
        "order": num_order,
        "equation": defaults["equation"],
        "indep_var": defaults["indep_var"],
        "t0": defaults["t0"],
        "y0": defaults["y0"],
        "v0": defaults["v0"],
        "t_end": defaults["t_end"],
        "step_size": defaults["step_size"],
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
        cur_order: NumericalODEOrder = form_state["order"]
        is_second = cur_order == NumericalODEOrder.SECOND_ORDER
        cur_defaults = _NUMERICAL_DEFAULTS[cur_order]

        with panel_box:
            # Informational Banner clarifying Explicit Euler vs Euler-Cauchy
            with ui.row().classes(
                "w-full items-start gap-2.5 p-3 rounded-xl bg-blue-50/70 border border-blue-200 text-xs text-blue-950"
            ):
                ui.icon("info", size="1.15rem").classes("text-blue-700 shrink-0 mt-0.5")
                ui.label(
                    "Chế độ giải số (IVP): Tính nghiệm xấp xỉ rời rạc trên đoạn [t₀, T] bằng Phương pháp Euler tiến "
                    "(Explicit Euler) từ các điều kiện ban đầu — khác với phương trình vi phân giải tích Euler–Cauchy."
                ).classes("leading-relaxed font-medium")

            # Order Switch within Numerical Mode
            with ui.row().classes("items-center justify-between w-full flex-wrap gap-2"):
                ui.label("CẤP PHƯƠNG TRÌNH (XẤP XỈ SỐ):").classes(
                    "text-xs font-bold text-slate-700 uppercase tracking-wider"
                )
                with ui.row().classes("gap-2 flex-wrap"):
                    for ord_val, lbl in (
                        (NumericalODEOrder.FIRST_ORDER, "PTVP Cấp 1 (y' = f(t, y))"),
                        (NumericalODEOrder.SECOND_ORDER, "PTVP Cấp 2 (y'' = F(t, y, y'))"),
                    ):
                        is_sel = cur_order == ord_val
                        btn_cls = (
                            "!bg-blue-600 !text-white font-bold border border-blue-600"
                            if is_sel
                            else "!bg-white !text-slate-700 hover:!bg-blue-50 border border-slate-300"
                        )

                        def _switch_num_order(target_ord: NumericalODEOrder = ord_val) -> None:
                            if form_state["order"] == target_ord:
                                return
                            new_def = _NUMERICAL_DEFAULTS[target_ord]
                            form_state["order"] = target_ord
                            form_state["equation"] = new_def["equation"]
                            form_state["indep_var"] = new_def["indep_var"]
                            form_state["t0"] = new_def["t0"]
                            form_state["y0"] = new_def["y0"]
                            form_state["v0"] = new_def["v0"]
                            form_state["t_end"] = new_def["t_end"]
                            form_state["step_size"] = new_def["step_size"]
                            _invalidate_stale_results()
                            if on_order_sync is not None:
                                on_order_sync(
                                    ODEOrder.FIRST_ORDER
                                    if target_ord == NumericalODEOrder.FIRST_ORDER
                                    else ODEOrder.SECOND_ORDER
                                )
                            else:
                                _render_form()

                        ui.button(lbl, on_click=_switch_num_order, color=None).props("unelevated dense no-caps").classes(
                            f"text-xs px-3 py-1.5 rounded-lg {btn_cls}"
                        )

            # Main Equation + Independent Var
            eq_label = (
                "Phương trình vi phân cấp 2: y'' = F(t, y, y') (hoặc At²y'' + Bty' + Cy = g(t))"
                if is_second
                else "Phương trình vi phân cấp 1: y' = f(t, y)"
            )
            with ui.row().classes("w-full items-start gap-3 flex-wrap min-w-0"):
                eq_inp = ui.input(
                    label=eq_label,
                    placeholder=cur_defaults["equation"],
                    value=form_state["equation"],
                ).classes("flex-1 min-w-[240px] w-full text-base font-mono").props("clearable")

                var_inp = ui.input(
                    label="Biến độc lập",
                    value=form_state["indep_var"],
                ).classes("w-full sm:w-28 text-base font-mono")

            # Initial Value Problem Parameters
            with ui.column().classes(
                "w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl gap-3 min-w-0"
            ):
                ivp_heading = (
                    "THAM SỐ BÀI TOÁN GIÁ TRỊ BAN ĐẦU (IVP CẤP 2) & BƯỚC NHẢY"
                    if is_second
                    else "THAM SỐ BÀI TOÁN GIÁ TRỊ BAN ĐẦU (IVP CẤP 1) & BƯỚC NHẢY"
                )
                ui.label(ivp_heading).classes("text-xs font-bold text-slate-700 uppercase tracking-wider")

                with ui.element("div").classes("grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 w-full"):
                    t0_inp = ui.input(label="Điểm bắt đầu t₀", value=form_state["t0"]).classes("w-full font-mono bg-white rounded")
                    y0_label = "Vị trí ban đầu y₀ = y(t₀)" if is_second else "Giá trị ban đầu y₀ = y(t₀)"
                    y0_inp = ui.input(label=y0_label, value=form_state["y0"]).classes("w-full font-mono bg-white rounded")

                    v0_inp: Any = None
                    if is_second:
                        v0_inp = ui.input(
                            label="Đạo hàm ban đầu v₀ = y'(t₀)",
                            value=form_state["v0"],
                        ).classes("w-full font-mono bg-white rounded")

                    t_end_inp = ui.input(label="Điểm kết thúc T", value=form_state["t_end"]).classes("w-full font-mono bg-white rounded")
                    h_inp = ui.input(label="Bước nhảy h (> 0)", value=form_state["step_size"]).classes("w-full font-mono bg-white rounded")

                compare_cb = ui.checkbox(
                    "Đối chiếu nghiệm giải tích (khi hệ thống hỗ trợ)",
                    value=form_state["compare_exact"],
                ).classes("text-xs font-medium text-slate-700")

            # Bind changes to clear stale results
            def _bind_field(ctrl: Any, key: str) -> None:
                if ctrl is None:
                    return

                def _on_chg(e: Any) -> None:
                    form_state[key] = e.value if e.value is not None else ""
                    _invalidate_stale_results()

                ctrl.on_value_change(_on_chg)
                ctrl.on("keydown.enter", handle_solve)

            # Example Chips
            examples_cfg = cur_defaults["examples"]
            chip_pairs = [(lbl, lbl) for lbl, _ in examples_cfg]
            payload_by_label = {lbl: vals for lbl, vals in examples_cfg}

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

            render_example_chips(chip_pairs, on_select=_apply_example, label="Ví dụ Euler tiến:")

            # Action Row
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
                        render_loading_card("Đang tính xấp xỉ Explicit Euler và kiểm chứng độc lập...")

                    req = NumericalODERequest(
                        raw_equation=str(form_state["equation"]),
                        order=form_state["order"],
                        independent_var=str(form_state["indep_var"]).strip() or "t",
                        dependent_var="y",
                        t0=str(form_state["t0"]),
                        y0=str(form_state["y0"]),
                        t_end=str(form_state["t_end"]),
                        step_size=str(form_state["step_size"]),
                        v0=str(form_state["v0"]) if form_state["order"] == NumericalODEOrder.SECOND_ORDER else None,
                        method=NumericalODEMethod.EXPLICIT_EULER,
                        compute_analytical_comparison=bool(form_state["compare_exact"]),
                    )

                    resp: NumericalODEResponse = await asyncio.to_thread(numerical_use_case.execute, req)
                    if my_token != form_state["run_token"]:
                        # Stale background result after user modified input
                        return

                    results_container.clear()
                    with results_container:
                        render_numerical_euler_result(resp)
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

            def _handle_reset() -> None:
                d = _NUMERICAL_DEFAULTS[form_state["order"]]
                form_state["equation"] = d["equation"]
                form_state["indep_var"] = d["indep_var"]
                form_state["t0"] = d["t0"]
                form_state["y0"] = d["y0"]
                form_state["v0"] = d["v0"]
                form_state["t_end"] = d["t_end"]
                form_state["step_size"] = d["step_size"]
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
            compare_cb.on_value_change(lambda e: (form_state.__setitem__("compare_exact", bool(e.value)), _invalidate_stale_results()))

            with ui.row().classes(
                "w-full items-center justify-between pt-3 border-t border-slate-100 flex-wrap gap-2"
            ):
                ui.button("Nhập lại", icon="refresh", on_click=_handle_reset).props(
                    'flat dense no-caps aria-label="Khôi phục tham số Euler tiến mặc định"'
                ).classes(
                    "text-xs text-slate-600 font-semibold hover:text-slate-900 rounded-lg px-2 py-1"
                )

                solve_btn = primary_button(
                    text="TÍNH XẤP XỈ EULER TIẾN",
                    icon="calculate",
                    aria_label="Tính nghiệm xấp xỉ theo phương pháp Euler tiến (Explicit Euler)",
                )
                solve_btn_ref[0] = solve_btn
                solve_btn.on_click(handle_solve)

    _render_form()

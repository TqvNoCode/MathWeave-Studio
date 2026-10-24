"""Solution display view component for MathWeave Studio."""

from __future__ import annotations

from typing import Any
from nicegui import ui

from math_app.application.dtos import SolutionResponse
from math_app.domain.models import ProblemType, SolutionStatus
from math_app.input.parser import parse_mathematical_input, parse_safe_expression
from math_app.presentation.components.domain_view import render_domain_restrictions
from math_app.presentation.components.math_view import ui_math
from math_app.presentation.components.operation_catalog import (
    OperationDef,
)
from math_app.presentation.components.problem_statement import (
    format_final_answer_latex,
    format_problem_statement_latex,
    get_result_card_title,
)
from math_app.presentation.components.step_viewer import render_steps_container
from math_app.presentation.components.variation_table import render_variation_table_component
from math_app.presentation.components.verification_badge import render_verification_badge
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.presentation.services.analysis_service import (
    can_compute_variation_table,
    can_plot_2d,
    can_plot_3d,
    compute_variation_table,
    create_2d_plot,
    create_3d_plot,
    sample_function_2d,
)
from math_app.presentation.services.plot_3d_service import (
    create_parametric_surface_plot,
)


def determine_contextual_tools(
    prob_type: ProblemType,
    raw_input: str,
    target_var: str = "x",
    is_success: bool = True,
    params: dict[str, Any] | None = None,
) -> tuple[bool, bool, bool]:
    """Authoritative helper to determine whether (tool_2d, tool_3d, tool_table) are active.

    Matrix operations ALWAYS return (False, False, False).
    """
    if prob_type.is_matrix or not is_success:
        return False, False, False

    try:
        tool_2d = can_plot_2d(raw_input, target_var)
    except Exception:
        tool_2d = False

    try:
        tool_3d = can_plot_3d(raw_input)
        if not tool_3d and params:
            surf_expr = str(params.get("surface_expr", "")).strip()
            if surf_expr and can_plot_3d(surf_expr):
                tool_3d = True
            elif params.get("surface_type") == "parametric" and params.get("param_x") and params.get("param_y"):
                tool_3d = True
    except Exception:
        tool_3d = False

    try:
        tool_table = (
            prob_type in {
                ProblemType.DERIVATIVE,
                ProblemType.HIGHER_ORDER_DERIVATIVE,
                ProblemType.INDEFINITE_INTEGRAL,
                ProblemType.INTEGRAL,
            }
            and can_compute_variation_table(raw_input, target_var)
        )
    except Exception:
        tool_table = False

    return tool_2d, tool_3d, tool_table


def render_solution_view(
    response: SolutionResponse,
    op: OperationDef | ProblemType | None = None,
    target_var: str = "x",
    params: dict[str, Any] | None = None,
) -> None:
    """Render the complete solution view: header, verification badge, problem statement,
    final answer, domain restrictions, analysis tools (2D/3D plot, variation table),
    and pedagogical derivation steps."""
    if isinstance(op, OperationDef):
        prob_type = op.problem_type
    elif isinstance(op, ProblemType):
        prob_type = op
    elif op is not None and hasattr(op, "problem_type"):
        prob_type = op.problem_type
    else:
        prob_type = ProblemType.DERIVATIVE

    p_params = params or {}

    # 1. Error / Invalid Input / Timeout Card
    if response.status in (SolutionStatus.INVALID_INPUT, SolutionStatus.CANNOT_SOLVE, SolutionStatus.ERROR, SolutionStatus.TIMEOUT):
        is_timeout = (response.status == SolutionStatus.TIMEOUT)
        card_bg = "border-amber-200 bg-amber-50/80 text-amber-900" if is_timeout else "border-red-200 bg-red-50/70 text-red-900"
        title_text = (
            "Quá thời gian tính toán cho phép (Computation Timed Out)"
            if is_timeout
            else "Không thể hoàn thành phép tính hoặc dữ liệu không hợp lệ"
        )
        icon_name = "timer_off" if is_timeout else "error"
        icon_color = "warning" if is_timeout else "negative"

        with ui.card().classes(f"w-full p-5 border {card_bg} rounded-xl shadow-xs"):
            with ui.row().classes("items-center gap-2 mb-2"):
                ui.icon(icon_name, color=icon_color, size="1.5rem")
                ui.label(title_text).classes(f"font-bold text-base {'text-amber-900' if is_timeout else 'text-red-900'}")
            for warn in response.warnings:
                ui.label(f"• {warn}").classes(f"text-sm {'text-amber-800' if is_timeout else 'text-red-800'} ml-6")
            if not response.warnings:
                ui.label("Dữ liệu đầu vào chưa đúng định dạng toán học hoặc vượt quá miền xác định.").classes("text-sm text-red-800 ml-6")
        return

    has_valid_answer = bool(response.final_result and response.final_result.strip())

    # 2. Main Solution Header & Final Answer Card
    with ui.card().classes("w-full p-6 shadow-sm border border-slate-200 rounded-xl bg-white gap-4"):
        # Header Row: Operation title (specific to operation) & Honest Verification Badge
        card_title = get_result_card_title(prob_type)
        with ui.row().classes("items-center justify-between w-full border-b border-slate-100 pb-3 flex-wrap gap-2"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("task_alt", color="positive", size="1.5rem")
                ui.label(card_title).classes("text-lg font-bold text-slate-900")

            # Verified Badge is ONLY rendered with non-empty valid answer
            render_verification_badge(response.verification, has_valid_result=has_valid_answer)

        # Problem statement: Labeled "ĐỀ CHO" and rendered with proper MathML notation
        statement_latex = format_problem_statement_latex(
            response.raw_input,
            prob_type,
            target_var,
            p_params,
        )
        with ui.column().classes("w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl gap-1.5"):
            ui.label("ĐỀ CHO:").classes("text-xs font-bold text-slate-600 uppercase tracking-wider")
            ui_math(statement_latex, block=True, classes="text-base md:text-lg text-slate-800 font-medium py-0.5")

        # Prominent Final Answer Box
        final_answer_latex = format_final_answer_latex(
            response.final_latex,
            prob_type,
            target_var,
            p_params,
        )
        with ui.column().classes("w-full p-5 bg-gradient-to-r from-blue-50/70 to-indigo-50/50 border border-blue-200 rounded-xl gap-2"):
            ui.label("ĐÁP SỐ CUỐI CÙNG:").classes("text-xs font-bold text-blue-900 uppercase tracking-wider")
            if final_answer_latex and final_answer_latex.strip():
                ui_math(final_answer_latex, block=True, classes="text-2xl md:text-3xl font-bold text-blue-900 py-1")
            else:
                ui.label(response.final_result or "Không tìm thấy kết quả hữu hạn").classes("text-xl font-bold text-slate-800 font-mono")

        # Domain Notes & Restrictions (Rendered cleanly as proper LaTeX)
        render_domain_restrictions(response.domain_restrictions, target_var)

        if response.warnings:
            with ui.column().classes("w-full p-3.5 bg-orange-50 border border-orange-200 rounded-lg gap-1"):
                ui.label("Lưu ý thuật toán / Giới hạn:").classes("text-xs font-bold text-orange-900 uppercase tracking-wide")
                for warn in response.warnings:
                    ui.label(f"• {warn}").classes("text-xs text-orange-950 font-medium")

        # Contextual Analysis Tools (2D Plot, 3D Plot, Bảng biến thiên)
        tool_2d, tool_3d, tool_table = determine_contextual_tools(
            prob_type,
            response.raw_input,
            target_var,
            is_success=(response.status == SolutionStatus.SUCCESS),
            params=params,
        )

        if tool_2d or tool_3d or tool_table:
            try:
                with ui.column().classes("w-full pt-2 border-t border-slate-100 gap-3"):
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label("Công cụ phân tích & trực quan hóa:").classes("text-xs font-bold text-slate-500 uppercase tracking-wider")

                    tools_row = ui.row().classes("items-center gap-2 flex-wrap")
                    chart_container = ui.column().classes("w-full mt-2")

                    with tools_row:
                        if tool_2d:
                            def show_2d():
                                chart_container.clear()
                                with chart_container:
                                    try:
                                        current_range = [-10.0, 10.0]
                                        fig = create_2d_plot(response.raw_input, target_var, tuple(current_range))
                                        if not fig:
                                            ui.notify("Không thể tạo đồ thị 2D cho hàm số này.", type="warning")
                                            return

                                        with ui.card().classes("w-full p-4 border border-blue-200 bg-white rounded-xl shadow-xs gap-3"):
                                            with ui.column().classes("w-full items-center text-center gap-1 border-b border-slate-100 pb-2"):
                                                ui.label("Đồ thị hàm số 2D (Tương tác Pan / Zoom):").classes("text-xs font-bold text-slate-500 uppercase tracking-wider")
                                                try:
                                                    p_expr, _ = parse_mathematical_input(response.raw_input, target_var)
                                                    ltx_title = f"y = {expr_to_latex(p_expr)}"
                                                except Exception:
                                                    ltx_title = f"y = {expr_to_latex(response.raw_input)}"
                                                ui_math(ltx_title, block=True, classes="text-xl md:text-2xl font-bold text-blue-900 py-0.5")

                                            # Viewport navigation toolbar
                                            with ui.row().classes("w-full items-center justify-between gap-2 flex-wrap bg-slate-50 p-2.5 rounded-lg border border-slate-200"):
                                                with ui.row().classes("items-center gap-1.5 flex-wrap"):
                                                    ui.label("Vùng hiển thị mẫu:").classes("text-xs font-bold text-slate-600")
                                                    presets = [
                                                        ("[-10, 10]", -10.0, 10.0),
                                                        ("[-24, -4]", -24.0, -4.0),
                                                        ("[-100, -80]", -100.0, -80.0),
                                                        ("[0, 20]", 0.0, 20.0),
                                                        ("[90, 110]", 90.0, 110.0),
                                                    ]
                                                    for label, r_min, r_max in presets:
                                                        ui.button(
                                                            label,
                                                            on_click=lambda _, rmin=r_min, rmax=r_max: update_plot_range(rmin, rmax),
                                                            color="slate-200",
                                                        ).classes("text-slate-800 text-xs px-2.5 py-1 rounded")

                                                with ui.row().classes("items-center gap-1 flex-wrap"):
                                                    def pan_left():
                                                        span = current_range[1] - current_range[0]
                                                        shift = span * 0.4
                                                        update_plot_range(current_range[0] - shift, current_range[1] - shift)

                                                    def pan_right():
                                                        span = current_range[1] - current_range[0]
                                                        shift = span * 0.4
                                                        update_plot_range(current_range[0] + shift, current_range[1] + shift)

                                                    def zoom_in():
                                                        mid = (current_range[0] + current_range[1]) / 2.0
                                                        span = (current_range[1] - current_range[0]) / 3.0
                                                        update_plot_range(mid - span, mid + span)

                                                    def zoom_out():
                                                        mid = (current_range[0] + current_range[1]) / 2.0
                                                        span = (current_range[1] - current_range[0]) * 0.75
                                                        update_plot_range(mid - span, mid + span)

                                                    def reset_view():
                                                        update_plot_range(-10.0, 10.0)

                                                    ui.button("⬅ Dịch trái", on_click=pan_left, color="slate-100").classes("text-slate-700 text-xs px-2 py-1 rounded")
                                                    ui.button("➡ Dịch phải", on_click=pan_right, color="slate-100").classes("text-slate-700 text-xs px-2 py-1 rounded")
                                                    ui.button("🔍+ Phóng to", on_click=zoom_in, color="slate-100").classes("text-slate-700 text-xs px-2 py-1 rounded")
                                                    ui.button("🔍- Thu nhỏ", on_click=zoom_out, color="slate-100").classes("text-slate-700 text-xs px-2 py-1 rounded")
                                                    ui.button("⟲ Đặt lại", on_click=reset_view, color="blue-1").classes("text-blue-800 text-xs px-2 py-1 rounded font-bold")

                                            # Plotly Element
                                            plot_elem = ui.plotly(fig).classes("w-full")

                                            def update_plot_range(x_min: float, x_max: float):
                                                try:
                                                    current_range[0] = x_min
                                                    current_range[1] = x_max
                                                    resampled = sample_function_2d(response.raw_input, target_var, x_min, x_max, 800)
                                                    if resampled:
                                                        xs, ys, ymin, ymax = resampled
                                                        plot_elem.figure["data"][0]["x"] = xs.tolist()
                                                        plot_elem.figure["data"][0]["y"] = ys.tolist()
                                                        plot_elem.figure["layout"]["xaxis"]["range"] = [x_min, x_max]
                                                        plot_elem.figure["layout"]["yaxis"]["range"] = [ymin, ymax]
                                                        plot_elem.update()
                                                except Exception as err:
                                                    ui.notify(f"Lỗi cập nhật vùng hiển thị: {err}", type="warning")

                                            def handle_relayout(e):
                                                args = getattr(e, "args", {}) or {}
                                                x0 = args.get("xaxis.range[0]")
                                                x1 = args.get("xaxis.range[1]")
                                                if x0 is not None and x1 is not None:
                                                    try:
                                                        fx0, fx1 = float(x0), float(x1)
                                                        if fx1 > fx0:
                                                            current_range[0], current_range[1] = fx0, fx1
                                                            span = fx1 - fx0
                                                            res = sample_function_2d(
                                                                response.raw_input,
                                                                target_var,
                                                                fx0 - 0.15 * span,
                                                                fx1 + 0.15 * span,
                                                                800,
                                                            )
                                                            if res:
                                                                xs, ys, _, _ = res
                                                                plot_elem.figure["data"][0]["x"] = xs.tolist()
                                                                plot_elem.figure["data"][0]["y"] = ys.tolist()
                                                                plot_elem.update()
                                                    except Exception:
                                                        pass

                                            plot_elem.on("plotly_relayout", handle_relayout)
                                    except Exception as exc:
                                        ui.notify(f"Không thể hiển thị đồ thị 2D: {exc}", type="warning")

                            ui.button("📊 Vẽ đồ thị 2D", on_click=show_2d, color="blue-7").classes("text-xs px-3 py-1.5 font-semibold rounded-lg")

                        if tool_3d:
                            def show_3d():
                                chart_container.clear()
                                with chart_container:
                                    try:
                                        p = params or {}
                                        plot_expr = response.raw_input
                                        is_surface_field = False
                                        if not can_plot_3d(plot_expr) and p.get("surface_expr"):
                                            plot_expr = p["surface_expr"]
                                            is_surface_field = True

                                        bounds: dict[str, tuple[float, float]] = {}
                                        u_var_name = str(p.get("u_var", "x")).strip()
                                        v_var_name = str(p.get("v_var", "y")).strip()
                                        if "u_min" in p and "u_max" in p:
                                            try:
                                                bounds[u_var_name] = (float(parse_safe_expression(p["u_min"], evaluate=True).evalf()), float(parse_safe_expression(p["u_max"], evaluate=True).evalf()))
                                                bounds[v_var_name] = (float(parse_safe_expression(p["v_min"], evaluate=True).evalf()), float(parse_safe_expression(p["v_max"], evaluate=True).evalf()))
                                            except Exception:
                                                pass
                                        elif "x_min" in p and "x_max" in p:
                                            try:
                                                bounds["x"] = (float(parse_safe_expression(p["x_min"], evaluate=True).evalf()), float(parse_safe_expression(p["x_max"], evaluate=True).evalf()))
                                                bounds["y"] = (float(parse_safe_expression(p["y_min"], evaluate=True).evalf()), float(parse_safe_expression(p["y_max"], evaluate=True).evalf()))
                                            except Exception:
                                                pass

                                        if p.get("surface_type") == "parametric" and p.get("param_x") and p.get("param_y"):
                                            u_b = bounds.get(u_var_name, (0.0, 1.0))
                                            v_b = bounds.get(v_var_name, (0.0, 1.0))
                                            fig = create_parametric_surface_plot(
                                                str(p.get("param_x", "u")),
                                                str(p.get("param_y", "v")),
                                                str(p.get("param_z", "0")),
                                                u_bounds=u_b,
                                                v_bounds=v_b,
                                                u_var=u_var_name,
                                                v_var=v_var_name,
                                            )
                                            ltx_title = rf"\mathbf{{r}}({u_var_name}, {v_var_name}) = \left({p.get('param_x')}, {p.get('param_y')}, {p.get('param_z')}\right)"
                                        else:
                                            fig = create_3d_plot(plot_expr, domain_bounds=bounds if bounds else None)
                                            clean_expr = plot_expr.split("=", 1)[1].strip() if "=" in plot_expr else plot_expr
                                            try:
                                                p_expr, _ = parse_mathematical_input(clean_expr, target_var)
                                                symbols = sorted(list(p_expr.free_symbols), key=lambda s: s.name)
                                                vars_str = ", ".join(s.name for s in symbols) if symbols else "x, y"
                                                if is_surface_field:
                                                    ltx_title = f"S: z = g({vars_str}) = {expr_to_latex(p_expr)}"
                                                else:
                                                    ltx_title = f"z = f({vars_str}) = {expr_to_latex(p_expr)}"
                                            except Exception:
                                                ltx_title = f"z = {expr_to_latex(clean_expr)}"

                                        if not fig:
                                            ui.notify("Không thể tạo đồ thị 3D cho hàm số này.", type="warning")
                                            return

                                        with ui.card().classes("w-full max-w-4xl mx-auto p-4 border border-indigo-200 bg-white rounded-xl shadow-xs gap-3"):
                                            with ui.column().classes("w-full items-center text-center gap-1 border-b border-slate-100 pb-2"):
                                                ui.label("Đồ thị không gian 3D (Hệ trục RGB: X-Đỏ, Y-Xanh lá, Z-Xanh dương):").classes("text-xs font-bold text-slate-500 uppercase tracking-wider")
                                                ui_math(ltx_title, block=True, classes="text-xl md:text-2xl font-bold text-indigo-900 py-0.5")

                                            ui.plotly(fig).classes("w-full h-[500px]")
                                    except Exception as exc:
                                        ui.notify(f"Không thể hiển thị đồ thị 3D: {exc}", type="warning")

                            ui.button("🌐 Vẽ đồ thị 3D", on_click=show_3d, color="indigo-7").classes("text-xs px-3 py-1.5 font-semibold rounded-lg")

                        if tool_table:
                            def show_table():
                                chart_container.clear()
                                with chart_container:
                                    try:
                                        table_data = compute_variation_table(response.raw_input, target_var)
                                        if table_data and table_data.get("intervals"):
                                            is_integral = prob_type in {ProblemType.INDEFINITE_INTEGRAL, ProblemType.INTEGRAL}
                                            if is_integral:
                                                table_data["context_title"] = f"Bảng biến thiên của hàm dưới dấu tích phân f({target_var})"
                                            else:
                                                table_data["context_title"] = f"Bảng biến thiên của hàm số f({target_var})"
                                            render_variation_table_component(table_data)
                                        else:
                                            ui.notify("Không thể xác định bảng biến thiên một cách chặt chẽ cho hàm này.", type="warning")
                                    except Exception as exc:
                                        ui.notify(f"Không thể tạo bảng biến thiên: {exc}", type="warning")

                            ui.button("📈 Bảng biến thiên", on_click=show_table, color="teal-7").classes("text-xs px-3 py-1.5 font-semibold rounded-lg")
            except Exception:
                pass

        # Computation time
        with ui.row().classes("justify-end w-full pt-1 text-xs text-slate-400"):
            ui.label(f"Thời gian tính toán & kiểm chứng: {response.execution_time_ms:.1f} ms")

    # 3. Derivation Steps Tree
    render_steps_container(response.steps, final_answer_latex=final_answer_latex)

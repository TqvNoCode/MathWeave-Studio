"""Result, paginated iteration table, Plotly chart, and pedagogical flow view for Explicit Euler."""

from __future__ import annotations

import math
from typing import Any

from nicegui import ui

from math_app.domain.numerical_ode import (
    NumericalIterationRow,
    NumericalODEOrder,
    NumericalODEResponse,
    NumericalODEStatus,
)
from math_app.presentation.components.math_view import ui_math, ui_math_text
from math_app.presentation.components.shared import render_feedback_card, status_badge
from math_app.presentation.design_system.tokens import INTERACTION
from math_app.presentation.services.numerical_plot_service import (
    create_numerical_derivative_plot,
    create_numerical_euler_plot,
)

_PREVIEW_LIMIT = 8
_PAGE_SIZE = 25


def format_numeric_display(val: float | None) -> str:
    """Format floating-point numbers consistently for iteration tables without mutating internal values."""
    if val is None:
        return "—"
    if not math.isfinite(val):
        return str(val)
    if val == 0.0:
        return "0.000000"
    abs_v = abs(val)
    if abs_v < 1e-4 or abs_v >= 1e6:
        return f"{val:.6e}"
    return f"{val:.6f}"


def _build_recurrence_sample_items(response: NumericalODEResponse) -> list[str]:
    """Generate worked KaTeX arithmetic samples for first two steps and final step."""
    rows = response.rows
    if len(rows) < 2:
        return []

    total_steps = len(rows) - 1
    sample_indices = [0]
    if total_steps >= 2:
        sample_indices.append(1)
    if total_steps > 2:
        sample_indices.append(total_steps - 1)

    t_var = response.independent_var
    y_var = response.dependent_var
    samples: list[str] = []
    for n in sample_indices:
        r0 = rows[n]
        r1 = rows[n + 1]
        h_n = r0.step_used if r0.step_used is not None else (r1.t - r0.t)
        if response.order == NumericalODEOrder.FIRST_ORDER:
            samples.append(
                f"• **Bước $n = {n}$:** "
                f"${t_var}_{{{n+1}}} = {r0.t:.6g} + ({h_n:.6g}) = {r1.t:.6g}$; "
                f"${y_var}_{{{n+1}}} = {r0.y:.6g} + ({h_n:.6g}) \\cdot ({r0.slope_y:.6g}) = {r1.y:.6g}$"
            )
        else:
            v0 = r0.v if r0.v is not None else 0.0
            v1 = r1.v if r1.v is not None else 0.0
            f_val = r0.slope_v if r0.slope_v is not None else 0.0
            samples.append(
                f"• **Bước $n = {n}$:** "
                f"${t_var}_{{{n+1}}} = {r1.t:.6g}$; "
                f"${y_var}_{{{n+1}}} = {r0.y:.6g} + ({h_n:.6g}) \\cdot ({v0:.6g}) = {r1.y:.6g}$; "
                f"$v_{{{n+1}}} = {v0:.6g} + ({h_n:.6g}) \\cdot ({f_val:.6g}) = {v1:.6g}$"
            )
    return samples


def _render_iteration_table_section(response: NumericalODEResponse) -> None:
    """Render Section 5: Compact preview + expandable paginated iteration table."""
    rows = response.rows
    if not rows:
        return

    ana = response.analytical_comparison
    has_exact = bool(ana is not None and ana.available and len(ana.points) == len(rows))
    exact_by_idx = {pt.step_index: pt for pt in ana.points} if has_exact and ana is not None else {}

    t_v = response.independent_var
    y_v = response.dependent_var
    is_second = response.order == NumericalODEOrder.SECOND_ORDER

    expanded_state = {"expanded": False, "page": 0}
    total_rows = len(rows)
    total_pages = max(1, math.ceil(total_rows / _PAGE_SIZE))

    with ui.column().classes("w-full gap-2.5 min-w-0"):
        with ui.row().classes("items-center justify-between w-full flex-wrap gap-2"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("table_rows", size="1.2rem").classes("text-blue-600")
                ui.label("5. Bảng giá trị lặp (Iteration Table)").classes(
                    "text-sm md:text-base font-bold text-slate-900"
                )
                status_badge(f"{total_rows} hàng (n = 0..{total_rows - 1})", variant="neutral")

            toggle_btn = ui.button(
                f"Mở rộng bảng đầy đủ ({total_rows} hàng)" if total_rows > _PREVIEW_LIMIT else "Đang hiển thị đầy đủ",
                icon="unfold_more" if total_rows > _PREVIEW_LIMIT else "check",
            ).props('outline dense no-caps aria-label="Mở rộng hoặc thu gọn bảng giá trị lặp"').classes(
                f"text-xs text-blue-700 border-blue-200 bg-white rounded-lg px-3 py-1 font-semibold {INTERACTION.FOCUS_RING}"
            )
            if total_rows <= _PREVIEW_LIMIT:
                toggle_btn.disable()

        table_container = ui.column().classes("w-full gap-2 min-w-0")

        def _render_table_body() -> None:
            table_container.clear()
            is_exp = expanded_state["expanded"]
            page = expanded_state["page"]

            if not is_exp and total_rows > _PREVIEW_LIMIT:
                display_rows: list[NumericalIterationRow | None] = list(rows[:_PREVIEW_LIMIT])
                if total_rows > _PREVIEW_LIMIT + 1:
                    display_rows.append(None)  # ellipsis row
                display_rows.append(rows[-1])
            elif is_exp:
                start = page * _PAGE_SIZE
                end = min(total_rows, start + _PAGE_SIZE)
                display_rows = list(rows[start:end])
            else:
                display_rows = list(rows)

            with table_container:
                if is_exp and total_pages > 1:
                    with ui.row().classes(
                        "w-full items-center justify-between p-2 bg-slate-50 border border-slate-200 rounded-lg flex-wrap gap-2"
                    ):
                        start_idx = page * _PAGE_SIZE
                        end_idx = min(total_rows, start_idx + _PAGE_SIZE) - 1
                        ui.label(
                            f"Trang {page + 1}/{total_pages} (hiển thị n = {start_idx}..{end_idx})"
                        ).classes("text-xs font-semibold text-slate-700")
                        with ui.row().classes("items-center gap-1.5 flex-wrap"):
                            def _go_page(p: int) -> None:
                                expanded_state["page"] = max(0, min(total_pages - 1, p))
                                _render_table_body()

                            btn_first = ui.button("Đầu", on_click=lambda: _go_page(0)).props("outline dense no-caps").classes("text-xs px-2 py-0.5 rounded")
                            btn_prev = ui.button("Trước", on_click=lambda: _go_page(page - 1)).props("outline dense no-caps").classes("text-xs px-2 py-0.5 rounded")
                            btn_next = ui.button("Sau", on_click=lambda: _go_page(page + 1)).props("outline dense no-caps").classes("text-xs px-2 py-0.5 rounded")
                            btn_last = ui.button("Cuối", on_click=lambda: _go_page(total_pages - 1)).props("outline dense no-caps").classes("text-xs px-2 py-0.5 rounded")
                            if page == 0:
                                btn_first.disable()
                                btn_prev.disable()
                            if page >= total_pages - 1:
                                btn_next.disable()
                                btn_last.disable()

                with ui.column().classes("w-full overflow-x-auto border border-slate-200 rounded-xl bg-white min-w-0 math-scroll-box"):
                    cols = [
                        ("n", False),
                        (f"{t_v}_n", True),
                        (f"{y_v}_n", True),
                    ]
                    if is_second:
                        cols.append((f"v_n = {y_v}'_n", True))
                        cols.append((f"F({t_v}_n, {y_v}_n, v_n)", True))
                    else:
                        cols.append((f"f({t_v}_n, {y_v}_n)", True))
                    if has_exact:
                        cols.append((f"{y_v}({t_v}_n)", True))
                        cols.append((f"E_n = |{y_v}({t_v}_n) - {y_v}_n|", True))

                    grid_cols = f"grid-template-columns: 64px repeat({len(cols) - 1}, minmax(132px, 1fr)); min-width: {64 + (len(cols) - 1) * 136}px;"

                    # Header Row
                    with ui.element("div").style(grid_cols).classes(
                        "grid items-center bg-slate-100 border-b border-slate-200 px-3 py-2 text-xs font-bold text-slate-800"
                    ):
                        for h_txt, is_math in cols:
                            with ui.element("div").classes("px-1.5 py-0.5 text-left"):
                                if is_math:
                                    ui_math(h_txt, block=False, classes="text-xs font-bold text-slate-800")
                                else:
                                    ui.label(h_txt).classes("text-xs font-bold text-slate-800 font-mono")

                    # Data Rows
                    for r in display_rows:
                        if r is None:
                            with ui.element("div").classes(
                                "px-4 py-1.5 text-xs text-slate-500 italic bg-slate-50/70 border-b border-slate-100"
                            ):
                                ui.label(
                                    f"... ({total_rows - _PREVIEW_LIMIT - 1} bước trung gian được thu gọn — bấm 'Mở rộng bảng đầy đủ' để xem toàn bộ)"
                                )
                            continue

                        is_final = r.step_index == total_rows - 1
                        row_bg = "bg-blue-50/70 font-semibold" if is_final else ("bg-white" if r.step_index % 2 == 0 else "bg-slate-50/50")
                        with ui.element("div").style(grid_cols).classes(
                            f"grid items-center px-3 py-1.5 text-xs border-b border-slate-100 {row_bg} font-mono text-slate-800"
                        ):
                            ui.label(str(r.step_index)).classes("px-1.5 text-slate-600")
                            ui.label(format_numeric_display(r.t)).props(f'title="{r.t!r}"').classes("px-1.5")
                            ui.label(format_numeric_display(r.y)).props(f'title="{r.y!r}"').classes("px-1.5 text-blue-900 font-semibold")
                            if is_second:
                                ui.label(format_numeric_display(r.v)).props(f'title="{r.v!r}"').classes("px-1.5")
                                ui.label(format_numeric_display(r.slope_v)).props(f'title="{r.slope_v!r}"').classes("px-1.5")
                            else:
                                ui.label(format_numeric_display(r.slope_y)).props(f'title="{r.slope_y!r}"').classes("px-1.5")
                            if has_exact:
                                pt = exact_by_idx[r.step_index]
                                ui.label(format_numeric_display(pt.y_exact)).props(f'title="{pt.y_exact!r}"').classes("px-1.5 text-emerald-800")
                                ui.label(format_numeric_display(pt.abs_error)).props(f'title="{pt.abs_error!r}"').classes("px-1.5 text-amber-800")

                ui.label(
                    "Lưu ý: Bảng hiển thị làm tròn 6 chữ số thập phân để dễ đọc; quá trình tính toán nội bộ luôn giữ độ chính xác dấu phẩy động đầy đủ (IEEE 754 float64)."
                ).classes("text-[11px] text-slate-500 italic")

        def _toggle_expand() -> None:
            expanded_state["expanded"] = not expanded_state["expanded"]
            expanded_state["page"] = 0
            if expanded_state["expanded"]:
                toggle_btn.set_text("Thu gọn bảng (xem tóm tắt)")
                toggle_btn.props("icon=unfold_less")
            else:
                toggle_btn.set_text(f"Mở rộng bảng đầy đủ ({total_rows} hàng)")
                toggle_btn.props("icon=unfold_more")
            _render_table_body()

        toggle_btn.on_click(_toggle_expand)
        _render_table_body()


def _render_graph_section(response: NumericalODEResponse) -> None:
    """Render Section 6: Interactive Plotly chart of y_n (and optional analytical curve / derivative)."""
    ana = response.analytical_comparison
    has_exact = bool(ana is not None and ana.available and ana.points)
    fig = create_numerical_euler_plot(response, show_exact=has_exact)
    if fig is None:
        return

    with ui.column().classes("w-full gap-2.5 min-w-0"):
        with ui.row().classes("items-center justify-between w-full flex-wrap gap-2"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("show_chart", size="1.2rem").classes("text-blue-600")
                ui.label("6. Đồ thị xấp xỉ số (Numerical Graph)").classes(
                    "text-sm md:text-base font-bold text-slate-900"
                )

            exact_toggle: Any = None
            if has_exact:
                exact_toggle = ui.checkbox(
                    "Hiển thị nghiệm giải tích đối chiếu",
                    value=True,
                ).classes("text-xs font-medium text-emerald-800")

        with ui.card().classes("w-full p-3 border border-slate-200 rounded-xl bg-white shadow-none min-w-0"):
            plot_el = ui.plotly(fig).classes("w-full")

            if exact_toggle is not None:
                def _on_toggle_exact(e: Any) -> None:
                    new_fig = create_numerical_euler_plot(response, show_exact=bool(e.value))
                    if new_fig is not None:
                        plot_el.update_figure(new_fig)

                exact_toggle.on_value_change(_on_toggle_exact)

        if response.order == NumericalODEOrder.SECOND_ORDER:
            deriv_fig = create_numerical_derivative_plot(response)
            if deriv_fig is not None:
                with ui.expansion(
                    f"Xem đồ thị đạo hàm xấp xỉ {response.dependent_var}'({response.independent_var})",
                    icon="timeline",
                ).classes("w-full bg-slate-50/70 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700"):
                    with ui.column().classes("w-full p-2 bg-white"):
                        ui.plotly(deriv_fig).classes("w-full")


def _render_pedagogical_explanation_section(response: NumericalODEResponse) -> None:
    """Render Section 7: 4-stage expandable pedagogical explanation with KaTeX formulas."""
    t_v = response.independent_var
    y_v = response.dependent_var
    is_second = response.order == NumericalODEOrder.SECOND_ORDER
    samples = _build_recurrence_sample_items(response)
    verif = response.verification
    ana = response.analytical_comparison

    with ui.column().classes("w-full gap-2.5 min-w-0"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("school", size="1.2rem").classes("text-blue-600")
            ui.label("7. Giải thích sư phạm chi tiết (4 giai đoạn)").classes(
                "text-sm md:text-base font-bold text-slate-900"
            )

        if not is_second:
            # First-Order 4 Stages
            with ui.expansion("Giai đoạn 1: Nhận dạng bài toán giá trị ban đầu (IVP)", icon="filter_1", value=True).classes(
                "w-full bg-white border border-slate-200 rounded-xl"
            ):
                with ui.column().classes("w-full p-3 gap-2 text-xs md:text-sm text-slate-700"):
                    ui_math_text(
                        f"Cô lập đạo hàm bậc nhất về dạng chuẩn $y' = f({t_v}, {y_v})$ kèm điều kiện ban đầu tại ${t_v}_0$:",
                        classes="leading-relaxed",
                    )
                    ui_math(
                        f"{y_v}'({t_v}) = {response.canonical_rhs_latex}, \\qquad {y_v}({response.t0:g}) = {response.y0:g}",
                        block=True,
                        classes="text-sm md:text-base font-semibold text-slate-900",
                    )

            with ui.expansion("Giai đoạn 2: Chọn bước nhảy và thiết lập lưới thời gian", icon="filter_2").classes(
                "w-full bg-white border border-slate-200 rounded-xl"
            ):
                with ui.column().classes("w-full p-3 gap-2 text-xs md:text-sm text-slate-700"):
                    dir_text = "thuận ($T > t_0$)" if response.direction > 0 else "lùi ($T < t_0$)"
                    ui_math_text(
                        f"Trên đoạn $[{response.t0:g}, {response.t_end:g}]$ theo chiều {dir_text} với bước nhảy chọn $h = {response.step_size:g}$, "
                        f"lưới gồm $N = {response.total_steps}$ bước: ${t_v}_{{n+1}} = {t_v}_n + h_n$.",
                        classes="leading-relaxed",
                    )
                    if response.has_shortened_final_step:
                        ui_math_text(
                            f"Do khoảng không chia hết cho $h$, bước cuối được rút ngắn thành "
                            f"$h_{{{response.total_steps - 1}}} = \\min(h, |T - {t_v}_{{{response.total_steps - 1}}}|) = {response.final_step_size:g}$ "
                            f"để dừng chính xác tại $T = {response.t_end:g}$.",
                            classes="text-amber-900 leading-relaxed",
                        )

            with ui.expansion("Giai đoạn 3: Áp dụng công thức truy hồi Explicit Euler", icon="filter_3").classes(
                "w-full bg-white border border-slate-200 rounded-xl"
            ):
                with ui.column().classes("w-full p-3 gap-2 text-xs md:text-sm text-slate-700"):
                    ui_math_text(
                        "Tại mỗi bước $n$, độ dốc được tính **chỉ từ giá trị ở bước trước** $({t_v}_n, {y_v}_n)$:",
                        classes="leading-relaxed",
                    )
                    ui_math(
                        f"{t_v}_{{n+1}} = {t_v}_n + h_n, \\qquad {y_v}_{{n+1}} = {y_v}_n + h_n\\,f({t_v}_n, {y_v}_n)",
                        block=True,
                        classes="text-sm md:text-base font-semibold text-blue-950",
                    )
                    if samples:
                        with ui.expansion("Xem tính toán mẫu cho các bước tiêu biểu", icon="calculate").classes(
                            "w-full bg-slate-50 border border-slate-200 rounded-lg text-xs"
                        ):
                            with ui.column().classes("w-full p-2.5 gap-1.5"):
                                for s in samples:
                                    ui_math_text(s, classes="text-xs text-slate-800")

            with ui.expansion("Giai đoạn 4: Diễn giải nghiệm xấp xỉ, sai số & kiểm chứng độc lập", icon="filter_4").classes(
                "w-full bg-white border border-slate-200 rounded-xl"
            ):
                with ui.column().classes("w-full p-3 gap-2 text-xs md:text-sm text-slate-700"):
                    ui_math_text(
                        f"• **Kết quả xấp xỉ:** Sau $N = {response.total_steps}$ bước, ta thu được ${y_v}({response.t_end:g}) \\approx {format_numeric_display(response.final_y)}$.",
                        classes="leading-relaxed",
                    )
                    ui_math_text(
                        "• **Bản chất sai số & ổn định:** Explicit Euler là phương pháp số bậc 1 với sai số chặt cục bộ $O(h^2)$ và sai số toàn cục $O(h)$ dưới các giả thiết đủ trơn và ổn định. Phương pháp không ổn định với mọi bước nhảy $h$ (đặc biệt với phương trình cứng).",
                        classes="leading-relaxed",
                    )
                    if ana is not None and ana.available and ana.final_abs_error is not None:
                        ui_math_text(
                            f"• **Đối chiếu giải tích:** ${ana.exact_latex}$; sai số tại điểm cuối $|{y_v}(T) - {y_v}_N| = {ana.final_abs_error:.6g}$, sai số lớn nhất trên lưới = ${ana.max_abs_error:.6g}$.",
                            classes="text-emerald-900 leading-relaxed",
                        )
                    if verif is not None and verif.checks:
                        for chk in verif.checks:
                            icon_ch = "✓" if chk.passed else "✗"
                            ui_math_text(
                                f"{icon_ch} **{chk.name}:** {chk.details}",
                                classes="text-xs text-slate-700",
                            )
        else:
            # Second-Order 4 Stages
            with ui.expansion("Giai đoạn 1: Chuyển PTVP cấp 2 về hệ phương trình cấp 1", icon="filter_1", value=True).classes(
                "w-full bg-white border border-slate-200 rounded-xl"
            ):
                with ui.column().classes("w-full p-3 gap-2 text-xs md:text-sm text-slate-700"):
                    if response.is_euler_cauchy_transformed:
                        ui_math_text(
                            f"Phương trình Euler–Cauchy được biến đổi đại số về dạng chuẩn $y'' = F({t_v}, y, y')$ trên miền chính quy (${t_v} \\neq 0$):",
                            classes="leading-relaxed",
                        )
                    ui_math_text(
                        f"Đặt $z_1 = {y_v}$ (vị trí) và $z_2 = v = {y_v}'$ (đạo hàm/vận tốc), phương trình cấp 2 trở thành hệ cấp 1:",
                        classes="leading-relaxed",
                    )
                    ui_math(
                        f"\\begin{{cases}} z_1' = z_2 \\\\ z_2' = F({t_v}, z_1, z_2) = {response.canonical_rhs_latex} \\end{{cases}}",
                        block=True,
                        classes="text-sm md:text-base font-semibold text-slate-900",
                    )

            with ui.expansion("Giai đoạn 2: Thiết lập điều kiện ban đầu và lưới thời gian", icon="filter_2").classes(
                "w-full bg-white border border-slate-200 rounded-xl"
            ):
                with ui.column().classes("w-full p-3 gap-2 text-xs md:text-sm text-slate-700"):
                    ui_math(
                        f"{t_v}_0 = {response.t0:g}, \\quad {y_v}_0 = {response.y0:g}, \\quad v_0 = {y_v}'({response.t0:g}) = {response.v0:g}",
                        block=True,
                        classes="text-sm md:text-base font-semibold text-slate-900",
                    )
                    ui_math_text(
                        f"Lưới trên đoạn $[{response.t0:g}, {response.t_end:g}]$ gồm $N = {response.total_steps}$ bước với $h = {response.step_size:g}$"
                        + (f" (bước cuối rút ngắn $h_{{{response.total_steps - 1}}} = {response.final_step_size:g}$)." if response.has_shortened_final_step else "."),
                        classes="leading-relaxed",
                    )

            with ui.expansion("Giai đoạn 3: Cập nhật đồng thời Explicit Euler cho cả hai biến", icon="filter_3").classes(
                "w-full bg-white border border-slate-200 rounded-xl"
            ):
                with ui.column().classes("w-full p-3 gap-2 text-xs md:text-sm text-slate-700"):
                    ui_math_text(
                        "Cả $y_{n+1}$ và $v_{n+1}$ đều được tính **đồng thời từ cặp giá trị cũ** $({y_v}_n, v_n)$ (không dùng ${y_v}_{n+1}$ vừa cập nhật để tính $v_{n+1}$):",
                        classes="leading-relaxed",
                    )
                    ui_math(
                        f"{y_v}_{{n+1}} = {y_v}_n + h_n\\,v_n, \\qquad v_{{n+1}} = v_n + h_n\\,F({t_v}_n, {y_v}_n, v_n)",
                        block=True,
                        classes="text-sm md:text-base font-semibold text-blue-950",
                    )
                    if samples:
                        with ui.expansion("Xem tính toán mẫu cho các bước tiêu biểu", icon="calculate").classes(
                            "w-full bg-slate-50 border border-slate-200 rounded-lg text-xs"
                        ):
                            with ui.column().classes("w-full p-2.5 gap-1.5"):
                                for s in samples:
                                    ui_math_text(s, classes="text-xs text-slate-800")

            with ui.expansion("Giai đoạn 4: Diễn giải kết quả, đối chiếu & kiểm chứng độc lập", icon="filter_4").classes(
                "w-full bg-white border border-slate-200 rounded-xl"
            ):
                with ui.column().classes("w-full p-3 gap-2 text-xs md:text-sm text-slate-700"):
                    ui_math_text(
                        f"• **Kết quả xấp xỉ tại $T = {response.t_end:g}$:** ${y_v}({response.t_end:g}) \\approx {format_numeric_display(response.final_y)}$ và ${y_v}'({response.t_end:g}) \\approx {format_numeric_display(response.final_v)}$.",
                        classes="leading-relaxed",
                    )
                    ui_math_text(
                        "• **Tính chất phương pháp:** Explicit Euler có sai số chặt cục bộ $O(h^2)$ và sai số toàn cục $O(h)$ dưới các giả thiết đủ trơn và ổn định; với hệ dao động như $y'' = -y$, Explicit Euler không bảo toàn năng lượng và có xu hướng khuếch đại biên độ theo thời gian.",
                        classes="leading-relaxed",
                    )
                    if ana is not None and ana.available and ana.final_abs_error is not None:
                        ui_math_text(
                            f"• **Đối chiếu giải tích:** ${ana.exact_latex}$; sai số tại điểm cuối $|{y_v}(T) - {y_v}_N| = {ana.final_abs_error:.6g}$, sai số lớn nhất = ${ana.max_abs_error:.6g}$.",
                            classes="text-emerald-900 leading-relaxed",
                        )
                    if verif is not None and verif.checks:
                        for chk in verif.checks:
                            icon_ch = "✓" if chk.passed else "✗"
                            ui_math_text(
                                f"{icon_ch} **{chk.name}:** {chk.details}",
                                classes="text-xs text-slate-700",
                            )


def render_numerical_euler_result(response: NumericalODEResponse) -> None:
    """Render complete Explicit Euler numerical results following the 7-section pedagogical hierarchy."""
    if response.status != NumericalODEStatus.SUCCESS:
        title_map = {
            NumericalODEStatus.INVALID_INPUT: "Tham số hoặc phương trình đầu vào chưa hợp lệ",
            NumericalODEStatus.SINGULARITY_ERROR: "Phát hiện điểm kỳ dị trên khoảng tích phân",
            NumericalODEStatus.NUMERICAL_ERROR: "Lỗi miền xác định hoặc tràn số học khi lặp",
            NumericalODEStatus.ITERATION_LIMIT_EXCEEDED: "Vượt quá giới hạn số bước lặp an toàn",
            NumericalODEStatus.ERROR: "Không thể thực hiện phép tính xấp xỉ số",
        }
        variant = "warning" if response.status == NumericalODEStatus.ITERATION_LIMIT_EXCEEDED else "error"
        msgs = [response.error_message or "Không thể thực hiện phép giải xấp xỉ Explicit Euler."]
        if response.failing_step is not None:
            msgs.append(f"Bước dừng lỗi: n = {response.failing_step}")
        render_feedback_card(
            title=title_map.get(response.status, "Lỗi phép tính số"),
            messages=msgs,
            variant=variant,
        )
        return

    t_v = response.independent_var
    y_v = response.dependent_var
    is_second = response.order == NumericalODEOrder.SECOND_ORDER
    verif = response.verification
    ana = response.analytical_comparison

    with ui.card().classes(
        "w-full p-4 md:p-5 shadow-sm border border-slate-200 rounded-xl bg-white gap-4 min-w-0 max-w-full"
    ):
        # Header Bar (Visually distinguishable from exact analytical solution)
        with ui.row().classes("items-center justify-between w-full border-b border-slate-100 pb-2.5 flex-wrap gap-2"):
            with ui.row().classes("items-center gap-2 flex-wrap"):
                ui.icon("analytics", color="primary", size="1.45rem")
                ui.label("Kết quả xấp xỉ số — Explicit Euler").classes("text-lg font-bold text-slate-900")
                status_badge("XẤP XỈ SỐ · KHÔNG PHẢI NGHIỆM CHÍNH XÁC", variant="info")

            if verif is not None and verif.is_verified:
                status_badge("✓ Đã kiểm chứng truy hồi số", variant="success")
            elif verif is not None:
                status_badge("⚠ Kiểm chứng số không đạt", variant="warning")

        # 1. Problem Summary
        with ui.column().classes(
            "w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl gap-2 min-w-0 math-scroll-box"
        ):
            ui.label("1. Tóm tắt bài toán (Problem Summary)").classes(
                "text-xs font-bold text-slate-700 uppercase tracking-wider"
            )
            ui_math(response.equation_latex, block=True, classes="text-base md:text-lg font-semibold text-slate-900")
            ic_latex = (
                f"{y_v}({response.t0:g}) = {response.y0:g}, \\quad {y_v}'({response.t0:g}) = {response.v0:g}"
                if is_second
                else f"{y_v}({response.t0:g}) = {response.y0:g}"
            )
            ui_math(
                f"\\text{{Điều kiện ban đầu: }} {ic_latex}, \\quad {t_v} \\in [{min(response.t0, response.t_end):g}, {max(response.t0, response.t_end):g}]",
                block=False,
                classes="text-xs md:text-sm text-slate-700 font-medium",
            )
            if response.is_euler_cauchy_transformed:
                with ui.row().classes(
                    "w-full items-start gap-2 p-2.5 bg-indigo-50/70 border border-indigo-200 rounded-lg text-xs text-indigo-950"
                ):
                    ui.icon("info", size="1rem").classes("text-indigo-700 shrink-0 mt-0.5")
                    ui_math_text(
                        f"Đã biến đổi phương trình Euler–Cauchy về dạng chuẩn số học "
                        f"${y_v}'' = {response.canonical_rhs_latex}$ (yêu cầu ${t_v} \\neq 0$ trên toàn đoạn tích phân).",
                        classes="text-xs leading-relaxed",
                    )

        # 2. Numerical Method Used
        with ui.column().classes("w-full p-3.5 bg-blue-50/40 border border-blue-200/80 rounded-xl gap-1.5 min-w-0"):
            ui.label("2. Phương pháp số áp dụng (Numerical Method)").classes(
                "text-xs font-bold text-blue-950 uppercase tracking-wider"
            )
            ui_math_text(
                "**Phương pháp Euler tiến (Explicit Euler / Forward Euler):** "
                "Phương pháp sai phân hữu hạn bậc nhất tính giá trị xấp xỉ rời rạc từ bài toán giá trị ban đầu (IVP). "
                "Sai số chặt cục bộ là $O(h^2)$ và sai số toàn cục là $O(h)$ dưới các giả thiết đủ trơn và ổn định; "
                "phương pháp không ổn định với mọi kích thước bước $h$. *(Lưu ý: Khác hoàn toàn với phương trình vi phân giải tích Euler–Cauchy).*",
                classes="text-xs md:text-sm text-slate-700 leading-relaxed",
            )

        # 3. Selected Parameters
        with ui.column().classes("w-full p-3.5 bg-white border border-slate-200 rounded-xl gap-2 min-w-0"):
            ui.label("3. Tham số đã chọn (Selected Parameters)").classes(
                "text-xs font-bold text-slate-700 uppercase tracking-wider"
            )
            step_desc = (
                f"{response.step_size:g} (bước cuối rút ngắn: {response.final_step_size:g})"
                if response.has_shortened_final_step
                else f"{response.step_size:g}"
            )
            dir_label = "Tịnh tiến thuận (+h)" if response.direction > 0 else "Tịnh tiến lùi (-h)"
            ic_disp = (
                f"{y_v}({response.t0:g}) = {response.y0:g}, {y_v}'({response.t0:g}) = {response.v0:g}"
                if is_second
                else f"{y_v}({response.t0:g}) = {response.y0:g}"
            )
            meta_items = [
                ("Phương pháp", "Explicit Euler"),
                ("Bước nhảy h", step_desc),
                ("Khoảng tích phân", f"[{response.t0:g} → {response.t_end:g}] ({dir_label})"),
                ("Tổng số bước lặp (N)", f"{response.total_steps:,}"),
                ("Điều kiện ban đầu", ic_disp),
                ("Thời gian thực thi", f"{response.execution_time_ms:.2f} ms"),
            ]
            with ui.element("div").classes("grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 w-full"):
                for k, v in meta_items:
                    with ui.column().classes("p-2.5 bg-slate-50 border border-slate-200/80 rounded-lg gap-0.5 min-w-0"):
                        ui.label(k).classes("text-[11px] font-bold text-slate-500 uppercase tracking-wider")
                        ui.label(v).classes("text-xs md:text-sm font-mono font-semibold text-slate-900 break-words")

        # 4. Final Numerical Result
        with ui.column().classes(
            "w-full p-4 bg-gradient-to-r from-blue-50/80 to-indigo-50/60 border-2 border-blue-200 rounded-xl gap-2 min-w-0 math-scroll-box"
        ):
            ui.label("4. Kết quả xấp xỉ cuối cùng (Final Numerical Approximation)").classes(
                "text-xs font-bold text-blue-900 uppercase tracking-wider"
            )
            final_ltx = (
                f"{y_v}({response.t_end:g}) \\approx {format_numeric_display(response.final_y)}, \\qquad "
                f"{y_v}'({response.t_end:g}) \\approx {format_numeric_display(response.final_v)}"
                if is_second
                else f"{y_v}({response.t_end:g}) \\approx {format_numeric_display(response.final_y)}"
            )
            ui_math(final_ltx, block=True, classes="text-xl md:text-2xl font-bold text-blue-950 py-0.5")

            if ana is not None and ana.available and ana.points:
                last_pt = ana.points[-1]
                with ui.row().classes(
                    "w-full items-center gap-3 flex-wrap p-2.5 bg-white/90 border border-emerald-200 rounded-lg text-xs text-emerald-950"
                ):
                    ui.icon("compare_arrows", size="1.1rem").classes("text-emerald-700 shrink-0")
                    ui_math_text(
                        f"**Đối chiếu giải tích:** ${ana.exact_latex}$ | "
                        f"Giá trị chính xác tại $T$: ${format_numeric_display(last_pt.y_exact)}$ | "
                        f"Sai số tuyệt đối cuối $|y(T)-y_N| = {ana.final_abs_error:.6g}$ | "
                        f"Sai số lớn nhất $= {ana.max_abs_error:.6g}$",
                        classes="text-xs leading-relaxed",
                    )
            elif ana is not None and not ana.available and ana.notes:
                ui.label(f"Đối chiếu giải tích: {ana.notes}").classes("text-xs text-slate-600 italic")

        # Warnings / Shortened step notice
        if response.warnings:
            with ui.column().classes("w-full p-3 bg-amber-50 border border-amber-200 rounded-xl gap-1 min-w-0"):
                for w in response.warnings:
                    ui.label(f"• {w}").classes("text-xs text-amber-900 font-medium")

        # 5. Iteration Table
        _render_iteration_table_section(response)

        # 6. Numerical Graph
        _render_graph_section(response)

        # 7. Detailed Pedagogical Explanation
        _render_pedagogical_explanation_section(response)

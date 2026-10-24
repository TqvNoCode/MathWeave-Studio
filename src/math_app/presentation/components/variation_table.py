"""Pedagogical mathematical variation table component."""

from __future__ import annotations

from typing import Any
from nicegui import ui

from math_app.presentation.components.math_view import math_html, ui_math


def _format_cell_math(val_str: str) -> str:
    """Format a table value using math_html, handling infinity and expressions cleanly."""
    if not val_str or not val_str.strip():
        return ""
    v = val_str.strip()
    if v in ("-oo", "-inf", "-\\infty", "-∞"):
        return math_html(r"-\infty", block=False)
    if v in ("oo", "inf", "\\infty", "+∞", "+\\infty", "+oo", "+inf"):
        return math_html(r"+\infty", block=False)
    return math_html(v, block=False)


def render_variation_table_component(table_data: dict[str, Any]) -> None:
    """Render a textbook-grade Vietnamese mathematical variation table (Bảng biến thiên)."""
    if not table_data:
        ui.notify("Không thể khởi tạo bảng biến thiên.", type="warning")
        return

    expr_ltx = table_data.get("expression_latex", table_data.get("expression", ""))
    d_expr_ltx = table_data.get("derivative_latex", table_data.get("derivative", ""))
    clean_var = table_data.get("variable", "x")
    domain_ltx = table_data.get("domain_latex", r"\mathcal{D} = \mathbb{R}")
    transition_pts = table_data.get("transition_points", [])
    intervals = table_data.get("intervals", [])
    is_complete = table_data.get("is_complete", True)
    limitations = table_data.get("limitations", [])

    with ui.card().classes("w-full p-5 border border-blue-200 bg-white rounded-xl shadow-xs gap-4"):
        # 1. Header with function title and domain
        with ui.column().classes("w-full items-center text-center gap-1.5 border-b border-slate-100 pb-3"):
            ctx_title = table_data.get("context_title", "Bảng biến thiên của hàm số")
            ui.label(ctx_title).classes("text-base font-bold text-red-600 tracking-tight")
            header_math = f"y = {expr_ltx}, \\quad \\text{{trên }} {domain_ltx}"
            ui_math(header_math, block=True, classes="text-lg md:text-xl font-bold text-blue-900 py-0.5")
            ui_math(f"f'({clean_var}) = {d_expr_ltx}", block=False, classes="text-xs font-mono text-slate-600")

        # 2. Main structured variation table
        table_html = _build_variation_table_html(clean_var, transition_pts, intervals)
        with ui.row().classes("w-full overflow-x-auto py-2 justify-center"):
            ui.html(table_html).classes("w-full")

        # 3. Partial / Incomplete analysis warning if applicable
        if not is_complete or limitations:
            with ui.column().classes("w-full p-3 bg-amber-50 border border-amber-200 rounded-lg gap-1 text-xs"):
                ui.label("Lưu ý về tính toán giải tích:").classes("font-bold text-amber-900")
                for lim in limitations:
                    ui.label(f"• {lim}").classes("text-amber-800")

        # 4. Monotonicity and Extrema Summary
        crit_pts = table_data.get("critical_points", [])
        if crit_pts:
            with ui.row().classes("items-center gap-2 flex-wrap text-xs text-slate-700 pt-1"):
                ui.label("Điểm dừng / cực trị giải tích:").classes("font-semibold text-slate-900")
                for cp in crit_pts:
                    x_val = cp.get("latex_x", str(cp.get("x", "")))
                    y_val = cp.get("latex_y", str(cp.get("y", "")))
                    ui.badge(f"({x_val}; {y_val})", color="blue-1").classes("text-blue-900 font-mono text-xs px-2 py-0.5 rounded")


def _build_variation_table_html(
    var_name: str,
    transition_pts: list[dict[str, Any]],
    intervals: list[dict[str, Any]],
) -> str:
    """Generate structured HTML for 3-row variation table matching textbook format with long SVG arrows."""
    if not intervals:
        return ""

    num_pts = len(transition_pts)
    html_parts = [
        "<div style='overflow-x: auto; width: 100%; max-width: 950px; margin: 0 auto;'>"
        "<table style='border-collapse: collapse; width: 100%; min-width: 550px; text-align: center; "
        "border: 2px solid #2563eb; background-color: #ffffff; table-layout: auto;'>"
    ]

    header_th_style = (
        "width: 70px; min-width: 60px; padding: 8px 6px; border-right: 2px solid #2563eb; "
        "color: #1e3a8a; font-size: 1.1rem; font-style: italic; background-color: #f8fafc;"
    )

    # --- ROW 1: x ---
    html_parts.append("<tr style='border-bottom: 2px solid #2563eb; height: 42px;'>")
    html_parts.append(f"<th style='{header_th_style}'>{_format_cell_math(var_name)}</th>")
    html_parts.append(f"<td style='width: 55px; min-width: 50px; padding: 4px;'>{_format_cell_math(r'-\infty')}</td>")

    for i in range(num_pts):
        pt = transition_pts[i]
        html_parts.append("<td style='padding: 4px; min-width: 100px;'></td>")  # Interval spacer
        pt_val = pt.get("val_latex", str(pt.get("val_float", "")))
        html_parts.append(f"<td style='min-width: 50px; padding: 4px;'>{_format_cell_math(pt_val)}</td>")

    # Last interval spacer and +oo
    html_parts.append("<td style='padding: 4px; min-width: 100px;'></td>")
    html_parts.append(f"<td style='width: 55px; min-width: 50px; padding: 4px;'>{_format_cell_math(r'+\infty')}</td>")
    html_parts.append("</tr>")

    # --- ROW 2: f'(x) ---
    f_prime_label = f"f'({var_name})"
    html_parts.append("<tr style='border-bottom: 2px solid #2563eb; height: 44px;'>")
    html_parts.append(f"<th style='{header_th_style}'>{_format_cell_math(f_prime_label)}</th>")
    html_parts.append("<td></td>")  # Under -oo

    for i in range(num_pts):
        sign = intervals[i].get("sign", "?") if i < len(intervals) else "?"
        sign_color = "#16a34a" if sign == "+" else ("#dc2626" if sign == "-" else "#64748b")
        html_parts.append(
            f"<td style='font-size: 1.45rem; font-weight: bold; color: {sign_color}; padding: 4px;'>{sign}</td>"
        )
        pt = transition_pts[i]
        if pt.get("type") == "pole":
            html_parts.append(
                "<td style='border-left: 2px solid #dc2626; border-right: 2px solid #dc2626; "
                "width: 10px; min-width: 10px; padding: 0; background-color: #fef2f2;'></td>"
            )
        else:
            html_parts.append(
                "<td style='font-weight: bold; color: #1e293b; font-size: 1.15rem; padding: 4px;'>0</td>"
            )

    # Last interval sign
    last_sign = intervals[-1].get("sign", "?") if intervals else "?"
    last_sign_color = "#16a34a" if last_sign == "+" else ("#dc2626" if last_sign == "-" else "#64748b")
    html_parts.append(
        f"<td style='font-size: 1.45rem; font-weight: bold; color: {last_sign_color}; padding: 4px;'>{last_sign}</td>"
    )
    html_parts.append("<td></td>")  # Under +oo
    html_parts.append("</tr>")

    # --- ROW 3: f(x) (variations with arrows) ---
    f_label = f"f({var_name})"
    html_parts.append("<tr style='height: 100px;'>")
    html_parts.append(f"<th style='{header_th_style} vertical-align: middle;'>{_format_cell_math(f_label)}</th>")

    # Col for -oo
    inter_0 = intervals[0]
    val_neg_inf = inter_0.get("start_val", r"-\infty")
    sign_0 = inter_0.get("sign", "+")
    valign_neg = "top; padding-top: 8px;" if sign_0 == "-" else ("bottom; padding-bottom: 8px;" if sign_0 == "+" else "middle;")
    html_parts.append(
        f"<td style='vertical-align: {valign_neg} padding-left: 4px; padding-right: 4px; width: 55px; min-width: 50px;'>"
        f"<div style='font-weight: 600; color: #1e3a8a;'>{_format_cell_math(val_neg_inf)}</div></td>"
    )

    def render_interval_arrow_cell(
        idx: int,
        sign: str,
        has_left_pole: bool,
        left_val: str,
        has_right_pole: bool,
        right_val: str,
    ) -> str:
        arrow_color = "#dc2626"
        cell = ["<td style='position: relative; height: 100px; min-width: 100px; padding: 0; vertical-align: middle;'>"]

        # Left limit at pole
        x1 = 12
        if has_left_pole and left_val:
            x1 = 38
            pos = "bottom: 6px; left: 4px;" if sign == "+" else "top: 6px; left: 4px;"
            cell.append(f"<div style='position: absolute; {pos} z-index: 2; font-weight: 600; color: #1e3a8a;'>{_format_cell_math(left_val)}</div>")

        # Right limit at pole
        x2 = 88
        if has_right_pole and right_val:
            x2 = 62
            pos = "top: 6px; right: 4px;" if sign == "+" else "bottom: 6px; right: 4px;"
            cell.append(f"<div style='position: absolute; {pos} z-index: 2; font-weight: 600; color: #1e3a8a;'>{_format_cell_math(right_val)}</div>")

        marker_id = f"arr-m-{idx}"
        cell.append(
            f"<svg style='position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; overflow: visible;' "
            f"viewBox='0 0 100 100' preserveAspectRatio='none'>"
            f"<defs><marker id='{marker_id}' viewBox='0 0 10 10' refX='6' refY='5' markerWidth='6' markerHeight='6' orient='auto-start-reverse'>"
            f"<path d='M 0 1.5 L 8 5 L 0 8.5 z' fill='{arrow_color}'/></marker></defs>"
        )

        if sign == "+":
            # Rising arrow: bottom-left to top-right
            cell.append(f"<line x1='{x1}' y1='78' x2='{x2}' y2='22' stroke='{arrow_color}' stroke-width='2.5' marker-end='url(#{marker_id})'/>")
        elif sign == "-":
            # Falling arrow: top-left to bottom-right
            cell.append(f"<line x1='{x1}' y1='22' x2='{x2}' y2='78' stroke='{arrow_color}' stroke-width='2.5' marker-end='url(#{marker_id})'/>")
        else:
            # Constant / flat
            cell.append(f"<line x1='{x1}' y1='50' x2='{x2}' y2='50' stroke='#2563eb' stroke-width='2' marker-end='url(#{marker_id})'/>")

        cell.append("</svg></td>")
        return "".join(cell)

    for i in range(num_pts):
        inter = intervals[i]
        sign = inter.get("sign", "+")
        has_left_pole = (i > 0 and transition_pts[i - 1].get("type") == "pole")
        left_val = inter.get("start_val", "") if has_left_pole else ""
        has_right_pole = (transition_pts[i].get("type") == "pole")
        right_val = inter.get("end_val", "") if has_right_pole else ""

        html_parts.append(render_interval_arrow_cell(i, sign, has_left_pole, left_val, has_right_pole, right_val))

        pt = transition_pts[i]
        if pt.get("type") == "pole":
            html_parts.append(
                "<td style='border-left: 2px solid #dc2626; border-right: 2px solid #dc2626; "
                "width: 10px; min-width: 10px; padding: 0; background-color: #fef2f2;'></td>"
            )
        else:
            prev_sign = intervals[i].get("sign", "+")
            next_sign = intervals[i + 1].get("sign", "+") if i + 1 < len(intervals) else "+"
            if prev_sign == "+" and next_sign == "-":
                valign = "top; padding-top: 8px;"
            elif prev_sign == "-" and next_sign == "+":
                valign = "bottom; padding-bottom: 8px;"
            else:
                valign = "middle;"

            y_val = pt.get("y_latex", str(pt.get("y_disp", "")))
            html_parts.append(
                f"<td style='vertical-align: {valign} min-width: 50px; padding: 4px;'>"
                f"<div style='font-weight: 600; color: #1e3a8a;'>{_format_cell_math(y_val)}</div></td>"
            )

    # Last interval
    last_inter = intervals[-1]
    last_sign = last_inter.get("sign", "+")
    has_left_pole = (num_pts > 0 and transition_pts[-1].get("type") == "pole")
    left_val = last_inter.get("start_val", "") if has_left_pole else ""
    html_parts.append(render_interval_arrow_cell(num_pts, last_sign, has_left_pole, left_val, False, ""))

    # Col for +oo
    val_pos_inf = last_inter.get("end_val", r"+\infty")
    valign_pos = "top; padding-top: 8px;" if last_sign == "+" else ("bottom; padding-bottom: 8px;" if last_sign == "-" else "middle;")
    html_parts.append(
        f"<td style='vertical-align: {valign_pos} padding-left: 4px; padding-right: 4px; width: 55px; min-width: 50px;'>"
        f"<div style='font-weight: 600; color: #1e3a8a;'>{_format_cell_math(val_pos_inf)}</div></td>"
    )

    html_parts.append("</tr></table></div>")
    return "".join(html_parts)

"""Matrix guidance, dimension templates, and visual syntax helper for Linear Algebra."""

from __future__ import annotations

from nicegui import ui

from math_app.domain.models import ProblemType
from math_app.presentation.components.operation_catalog import OperationDef


def render_matrix_helper_panel(
    op: OperationDef,
    expr_input: ui.input,
) -> ui.column | None:
    """Render structured syntax guidance, dimension presets, and operand templates for matrix operations."""
    if not op.is_matrix:
        return None

    pt = op.problem_type
    is_binary = pt in (
        ProblemType.MATRIX_ADD_SUB,
        ProblemType.MATRIX_MULTIPLY,
        ProblemType.MATRIX_SOLVE_SYSTEM,
    )

    with ui.column().classes("w-full gap-2 p-3.5 bg-blue-50/60 border border-blue-200 rounded-xl") as panel:
        # Guidance row
        with ui.row().classes("items-center justify-between w-full flex-wrap gap-2"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("grid_on", size="1.2rem").classes("text-blue-700")
                ui.label("HƯỚNG DẪN NHẬP DỮ LIỆU MA TRẬN:").classes(
                    "text-xs font-black text-blue-950 uppercase tracking-wider"
                )

            if is_binary:
                if pt == ProblemType.MATRIX_ADD_SUB:
                    syntax_hint = "Cú pháp: A + B hoặc A - B (ví dụ: [[1, 2], [3, 4]] + [[5, 6], [7, 8]])"
                elif pt == ProblemType.MATRIX_MULTIPLY:
                    syntax_hint = "Cú pháp: A * B (ví dụ: [[1, 2], [3, 4]] * [[5, 6], [7, 8]])"
                else:  # MATRIX_SOLVE_SYSTEM
                    syntax_hint = "Cú pháp hệ Ax = b: [[a, b], [c, d]] = [b1, b2]"
            else:
                syntax_hint = "Cú pháp: [[a, b], [c, d]] — Mỗi hàng đặt trong cặp ngoặc vuông, phân cách bằng dấu phẩy."

            ui.label(syntax_hint).classes("text-xs text-blue-900 font-medium")

        # Quick templates row
        with ui.row().classes("items-center gap-2 flex-wrap pt-1"):
            ui.label("Mẫu nhanh:").classes("text-xs font-bold text-slate-600")

            if not is_binary:
                templates = [
                    ("Đơn vị 2×2 (I₂)", "[[1, 0], [0, 1]]"),
                    ("Đơn vị 3×3 (I₃)", "[[1, 0, 0], [0, 1, 0], [0, 0, 1]]"),
                    ("Vuông 2×2", "[[2, 1], [5, 3]]"),
                    ("Vuông 3×3", "[[1, 2, 3], [0, 1, 4], [5, 6, 0]]"),
                    ("Chữ nhật 2×3", "[[1, 2, 3], [4, 5, 6]]"),
                ]
            elif pt == ProblemType.MATRIX_SOLVE_SYSTEM:
                templates = [
                    ("Hệ 2 ẩn", "[[2, 1], [1, -1]] = [5, 1]"),
                    ("Hệ 3 ẩn", "[[1, 1, 1], [0, 2, 5], [2, 5, -1]] = [6, -4, 27]"),
                ]
            else:  # ADD_SUB, MULTIPLY
                op_symbol = "+" if pt == ProblemType.MATRIX_ADD_SUB else "*"
                templates = [
                    (f"Hai ma trận 2×2 ({op_symbol})", f"[[1, 2], [3, 4]] {op_symbol} [[5, 6], [7, 8]]"),
                    (f"Hai ma trận 3×3 ({op_symbol})", f"[[1, 0, 2], [2, 1, 3], [0, 1, 1]] {op_symbol} [[2, 1, 0], [1, 3, 2], [0, 1, 1]]"),
                ]

            for lbl, tmpl in templates:
                def _apply(_: object = None, t: str = tmpl) -> None:
                    expr_input.set_value(t)

                (
                    ui.button(lbl, on_click=_apply)
                    .props(f'outline dense no-caps aria-label="Điền mẫu {lbl}"')
                    .classes("text-xs px-2.5 py-1 min-h-[32px] rounded-lg bg-white text-blue-800 border-blue-300 hover:bg-blue-100 font-mono transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500")
                )

    return panel

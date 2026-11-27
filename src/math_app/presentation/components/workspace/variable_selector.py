"""Adaptive variable selector component for MathWeave Studio."""

from __future__ import annotations

from nicegui import ui

from math_app.domain.models import ProblemType
from math_app.presentation.components.operation_catalog import OperationDef


def get_variable_pool_for_operation(op: OperationDef) -> list[str]:
    """Return the context-appropriate variable choices for a mathematical operation."""
    pt = op.problem_type
    if pt.is_ode:
        return ["t", "x"]
    if pt == ProblemType.PARTIAL_DERIVATIVE:
        return ["x", "y", "z"]
    if pt == ProblemType.SOLVE_EQUATION:
        return ["x", "y", "t"]
    if pt in (
        ProblemType.DERIVATIVE,
        ProblemType.INDEFINITE_INTEGRAL,
        ProblemType.DEFINITE_INTEGRAL,
        ProblemType.LIMIT,
        ProblemType.ARC_LENGTH,
        ProblemType.SURFACE_OF_REVOLUTION,
    ):
        return ["x", "t", "y", "u"]
    # Fallback default
    return ["x", "y", "t"]


def render_adaptive_variable_selector(
    op: OperationDef,
    var_input: ui.input,
) -> ui.row | None:
    """Render a compact, operation-specific variable selection toolbar.

    Eliminates irrelevant coordinate grids (Cylindrical/Spherical) for ordinary
    single-variable operations, providing quick, accessible chips with reactive
    styling that updates upon selection or programmatic input changes.
    """
    pool = get_variable_pool_for_operation(op)

    active_classes = "bg-blue-600 !bg-blue-600 text-white !text-white font-bold !font-bold shadow-xs"
    inactive_classes = "bg-white !bg-white text-slate-700 !text-slate-700 hover:!bg-blue-50 hover:!text-blue-700 border border-slate-300"
    base_classes = "text-xs px-2.5 py-1 min-w-[36px] min-h-[32px] rounded-lg font-mono transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500"

    with ui.row().classes("items-center gap-3 flex-wrap pt-1 min-w-0") as row:
        with ui.row().classes("items-center gap-2"):
            ui.icon("tune", size="1.1rem").classes("text-slate-400")
            label_text = "Biến khảo sát:"
            if "đạo hàm" in op.title.lower():
                label_text = "Biến lấy đạo hàm:"
            elif "tích phân" in op.title.lower() or "nguyên hàm" in op.title.lower():
                label_text = "Biến tích phân:"
            elif op.problem_type == ProblemType.SOLVE_EQUATION:
                label_text = "Ẩn số cần tìm:"
            ui.label(label_text).classes("text-xs font-bold text-slate-700 uppercase tracking-wider")

        buttons: dict[str, ui.button] = {}

        def _update_chip_styles() -> None:
            current_val = var_input.value.strip() if var_input.value else ""
            for val_str, btn in buttons.items():
                if val_str == current_val:
                    btn.classes(add=active_classes, remove=inactive_classes)
                else:
                    btn.classes(add=inactive_classes, remove=active_classes)

        with ui.row().classes("items-center gap-1.5 flex-wrap"):
            for v in pool:
                def _set_var(_: object = None, val: str = v) -> None:
                    var_input.set_value(val)

                is_active = (var_input.value == v)
                btn = (
                    ui.button(v, on_click=_set_var, color=None)
                    .props("unelevated dense no-caps")
                    .classes(f"{base_classes} {active_classes if is_active else inactive_classes}")
                )
                buttons[v] = btn

        var_input.on_value_change(_update_chip_styles)

    return row

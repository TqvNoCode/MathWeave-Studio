"""Presentation component for First-Order ODE Guided Classification & Intelligent Method Selection.

Implements UX3.6 & UX3.7.1:
- Automatic mathematical classification panel with extracted components
- Mathematical explanation of why the classification is valid
- Theoretical reference card (e.g. homogeneous counterpart for nonhomogeneous ODEs)
- Primary recommended solving method with pedagogical reasoning
- Minimalist flow: Redundant manual override and beginner recognition panels removed
"""

from __future__ import annotations

from typing import Callable
from nicegui import ui

from math_app.presentation.components.math_view import ui_math, ui_math_text
from math_app.presentation.components.shared.status_badge import status_badge
from math_app.presentation.components.workspace.ode.first_order_classifier import (
    FirstOrderClassificationResult,
)
from math_app.presentation.components.workspace.ode.ode_state import (
    ODEClassification,
    ODEOrder,
    ODEState,
)


def render_ode_guided_classification_view(
    result: FirstOrderClassificationResult,
    state: ODEState,
    on_select_classification: Callable[[ODEClassification], None] | None = None,
    on_switch_order: Callable[[ODEOrder], None] | None = None,
    on_back_to_catalog: Callable[[], None] | None = None,
) -> None:
    """Render the 4-stage guided classification & method selection experience for First-Order ODEs."""
    # -------------------------------------------------------------------------
    # Case 1: Invalid Equation or Order Mismatch
    # -------------------------------------------------------------------------
    if not result.is_valid_ode:
        if result.detected_order == 2:
            with ui.card().classes(
                "w-full p-4 md:p-5 border-2 border-amber-200 bg-gradient-to-r from-amber-50/90 to-orange-50/70 rounded-xl shadow-xs gap-3 text-amber-950 min-w-0"
            ):
                with ui.row().classes("items-center justify-between w-full flex-wrap gap-2 border-b border-amber-200/80 pb-2.5"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("swap_vertical_circle", size="1.4rem").classes("text-amber-700")
                        ui.label("Phương trình không đúng cấp").classes("text-base font-bold text-amber-950")
                    with ui.badge(color="amber-2").classes("text-amber-900 text-xs px-2.5 py-0.5 rounded-full font-medium"):
                        ui.label("Cần chuyển không gian làm việc")

                ui.label(result.error_message or "").classes("text-sm text-amber-950 font-medium leading-relaxed")

                with ui.row().classes("items-center gap-2.5 pt-2 flex-wrap"):
                    if on_switch_order:
                        ui.button(
                            "Chuyển sang PTVP cấp 2",
                            icon="arrow_forward",
                            on_click=lambda: on_switch_order(ODEOrder.SECOND_ORDER),
                        ).props("unelevated dense no-caps").classes(
                            "bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-3.5 py-2 rounded-lg shadow-xs"
                        )
                    if on_back_to_catalog:
                        ui.button(
                            "Quay lại danh mục toán học",
                            icon="menu_book",
                            on_click=on_back_to_catalog,
                        ).props("outline dense no-caps").classes(
                            "border-blue-300 text-blue-800 hover:bg-blue-50 font-semibold text-xs px-3.5 py-2 rounded-lg"
                        )
            return

        # Syntax error or other order mismatches
        with ui.card().classes(
            "w-full p-4 md:p-5 border border-rose-200 bg-rose-50/80 rounded-xl shadow-xs gap-2.5 text-rose-950 min-w-0"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.icon("error_outline", size="1.3rem").classes("text-rose-600")
                ui.label("Phương trình chưa hợp lệ").classes("text-base font-bold text-rose-950")
            ui.label(result.error_message or "").classes("text-sm text-rose-900 leading-relaxed")
            if result.order_mismatch_recommendation:
                ui.label(result.order_mismatch_recommendation).classes("text-xs text-rose-700 font-medium")
        return

    # -------------------------------------------------------------------------
    # Case 2: Valid First-Order ODE — Guided Pedagogical Presentation
    # -------------------------------------------------------------------------
    with ui.column().classes("w-full gap-4 mt-1"):

        # =====================================================================
        # STEP 2: Automatic Classification & Canonical Form
        # =====================================================================
        with ui.card().classes(
            "w-full p-4 md:p-5 border border-blue-200 bg-gradient-to-br from-blue-50/70 via-white to-slate-50/80 rounded-xl shadow-xs gap-3 min-w-0"
        ):
            with ui.row().classes("items-center justify-between w-full flex-wrap gap-2 border-b border-blue-100 pb-2.5"):
                with ui.row().classes("items-center gap-2"):
                    ui.badge("BƯỚC 2", color="primary").classes("text-xs font-bold")
                    ui.label("TỰ ĐỘNG PHÂN LOẠI TOÁN HỌC:").classes(
                        "text-xs font-bold text-slate-800 uppercase tracking-wider"
                    )
                with ui.row().classes("items-center gap-1.5 flex-wrap"):
                    status_badge(result.primary_title, variant="info")
                    for add_c in result.additional_categories:
                        status_badge(f"Đồng thời là: {add_c['title']}", variant="neutral")

            # Canonical Form Box
            with ui.row().classes("w-full items-center justify-between bg-white border border-slate-200 rounded-lg p-3 gap-3 flex-wrap"):
                with ui.column().classes("gap-1 min-w-[200px]"):
                    ui.label("Dạng chuẩn tắc tương ứng:").classes("text-xs font-semibold text-slate-500 uppercase")
                    ui_math(result.canonical_form_latex, block=False, classes="text-base md:text-lg font-bold text-slate-900")
                with ui.badge(color="blue-1").classes("text-blue-900 text-xs px-2.5 py-1 rounded-md font-mono"):
                    ui.label(f"Bậc đạo hàm: Cấp {result.detected_order}")

            # Variable and Parameter Roles
            if result.detected_parameters:
                with ui.row().classes("w-full items-center justify-between bg-blue-50/60 border border-blue-100 rounded-lg p-2.5 gap-2 flex-wrap text-xs"):
                    with ui.row().classes("items-center gap-1.5"):
                        ui.icon("tune", size="1.1rem").classes("text-blue-700")
                        ui.label("Phân vai trò ký hiệu:").classes("font-bold text-blue-950 uppercase")
                    with ui.row().classes("items-center gap-2 flex-wrap"):
                        with ui.badge(color="blue-2").classes("text-blue-900 text-xs px-2 py-0.5 rounded font-mono"):
                            ui.label(f"Biến độc lập: {result.detected_independent_var}")
                        with ui.badge(color="indigo-2").classes("text-indigo-900 text-xs px-2 py-0.5 rounded font-mono"):
                            ui.label(f"Hàm phụ thuộc: {result.detected_dependent_var}")
                        with ui.badge(color="amber-2").classes("text-amber-950 text-xs px-2 py-0.5 rounded font-mono"):
                            ui.label(f"Tham số hằng: {', '.join(result.detected_parameters)}")

            # Extracted Components Cards
            if result.is_linear:
                with ui.row().classes("w-full gap-3 flex-wrap md:flex-nowrap"):
                    with ui.card().classes("flex-1 p-3 bg-white border border-slate-200 rounded-lg min-w-[140px]"):
                        ui.label(f"Hệ số p({state.target_var}):").classes("text-xs text-slate-500 font-medium")
                        ui_math(result.p_expr_latex or "0", block=False, classes="text-sm md:text-base font-bold text-blue-800")
                    with ui.card().classes("flex-1 p-3 bg-white border border-slate-200 rounded-lg min-w-[140px]"):
                        ui.label(f"Hàm vế phải g({state.target_var}):").classes("text-xs text-slate-500 font-medium")
                        ui_math(result.g_expr_latex or "0", block=False, classes="text-sm md:text-base font-bold text-blue-800")

                # Reference Homogeneous Counterpart Card for Nonhomogeneous Equations
                if not result.is_linear_homogeneous and result.reference_homogeneous_latex:
                    with ui.card().classes(
                        "w-full p-3 bg-amber-50/70 border border-amber-200 rounded-lg gap-1.5"
                    ):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("compare_arrows", size="1.2rem").classes("text-amber-700")
                            ui.label("Đối chứng sư phạm: Phương trình thuần nhất liên kết").classes(
                                "text-xs font-bold text-amber-950 uppercase"
                            )
                        with ui.row().classes("items-center gap-3 pl-2 flex-wrap"):
                            ui_math(result.reference_homogeneous_latex, block=False, classes="text-sm font-bold text-amber-900")
                            ui.label("(Phương trình thu được khi triệt tiêu hàm tự do vế phải g(t) = 0)").classes(
                                "text-xs text-amber-800 italic"
                            )

            elif result.primary_category == "SEPARABLE" and result.is_separable:
                with ui.row().classes("w-full gap-3 flex-wrap md:flex-nowrap"):
                    with ui.card().classes("flex-1 p-3 bg-white border border-slate-200 rounded-lg min-w-[140px]"):
                        ui.label(f"Thành phần theo biến độc lập f({state.target_var}):").classes("text-xs text-slate-500 font-medium")
                        ui_math(result.f_expr_latex or "1", block=False, classes="text-sm font-bold text-slate-800")
                    with ui.card().classes("flex-1 p-3 bg-white border border-slate-200 rounded-lg min-w-[140px]"):
                        ui.label("Thành phần theo hàm số g(y):").classes("text-xs text-slate-500 font-medium")
                        ui_math(result.g_sep_latex or "1", block=False, classes="text-sm font-bold text-slate-800")

            elif result.is_exact_form:
                with ui.row().classes("w-full gap-3 flex-wrap md:flex-nowrap"):
                    with ui.card().classes("flex-1 p-3 bg-white border border-slate-200 rounded-lg min-w-[140px]"):
                        ui.label(f"Hàm M({state.target_var}, y):").classes("text-xs text-slate-500 font-medium")
                        ui_math(result.M_expr_latex or "0", block=False, classes="text-sm font-mono text-slate-800")
                    with ui.card().classes("flex-1 p-3 bg-white border border-slate-200 rounded-lg min-w-[140px]"):
                        ui.label(f"Hàm N({state.target_var}, y):").classes("text-xs text-slate-500 font-medium")
                        ui_math(result.N_expr_latex or "0", block=False, classes="text-sm font-mono text-slate-800")

                with ui.row().classes("w-full gap-3 flex-wrap md:flex-nowrap"):
                    with ui.card().classes("flex-1 p-3 bg-white border border-slate-200 rounded-lg min-w-[140px]"):
                        ui.label("Đạo hàm riêng ∂M/∂y:").classes("text-xs text-slate-500 font-medium")
                        ui_math(result.dM_dy_latex or "0", block=False, classes="text-sm font-bold text-slate-800")
                    with ui.card().classes("flex-1 p-3 bg-white border border-slate-200 rounded-lg min-w-[140px]"):
                        ui.label(f"Đạo hàm riêng ∂N/∂{state.target_var}:").classes("text-xs text-slate-500 font-medium")
                        ui_math(result.dN_dt_latex or "0", block=False, classes="text-sm font-bold text-slate-800")

            elif result.is_separable:
                with ui.row().classes("w-full gap-3 flex-wrap md:flex-nowrap"):
                    with ui.card().classes("flex-1 p-3 bg-white border border-slate-200 rounded-lg min-w-[140px]"):
                        ui.label(f"Thành phần theo biến độc lập f({state.target_var}):").classes("text-xs text-slate-500 font-medium")
                        ui_math(result.f_expr_latex or "1", block=False, classes="text-sm font-bold text-slate-800")
                    with ui.card().classes("flex-1 p-3 bg-white border border-slate-200 rounded-lg min-w-[140px]"):
                        ui.label("Thành phần theo hàm số g(y):").classes("text-xs text-slate-500 font-medium")
                        ui_math(result.g_sep_latex or "1", block=False, classes="text-sm font-bold text-slate-800")

        # =====================================================================
        # STEP 3: Explanation of Why the Classification is Valid
        # =====================================================================
        with ui.card().classes("w-full p-4 md:p-5 border border-slate-200 bg-white rounded-xl shadow-xs gap-2.5 min-w-0"):
            with ui.row().classes("items-center gap-2 border-b border-slate-100 pb-2"):
                ui.badge("BƯỚC 3", color="primary").classes("text-xs font-bold")
                ui.label("CƠ SỞ VÀ LÝ LẼ PHÂN LOẠI TOÁN HỌC:").classes(
                    "text-xs font-bold text-slate-800 uppercase tracking-wider"
                )

            with ui.column().classes("gap-2 w-full pt-1"):
                for point in result.explanation_points:
                    with ui.row().classes("items-start gap-2"):
                        ui.icon("check_circle", size="1.1rem").classes("text-emerald-600 mt-0.5 shrink-0")
                        ui_math_text(point, classes="text-xs md:text-sm text-slate-700 leading-relaxed")

        # =====================================================================
        # STEP 4: Recommended Solving Method
        # =====================================================================
        with ui.card().classes(
            "w-full p-4 md:p-5 border-2 border-blue-200 bg-gradient-to-r from-blue-50/90 via-sky-50/60 to-white rounded-xl shadow-xs gap-3 min-w-0"
        ):
            with ui.row().classes("items-center justify-between w-full flex-wrap gap-2 border-b border-blue-200/80 pb-2.5"):
                with ui.row().classes("items-center gap-2"):
                    ui.badge("BƯỚC 4", color="primary").classes("text-xs font-bold")
                    ui.label("PHƯƠNG PHÁP GIẢI KHUYẾN NGHỊ:").classes(
                        "text-xs font-bold text-blue-950 uppercase tracking-wider"
                    )
                with ui.badge(color="blue-2").classes("text-blue-900 text-xs px-2.5 py-0.5 rounded-full font-bold"):
                    ui.label("TỐI ƯU SƯ PHẠM")

            with ui.column().classes("gap-1.5 w-full"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("stars", size="1.3rem").classes("text-blue-600")
                    ui.label(result.recommended_method_title).classes("text-sm md:text-base font-bold text-blue-900")
                ui_math_text(result.recommended_method_reason, classes="text-xs md:text-sm text-slate-700 leading-relaxed pl-7")

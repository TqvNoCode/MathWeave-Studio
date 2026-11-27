"""Central ODE workspace component unifying First-Order and Second-Order ODE workflows."""

from __future__ import annotations

import asyncio
from typing import Any, Callable
from nicegui import ui

from math_app.application.dtos import SolutionResponse
from math_app.application.use_cases.solve_problem import SolveProblemUseCase
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus
from math_app.presentation.components.math_view import ui_math, ui_math_text
from math_app.presentation.components.operation_catalog import (
    OperationDef,
    get_operation_by_type,
    get_second_order_examples,
)
from math_app.presentation.components.shared.primary_button import primary_button
from math_app.presentation.components.shared.section_card import section_card
from math_app.presentation.components.shared.status_badge import status_badge
from math_app.presentation.components.solution_view import render_solution_view
from math_app.presentation.components.workspace.ode.first_order_classifier import (
    classify_first_order_ode,
)
from math_app.presentation.components.workspace.ode.ode_classification_selector import (
    render_ode_classification_selector,
)
from math_app.presentation.components.workspace.ode.ode_guided_classification_view import (
    render_ode_guided_classification_view,
)
from math_app.presentation.components.workspace.ode.ode_method_selector import (
    render_ode_method_selector,
)
from math_app.presentation.components.workspace.ode.ode_mode_selector import (
    render_ode_mode_selector,
)
from math_app.presentation.components.workspace.ode.ode_order_selector import (
    render_ode_order_selector,
)
from math_app.presentation.components.workspace.ode.ode_state import (
    DEFAULT_CONFIGS,
    ODEClassification,
    ODEMode,
    ODEMethodPreference,
    ODEOrder,
    ODEState,
    split_first_order_equation_clauses,
    split_second_order_equation_clauses,
)
from math_app.presentation.components.workspace.variable_selector import (
    render_adaptive_variable_selector,
)


def render_ode_validation_card(
    err_msg: str,
    state: ODEState,
    on_switch_order: Callable[[ODEOrder], None] | None = None,
    on_back_to_catalog: Callable[[], None] | None = None,
) -> None:
    """Render a context-aware Academic Blue validation card for ODE input or order mismatches."""
    err_lower = err_msg.lower()
    is_nonlinearity = "phi tuyến" in err_lower or "nonlinear" in err_lower
    is_cauchy_ic_error = any(
        term in err_lower
        for term in (
            "điều kiện ban đầu",
            "điều kiện đạo hàm ban đầu",
            "không cùng điểm khởi đầu",
            "base point mismatch",
            "xung đột điều kiện",
            "thiếu điều kiện",
            "bài toán cauchy",
            "bài toán giá trị ban đầu",
        )
    )
    is_order_mismatch = (
        any(
            term in err_lower
            for term in (
                "không đúng cấp",
                "không chứa đạo hàm cấp",
                "phương trình vi phân cấp cao",
            )
        )
        and not is_nonlinearity
        and not is_cauchy_ic_error
    )
    is_syntax_error = any(term in err_lower for term in ("ngoặc", "syntax", "cú pháp", "toán tử", "không khớp"))

    if is_order_mismatch and not is_syntax_error:
        with ui.card().classes(
            "w-full p-4 md:p-5 border-2 border-amber-200 bg-gradient-to-r from-amber-50/90 to-orange-50/70 rounded-xl shadow-xs gap-3 text-amber-950 min-w-0"
        ):
            with ui.row().classes("items-center justify-between w-full flex-wrap gap-2 border-b border-amber-200/80 pb-2.5"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("swap_vertical_circle", size="1.4rem").classes("text-amber-700")
                    ui.label("Phương trình không đúng cấp").classes("text-base font-bold text-amber-950")
                with ui.badge(color="amber-2").classes("text-amber-900 text-xs px-2.5 py-0.5 rounded-full font-medium"):
                    ui.label("Cần chuyển không gian làm việc")

            clean_msg = err_msg.replace("Phương trình không đúng cấp: ", "").strip()
            ui.label(clean_msg).classes("text-sm text-amber-950 font-medium leading-relaxed")

            with ui.row().classes("items-center gap-2.5 pt-2 flex-wrap"):
                if state.order == ODEOrder.FIRST_ORDER and ("cấp 2" in err_msg or "cấp hai" in err_msg):
                    if on_switch_order:
                        ui.button(
                            "Chuyển sang PTVP cấp 2",
                            icon="arrow_forward",
                            on_click=lambda: on_switch_order(ODEOrder.SECOND_ORDER),
                        ).props("unelevated dense no-caps").classes(
                            "bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-3.5 py-2 rounded-lg shadow-xs"
                        )
                elif state.order == ODEOrder.SECOND_ORDER and ("cấp 1" in err_msg or "cấp một" in err_msg):
                    if on_switch_order:
                        ui.button(
                            "Chuyển sang PTVP cấp 1",
                            icon="arrow_forward",
                            on_click=lambda: on_switch_order(ODEOrder.FIRST_ORDER),
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
    elif is_nonlinearity:
        with ui.card().classes(
            "w-full p-4 md:p-5 border-2 border-indigo-200 bg-gradient-to-r from-indigo-50/90 via-sky-50/70 to-white rounded-xl shadow-xs gap-3 text-indigo-950 min-w-0"
        ):
            with ui.row().classes("items-center justify-between w-full flex-wrap gap-2 border-b border-indigo-200/80 pb-2.5"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("functions", size="1.4rem").classes("text-indigo-700")
                    ui.label("Phương trình vi phân phi tuyến tính cấp 1").classes("text-base font-bold text-indigo-950")
                with ui.badge(color="indigo-2").classes("text-indigo-900 text-xs px-2.5 py-0.5 rounded-full font-medium"):
                    ui.label("Giới hạn thuật toán giải")

            ui.label(err_msg).classes("text-sm text-indigo-950 font-medium leading-relaxed")
            if on_back_to_catalog:
                with ui.row().classes("items-center gap-2.5 pt-2 flex-wrap"):
                    ui.button(
                        "Quay lại danh mục toán học",
                        icon="menu_book",
                        on_click=on_back_to_catalog,
                    ).props("outline dense no-caps").classes(
                        "border-indigo-300 text-indigo-800 hover:bg-indigo-50 font-semibold text-xs px-3.5 py-2 rounded-lg"
                    )
    elif is_cauchy_ic_error:
        is_base_mismatch = any(
            t in err_lower for t in ("không cùng điểm khởi đầu", "cùng một điểm", "base point mismatch")
        )
        is_missing_ic = any(
            t in err_lower for t in ("thiếu điều kiện", "yêu cầu cung cấp đầy đủ", "không hoàn chỉnh")
        )
        if is_base_mismatch:
            ic_title = "Điểm ban đầu Cauchy không nhất quán"
            ic_hint = "Cả hai điều kiện y(t₀) = y₀ và y'(t₀) = v₀ phải được cho tại cùng một điểm khởi đầu t₀."
        elif is_missing_ic:
            ic_title = "Thiếu điều kiện ban đầu Cauchy (IVP)"
            ic_hint = "Bài toán Cauchy cấp 2 yêu cầu cung cấp đầy đủ cả hai điều kiện y(t₀) = y₀ và y'(t₀) = v₀."
        else:
            ic_title = "Điều kiện ban đầu Cauchy chưa hợp lệ"
            ic_hint = "Vui lòng kiểm tra lại cú pháp và giá trị thực hữu hạn của các điều kiện ban đầu."

        with ui.card().classes(
            "w-full p-4 md:p-5 border border-rose-200 bg-rose-50/80 rounded-xl shadow-xs gap-2.5 text-rose-950 min-w-0"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.icon("rule", size="1.3rem").classes("text-rose-600")
                ui.label(ic_title).classes("text-base font-bold text-rose-950")
            ui.label(err_msg).classes("text-sm text-rose-900 leading-relaxed")
            ui.label(ic_hint).classes("text-xs text-rose-700 italic")
    else:
        with ui.card().classes(
            "w-full p-4 md:p-5 border border-rose-200 bg-rose-50/80 rounded-xl shadow-xs gap-2.5 text-rose-950 min-w-0"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.icon("error_outline", size="1.3rem").classes("text-rose-600")
                ui.label("Dữ liệu đầu vào chưa hợp lệ").classes("text-base font-bold text-rose-950")
            ui.label(err_msg).classes("text-sm text-rose-900 leading-relaxed")
            ui.label("Vui lòng kiểm tra lại tính đóng mở của các dấu ngoặc hoặc các toán tử toán học.").classes(
                "text-xs text-rose-700 italic"
            )


def render_ode_workspace(
    current_op: OperationDef,
    use_case: SolveProblemUseCase,
    on_operation_switch: Callable[[OperationDef], None] | None = None,
    on_back_to_catalog: Callable[[], None] | None = None,
    initial_eq: str | None = None,
    initial_ic: str | None = None,
    auto_solve: bool = False,
) -> None:
    """Render unified Academic Blue workspace for all Differential Equations operations."""
    # Initialize state from incoming OperationDef
    state = ODEState.from_operation(current_op)
    if initial_eq is not None:
        state = state.with_equation(initial_eq)
    if initial_ic is not None:
        state = state.with_mode(ODEMode.CAUCHY_IVP).with_initial_condition(initial_ic)
    is_submitting = False
    is_manual_override = False

    with section_card("p-5 md:p-6 gap-5"):
        # Interactive ODE Container
        interactive_container = ui.column().classes("w-full gap-4")

        def render_content() -> None:
            nonlocal state, is_manual_override
            interactive_container.clear()
            ic_input_ref: list[Any] = [None]

            # Dynamic Operation Identity & Header (F3)
            active_op = get_operation_by_type(state.problem_type) or current_op

            with interactive_container:
                # Section A: Dynamic Header & Operation Identity
                with ui.row().classes("items-center justify-between w-full pb-3 border-b border-slate-100 flex-wrap gap-2"):
                    with ui.row().classes("items-center gap-3"):
                        if active_op.math_icon:
                            with ui.row().classes(
                                "px-3 py-1.5 min-w-[3rem] rounded-lg bg-blue-50 text-blue-800 items-center justify-center overflow-visible shadow-xs"
                            ):
                                ui_math(
                                    active_op.math_icon,
                                    block=False,
                                    classes="math-icon text-base font-bold select-none pointer-events-none",
                                    is_icon=True,
                                )
                        else:
                            ui.icon(active_op.icon or "functions", size="1.4rem").classes("text-blue-600")

                        with ui.column().classes("gap-0"):
                            ui.label(active_op.title).classes("text-base md:text-lg font-bold text-slate-900")
                            ui.label(active_op.description).classes("text-xs text-slate-500 line-clamp-1")

                    status_badge(state.order.display_label, variant="info")

                # Hidden order selector preserving programmatic compatibility while eliminating visual duplication
                with ui.column().classes("hidden"):
                    def handle_order_change(new_order: ODEOrder) -> None:
                        nonlocal state, is_manual_override
                        state = state.with_order(new_order)
                        results_container.clear()
                        render_content()

                    render_ode_order_selector(state.order, handle_order_change)

                def handle_classification_change(new_cls: ODEClassification) -> None:
                    nonlocal state, is_manual_override
                    is_manual_override = True
                    state = state.with_classification(new_cls)
                    results_container.clear()
                    render_content()

                # =============================================================
                # BRANCH A: Second-Order ODE Workflow (Preserved 100%)
                # =============================================================
                if state.order == ODEOrder.SECOND_ORDER:
                    # 1. Classification Selection (Step 1)
                    render_ode_classification_selector(state.order, state.classification, handle_classification_change)

                    # 2. Equation & Variable Inputs (Step 2)
                    with ui.column().classes("w-full gap-3 mt-1"):
                        with ui.row().classes("items-center gap-2"):
                            ui.badge("BƯỚC 2", color="primary").classes("text-xs font-bold")
                            ui.label("NHẬP PHƯƠNG TRÌNH & BIẾN SỐ:").classes(
                                "text-xs font-bold text-slate-700 uppercase tracking-wider"
                            )

                        with ui.row().classes("w-full items-center gap-3 flex-wrap md:flex-nowrap"):
                            if state.classification == ODEClassification.WRONSKIAN:
                                input_label = "Hai hàm số y1, y2 (phân tách bởi dấu phẩy)"
                                input_ph = "Ví dụ: cos(t), sin(t) hoặc exp(t), t*exp(t)"
                            elif state.classification == ODEClassification.REDUCTION_OF_ORDER:
                                input_label = "Phương trình vi phân cấp 2 (ví dụ: 2*t^2*y'' + 3*t*y' - y = 0)"
                                input_ph = "2*t^2*y'' + 3*t*y' - y = 0"
                            else:
                                input_label = f"Phương trình ({state.classification.math_subtitle_for_var(state.target_var)})"
                                input_ph = state.equation

                            eq_input = ui.input(
                                label=input_label,
                                placeholder=input_ph,
                                value=state.equation,
                            ).classes("flex-1 text-base font-mono min-w-[280px]")

                            def handle_eq_change(e: Any) -> None:
                                nonlocal state
                                state = state.with_equation(e.value or "")

                            eq_input.on_value_change(handle_eq_change)

                            var_input = ui.input(
                                label="Biến số độc lập",
                                value=state.target_var,
                            ).classes("w-36 text-base font-mono")

                            def handle_var_change(e: Any) -> None:
                                nonlocal state
                                state = state.with_target_var(e.value or "t")

                            var_input.on_value_change(handle_var_change)

                            # Adaptive Variable Selector Chips
                            render_adaptive_variable_selector(active_op, var_input)

                        # Specialized Known Solution input for Reduction of Order
                        if state.classification == ODEClassification.REDUCTION_OF_ORDER:
                            with ui.row().classes("w-full items-center gap-3"):
                                y1_input = ui.input(
                                    label="Nghiệm đã biết y₁(t) (tùy chọn nếu đã viết trong phương trình)",
                                    placeholder="Ví dụ: 1/t hoặc exp(t)",
                                    value=state.known_solution,
                                ).classes("w-full text-base font-mono")

                                def handle_known_sol_change(e: Any) -> None:
                                    nonlocal state
                                    state = state.with_known_solution(e.value or "")

                                y1_input.on_value_change(handle_known_sol_change)

                    # 4. Problem Mode Selection (Step 4: General vs Cauchy IVP)
                    def handle_mode_change(new_mode: ODEMode) -> None:
                        nonlocal state
                        state = state.with_mode(new_mode)
                        results_container.clear()
                        render_content()

                    def handle_ic_change(new_ic: str) -> None:
                        nonlocal state
                        state = state.with_initial_condition(new_ic)

                    render_ode_mode_selector(
                        state.order,
                        state.classification,
                        state.mode,
                        state.initial_condition,
                        handle_mode_change,
                        handle_ic_change,
                        on_ic_input_created=lambda inp: ic_input_ref.__setitem__(0, inp),
                    )

                    # 5. Method Selection (Step 5: Nonhomogeneous Second-Order)
                    def handle_method_change(new_pref: ODEMethodPreference) -> None:
                        nonlocal state
                        state = state.with_method_preference(new_pref)

                    render_ode_method_selector(
                        state.order,
                        state.classification,
                        state.method_preference,
                        handle_method_change,
                    )

                    # 6. Example Chips
                    if state.classification in {
                        ODEClassification.SECOND_ORDER_HOMOGENEOUS,
                        ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
                    }:
                        cat_str = "HOMOGENEOUS" if state.classification == ODEClassification.SECOND_ORDER_HOMOGENEOUS else "NONHOMOGENEOUS"
                        mode_str = "CAUCHY_IVP" if state.mode == ODEMode.CAUCHY_IVP else "GENERAL"
                        ex_list = get_second_order_examples(cat_str, mode_str)
                    else:
                        ex_list = DEFAULT_CONFIGS.get(state.classification, {}).get("examples", ())

                    if ex_list:
                        with ui.row().classes("items-center gap-2 pt-1 flex-wrap"):
                            ui.label("Ví dụ mẫu:").classes("text-xs text-slate-500 font-semibold")
                            for label, val in ex_list:
                                def make_so_example_callback(example_val: str) -> Callable[[], None]:
                                    def _apply() -> None:
                                        nonlocal state
                                        clean_e, y_ic_ex, yp_ic_ex, _, _ = split_second_order_equation_clauses(example_val)
                                        if state.mode == ODEMode.CAUCHY_IVP and y_ic_ex and yp_ic_ex:
                                            ic_comb = f"{y_ic_ex}, {yp_ic_ex}"
                                            state = state.with_equation(clean_e).with_initial_condition(ic_comb)
                                            eq_input.set_value(clean_e)
                                            if ic_input_ref[0] is not None:
                                                ic_input_ref[0].set_value(ic_comb)
                                        else:
                                            has_split_support = state.classification in {
                                                ODEClassification.SECOND_ORDER_HOMOGENEOUS,
                                                ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
                                                ODEClassification.EULER_CAUCHY,
                                            }
                                            target_eq = clean_e if (state.mode == ODEMode.GENERAL and has_split_support) else example_val
                                            state = state.with_equation(target_eq)
                                            if state.mode == ODEMode.GENERAL:
                                                state = state.with_initial_condition("")
                                                if ic_input_ref[0] is not None:
                                                    ic_input_ref[0].set_value("")
                                            eq_input.set_value(target_eq)
                                        results_container.clear()
                                    return _apply

                                ui.chip(
                                    label,
                                    on_click=make_so_example_callback(val),
                                ).classes(
                                    "cursor-pointer hover:bg-blue-100 text-xs px-2.5 py-0.5 rounded-full font-mono bg-slate-100 border border-slate-200 text-slate-800 transition-colors"
                                )

                # =============================================================
                # BRANCH B: First-Order Guided Classification Workflow (UX3.6)
                # =============================================================
                else:
                    # STEP 1: Equation & Variable Inputs
                    with ui.column().classes("w-full gap-3 mt-1"):
                        with ui.row().classes("items-center gap-2"):
                            ui.badge("BƯỚC 1", color="primary").classes("text-xs font-bold")
                            ui.label("NHẬP PHƯƠNG TRÌNH & BIẾN SỐ:").classes(
                                "text-xs font-bold text-slate-700 uppercase tracking-wider"
                            )

                        with ui.row().classes("w-full items-center gap-3 flex-wrap md:flex-nowrap"):
                            eq_input = ui.input(
                                label=f"Phương trình ({state.classification.math_subtitle_for_var(state.target_var)})",
                                placeholder=state.equation,
                                value=state.equation,
                            ).classes("flex-1 text-base font-mono min-w-[280px]")

                            var_input = ui.input(
                                label="Biến số độc lập",
                                value=state.target_var,
                            ).classes("w-36 text-base font-mono")

                            # Adaptive Variable Selector Chips
                            render_adaptive_variable_selector(active_op, var_input)

                        # Problem Mode Selection (General vs Cauchy IVP)
                        def handle_fo_mode_change(new_mode: ODEMode) -> None:
                            nonlocal state
                            state = state.with_mode(new_mode)
                            results_container.clear()
                            render_content()

                        def handle_fo_ic_change(new_ic: str) -> None:
                            nonlocal state
                            state = state.with_initial_condition(new_ic)

                        render_ode_mode_selector(
                            state.order,
                            state.classification,
                            state.mode,
                            state.initial_condition,
                            handle_fo_mode_change,
                            handle_fo_ic_change,
                            on_ic_input_created=lambda inp: ic_input_ref.__setitem__(0, inp),
                        )

                        # Example Chips for First-Order
                        ex_list = DEFAULT_CONFIGS.get(state.classification, {}).get("examples", ())
                        if ex_list:
                            with ui.row().classes("items-center gap-2 pt-1 flex-wrap"):
                                ui.label("Ví dụ mẫu:").classes("text-xs text-slate-500 font-semibold")
                                for label, val in ex_list:
                                    def make_fo_example_callback(example_val: str) -> Callable[[], None]:
                                        def _apply() -> None:
                                            nonlocal state
                                            clean_e, inline_ic, _ = split_first_order_equation_clauses(example_val)
                                            if state.mode == ODEMode.CAUCHY_IVP and inline_ic:
                                                state = state.with_equation(clean_e).with_initial_condition(inline_ic)
                                                eq_input.set_value(clean_e)
                                                if ic_input_ref[0] is not None:
                                                    ic_input_ref[0].set_value(inline_ic)
                                            else:
                                                target_eq = clean_e if state.mode == ODEMode.GENERAL else example_val
                                                state = state.with_equation(target_eq)
                                                if state.mode == ODEMode.GENERAL:
                                                    state = state.with_initial_condition("")
                                                    if ic_input_ref[0] is not None:
                                                        ic_input_ref[0].set_value("")
                                                eq_input.set_value(target_eq)
                                            results_container.clear()
                                            update_guided_classification_panel()
                                        return _apply

                                    ui.chip(
                                        label,
                                        on_click=make_fo_example_callback(val),
                                    ).classes(
                                        "cursor-pointer hover:bg-blue-100 text-xs px-2.5 py-0.5 rounded-full font-mono bg-slate-100 border border-slate-200 text-slate-800 transition-colors"
                                    )

                    # Dynamic Container for Guided Classification Steps 2, 3, 4
                    guided_container = ui.column().classes("w-full")

                    def handle_fo_classification_change(new_cls: ODEClassification) -> None:
                        nonlocal state, is_manual_override
                        is_manual_override = True
                        state = state.with_classification(new_cls, preserve_equation=True)
                        results_container.clear()
                        render_content()

                    def update_guided_classification_panel() -> None:
                        guided_container.clear()
                        with guided_container:
                            clf_res = classify_first_order_ode(state.equation, target_var=state.target_var)

                            # Module consistency sync banner
                            if clf_res.is_valid_ode and clf_res.target_problem_type and clf_res.target_problem_type != state.problem_type:
                                pt_to_cls_map = {
                                    ProblemType.ODE_FIRST_ORDER_LINEAR: (ODEClassification.FIRST_ORDER_LINEAR, "Tuyến tính cấp 1"),
                                    ProblemType.ODE_SEPARABLE: (ODEClassification.SEPARABLE, "Tách biến"),
                                    ProblemType.ODE_EXACT: (ODEClassification.EXACT, "Vi phân toàn phần"),
                                    ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS: (ODEClassification.FIRST_ORDER_HOMOGENEOUS, "Thuần nhất cấp 1"),
                                    ProblemType.ODE_INTEGRATING_FACTOR: (ODEClassification.INTEGRATING_FACTOR, "Thừa số tích phân"),
                                }
                                if clf_res.target_problem_type in pt_to_cls_map:
                                    detected_cls, detected_name = pt_to_cls_map[clf_res.target_problem_type]
                                    with ui.card().classes(
                                        "w-full p-3 md:p-3.5 border border-amber-300 bg-amber-50/90 rounded-xl shadow-xs gap-2 min-w-0 mb-1"
                                    ):
                                        with ui.row().classes("items-center justify-between w-full flex-wrap gap-2"):
                                            with ui.row().classes("items-center gap-2"):
                                                ui.icon("sync_problem", size="1.25rem").classes("text-amber-700")
                                                ui_math_text(
                                                    f"Phương trình vừa nhập thuộc dạng **{detected_name}**, khác với danh mục đang mở (**{state.classification.display_label}**).",
                                                    classes="text-xs md:text-sm font-semibold text-amber-950",
                                                )
                                            ui.button(
                                                f"Đồng bộ sang {detected_name}",
                                                icon="sync",
                                                on_click=lambda dc=detected_cls: handle_fo_classification_change(dc),
                                            ).props("unelevated dense no-caps").classes(
                                                "bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-3.5 py-1.5 rounded-lg shadow-xs"
                                            )

                            render_ode_guided_classification_view(
                                clf_res,
                                state,
                                on_select_classification=handle_fo_classification_change,
                                on_switch_order=handle_switch_order,
                                on_back_to_catalog=on_back_to_catalog,
                            )

                    def handle_fo_eq_change(e: Any) -> None:
                        nonlocal state
                        state = state.with_equation(e.value or "")
                        update_guided_classification_panel()

                    def handle_fo_var_change(e: Any) -> None:
                        nonlocal state
                        new_var = e.value or "t"
                        state = state.with_target_var(new_var)
                        eq_input._props["label"] = f"Phương trình ({state.classification.math_subtitle_for_var(new_var)})"
                        eq_input.update()
                        update_guided_classification_panel()

                    eq_input.on_value_change(handle_fo_eq_change)
                    var_input.on_value_change(handle_fo_var_change)

                    # Initial rendering of guided classification panel
                    update_guided_classification_panel()

                # 7. Action Row: Reset & Solve (Shared across all ODEs)
                with ui.row().classes("w-full items-center justify-between pt-3 border-t border-slate-100 flex-wrap gap-2"):
                    def handle_reset() -> None:
                        nonlocal state, is_manual_override
                        is_manual_override = False
                        state = state.reset()
                        results_container.clear()
                        render_content()

                    ui.button("Nhập lại", icon="refresh", on_click=handle_reset).props("flat dense no-caps").classes(
                        "text-xs text-slate-500 font-semibold hover:text-slate-800"
                    )

                    solve_btn = primary_button(
                        text="GIẢI PHƯƠNG TRÌNH",
                        icon="calculate",
                    )
                    solve_btn.on_click(handle_submit)

                    # Enter key submits from equation and variable inputs
                    eq_input.on("keydown.enter", handle_submit)
                    var_input.on("keydown.enter", handle_submit)

        def handle_switch_order(new_order: ODEOrder) -> None:
            nonlocal state
            state = state.with_order(new_order, preserve_equation=True)
            results_container.clear()
            render_content()

        async def handle_submit() -> None:
            nonlocal is_submitting, state
            if is_submitting:
                return
            is_submitting = True
            try:
                results_container.clear()

                # Auto-align First-Order classification to detected category unless manual override was chosen
                if state.order == ODEOrder.FIRST_ORDER and not is_manual_override:
                    clf_check = classify_first_order_ode(state.equation, state.target_var)
                    if clf_check.is_valid_ode:
                        current_is_valid = False
                        if state.classification == ODEClassification.FIRST_ORDER_LINEAR and clf_check.is_linear:
                            current_is_valid = True
                        elif state.classification == ODEClassification.SEPARABLE and clf_check.is_separable:
                            current_is_valid = True
                        elif state.classification == ODEClassification.EXACT and clf_check.is_exact:
                            current_is_valid = True
                        elif state.classification == ODEClassification.FIRST_ORDER_HOMOGENEOUS and clf_check.is_classical_homogeneous:
                            current_is_valid = True
                        elif state.classification == ODEClassification.INTEGRATING_FACTOR and (clf_check.is_linear or clf_check.is_exact_form):
                            current_is_valid = True

                        if not current_is_valid:
                            pt_to_cls = {
                                ProblemType.ODE_FIRST_ORDER_LINEAR: ODEClassification.FIRST_ORDER_LINEAR,
                                ProblemType.ODE_SEPARABLE: ODEClassification.SEPARABLE,
                                ProblemType.ODE_EXACT: ODEClassification.EXACT,
                                ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS: ODEClassification.FIRST_ORDER_HOMOGENEOUS,
                                ProblemType.ODE_INTEGRATING_FACTOR: ODEClassification.INTEGRATING_FACTOR,
                            }
                            if clf_check.target_problem_type in pt_to_cls:
                                state = state.with_classification(pt_to_cls[clf_check.target_problem_type])

                try:
                    req = state.build_problem_request()
                except InvalidInputError as err:
                    with results_container:
                        render_ode_validation_card(
                            err_msg=str(err),
                            state=state,
                            on_switch_order=handle_switch_order,
                            on_back_to_catalog=on_back_to_catalog,
                        )
                    return

                # Loading indicator
                with results_container:
                    with ui.card().classes("w-full p-6 border border-slate-200 bg-white rounded-xl shadow-xs text-center items-center justify-center"):
                        ui.spinner("dots", size="2.5rem", color="primary")
                        ui.label("Đang giải phương trình vi phân và thực hiện kiểm định độc lập...").classes(
                            "text-sm font-medium text-slate-600 mt-2"
                        )

                try:
                    resp: SolutionResponse = await asyncio.to_thread(use_case.execute, req, 8.0)
                except Exception as exc:
                    results_container.clear()
                    with results_container:
                        with ui.card().classes("w-full p-4 border border-red-200 bg-red-50 text-red-900 rounded-xl"):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("error", color="negative")
                                ui.label(f"Lỗi thực thi hệ thống: {exc}").classes("text-sm font-semibold")
                    return

                results_container.clear()
                if resp.status == SolutionStatus.INVALID_INPUT:
                    err_text = " ".join(resp.warnings) if resp.warnings else "Dữ liệu đầu vào chưa hợp lệ."
                    with results_container:
                        render_ode_validation_card(
                            err_msg=err_text,
                            state=state,
                            on_switch_order=handle_switch_order,
                            on_back_to_catalog=on_back_to_catalog,
                        )
                    return

                resolved_op = get_operation_by_type(req.problem_type)
                with results_container:
                    render_solution_view(resp, resolved_op, req.target_variable, req.parameters)
            finally:
                is_submitting = False

        # Results & Analysis Container
        results_container = ui.column().classes("w-full gap-5")

        # Initial render of ODE workspace content
        render_content()

        if auto_solve:
            ui.timer(0.2, handle_submit, once=True)

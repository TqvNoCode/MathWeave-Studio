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
from math_app.presentation.components.shared import (
    get_primary_action_spec,
    primary_button,
    render_example_chips,
    render_feedback_card,
    render_loading_card,
    render_workspace_header,
    section_card,
    status_badge,
)
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
from math_app.presentation.components.workspace.ode.second_order_classifier import (
    classify_second_order_ode,
)
from math_app.presentation.components.workspace.variable_selector import (
    render_adaptive_variable_selector,
)
from math_app.presentation.design_system.tokens import INTERACTION


def detect_second_order_classification(
    raw_equation: str,
    target_var: str = "t",
) -> tuple[ODEClassification | str, str] | None:
    """Detect whether a typed equation belongs to Order 1 or a specific Second-Order ODE family.

    Reuses ``second_order_classifier`` (backed by read-only ``ode_parser``) conservatively;
    returns ``None`` when the input is incomplete, ambiguous, or unsupported without raising.
    """
    summary = classify_second_order_ode(raw_equation, target_var=target_var)
    if summary.status == "ORDER_1_MISMATCH":
        return ("ORDER_1_MISMATCH", summary.badge_label)
    if summary.status == "DETECTED" and summary.detected_classification is not None:
        return (summary.detected_classification, summary.badge_label)
    return None


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
    on_title_change: Callable[[str], None] | None = None,
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
    is_override_panel_open = False

    def _so_input_meta(st: ODEState) -> tuple[str, str]:
        if st.classification == ODEClassification.WRONSKIAN:
            return (
                "Hai hàm số y1, y2 (phân tách bởi dấu phẩy)",
                "Ví dụ: cos(t), sin(t) hoặc exp(t), t*exp(t)",
            )
        if st.classification == ODEClassification.REDUCTION_OF_ORDER:
            return (
                "Phương trình vi phân cấp 2 (ví dụ: 2*t^2*y'' + 3*t*y' - y = 0)",
                "2*t^2*y'' + 3*t*y' - y = 0",
            )
        return (
            f"Phương trình ({st.classification.math_subtitle_for_var(st.target_var)})",
            st.equation,
        )

    with section_card("p-4 sm:p-5 md:p-6 gap-5 min-w-0"):
        # Interactive ODE Container
        interactive_container = ui.column().classes("w-full gap-4 min-w-0")
        solve_btn_ref: list[Any] = [None]

        def render_content() -> None:
            nonlocal state, is_manual_override, is_override_panel_open
            interactive_container.clear()
            ic_input_ref: list[Any] = [None]

            with interactive_container:
                # Section A: Dynamic Header & Operation Identity (updatable in-place without destroying eq_input)
                header_container = ui.column().classes("w-full min-w-0")

                def render_header() -> OperationDef:
                    active = get_operation_by_type(state.problem_type) or current_op
                    if on_title_change is not None:
                        on_title_change(active.title)
                    header_container.clear()
                    with header_container:
                        render_workspace_header(
                            title=active.title,
                            description=active.description,
                            badge_text=state.order.display_label,
                            math_icon=active.math_icon,
                            icon=active.icon or "functions",
                        )
                    return active

                active_op = render_header()

                # Hidden order selector preserving programmatic compatibility while eliminating visual duplication
                with ui.column().classes("hidden"):
                    def handle_order_change(new_order: ODEOrder) -> None:
                        nonlocal state, is_manual_override, is_override_panel_open
                        is_manual_override = False
                        is_override_panel_open = False
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

                def handle_reset() -> None:
                    nonlocal state, is_manual_override, is_override_panel_open
                    is_manual_override = False
                    is_override_panel_open = False
                    state = state.reset()
                    results_container.clear()
                    render_content()

                # =============================================================
                # BRANCH A: Second-Order ODE — Equation-First Workflow
                # =============================================================
                if state.order == ODEOrder.SECOND_ORDER:
                    # Auto-align initial deep-linked equation before initial render if not manually overridden
                    if not is_manual_override and state.classification != ODEClassification.WRONSKIAN:
                        init_clf = classify_second_order_ode(
                            state.equation,
                            target_var=state.target_var,
                            current_classification=state.classification,
                            known_solution=state.known_solution,
                        )
                        if (
                            init_clf.status == "DETECTED"
                            and init_clf.detected_classification is not None
                            and init_clf.detected_classification != state.classification
                        ):
                            state = state.with_classification(
                                init_clf.detected_classification,
                                preserve_equation=True,
                            )
                            active_op = render_header()

                    # 1. Equation & Variable Inputs FIRST (NHẬP BÀI TOÁN)
                    with ui.column().classes("w-full gap-3 mt-1 min-w-0"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("edit_note", size="1.15rem").classes("text-blue-600")
                            ui.label("NHẬP BÀI TOÁN").classes(
                                "text-xs font-bold text-slate-700 uppercase tracking-wider"
                            )

                        input_label, input_ph = _so_input_meta(state)

                        eq_input = (
                            ui.input(
                                label=input_label,
                                placeholder=input_ph,
                                value=state.equation,
                            )
                            .classes("w-full text-base font-mono")
                            .props("clearable")
                        )

                        with ui.row().classes("w-full items-center gap-3 flex-wrap min-w-0"):
                            var_input = ui.input(
                                label="Biến số",
                                value=state.target_var,
                            ).classes("w-full sm:w-36 text-base font-mono")

                            # Adaptive Variable Selector Chips
                            render_adaptive_variable_selector(active_op, var_input)

                    # Separate lightweight summary container (updates on every keystroke)
                    # from controls container (only rebuilds when classification or mode changes,
                    # preserving example chips, mode buttons, and radio elements in-place).
                    so_y1_container = ui.column().classes("w-full min-w-0")
                    so_summary_container = ui.column().classes("w-full min-w-0")
                    so_controls_container = ui.column().classes("w-full gap-4 min-w-0")
                    so_rendered_cls: list[ODEClassification | None] = [None]

                    def render_so_summary_card() -> None:
                        nonlocal state, is_manual_override, is_override_panel_open
                        so_summary_container.clear()
                        summary = classify_second_order_ode(
                            state.equation,
                            target_var=state.target_var,
                            current_classification=state.classification,
                            known_solution=state.known_solution,
                        )
                        with so_summary_container:
                            with ui.card().classes(
                                "w-full p-3.5 md:p-4 border border-blue-200 bg-blue-50/40 rounded-xl shadow-xs gap-2.5 min-w-0"
                            ):
                                with ui.row().classes("items-center justify-between w-full flex-wrap gap-2"):
                                    with ui.row().classes("items-center gap-2 flex-wrap min-w-0"):
                                        ui.icon("analytics", size="1.15rem").classes("text-blue-600 shrink-0")
                                        ui.label("PHÂN TÍCH TỰ ĐỘNG").classes(
                                            "text-xs font-bold text-slate-800 uppercase tracking-wider"
                                        )
                                        status_badge(state.classification.display_label, variant="info")
                                        status_badge(
                                            "Ghi đè thủ công" if is_manual_override else "Tự động nhận diện",
                                            variant="warning" if is_manual_override else "neutral",
                                        )

                                    with ui.row().classes("items-center gap-1.5 flex-wrap"):
                                        if is_manual_override:
                                            def _restore_auto_detect() -> None:
                                                nonlocal state, is_manual_override
                                                is_manual_override = False
                                                changed = _sync_so_auto_classification()
                                                results_container.clear()
                                                render_so_summary_card()
                                                if changed:
                                                    render_so_controls()

                                            ui.button(
                                                "Bật lại tự động",
                                                icon="auto_fix_high",
                                                on_click=_restore_auto_detect,
                                            ).props(
                                                'flat dense no-caps aria-label="Khôi phục tự động nhận diện phân loại phương trình"'
                                            ).classes(
                                                f"text-xs text-blue-700 font-semibold rounded-lg px-2 py-1 {INTERACTION.FOCUS_RING}"
                                            )

                                        override_toggle_btn = (
                                            ui.button(
                                                "Ẩn tùy chọn phân loại" if is_override_panel_open else "Đổi phân loại thủ công",
                                                icon="unfold_less" if is_override_panel_open else "tune",
                                            )
                                            .props(
                                                f'outline dense no-caps aria-expanded="{"true" if is_override_panel_open else "false"}" '
                                                'aria-label="Mở rộng hoặc thu gọn tùy chọn phân loại phương trình cấp 2 thủ công"'
                                            )
                                            .classes(
                                                f"text-xs text-blue-700 border-blue-200 bg-white rounded-lg px-2.5 py-1 font-semibold {INTERACTION.FOCUS_RING}"
                                            )
                                        )

                                # Concise canonical form & method summary
                                with ui.row().classes(
                                    "w-full items-center justify-between bg-white border border-slate-200 rounded-lg px-3 py-2.5 gap-3 flex-wrap min-w-0"
                                ):
                                    with ui.column().classes("gap-1 min-w-0 flex-1"):
                                        if summary.canonical_form_latex:
                                            ui_math(
                                                summary.canonical_form_latex,
                                                block=False,
                                                classes="text-sm md:text-base font-bold text-slate-900",
                                            )
                                        ui.label(summary.method_hint).classes(
                                            "text-xs text-slate-600 leading-relaxed"
                                        )

                                # Order-1 mismatch or manual-override mismatch helper banner
                                if summary.status == "ORDER_1_MISMATCH":
                                    with ui.row().classes(
                                        "w-full items-center justify-between p-2.5 bg-amber-50 border border-amber-300 rounded-lg flex-wrap gap-2 min-w-0"
                                    ):
                                        with ui.row().classes("items-center gap-2 min-w-0 flex-1"):
                                            ui.icon("swap_vertical_circle", size="1.15rem").classes("text-amber-700 shrink-0")
                                            ui_math_text(
                                                f"Phương trình vừa nhập thuộc **{summary.badge_label}**, khác với không gian Cấp 2 hiện tại.",
                                                classes="text-xs font-semibold text-amber-950",
                                            )
                                        ui.button(
                                            "Chuyển sang PTVP cấp 1",
                                            icon="arrow_forward",
                                            on_click=lambda: handle_switch_order(ODEOrder.FIRST_ORDER),
                                        ).props("unelevated dense no-caps").classes(
                                            "bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-3 py-1.5 rounded-lg shadow-xs shrink-0"
                                        )
                                elif (
                                    is_manual_override
                                    and summary.status == "DETECTED"
                                    and summary.detected_classification is not None
                                    and summary.detected_classification != state.classification
                                ):
                                    det_cls = summary.detected_classification
                                    det_lbl = summary.badge_label

                                    def _sync_manual_override(dc: ODEClassification = det_cls) -> None:
                                        nonlocal state, is_manual_override
                                        is_manual_override = False
                                        state = state.with_classification(dc, preserve_equation=True)
                                        new_lbl, _ = _so_input_meta(state)
                                        eq_input._props["label"] = new_lbl
                                        eq_input.update()
                                        render_header()
                                        results_container.clear()
                                        render_so_summary_card()
                                        render_so_controls()

                                    with ui.row().classes(
                                        "w-full items-center justify-between p-2.5 bg-amber-50 border border-amber-300 rounded-lg flex-wrap gap-2 min-w-0"
                                    ):
                                        with ui.row().classes("items-center gap-2 min-w-0 flex-1"):
                                            ui.icon("sync_problem", size="1.15rem").classes("text-amber-700 shrink-0")
                                            ui_math_text(
                                                f"Phương trình vừa nhập có dạng **{det_lbl}**, khác với phân loại thủ công hiện tại (**{state.classification.display_label}**).",
                                                classes="text-xs font-semibold text-amber-950",
                                            )
                                        ui.button(
                                            f"Đồng bộ sang {det_lbl}",
                                            icon="sync",
                                            on_click=_sync_manual_override,
                                        ).props("unelevated dense no-caps").classes(
                                            "bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-3 py-1.5 rounded-lg shadow-xs shrink-0"
                                        )

                                # Expandable Manual Classification Override Panel (Secondary Control)
                                override_panel = ui.column().classes("w-full gap-2 pt-2 border-t border-blue-100 min-w-0")
                                override_panel.set_visibility(is_override_panel_open)
                                with override_panel:
                                    render_ode_classification_selector(
                                        state.order,
                                        state.classification,
                                        handle_classification_change,
                                        show_heading=False,
                                    )

                                def _toggle_override_panel() -> None:
                                    nonlocal is_override_panel_open
                                    is_override_panel_open = not is_override_panel_open
                                    override_panel.set_visibility(is_override_panel_open)
                                    override_toggle_btn.props(
                                        f'icon={"unfold_less" if is_override_panel_open else "tune"} '
                                        f'aria-expanded={"true" if is_override_panel_open else "false"}'
                                    )
                                    override_toggle_btn.set_text(
                                        "Ẩn tùy chọn phân loại" if is_override_panel_open else "Đổi phân loại thủ công"
                                    )

                                override_toggle_btn.on_click(_toggle_override_panel)

                    def render_so_controls() -> None:
                        nonlocal state
                        so_y1_container.clear()
                        so_controls_container.clear()
                        ic_input_ref[0] = None
                        so_rendered_cls[0] = state.classification

                        summary = classify_second_order_ode(
                            state.equation,
                            target_var=state.target_var,
                            current_classification=state.classification,
                            known_solution=state.known_solution,
                        )

                        # Specialized Known Solution input for Reduction of Order
                        if state.classification == ODEClassification.REDUCTION_OF_ORDER:
                            with so_y1_container:
                                with ui.row().classes("w-full items-center gap-3 min-w-0"):
                                    y1_input = ui.input(
                                        label="Nghiệm đã biết y₁(t) (tùy chọn nếu đã viết trong phương trình)",
                                        placeholder="Ví dụ: 1/t hoặc exp(t)",
                                        value=state.known_solution,
                                    ).classes("w-full text-base font-mono")

                                    def handle_known_sol_change(e: Any) -> None:
                                        nonlocal state
                                        state = state.with_known_solution(e.value or "")
                                        results_container.clear()

                                    y1_input.on_value_change(handle_known_sol_change)
                                    y1_input.on("keydown.enter", handle_submit)

                        with so_controls_container:
                            # 3. Problem Mode Selection (General vs Cauchy IVP)
                            def handle_mode_change(new_mode: ODEMode) -> None:
                                nonlocal state
                                state = state.with_mode(new_mode)
                                render_header()
                                results_container.clear()
                                render_so_controls()

                            def handle_ic_change(new_ic: str) -> None:
                                nonlocal state
                                state = state.with_initial_condition(new_ic)
                                results_container.clear()

                            render_ode_mode_selector(
                                state.order,
                                state.classification,
                                state.mode,
                                state.initial_condition,
                                handle_mode_change,
                                handle_ic_change,
                                on_ic_input_created=lambda inp: ic_input_ref.__setitem__(0, inp),
                            )
                            if ic_input_ref[0] is not None:
                                ic_input_ref[0].on("keydown.enter", handle_submit)

                            # 4. Method Selection (only for Nonhomogeneous — avoids duplicating Homogeneous/Euler summary)
                            if state.classification == ODEClassification.SECOND_ORDER_NONHOMOGENEOUS:
                                def handle_method_change(new_pref: ODEMethodPreference) -> None:
                                    nonlocal state
                                    state = state.with_method_preference(new_pref)

                                render_ode_method_selector(
                                    state.order,
                                    state.classification,
                                    state.method_preference,
                                    handle_method_change,
                                    recommended_method_hint=summary.recommended_nonhomo_method,
                                )

                            # 5. Contextual Example Chips
                            if state.classification in {
                                ODEClassification.SECOND_ORDER_HOMOGENEOUS,
                                ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
                            }:
                                cat_str = (
                                    "HOMOGENEOUS"
                                    if state.classification == ODEClassification.SECOND_ORDER_HOMOGENEOUS
                                    else "NONHOMOGENEOUS"
                                )
                                mode_str = "CAUCHY_IVP" if state.mode == ODEMode.CAUCHY_IVP else "GENERAL"
                                ex_list = get_second_order_examples(cat_str, mode_str)
                            else:
                                ex_list = DEFAULT_CONFIGS.get(state.classification, {}).get("examples", ())

                            if ex_list:
                                def _apply_so_example(example_val: str) -> None:
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
                                        target_eq = (
                                            clean_e
                                            if (state.mode == ODEMode.GENERAL and has_split_support)
                                            else example_val
                                        )
                                        state = state.with_equation(target_eq)
                                        if state.mode == ODEMode.GENERAL:
                                            state = state.with_initial_condition("")
                                            if ic_input_ref[0] is not None:
                                                ic_input_ref[0].set_value("")
                                        eq_input.set_value(target_eq)
                                    results_container.clear()
                                    render_so_summary_card()

                                render_example_chips(ex_list, on_select=_apply_so_example, label="Ví dụ mẫu:")

                            # 6. Action Row: Reset & Solve (stays synced with detected/active classification)
                            cur_active_op = get_operation_by_type(state.problem_type) or current_op
                            with ui.row().classes(
                                "w-full items-center justify-between pt-3 border-t border-slate-100 flex-wrap gap-2"
                            ):
                                ui.button("Nhập lại", icon="refresh", on_click=handle_reset).props(
                                    'flat dense no-caps aria-label="Khôi phục phương trình mặc định"'
                                ).classes(
                                    "text-xs text-slate-600 font-semibold hover:text-slate-900 rounded-lg px-2 py-1"
                                )

                                action_spec = get_primary_action_spec(cur_active_op.problem_type)
                                solve_btn = primary_button(
                                    text=action_spec.label,
                                    icon=action_spec.icon,
                                    aria_label=action_spec.aria_label,
                                )
                                solve_btn_ref[0] = solve_btn
                                solve_btn.on_click(handle_submit)

                    def _sync_so_auto_classification() -> bool:
                        nonlocal state
                        if is_manual_override or state.classification == ODEClassification.WRONSKIAN:
                            return False
                        detected_summary = classify_second_order_ode(
                            state.equation,
                            target_var=state.target_var,
                            current_classification=state.classification,
                            known_solution=state.known_solution,
                        )
                        if (
                            detected_summary.status == "DETECTED"
                            and detected_summary.detected_classification is not None
                            and detected_summary.detected_classification != state.classification
                        ):
                            state = state.with_classification(
                                detected_summary.detected_classification,
                                preserve_equation=True,
                            )
                            new_lbl, _ = _so_input_meta(state)
                            eq_input._props["label"] = new_lbl
                            eq_input.update()
                            render_header()
                            return True
                        return False

                    def handle_eq_change(e: Any) -> None:
                        nonlocal state
                        state = state.with_equation(e.value or "")
                        results_container.clear()
                        cls_changed = _sync_so_auto_classification()
                        render_so_summary_card()
                        if cls_changed or so_rendered_cls[0] != state.classification:
                            render_so_controls()

                    def handle_var_change(e: Any) -> None:
                        nonlocal state
                        state = state.with_target_var(e.value or "t")
                        new_lbl, _ = _so_input_meta(state)
                        eq_input._props["label"] = new_lbl
                        eq_input.update()
                        results_container.clear()
                        cls_changed = _sync_so_auto_classification()
                        render_so_summary_card()
                        if cls_changed or so_rendered_cls[0] != state.classification:
                            render_so_controls()

                    eq_input.on_value_change(handle_eq_change)
                    var_input.on_value_change(handle_var_change)
                    eq_input.on("keydown.enter", handle_submit)
                    var_input.on("keydown.enter", handle_submit)

                    render_so_summary_card()
                    render_so_controls()

                # =============================================================
                # BRANCH B: First-Order Guided Classification Workflow (Semantic Sections)
                # =============================================================
                else:
                    # SECTION: NHẬP BÀI TOÁN
                    with ui.column().classes("w-full gap-3 mt-1 min-w-0"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("edit_note", size="1.15rem").classes("text-blue-600")
                            ui.label("NHẬP BÀI TOÁN").classes(
                                "text-xs font-bold text-slate-700 uppercase tracking-wider"
                            )

                        eq_input = (
                            ui.input(
                                label=f"Phương trình ({state.classification.math_subtitle_for_var(state.target_var)})",
                                placeholder=state.equation,
                                value=state.equation,
                            )
                            .classes("w-full text-base font-mono")
                            .props("clearable")
                        )

                        with ui.row().classes("w-full items-center gap-3 flex-wrap min-w-0"):
                            var_input = ui.input(
                                label="Biến số",
                                value=state.target_var,
                            ).classes("w-full sm:w-36 text-base font-mono")

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
                            results_container.clear()

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
                            def _apply_fo_example(example_val: str) -> None:
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

                            render_example_chips(ex_list, on_select=_apply_fo_example, label="Ví dụ mẫu:")

                    # Dynamic Container for Semantic Analysis Sections (PHÂN TÍCH TỰ ĐỘNG, CƠ SỞ PHÂN LOẠI, PHƯƠNG PHÁP ĐỀ XUẤT)
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
                        results_container.clear()
                        update_guided_classification_panel()

                    def handle_fo_var_change(e: Any) -> None:
                        nonlocal state
                        new_var = e.value or "t"
                        state = state.with_target_var(new_var)
                        eq_input._props["label"] = f"Phương trình ({state.classification.math_subtitle_for_var(new_var)})"
                        eq_input.update()
                        results_container.clear()
                        update_guided_classification_panel()

                    eq_input.on_value_change(handle_fo_eq_change)
                    var_input.on_value_change(handle_fo_var_change)

                    # Initial rendering of guided classification panel
                    update_guided_classification_panel()

                    # Action Row: Reset & Solve (First-Order)
                    with ui.row().classes("w-full items-center justify-between pt-3 border-t border-slate-100 flex-wrap gap-2"):
                        ui.button("Nhập lại", icon="refresh", on_click=handle_reset).props(
                            'flat dense no-caps aria-label="Khôi phục phương trình mặc định"'
                        ).classes(
                            "text-xs text-slate-600 font-semibold hover:text-slate-900 rounded-lg px-2 py-1"
                        )

                        action_spec = get_primary_action_spec(active_op.problem_type)
                        solve_btn = primary_button(
                            text=action_spec.label,
                            icon=action_spec.icon,
                            aria_label=action_spec.aria_label,
                        )
                        solve_btn_ref[0] = solve_btn
                        solve_btn.on_click(handle_submit)

                        # Enter key submits from equation, variable, and optional IC inputs
                        eq_input.on("keydown.enter", handle_submit)
                        var_input.on("keydown.enter", handle_submit)
                        if ic_input_ref[0] is not None:
                            ic_input_ref[0].on("keydown.enter", handle_submit)

        def handle_switch_order(new_order: ODEOrder) -> None:
            nonlocal state, is_manual_override, is_override_panel_open
            is_manual_override = False
            is_override_panel_open = False
            state = state.with_order(new_order, preserve_equation=True)
            results_container.clear()
            render_content()

        async def handle_submit() -> None:
            nonlocal is_submitting, state
            if is_submitting:
                return
            is_submitting = True
            if solve_btn_ref[0] is not None:
                solve_btn_ref[0].disable()
            try:
                results_container.clear()

                # Auto-align Second-Order classification to detected category unless manual override was chosen
                if (
                    state.order == ODEOrder.SECOND_ORDER
                    and not is_manual_override
                    and state.classification != ODEClassification.WRONSKIAN
                ):
                    so_clf = classify_second_order_ode(
                        state.equation,
                        target_var=state.target_var,
                        current_classification=state.classification,
                        known_solution=state.known_solution,
                    )
                    if (
                        so_clf.status == "DETECTED"
                        and so_clf.detected_classification is not None
                        and so_clf.detected_classification != state.classification
                    ):
                        state = state.with_classification(
                            so_clf.detected_classification,
                            preserve_equation=True,
                        )

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
                                state = state.with_classification(
                                    pt_to_cls[clf_check.target_problem_type],
                                    preserve_equation=True,
                                )

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
                    render_loading_card("Đang giải phương trình vi phân và thực hiện kiểm định độc lập...")

                try:
                    resp: SolutionResponse = await asyncio.to_thread(use_case.execute, req, 8.0)
                except Exception as exc:
                    results_container.clear()
                    with results_container:
                        render_feedback_card(
                            title="Lỗi thực thi hệ thống",
                            messages=[f"Lỗi thực thi hệ thống: {exc}"],
                            variant="error",
                        )
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
                if solve_btn_ref[0] is not None:
                    solve_btn_ref[0].enable()

        # Results & Analysis Container
        results_container = ui.column().classes("w-full gap-5")

        # Initial render of ODE workspace content
        render_content()

        if auto_solve:
            ui.timer(0.2, handle_submit, once=True)

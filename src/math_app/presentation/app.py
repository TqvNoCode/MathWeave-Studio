"""Main NiceGUI application page and state coordinator."""

from __future__ import annotations

import asyncio
from typing import Any
from nicegui import app, ui

from math_app import __title__, __version__
from math_app.application.dtos import ProblemRequest, SolutionResponse
from math_app.application.use_cases.solve_problem import SolveProblemUseCase
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType
from math_app.input.ode_parser import (
    extract_second_order_ics_from_string,
    parse_second_order_initial_conditions,
)
from math_app.presentation.components.catalog import render_operation_catalog
from math_app.presentation.components.footer import AUTHOR_CREDIT, render_footer
from math_app.presentation.components.math_view import ui_math
from math_app.presentation.components.operation_catalog import (
    MAIN_OPERATIONS,
    OPERATIONS,
    OperationDef,
    get_operation_by_type,
)
from math_app.presentation.components.shell import (
    capture_catalog_scroll,
    create_page_shell,
    render_app_header,
    render_sticky_nav_bar,
    reset_workspace_scroll,
    restore_catalog_scroll,
)
from math_app.presentation.components.shared import (
    primary_button,
    section_card,
    status_badge,
)
from math_app.presentation.components.solution_view import render_solution_view
from math_app.presentation.components.workspace import (
    render_adaptive_variable_selector,
    render_matrix_helper_panel,
)
from math_app.presentation.components.workspace.ode import render_ode_workspace
from math_app.presentation.design_system.styles import get_head_html
from math_app.presentation.startup import resolve_assets_path
import sympy as sp


def build_second_order_problem_request(
    equation: str,
    category: str = "HOMOGENEOUS",
    mode: str = "GENERAL",
    initial_condition: str = "",
    method_pref: str = "AUTO",
    target_var: str = "t",
) -> ProblemRequest:
    """Validate inputs, resolve Cauchy conditions, detect conflicts, and construct
    the authoritative ProblemRequest for second-order ODE and Cauchy IVP workflows.
    """
    cleaned_eq = equation.strip()
    if not cleaned_eq:
        raise InvalidInputError("Phương trình không được để trống. Vui lòng nhập dữ liệu trước khi thực hiện.")

    target_variable = target_var.strip() or "t"
    cat = category.strip().upper()
    md = mode.strip().upper()
    pref = method_pref.strip().upper() if method_pref else "AUTO"

    clean_eq, inline_y_ic, inline_yp_ic, _ = extract_second_order_ics_from_string(cleaned_eq)
    has_inline = bool(inline_y_ic or inline_yp_ic)
    complete_inline = bool(inline_y_ic and inline_yp_ic)

    dedicated_ic = initial_condition.strip()
    ded_y_ic: str | None = None
    ded_yp_ic: str | None = None
    if dedicated_ic:
        _, ded_y_ic, ded_yp_ic, _ = extract_second_order_ics_from_string("dummy = 0, " + dedicated_ic)
        if not ded_y_ic and not ded_yp_ic and "=" in dedicated_ic:
            if "'" in dedicated_ic or "prime" in dedicated_ic:
                ded_yp_ic = dedicated_ic
            else:
                ded_y_ic = dedicated_ic

    has_dedicated = bool(ded_y_ic or ded_yp_ic)
    complete_dedicated = bool(ded_y_ic and ded_yp_ic)

    if md == "CAUCHY_IVP":
        if has_inline and has_dedicated:
            if not complete_inline or not complete_dedicated:
                raise InvalidInputError(
                    "Phát hiện xung đột hoặc không đồng nhất điều kiện ban đầu: "
                    "Vui lòng cung cấp đầy đủ cả y(t0) và y'(t0) tại một nơi duy nhất."
                )
            # Parse both pairs to check equality
            try:
                ((t0_in, y0_in), (_, v0_in)) = parse_second_order_initial_conditions(
                    inline_y_ic, inline_yp_ic, target_variable  # type: ignore[arg-type]
                )
                ((t0_ded, y0_ded), (_, v0_ded)) = parse_second_order_initial_conditions(
                    ded_y_ic, ded_yp_ic, target_variable  # type: ignore[arg-type]
                )
            except InvalidInputError as e:
                raise InvalidInputError(f"Lỗi phân tích điều kiện ban đầu: {e}") from e

            same_t0 = sp.simplify(t0_in - t0_ded) == 0
            same_y0 = sp.simplify(y0_in - y0_ded) == 0
            same_v0 = sp.simplify(v0_in - v0_ded) == 0
            if not (same_t0 and same_y0 and same_v0):
                raise InvalidInputError(
                    f"Phát hiện xung đột điều kiện ban đầu: Phương trình chứa điều kiện '{inline_y_ic}, {inline_yp_ic}', "
                    f"nhưng ô điều kiện ban đầu chuyên biệt lại chứa '{ded_y_ic}, {ded_yp_ic}'. "
                    "Vui lòng chỉ nhập điều kiện ban đầu tại một nơi duy nhất hoặc đồng nhất dữ liệu giữa hai nguồn."
                )
            auth_ic = f"{ded_y_ic}, {ded_yp_ic}"
        elif has_dedicated:
            if not complete_dedicated:
                raise InvalidInputError(
                    "Bài toán Cauchy (IVP) cấp hai yêu cầu cung cấp đầy đủ hai điều kiện ban đầu: y(t0) = y0 và y'(t0) = v0."
                )
            parse_second_order_initial_conditions(ded_y_ic, ded_yp_ic, target_variable)  # type: ignore[arg-type]
            auth_ic = f"{ded_y_ic}, {ded_yp_ic}"
        elif has_inline:
            if not complete_inline:
                raise InvalidInputError(
                    "Bài toán Cauchy (IVP) cấp hai yêu cầu cung cấp đầy đủ hai điều kiện ban đầu: y(t0) = y0 và y'(t0) = v0."
                )
            parse_second_order_initial_conditions(inline_y_ic, inline_yp_ic, target_variable)  # type: ignore[arg-type]
            auth_ic = f"{inline_y_ic}, {inline_yp_ic}"
        else:
            raise InvalidInputError(
                "Bài toán Cauchy (IVP) cấp hai yêu cầu cung cấp đầy đủ hai điều kiện ban đầu: y(t0) = y0 và y'(t0) = v0."
            )

        req_raw = clean_eq
        problem_type = ProblemType.ODE_SECOND_ORDER_IVP
        params: dict[str, Any] = {
            "expected_classification": cat,
            "problem_mode": md,
            "initial_condition": auth_ic,
        }
    else:  # GENERAL
        req_raw = cleaned_eq
        problem_type = ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF
        params = {
            "expected_classification": cat,
            "problem_mode": md,
        }

    if cat == "NONHOMOGENEOUS":
        params["method_preference"] = pref

    return ProblemRequest(
        raw_input=req_raw,
        problem_type=problem_type,
        target_variable=target_variable,
        parameters=params,
    )


def create_app(use_case: SolveProblemUseCase) -> None:
    """Configure the NiceGUI page layout and interaction handlers."""

    # Mount static assets for offline OpenType math fonts and local stylesheets
    base_assets = resolve_assets_path()
    if base_assets.is_dir():
        try:
            app.add_static_files("/assets", str(base_assets))
        except ValueError:
            pass  # Route already mounted (e.g. repeated create_app in test harness)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("Không thể mount thư mục static assets %s: %s", base_assets, exc)
    else:
        import logging
        logging.getLogger(__name__).warning("Không tìm thấy thư mục static assets tại: %s. KaTeX cục bộ và font có thể không tải được.", base_assets)

    @ui.page("/")
    def main_page(
        op: str | None = None,
        eq: str | None = None,
        ic: str | None = None,
        solve: str | bool | None = None,
    ) -> None:
        ui.page_title(f"{__title__} — Phần mềm Học tập & Nghiên cứu Toán học")

        # Inject global styles and local KaTeX for robust cross-browser math rendering
        # Includes strict mode filtering callback for Unicode & unknown symbols:
        # strict: function(errorCode, errorMsg, token) {
        #     if (errorCode === 'unknownSymbol' || errorCode === 'unicodeTextInMathMode') {
        #         return 'ignore';
        #     }
        #     return 'warn';
        # }
        ui.add_head_html(get_head_html())

        # Application state
        current_op: OperationDef = OPERATIONS[0]
        active_screen = "SCREEN_A"  # "SCREEN_A" (Catalog) or "SCREEN_B" (Problem Solving)

        # Query parameter prefill support for direct navigation and genuine automated UI testing
        auto_solve_req = False
        if eq is not None or op is not None:
            active_screen = "SCREEN_B"
            if op is not None:
                try:
                    pt = ProblemType(op)
                    resolved = get_operation_by_type(pt)
                    if resolved:
                        current_op = resolved
                except Exception:
                    pass
            elif eq is not None:
                current_op = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR) or current_op
            if solve is not None and str(solve).lower() in ("1", "true", "yes"):
                auto_solve_req = True

        def open_about_dialog() -> None:
            """Display modal with MathWeave Studio application information and metadata."""
            with ui.dialog() as dialog, ui.card().classes("p-6 max-w-md w-full rounded-2xl shadow-xl"):
                with ui.column().classes("gap-4 w-full"):
                    with ui.row().classes("items-center gap-3"):
                        with ui.avatar(icon="functions", color="primary", text_color="white").classes("shadow-sm"):
                            pass
                        with ui.column().classes("gap-0.5"):
                            ui.label(__title__).classes("text-lg font-black text-slate-900 tracking-tight")
                            ui.label("Phần mềm Hỗ trợ Học tập & Nghiên cứu Toán học Chuyên sâu").classes("text-xs text-slate-500 font-medium")

                    ui.separator()

                    with ui.column().classes("gap-2.5 text-xs text-slate-600"):
                        with ui.row().classes("justify-between w-full items-center"):
                            ui.label("Phiên bản:").classes("font-semibold text-slate-700")
                            ui.label(f"MVP · v{__version__}").classes("font-mono font-medium bg-slate-100 px-2 py-0.5 rounded")
                        with ui.row().classes("justify-between w-full items-center"):
                            ui.label("Nền tảng:").classes("font-semibold text-slate-700")
                            ui.label("Desktop Application (Linux / Cross-platform)").classes("font-medium")
                        with ui.row().classes("justify-between w-full items-center"):
                            ui.label("Bản quyền:").classes("font-semibold text-slate-700")
                            ui.label(AUTHOR_CREDIT).classes("font-medium")
                        with ui.row().classes("justify-between w-full items-center"):
                            ui.label("Công nghệ:").classes("font-semibold text-slate-700")
                            ui.label("NiceGUI · SymPy · NumPy · Plotly").classes("font-medium")

                    with ui.row().classes("w-full justify-end pt-2"):
                        ui.button("Đóng", on_click=dialog.close).props("flat no-caps").classes("text-xs font-bold text-slate-700")
            dialog.open()

        # Root page container
        page_col = create_page_shell()

        with page_col:
            # Global Header
            render_app_header(on_about_click=open_about_dialog)

            # Dynamic Screen Body
            screen_body = ui.column().classes("w-full gap-6 flex-grow")

            def render_current_screen() -> None:
                screen_body.clear()
                with screen_body:
                    if active_screen == "SCREEN_A":
                        render_screen_a()
                    else:
                        render_screen_b()

            def switch_to_operation(op: OperationDef) -> None:
                nonlocal current_op, active_screen
                capture_catalog_scroll(screen_body.client)
                current_op = op
                active_screen = "SCREEN_B"
                render_current_screen()
                reset_workspace_scroll(screen_body.client)

            def switch_to_catalog() -> None:
                nonlocal active_screen
                active_screen = "SCREEN_A"
                render_current_screen()
                restore_catalog_scroll(screen_body.client)

            # ================= SCREEN A: OPERATION CATALOG =================
            def render_screen_a() -> None:
                render_operation_catalog(
                    on_select=switch_to_operation,
                    operations=MAIN_OPERATIONS,
                )

            # ================= SCREEN B: PROBLEM SOLVING & RESULTS =================
            def render_screen_b() -> None:
                is_calculus = current_op.is_calculus
                is_matrix_op = current_op.is_matrix

                with ui.column().classes("w-full gap-5"):
                    # Shared High-Contrast Sticky Navigation Bar
                    display_title = current_op.title
                    if current_op.problem_type == ProblemType.DEFINITE_INTEGRAL:
                        display_title = "Tích phân xác định (Một biến)"
                    elif current_op.problem_type == ProblemType.TRIPLE_INTEGRAL:
                        display_title = "Tích phân khối"

                    render_sticky_nav_bar(
                        title=display_title,
                        domain=current_op.domain,
                        on_back=switch_to_catalog,
                        math_icon=current_op.math_icon,
                        icon=current_op.icon,
                    )

                    # Definite Integration Subtype Selector Banner
                    if current_op.problem_type in {
                        ProblemType.DEFINITE_INTEGRAL,
                        ProblemType.LINE_INTEGRAL,
                        ProblemType.SURFACE_INTEGRAL,
                        ProblemType.TRIPLE_INTEGRAL,
                    }:
                        with ui.card().classes("w-full p-3.5 bg-blue-50/90 border border-blue-200 rounded-xl shadow-xs"):
                            with ui.row().classes("items-center justify-between w-full flex-wrap gap-3"):
                                with ui.row().classes("items-center gap-2 shrink-0"):
                                    ui.icon("layers", color="primary", size="1.25rem")
                                    ui.label("CHỌN DẠNG TÍCH PHÂN:").classes("text-xs md:text-sm font-black text-blue-950 uppercase tracking-wider")
                                with ui.row().classes("gap-2 flex-wrap items-center"):
                                    subtypes = [
                                        (ProblemType.DEFINITE_INTEGRAL, "Một biến"),
                                        (ProblemType.LINE_INTEGRAL, "Tích phân đường"),
                                        (ProblemType.SURFACE_INTEGRAL, "Tích phân mặt"),
                                        (ProblemType.TRIPLE_INTEGRAL, "Tích phân khối"),
                                    ]
                                    for pt, lbl in subtypes:
                                        is_sel = (current_op.problem_type == pt)
                                        btn_cls = (
                                            "bg-blue-600 text-white font-bold shadow-sm ring-2 ring-blue-400"
                                            if is_sel
                                            else "bg-white text-slate-700 hover:bg-slate-100 border border-slate-200"
                                        )
                                        ui.button(
                                            lbl,
                                            on_click=lambda _, p=pt: switch_to_operation(get_operation_by_type(p)),
                                        ).props(f"{'unelevated' if is_sel else 'outline'} no-caps").classes(
                                            f"text-xs md:text-sm h-10 px-4 rounded-lg {btn_cls} transition-all font-semibold"
                                        )

                    # Route to Unified ODE Workspace or Unified Non-ODE Workspace
                    is_ode_op = current_op.problem_type in {
                        ProblemType.ODE_FIRST_ORDER_LINEAR,
                        ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
                        ProblemType.ODE_SEPARABLE,
                        ProblemType.ODE_EXACT,
                        ProblemType.ODE_INTEGRATING_FACTOR,
                        ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
                        ProblemType.ODE_SECOND_ORDER_IVP,
                        ProblemType.ODE_REDUCTION_OF_ORDER,
                        ProblemType.WRONSKIAN,
                    }

                    if is_ode_op:
                        render_ode_workspace(
                            current_op=current_op,
                            use_case=use_case,
                            on_operation_switch=switch_to_operation,
                            on_back_to_catalog=switch_to_catalog,
                            initial_eq=eq,
                            initial_ic=ic,
                            auto_solve=auto_solve_req,
                        )
                    else:
                        # Unified Workspace Card for Calculus, Algebra & Linear Algebra
                        with section_card("p-5 md:p-6 gap-5"):
                            # Section A: Header & Operation Identity
                            with ui.row().classes("items-center justify-between w-full pb-3 border-b border-slate-100 flex-wrap gap-2"):
                                with ui.row().classes("items-center gap-3"):
                                    if current_op.math_icon:
                                        with ui.row().classes(
                                            "px-3 py-1.5 min-w-[3rem] rounded-lg bg-blue-50 text-blue-800 items-center justify-center overflow-visible shadow-xs"
                                        ):
                                            ui_math(
                                                current_op.math_icon,
                                                block=False,
                                                classes="math-icon text-base font-bold select-none pointer-events-none",
                                                is_icon=True,
                                            )
                                    else:
                                        ui.icon(current_op.icon, size="1.4rem").classes("text-blue-600")

                                    with ui.column().classes("gap-0"):
                                        ui.label(current_op.title).classes("text-base md:text-lg font-bold text-slate-900")
                                        ui.label(current_op.description).classes("text-xs text-slate-500 leading-snug")

                                status_badge(current_op.domain, variant="info")

                            # Dynamic Form Inputs
                            form_container = ui.column().classes("w-full gap-4")
                            extra_controls: dict[str, Any] = {}

                            with form_container:
                                # 1. Main mathematical expression or matrix input
                                if is_matrix_op:
                                    main_input_label = "Dữ liệu ma trận A"
                                elif current_op.problem_type == ProblemType.SOLVE_EQUATION:
                                    main_input_label = "Phương trình đại số hoặc biểu thức f(x) = 0"
                                elif current_op.problem_type == ProblemType.DEFINITE_INTEGRAL:
                                    main_input_label = "Hàm số dưới dấu tích phân f(x)"
                                elif current_op.problem_type == ProblemType.LINE_INTEGRAL:
                                    main_input_label = "Hàm dưới dấu tích phân (Vô hướng f(x, y, z) hoặc Trường vectơ F = P, Q, R)"
                                elif current_op.problem_type == ProblemType.SURFACE_INTEGRAL:
                                    main_input_label = "Hàm dưới dấu tích phân (Vô hướng f(x, y, z) hoặc Trường vectơ F = P, Q, R)"
                                elif current_op.problem_type == ProblemType.TRIPLE_INTEGRAL:
                                    main_input_label = "Hàm dưới dấu tích phân khối f(x, y, z)"
                                elif current_op.problem_type in (
                                    ProblemType.GREENS_THEOREM,
                                    ProblemType.STOKES_THEOREM,
                                    ProblemType.DIVERGENCE_THEOREM,
                                ):
                                    main_input_label = "Biểu thức trường vectơ F (phân tách bởi dấu phẩy)"
                                elif current_op.problem_type == ProblemType.SURFACE_AREA:
                                    main_input_label = "Hàm mặt cong z = f(x, y)"
                                elif current_op.problem_type == ProblemType.SURFACE_OF_REVOLUTION:
                                    main_input_label = "Hàm đường sinh y = f(x)"
                                else:
                                    main_input_label = "Biểu thức toán học f(x)"

                                expr_input = (
                                    ui.input(
                                        label=main_input_label,
                                        placeholder=current_op.default_input,
                                        value=current_op.default_input,
                                    )
                                    .classes("w-full text-base font-mono")
                                    .props("clearable")
                                )

                                # Matrix Guidance & Interactive Templates (Linear Algebra)
                                if is_matrix_op:
                                    render_matrix_helper_panel(current_op, expr_input)

                                # 2. Derivative-specific repositioned order field
                                if current_op.problem_type == ProblemType.DERIVATIVE:
                                    with ui.row().classes("items-center gap-3 pt-1"):
                                        order_input = ui.number(
                                            label="Cấp đạo hàm (n)",
                                            value=1,
                                            min=1,
                                            max=10,
                                            step=1,
                                        ).classes("w-36 text-base")
                                        extra_controls["order"] = order_input
                                        ui.label("(n = 1: Đạo hàm bậc 1; n ≥ 2: Đạo hàm cấp cao)").classes(
                                            "text-xs text-slate-400 self-center pt-2"
                                        )

                                # 3. Variable Selection: Adaptive for 1D/Algebra, Custom for Multivariable
                                has_custom_multivar = current_op.problem_type in {
                                    ProblemType.LINE_INTEGRAL,
                                    ProblemType.SURFACE_INTEGRAL,
                                    ProblemType.TRIPLE_INTEGRAL,
                                    ProblemType.GREENS_THEOREM,
                                    ProblemType.STOKES_THEOREM,
                                    ProblemType.DIVERGENCE_THEOREM,
                                    ProblemType.SURFACE_AREA,
                                }

                                if not is_matrix_op and not has_custom_multivar:
                                    with ui.column().classes("w-full gap-2 pt-1"):
                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                            var_input = ui.input(
                                                label="Biến số / biến vi phân",
                                                value=current_op.target_var,
                                            ).classes("w-36 text-base font-mono")
                                            extra_controls["target_var"] = var_input
                                            render_adaptive_variable_selector(current_op, var_input)

                                # 4. Parameters for Definite Integrals & Arc Length
                                if current_op.problem_type in (ProblemType.DEFINITE_INTEGRAL, ProblemType.ARC_LENGTH):
                                    with ui.column().classes("w-full p-3.5 bg-blue-50/50 border border-blue-200 rounded-xl gap-2"):
                                        bounds_label = (
                                            "Khoảng lấy tích phân [a, b]:"
                                            if current_op.problem_type == ProblemType.DEFINITE_INTEGRAL
                                            else "Khoảng độ dài cung [a, b]:"
                                        )
                                        with ui.row().classes("items-center gap-2"):
                                            ui.icon("straighten", size="1.1rem").classes("text-blue-700")
                                            ui.label(bounds_label).classes("text-xs font-bold text-blue-950 uppercase tracking-wider")
                                        with ui.row().classes("items-center gap-2 flex-wrap"):
                                            ui.label("[").classes("text-lg font-bold text-blue-400 select-none")
                                            lower_input = ui.input(label="Cận dưới (a)", value="0").classes("w-32 font-mono")
                                            ui.label(";").classes("text-lg font-bold text-blue-400 select-none self-center")
                                            upper_input = ui.input(
                                                label="Cận trên (b)",
                                                value="1" if current_op.problem_type == ProblemType.DEFINITE_INTEGRAL else "3",
                                            ).classes("w-32 font-mono")
                                            ui.label("]").classes("text-lg font-bold text-blue-400 select-none")
                                            extra_controls["lower_bound"] = lower_input
                                            extra_controls["upper_bound"] = upper_input

                                # 5. Parameters for Line Integrals
                                if current_op.problem_type == ProblemType.LINE_INTEGRAL:
                                    with ui.column().classes("w-full gap-3 p-4 bg-slate-50 border border-slate-200 rounded-xl"):
                                        with ui.row().classes("items-center gap-2"):
                                            ui.icon("timeline", size="1.1rem").classes("text-blue-700")
                                            ui.label("Cấu hình kiểu tích phân đường & Định hướng cung C:").classes(
                                                "text-xs font-bold text-slate-800 uppercase tracking-wider"
                                            )
                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                            line_mode = ui.select(
                                                options=["Vô hướng (f ds)", "Trường vectơ (F·dr)"],
                                                value="Vô hướng (f ds)",
                                                label="Kiểu tích phân",
                                            ).classes("w-52")
                                            line_orient = ui.select(
                                                options=["Hướng thuận (+t)", "Hướng nghịch (-t)"],
                                                value="Hướng thuận (+t)",
                                                label="Định hướng cung C",
                                            ).classes("w-44")
                                            extra_controls["line_mode"] = line_mode
                                            extra_controls["orientation"] = line_orient

                                        ui.label("Tham số hóa đường cong C: r(t) = (x(t), y(t), z(t)) trên [t_min, t_max]:").classes(
                                            "text-xs font-bold text-slate-700 uppercase tracking-wider mt-1"
                                        )
                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                            param_var = ui.input(label="Tham số t", value="t").classes("w-20 font-mono")
                                            t_min = ui.input(label="t_min", value="0").classes("w-24 font-mono")
                                            t_max = ui.input(label="t_max", value="1").classes("w-24 font-mono")
                                            extra_controls["param_var"] = param_var
                                            extra_controls["t_min"] = t_min
                                            extra_controls["t_max"] = t_max
                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                            param_x = ui.input(label="x(t)", value="3*t").classes("w-32 font-mono")
                                            param_y = ui.input(label="y(t)", value="4*t").classes("w-32 font-mono")
                                            param_z = ui.input(label="z(t)", value="0").classes("w-32 font-mono")
                                            extra_controls["param_x"] = param_x
                                            extra_controls["param_y"] = param_y
                                            extra_controls["param_z"] = param_z

                                # 6. Parameters for Surface Integrals
                                if current_op.problem_type == ProblemType.SURFACE_INTEGRAL:
                                    with ui.column().classes("w-full gap-3 p-4 bg-slate-50 border border-slate-200 rounded-xl"):
                                        with ui.row().classes("items-center gap-2"):
                                            ui.icon("layers", size="1.1rem").classes("text-blue-700")
                                            ui.label("Kiểu tích phân mặt & Định hướng pháp tuyến:").classes(
                                                "text-xs font-bold text-slate-800 uppercase tracking-wider"
                                            )
                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                            surf_mode = ui.select(
                                                options=["Vô hướng (f dS)", "Thông lượng vectơ (F·n dS)"],
                                                value="Vô hướng (f dS)",
                                                label="Kiểu tích phân mặt",
                                            ).classes("w-56")
                                            surf_orient = ui.select(
                                                options=["Pháp tuyến hướng lên (Upward / +k)", "Pháp tuyến hướng xuống (Downward / -k)"],
                                                value="Pháp tuyến hướng lên (Upward / +k)",
                                                label="Định hướng mặt S",
                                            ).classes("w-60")
                                            surf_type = ui.select(
                                                options=["Mặt đồ thị: z = g(x, y)", "Mặt tham số: r(u, v)"],
                                                value="Mặt đồ thị: z = g(x, y)",
                                                label="Hình học mặt S",
                                            ).classes("w-56")
                                            extra_controls["surf_mode"] = surf_mode
                                            extra_controls["orientation"] = surf_orient
                                            extra_controls["surface_type"] = surf_type

                                        surf_geo_box = ui.column().classes("w-full gap-2 mt-1")
                                        with surf_geo_box:
                                            def update_surf_geo_fields():
                                                surf_geo_box.clear()
                                                with surf_geo_box:
                                                    is_param = "tham số" in str(surf_type.value).lower()
                                                    # Preserve user-entered bounds when practical across mode switches
                                                    curr_u_min = extra_controls["u_min"].value if "u_min" in extra_controls and hasattr(extra_controls["u_min"], "value") else "0"
                                                    curr_u_max = extra_controls["u_max"].value if "u_max" in extra_controls and hasattr(extra_controls["u_max"], "value") else "1"
                                                    curr_v_min = extra_controls["v_min"].value if "v_min" in extra_controls and hasattr(extra_controls["v_min"], "value") else "0"
                                                    curr_v_max = extra_controls["v_max"].value if "v_max" in extra_controls and hasattr(extra_controls["v_max"], "value") else "1"

                                                    if is_param:
                                                        # Explicitly purge obsolete graph mode controls
                                                        extra_controls.pop("surface_expr", None)
                                                        ui.label("Tham số hóa mặt cong S: r(u, v) = (x(u,v), y(u,v), z(u,v)):").classes(
                                                            "text-xs font-bold text-slate-700 uppercase tracking-wider"
                                                        )
                                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                                            px = ui.input(label="x(u, v)", value="u").classes("w-32 font-mono")
                                                            py = ui.input(label="y(u, v)", value="v").classes("w-32 font-mono")
                                                            pz = ui.input(label="z(u, v)", value="1 - u - v").classes("w-36 font-mono")
                                                            extra_controls["param_x"] = px
                                                            extra_controls["param_y"] = py
                                                            extra_controls["param_z"] = pz
                                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                                            u_var = ui.input(label="Biến u", value="u").classes("w-20 font-mono")
                                                            u_min = ui.input(label="u_min", value=curr_u_min).classes("w-24 font-mono")
                                                            u_max = ui.input(label="u_max", value=curr_u_max).classes("w-24 font-mono")
                                                            v_var = ui.input(label="Biến v", value="v").classes("w-20 font-mono")
                                                            v_min = ui.input(label="v_min", value=curr_v_min).classes("w-24 font-mono")
                                                            v_max = ui.input(label="v_max", value=curr_v_max).classes("w-24 font-mono")
                                                            extra_controls["u_var"] = u_var
                                                            extra_controls["u_min"] = u_min
                                                            extra_controls["u_max"] = u_max
                                                            extra_controls["v_var"] = v_var
                                                            extra_controls["v_min"] = v_min
                                                            extra_controls["v_max"] = v_max
                                                    else:
                                                        # Explicitly purge obsolete parametric mode controls
                                                        extra_controls.pop("param_x", None)
                                                        extra_controls.pop("param_y", None)
                                                        extra_controls.pop("param_z", None)
                                                        ui.label("Phương trình mặt cong và miền chữ nhật D [x_min, x_max] × [y_min, y_max]:").classes(
                                                            "text-xs font-bold text-slate-700 uppercase tracking-wider"
                                                        )
                                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                                            surf_expr = ui.input(label="Phương trình mặt: z = g(x, y)", value="1 - x - y").classes("w-64 font-mono")
                                                            extra_controls["surface_expr"] = surf_expr
                                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                                            u_min = ui.input(label="x_min", value=curr_u_min).classes("w-24 font-mono")
                                                            u_max = ui.input(label="x_max", value=curr_u_max).classes("w-24 font-mono")
                                                            v_min = ui.input(label="y_min", value=curr_v_min).classes("w-24 font-mono")
                                                            v_max = ui.input(label="y_max", value=curr_v_max).classes("w-24 font-mono")
                                                            extra_controls["u_var"] = "x"
                                                            extra_controls["v_var"] = "y"
                                                            extra_controls["u_min"] = u_min
                                                            extra_controls["u_max"] = u_max
                                                            extra_controls["v_min"] = v_min
                                                            extra_controls["v_max"] = v_max

                                            update_surf_geo_fields()
                                            surf_type.on_value_change(lambda: update_surf_geo_fields())

                                # 7. Parameters for Triple Integrals
                                if current_op.problem_type == ProblemType.TRIPLE_INTEGRAL:
                                    with ui.column().classes("w-full gap-3 p-4 bg-slate-50 border border-slate-200 rounded-xl"):
                                        with ui.row().classes("items-center gap-2"):
                                            ui.icon("view_in_ar", size="1.1rem").classes("text-blue-700")
                                            ui.label("Hệ tọa độ không gian 3D & Cận tích phân khối:").classes(
                                                "text-xs font-bold text-slate-800 uppercase tracking-wider"
                                            )
                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                            coord_sel = ui.select(
                                                options=["Tọa độ Descartes (x, y, z)", "Tọa độ trụ (r, θ, z)", "Tọa độ cầu (ρ, φ, θ)"],
                                                value="Tọa độ Descartes (x, y, z)",
                                                label="Hệ tọa độ",
                                            ).classes("w-64")
                                            extra_controls["coord_system"] = coord_sel

                                        triple_bounds_box = ui.column().classes("w-full gap-2 mt-1")
                                        with triple_bounds_box:
                                            def update_triple_bounds():
                                                # Explicitly purge all coordinate bounds before registering active set
                                                for k in (
                                                    "x_min", "x_max", "y_min", "y_max", "z_min", "z_max",
                                                    "th_min", "th_max", "r_min", "r_max",
                                                    "phi_min", "phi_max", "rho_min", "rho_max",
                                                ):
                                                    extra_controls.pop(k, None)

                                                triple_bounds_box.clear()
                                                with triple_bounds_box:
                                                    c_val = str(coord_sel.value).lower()
                                                    if "trụ" in c_val or "cylindrical" in c_val:
                                                        ui.label("Cận tọa độ trụ [θ_min, θ_max] × [r_min, r_max] × [z_min, z_max] (dV = r dz dr dθ):").classes(
                                                            "text-xs font-bold text-slate-700 uppercase tracking-wider"
                                                        )
                                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                                            th_min = ui.input(label="θ_min", value="0").classes("w-24 font-mono")
                                                            th_max = ui.input(label="θ_max", value="2*pi").classes("w-24 font-mono")
                                                            r_min = ui.input(label="r_min", value="0").classes("w-24 font-mono")
                                                            r_max = ui.input(label="r_max", value="1").classes("w-24 font-mono")
                                                            z_min = ui.input(label="z_min", value="0").classes("w-24 font-mono")
                                                            z_max = ui.input(label="z_max", value="2").classes("w-24 font-mono")
                                                            extra_controls["th_min"] = th_min
                                                            extra_controls["th_max"] = th_max
                                                            extra_controls["r_min"] = r_min
                                                            extra_controls["r_max"] = r_max
                                                            extra_controls["z_min"] = z_min
                                                            extra_controls["z_max"] = z_max
                                                    elif "cầu" in c_val or "spherical" in c_val:
                                                        ui.label("Cận tọa độ cầu [θ_min, θ_max] × [φ_min, φ_max] × [ρ_min, ρ_max] (dV = ρ² sin(φ) dρ dφ dθ):").classes(
                                                            "text-xs font-bold text-slate-700 uppercase tracking-wider"
                                                        )
                                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                                            th_min = ui.input(label="θ_min", value="0").classes("w-24 font-mono")
                                                            th_max = ui.input(label="θ_max", value="2*pi").classes("w-24 font-mono")
                                                            phi_min = ui.input(label="φ_min", value="0").classes("w-24 font-mono")
                                                            phi_max = ui.input(label="φ_max", value="pi").classes("w-24 font-mono")
                                                            rho_min = ui.input(label="ρ_min", value="0").classes("w-24 font-mono")
                                                            rho_max = ui.input(label="ρ_max", value="1").classes("w-24 font-mono")
                                                            extra_controls["th_min"] = th_min
                                                            extra_controls["th_max"] = th_max
                                                            extra_controls["phi_min"] = phi_min
                                                            extra_controls["phi_max"] = phi_max
                                                            extra_controls["rho_min"] = rho_min
                                                            extra_controls["rho_max"] = rho_max
                                                    else:
                                                        ui.label("Cận khối hộp V [x_min, x_max] × [y_min, y_max] × [z_min, z_max] (dV = dz dy dx):").classes(
                                                            "text-xs font-bold text-slate-700 uppercase tracking-wider"
                                                        )
                                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                                            x_min = ui.input(label="x_min", value="0").classes("w-24 font-mono")
                                                            x_max = ui.input(label="x_max", value="1").classes("w-24 font-mono")
                                                            y_min = ui.input(label="y_min", value="0").classes("w-24 font-mono")
                                                            y_max = ui.input(label="y_max", value="2").classes("w-24 font-mono")
                                                            z_min = ui.input(label="z_min", value="0").classes("w-24 font-mono")
                                                            z_max = ui.input(label="z_max", value="3").classes("w-24 font-mono")
                                                            extra_controls["x_min"] = x_min
                                                            extra_controls["x_max"] = x_max
                                                            extra_controls["y_min"] = y_min
                                                            extra_controls["y_max"] = y_max
                                                            extra_controls["z_min"] = z_min
                                                            extra_controls["z_max"] = z_max

                                            update_triple_bounds()
                                            coord_sel.on_value_change(lambda: update_triple_bounds())

                                # 8. Parameters for Surface Area
                                if current_op.problem_type == ProblemType.SURFACE_AREA:
                                    with ui.column().classes("w-full p-3.5 bg-blue-50/50 border border-blue-200 rounded-xl gap-2"):
                                        with ui.row().classes("items-center gap-2"):
                                            ui.icon("aspect_ratio", size="1.1rem").classes("text-blue-700")
                                            ui.label("Miền chữ nhật D: [x_min, x_max] × [y_min, y_max]:").classes(
                                                "text-xs font-bold text-blue-950 uppercase tracking-wider"
                                            )
                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                            u_min = ui.input(label="x_min", value="0").classes("w-24 font-mono")
                                            u_max = ui.input(label="x_max", value="1").classes("w-24 font-mono")
                                            v_min = ui.input(label="y_min", value="0").classes("w-24 font-mono")
                                            v_max = ui.input(label="y_max", value="1").classes("w-24 font-mono")
                                            extra_controls["u_min"] = u_min
                                            extra_controls["u_max"] = u_max
                                            extra_controls["v_min"] = v_min
                                            extra_controls["v_max"] = v_max

                                # 9. Parameters for Surface of Revolution
                                if current_op.problem_type == ProblemType.SURFACE_OF_REVOLUTION:
                                    with ui.column().classes("w-full p-3.5 bg-blue-50/50 border border-blue-200 rounded-xl gap-2"):
                                        with ui.row().classes("items-center gap-2"):
                                            ui.icon("rotate_right", size="1.1rem").classes("text-blue-700")
                                            ui.label("Trục quay & Khoảng [a, b]:").classes("text-xs font-bold text-blue-950 uppercase tracking-wider")
                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                            axis_sel = ui.select(options=["Ox (y = 0)", "Oy (x = 0)"], value="Ox (y = 0)", label="Trục quay").classes("w-40 text-sm")
                                            a_in = ui.input(label="Cận dưới (a)", value="0").classes("w-32 font-mono")
                                            b_in = ui.input(label="Cận trên (b)", value="1").classes("w-32 font-mono")
                                            extra_controls["axis"] = axis_sel
                                            extra_controls["lower_bound"] = a_in
                                            extra_controls["upper_bound"] = b_in

                                # 10. Parameters for Green's Theorem
                                if current_op.problem_type == ProblemType.GREENS_THEOREM:
                                    with ui.column().classes("w-full gap-2 p-3.5 bg-slate-50 border border-slate-200 rounded-xl"):
                                        with ui.row().classes("items-center gap-2"):
                                            ui.icon("all_inclusive", size="1.1rem").classes("text-blue-700")
                                            ui.label("Dạng định lý và miền chữ nhật D:").classes("text-xs font-bold text-slate-800 uppercase tracking-wider")
                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                            form_sel = ui.select(options=["Lưu thông (Circulation)", "Thông lượng (Flux)"], value="Lưu thông (Circulation)", label="Dạng định lý").classes("w-56 text-sm")
                                            x_min = ui.input(label="x_min", value="0").classes("w-24 font-mono")
                                            x_max = ui.input(label="x_max", value="1").classes("w-24 font-mono")
                                            y_min = ui.input(label="y_min", value="0").classes("w-24 font-mono")
                                            y_max = ui.input(label="y_max", value="1").classes("w-24 font-mono")
                                            extra_controls["form"] = form_sel
                                            extra_controls["x_min"] = x_min
                                            extra_controls["x_max"] = x_max
                                            extra_controls["y_min"] = y_min
                                            extra_controls["y_max"] = y_max

                                # 11. Parameters for Stokes' Theorem
                                if current_op.problem_type == ProblemType.STOKES_THEOREM:
                                    with ui.column().classes("w-full gap-2 p-3.5 bg-slate-50 border border-slate-200 rounded-xl"):
                                        with ui.row().classes("items-center gap-2"):
                                            ui.icon("all_inclusive", size="1.1rem").classes("text-blue-700")
                                            ui.label("Mặt cong S và miền tham số D:").classes("text-xs font-bold text-slate-800 uppercase tracking-wider")
                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                            surf_in = ui.input(label="Mặt cong S: z = g(x, y)", value="0").classes("w-52 font-mono")
                                            x_min = ui.input(label="x_min", value="0").classes("w-24 font-mono")
                                            x_max = ui.input(label="x_max", value="1").classes("w-24 font-mono")
                                            y_min = ui.input(label="y_min", value="0").classes("w-24 font-mono")
                                            y_max = ui.input(label="y_max", value="1").classes("w-24 font-mono")
                                            extra_controls["surface_expr"] = surf_in
                                            extra_controls["x_min"] = x_min
                                            extra_controls["x_max"] = x_max
                                            extra_controls["y_min"] = y_min
                                            extra_controls["y_max"] = y_max

                                # 12. Parameters for Divergence Theorem
                                if current_op.problem_type == ProblemType.DIVERGENCE_THEOREM:
                                    with ui.column().classes("w-full gap-2 p-3.5 bg-slate-50 border border-slate-200 rounded-xl"):
                                        with ui.row().classes("items-center gap-2"):
                                            ui.icon("all_inclusive", size="1.1rem").classes("text-blue-700")
                                            ui.label("Cận khối hộp V [x_min, x_max] × [y_min, y_max] × [z_min, z_max]:").classes(
                                                "text-xs font-bold text-slate-800 uppercase tracking-wider"
                                            )
                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                            x_min = ui.input(label="x_min", value="0").classes("w-24 font-mono")
                                            x_max = ui.input(label="x_max", value="1").classes("w-24 font-mono")
                                            y_min = ui.input(label="y_min", value="0").classes("w-24 font-mono")
                                            y_max = ui.input(label="y_max", value="1").classes("w-24 font-mono")
                                            z_min = ui.input(label="z_min", value="0").classes("w-24 font-mono")
                                            z_max = ui.input(label="z_max", value="1").classes("w-24 font-mono")
                                            extra_controls["x_min"] = x_min
                                            extra_controls["x_max"] = x_max
                                            extra_controls["y_min"] = y_min
                                            extra_controls["y_max"] = y_max
                                            extra_controls["z_min"] = z_min
                                            extra_controls["z_max"] = z_max

                                # Parameters for Limits
                                if "limit_point" in current_op.extra_fields:
                                    with ui.column().classes("w-full p-3.5 bg-blue-50/50 border border-blue-200 rounded-xl gap-2"):
                                        with ui.row().classes("items-center gap-2"):
                                            ui.icon("trending_flat", size="1.1rem").classes("text-blue-700")
                                            ui.label("Điểm tiến tới & Hướng khảo sát giới hạn:").classes(
                                                "text-xs font-bold text-blue-950 uppercase tracking-wider"
                                            )
                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                            point_input = ui.input(label="Điểm tiến tới (a)", value="0").classes("w-36 font-mono")
                                            dir_select = ui.select(
                                                options=[
                                                    "+- (Hai phía) — x → a",
                                                    "+ (Bên phải) — x → a⁺",
                                                    "- (Bên trái) — x → a⁻",
                                                ],
                                                value="+- (Hai phía) — x → a",
                                                label="Hướng tiến tới",
                                            ).classes("w-56")
                                            extra_controls["limit_point"] = point_input
                                            extra_controls["direction"] = dir_select

                                        # Quick limit points toolbar
                                        with ui.row().classes("items-center gap-1.5 pt-0.5 flex-wrap"):
                                            ui.label("Điểm đặc biệt:").classes("text-xs text-slate-500 font-semibold")
                                            limit_presets = [("0", "0"), ("+∞", "oo"), ("-∞", "-oo"), ("1", "1")]
                                            for p_lbl, p_val in limit_presets:
                                                ui.chip(
                                                    p_lbl,
                                                    on_click=lambda _, v=p_val: point_input.set_value(v),
                                                ).classes(
                                                    "cursor-pointer hover:bg-blue-100 text-xs px-2.5 py-0.5 rounded-full font-mono bg-slate-100 border border-slate-200 text-slate-800 transition-colors"
                                                )

                            # Section C: Example Chips
                            if current_op.examples:
                                with ui.row().classes("items-center gap-2 pt-1 flex-wrap"):
                                    ui.label("Ví dụ mẫu:").classes("text-xs text-slate-500 font-semibold")
                                    for label, val in current_op.examples:
                                        ui.chip(
                                            label,
                                            on_click=lambda _, v=val: expr_input.set_value(v),
                                        ).classes(
                                            "cursor-pointer hover:bg-blue-100 text-xs px-2.5 py-0.5 rounded-full font-mono bg-slate-100 border border-slate-200 text-slate-800 transition-colors"
                                        )

                            # Section D: Primary Action & Reset
                            calc_button_label = "GIẢI PHƯƠNG TRÌNH" if is_calculus else "GIẢI PHÉP TOÁN MA TRẬN"
                            btn_icon = (
                                "calculate"
                                if current_op.problem_type == ProblemType.SOLVE_EQUATION
                                else ("grid_view" if is_matrix_op else "functions")
                            )

                            with ui.row().classes("w-full items-center justify-between pt-3 border-t border-slate-100 flex-wrap gap-2"):
                                def _handle_reset() -> None:
                                    # 1. Main expression
                                    expr_input.set_value(current_op.default_input)

                                    # 2. Target variable
                                    if "target_var" in extra_controls and hasattr(extra_controls["target_var"], "set_value"):
                                        extra_controls["target_var"].set_value(current_op.target_var)

                                    # 3. Number inputs (Order)
                                    if "order" in extra_controls and hasattr(extra_controls["order"], "set_value"):
                                        extra_controls["order"].set_value(1)

                                    # 4. Bounds for Definite Integral & Arc Length
                                    if "lower_bound" in extra_controls and hasattr(extra_controls["lower_bound"], "set_value"):
                                        extra_controls["lower_bound"].set_value("0")
                                    if "upper_bound" in extra_controls and hasattr(extra_controls["upper_bound"], "set_value"):
                                        default_upper = "3" if current_op.problem_type == ProblemType.ARC_LENGTH else "1"
                                        extra_controls["upper_bound"].set_value(default_upper)

                                    # 5. Limit point and direction
                                    if "limit_point" in extra_controls and hasattr(extra_controls["limit_point"], "set_value"):
                                        extra_controls["limit_point"].set_value("0")
                                    if "direction" in extra_controls and hasattr(extra_controls["direction"], "set_value"):
                                        extra_controls["direction"].set_value("+- (Hai phía) — x → a")

                                    # 6. Surface of revolution axis
                                    if "axis" in extra_controls and hasattr(extra_controls["axis"], "set_value"):
                                        extra_controls["axis"].set_value("Ox (y = 0)")

                                    # 7. Line Integral controls
                                    if "line_mode" in extra_controls and hasattr(extra_controls["line_mode"], "set_value"):
                                        extra_controls["line_mode"].set_value("Vô hướng (f ds)")
                                    if "param_var" in extra_controls and hasattr(extra_controls["param_var"], "set_value"):
                                        extra_controls["param_var"].set_value("t")
                                    if "t_min" in extra_controls and hasattr(extra_controls["t_min"], "set_value"):
                                        extra_controls["t_min"].set_value("0")
                                    if "t_max" in extra_controls and hasattr(extra_controls["t_max"], "set_value"):
                                        extra_controls["t_max"].set_value("1")
                                    if "param_x" in extra_controls and hasattr(extra_controls["param_x"], "set_value"):
                                        extra_controls["param_x"].set_value("3*t")
                                    if "param_y" in extra_controls and hasattr(extra_controls["param_y"], "set_value"):
                                        extra_controls["param_y"].set_value("4*t")
                                    if "param_z" in extra_controls and hasattr(extra_controls["param_z"], "set_value"):
                                        extra_controls["param_z"].set_value("0")

                                    # 8. Surface Integral controls
                                    if current_op.problem_type == ProblemType.SURFACE_INTEGRAL:
                                        if "surf_mode" in extra_controls and hasattr(extra_controls["surf_mode"], "set_value"):
                                            extra_controls["surf_mode"].set_value("Vô hướng (f dS)")
                                        if "orientation" in extra_controls and hasattr(extra_controls["orientation"], "set_value"):
                                            extra_controls["orientation"].set_value("Pháp tuyến hướng lên (Upward / +k)")

                                        # Explicitly restore existing bounds to defaults before rebuild so preservation logic reads defaults
                                        for k, def_v in (("u_min", "0"), ("u_max", "1"), ("v_min", "0"), ("v_max", "1")):
                                            if k in extra_controls and hasattr(extra_controls[k], "set_value"):
                                                extra_controls[k].set_value(def_v)

                                        # Revert geometry selector to Graph mode without redundant duplicate rebuild
                                        graph_mode_label = "Mặt đồ thị: z = g(x, y)"
                                        if "surface_type" in extra_controls and hasattr(extra_controls["surface_type"], "set_value"):
                                            if extra_controls["surface_type"].value != graph_mode_label:
                                                extra_controls["surface_type"].set_value(graph_mode_label)
                                                # set_value triggers on_value_change which invokes update_surf_geo_fields
                                            else:
                                                update_surf_geo_fields()
                                        else:
                                            update_surf_geo_fields()

                                        # Ensure Graph mode inputs are explicitly restored to defaults after rebuild
                                        for k, def_v in (("u_min", "0"), ("u_max", "1"), ("v_min", "0"), ("v_max", "1")):
                                            if k in extra_controls and hasattr(extra_controls[k], "set_value"):
                                                extra_controls[k].set_value(def_v)
                                        if "surface_expr" in extra_controls and hasattr(extra_controls["surface_expr"], "set_value"):
                                            extra_controls["surface_expr"].set_value("1 - x - y")

                                        # Purge any obsolete parametric controls
                                        extra_controls.pop("param_x", None)
                                        extra_controls.pop("param_y", None)
                                        extra_controls.pop("param_z", None)

                                    # 9. Orientation for Line / Surface integrals
                                    if "orientation" in extra_controls and hasattr(extra_controls["orientation"], "set_value"):
                                        if current_op.problem_type == ProblemType.SURFACE_INTEGRAL:
                                            extra_controls["orientation"].set_value("Pháp tuyến hướng lên (Upward / +k)")
                                        else:
                                            extra_controls["orientation"].set_value("Hướng thuận (+t)")

                                    # 10. Triple Integral controls
                                    if current_op.problem_type == ProblemType.TRIPLE_INTEGRAL:
                                        if "coord_system" in extra_controls and hasattr(extra_controls["coord_system"], "set_value"):
                                            extra_controls["coord_system"].set_value("Tọa độ Descartes (x, y, z)")
                                        update_triple_bounds()

                                    # 11. Surface Area
                                    if current_op.problem_type == ProblemType.SURFACE_AREA:
                                        if "u_min" in extra_controls and hasattr(extra_controls["u_min"], "set_value"):
                                            extra_controls["u_min"].set_value("0")
                                        if "u_max" in extra_controls and hasattr(extra_controls["u_max"], "set_value"):
                                            extra_controls["u_max"].set_value("1")
                                        if "v_min" in extra_controls and hasattr(extra_controls["v_min"], "set_value"):
                                            extra_controls["v_min"].set_value("0")
                                        if "v_max" in extra_controls and hasattr(extra_controls["v_max"], "set_value"):
                                            extra_controls["v_max"].set_value("1")

                                    # 12. Green's Theorem
                                    if current_op.problem_type == ProblemType.GREENS_THEOREM:
                                        if "form" in extra_controls and hasattr(extra_controls["form"], "set_value"):
                                            extra_controls["form"].set_value("Lưu thông (Circulation)")
                                        if "x_min" in extra_controls and hasattr(extra_controls["x_min"], "set_value"):
                                            extra_controls["x_min"].set_value("0")
                                        if "x_max" in extra_controls and hasattr(extra_controls["x_max"], "set_value"):
                                            extra_controls["x_max"].set_value("1")
                                        if "y_min" in extra_controls and hasattr(extra_controls["y_min"], "set_value"):
                                            extra_controls["y_min"].set_value("0")
                                        if "y_max" in extra_controls and hasattr(extra_controls["y_max"], "set_value"):
                                            extra_controls["y_max"].set_value("1")

                                    # 13. Stokes' Theorem
                                    if current_op.problem_type == ProblemType.STOKES_THEOREM:
                                        if "surface_expr" in extra_controls and hasattr(extra_controls["surface_expr"], "set_value"):
                                            extra_controls["surface_expr"].set_value("0")
                                        if "x_min" in extra_controls and hasattr(extra_controls["x_min"], "set_value"):
                                            extra_controls["x_min"].set_value("0")
                                        if "x_max" in extra_controls and hasattr(extra_controls["x_max"], "set_value"):
                                            extra_controls["x_max"].set_value("1")
                                        if "y_min" in extra_controls and hasattr(extra_controls["y_min"], "set_value"):
                                            extra_controls["y_min"].set_value("0")
                                        if "y_max" in extra_controls and hasattr(extra_controls["y_max"], "set_value"):
                                            extra_controls["y_max"].set_value("1")

                                    # 14. Divergence Theorem
                                    if current_op.problem_type == ProblemType.DIVERGENCE_THEOREM:
                                        if "x_min" in extra_controls and hasattr(extra_controls["x_min"], "set_value"):
                                            extra_controls["x_min"].set_value("0")
                                        if "x_max" in extra_controls and hasattr(extra_controls["x_max"], "set_value"):
                                            extra_controls["x_max"].set_value("1")
                                        if "y_min" in extra_controls and hasattr(extra_controls["y_min"], "set_value"):
                                            extra_controls["y_min"].set_value("0")
                                        if "y_max" in extra_controls and hasattr(extra_controls["y_max"], "set_value"):
                                            extra_controls["y_max"].set_value("1")
                                        if "z_min" in extra_controls and hasattr(extra_controls["z_min"], "set_value"):
                                            extra_controls["z_min"].set_value("0")
                                        if "z_max" in extra_controls and hasattr(extra_controls["z_max"], "set_value"):
                                            extra_controls["z_max"].set_value("1")

                                    # 15. Optional ODE controls
                                    if "initial_condition" in extra_controls and hasattr(extra_controls["initial_condition"], "set_value"):
                                        extra_controls["initial_condition"].set_value("")
                                    if "y1" in extra_controls and hasattr(extra_controls["y1"], "set_value"):
                                        extra_controls["y1"].set_value("")

                                    # 16. Clear results container
                                    results_container.clear()

                                ui.button("Nhập lại", icon="refresh", on_click=_handle_reset).props("flat dense no-caps").classes(
                                    "text-xs text-slate-500 font-semibold hover:text-slate-800"
                                )
                                solve_button = primary_button(
                                    text=calc_button_label,
                                    icon=btn_icon,
                                )

                        # Results & Analysis Container for generic operations
                        results_container = ui.column().classes("w-full gap-5")

                        # Submission handler with debounce flag
                        is_submitting = False

                        async def handle_submit() -> None:
                            nonlocal is_submitting
                            if is_submitting:
                                return
                            is_submitting = True
                            try:
                                results_container.clear()
                                raw_val = expr_input.value.strip()

                                if not raw_val:
                                    with results_container:
                                        with ui.card().classes("w-full p-4 border border-amber-200 bg-amber-50 text-amber-900 rounded-xl"):
                                            with ui.row().classes("items-center gap-2"):
                                                ui.icon("warning", color="warning")
                                                ui.label("Dữ liệu không được để trống. Vui lòng nhập dữ liệu trước khi thực hiện.").classes("text-sm font-semibold")
                                    return

                                # Loading indicator
                                with results_container:
                                    with ui.card().classes("w-full p-6 border border-slate-200 bg-white rounded-xl shadow-xs text-center items-center justify-center"):
                                        ui.spinner("dots", size="2.5rem", color="primary")
                                        ui.label("Đang giải toán và thực hiện kiểm định độc lập...").classes("text-sm font-medium text-slate-600 mt-2")

                                # Request parameters
                                params: dict[str, Any] = {}
                                target_var = "x"

                                if not is_matrix_op and "target_var" in extra_controls:
                                    target_var = extra_controls["target_var"].value.strip() or "x"

                                # Dynamic parameter extraction from extra_controls
                                for key, ctrl in extra_controls.items():
                                    if hasattr(ctrl, "value"):
                                        v = ctrl.value
                                        if key == "line_mode":
                                            params["mode"] = "vector" if "vector" in str(v).lower() or "f·dr" in str(v).lower() else "scalar"
                                        elif key == "surf_mode":
                                            params["mode"] = "vector" if "vector" in str(v).lower() or "thông lượng" in str(v).lower() or "f·n" in str(v).lower() else "scalar"
                                        elif key == "surface_type":
                                            params["surface_type"] = "parametric" if "tham số" in str(v).lower() or "parametric" in str(v).lower() else "explicit"
                                        elif key == "coord_system":
                                            c_str = str(v).lower()
                                            if "trụ" in c_str or "cylindrical" in c_str:
                                                params["coord_system"] = "cylindrical"
                                            elif "cầu" in c_str or "spherical" in c_str:
                                                params["coord_system"] = "spherical"
                                            else:
                                                params["coord_system"] = "cartesian"
                                        elif key == "orientation":
                                            o_str = str(v).lower()
                                            if current_op.problem_type == ProblemType.SURFACE_INTEGRAL:
                                                params["orientation"] = "downward" if "xuống" in o_str or "down" in o_str or "-" in o_str else "upward"
                                            else:
                                                params["orientation"] = "backward" if "nghịch" in o_str or "back" in o_str or "-" in o_str else "forward"
                                        elif key == "axis":
                                            params["axis"] = "x" if "Ox" in str(v) else "y"
                                        elif key == "form":
                                            params["form"] = "flux" if "flux" in str(v).lower() or "thông lượng" in str(v).lower() else "circulation"
                                        elif key == "direction":
                                            val_str = str(v).strip()
                                            if val_str in ("+", "-", "+-"):
                                                params["direction"] = val_str
                                            elif "a⁺" in val_str or ("+" in val_str and "+-" not in val_str):
                                                params["direction"] = "+"
                                            elif "a⁻" in val_str or ("-" in val_str and "+-" not in val_str):
                                                params["direction"] = "-"
                                            else:
                                                params["direction"] = "+-"
                                        elif key == "limit_point":
                                            lp = str(v).strip()
                                            if lp in ("+\\infty", "+∞", "\\infty", "∞", "+oo"):
                                                params["limit_point"] = "oo"
                                            elif lp in ("-\\infty", "-∞", "-oo"):
                                                params["limit_point"] = "-oo"
                                            else:
                                                params["limit_point"] = lp
                                        elif key == "order":
                                            try:
                                                params["order"] = max(1, int(v or 1))
                                            except (ValueError, TypeError):
                                                params["order"] = 1
                                        elif key != "target_var":
                                            params[key] = str(v).strip()
                                    elif isinstance(ctrl, str):
                                        params[key] = ctrl

                                # Explicit parameter ownership enforcement to guarantee zero state leakage
                                if current_op.problem_type == ProblemType.SURFACE_INTEGRAL:
                                    if params.get("surface_type") == "parametric":
                                        params.pop("surface_expr", None)
                                    else:
                                        params.pop("param_x", None)
                                        params.pop("param_y", None)
                                        params.pop("param_z", None)
                                elif current_op.problem_type == ProblemType.TRIPLE_INTEGRAL:
                                    coord_sys = params.get("coord_system", "cartesian")
                                    if coord_sys == "cylindrical":
                                        for obsolete_k in ("x_min", "x_max", "y_min", "y_max", "phi_min", "phi_max", "rho_min", "rho_max"):
                                            params.pop(obsolete_k, None)
                                    elif coord_sys == "spherical":
                                        for obsolete_k in ("x_min", "x_max", "y_min", "y_max", "z_min", "z_max", "r_min", "r_max"):
                                            params.pop(obsolete_k, None)
                                    else:  # cartesian
                                        for obsolete_k in ("th_min", "th_max", "r_min", "r_max", "phi_min", "phi_max", "rho_min", "rho_max"):
                                            params.pop(obsolete_k, None)

                                request = ProblemRequest(
                                    raw_input=raw_val,
                                    problem_type=current_op.problem_type,
                                    target_variable=target_var,
                                    parameters=params,
                                )

                                try:
                                    response: SolutionResponse = await asyncio.to_thread(use_case.execute, request, 8.0)
                                except Exception as exc:
                                    results_container.clear()
                                    with results_container:
                                        with ui.card().classes("w-full p-4 border border-red-200 bg-red-50 text-red-900 rounded-xl"):
                                            with ui.row().classes("items-center gap-2"):
                                                ui.icon("error", color="negative")
                                                ui.label(f"Lỗi thực thi hệ thống: {exc}").classes("text-sm font-semibold")
                                    return

                                results_container.clear()
                                with results_container:
                                    render_solution_view(response, current_op, target_var, params)
                            finally:
                                is_submitting = False

                        solve_button.on_click(handle_submit)
                        expr_input.on("keydown.enter", handle_submit)
                        expr_input.on("input", lambda: results_container.clear())

                        # Support Enter key submission on all parameter controls
                        for ctrl in extra_controls.values():
                            if hasattr(ctrl, "on"):
                                ctrl.on("keydown.enter", handle_submit)

            # Initial Render
            render_current_screen()

            # Shared Application Footer
            render_footer()

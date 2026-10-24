"""Main NiceGUI application page and state coordinator."""

from __future__ import annotations

import asyncio
from typing import Any
from nicegui import ui

from math_app import __title__, __version__
from math_app.application.dtos import ProblemRequest, SolutionResponse
from math_app.application.use_cases.solve_problem import SolveProblemUseCase
from math_app.domain.models import ProblemType
from math_app.presentation.components.back_button import render_back_button
from math_app.presentation.components.footer import AUTHOR_CREDIT, render_footer
from math_app.presentation.components.math_view import ui_math
from math_app.presentation.components.operation_catalog import (
    MAIN_OPERATIONS,
    OPERATIONS,
    OperationDef,
    get_operation_by_type,
)
from math_app.presentation.components.solution_view import render_solution_view


def create_app(use_case: SolveProblemUseCase) -> None:
    """Configure the NiceGUI page layout and interaction handlers."""

    @ui.page("/")
    def main_page() -> None:
        ui.page_title(f"{__title__} — Phần mềm Học tập & Nghiên cứu Toán học")

        # Inject global styles for typography and MathML rendering without scrollbar artifacts
        ui.add_head_html("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
            @import url('https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css');
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background-color: #f8fafc;
                color: #0f172a;
            }
            math {
                font-family: 'KaTeX_Math', 'Latin Modern Math', 'STIX Two Math', 'Cambria Math', 'Times New Roman', serif;
                font-size: 1.15em;
                letter-spacing: 0.02em;
            }
            .math-container {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                vertical-align: middle;
                overflow: visible !important;
                max-width: 100%;
                line-height: normal;
            }
            .math-icon {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                overflow: visible !important;
                pointer-events: none;
                user-select: none;
                max-width: 100%;
                max-height: 100%;
                line-height: normal;
            }
            .math-icon math {
                font-size: 0.88em;
            }
            math mtable, mtable {
                border-spacing: 0.85em 0.35em !important;
                border-collapse: separate !important;
            }
            math mtd, mtd {
                padding: 0.15em 0.45em !important;
                text-align: center !important;
            }
            .math-block {
                display: flex;
                justify-content: flex-start;
                align-items: center;
                margin: 0.25rem 0;
                overflow-x: auto;
                overflow-y: hidden !important;
                max-width: 100%;
                padding: 0.35rem 0.5rem;
                scrollbar-width: thin;
                scrollbar-color: #cbd5e1 transparent;
            }
            /* Eliminate native browser scrollbar stepper arrows and customize scrollbar track */
            *::-webkit-scrollbar-button,
            .math-container::-webkit-scrollbar-button,
            .math-block::-webkit-scrollbar-button,
            math::-webkit-scrollbar-button {
                display: none !important;
                width: 0 !important;
                height: 0 !important;
            }
            .math-container::-webkit-scrollbar,
            .math-block::-webkit-scrollbar,
            math::-webkit-scrollbar {
                height: 4px;
                width: 4px;
            }
            .math-container::-webkit-scrollbar-thumb,
            .math-block::-webkit-scrollbar-thumb,
            math::-webkit-scrollbar-thumb {
                background-color: #cbd5e1;
                border-radius: 4px;
            }
        </style>
        """)

        # Application state
        current_op: OperationDef = OPERATIONS[0]
        active_screen = "SCREEN_A"  # "SCREEN_A" (Catalog) or "SCREEN_B" (Problem Solving)

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
        page_col = ui.column().classes("w-full max-w-6xl mx-auto p-4 md:p-6 gap-6 min-h-screen flex flex-col justify-between")

        with page_col:
            # Global Header
            with ui.row().classes("items-center justify-between w-full border-b border-slate-200 pb-4"):
                with ui.row().classes("items-center gap-3"):
                    with ui.avatar(icon="functions", color="primary", text_color="white").classes("shadow-sm"):
                        pass
                    with ui.column().classes("gap-0"):
                        ui.label(__title__).classes("text-2xl font-black text-slate-900 tracking-tight")
                        ui.label("Phần mềm Hỗ trợ Học tập & Nghiên cứu Toán học Chuyên sâu").classes("text-xs text-slate-500 font-medium")
                with ui.row().classes("items-center gap-2"):
                    with ui.badge(f"MVP · v{__version__}", color="blue-grey-7").classes(
                        "text-xs px-2.5 py-1 rounded-full cursor-pointer hover:bg-slate-600 transition-colors"
                    ).on("click", lambda: open_about_dialog()):
                        ui.tooltip("Thông tin ứng dụng (About)")

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
                current_op = op
                active_screen = "SCREEN_B"
                render_current_screen()

            def switch_to_catalog() -> None:
                nonlocal active_screen
                active_screen = "SCREEN_A"
                render_current_screen()

            # ================= SCREEN A: OPERATION CATALOG =================
            def render_screen_a() -> None:
                with ui.column().classes("w-full gap-5"):
                    # Main Heading: Exact wording requested, without descriptive subtitle below
                    with ui.row().classes("w-full items-center justify-between pt-1 pb-2 border-b border-slate-100"):
                        ui.label("Chọn dạng toán cần giải quyết").classes("text-xl md:text-2xl font-black text-slate-900 tracking-tight")

                    domains = [
                        "Giải tích (Calculus)",
                        "Giải tích vectơ (Vector Calculus)",
                        "Đại số tuyến tính (Linear Algebra)",
                    ]
                    for dom in domains:
                        domain_ops = [o for o in MAIN_OPERATIONS if o.domain == dom]
                        with ui.column().classes("w-full gap-3 mt-1"):
                            with ui.row().classes("items-center gap-2"):
                                if "Giải tích vectơ" in dom:
                                    domain_icon = "all_inclusive"
                                elif "Giải tích" in dom:
                                    domain_icon = "query_stats"
                                else:
                                    domain_icon = "grid_view"
                                ui.icon(domain_icon, size="1.3rem").classes("text-blue-600")
                                ui.label(dom).classes("text-sm md:text-base font-bold text-slate-800 uppercase tracking-wider")
                                ui.badge(f"{len(domain_ops)} dạng toán", color="slate-200").classes("text-xs text-slate-700 font-semibold rounded-md px-2")

                            with ui.grid().classes("grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 w-full"):
                                for op in domain_ops:
                                    with ui.card().classes(
                                        "p-4 border border-slate-200 hover:border-blue-500 hover:shadow-md transition-all "
                                        "cursor-pointer rounded-xl bg-white flex flex-col justify-between group h-full"
                                    ).on("click", lambda _, selected_op=op: switch_to_operation(selected_op)):
                                        with ui.column().classes("gap-2.5 w-full flex-grow"):
                                            # Header Row: Icon (Left) + Title (Immediately beside icon) + Navigation Arrow (Far right)
                                            with ui.row().classes("items-center justify-between w-full gap-2.5"):
                                                with ui.row().classes("items-center gap-2.5 flex-1 min-w-0"):
                                                    if op.math_icon:
                                                        with ui.row().classes(
                                                            "min-w-[3.25rem] h-12 px-2 shrink-0 rounded-lg bg-blue-50 text-blue-700 items-center justify-center "
                                                            "group-hover:bg-blue-600 group-hover:text-white transition-colors overflow-visible"
                                                        ):
                                                            ui_math(op.math_icon, block=False, classes="math-icon font-bold select-none pointer-events-none", is_icon=True)
                                                    else:
                                                        with ui.avatar(icon=op.icon, color="blue-50", text_color="blue-700", size="md").classes(
                                                            "shrink-0 group-hover:bg-blue-600 group-hover:text-white transition-colors"
                                                        ):
                                                            pass

                                                    ui.label(op.title).classes("font-bold text-slate-800 text-sm md:text-base group-hover:text-blue-700 leading-snug flex-1 break-words")

                                                ui.icon("arrow_forward", size="1.2rem").classes("text-slate-300 group-hover:text-blue-600 transition-colors shrink-0 self-center")

                                            # Description remains below header
                                            ui.label(op.description).classes("text-xs text-slate-500 leading-relaxed mt-0.5")

                                        # Card Action: "Chọn →" aligned without example line and divider
                                        with ui.row().classes("w-full justify-end items-center pt-2 text-xs"):
                                            ui.label("Chọn →").classes("text-blue-600 font-semibold group-hover:translate-x-0.5 transition-transform shrink-0")

            # ================= SCREEN B: PROBLEM SOLVING & RESULTS =================
            def render_screen_b() -> None:
                is_calculus = current_op.is_calculus
                is_matrix_op = current_op.is_matrix

                with ui.column().classes("w-full gap-5"):
                    # Navigation Bar with Shared High-Contrast Back Button
                    with ui.row().classes("w-full items-center justify-between bg-white p-3 rounded-xl border border-slate-200 shadow-xs"):
                        with ui.row().classes("items-center gap-3"):
                            render_back_button(on_click=switch_to_catalog)
                            ui.separator().props("vertical")

                            with ui.row().classes("items-center gap-2"):
                                if current_op.math_icon:
                                    with ui.row().classes("px-3 py-1.5 min-w-[3rem] rounded-lg bg-blue-50 text-blue-800 items-center justify-center overflow-visible"):
                                        ui_math(current_op.math_icon, block=False, classes="math-icon text-base font-bold select-none pointer-events-none", is_icon=True)
                                else:
                                    ui.icon(current_op.icon, size="1.3rem").classes("text-blue-600")

                                display_title = current_op.title
                                if current_op.problem_type == ProblemType.DEFINITE_INTEGRAL:
                                    display_title = "Tích phân xác định (Một biến)"
                                elif current_op.problem_type == ProblemType.TRIPLE_INTEGRAL:
                                    display_title = "Tích phân khối"
                                ui.label(display_title).classes("font-bold text-slate-900 text-sm md:text-base")

                        ui.badge(current_op.domain, color="blue-1").classes("text-blue-800 text-xs px-2.5 py-1 rounded-full hidden sm:inline-flex")

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

                    # Dynamic Input Form Card
                    with ui.card().classes("w-full p-5 shadow-xs border border-slate-200 rounded-xl bg-white gap-4"):
                        with ui.column().classes("gap-0.5"):
                            ui.label("Nhập dữ liệu bài toán").classes("text-base font-bold text-slate-900")
                            ui.label(current_op.description).classes("text-xs text-slate-500")

                        # Dynamic Form Inputs
                        form_container = ui.column().classes("w-full gap-3")
                        extra_controls: dict[str, Any] = {}

                        with form_container:
                            # 1. Main mathematical expression or matrix input
                            if is_matrix_op:
                                main_input_label = "Dữ liệu ma trận A"
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

                            expr_input = ui.input(
                                label=main_input_label,
                                placeholder=current_op.default_input,
                                value=current_op.default_input,
                            ).classes("w-full text-base font-mono")

                            # 2. Derivative-specific repositioned order field
                            if current_op.problem_type == ProblemType.DERIVATIVE:
                                with ui.row().classes("items-center gap-3"):
                                    order_input = ui.number(
                                        label="Cấp đạo hàm (n)",
                                        value=1,
                                        min=1,
                                        max=10,
                                        step=1,
                                    ).classes("w-40 text-base")
                                    extra_controls["order"] = order_input
                                    ui.label("(n = 1: Đạo hàm bậc 1; n ≥ 2: Đạo hàm cấp cao)").classes("text-xs text-slate-400 self-center pt-2")

                            # 3. Differentiation variable input and "Chọn biến" grouped controls
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
                                    var_input = ui.input(
                                        label="Biến vi phân / biến số",
                                        value=current_op.target_var,
                                    ).classes("w-36 text-base font-mono")
                                    extra_controls["target_var"] = var_input

                                    # Grouped Variable Selection
                                    with ui.column().classes("w-full p-3 bg-slate-50 border border-slate-200 rounded-xl gap-2"):
                                        ui.label("Chọn biến:").classes("text-xs font-bold text-slate-600 uppercase tracking-wider")

                                        with ui.row().classes("items-center gap-2 flex-wrap"):
                                            ui.label("Tọa độ Descartes:").classes("text-xs text-slate-400 font-medium w-28")
                                            for v in ("x", "y", "z", "t", "u", "v"):
                                                ui.chip(
                                                    v,
                                                    on_click=lambda _, val=v: var_input.set_value(val),
                                                ).classes("cursor-pointer text-xs px-2.5 py-0.5 bg-white border border-slate-200 hover:bg-blue-100 font-mono")

                                        with ui.row().classes("items-center gap-2 flex-wrap"):
                                            ui.label("Tọa độ cực/trụ:").classes("text-xs text-slate-400 font-medium w-28")
                                            for v in ("r", "θ", "z"):
                                                ui.chip(
                                                    v,
                                                    on_click=lambda _, val=v: var_input.set_value(val),
                                                ).classes("cursor-pointer text-xs px-2.5 py-0.5 bg-white border border-slate-200 hover:bg-blue-100 font-mono")

                                        with ui.row().classes("items-center gap-2 flex-wrap"):
                                            ui.label("Tọa độ cầu:").classes("text-xs text-slate-400 font-medium w-28")
                                            for v in ("ρ", "θ", "φ"):
                                                ui.chip(
                                                    v,
                                                    on_click=lambda _, val=v: var_input.set_value(val),
                                                ).classes("cursor-pointer text-xs px-2.5 py-0.5 bg-white border border-slate-200 hover:bg-blue-100 font-mono")

                            # 4. Parameters for Definite Integrals & Arc Length
                            if current_op.problem_type in (ProblemType.DEFINITE_INTEGRAL, ProblemType.ARC_LENGTH):
                                with ui.row().classes("items-center gap-3"):
                                    lower_input = ui.input(label="Cận dưới (a)", value="0").classes("w-32 font-mono")
                                    upper_input = ui.input(label="Cận trên (b)", value="1" if current_op.problem_type == ProblemType.DEFINITE_INTEGRAL else "3").classes("w-32 font-mono")
                                    extra_controls["lower_bound"] = lower_input
                                    extra_controls["upper_bound"] = upper_input

                            # 5. Parameters for Line Integrals
                            if current_op.problem_type == ProblemType.LINE_INTEGRAL:
                                with ui.column().classes("w-full gap-3 p-3.5 bg-slate-50 border border-slate-200 rounded-xl"):
                                    ui.label("Cấu hình kiểu tích phân đường & Định hướng:").classes("text-xs font-bold text-slate-700 uppercase tracking-wider")
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

                                    ui.label("Tham số hóa đường cong C: r(t) = (x(t), y(t), z(t)):").classes("text-xs font-bold text-slate-700 uppercase tracking-wider mt-1")
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
                                with ui.column().classes("w-full gap-3 p-3.5 bg-slate-50 border border-slate-200 rounded-xl"):
                                    ui.label("Kiểu tích phân mặt & Định hướng pháp tuyến:").classes("text-xs font-bold text-slate-700 uppercase tracking-wider")
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
                                                if is_param:
                                                    ui.label("Tham số hóa mặt cong S: r(u, v) = (x(u,v), y(u,v), z(u,v)):").classes("text-xs font-bold text-slate-700 uppercase tracking-wider")
                                                    with ui.row().classes("items-center gap-3 flex-wrap"):
                                                        px = ui.input(label="x(u, v)", value="u").classes("w-32 font-mono")
                                                        py = ui.input(label="y(u, v)", value="v").classes("w-32 font-mono")
                                                        pz = ui.input(label="z(u, v)", value="1 - u - v").classes("w-36 font-mono")
                                                        extra_controls["param_x"] = px
                                                        extra_controls["param_y"] = py
                                                        extra_controls["param_z"] = pz
                                                    with ui.row().classes("items-center gap-3 flex-wrap"):
                                                        u_var = ui.input(label="Biến u", value="u").classes("w-20 font-mono")
                                                        u_min = ui.input(label="u_min", value="0").classes("w-24 font-mono")
                                                        u_max = ui.input(label="u_max", value="1").classes("w-24 font-mono")
                                                        v_var = ui.input(label="Biến v", value="v").classes("w-20 font-mono")
                                                        v_min = ui.input(label="v_min", value="0").classes("w-24 font-mono")
                                                        v_max = ui.input(label="v_max", value="1").classes("w-24 font-mono")
                                                        extra_controls["u_var"] = u_var
                                                        extra_controls["u_min"] = u_min
                                                        extra_controls["u_max"] = u_max
                                                        extra_controls["v_var"] = v_var
                                                        extra_controls["v_min"] = v_min
                                                        extra_controls["v_max"] = v_max
                                                else:
                                                    extra_controls.pop("param_x", None)
                                                    extra_controls.pop("param_y", None)
                                                    extra_controls.pop("param_z", None)
                                                    ui.label("Phương trình mặt cong và miền chữ nhật D [x_min, x_max] × [y_min, y_max]:").classes("text-xs font-bold text-slate-700 uppercase tracking-wider")
                                                    with ui.row().classes("items-center gap-3 flex-wrap"):
                                                        surf_expr = ui.input(label="Phương trình mặt: z = g(x, y)", value="1 - x - y").classes("w-64 font-mono")
                                                        extra_controls["surface_expr"] = surf_expr
                                                    with ui.row().classes("items-center gap-3 flex-wrap"):
                                                        u_min = ui.input(label="x_min", value="0").classes("w-24 font-mono")
                                                        u_max = ui.input(label="x_max", value="1").classes("w-24 font-mono")
                                                        v_min = ui.input(label="y_min", value="0").classes("w-24 font-mono")
                                                        v_max = ui.input(label="y_max", value="1").classes("w-24 font-mono")
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
                                with ui.column().classes("w-full gap-3 p-3.5 bg-slate-50 border border-slate-200 rounded-xl"):
                                    ui.label("Hệ tọa độ không gian 3D:").classes("text-xs font-bold text-slate-700 uppercase tracking-wider")
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
                                            triple_bounds_box.clear()
                                            with triple_bounds_box:
                                                c_val = str(coord_sel.value).lower()
                                                if "trụ" in c_val or "cylindrical" in c_val:
                                                    ui.label("Cận tọa độ trụ [θ_min, θ_max] × [r_min, r_max] × [z_min, z_max] (dV = r dz dr dθ):").classes("text-xs font-bold text-slate-700 uppercase tracking-wider")
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
                                                    ui.label("Cận tọa độ cầu [θ_min, θ_max] × [φ_min, φ_max] × [ρ_min, ρ_max] (dV = ρ² sin(φ) dρ dφ dθ):").classes("text-xs font-bold text-slate-700 uppercase tracking-wider")
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
                                                    ui.label("Cận khối hộp V [x_min, x_max] × [y_min, y_max] × [z_min, z_max] (dV = dz dy dx):").classes("text-xs font-bold text-slate-700 uppercase tracking-wider")
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
                                with ui.row().classes("items-center gap-3 flex-wrap"):
                                    axis_sel = ui.select(options=["Ox (y = 0)", "Oy (x = 0)"], value="Ox (y = 0)", label="Trục quay").classes("w-40 text-sm")
                                    a_in = ui.input(label="Cận dưới (a)", value="0").classes("w-32 font-mono")
                                    b_in = ui.input(label="Cận trên (b)", value="1").classes("w-32 font-mono")
                                    extra_controls["axis"] = axis_sel
                                    extra_controls["lower_bound"] = a_in
                                    extra_controls["upper_bound"] = b_in

                            # 10. Parameters for Green's Theorem
                            if current_op.problem_type == ProblemType.GREENS_THEOREM:
                                with ui.column().classes("w-full gap-2 p-3 bg-slate-50 border border-slate-200 rounded-xl"):
                                    ui.label("Dạng định lý và miền chữ nhật D:").classes("text-xs font-bold text-slate-700 uppercase tracking-wider")
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
                                with ui.column().classes("w-full gap-2 p-3 bg-slate-50 border border-slate-200 rounded-xl"):
                                    ui.label("Mặt cong S và miền tham số D:").classes("text-xs font-bold text-slate-700 uppercase tracking-wider")
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
                                with ui.column().classes("w-full gap-2 p-3 bg-slate-50 border border-slate-200 rounded-xl"):
                                    ui.label("Cận khối hộp V:").classes("text-xs font-bold text-slate-700 uppercase tracking-wider")
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
                                with ui.row().classes("items-center gap-3"):
                                    point_input = ui.input(label="Điểm tiến tới (a)", value="0").classes("w-32 font-mono")
                                    dir_select = ui.select(
                                        options=["+- (Hai phía)", "+ (Bên phải)", "- (Bên trái)"],
                                        value="+- (Hai phía)",
                                        label="Hướng tiến tới",
                                    ).classes("w-44")
                                    extra_controls["limit_point"] = point_input
                                    extra_controls["direction"] = dir_select

                            # Helper text for binary matrix operations
                            if is_matrix_op and current_op.problem_type in {
                                ProblemType.MATRIX_ADD_SUB,
                                ProblemType.MATRIX_MULTIPLY,
                                ProblemType.MATRIX_SOLVE_SYSTEM,
                            }:
                                ui.label("Nhập trực tiếp định dạng A + B, A - B, A * B hoặc A = b").classes("text-xs text-slate-400 italic")

                        # 6. Example Chips
                        if current_op.examples:
                            with ui.row().classes("items-center gap-2 mt-1 flex-wrap"):
                                ui.label("Ví dụ mẫu:").classes("text-xs text-slate-500 font-semibold")
                                for label, val in current_op.examples:
                                    ui.chip(label, on_click=lambda _, v=val: expr_input.set_value(v)).classes(
                                        "cursor-pointer hover:bg-blue-100 text-xs px-2.5 py-0.5 rounded-full"
                                    )

                        # 7. Primary Action Button
                        calc_button_label = "GIẢI PHƯƠNG TRÌNH" if is_calculus else "GIẢI PHÉP TOÁN MA TRẬN"
                        with ui.row().classes("w-full justify-end pt-2"):
                            solve_button = ui.button(
                                calc_button_label,
                                icon="calculate" if is_calculus else "grid_on",
                                color="primary",
                            ).classes("px-7 py-2.5 text-base font-bold shadow-md rounded-xl")

                    # Results & Analysis Container
                    results_container = ui.column().classes("w-full gap-4")

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
                                        params["direction"] = "+" if "+" in str(v) and "+-" not in str(v) else ("-" if "-" in str(v) and "+-" not in str(v) else "+-")
                                    elif key == "order":
                                        try:
                                            params["order"] = max(1, int(v or 1))
                                        except (ValueError, TypeError):
                                            params["order"] = 1
                                    elif key != "target_var":
                                        params[key] = str(v).strip()
                                elif isinstance(ctrl, str):
                                    params[key] = ctrl

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

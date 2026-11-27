"""Solution display view component for MathWeave Studio."""

from __future__ import annotations

from typing import Any
from nicegui import ui

from math_app.application.dtos import BranchSolution, SolutionResponse
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.input.parser import parse_mathematical_input, parse_safe_expression
from math_app.presentation.components.domain_view import render_domain_restrictions
from math_app.presentation.components.math_view import ui_math, ui_math_text
from math_app.presentation.components.operation_catalog import (
    OperationDef,
)
from math_app.presentation.design_system.tokens import INTERACTION
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


def _filter_ui_warnings(warnings: tuple[str, ...] | list[str]) -> list[str]:
    """Filter out obsolete or contradictory legacy limitations and sanitize internal identifiers."""
    filtered: list[str] = []
    for w in warnings:
        if "Chức năng giải không thuần nhất sẽ được nâng cấp toàn diện trong phiên bản tiếp theo" in w:
            continue
        cleaned_w = w
        # Sanitize internal parser identifiers so ordinary users never see raw internal tokens
        if "y_double_prime" in cleaned_w:
            cleaned_w = cleaned_w.replace("'y_double_prime'", "đạo hàm cấp 2 y''").replace("y_double_prime", "y''")
        if "y_higher_prime" in cleaned_w:
            cleaned_w = cleaned_w.replace("'y_higher_prime'", "đạo hàm cấp cao").replace(
                "y_higher_prime", "đạo hàm cấp cao"
            )
        if "y_prime" in cleaned_w:
            cleaned_w = cleaned_w.replace("'y_prime'", "đạo hàm cấp 1 y'").replace("y_prime", "y'")
        filtered.append(cleaned_w)
    return filtered


def _compute_approximate_roots(raw_input: str, target_var: str = "x") -> str | None:
    """Compute clean numerical approximations for polynomial equation roots when beneficial."""
    try:
        import sympy as sp

        clean_input = raw_input.strip()
        lhs_str = clean_input.split("=")[0].strip() if "=" in clean_input else clean_input
        rhs_str = clean_input.split("=")[1].strip() if "=" in clean_input else "0"
        var = sp.Symbol(target_var)
        lhs_expr, _ = parse_mathematical_input(lhs_str, target_var)
        rhs_expr, _ = parse_mathematical_input(rhs_str, target_var)
        eq_poly = sp.Poly(sp.expand(lhs_expr - rhs_expr), var)
        degree = eq_poly.degree()
        if degree < 2:
            return None
        roots = sp.solve(eq_poly.as_expr(), var)
        if not roots or len(roots) < 2:
            return None
        if all(r.is_integer for r in roots):
            return None
        approx_parts = []
        for idx, r in enumerate(roots, 1):
            val = complex(r.evalf())
            if abs(val.imag) < 1e-9:
                approx_parts.append(f"{target_var}_{{{idx}}} \\approx {val.real:.4f}")
            else:
                sign = "+" if val.imag >= 0 else "-"
                approx_parts.append(f"{target_var}_{{{idx}}} \\approx {val.real:.4f} {sign} {abs(val.imag):.4f}i")
        return ", \\quad ".join(approx_parts)
    except Exception:
        return None


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
        tool_table = prob_type in {
            ProblemType.DERIVATIVE,
            ProblemType.HIGHER_ORDER_DERIVATIVE,
            ProblemType.INDEFINITE_INTEGRAL,
            ProblemType.INTEGRAL,
        } and can_compute_variation_table(raw_input, target_var)
    except Exception:
        tool_table = False

    return tool_2d, tool_3d, tool_table


def render_ode_classification_card(
    response: SolutionResponse,
    prob_type: ProblemType,
    params: dict[str, Any] | None = None,
    target_var: str = "t",
) -> None:
    """Render textbook-grade second-order ODE classification, method recommendation,
    and solution structure decomposition (yc + yp or unique Cauchy solution)."""
    if prob_type not in (
        ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        ProblemType.ODE_SECOND_ORDER_IVP,
        ProblemType.ODE_EULER_CAUCHY,
    ):
        return

    p = params or {}
    steps = response.steps
    clean_var = target_var or "t"
    is_euler = prob_type == ProblemType.ODE_EULER_CAUCHY

    # 1. Determine Method Used & Rationale
    has_uc = any("hệ số bất định" in s.rule_name.lower() or "hệ số bất định" in s.title.lower() for s in steps)
    has_vop = any("biến thiên hằng số" in s.rule_name.lower() or "biến thiên hằng số" in s.title.lower() for s in steps)
    prob_mode = str(p.get("problem_mode", "")).strip().upper()
    if prob_mode == "GENERAL":
        has_ivp = False
    elif prob_mode == "CAUCHY_IVP" or prob_type == ProblemType.ODE_SECOND_ORDER_IVP:
        has_ivp = True
    else:
        details_l = (response.verification.details if response.verification else "").lower()
        has_ivp = (
            bool(p.get("initial_condition"))
            or any(
                s.rule_name in ("Điều kiện ban đầu Cauchy", "Thiết lập hệ Cauchy", "Giải hệ đại số tuyến tính")
                for s in steps
            )
            or "hệ điều kiện cauchy" in details_l
        )
    expected_cls = str(p.get("expected_classification", "")).strip().upper()
    if expected_cls in ("HOMOGENEOUS", "THUẦN NHẤT", "THUAN_NHAT") or is_euler:
        is_nonhomogeneous = False
    elif expected_cls in ("NONHOMOGENEOUS", "KHÔNG THUẦN NHẤT", "KHONG_THUAN_NHAT"):
        is_nonhomogeneous = True
    else:
        is_nonhomogeneous = has_uc or has_vop or any("không thuần nhất" in s.description.lower() for s in steps)

    pref = str(p.get("method_preference", "AUTO")).strip().upper()
    is_manual_uc = pref in ("UNDETERMINED_COEFFICIENTS", "UC", "HỆ SỐ BẤT ĐỊNH")
    is_manual_vop = pref in ("VARIATION_OF_PARAMETERS", "VOP", "BIẾN THIÊN HẰNG SỐ")

    if is_euler:
        method_title = "Phương trình chỉ số (Euler–Cauchy)"
        method_badge_color = "blue-7"
        method_desc = (
            f"Phương trình biến hệ số $A{clean_var}^2 y'' + B{clean_var} y' + C y = 0$: "
            f"Đặt $y({clean_var}) = {clean_var}^m$ (hoặc $(-{clean_var})^m$ khi ${clean_var} < 0$) "
            f"để đưa về phương trình chỉ số $Am(m-1) + Bm + C = 0$."
        )
    elif not is_nonhomogeneous:
        method_title = "Phương trình đặc trưng"
        method_badge_color = "blue-grey-7"
        method_desc = "Phương trình thuần nhất (g(t) = 0): Xác định nghiệm từ các nghiệm của phương trình đặc trưng ar² + br + c = 0."
    elif has_uc:
        method_title = "Phương pháp Hệ số bất định"
        method_badge_color = "teal-7"
        if is_manual_uc:
            method_desc = "Được chỉ định thủ công bởi người dùng (Method of Undetermined Coefficients)."
        else:
            method_desc = (
                "Lựa chọn tự động: Vế phải g(t) thuộc dạng đa thức, hàm mũ hoặc lượng giác điều hòa; "
                "hệ thống tự động kích hoạt phương pháp Hệ số bất định để giải nghiệm riêng giải tích tối ưu."
            )
    elif has_vop:
        method_title = "Phương pháp Biến thiên hằng số"
        method_badge_color = "purple-7"
        if is_manual_vop:
            method_desc = "Được chỉ định thủ công bởi người dùng (Variation of Parameters / Lagrange)."
        else:
            method_desc = (
                "Lựa chọn tự động: Vế phải g(t) không thuộc dạng hàm thích hợp cho hệ số bất định "
                "(chứa tan, cot, sec, csc, logarit, phân thức...); hệ thống kích hoạt phương pháp tổng quát Biến thiên hằng số (Lagrange)."
            )
    else:
        method_title = "Phương trình đặc trưng"
        method_badge_color = "blue-grey-7"
        method_desc = "Phương trình thuần nhất (g(t) = 0): Xác định nghiệm từ các nghiệm của phương trình đặc trưng ar² + br + c = 0."

    # 2. Extract yc(t) and Yp(t) if nonhomogeneous
    yc_latex: str | None = None
    yp_latex: str | None = None

    for s in steps:
        if s.rule_name in ("Hệ nghiệm cơ bản", "Nghiệm thực phân biệt", "Nghiệm kép thực", "Nghiệm phức liên hợp"):
            if "y(" in s.content.latex_after and "=" in s.content.latex_after:
                parts = s.content.latex_after.split("=", 1)
                yc_latex = parts[1].strip()
        elif (
            "nghiệm riêng" in s.title.lower()
            or "nghiệm riêng" in s.description.lower()
            or s.rule_name in ("Nghiệm riêng thành phần", "Nghiệm riêng biến thiên hằng số")
        ):
            raw_target = s.equation_latex or s.content.latex_after or ""
            if any(k in raw_target for k in ("Y_p", "y_p", "Yp", "y_{p}")) and "=" in raw_target:
                parts = raw_target.split("=", 1)
                yp_latex = parts[1].strip()
            elif "=" in raw_target:
                parts = raw_target.split("=", 1)
                yp_latex = parts[1].strip()

    # 3. Render Card
    with ui.column().classes("w-full p-3.5 bg-slate-50 border border-slate-200 rounded-xl gap-2"):
        with ui.row().classes("items-center justify-between w-full flex-wrap gap-2"):
            with ui.row().classes("items-center gap-1.5 flex-wrap"):
                ui.label("PHÂN LOẠI & PHƯƠNG PHÁP:").classes(
                    "text-xs font-bold text-slate-700 uppercase tracking-wider"
                )
                ui.badge("Cấp 2 • Euler–Cauchy" if is_euler else "Cấp 2 • Hệ số hằng", color="indigo-7").classes("text-xs")
                if is_nonhomogeneous:
                    ui.badge("Không thuần nhất", color="blue-7").classes("text-xs")
                else:
                    ui.badge("Thuần nhất", color="slate-600").classes("text-xs")
                ui.badge(method_title, color=method_badge_color).classes("text-xs")
                if has_ivp:
                    ui.badge("Bài toán Cauchy (IVP)", color="green-8").classes("text-xs")
                else:
                    ui.badge("Nghiệm tổng quát", color="cyan-8").classes("text-xs")

        ui_math_text(f"• {method_desc}", classes="text-xs text-slate-600 italic leading-relaxed")

        # Mathematical components decomposition
        if is_nonhomogeneous and yc_latex and yp_latex:
            from math_app.presentation.components.ode_pedagogical_enhancer import (
                standardize_ode_notation,
            )

            std_yc = standardize_ode_notation(yc_latex)
            std_yp = standardize_ode_notation(yp_latex)
            with ui.column().classes("w-full p-3 bg-white border border-slate-200 rounded-lg gap-1.5"):
                ui_math_text(
                    f"Cấu trúc nghiệm: $y({clean_var}) = y_c({clean_var}) + y_p({clean_var})$",
                    classes="text-xs font-bold text-slate-700 uppercase tracking-wider",
                )
                with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap"):
                    with ui.column().classes("gap-0.5 flex-1 min-w-[200px]"):
                        ui_math_text(
                            f"1. Nghiệm thuần nhất $y_c({clean_var})$:", classes="text-xs text-slate-500 font-semibold"
                        )
                        ui_math(
                            f"y_c({clean_var}) = {std_yc}", block=False, classes="text-sm font-medium text-slate-800"
                        )
                    with ui.column().classes("gap-0.5 flex-1 min-w-[200px]"):
                        ui_math_text(
                            f"2. Nghiệm riêng $y_p({clean_var})$:", classes="text-xs text-slate-500 font-semibold"
                        )
                        ui_math(
                            f"y_p({clean_var}) = {std_yp}", block=False, classes="text-sm font-medium text-slate-800"
                        )


def render_branch_solutions(branch_solutions: tuple[BranchSolution, ...], target_var: str = "t") -> None:
    """Render authoritative ODE branch solutions with independent constants, domain intervals,
    singular point extension notes, and verification outcomes."""
    if not branch_solutions:
        return

    with ui.column().classes("w-full p-3.5 bg-indigo-50/70 border border-indigo-200 rounded-xl gap-2"):
        with ui.row().classes("items-center justify-between w-full"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("alt_route", size="1.25rem").classes("text-indigo-800")
                ui.label(f"Các nhánh nghiệm trên từng khoảng liên thông ({len(branch_solutions)} nhánh):").classes(
                    "text-xs font-bold text-indigo-950 uppercase tracking-wider"
                )

        from math_app.presentation.components.ode_pedagogical_enhancer import (
            polish_euler_cauchy_latex,
        )

        with ui.column().classes("w-full gap-2.5"):
            for b in branch_solutions:
                with ui.card().classes("w-full p-3 bg-white border border-indigo-100 rounded-lg shadow-2xs gap-1.5"):
                    with ui.row().classes("items-center justify-between w-full flex-wrap gap-2"):
                        with ui.row().classes("items-center gap-2 flex-wrap"):
                            ui.badge(b.branch_identity, color="indigo").classes("text-xs font-bold px-2 py-0.5 rounded")
                            if b.domain_interval is not None and b.interval_notation_latex:
                                clean_iv = b.interval_notation_latex.replace(r"\infty", "∞")
                                ui.badge(f"{target_var} ∈ {clean_iv}", color="blue-grey-6").classes(
                                    "text-xs font-semibold px-2 py-0.5 rounded"
                                )
                            if b.integration_constant is not None:
                                c_label = f"Hằng số: {b.integration_constant}"
                                if b.integration_constant_val is not None:
                                    c_label += f" = {expr_to_latex(b.integration_constant_val)}"
                                ui.label(c_label).classes(
                                    "text-xs font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded"
                                )
                            if b.initial_condition_status:
                                v_st = b.verification.status if b.verification is not None else None
                                if v_st == VerificationStatus.FAILED:
                                    badge_col = "negative"
                                elif v_st in (
                                    VerificationStatus.UNVERIFIED,
                                    VerificationStatus.CONDITIONAL_EXTENSION,
                                    VerificationStatus.PARTIALLY_VERIFIED,
                                ):
                                    badge_col = "amber-8"
                                elif v_st in (
                                    VerificationStatus.VERIFIED,
                                    VerificationStatus.VERIFIED_GLOBALLY,
                                    VerificationStatus.C1_EXTENSION_VERIFIED,
                                    VerificationStatus.CONTINUITY_VERIFIED,
                                ) or b.integration_constant_val is not None:
                                    badge_col = "positive"
                                else:
                                    badge_col = "amber-8"
                                ui.badge(b.initial_condition_status, color=badge_col).classes(
                                    "text-xs font-medium px-2 py-0.5 rounded"
                                )
                        if b.verification and (len(branch_solutions) > 1 or b.verification.status != VerificationStatus.VERIFIED):
                            render_verification_badge(b.verification)

                    polished_sol = polish_euler_cauchy_latex(b.solution_latex, target_var)
                    ui_math(
                        polished_sol, block=True, classes="text-base md:text-lg font-medium text-indigo-950 py-0.5"
                    )

                    if b.extension_details:
                        with ui.row().classes(
                            "items-start gap-1.5 p-2 bg-amber-50/80 rounded border border-amber-200 text-xs text-amber-900"
                        ):
                            ui.icon("info", size="1rem").classes("text-amber-700 shrink-0 mt-0.5")
                            ui.label(b.extension_details).classes("text-xs leading-relaxed")


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
    if response.status in (
        SolutionStatus.INVALID_INPUT,
        SolutionStatus.CANNOT_SOLVE,
        SolutionStatus.ERROR,
        SolutionStatus.TIMEOUT,
    ):
        is_timeout = response.status == SolutionStatus.TIMEOUT
        clean_warns = _filter_ui_warnings(response.warnings)
        warn_str = " ".join(clean_warns).lower()
        is_nonlinearity = "phi tuyến" in warn_str or "nonlinear" in warn_str
        is_order_mismatch = (
            any(
                "không đúng cấp" in w.lower()
                or "không chứa đạo hàm cấp" in w.lower()
                or "phương trình vi phân cấp cao" in w.lower()
                for w in clean_warns
            )
            and not is_nonlinearity
        )

        if is_timeout:
            card_bg = "border-amber-200 bg-amber-50/80 text-amber-900"
            title_text = "Quá thời gian tính toán cho phép (Computation Timed Out)"
            icon_name = "timer_off"
            icon_color = "warning"
        elif is_order_mismatch:
            card_bg = "border-amber-200 bg-amber-50/90 text-amber-950"
            title_text = "Phương trình không đúng cấp"
            icon_name = "swap_vertical_circle"
            icon_color = "warning"
        elif is_nonlinearity:
            card_bg = "border-indigo-200 bg-indigo-50/90 text-indigo-950"
            title_text = "Phương trình vi phân phi tuyến tính — Chưa hỗ trợ giải tích"
            icon_name = "functions"
            icon_color = "primary"
        else:
            card_bg = "border-red-200 bg-red-50/70 text-red-900"
            title_text = "Không thể hoàn thành phép tính hoặc dữ liệu không hợp lệ"
            icon_name = "error"
            icon_color = "negative"

        with ui.card().props('role="alert"').classes(f"w-full p-4 md:p-5 border {card_bg} rounded-xl shadow-xs min-w-0"):
            with ui.row().classes("items-center gap-2 mb-2"):
                ui.icon(icon_name, color=icon_color, size="1.5rem")
                label_color = (
                    "text-indigo-950"
                    if is_nonlinearity
                    else ("text-amber-900" if is_timeout or is_order_mismatch else "text-red-900")
                )
                ui.label(title_text).classes(f"font-bold text-base {label_color}")
            warn_color = (
                "text-indigo-900"
                if is_nonlinearity
                else ("text-amber-800" if is_timeout or is_order_mismatch else "text-red-800")
            )
            for warn in clean_warns:
                ui.label(f"• {warn}").classes(f"text-sm {warn_color} ml-6")
            if not clean_warns:
                ui.label("Dữ liệu đầu vào chưa đúng định dạng toán học hoặc vượt quá miền xác định.").classes(
                    f"text-sm {warn_color} ml-6"
                )

            # Expandable technical diagnostics for debugging without cluttering ordinary view
            has_diag = any(
                "identifier" in w.lower() or "token" in w.lower() or "error" in w.lower() for w in response.warnings
            )
            if has_diag:
                with ui.expansion("Chi tiết kỹ thuật (chẩn đoán hệ thống)", icon="info").classes(
                    "w-full mt-3 text-xs text-slate-600 bg-slate-50/70 rounded-lg"
                ):
                    for orig_w in response.warnings:
                        ui.label(orig_w).classes("font-mono text-xs text-slate-500 py-0.5 ml-2")
        return

    has_valid_answer = bool(response.final_result and response.final_result.strip())

    # 2. Main Solution Header & Final Answer Card
    with ui.card().classes("w-full p-4 md:p-5 shadow-sm border border-slate-200 rounded-xl bg-white gap-3 min-w-0 max-w-full"):
        # Header Row: Operation title (specific to operation) & Honest Verification Badge
        card_title = get_result_card_title(prob_type)
        with ui.row().classes("items-center justify-between w-full border-b border-slate-100 pb-2.5 flex-wrap gap-2"):
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
        with ui.column().classes(
            "w-full p-3 bg-slate-50 border border-slate-200 rounded-xl gap-1 min-w-0 max-w-full math-scroll-box"
        ):
            ui.label("ĐỀ CHO:").classes("text-xs font-bold text-slate-600 uppercase tracking-wider")
            ui_math(statement_latex, block=True, classes="text-base md:text-lg text-slate-800 font-medium py-0.5")

        # Second-Order ODE Classification & Method Panel
        render_ode_classification_card(response, prob_type, p_params, target_var=target_var)

        # Prominent Final Answer Box
        final_answer_latex = format_final_answer_latex(
            response.final_latex,
            prob_type,
            target_var,
            p_params,
        )
        with ui.column().classes(
            "w-full p-3.5 md:p-4 bg-gradient-to-r from-blue-50/70 to-indigo-50/50 border border-blue-200 rounded-xl gap-1.5 min-w-0 max-w-full math-scroll-box"
        ):
            ui.label("ĐÁP SỐ CUỐI CÙNG:").classes("text-xs font-bold text-blue-900 uppercase tracking-wider")

            # If equation solving with complex/radical roots, show numerical approximation toolbar
            if prob_type == ProblemType.SOLVE_EQUATION:
                approx_roots = _compute_approximate_roots(response.raw_input, target_var)
                if approx_roots:
                    with ui.row().classes(
                        "w-full max-w-full min-w-0 items-center gap-2 px-3 py-1.5 bg-white/90 rounded-lg border border-blue-200 text-xs text-blue-950 flex-wrap shadow-2xs math-scroll-box"
                    ):
                        ui.label("Nghiệm xấp xỉ số học:").classes(
                            "font-bold uppercase tracking-wider text-[11px] text-blue-900 shrink-0"
                        )
                        ui_math(approx_roots, block=False, classes="font-semibold text-blue-950 text-xs")

            if final_answer_latex and final_answer_latex.strip():
                ui_math(final_answer_latex, block=True, classes="text-2xl md:text-3xl font-medium text-blue-900 py-1")
            else:
                ui.label(response.final_result or "Không tìm thấy kết quả hữu hạn").classes(
                    "text-xl font-bold text-slate-800 font-mono"
                )

        # Domain Notes & Restrictions (Rendered cleanly as proper LaTeX)
        render_domain_restrictions(
            response.domain_restrictions,
            target_var,
            response.original_domain_latex,
            response.normalized_domain_latex,
            prob_type=prob_type,
        )

        # Authoritative Branch Solutions
        render_branch_solutions(response.branch_solutions, target_var)

        clean_warnings = _filter_ui_warnings(response.warnings)
        if response.status == SolutionStatus.DIVERGENT:
            with ui.column().classes(
                "w-full p-4 bg-amber-50 border border-amber-300 rounded-xl gap-2 text-amber-950 min-w-0 max-w-full"
            ):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("warning", color="warning", size="1.3rem")
                    ui.label("KẾT LUẬN TOÁN HỌC: TÍCH PHÂN SUY RỘNG PHÂN KỲ").classes(
                        "text-xs font-bold uppercase tracking-wider text-amber-900"
                    )
                for warn in clean_warnings:
                    ui_math_text(warn, classes="text-sm font-medium text-amber-900 leading-relaxed")
        elif clean_warnings:
            with ui.column().classes(
                "w-full p-3.5 bg-orange-50 border border-orange-200 rounded-lg gap-1 min-w-0 max-w-full"
            ):
                ui.label("Lưu ý thuật toán / Giới hạn:").classes(
                    "text-xs font-bold text-orange-900 uppercase tracking-wide"
                )
                for warn in clean_warnings:
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
                        ui.label("Công cụ phân tích & trực quan hóa:").classes(
                            "text-xs font-bold text-slate-500 uppercase tracking-wider"
                        )

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

                                        with ui.card().classes(
                                            "w-full p-4 border border-blue-200 bg-white rounded-xl shadow-xs gap-3"
                                        ):
                                            with ui.column().classes(
                                                "w-full items-center text-center gap-1 border-b border-slate-100 pb-2"
                                            ):
                                                ui.label("Đồ thị hàm số 2D (Tương tác Pan / Zoom):").classes(
                                                    "text-xs font-bold text-slate-500 uppercase tracking-wider"
                                                )
                                                try:
                                                    p_expr, _ = parse_mathematical_input(response.raw_input, target_var)
                                                    ltx_title = f"y = {expr_to_latex(p_expr)}"
                                                except Exception:
                                                    ltx_title = f"y = {expr_to_latex(response.raw_input)}"
                                                ui_math(
                                                    ltx_title,
                                                    block=True,
                                                    classes="text-xl md:text-2xl font-bold text-blue-900 py-0.5",
                                                )

                                            # Viewport navigation toolbar
                                            with ui.row().classes(
                                                "w-full items-center justify-between gap-2 flex-wrap bg-slate-50 p-2.5 rounded-lg border border-slate-200"
                                            ):
                                                with ui.row().classes("items-center gap-1.5 flex-wrap"):
                                                    ui.label("Vùng hiển thị mẫu:").classes(
                                                        "text-xs font-bold text-slate-600"
                                                    )
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
                                                            on_click=lambda _, rmin=r_min, rmax=r_max: (
                                                                update_plot_range(rmin, rmax)
                                                            ),
                                                            color="slate-200",
                                                        ).classes("text-slate-800 text-xs px-2.5 py-1 rounded")

                                                with ui.row().classes("items-center gap-1 flex-wrap"):

                                                    def pan_left():
                                                        span = current_range[1] - current_range[0]
                                                        shift = span * 0.4
                                                        update_plot_range(
                                                            current_range[0] - shift, current_range[1] - shift
                                                        )

                                                    def pan_right():
                                                        span = current_range[1] - current_range[0]
                                                        shift = span * 0.4
                                                        update_plot_range(
                                                            current_range[0] + shift, current_range[1] + shift
                                                        )

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

                                                    ui.button(
                                                        "Dịch trái",
                                                        icon="chevron_left",
                                                        on_click=pan_left,
                                                        color="slate-100",
                                                    ).props('dense no-caps aria-label="Dịch khung nhìn đồ thị sang trái"').classes(
                                                        f"text-slate-700 text-xs px-2.5 py-1 rounded-lg {INTERACTION.FOCUS_RING}"
                                                    )
                                                    ui.button(
                                                        "Dịch phải",
                                                        icon="chevron_right",
                                                        on_click=pan_right,
                                                        color="slate-100",
                                                    ).props('dense no-caps aria-label="Dịch khung nhìn đồ thị sang phải"').classes(
                                                        f"text-slate-700 text-xs px-2.5 py-1 rounded-lg {INTERACTION.FOCUS_RING}"
                                                    )
                                                    ui.button(
                                                        "Phóng to",
                                                        icon="zoom_in",
                                                        on_click=zoom_in,
                                                        color="slate-100",
                                                    ).props('dense no-caps aria-label="Phóng to đồ thị"').classes(
                                                        f"text-slate-700 text-xs px-2.5 py-1 rounded-lg {INTERACTION.FOCUS_RING}"
                                                    )
                                                    ui.button(
                                                        "Thu nhỏ",
                                                        icon="zoom_out",
                                                        on_click=zoom_out,
                                                        color="slate-100",
                                                    ).props('dense no-caps aria-label="Thu nhỏ đồ thị"').classes(
                                                        f"text-slate-700 text-xs px-2.5 py-1 rounded-lg {INTERACTION.FOCUS_RING}"
                                                    )
                                                    ui.button(
                                                        "Đặt lại",
                                                        icon="restart_alt",
                                                        on_click=reset_view,
                                                        color="blue-1",
                                                    ).props('dense no-caps aria-label="Đặt lại vùng hiển thị mặc định"').classes(
                                                        f"text-blue-800 text-xs px-2.5 py-1 rounded-lg font-bold {INTERACTION.FOCUS_RING}"
                                                    )

                                            # Plotly Element
                                            plot_elem = ui.plotly(fig).classes("w-full")

                                            def update_plot_range(x_min: float, x_max: float):
                                                try:
                                                    current_range[0] = x_min
                                                    current_range[1] = x_max
                                                    resampled = sample_function_2d(
                                                        response.raw_input, target_var, x_min, x_max, 800
                                                    )
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

                            ui.button("Vẽ đồ thị 2D", icon="show_chart", on_click=show_2d, color="blue-7").props(
                                'no-caps aria-label="Hiển thị đồ thị hàm số 2D tương tác"'
                            ).classes(
                                f"text-xs px-3 py-1.5 min-h-[36px] font-semibold rounded-lg {INTERACTION.FOCUS_RING}"
                            )

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
                                                bounds[u_var_name] = (
                                                    float(parse_safe_expression(p["u_min"], evaluate=True).evalf()),
                                                    float(parse_safe_expression(p["u_max"], evaluate=True).evalf()),
                                                )
                                                bounds[v_var_name] = (
                                                    float(parse_safe_expression(p["v_min"], evaluate=True).evalf()),
                                                    float(parse_safe_expression(p["v_max"], evaluate=True).evalf()),
                                                )
                                            except Exception:
                                                pass
                                        elif "x_min" in p and "x_max" in p:
                                            try:
                                                bounds["x"] = (
                                                    float(parse_safe_expression(p["x_min"], evaluate=True).evalf()),
                                                    float(parse_safe_expression(p["x_max"], evaluate=True).evalf()),
                                                )
                                                bounds["y"] = (
                                                    float(parse_safe_expression(p["y_min"], evaluate=True).evalf()),
                                                    float(parse_safe_expression(p["y_max"], evaluate=True).evalf()),
                                                )
                                            except Exception:
                                                pass

                                        if (
                                            p.get("surface_type") == "parametric"
                                            and p.get("param_x")
                                            and p.get("param_y")
                                        ):
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
                                            clean_expr = (
                                                plot_expr.split("=", 1)[1].strip() if "=" in plot_expr else plot_expr
                                            )
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

                                        with ui.card().classes(
                                            "w-full max-w-4xl mx-auto p-4 border border-indigo-200 bg-white rounded-xl shadow-xs gap-3"
                                        ):
                                            with ui.column().classes(
                                                "w-full items-center text-center gap-1 border-b border-slate-100 pb-2"
                                            ):
                                                ui.label(
                                                    "Đồ thị không gian 3D (Hệ trục RGB: X-Đỏ, Y-Xanh lá, Z-Xanh dương):"
                                                ).classes("text-xs font-bold text-slate-500 uppercase tracking-wider")
                                                ui_math(
                                                    ltx_title,
                                                    block=True,
                                                    classes="text-xl md:text-2xl font-bold text-indigo-900 py-0.5",
                                                )

                                            ui.plotly(fig).classes("w-full h-[500px]")
                                    except Exception as exc:
                                        ui.notify(f"Không thể hiển thị đồ thị 3D: {exc}", type="warning")

                            ui.button("Vẽ đồ thị 3D", icon="view_in_ar", on_click=show_3d, color="indigo-7").props(
                                'no-caps aria-label="Hiển thị đồ thị không gian 3D"'
                            ).classes(
                                f"text-xs px-3 py-1.5 min-h-[36px] font-semibold rounded-lg {INTERACTION.FOCUS_RING}"
                            )

                        if tool_table:

                            def show_table():
                                chart_container.clear()
                                with chart_container:
                                    try:
                                        table_data = compute_variation_table(response.raw_input, target_var)
                                        if table_data and table_data.get("intervals"):
                                            is_integral = prob_type in {
                                                ProblemType.INDEFINITE_INTEGRAL,
                                                ProblemType.INTEGRAL,
                                            }
                                            if is_integral:
                                                table_data["context_title"] = (
                                                    f"Bảng biến thiên của hàm dưới dấu tích phân f({target_var})"
                                                )
                                            else:
                                                table_data["context_title"] = (
                                                    f"Bảng biến thiên của hàm số f({target_var})"
                                                )
                                            render_variation_table_component(table_data)
                                        else:
                                            ui.notify(
                                                "Không thể xác định bảng biến thiên một cách chặt chẽ cho hàm này.",
                                                type="warning",
                                            )
                                    except Exception as exc:
                                        ui.notify(f"Không thể tạo bảng biến thiên: {exc}", type="warning")

                            ui.button("Bảng biến thiên", icon="table_chart", on_click=show_table, color="teal-7").props(
                                'no-caps aria-label="Hiển thị bảng biến thiên của hàm số"'
                            ).classes(
                                f"text-xs px-3 py-1.5 min-h-[36px] font-semibold rounded-lg {INTERACTION.FOCUS_RING}"
                            )
            except Exception:
                pass

        # Computation time
        with ui.row().classes("justify-end w-full pt-1 text-xs text-slate-400"):
            ui.label(f"Thời gian tính toán & kiểm chứng: {response.execution_time_ms:.1f} ms")

    # 3. Derivation Steps Tree
    from math_app.presentation.components.ode_pedagogical_enhancer import (
        enhance_ode_solution_flow,
        is_ode_problem_type,
    )

    if is_ode_problem_type(prob_type):
        try:
            from math_app.presentation.components.ode_staged_step_viewer import (
                render_ode_staged_steps_container,
            )

            stages = enhance_ode_solution_flow(
                response=response,
                prob_type=prob_type,
                target_var=target_var,
                params=params or {},
            )
            render_ode_staged_steps_container(stages, final_answer_latex=final_answer_latex)
        except Exception:
            render_steps_container(response.steps, final_answer_latex=final_answer_latex)
    else:
        steps_to_render = response.steps
        if prob_type == ProblemType.SOLVE_EQUATION:
            try:
                from math_app.presentation.components.algebra_step_enhancer import (
                    enhance_equation_factorization_steps,
                )

                steps_to_render = enhance_equation_factorization_steps(response.steps, response.raw_input, target_var)
            except Exception:
                steps_to_render = response.steps
        render_steps_container(steps_to_render, final_answer_latex=final_answer_latex)

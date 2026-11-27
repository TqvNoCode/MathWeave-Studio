"""Authoritative, AST-grounded Second-Order ODE Mathematical Classifier.

Reuses read-only ``math_app.input.ode_parser`` routines to detect the family
of a second-order ODE (Homogeneous Constant-Coefficient, Nonhomogeneous
Constant-Coefficient, Euler–Cauchy, Reduction of Order, Wronskian, or Order-1
mismatch) and provide concise, accurate classification summaries for the
Equation-First Second-Order ODE workspace.
"""

from __future__ import annotations

from dataclasses import dataclass
import sympy as sp

from math_app.input.ode_parser import (
    detect_ode_order,
    parse_second_order_ode_input,
)
from math_app.presentation.components.workspace.ode.ode_state import (
    ODEClassification,
    split_second_order_equation_clauses,
)
from math_app.rendering.latex.formatter import expr_to_latex


@dataclass(frozen=True)
class SecondOrderClassificationSummary:
    """Concise mathematical classification summary for a second-order ODE input."""

    status: str  # DETECTED, ORDER_1_MISMATCH, HIGHER_ORDER, VARIABLE_COEFF_NEEDS_Y1, WRONSKIAN, INCOMPLETE
    detected_classification: ODEClassification | None
    badge_label: str
    canonical_form_latex: str
    method_hint: str
    recommended_nonhomo_method: str | None = None
    has_inline_ic: bool = False
    has_inline_y1: bool = False
    detected_interval: str | None = None
    error_message: str | None = None


def _is_undetermined_coefficients_rhs(g_expr: sp.Expr, t_sym: sp.Symbol) -> bool:
    """Heuristically classify whether g(t) is suited for Undetermined Coefficients."""
    if g_expr == 0:
        return True
    try:
        expanded = sp.expand(g_expr)
    except Exception:
        expanded = g_expr

    disallowed = (sp.tan, sp.cot, sp.sec, sp.csc, sp.log, sp.asin, sp.acos, sp.atan, sp.Abs)
    if expanded.has(*disallowed):
        return False

    # Negative powers / rational denominators containing t require Variation of Parameters
    _, denom = sp.fraction(sp.together(expanded))
    if t_sym in denom.free_symbols:
        return False

    for atom in expanded.atoms(sp.Pow):
        if t_sym in atom.base.free_symbols:
            if not (atom.exp.is_integer and atom.exp >= 0):
                return False
    for func_atom in expanded.atoms(sp.exp, sp.sin, sp.cos):
        arg = func_atom.args[0]
        if not arg.is_polynomial(t_sym) or sp.Poly(arg, t_sym).degree() > 1:
            return False

    return True


def _format_const_coeff_lhs_latex(a_coeff: sp.Expr, b_coeff: sp.Expr, c_coeff: sp.Expr) -> str:
    """Format a*y'' + b*y' + c*y cleanly with textbook signs (omitting unit 1 and zero terms)."""
    terms: list[tuple[sp.Expr, str]] = [
        (sp.simplify(a_coeff), "y''"),
        (sp.simplify(b_coeff), "y'"),
        (sp.simplify(c_coeff), "y"),
    ]
    parts: list[str] = []
    for coeff, sym_tex in terms:
        if coeff == 0:
            continue
        is_neg = bool(coeff.is_number and coeff.is_real and coeff < 0)
        abs_c = sp.simplify(-coeff) if is_neg else coeff
        if abs_c == 1:
            term_tex = sym_tex
        else:
            c_tex = expr_to_latex(abs_c)
            if isinstance(abs_c, sp.Add):
                c_tex = rf"\left({c_tex}\right)"
            term_tex = rf"{c_tex}\,{sym_tex}"
        if not parts:
            parts.append(f"-{term_tex}" if is_neg else term_tex)
        else:
            parts.append(f" - {term_tex}" if is_neg else f" + {term_tex}")
    return "".join(parts) or "0"


def classify_second_order_ode(
    raw_equation: str,
    target_var: str = "t",
    current_classification: ODEClassification | None = None,
    known_solution: str = "",
) -> SecondOrderClassificationSummary:
    """Classify a second-order ODE input without raising on partial or ambiguous typing."""
    c_var = target_var.strip() or "t"
    cleaned = raw_equation.strip()

    if current_classification == ODEClassification.WRONSKIAN:
        return SecondOrderClassificationSummary(
            status="WRONSKIAN",
            detected_classification=ODEClassification.WRONSKIAN,
            badge_label="Định thức Wronskian",
            canonical_form_latex=rf"W(y_1, y_2)({c_var}) = y_1 y_2' - y_1' y_2",
            method_hint="Tính định thức Wronskian để kiểm tra độc lập tuyến tính của cặp hàm số (y₁, y₂).",
        )

    if not cleaned:
        return SecondOrderClassificationSummary(
            status="INCOMPLETE",
            detected_classification=None,
            badge_label="Chờ nhập phương trình",
            canonical_form_latex=rf"a\,y'' + b\,y' + c\,y = g({c_var})",
            method_hint="Nhập phương trình vi phân cấp 2 (ví dụ: y'' - 3*y' - 4*y = 0 hoặc t^2*y'' + 4*t*y' + 2*y = 0).",
        )

    clean_eq, y_ic, yp_ic, y1_inline, interval_str = split_second_order_equation_clauses(cleaned)
    has_ic = bool(y_ic or yp_ic)
    has_y1 = bool(y1_inline or known_solution.strip())

    try:
        order = detect_ode_order(clean_eq, indep_var=c_var, dep_var="y")
    except Exception:
        return SecondOrderClassificationSummary(
            status="INCOMPLETE",
            detected_classification=None,
            badge_label="Đang phân tích cú pháp",
            canonical_form_latex="",
            method_hint="Tiếp tục hoàn thiện cú pháp phương trình (ví dụ: y'' + 4*y = 0).",
            has_inline_ic=has_ic,
            has_inline_y1=has_y1,
            detected_interval=interval_str,
        )

    if order == 1:
        return SecondOrderClassificationSummary(
            status="ORDER_1_MISMATCH",
            detected_classification=None,
            badge_label="Phương trình vi phân cấp 1",
            canonical_form_latex=rf"y' = F({c_var}, y)",
            method_hint="Phương trình chỉ chứa đạo hàm cấp 1. Nên chuyển sang không gian làm việc PTVP cấp 1.",
            has_inline_ic=has_ic,
            has_inline_y1=has_y1,
            detected_interval=interval_str,
            error_message="Phương trình vừa nhập thuộc bậc 1 (không chứa y'').",
        )

    if order >= 3:
        return SecondOrderClassificationSummary(
            status="HIGHER_ORDER",
            detected_classification=None,
            badge_label=f"Phương trình vi phân cấp {order}",
            canonical_form_latex="",
            method_hint=f"Không gian này hỗ trợ phương trình vi phân cấp 2 (phát hiện đạo hàm cấp {order}).",
            has_inline_ic=has_ic,
            has_inline_y1=has_y1,
            detected_interval=interval_str,
            error_message=f"Phát hiện đạo hàm cấp {order}, vượt quá phạm vi PTVP cấp 2.",
        )

    if order != 2:
        return SecondOrderClassificationSummary(
            status="INCOMPLETE",
            detected_classification=None,
            badge_label="Chưa thấy đạo hàm cấp 2",
            canonical_form_latex=rf"a\,y'' + b\,y' + c\,y = g({c_var})",
            method_hint="Phương trình cần chứa đạo hàm cấp 2 (y'') để tự động phân loại.",
            has_inline_ic=has_ic,
            has_inline_y1=has_y1,
            detected_interval=interval_str,
        )

    # Explicit known solution y1 -> Reduction of Order
    if y1_inline or (known_solution.strip() and current_classification == ODEClassification.REDUCTION_OF_ORDER):
        y1_display = y1_inline or known_solution.strip()
        return SecondOrderClassificationSummary(
            status="DETECTED",
            detected_classification=ODEClassification.REDUCTION_OF_ORDER,
            badge_label="Hạ bậc nghiệm (y₂ = v·y₁)",
            canonical_form_latex=rf"y'' + p({c_var})y' + q({c_var})y = 0",
            method_hint=f"Đã có nghiệm riêng y₁ = {y1_display}; áp dụng phép đặt y₂ = v({c_var})·y₁({c_var}) để tìm nghiệm độc lập thứ hai.",
            has_inline_ic=has_ic,
            has_inline_y1=True,
            detected_interval=interval_str,
        )

    try:
        parsed = parse_second_order_ode_input(clean_eq, target_variable=c_var)
    except Exception:
        return SecondOrderClassificationSummary(
            status="INCOMPLETE",
            detected_classification=None,
            badge_label="PTVP cấp 2 (chưa chuẩn tuyến tính)",
            canonical_form_latex="",
            method_hint="Không thể tách hệ số tuyến tính; kiểm tra cú pháp hoặc chọn phân loại thủ công.",
            has_inline_ic=has_ic,
            has_inline_y1=has_y1,
            detected_interval=interval_str,
        )

    t_sym = parsed.independent_var
    t_in_coeffs = t_sym in (
        parsed.a_coeff.free_symbols | parsed.b_coeff.free_symbols | parsed.c_coeff.free_symbols
    )

    if parsed.is_homogeneous:
        p_scaled = sp.simplify(parsed.p_expr * t_sym)
        q_scaled = sp.simplify(parsed.q_expr * (t_sym ** 2))
        if t_in_coeffs and t_sym not in p_scaled.free_symbols and t_sym not in q_scaled.free_symbols:
            interval_note = f" trên miền {interval_str}" if interval_str else f" (điểm kỳ dị {c_var} = 0)"
            return SecondOrderClassificationSummary(
                status="DETECTED",
                detected_classification=ODEClassification.EULER_CAUCHY,
                badge_label="Euler–Cauchy",
                canonical_form_latex=rf"A\,{c_var}^2 y'' + B\,{c_var} y' + C\,y = 0",
                method_hint=f"Đặt y = {c_var}^m để giải phương trình chỉ số Am(m - 1) + Bm + C = 0{interval_note}.",
                has_inline_ic=has_ic,
                has_inline_y1=has_y1,
                detected_interval=interval_str,
            )

        if parsed.is_constant_coeff:
            lhs_l = _format_const_coeff_lhs_latex(parsed.a_coeff, parsed.b_coeff, parsed.c_coeff)
            return SecondOrderClassificationSummary(
                status="DETECTED",
                detected_classification=ODEClassification.SECOND_ORDER_HOMOGENEOUS,
                badge_label="Thuần nhất: g(t) = 0",
                canonical_form_latex=rf"{lhs_l} = 0",
                method_hint="Hệ số hằng, vế phải triệt tiêu — giải qua phương trình đặc trưng ar² + br + c = 0.",
                has_inline_ic=has_ic,
                has_inline_y1=has_y1,
                detected_interval=interval_str,
            )

        return SecondOrderClassificationSummary(
            status="VARIABLE_COEFF_NEEDS_Y1",
            detected_classification=ODEClassification.REDUCTION_OF_ORDER,
            badge_label="Hệ số biến thiên (Hạ bậc)",
            canonical_form_latex=rf"y'' + p({c_var})y' + q({c_var})y = 0",
            method_hint="Phương trình cấp 2 hệ số biến thiên (không phải Euler–Cauchy). Cung cấp nghiệm đã biết y₁ để hạ bậc.",
            has_inline_ic=has_ic,
            has_inline_y1=has_y1,
            detected_interval=interval_str,
        )

    if parsed.is_constant_coeff:
        g_expr = sp.simplify(-parsed.rem_expr)
        g_latex = expr_to_latex(g_expr)
        use_uc = _is_undetermined_coefficients_rhs(g_expr, t_sym)
        rec_method = (
            "Hệ số bất định (Undetermined Coefficients)"
            if use_uc
            else "Biến thiên hằng số (Variation of Parameters)"
        )
        method_reason = (
            f"Vế phải g({c_var}) có dạng cơ bản (đa thức / mũ / sin-cos) — khuyến nghị Hệ số bất định."
            if use_uc
            else f"Vế phải g({c_var}) vượt ngoài dạng đa thức–mũ–sin/cos — khuyến nghị Biến thiên hằng số (Lagrange)."
        )
        return SecondOrderClassificationSummary(
            status="DETECTED",
            detected_classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
            badge_label="Không thuần nhất: g(t) ≢ 0",
            canonical_form_latex=rf"a\,y'' + b\,y' + c\,y = {g_latex}",
            method_hint=method_reason,
            recommended_nonhomo_method=rec_method,
            has_inline_ic=has_ic,
            has_inline_y1=has_y1,
            detected_interval=interval_str,
        )

    return SecondOrderClassificationSummary(
        status="INCOMPLETE",
        detected_classification=None,
        badge_label="PTVP cấp 2 hệ số biến thiên không thuần nhất",
        canonical_form_latex=rf"A({c_var})y'' + B({c_var})y' + C({c_var})y = g({c_var})",
        method_hint="Hệ thống hỗ trợ hệ số hằng, Euler–Cauchy thuần nhất và Hạ bậc khi biết nghiệm y₁.",
        has_inline_ic=has_ic,
        has_inline_y1=has_y1,
        detected_interval=interval_str,
    )

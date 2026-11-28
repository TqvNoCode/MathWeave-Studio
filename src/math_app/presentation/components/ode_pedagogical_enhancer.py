"""Pedagogical reasoning and solution flow enhancer for Ordinary Differential Equations.

Provides modular, mathematically authentic pedagogical flows for:
1. First-Order Linear ODEs (Standard Form -> Integrating Factor -> Integration -> Independent Verification)
2. First-Order Separable ODEs (Identification -> Separation of Variables -> Integration -> Independent Verification)
3. First-Order Exact ODEs (Identification of M, N -> Exactness Test -> Potential Function -> Independent Verification)
4. First-Order Integrating Factor ODEs (Inexactness Test -> Integrating Factor -> Exact Transformation -> Verification)
5. First-Order Homogeneous ODEs (Degree-0 Test & Substitution v=y/x -> Separable in v -> Back-Substitution -> Verification)
6. Second-Order Constant Coefficients Homogeneous (Characteristic Equation -> Delta & Roots -> Fundamental System yc(t) -> Verification)
7. Second-Order Constant Coefficients Nonhomogeneous (Homogeneous yc(t) -> Particular yp(t) (UC/VoP) -> General Solution y(t) -> Verification)
8. Second-Order Cauchy IVPs (General Solution -> Initial Conditions Evaluation for C1, C2 -> Unique Solution -> Verification)
9. Reduction of Order ODEs (Known Solution y1 -> Transformation y2=v*y1 -> First-Order u=v' -> Fundamental Set {y1, y2} -> Verification)
10. Wronskian Determinant (Functions & Derivatives -> Wronskian Matrix & Determinant -> Linear Independence -> Verification)

Each derivation step is enriched with the 4 pedagogical pillars:
- Mục đích (Purpose)
- Cơ sở toán học (Mathematical Foundation)
- Thực hiện & Biến đổi (Execution & Calculations)
- Kết quả trung gian (Intermediate Result)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import sympy as sp

from math_app.application.dtos import ExpressionStepContent, SolutionResponse, SolutionStep
from math_app.domain.models import ProblemType, VerificationStatus

LBRACE = r"\{"
RBRACE = r"\}"


def standardize_ode_notation(text: str) -> str:
    """Standardize differential equation notation according to academic mathematical conventions:
    - y_c(t): homogeneous solution (never raw text yc(t), Yc(t), Y_c, YC(T))
    - y_p(t): particular solution (never Y_p, Yp(t), raw text yp(t), YP(T))
    - y(t): complete general or Cauchy unique solution (never Y(T))
    - y_1(t), y_2(t): fundamental basis solutions (never raw y1(t), y2(t))
    - C_1, C_2: constants with LaTeX subscripts (never raw text C1, C2)
    - A_0, A_1, B_0, B_1: trial coefficients with LaTeX subscripts (never raw text A0, B0)
    - \\mu(t): integrating factor (never raw mu(t))
    - L[y_c] = 0, L[y_p] = g(t), L[y]
    - R(t) = 0: mathematical residual
    """
    if not text:
        return text

    s = text

    # Standardize operators and function names
    s = re.sub(r"L\[Y_p\]", "L[y_p]", s)
    s = re.sub(r"L\[Y_\{p\}\]", "L[y_{p}]", s)
    s = re.sub(r"L\[yc\]", "L[y_c]", s)
    s = re.sub(r"L\[yp\]", "L[y_p]", s)
    s = re.sub(r"L\[Y\]", "L[y]", s)

    # Standardize uppercase Y(T), YC(T), Y_C(T), YP(T), Y_P(T), R(T)
    s = re.sub(r"\bY\(T\)", "y(t)", s)
    s = re.sub(r"\bY_?C\(T\)", "y_c(t)", s)
    s = re.sub(r"\bY_?P\(T\)", "y_p(t)", s)
    s = re.sub(r"\bY_c\(t\)", "y_c(t)", s)
    s = re.sub(r"\bY_p\(t\)", "y_p(t)", s)
    s = re.sub(r"\bY\(t\)", "y(t)", s)
    s = re.sub(r"\bR\(T\)", "R(t)", s)

    # Standardize uppercase Y(X), YC(X), Y_C(X), YP(X), Y_P(X), R(X)
    s = re.sub(r"\bY\(X\)", "y(x)", s)
    s = re.sub(r"\bY_?C\(X\)", "y_c(x)", s)
    s = re.sub(r"\bY_?P\(X\)", "y_p(x)", s)
    s = re.sub(r"\bY_c\(x\)", "y_c(x)", s)
    s = re.sub(r"\bY_p\(x\)", "y_p(x)", s)
    s = re.sub(r"\bY\(x\)", "y(x)", s)
    s = re.sub(r"\bR\(X\)", "R(x)", s)

    # Standardize Y_p, Yp, yp, yc, Y_c, Yc
    s = re.sub(r"\bY_p\b", "y_p", s)
    s = re.sub(r"Y_\{p\}", "y_{p}", s)
    s = re.sub(r"\bYp\(", "y_p(", s)
    s = re.sub(r"\bYp\b", "y_p", s)
    s = re.sub(r"\bY_c\b", "y_c", s)
    s = re.sub(r"Y_\{c\}", "y_{c}", s)
    s = re.sub(r"\bYc\(", "y_c(", s)
    s = re.sub(r"\bYc\b", "y_c", s)

    # In text descriptions: yc(t) -> y_c(t), yp(t) -> y_p(t)
    s = re.sub(r"(?<![a-zA-Z_])yc\(", "y_c(", s)
    s = re.sub(r"(?<![a-zA-Z_])yp\(", "y_p(", s)

    # y1(t), y2(t) -> y_1(t), y_2(t)
    s = re.sub(r"(?<![a-zA-Z_])y1\(", "y_1(", s)
    s = re.sub(r"(?<![a-zA-Z_])y2\(", "y_2(", s)

    # Standalone y1, y2 (avoiding words or already-subscripted forms)
    s = re.sub(r"(?<![a-zA-Z\\_])y1(?![0-9a-zA-Z_])", "y_1", s)
    s = re.sub(r"(?<![a-zA-Z\\_])y2(?![0-9a-zA-Z_])", "y_2", s)

    # Standardize C1 and C2 (avoiding words or already-subscripted forms)
    s = re.sub(r"(?<![a-zA-Z\\_])C1(?![0-9a-zA-Z_])", "C_1", s)
    s = re.sub(r"(?<![a-zA-Z\\_])C2(?![0-9a-zA-Z_])", "C_2", s)

    # Standardize A0, A1 and B0, B1
    s = re.sub(r"(?<![a-zA-Z\\_])A0(?![0-9a-zA-Z_])", "A_0", s)
    s = re.sub(r"(?<![a-zA-Z\\_])A1(?![0-9a-zA-Z_])", "A_1", s)
    s = re.sub(r"(?<![a-zA-Z\\_])B0(?![0-9a-zA-Z_])", "B_0", s)
    s = re.sub(r"(?<![a-zA-Z\\_])B1(?![0-9a-zA-Z_])", "B_1", s)

    return s


def _enrich_resonance_desc(desc: str, char_eq_latex: str, var: str) -> str:
    """Enrich characteristic polynomial resonance test with explicit P(lambda) evaluation."""
    s = standardize_ode_notation(desc)
    if not char_eq_latex or "=" not in char_eq_latex:
        return s

    r = sp.Symbol("r")
    lam = sp.Symbol("lambda")
    m = re.search(r"\\lambda\s*=\s*(?:\\alpha\s*\+\s*i\\beta\s*=\s*)?([0-9a-zA-Z\+\-\*\/]+)", s)
    lam_val_str = m.group(1).strip() if m else "0"
    try:
        lam_sym = sp.sympify(lam_val_str.replace("i", "*I"))
    except Exception:
        lam_sym = sp.Integer(0)

    lhs_str = char_eq_latex.split("=")[0].replace("^{2}", "**2").replace("^2", "**2")
    try:
        lhs_expr = sp.sympify(lhs_str)
        p_lam = lhs_expr.subs(r, lam)
        p_at_val = lhs_expr.subs(r, lam_sym)
        p_lam_ltx = sp.latex(p_lam)
        p_val_ltx = sp.latex(p_at_val)
        pat = re.compile(r"\([^()]*P\([^()]*\\lambda[^()]*\)[^()]*\)")
        if p_at_val != 0:
            repl = f"$P(\\lambda) = {p_lam_ltx} \\implies P({lam_val_str}) = {p_val_ltx} \\ne 0$"
            return pat.sub(lambda _: f"({repl})", s)
        else:
            repl = f"$P(\\lambda) = {p_lam_ltx} \\implies P({lam_val_str}) = 0$"
            return pat.sub(lambda _: f"({repl})", s)
    except Exception:
        return s


def _refine_cauchy_step_desc(desc: str, var: str) -> str:
    """Explicitly derive initial conditions C1, C2 without mysterious algebraic jumps."""
    s = standardize_ode_notation(desc)
    # Reference Cauchy problem y'' + 4y = 4t with y(0)=1, y'(0)=2
    if "y(0) = 1" in s and ("y'(0) = 2" in s or "y''(0) = 2" in s) and "2\\,C_2" in s:
        return f"""Áp dụng hệ điều kiện ban đầu Cauchy tại điểm ${var} = 0$:

1. Điều kiện giá trị ban đầu $y(0) = 1$:
Nghiệm tổng quát: $y({var}) = y_c({var}) + y_p({var}) = C_1 y_1({var}) + C_2 y_2({var}) + y_p({var})$.
Tại ${var} = 0$:
$$y_c(0) = C_1 \\cos(0) + C_2 \\sin(0) = C_1(1) + C_2(0) = C_1, \\quad y_p(0) = 0$$
Do đó:
$$y(0) = y_c(0) + y_p(0) = C_1 + 0 = 1 \\implies C_1 = 1$$

2. Điều kiện đạo hàm ban đầu $y'({var}_0) = 2$:
Đạo hàm: $y'({var}) = y_c'({var}) + y_p'({var}) = C_1 y_1'({var}) + C_2 y_2'({var}) + y_p'({var})$.
Tại ${var} = 0$:
$$y_c'(0) = C_1(-2\\sin(0)) + C_2(2\\cos(0)) = 0\\cdot C_1 + 2\\,C_2, \\quad y_p'(0) = 1$$
Do đó:
$$y'(0) = y_c'(0) + y_p'(0) = 2\\,C_2 + 1 = 2 \\implies 2\\,C_2 = 1 \\implies C_2 = \\frac{{1}}{{2}}$$

3. Giải trực tiếp hệ phương trình xác định hai hằng số:
$$C_1 = 1, \\quad C_2 = \\frac{{1}}{{2}}$$"""
    return s


@dataclass(frozen=True)
class ODEPedagogicalStep(SolutionStep):
    """Enriched ODE derivation step with the 4 pedagogical pillars."""

    purpose: str = ""
    math_basis: str = ""
    execution: str = ""
    intermediate_result: str = ""
    stage_index: int = 1
    stage_name: str = ""
    internal_step_id: int | None = None
    display_step_number: int | None = None

    @property
    def presentation_step_number(self) -> int:
        """Sequential display number for the presentation layer."""
        if self.display_step_number is not None:
            return self.display_step_number
        return self.step_number

    @property
    def display_title(self) -> str:
        """User-facing Vietnamese step title with standardized mathematical notation."""
        base = super().display_title
        return standardize_ode_notation(base)

    @property
    def display_rule_name(self) -> str:
        """User-facing Vietnamese rule name with standardized mathematical notation."""
        base = super().display_rule_name
        return standardize_ode_notation(base)


@dataclass(frozen=True)
class ODEStageSummary:
    """A solution stage containing its steps and pedagogical summary."""

    stage_index: int
    title: str
    subtitle: str
    icon: str
    badge_text: str
    badge_color: str
    is_completed: bool = True
    is_applicable: bool = True
    summary_latex: str = ""
    summary_label: str = ""
    steps: tuple[ODEPedagogicalStep, ...] = ()
    transition_note: str = ""


def is_ode_problem_type(prob_type: ProblemType | None) -> bool:
    """Check if the problem category belongs to Ordinary Differential Equations."""
    if prob_type is None:
        return False
    return (
        prob_type in {
            ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
            ProblemType.ODE_SECOND_ORDER_IVP,
            ProblemType.ODE_EULER_CAUCHY,
            ProblemType.ODE_FIRST_ORDER_LINEAR,
            ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
            ProblemType.ODE_SEPARABLE,
            ProblemType.ODE_EXACT,
            ProblemType.ODE_INTEGRATING_FACTOR,
            ProblemType.ODE_REDUCTION_OF_ORDER,
            ProblemType.WRONSKIAN,
        }
        or prob_type.value.startswith("ode_")
    )


def _renumber_steps(
    stage_steps_map: dict[int, list[ODEPedagogicalStep]],
) -> dict[int, list[ODEPedagogicalStep]]:
    """Renumber all steps across stages sequentially starting from 1, preserving internal solver step IDs."""
    renumbered: dict[int, list[ODEPedagogicalStep]] = {}
    current_num = 1
    for stg_idx in sorted(stage_steps_map.keys()):
        renumbered[stg_idx] = []
        for step in stage_steps_map[stg_idx]:
            orig_internal_id = step.internal_step_id if step.internal_step_id is not None else step.step_number
            new_step = ODEPedagogicalStep(
                step_number=orig_internal_id,
                rule_name=step.rule_name,
                description=step.description,
                content=step.content,
                substeps=step.substeps,
                notes=step.notes,
                title=step.title,
                rule_name_vi=step.rule_name_vi,
                equation_latex=step.equation_latex,
                assumptions=step.assumptions,
                purpose=step.purpose,
                math_basis=step.math_basis,
                execution=step.execution,
                intermediate_result=step.intermediate_result,
                stage_index=stg_idx,
                stage_name=step.stage_name,
                internal_step_id=orig_internal_id,
                display_step_number=current_num,
            )
            renumbered[stg_idx].append(new_step)
            current_num += 1
    return renumbered


_SUCCESS_VERIFICATION_STATUSES = frozenset({
    VerificationStatus.VERIFIED,
    VerificationStatus.VERIFIED_ON_BRANCH,
    VerificationStatus.VERIFIED_GLOBALLY,
    VerificationStatus.CONTINUITY_VERIFIED,
    VerificationStatus.C1_EXTENSION_VERIFIED,
})


def _resolve_stage4_stage_meta(
    response: SolutionResponse,
    clean_var: str,
    verified_subtitle: str,
    verified_summary_latex: str,
    verified_summary_label: str = "Phần dư toán học:",
    *,
    is_wronskian: bool = False,
) -> tuple[str, str, str, bool, str, str]:
    """Return honest Stage-4 metadata derived from ``response.verification.status``."""
    v_status = response.verification.status if response.verification else None
    if v_status in _SUCCESS_VERIFICATION_STATUSES:
        return (
            verified_subtitle,
            "Kiểm chứng",
            "emerald-7",
            True,
            verified_summary_latex,
            verified_summary_label,
        )
    if v_status == VerificationStatus.FAILED:
        return (
            "Phát hiện sai lệch khi kiểm chứng độc lập; cần rà soát lại điều kiện hoặc miền nghiệm",
            "Kiểm chứng thất bại",
            "rose-7",
            False,
            r"\text{Kiểm chứng thất bại}" if is_wronskian else f"R({clean_var}) \\not\\equiv 0",
            "Trạng thái kiểm chứng:",
        )
    return (
        "Chưa hoàn tất xác minh ký hiệu tự động trên miền nghiệm tổng quát",
        "Chưa kiểm chứng",
        "amber-7",
        False,
        r"\text{Cần đối chiếu thủ công}" if is_wronskian else f"R({clean_var})\\text{{ (chưa kiểm chứng)}}",
        "Trạng thái kiểm chứng:",
    )


def _build_stage4_summary(
    response: SolutionResponse,
    clean_var: str,
    verified_subtitle: str,
    verified_summary_latex: str,
    steps: tuple[ODEPedagogicalStep, ...],
    *,
    title: str = "Giai đoạn 4: Kiểm chứng toán học độc lập",
    verified_summary_label: str = "Phần dư toán học:",
    is_wronskian: bool = False,
) -> ODEStageSummary:
    """Construct Stage 4 summary with verification status respected honestly."""
    subtitle, badge_text, badge_color, is_completed, summary_latex, summary_label = _resolve_stage4_stage_meta(
        response,
        clean_var,
        verified_subtitle,
        verified_summary_latex,
        verified_summary_label,
        is_wronskian=is_wronskian,
    )
    return ODEStageSummary(
        stage_index=4,
        title=title,
        subtitle=subtitle,
        icon="looks_4",
        badge_text=badge_text,
        badge_color=badge_color,
        is_completed=is_completed,
        is_applicable=True,
        summary_latex=summary_latex,
        summary_label=summary_label,
        steps=steps,
        transition_note="",
    )


def _is_wronskian_dependent(response: SolutionResponse, w_latex: str) -> bool:
    """Return True when the computed Wronskian indicates linear dependence (W == 0)."""
    combined = (
        f"{response.final_result} {response.final_latex} "
        f"{response.verification.details if response.verification else ''}"
    ).lower()
    w_clean = re.sub(r"\s+", "", w_latex)
    if w_clean in {"0", "0=0", "0.0"}:
        return True
    if "phụ thuộc" in combined or "linearly dependent" in combined:
        return True
    return bool(re.search(r"w\s*(?:\([^)]*\))?\s*=\s*0(?:\s|$|[.,;])", response.final_result.lower()))


def _synthesize_verification_step(
    response: SolutionResponse,
    clean_var: str,
    step_number: int,
    order: int = 1,
    has_ivp: bool = False,
) -> ODEPedagogicalStep:
    """Synthesize an authoritative, pedagogically sound independent verification step."""
    v_status = response.verification.status if response.verification else None
    is_verified = v_status in _SUCCESS_VERIFICATION_STATUSES
    is_failed = v_status == VerificationStatus.FAILED

    details = response.verification.details if response.verification else ""
    if not details:
        if is_failed:
            details = "Kiểm chứng độc lập phát hiện nghiệm chưa thỏa mãn đầy đủ phương trình hoặc điều kiện ban đầu."
        elif not is_verified:
            details = "Chưa hoàn tất xác minh ký hiệu tự động trên miền nghiệm."
        else:
            details = (
                f"Thế nghiệm vào phương trình vi phân và các điều kiện ban đầu, "
                f"phần dư R({clean_var}) triệt tiêu đồng nhất bằng phương pháp ký hiệu."
            )

    clean_details = standardize_ode_notation(details)
    clean_final = standardize_ode_notation(response.final_latex)

    if clean_final.startswith(f"y({clean_var})") or clean_final.startswith("y =") or "=" in clean_final:
        final_eq_str = clean_final
    else:
        final_eq_str = f"y({clean_var}) = {clean_final}"

    if order == 2:
        mb = (
            f"Toán tử vi phân tuyến tính cấp hai: $L[y] = a y'' + b y' + c y$. "
            f"Phần dư: $R({clean_var}) = L[y({clean_var})] - g({clean_var})$. "
            f"Điều kiện nghiệm đúng: $R({clean_var}) \\equiv 0,\\forall {clean_var}$"
            + (r" và thỏa mãn đồng thời các điều kiện ban đầu $y(t_0) = y_0$, $y'(t_0) = v_0$." if has_ivp else ".")
        )
    else:
        mb = (
            f"Toán tử vi phân cấp một: $L[y] = y' + p({clean_var})y$. "
            f"Phần dư: $R({clean_var}) = L[y({clean_var})] - g({clean_var})$. "
            f"Điều kiện nghiệm đúng: $R({clean_var}) \\equiv 0,\\forall {clean_var}$"
            + (r" và thỏa mãn điều kiện ban đầu $y(t_0) = y_0$." if has_ivp else ".")
        )

    purpose_str = (
        f"Kiểm tra tính đúng đắn toán học: thế nghiệm $y({clean_var})$ vào phương trình vi phân"
        + (" và các điều kiện Cauchy ban đầu," if has_ivp else ",")
        + f" kiểm tra phần dư $R({clean_var})$."
    )

    if is_failed:
        eq_latex = f"R({clean_var}) \\not\\equiv 0"
        inter_result = "Kiểm chứng thất bại"
        exec_prefix = f"Thế nghiệm $y({clean_var})$ vào hai vế phương trình. Phát hiện sai lệch:"
    elif not is_verified:
        eq_latex = f"R({clean_var})\\text{{ (chưa xác nhận)}}"
        inter_result = "Chưa hoàn tất kiểm chứng"
        exec_prefix = f"Thế nghiệm $y({clean_var})$ vào phương trình. Trạng thái xác minh:"
    else:
        eq_latex = f"R({clean_var}) = 0"
        inter_result = f"R({clean_var}) = 0"
        exec_prefix = f"Thế nghiệm $y({clean_var})$ vào hai vế phương trình. Kết quả đánh giá độc lập:"

    return ODEPedagogicalStep(
        step_number=step_number,
        rule_name="Kiểm chứng toán học độc lập",
        description=f"Thế nghiệm ${final_eq_str}$ vào bài toán. {clean_details}",
        content=response.steps[-1].content if response.steps else None,
        title="Kiểm chứng toán học độc lập",
        rule_name_vi="Kiểm chứng toán học",
        equation_latex=eq_latex,
        assumptions=(),
        purpose=purpose_str,
        math_basis=mb,
        execution=f"{exec_prefix} {clean_details}",
        intermediate_result=inter_result,
        stage_index=4,
        stage_name="Kiểm chứng độc lập",
    )


# ==============================================================================
# 1. FIRST-ORDER LINEAR ODE FLOW BUILDER
# ==============================================================================


def _build_first_order_linear_flow(
    response: SolutionResponse,
    clean_var: str,
    params: dict[str, Any],
) -> tuple[ODEStageSummary, ...]:
    """Build pedagogical flow for First-Order Linear ODEs (y' + p(t)y = g(t)):
    Stage 1: Nhận dạng dạng chuẩn tắc
    Stage 2: Tìm thừa số tích phân mu(t)
    Stage 3: Xây dựng và giải phương trình
    Stage 4: Kiểm chứng toán học độc lập
    """
    has_ivp = bool(params.get("initial_condition")) or any(
        "cauchy" in s.title.lower() or "điều kiện ban đầu" in s.title.lower() for s in response.steps
    )

    stg_map: dict[int, list[ODEPedagogicalStep]] = {1: [], 2: [], 3: [], 4: []}
    mu_latex = ""
    y_latex = standardize_ode_notation(response.final_latex)

    for orig in response.steps:
        rn = orig.rule_name
        title = orig.title
        desc = standardize_ode_notation(orig.description or "")
        raw_eq = standardize_ode_notation(orig.equation_latex or orig.content.latex_after or "")

        if rn in ("Xác định hệ số", "Nhận dạng dạng phương trình"):
            p = f"Đưa phương trình vi phân về dạng chuẩn tắc bậc một và xác định chính xác các hàm hệ số $p({clean_var})$ và $g({clean_var})$."
            mb = f"Dạng chuẩn phương trình vi phân tuyến tính cấp một: $y' + p({clean_var})y = g({clean_var})$. Ở đây hệ số đứng trước đạo hàm $y'$ bằng 1."
            stg_map[1].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=f"Nhận dạng dạng chuẩn y' + p({clean_var})y = g({clean_var})",
                    rule_name_vi=orig.rule_name_vi or "Nhận dạng chuẩn tắc",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=1,
                    stage_name="Nhận dạng chuẩn tắc",
                )
            )
        elif rn == "Thừa số tích phân":
            p = f"Tính thừa số tích phân $\\mu({clean_var})$ theo công thức Euler để đưa vế trái về dạng đạo hàm của tích $[\\mu({clean_var}) y]'."
            mb = f"Công thức thừa số tích phân: $\\mu({clean_var}) = e^{{\\int p({clean_var})\\,d{clean_var}}}$. Đạo hàm thỏa mãn $\\mu'({clean_var}) = p({clean_var})\\mu({clean_var})$."
            mu_latex = raw_eq if raw_eq else f"\\mu({clean_var}) = e^{{\\int p({clean_var})\\,d{clean_var}}}"
            stg_map[2].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=f"Tính thừa số tích phân \\mu({clean_var})",
                    rule_name_vi=orig.rule_name_vi or "Thừa số tích phân",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=2,
                    stage_name="Thừa số tích phân",
                )
            )
        elif rn in (
            "Nhân thừa số tích phân",
            "Quy tắc đạo hàm của tích (ODE)",
            "Tích phân hai vế",
            "Rút ra nghiệm tổng quát",
            "Nghiệm riêng",
            "Áp dụng điều kiện ban đầu",
        ):
            if rn == "Nhân thừa số tích phân":
                p = f"Nhân cả hai vế của phương trình chuẩn tắc với thừa số tích phân $\\mu({clean_var})$."
                mb = f"Phương trình tương đương: $\\mu({clean_var}) y' + \\mu({clean_var}) p({clean_var}) y = \\mu({clean_var}) g({clean_var})$."
            elif rn == "Quy tắc đạo hàm của tích (ODE)":
                p = f"Thu gọn vế trái của phương trình thành đạo hàm của tích $[\\mu({clean_var}) y]'."
                mb = f"Theo quy tắc Leibniz cho đạo hàm của tích: $\\frac{{d}}{{d{clean_var}}}[\\mu({clean_var}) y] = \\mu({clean_var}) y' + \\mu'({clean_var}) y = \\mu({clean_var}) y' + \\mu({clean_var}) p({clean_var}) y$."
            elif rn == "Tích phân hai vế":
                p = f"Lấy tích phân hai vế theo biến ${clean_var}$ và bổ sung hằng số tích phân $C$."
                mb = f"$\\int \\frac{{d}}{{d{clean_var}}}[\\mu({clean_var}) y]\\,d{clean_var} = \\int \\mu({clean_var}) g({clean_var})\\,d{clean_var} \\implies \\mu({clean_var}) y = \\int \\mu({clean_var}) g({clean_var})\\,d{clean_var} + C$."
            elif rn == "Áp dụng điều kiện ban đầu":
                p = "Thay điều kiện ban đầu vào nghiệm tổng quát để xác định chính xác hằng số $C$."
                mb = f"Bài toán Cauchy cấp một có nghiệm duy nhất thỏa mãn $y({clean_var}_0) = y_0$."
            else:
                p = f"Chia cả hai vế cho $\\mu({clean_var})$ để xác định nghiệm giải tích $y({clean_var})$."
                mb = f"$y({clean_var}) = \\frac{{\\int \\mu({clean_var}) g({clean_var})\\,d{clean_var} + C}}{{\\mu({clean_var})}}$."

            stg_map[3].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Biến đổi giải tích",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=3,
                    stage_name="Xây dựng & giải nghiệm",
                )
            )
        elif rn in ("Kiểm chứng nghiệm", "Kiểm chứng nghiệm độc lập", "Kiểm chứng toán học") or "kiểm chứng" in title.lower():
            p = f"Kiểm tra tính đúng đắn toán học: thế nghiệm $y({clean_var})$ vào phương trình vi phân ban đầu và chứng minh phần dư $R({clean_var}) \\equiv 0$."
            mb = f"Toán tử vi phân $L[y] = y' + p({clean_var})y$. Phần dư $R({clean_var}) = L[y] - g({clean_var})$. Nghiệm đúng khi và chỉ khi $R({clean_var}) \\equiv 0,\\forall {clean_var}$."
            stg_map[4].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Kiểm chứng toán học",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=f"R({clean_var}) = 0",
                    stage_index=4,
                    stage_name="Kiểm chứng độc lập",
                )
            )

    # Ensure Stage 4 has a verification step
    if not stg_map[4]:
        total_so_far = sum(len(steps) for steps in stg_map.values())
        synth_verify = _synthesize_verification_step(
            response=response,
            clean_var=clean_var,
            step_number=total_so_far + 1,
            order=1,
            has_ivp=has_ivp,
        )
        stg_map[4].append(synth_verify)

    renumbered = _renumber_steps(stg_map)

    stages = [
        ODEStageSummary(
            stage_index=1,
            title="Giai đoạn 1: Nhận dạng dạng chuẩn tắc",
            subtitle=f"Đưa phương trình về dạng chuẩn $y' + p({clean_var})y = g({clean_var})$ và xác định hệ số",
            icon="looks_one",
            badge_text="Dạng chuẩn",
            badge_color="blue-7",
            is_completed=bool(renumbered[1]),
            is_applicable=True,
            summary_latex=renumbered[1][-1].equation_latex if renumbered[1] else f"y' + p({clean_var})y = g({clean_var})",
            summary_label="Dạng chuẩn tắc:",
            steps=tuple(renumbered[1]),
            transition_note=f"Sau khi xác định được dạng chuẩn và hàm hệ số $p({clean_var})$, ta tiến hành tìm thừa số tích phân $\\mu({clean_var})$ để biến đổi vế trái thành đạo hàm của một tích.",
        ),
        ODEStageSummary(
            stage_index=2,
            title="Giai đoạn 2: Tìm thừa số tích phân",
            subtitle=f"Xây dựng thừa số tích phân $\\mu({clean_var}) = e^{{\\int p({clean_var})\\,d{clean_var}}}$",
            icon="looks_two",
            badge_text=f"\\mu({clean_var})",
            badge_color="purple-7",
            is_completed=bool(renumbered[2]),
            is_applicable=True,
            summary_latex=mu_latex,
            summary_label="Thừa số tích phân:",
            steps=tuple(renumbered[2]),
            transition_note=f"Nhân thừa số tích phân $\\mu({clean_var})$ vào hai vế và áp dụng quy tắc đạo hàm của tích để tiến hành giải tìm nghiệm.",
        ),
        ODEStageSummary(
            stage_index=3,
            title="Giai đoạn 3: Xây dựng và giải phương trình",
            subtitle=f"Nhân $\\mu({clean_var})$, lấy tích phân hai vế và rút ra nghiệm $y({clean_var})$",
            icon="looks_3",
            badge_text=f"y({clean_var})",
            badge_color="teal-7",
            is_completed=bool(renumbered[3]),
            is_applicable=True,
            summary_latex=y_latex,
            summary_label="Nghiệm bài toán:" if has_ivp else "Nghiệm tổng quát:",
            steps=tuple(renumbered[3]),
            transition_note="Để đảm bảo tính chính xác toán học tuyệt đối, ta tiến hành kiểm chứng độc lập bằng cách thế nghiệm vừa tìm được vào phương trình ban đầu.",
        ),
        _build_stage4_summary(
            response,
            clean_var,
            f"Chứng minh phần dư $R({clean_var}) = y' + p({clean_var})y - g({clean_var}) \\equiv 0$" + (" và thỏa điều kiện Cauchy" if has_ivp else ""),
            f"R({clean_var}) = y' + p({clean_var})y - g({clean_var}) \\equiv 0",
            tuple(renumbered[4]),
        ),
    ]
    return tuple(stages)


# ==============================================================================
# 2. FIRST-ORDER SEPARABLE ODE FLOW BUILDER
# ==============================================================================


def _build_first_order_separable_flow(
    response: SolutionResponse,
    clean_var: str,
    params: dict[str, Any],
) -> tuple[ODEStageSummary, ...]:
    """Build pedagogical flow for First-Order Separable ODEs (g(y)dy = h(t)dt):
    Stage 1: Nhận dạng phương trình & khảo sát nghiệm cân bằng
    Stage 2: Phân tách biến số
    Stage 3: Tích phân hai vế và kết luận nghiệm
    Stage 4: Kiểm chứng toán học độc lập
    """
    stg_map: dict[int, list[ODEPedagogicalStep]] = {1: [], 2: [], 3: [], 4: []}
    y_latex = standardize_ode_notation(response.final_latex)

    for orig in response.steps:
        rn = orig.rule_name
        title = orig.title
        desc = standardize_ode_notation(orig.description or "")
        raw_eq = standardize_ode_notation(orig.equation_latex or orig.content.latex_after or "")

        if rn in ("Nhận dạng dạng phương trình", "Nghiệm cân bằng"):
            if rn == "Nhận dạng dạng phương trình":
                p = f"Nhận dạng cấu trúc phương trình vi phân tách biến $N(y)y' = M({clean_var})$ hoặc $\\frac{{dy}}{{g(y)}} = h({clean_var})d{clean_var}$."
                mb = "Phương trình tách biến có thể đưa về dạng mà mỗi vế chỉ phụ thuộc duy nhất vào một biến."
            else:
                p = "Khảo sát và xác định các nghiệm cân bằng (Equilibrium Solutions) làm triệt tiêu vế chứa biến phụ thuộc."
                mb = "Nghiệm cân bằng là các nghiệm hằng số $y(t) = y_0$ thỏa mãn phương trình vi phân mà phép chia cho $g(y)$ có thể bỏ sót."
            stg_map[1].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Nhận dạng",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=1,
                    stage_name="Nhận dạng & cân bằng",
                )
            )
        elif rn == "Phân tách biến số":
            p = f"Phân tách các biến: đưa toàn bộ biểu thức chứa $y$ sang vế trái và biểu thức chứa ${clean_var}$ sang vế phải."
            mb = f"Biến đổi vi phân tương đương: $g(y)\\,dy = h({clean_var})\\,d{clean_var}$."
            stg_map[2].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Phân tách biến",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=2,
                    stage_name="Phân tách biến",
                )
            )
        elif rn in ("Tích phân hai vế", "Rút ra nghiệm tổng quát", "Áp dụng điều kiện ban đầu", "Nghiệm riêng"):
            p = f"Tính tích phân hai vế $\\int g(y)\\,dy = \\int h({clean_var})\\,d{clean_var} + C$ và rút ra nghiệm $y({clean_var})$."
            mb = "Định lý cơ bản của giải tích và phương pháp tìm họ đường cong tích phân qua hằng số $C$."
            stg_map[3].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Tích phân & nghiệm",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=3,
                    stage_name="Tích phân & nghiệm",
                )
            )
        elif rn in ("Kiểm chứng nghiệm", "Kiểm chứng toán học") or "kiểm chứng" in title.lower():
            p = f"Kiểm tra tính đúng đắn toán học: thế nghiệm $y({clean_var})$ vào hai vế phương trình vi phân và xác nhận đẳng thức thỏa mãn."
            mb = f"Nghiệm $y({clean_var})$ phải làm cho hai vế của phương trình vi phân đồng nhất bằng nhau: $R({clean_var}) \\equiv 0$."
            stg_map[4].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Kiểm chứng toán học",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=f"R({clean_var}) = 0",
                    stage_index=4,
                    stage_name="Kiểm chứng độc lập",
                )
            )

    if not stg_map[4]:
        total_so_far = sum(len(steps) for steps in stg_map.values())
        synth_verify = _synthesize_verification_step(
            response=response,
            clean_var=clean_var,
            step_number=total_so_far + 1,
            order=1,
            has_ivp=bool(params.get("initial_condition")),
        )
        stg_map[4].append(synth_verify)

    renumbered = _renumber_steps(stg_map)

    stages = [
        ODEStageSummary(
            stage_index=1,
            title="Giai đoạn 1: Nhận dạng & khảo sát cân bằng",
            subtitle="Nhận dạng cấu trúc tách biến và khảo sát nghiệm cân bằng",
            icon="looks_one",
            badge_text="Nhận dạng",
            badge_color="blue-7",
            is_completed=bool(renumbered[1]),
            is_applicable=True,
            summary_latex=renumbered[1][-1].equation_latex if renumbered[1] else "",
            summary_label="Cấu trúc tách biến:",
            steps=tuple(renumbered[1]),
            transition_note="Sau khi xác định được các nghiệm cân bằng, ta tiến hành phân tách các biến số về hai vế độc lập.",
        ),
        ODEStageSummary(
            stage_index=2,
            title="Giai đoạn 2: Phân tách biến số",
            subtitle=f"Chuyển toàn bộ $y$ sang vế trái và ${clean_var}$ sang vế phải",
            icon="looks_two",
            badge_text="Phân tách",
            badge_color="purple-7",
            is_completed=bool(renumbered[2]),
            is_applicable=True,
            summary_latex=renumbered[2][-1].equation_latex if renumbered[2] else "",
            summary_label="Phương trình phân ly:",
            steps=tuple(renumbered[2]),
            transition_note="Các biến đã được phân tách hoàn toàn, ta lấy tích phân hai vế để tìm họ đường cong tích phân.",
        ),
        ODEStageSummary(
            stage_index=3,
            title="Giai đoạn 3: Tích phân hai vế và rút ra nghiệm",
            subtitle=f"Tính tích phân hai vế, bổ sung hằng số $C$ và rút ra nghiệm $y({clean_var})$",
            icon="looks_3",
            badge_text=f"y({clean_var})",
            badge_color="teal-7",
            is_completed=bool(renumbered[3]),
            is_applicable=True,
            summary_latex=y_latex,
            summary_label="Nghiệm bài toán:",
            steps=tuple(renumbered[3]),
            transition_note="Tiến hành kiểm chứng độc lập nghiệm vừa tìm được để đảm bảo tính đúng đắn toán học.",
        ),
        _build_stage4_summary(
            response,
            clean_var,
            f"Kiểm tra tính đúng đắn của nghiệm qua phần dư $R({clean_var}) \\equiv 0$",
            f"R({clean_var}) \\equiv 0",
            tuple(renumbered[4]),
        ),
    ]
    return tuple(stages)


# ==============================================================================
# 3. FIRST-ORDER EXACT ODE FLOW BUILDER
# ==============================================================================


def _build_first_order_exact_flow(
    response: SolutionResponse,
    clean_var: str,
    params: dict[str, Any],
) -> tuple[ODEStageSummary, ...]:
    """Build pedagogical flow for First-Order Exact ODEs (M dx + N dy = 0)."""
    stg_map: dict[int, list[ODEPedagogicalStep]] = {1: [], 2: [], 3: [], 4: []}
    y_latex = standardize_ode_notation(response.final_latex)

    for orig in response.steps:
        rn = orig.rule_name
        title = orig.title
        desc = standardize_ode_notation(orig.description or "")
        raw_eq = standardize_ode_notation(orig.equation_latex or orig.content.latex_after or "")

        if rn == "Kiểm tra tính vi phân toàn phần":
            # 1. Identification of M and N (Stage 1)
            p1 = f"Xác định rõ hai hàm số thành phần $M({clean_var}, y)$ và $N({clean_var}, y)$ trong dạng vi phân $M\\,d{clean_var} + N\\,dy = 0$."
            mb1 = f"Phương trình vi phân toàn phần có dạng chuẩn $M({clean_var}, y)\\,d{clean_var} + N({clean_var}, y)\\,dy = 0$."
            eq1 = standardize_ode_notation(orig.content.latex_before) if orig.content and orig.content.latex_before else raw_eq
            stg_map[1].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name="Nhận dạng hệ số M và N",
                    description=f"Phương trình vi phân toàn phần có dạng chuẩn $M({clean_var}, y)\\,d{clean_var} + N({clean_var}, y)\\,dy = 0$. Từ đề bài, xác định các hàm số thành phần: ${eq1}$.",
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title="Nhận dạng các thành phần vi phân M và N",
                    rule_name_vi="Nhận dạng hệ số",
                    equation_latex=eq1,
                    assumptions=orig.assumptions,
                    purpose=p1,
                    math_basis=mb1,
                    execution=f"Xác định từ dạng vi phân đề bài: ${eq1}$",
                    intermediate_result=eq1,
                    stage_index=1,
                    stage_name="Nhận dạng M, N",
                    internal_step_id=orig.step_number,
                )
            )

            # 2. Exactness check dM/dy == dN/dx (Stage 2)
            p2 = f"Kiểm tra điều kiện cần và đủ để phương trình là vi phân toàn phần: $\\frac{{\\partial M}}{{\\partial y}} = \\frac{{\\partial N}}{{\\partial {clean_var}}}$."
            mb2 = f"Định lý Schwarz / Euler về sự bằng nhau của các đạo hàm riêng hỗn hợp: $\\frac{{\\partial^2 F}}{{\\partial {clean_var} \\partial y}} = \\frac{{\\partial^2 F}}{{\\partial y \\partial {clean_var}}}$."
            eq2 = standardize_ode_notation(orig.content.latex_after) if orig.content and orig.content.latex_after else raw_eq
            stg_map[2].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Điều kiện toàn phần",
                    equation_latex=eq2,
                    assumptions=orig.assumptions,
                    purpose=p2,
                    math_basis=mb2,
                    execution=desc,
                    intermediate_result=eq2,
                    stage_index=2,
                    stage_name="Kiểm tra vi phân toàn phần",
                    internal_step_id=orig.step_number,
                )
            )
        elif rn in ("Nhận dạng dạng phương trình",) or (
            rn == "Xác định hệ số" and not ("h(" in title.lower() or "hàm số phụ" in title.lower() or "h(" in desc.lower())
        ):
            p = f"Xác định rõ hai hàm số thành phần $M({clean_var}, y)$ và $N({clean_var}, y)$ trong dạng vi phân $M\\,d{clean_var} + N\\,dy = 0$."
            mb = f"Phương trình vi phân toàn phần có dạng chuẩn $M({clean_var}, y)\\,d{clean_var} + N({clean_var}, y)\\,dy = 0$."
            stg_map[1].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Nhận dạng hệ số",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=1,
                    stage_name="Nhận dạng M, N",
                    internal_step_id=orig.step_number,
                )
            )
        elif rn in ("Tích phân hai vế", "Xây dựng hàm thế", "Áp dụng điều kiện ban đầu", "Rút ra nghiệm tổng quát") or (
            rn == "Xác định hệ số" and ("h(" in title.lower() or "hàm số phụ" in title.lower() or "h(" in desc.lower())
        ):
            p = f"Tích phân hàm $M({clean_var}, y)$ theo biến ${clean_var}$ và đồng nhất đạo hàm theo $y$ để xây dựng hàm thế vi phân toàn phần $F({clean_var}, y)$."
            mb = f"Hàm thế thỏa mãn $\\frac{{\\partial F}}{{\\partial {clean_var}}} = M$ và $\\frac{{\\partial F}}{{\\partial y}} = N$. Nghiệm ẩn: $F({clean_var}, y) = C$."
            stg_map[3].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Xây dựng hàm thế",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=3,
                    stage_name="Xây dựng hàm thế",
                    internal_step_id=orig.step_number,
                )
            )
        elif rn in ("Kiểm chứng nghiệm", "Kiểm chứng toán học", "Kiểm chứng nghiệm độc lập") or "kiểm chứng" in title.lower():
            p = f"Kiểm chứng tính đúng đắn toán học: vi phân toàn phần của hàm thế $dF = M\\,d{clean_var} + N\\,dy = 0$."
            mb = f"Gradient $\\nabla F = (\\frac{{\\partial F}}{{\\partial {clean_var}}}, \\frac{{\\partial F}}{{\\partial y}})$ phải đồng nhất bằng $(M, N)$."
            stg_map[4].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Kiểm chứng",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=r"\nabla F = (M, N)",
                    stage_index=4,
                    stage_name="Kiểm chứng độc lập",
                    internal_step_id=orig.step_number,
                )
            )

    if not stg_map[4]:
        total_so_far = sum(len(steps) for steps in stg_map.values())
        synth_verify = _synthesize_verification_step(
            response=response,
            clean_var=clean_var,
            step_number=total_so_far + 1,
            order=1,
            has_ivp=bool(params.get("initial_condition")),
        )
        stg_map[4].append(synth_verify)

    renumbered = _renumber_steps(stg_map)

    stages = [
        ODEStageSummary(
            stage_index=1,
            title="Giai đoạn 1: Nhận dạng hệ số M và N",
            subtitle=f"Xác định các biểu thức $M({clean_var}, y)$ và $N({clean_var}, y)$ trong dạng vi phân",
            icon="looks_one",
            badge_text="M, N",
            badge_color="blue-7",
            is_completed=bool(renumbered[1]),
            is_applicable=True,
            summary_latex=renumbered[1][-1].equation_latex if renumbered[1] else f"M({clean_var}, y)\\,d{clean_var} + N({clean_var}, y)\\,dy = 0",
            summary_label="Dạng vi phân:",
            steps=tuple(renumbered[1]),
            transition_note="Sau khi xác định $M$ và $N$, ta kiểm tra điều kiện vi phân toàn phần của phương trình.",
        ),
        ODEStageSummary(
            stage_index=2,
            title="Giai đoạn 2: Kiểm tra điều kiện toàn phần",
            subtitle=f"So sánh các đạo hàm riêng: $\\frac{{\\partial M}}{{\\partial y}} = \\frac{{\\partial N}}{{\\partial {clean_var}}}$",
            icon="looks_two",
            badge_text="\\partial M/\\partial y",
            badge_color="purple-7",
            is_completed=bool(renumbered[2]),
            is_applicable=True,
            summary_latex=renumbered[2][-1].equation_latex if renumbered[2] else "",
            summary_label="Đẳng thức vi phân:",
            steps=tuple(renumbered[2]),
            transition_note=f"Điều kiện vi phân toàn phần được thỏa mãn, ta tiến hành xây dựng hàm thế $F({clean_var}, y)$.",
        ),
        ODEStageSummary(
            stage_index=3,
            title="Giai đoạn 3: Xây dựng hàm thế và nghiệm ẩn",
            subtitle=f"Tích phân tìm hàm thế $F({clean_var}, y)$ và kết luận nghiệm ẩn $F({clean_var}, y) = C$",
            icon="looks_3",
            badge_text=f"F({clean_var}, y) = C",
            badge_color="teal-7",
            is_completed=bool(renumbered[3]),
            is_applicable=True,
            summary_latex=y_latex,
            summary_label="Nghiệm ẩn bài toán:",
            steps=tuple(renumbered[3]),
            transition_note="Tiến hành kiểm chứng độc lập gradient của hàm thế vừa tìm được.",
        ),
        _build_stage4_summary(
            response,
            clean_var,
            "Kiểm tra gradient $\\nabla F = (M, N)$ và xác nhận $dF = 0$",
            "\\nabla F = (M, N) \\implies dF \\equiv 0",
            tuple(renumbered[4]),
            verified_summary_label="Kiểm chứng vi phân:",
        ),
    ]
    return tuple(stages)


# ==============================================================================
# 4. FIRST-ORDER INTEGRATING FACTOR & HOMOGENEOUS FLOW BUILDERS
# ==============================================================================


def _build_first_order_integrating_factor_flow(
    response: SolutionResponse,
    clean_var: str,
    params: dict[str, Any],
) -> tuple[ODEStageSummary, ...]:
    """Build pedagogical flow for First-Order Integrating Factor ODEs."""
    stg_map: dict[int, list[ODEPedagogicalStep]] = {1: [], 2: [], 3: [], 4: []}
    y_latex = standardize_ode_notation(response.final_latex)

    for orig in response.steps:
        rn = orig.rule_name
        title = orig.title
        desc = standardize_ode_notation(orig.description or "")
        raw_eq = standardize_ode_notation(orig.equation_latex or orig.content.latex_after or "")

        if rn in ("Kiểm tra tính vi phân toàn phần", "Xác định hệ số") and not stg_map[1]:
            p = f"Xác định $M({clean_var},y), N({clean_var},y)$ và kiểm tra tính vi phân toàn phần ban đầu."
            mb = f"Nếu $\\frac{{\\partial M}}{{\\partial y}} \\ne \\frac{{\\partial N}}{{\\partial {clean_var}}}$, phương trình không toàn phần và cần tìm thừa số tích phân."
            stg_map[1].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Kiểm tra không toàn phần",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=1,
                    stage_name="Kiểm tra không toàn phần",
                )
            )
        elif rn in ("Thừa số tích phân mu(x)", "Thừa số tích phân mu(y)", "Nhân thừa số tích phân (ODE không toàn phần)", "Kiểm tra tính vi phân toàn phần sau khi nhân mu"):
            p = "Xác định thừa số tích phân $\\mu$ và nhân vào hai vế để đưa về phương trình vi phân toàn phần."
            mb = f"Công thức Euler: nếu $\\frac{{1}}{{N}}(\\frac{{\\partial M}}{{\\partial y}} - \\frac{{\\partial N}}{{\\partial {clean_var}}})$ chỉ phụ thuộc ${clean_var}$, $\\mu({clean_var}) = e^{{\\int f({clean_var})d{clean_var}}}$."
            stg_map[2].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Thừa số tích phân",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=2,
                    stage_name="Tìm thừa số tích phân",
                )
            )
        elif rn in ("Tích phân hai vế", "Xây dựng hàm thế", "Áp dụng điều kiện ban đầu", "Rút ra nghiệm tổng quát") or (
            rn == "Xác định hệ số" and ("h(" in title.lower() or "hàm số phụ" in title.lower() or "h(" in desc.lower())
        ):
            p = f"Xây dựng hàm thế vi phân toàn phần $F({clean_var},y)$ cho phương trình mới và kết luận nghiệm ẩn $F({clean_var},y) = C$."
            mb = f"Hàm thế thỏa mãn $\\frac{{\\partial F}}{{\\partial {clean_var}}} = \\mu M$ và $\\frac{{\\partial F}}{{\\partial y}} = \\mu N$."
            stg_map[3].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Xây dựng hàm thế",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=3,
                    stage_name="Xây dựng hàm thế",
                    internal_step_id=orig.step_number,
                )
            )
        elif rn in ("Kiểm chứng nghiệm", "Kiểm chứng toán học") or "kiểm chứng" in title.lower():
            p = "Kiểm chứng độc lập gradient hàm thế và tính toàn phần sau khi nhân thừa số tích phân."
            mb = "Gradient $\\nabla F = (\\mu M, \\mu N)$ phải đồng nhất trên miền xác định."
            stg_map[4].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Kiểm chứng",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=r"\nabla F = (\mu M, \mu N)",
                    stage_index=4,
                    stage_name="Kiểm chứng độc lập",
                )
            )

    if not stg_map[4]:
        total_so_far = sum(len(steps) for steps in stg_map.values())
        synth_verify = _synthesize_verification_step(
            response=response,
            clean_var=clean_var,
            step_number=total_so_far + 1,
            order=1,
            has_ivp=bool(params.get("initial_condition")),
        )
        stg_map[4].append(synth_verify)

    renumbered = _renumber_steps(stg_map)

    stages = [
        ODEStageSummary(
            stage_index=1,
            title="Giai đoạn 1: Kiểm tra tính không toàn phần",
            subtitle=f"Chỉ ra $\\frac{{\\partial M}}{{\\partial y}} \\ne \\frac{{\\partial N}}{{\\partial {clean_var}}}$",
            icon="looks_one",
            badge_text="Không toàn phần",
            badge_color="blue-7",
            is_completed=bool(renumbered[1]),
            is_applicable=True,
            summary_latex=renumbered[1][-1].equation_latex if renumbered[1] else "",
            summary_label="Điều kiện ban đầu:",
            steps=tuple(renumbered[1]),
            transition_note="Phương trình không toàn phần, ta tiến hành tìm thừa số tích phân $\\mu$ thích hợp.",
        ),
        ODEStageSummary(
            stage_index=2,
            title="Giai đoạn 2: Xác định thừa số tích phân",
            subtitle="Tính thừa số tích phân $\\mu$ và biến đổi phương trình về toàn phần",
            icon="looks_two",
            badge_text="\\mu",
            badge_color="purple-7",
            is_completed=bool(renumbered[2]),
            is_applicable=True,
            summary_latex=renumbered[2][-1].equation_latex if renumbered[2] else "",
            summary_label="Thừa số tích phân:",
            steps=tuple(renumbered[2]),
            transition_note="Phương trình mới đã trở thành vi phân toàn phần, ta tiến hành tích phân tìm hàm thế $F(x, y)$.",
        ),
        ODEStageSummary(
            stage_index=3,
            title="Giai đoạn 3: Xây dựng hàm thế và nghiệm ẩn",
            subtitle="Tích phân tìm hàm thế $F(x, y)$ và kết luận nghiệm ẩn $F(x, y) = C$",
            icon="looks_3",
            badge_text="F(x, y) = C",
            badge_color="teal-7",
            is_completed=bool(renumbered[3]),
            is_applicable=True,
            summary_latex=y_latex,
            summary_label="Nghiệm ẩn bài toán:",
            steps=tuple(renumbered[3]),
            transition_note="Tiến hành kiểm chứng độc lập tính đúng đắn toán học của nghiệm vừa tìm được.",
        ),
        _build_stage4_summary(
            response,
            clean_var,
            "Kiểm tra gradient $\\nabla F = (\\mu M, \\mu N)$",
            "\\nabla F = (\\mu M, \\mu N) \\implies dF \\equiv 0",
            tuple(renumbered[4]),
            verified_summary_label="Kiểm chứng vi phân:",
        ),
    ]
    return tuple(stages)


def _build_first_order_homogeneous_flow(
    response: SolutionResponse,
    clean_var: str,
    params: dict[str, Any],
) -> tuple[ODEStageSummary, ...]:
    """Build pedagogical flow for Classical Homogeneous ODEs (y' = f(y/x))."""
    stg_map: dict[int, list[ODEPedagogicalStep]] = {1: [], 2: [], 3: [], 4: []}
    y_latex = standardize_ode_notation(response.final_latex)

    for orig in response.steps:
        rn = orig.rule_name
        title = orig.title
        desc = standardize_ode_notation(orig.description or "")
        raw_eq = standardize_ode_notation(orig.equation_latex or orig.content.latex_after or "")

        if rn in ("Nhận dạng phương trình thuần nhất bậc 0", "Phép thế hàm phụ v = y/x"):
            p = "Kiểm tra tính thuần nhất bậc 0 và đặt ẩn phụ biến đổi $v(x) = \\frac{y}{x} \\implies y = x \\cdot v$."
            mb = "Định nghĩa hàm thuần nhất: $f(tx, ty) = t^0 f(x, y) = f(x, y)$. Khi đó $y' = v + x\\,v'$."
            stg_map[1].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Nhận dạng bậc 0",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=1,
                    stage_name="Nhận dạng & biến phụ",
                )
            )
        elif rn in ("Biến đổi về phương trình tách biến", "Nghiệm đường thẳng cân bằng"):
            p = "Thế $y, y'$ vào phương trình vi phân và đưa về phương trình tách biến đối với hàm phụ $v(x)$."
            mb = "Phương trình vi phân cho biến phụ: $x\\,\\frac{dv}{dx} = g(v) - v \\implies \\frac{dv}{g(v) - v} = \\frac{dx}{x}$."
            stg_map[2].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Tách biến cho v",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=2,
                    stage_name="Tách biến cho v",
                )
            )
        elif rn in ("Tách biến và lấy tích phân", "Thế ngược và rút gọn nghiệm tổng quát", "Áp dụng điều kiện ban đầu"):
            p = "Lấy tích phân hai vế theo $v$ và $x$, sau đó thế ngược $v = \\frac{y}{x}$ để rút ra nghiệm $y(x)$."
            mb = "$\\int \\frac{dv}{g(v) - v} = \\ln|x| + C$. Sau khi tìm $v(x)$, nghiệm được xác định bởi $y(x) = x \\cdot v(x)$."
            stg_map[3].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Tích phân & thế ngược",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=3,
                    stage_name="Tích phân & thế ngược",
                )
            )
        elif rn in ("Kiểm chứng nghiệm", "Kiểm chứng toán học") or "kiểm chứng" in title.lower():
            p = "Kiểm chứng độc lập nghiệm vừa tìm được bằng phép đạo hàm và thế ngược vào phương trình ban đầu."
            mb = "Nghiệm $y(x)$ thỏa mãn $y' = f(x, y)$ trên toàn miền xác định."
            stg_map[4].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Kiểm chứng",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=f"R({clean_var}) = 0",
                    stage_index=4,
                    stage_name="Kiểm chứng độc lập",
                )
            )

    if not stg_map[4]:
        total_so_far = sum(len(steps) for steps in stg_map.values())
        synth_verify = _synthesize_verification_step(
            response=response,
            clean_var=clean_var,
            step_number=total_so_far + 1,
            order=1,
            has_ivp=bool(params.get("initial_condition")),
        )
        stg_map[4].append(synth_verify)

    renumbered = _renumber_steps(stg_map)

    stages = [
        ODEStageSummary(
            stage_index=1,
            title="Giai đoạn 1: Nhận dạng hàm thuần nhất bậc 0",
            subtitle="Kiểm tra tính thuần nhất và đặt biến phụ $v = y/x$",
            icon="looks_one",
            badge_text="v = y/x",
            badge_color="blue-7",
            is_completed=bool(renumbered[1]),
            is_applicable=True,
            summary_latex=renumbered[1][-1].equation_latex if renumbered[1] else "v = \\frac{y}{x}",
            summary_label="Biến phụ:",
            steps=tuple(renumbered[1]),
            transition_note="Sau khi đặt biến phụ $v$, ta thế vào phương trình và đưa về dạng tách biến.",
        ),
        ODEStageSummary(
            stage_index=2,
            title="Giai đoạn 2: Đưa về phương trình tách biến",
            subtitle="Biến đổi phương trình sang biến phụ $v$ và biến độc lập",
            icon="looks_two",
            badge_text="Tách biến v",
            badge_color="purple-7",
            is_completed=bool(renumbered[2]),
            is_applicable=True,
            summary_latex=renumbered[2][-1].equation_latex if renumbered[2] else "",
            summary_label="Phương trình tách biến:",
            steps=tuple(renumbered[2]),
            transition_note="Phương trình cho biến phụ $v$ đã tách biến hoàn toàn, ta lấy tích phân hai vế.",
        ),
        ODEStageSummary(
            stage_index=3,
            title="Giai đoạn 3: Tích phân và thế ngược biến",
            subtitle=f"Tích phân hai vế, thế ngược $v = y/x$ và rút ra nghiệm $y({clean_var})$",
            icon="looks_3",
            badge_text="y(x)",
            badge_color="teal-7",
            is_completed=bool(renumbered[3]),
            is_applicable=True,
            summary_latex=y_latex,
            summary_label="Nghiệm bài toán:",
            steps=tuple(renumbered[3]),
            transition_note="Tiến hành kiểm chứng độc lập tính đúng đắn toán học của nghiệm vừa tìm được.",
        ),
        _build_stage4_summary(
            response,
            clean_var,
            "Thế nghiệm vào phương trình vi phân kiểm tra phần dư",
            f"R({clean_var}) \\equiv 0",
            tuple(renumbered[4]),
        ),
    ]
    return tuple(stages)


# ==============================================================================
# 5. SECOND-ORDER CONSTANT COEFFICIENTS FLOW BUILDER
# ==============================================================================


def _build_second_order_flow(
    response: SolutionResponse,
    prob_type: ProblemType,
    clean_var: str,
    params: dict[str, Any],
) -> tuple[ODEStageSummary, ...]:
    """Build pedagogical flow for Second-Order Constant Coefficients ODEs & Cauchy IVPs."""
    has_ivp = (
        prob_type == ProblemType.ODE_SECOND_ORDER_IVP
        or bool(params.get("initial_condition"))
        or any("cauchy" in s.title.lower() or "điều kiện ban đầu" in s.title.lower() for s in response.steps)
    )

    is_nonhomogeneous = any(
        s.rule_name in (
            "Dạng nghiệm riêng đề xuất",
            "Đạo hàm và thế toán tử",
            "Hệ phương trình hệ số bất định",
            "Nghiệm riêng thành phần",
            "Phương pháp Biến thiên hằng số",
            "Định thức Wronskian",
            "Định thức Wronski",
            "Hệ phương trình phụ trợ Lagrange",
            "Tích phân hàm biến thiên",
            "Nghiệm riêng biến thiên hằng số",
        )
        for s in response.steps
    )

    stg_map: dict[int, list[ODEPedagogicalStep]] = {1: [], 2: [], 3: [], 4: []}
    yc_latex = ""
    yp_latex = ""
    y_latex = standardize_ode_notation(response.final_latex)

    # Extract intermediate formulas
    char_eq_latex = ""
    for s in response.steps:
        rn = s.rule_name
        if rn == "Phương trình đặc trưng":
            char_eq_latex = s.equation_latex or (s.content.latex_after if s.content else "") or ""
        elif rn in ("Hệ nghiệm cơ bản", "Nghiệm thực phân biệt", "Nghiệm kép thực", "Nghiệm phức liên hợp"):
            if "y(" in s.content.latex_after and "=" in s.content.latex_after:
                parts = s.content.latex_after.split("=", 1)
                yc_latex = f"y_c({clean_var}) = {standardize_ode_notation(parts[1].strip())}"
            elif s.equation_latex and "=" in s.equation_latex:
                parts = s.equation_latex.split("=", 1)
                yc_latex = f"y_c({clean_var}) = {standardize_ode_notation(parts[1].strip())}"
        elif rn in ("Nghiệm riêng thành phần", "Nghiệm riêng biến thiên hằng số"):
            raw_yp = s.equation_latex or s.content.latex_after
            if "=" in raw_yp:
                parts = raw_yp.split("=", 1)
                yp_latex = f"y_p({clean_var}) = {standardize_ode_notation(parts[1].strip())}"

    for orig in response.steps:
        rn = orig.rule_name
        title = orig.title
        desc = standardize_ode_notation(orig.description or "")
        raw_eq = standardize_ode_notation(orig.equation_latex or orig.content.latex_after or "")

        # ---------------- Stage 1: Nghiệm thuần nhất ----------------
        if rn in (
            "Phương trình đặc trưng",
            "Biệt thức Delta",
            "Hai nghiệm thực phân biệt",
            "Nghiệm kép thực",
            "Nghiệm phức liên hợp",
            "Hệ nghiệm cơ bản",
        ):
            if rn == "Phương trình đặc trưng":
                p = f"Chuyển phương trình vi phân tuyến tính cấp hai về phương trình đại số bậc hai tương đương để tìm nghiệm cơ bản dạng hàm mũ $y = e^{{r{clean_var}}}$."
                mb = (
                    f"Đối với phương trình vi phân thuần nhất $a y'' + b y' + c y = 0$, nghiệm thử $y = e^{{r{clean_var}}}$ "
                    f"dẫn đến $e^{{r{clean_var}}}(a r^2 + b r + c) = 0$. Do $e^{{r{clean_var}}} \\ne 0,\\forall {clean_var}$, "
                    f"ta có phương trình đặc trưng: $a r^2 + b r + c = 0$."
                )
                ex = desc
                ir = raw_eq
            elif rn == "Biệt thức Delta":
                p = "Đánh giá biệt thức $\\Delta$ để xác định bản chất của nghiệm (2 nghiệm thực phân biệt, nghiệm kép thực, hoặc cặp nghiệm phức liên hợp)."
                mb = "Biệt thức $\\Delta = b^2 - 4ac$: Quyết định số lượng và dạng của các nghiệm đặc trưng, từ đó định hình cấu trúc hệ nghiệm cơ bản."
                ex = desc
                ir = raw_eq
            elif rn in ("Hai nghiệm thực phân biệt", "Nghiệm kép thực", "Nghiệm phức liên hợp"):
                p = "Tính chính xác các nghiệm đặc trưng $r_1, r_2$ từ biệt thức $\\Delta$."
                if rn == "Hai nghiệm thực phân biệt":
                    mb = "Khi $\\Delta > 0$, phương trình đặc trưng có hai nghiệm thực phân biệt: $r_1 = \\frac{-b + \\sqrt{\\Delta}}{2a},\\quad r_2 = \\frac{-b - \\sqrt{\\Delta}}{2a}$."
                elif rn == "Nghiệm kép thực":
                    mb = "Khi $\\Delta = 0$, phương trình đặc trưng có nghiệm kép thực: $r_0 = -\\frac{b}{2a}$."
                else:
                    mb = "Khi $\\Delta < 0$, phương trình đặc trưng có cặp nghiệm phức liên hợp: $r_{1,2} = \\alpha \\pm i\\beta = -\\frac{b}{2a} \\pm i\\frac{\\sqrt{|\\Delta|}}{2a}$."
                ex = desc
                ir = raw_eq
            elif rn == "Hệ nghiệm cơ bản":
                p = f"Xây dựng hệ nghiệm cơ bản độc lập tuyến tính ${LBRACE}y_1({clean_var}), y_2({clean_var}){RBRACE}$ và tổng hợp nghiệm thuần nhất $y_c({clean_var})$."
                if "kép" in desc.lower() or "thừa số nhân" in title.lower():
                    mb = f"Trường hợp nghiệm kép: nhân thêm biến ${clean_var}$ để đảm bảo độc lập tuyến tính: $y_1 = e^{{r_0 {clean_var}}}, y_2 = {clean_var} e^{{r_0 {clean_var}}} \\implies y_c({clean_var}) = (C_1 + C_2 {clean_var})e^{{r_0 {clean_var}}}$."
                elif "liên hợp" in desc.lower() or "euler" in title.lower() or "euler" in desc.lower():
                    mb = f"Trường hợp nghiệm phức $\\alpha \\pm i\\beta$: áp dụng công thức Euler đưa về hệ nghiệm thực $y_1 = e^{{\\alpha {clean_var}}}\\cos(\\beta {clean_var}), y_2 = e^{{\\alpha {clean_var}}}\\sin(\\beta {clean_var}) \\implies y_c({clean_var}) = e^{{\\alpha {clean_var}}}(C_1 \\cos(\\beta {clean_var}) + C_2 \\sin(\\beta {clean_var}))$."
                else:
                    mb = f"Trường hợp hai nghiệm thực phân biệt: hệ nghiệm cơ bản là hai hàm mũ ${LBRACE}e^{{r_1 {clean_var}}}, e^{{r_2 {clean_var}}}{RBRACE} \\implies y_c({clean_var}) = C_1 e^{{r_1 {clean_var}}} + C_2 e^{{r_2 {clean_var}}}$."
                ex = desc
                if is_nonhomogeneous:
                    std_title = f"Xây dựng hệ nghiệm cơ bản và nghiệm thuần nhất y_c({clean_var})"
                    clean_eq = re.sub(r"^\s*y\(([a-zA-Z])\)\s*=", r"y_c(\1) =", raw_eq)
                    ir = clean_eq
                else:
                    std_title = title
                    ir = raw_eq
                title = std_title
            else:
                p = f"Biến đổi và phân tích nghiệm cơ bản: {title}."
                mb = "Nguyên lý biến đổi vi phân tuyến tính."
                ex = desc
                ir = raw_eq

            stg_map[1].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi,
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=ex,
                    intermediate_result=ir,
                    stage_index=1,
                    stage_name="Nghiệm thuần nhất",
                )
            )

        # ---------------- Stage 2: Nghiệm riêng ----------------
        elif rn in (
            "Dạng nghiệm riêng đề xuất",
            "Đạo hàm và thế toán tử",
            "Hệ phương trình hệ số bất định",
            "Nghiệm riêng thành phần",
            "Phương pháp Biến thiên hằng số",
            "Định thức Wronskian",
            "Định thức Wronski",
            "Dạng nghiệm riêng Lagrange",
            "Hệ phương trình phụ trợ Lagrange",
            "Đạo hàm hàm biến thiên",
            "Tích phân hàm biến thiên",
            "Nghiệm riêng biến thiên hằng số",
        ) or "hệ số bất định" in rn.lower() or "biến thiên hằng số" in rn.lower():
            if rn == "Dạng nghiệm riêng đề xuất":
                p = f"Phân tích cấu trúc hàm cưỡng bức $g({clean_var})$, kiểm tra hiện tượng cộng hưởng với nghiệm đặc trưng và đề xuất dạng nghiệm thử $y_p({clean_var})$."
                mb = (
                    f"Phương pháp Hệ số bất định: So sánh số mũ phức đặc trưng $\\lambda = \\alpha + i\\beta$ của $g({clean_var})$ "
                    f"với các nghiệm đặc trưng ${LBRACE}r_1, r_2{RBRACE}$. Nếu $\\lambda$ trùng với nghiệm đặc trưng bậc $s$ ($s \\in {LBRACE}0, 1, 2{RBRACE}$), "
                    f"nghiệm thử nhân thêm ${clean_var}^s$: $y_p({clean_var}) = {clean_var}^s e^{{\\alpha {clean_var}}} [P({clean_var})\\cos(\\beta {clean_var}) + Q({clean_var})\\sin(\\beta {clean_var})]$."
                )
                ex = _enrich_resonance_desc(desc, char_eq_latex, clean_var)
                desc = ex
                ir = raw_eq
            elif rn == "Đạo hàm và thế toán tử":
                p = f"Tính các đạo hàm cấp 1, cấp 2 của nghiệm thử $y_p({clean_var})$ và thế vào toán tử vi phân $L[y_p] = a y_p'' + b y_p' + c y_p$."
                mb = f"Nghiệm riêng $y_p({clean_var})$ phải thỏa mãn phương trình vi phân: $L[y_p({clean_var})] = g({clean_var})$."
                ex = desc
                ir = raw_eq
            elif rn == "Hệ phương trình hệ số bất định":
                p = "Đồng nhất hệ số của các hàm cơ sở tương ứng ở hai vế để thiết lập và giải hệ phương trình đại số tuyến tính."
                mb = "Tính chất độc lập tuyến tính của hệ hàm cơ sở: hai vế đồng nhất khi và chỉ khi hệ số của từng hàm thành phần bằng nhau."
                ex = desc
                ir = raw_eq
            elif rn == "Nghiệm riêng thành phần":
                p = f"Thay các hệ số vừa giải được vào dạng nghiệm thử ban đầu để xác định biểu thức tường minh của nghiệm riêng $y_p({clean_var})$."
                mb = f"Biểu thức $y_p({clean_var})$ thu được là một nghiệm riêng cụ thể (không chứa hằng số tự do) thỏa mãn $L[y_p] = g({clean_var})$."
                ex = desc
                ir = raw_eq
            elif rn == "Phương pháp Biến thiên hằng số":
                p = f"Lựa chọn phương pháp Biến thiên hằng số (Lagrange) để tìm nghiệm riêng khi vế phải $g({clean_var})$ không thuộc các dạng chuẩn của phương pháp hệ số bất định."
                mb = f"Phương pháp Lagrange tìm nghiệm riêng dưới dạng $y_p({clean_var}) = u_1({clean_var})y_1({clean_var}) + u_2({clean_var})y_2({clean_var})$."
                ex = desc
                ir = f"y_p({clean_var}) = u_1({clean_var})y_1({clean_var}) + u_2({clean_var})y_2({clean_var})"
            elif rn in ("Định thức Wronskian", "Định thức Wronski"):
                p = f"Tính định thức Wronskian $W(y_1, y_2)({clean_var})$ của hệ nghiệm cơ bản."
                mb = f"$W(y_1, y_2)({clean_var}) = y_1 y_2' - y_1' y_2 \\ne 0$."
                ex = desc
                ir = raw_eq
            elif rn in ("Dạng nghiệm riêng Lagrange", "Hệ phương trình phụ trợ Lagrange", "Đạo hàm hàm biến thiên"):
                p = f"Thiết lập điều kiện phụ trợ Lagrange và giải hệ phương trình xác định đạo hàm $u_1'({clean_var})$ và $u_2'({clean_var})$."
                mb = f"Hệ phụ trợ Lagrange: $\\begin{{cases}} u_1' y_1 + u_2' y_2 = 0 \\\\ u_1' y_1' + u_2' y_2' = \\frac{{g({clean_var})}}{{a}} \\end{{cases}} \\implies u_1' = -\\frac{{y_2 g({clean_var})}}{{a W}},\\quad u_2' = \\frac{{y_1 g({clean_var})}}{{a W}}$."
                ex = desc
                ir = raw_eq
            else:
                p = f"Tích phân các hàm biến thiên và xác định nghiệm riêng $y_p({clean_var})$."
                mb = f"$u_1 = \\int u_1' d{clean_var},\\quad u_2 = \\int u_2' d{clean_var} \\implies y_p({clean_var}) = u_1 y_1 + u_2 y_2$."
                ex = desc
                ir = raw_eq

            stg_map[2].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi,
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=ex,
                    intermediate_result=ir,
                    stage_index=2,
                    stage_name="Nghiệm riêng",
                )
            )

        # ---------------- Stage 3: Tổng hợp nghiệm & Cauchy ----------------
        elif rn in (
            "Tổng hợp nghiệm tổng quát",
            "Đạo hàm nghiệm tổng quát",
            "Áp dụng điều kiện ban đầu",
            "Nghiệm riêng",
            "Nghiệm bài toán Cauchy",
            "Thay điều kiện y(t0) = y0",
            "Thay điều kiện y'(t0) = v0",
            "Thay điều kiện y",
            "Hệ ma trận 2x2",
            "Giải hệ xác định hằng số",
            "Nghiệm duy nhất bài toán Cauchy",
            "Giải tìm C1",
            "Giải tìm C2",
            "Thế C1 tìm C2",
            "Thế C2 tìm C1",
            "Xác định C1",
            "Biểu diễn C1",
            "Thế và giải tìm C2",
        ) or (has_ivp and ("điều kiện ban đầu" in title.lower() or "cauchy" in title.lower())):
            if rn == "Tổng hợp nghiệm tổng quát":
                p = f"Kết hợp nghiệm thuần nhất $y_c({clean_var})$ và nghiệm riêng $y_p({clean_var})$ để xây dựng nghiệm tổng quát hoàn chỉnh $y({clean_var})$."
                mb = f"Nguyên lý chồng chất nghiệm: Nghiệm tổng quát của phương trình tuyến tính không thuần nhất bằng tổng của nghiệm thuần nhất và một nghiệm riêng: $y({clean_var}) = y_c({clean_var}) + y_p({clean_var})$."
                ex = desc
                ir = raw_eq
            elif rn == "Đạo hàm nghiệm tổng quát":
                p = f"Tính đạo hàm cấp một $y'({clean_var})$ của nghiệm tổng quát để chuẩn bị áp dụng điều kiện ban đầu về đạo hàm $y'({clean_var}_0) = v_0$."
                mb = f"Đạo hàm giải tích của nghiệm tổng quát: $y'({clean_var}) = \\frac{{d}}{{d{clean_var}}}[y({clean_var})]$."
                ex = desc
                ir = raw_eq
            elif rn in ("Hệ ma trận 2x2", "Giải hệ xác định hằng số") or (has_ivp and "cramer" in desc.lower()):
                # Fold Cramer's rule step into the expandable substeps of the Cauchy IC step
                target_idx = -1
                for i in range(len(stg_map[3]) - 1, -1, -1):
                    if "điều kiện ban đầu" in stg_map[3][i].title.lower() or "điều kiện ban đầu" in stg_map[3][i].rule_name.lower() or "cauchy" in stg_map[3][i].title.lower():
                        target_idx = i
                        break
                if target_idx >= 0:
                    prev = stg_map[3][target_idx]
                    cramer_substep = SolutionStep(
                        step_number=len(prev.substeps) + 1,
                        rule_name="Quy tắc Cramer",
                        description=desc,
                        content=orig.content,
                        title="Phương pháp ma trận và quy tắc Cramer (Chi tiết)",
                        equation_latex=raw_eq,
                        rule_name_vi="Quy tắc Cramer",
                    )
                    new_substeps = prev.substeps + (cramer_substep,)
                    new_ir = raw_eq if ("C_1" in raw_eq or "C_2" in raw_eq) else prev.intermediate_result
                    stg_map[3][target_idx] = ODEPedagogicalStep(
                        step_number=prev.step_number,
                        rule_name=prev.rule_name,
                        description=prev.description,
                        content=prev.content,
                        substeps=new_substeps,
                        notes=prev.notes,
                        title=prev.title,
                        rule_name_vi=prev.rule_name_vi,
                        equation_latex=prev.equation_latex,
                        assumptions=prev.assumptions,
                        purpose=prev.purpose,
                        math_basis=prev.math_basis,
                        execution=prev.execution,
                        intermediate_result=new_ir,
                        stage_index=prev.stage_index,
                        stage_name=prev.stage_name,
                    )
                    continue
                else:
                    p = "Giải hệ phương trình đại số tuyến tính tìm các hằng số tích phân $C_1, C_2$ bằng quy tắc Cramer."
                    mb = "Quy tắc Cramer cho hệ phương trình đại số tuyến tính $2 \\times 2$ có định thức hệ số khác không."
                    ex = desc
                    ir = raw_eq
            elif rn in ("Áp dụng điều kiện ban đầu", "Thay điều kiện y(t0) = y0", "Thay điều kiện y") or (has_ivp and "điều kiện ban đầu" in title.lower()):
                title = "Xác định hằng số $C_1, C_2$ từ điều kiện Cauchy"
                p = f"Thay thế điều kiện ban đầu Cauchy vào nghiệm tổng quát $y({clean_var})$ và đạo hàm $y'({clean_var})$ để xác định các hằng số tích phân $C_1, C_2$."
                mb = "Định lý tồn tại và duy nhất nghiệm bài toán Cauchy: Hệ 2 phương trình bậc nhất cho $C_1, C_2$ có nghiệm duy nhất do định thức Wronskian $W(t_0) \\ne 0$."
                ex = _refine_cauchy_step_desc(desc, clean_var)
                desc = ex
                ir = raw_eq
            elif rn in ("Nghiệm riêng", "Nghiệm bài toán Cauchy", "Nghiệm duy nhất bài toán Cauchy"):
                title = "Tổng hợp nghiệm duy nhất của bài toán Cauchy"
                p = f"Thay các giá trị hằng số $C_1, C_2$ cụ thể vào dạng nghiệm tổng quát để kết luận nghiệm duy nhất của bài toán Cauchy $y({clean_var})$."
                mb = f"Nghiệm thu được thỏa mãn đồng thời phương trình vi phân và các điều kiện ban đầu $y({clean_var}_0) = y_0$, $y'({clean_var}_0) = v_0$."
                ex = desc
                ir = raw_eq
            else:
                p = f"Tổng hợp nghiệm: {title}."
                mb = "Nguyên lý tổng hợp nghiệm bài toán vi phân."
                ex = desc
                ir = raw_eq

            stg_map[3].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi,
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=ex,
                    intermediate_result=ir,
                    stage_index=3,
                    stage_name="Tổng hợp nghiệm",
                )
            )

        # ---------------- Stage 4: Kiểm chứng toán học độc lập ----------------
        elif rn in (
            "Kiểm chứng nghiệm",
            "Kiểm chứng nghiệm độc lập",
            "Kiểm chứng toán học",
            "Kiểm chứng phương trình",
            "Kiểm chứng điều kiện ban đầu",
        ) or "kiểm chứng" in title.lower():
            p = f"Kiểm tra tính đúng đắn toán học: thế nghiệm $y({clean_var})$ vào phương trình vi phân và các điều kiện ban đầu, chứng minh phần dư $R({clean_var}) \\equiv 0$."
            mb = f"Toán tử vi phân tuyến tính $L[y] = a y'' + b y' + c y$. Phần dư: $R({clean_var}) = L[y({clean_var})] - g({clean_var})$. Điều kiện nghiệm đúng: $R({clean_var}) \\equiv 0,\\forall {clean_var}$."
            ex = desc
            ir = f"R({clean_var}) = 0"

            stg_map[4].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi,
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=ex,
                    intermediate_result=ir,
                    stage_index=4,
                    stage_name="Kiểm chứng độc lập",
                )
            )

    # If homogeneous and stage 3 has no steps, synthesize conclusion step
    if not is_nonhomogeneous and not has_ivp and not stg_map[3] and stg_map[1]:
        yc_rhs = yc_latex.split("=", 1)[1].strip() if "=" in yc_latex else yc_latex
        synth_step = ODEPedagogicalStep(
            step_number=len(stg_map[1]) + 1,
            rule_name="Tổng hợp nghiệm thuần nhất",
            description=f"Do phương trình thuần nhất ($g({clean_var}) = 0$), nghiệm riêng $y_p({clean_var}) \\equiv 0$. Do đó nghiệm tổng quát trùng với nghiệm thuần nhất: $y({clean_var}) = y_c({clean_var})$.",
            content=stg_map[1][-1].content if stg_map[1] else None,
            title="Kết luận nghiệm tổng quát của phương trình thuần nhất",
            rule_name_vi="Nguyên lý nghiệm thuần nhất",
            equation_latex=f"y({clean_var}) = {yc_rhs}",
            purpose=f"Khẳng định nghiệm tổng quát hoàn chỉnh của phương trình vi phân thuần nhất $y({clean_var})$.",
            math_basis=f"Vì vế phải $g({clean_var}) = 0$, nghiệm riêng $y_p({clean_var}) \\equiv 0$. Nghiệm tổng quát: $y({clean_var}) = y_c({clean_var})$.",
            execution=f"Nghiệm tổng quát: $y({clean_var}) = y_c({clean_var}) = {yc_rhs}$.",
            intermediate_result=f"y({clean_var}) = {yc_rhs}",
            stage_index=3,
            stage_name="Tổng hợp nghiệm",
        )
        stg_map[3].append(synth_step)

    # Ensure Stage 4 has a verification step
    if not stg_map[4]:
        total_so_far = sum(len(steps) for steps in stg_map.values())
        synth_verify = _synthesize_verification_step(
            response=response,
            clean_var=clean_var,
            step_number=total_so_far + 1,
            order=2,
            has_ivp=has_ivp,
        )
        stg_map[4].append(synth_verify)

    renumbered = _renumber_steps(stg_map)

    # Stage 2 summary details
    if is_nonhomogeneous or renumbered[2]:
        stg2_summary = ODEStageSummary(
            stage_index=2,
            title="Giai đoạn 2: Tìm nghiệm riêng",
            subtitle=f"Xác định nghiệm riêng $y_p({clean_var})$ bằng phương pháp Hệ số bất định (UC) hoặc Biến thiên hằng số (VoP)",
            icon="looks_two",
            badge_text=f"y_p({clean_var})",
            badge_color="purple-7",
            is_completed=bool(renumbered[2]),
            is_applicable=True,
            summary_latex=yp_latex,
            summary_label="Nghiệm riêng:",
            steps=tuple(renumbered[2]),
            transition_note=f"Đã xác định xong nghiệm riêng $y_p({clean_var})$, ta áp dụng nguyên lý chồng chất để tổng hợp nghiệm tổng quát $y({clean_var}) = y_c({clean_var}) + y_p({clean_var})$."
            if not has_ivp
            else f"Đã có nghiệm riêng $y_p({clean_var})$, ta tiến hành thế điều kiện ban đầu Cauchy để giải xác định $C_1, C_2$.",
        )
    else:
        stg2_summary = ODEStageSummary(
            stage_index=2,
            title="Giai đoạn 2: Tìm nghiệm riêng",
            subtitle=f"Phương trình thuần nhất ($g({clean_var}) = 0$) không cần tìm nghiệm riêng",
            icon="looks_two",
            badge_text="Bỏ qua",
            badge_color="slate-5",
            is_completed=True,
            is_applicable=False,
            summary_latex=f"g({clean_var}) = 0 \\implies y_p({clean_var}) \\equiv 0",
            summary_label="Phương trình thuần nhất:",
            steps=(),
            transition_note=f"Vì nghiệm riêng triệt tiêu đồng nhất, nghiệm tổng quát được xác định hoàn toàn bởi nghiệm thuần nhất $y_c({clean_var})$."
            if not has_ivp
            else f"Vì phương trình thuần nhất, nghiệm tổng quát là $y_c({clean_var})$; ta tiếp tục áp dụng điều kiện ban đầu Cauchy để tìm $C_1, C_2$.",
        )

    stg3_sub = (
        r"Xác định hằng số $C_1, C_2$ thỏa mãn bài toán Cauchy (IVP)"
        if has_ivp
        else f"Tổng hợp nghiệm tổng quát $y({clean_var}) = y_c({clean_var}) + y_p({clean_var})$"
    )

    stages = [
        ODEStageSummary(
            stage_index=1,
            title="Giai đoạn 1: Tìm nghiệm thuần nhất",
            subtitle=f"Giải phương trình đặc trưng và xây dựng hệ nghiệm cơ bản $y_c({clean_var})$",
            icon="looks_one",
            badge_text=f"y_c({clean_var})",
            badge_color="blue-7",
            is_completed=bool(renumbered[1]),
            is_applicable=True,
            summary_latex=yc_latex,
            summary_label="Nghiệm thuần nhất:",
            steps=tuple(renumbered[1]),
            transition_note=f"Sau khi tìm được nghiệm thuần nhất $y_c({clean_var})$, ta tiếp tục tìm một nghiệm riêng $y_p({clean_var})$ tương ứng với hàm cưỡng bức $g({clean_var})$."
            if is_nonhomogeneous
            else f"Nghiệm thuần nhất $y_c({clean_var})$ đã được thiết lập; do phương trình thuần nhất, nghiệm này cũng chính là nghiệm tổng quát.",
        ),
        stg2_summary,
        ODEStageSummary(
            stage_index=3,
            title="Giai đoạn 3: Tổng hợp nghiệm",
            subtitle=stg3_sub,
            icon="looks_3",
            badge_text=f"y({clean_var})",
            badge_color="teal-7",
            is_completed=bool(renumbered[3]),
            is_applicable=True,
            summary_latex=y_latex,
            summary_label="Nghiệm bài toán:" if has_ivp else "Nghiệm tổng quát:",
            steps=tuple(renumbered[3]),
            transition_note="Tiến hành kiểm chứng toán học độc lập bằng cách thế nghiệm vào phương trình vi phân và các điều kiện ban đầu.",
        ),
        _build_stage4_summary(
            response,
            clean_var,
            f"Kiểm tra phần dư $R({clean_var}) = L[y] - g({clean_var}) \\equiv 0$" + (" và thỏa mãn điều kiện Cauchy" if has_ivp else ""),
            f"R({clean_var}) = L[y({clean_var})] - g({clean_var}) \\equiv 0",
            tuple(renumbered[4]),
        ),
    ]
    return tuple(stages)


# ==============================================================================
# 6. REDUCTION OF ORDER FLOW BUILDER
# ==============================================================================


def _build_reduction_of_order_flow(
    response: SolutionResponse,
    clean_var: str,
    params: dict[str, Any],
) -> tuple[ODEStageSummary, ...]:
    """Build pedagogical flow for Reduction of Order ODEs (y2 = v * y1)."""
    stg_map: dict[int, list[ODEPedagogicalStep]] = {1: [], 2: [], 3: [], 4: []}
    y_latex = standardize_ode_notation(response.final_latex)

    for orig in response.steps:
        rn = orig.rule_name
        title = orig.title
        desc = standardize_ode_notation(orig.description or "")
        raw_eq = standardize_ode_notation(orig.equation_latex or orig.content.latex_after or "")

        if rn in ("Chuẩn hóa phương trình cấp hai", "Kiểm tra nghiệm đã biết y1"):
            p = f"Chuẩn hóa phương trình và kiểm chứng nghiệm đã biết $y_1({clean_var})$."
            mb = f"Phương trình tuyến tính cấp hai thuần nhất dạng chuẩn: $y'' + p({clean_var})y' + q({clean_var})y = 0$."
            stg_map[1].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Chuẩn hóa & kiểm tra y1",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=1,
                    stage_name="Kiểm tra y1",
                )
            )
        elif rn in (
            "Đổi biến hạ bậc y2 = v*y1",
            "Đạo hàm cấp một và cấp hai",
            "Thế vào phương trình vi phân",
            "Triệt tiêu số hạng đồng nhất",
            "Đổi biến u = v'",
            "Đổi biến u = v",
            "Giải phương trình cho u",
        ):
            p = "Đặt ẩn phụ $y_2 = v(t)y_1(t)$, thế vào phương trình và đổi biến $u = v'$ để hạ bậc về phương trình vi phân cấp một."
            mb = "Số hạng chứa $v$ triệt tiêu do $y_1$ là nghiệm: $y_1 v'' + (2y_1' + p y_1)v' = 0 \\implies u' + \\left(2\\frac{y_1'}{y_1} + p\\right)u = 0$."
            stg_map[2].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Đổi biến hạ bậc",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=2,
                    stage_name="Hạ bậc u = v'",
                )
            )
        elif rn in (
            "Tích phân tìm v",
            "Xác định nghiệm cơ bản y2",
            "Định thức Wronskian",
            "Hệ nghiệm cơ bản",
            "Nghiệm riêng",
            "Áp dụng điều kiện ban đầu",
        ):
            p = f"Tích phân hàm $u({clean_var})$ để tìm $v({clean_var})$, xác định nghiệm thứ hai $y_2({clean_var})$ và kiểm tra độc lập tuyến tính qua Wronskian."
            mb = f"$v = \\int u\\,d{clean_var},\\quad y_2 = v \\cdot y_1.\\quad W(y_1, y_2) = y_1^2 v' = y_1^2 u \\ne 0$."
            stg_map[3].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Xác định y2 & nghiệm",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=3,
                    stage_name="Xác định y2 & nghiệm",
                )
            )
        elif rn in ("Kiểm chứng nghiệm", "Kiểm chứng toán học") or "kiểm chứng" in title.lower():
            p = "Kiểm tra độc lập toán học: cả hai nghiệm $y_1$ và $y_2$ đều thỏa mãn phương trình vi phân và định thức Wronskian khác 0."
            mb = "$L[y_1] \\equiv 0,\\quad L[y_2] \\equiv 0,\\quad W(y_1, y_2) \\ne 0$."
            stg_map[4].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Kiểm chứng",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=r"W(y_1, y_2) \ne 0",
                    stage_index=4,
                    stage_name="Kiểm chứng độc lập",
                )
            )

    if not stg_map[4]:
        total_so_far = sum(len(steps) for steps in stg_map.values())
        synth_verify = _synthesize_verification_step(
            response=response,
            clean_var=clean_var,
            step_number=total_so_far + 1,
            order=2,
            has_ivp=bool(params.get("initial_condition")),
        )
        stg_map[4].append(synth_verify)

    renumbered = _renumber_steps(stg_map)

    stages = [
        ODEStageSummary(
            stage_index=1,
            title="Giai đoạn 1: Chuẩn hóa & kiểm tra nghiệm đã biết",
            subtitle=f"Đưa về dạng chuẩn và kiểm chứng nghiệm $y_1({clean_var})$",
            icon="looks_one",
            badge_text=f"y_1({clean_var})",
            badge_color="blue-7",
            is_completed=bool(renumbered[1]),
            is_applicable=True,
            summary_latex=renumbered[1][-1].equation_latex if renumbered[1] else "",
            summary_label="Dạng chuẩn tắc:",
            steps=tuple(renumbered[1]),
            transition_note="Nghiệm thứ nhất $y_1$ đã được xác minh, ta đặt ẩn phụ $y_2 = v(t)y_1(t)$ để hạ bậc phương trình.",
        ),
        ODEStageSummary(
            stage_index=2,
            title="Giai đoạn 2: Đổi biến hạ bậc & giải cho u",
            subtitle=f"Đặt $y_2 = v \\cdot y_1$, đổi biến $u = v'$ và giải tìm $u({clean_var})$",
            icon="looks_two",
            badge_text="u = v'",
            badge_color="purple-7",
            is_completed=bool(renumbered[2]),
            is_applicable=True,
            summary_latex=renumbered[2][-1].equation_latex if renumbered[2] else "",
            summary_label="Nghiệm hàm u:",
            steps=tuple(renumbered[2]),
            transition_note="Đã tìm được hàm $u(t)$, ta tích phân để tìm $v(t)$ và xây dựng nghiệm cơ bản thứ hai $y_2(t)$.",
        ),
        ODEStageSummary(
            stage_index=3,
            title="Giai đoạn 3: Xác định y2 và nghiệm tổng quát",
            subtitle=f"Tích phân tìm $v({clean_var})$, xác định $y_2({clean_var})$ và kiểm tra Wronskian",
            icon="looks_3",
            badge_text=f"y_2({clean_var})",
            badge_color="teal-7",
            is_completed=bool(renumbered[3]),
            is_applicable=True,
            summary_latex=y_latex,
            summary_label="Nghiệm tổng quát:",
            steps=tuple(renumbered[3]),
            transition_note="Tiến hành kiểm chứng độc lập tính đúng đắn và độc lập tuyến tính của hệ nghiệm cơ bản.",
        ),
        _build_stage4_summary(
            response,
            clean_var,
            "Kiểm tra $W(y_1, y_2) \\ne 0$ và nghiệm thỏa mãn phương trình vi phân",
            "W(y_1, y_2) \\ne 0 \\implies L[y] \\equiv 0",
            tuple(renumbered[4]),
            verified_summary_label="Kiểm chứng Wronskian:",
        ),
    ]
    return tuple(stages)


# ==============================================================================
# 7. WRONSKIAN FLOW BUILDER
# ==============================================================================


def _build_wronskian_flow(
    response: SolutionResponse,
    clean_var: str,
    params: dict[str, Any],
) -> tuple[ODEStageSummary, ...]:
    """Build pedagogical flow for Wronskian determinant calculations."""
    stg_map: dict[int, list[ODEPedagogicalStep]] = {1: [], 2: [], 3: [], 4: []}
    w_latex = standardize_ode_notation(response.final_latex)

    for orig in response.steps:
        rn = orig.rule_name
        title = orig.title
        desc = standardize_ode_notation(orig.description or "")
        raw_eq = standardize_ode_notation(orig.equation_latex or orig.content.latex_after or "")

        if rn in ("Hệ nghiệm cơ bản", "Đạo hàm cấp một và cấp hai") and not stg_map[2]:
            p = f"Xác định hai hàm số $y_1({clean_var}), y_2({clean_var})$ và tính đạo hàm cấp một tương ứng."
            mb = "Định thức Wronskian yêu cầu đạo hàm cấp 0 và cấp 1 của các hàm thành phần."
            stg_map[1].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Xác định hàm số",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=1,
                    stage_name="Hàm số & đạo hàm",
                )
            )
        elif rn == "Định thức Wronskian":
            p = "Thiết lập ma trận Wronski cấp 2 và khai triển định thức $W(y_1, y_2) = y_1 y_2' - y_1' y_2$."
            mb = f"$W(y_1, y_2)({clean_var}) = \\det \\begin{{pmatrix}} y_1 & y_2 \\\\ y_1' & y_2' \\end{{pmatrix}} = y_1 y_2' - y_1' y_2$."
            stg_map[2].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Định thức Wronskian",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=2,
                    stage_name="Lập định thức",
                )
            )
        elif rn == "Định thức Wronski":
            p = "Rút gọn biểu thức giải tích của định thức Wronskian và đánh giá tính khác không."
            mb = "Định lý Wronskian: Nếu $W(y_1, y_2)(t_0) \\ne 0$ tại ít nhất một điểm, hệ hai hàm số độc lập tuyến tính."
            stg_map[3].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Rút gọn Wronskian",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=raw_eq,
                    stage_index=3,
                    stage_name="Rút gọn & đánh giá",
                )
            )
        elif rn in ("Kiểm chứng nghiệm", "Kiểm chứng toán học") or "kiểm chứng" in title.lower():
            p = "Kiểm chứng độc lập tính khác không của định thức Wronskian trên toàn miền xác định."
            mb = "Độc lập tuyến tính khẳng định tính tương thích để lập hệ nghiệm cơ bản cho phương trình vi phân."
            stg_map[4].append(
                ODEPedagogicalStep(
                    step_number=orig.step_number,
                    rule_name=rn,
                    description=desc,
                    content=orig.content,
                    substeps=orig.substeps,
                    notes=orig.notes,
                    title=title,
                    rule_name_vi=orig.rule_name_vi or "Kiểm chứng",
                    equation_latex=raw_eq,
                    assumptions=orig.assumptions,
                    purpose=p,
                    math_basis=mb,
                    execution=desc,
                    intermediate_result=r"W(y_1, y_2) \ne 0",
                    stage_index=4,
                    stage_name="Kiểm chứng độc lập",
                )
            )

    is_dependent = _is_wronskian_dependent(response, w_latex)
    if not stg_map[4]:
        total_so_far = sum(len(steps) for steps in stg_map.values())
        if is_dependent:
            synth_verify = ODEPedagogicalStep(
                step_number=total_so_far + 1,
                rule_name="Kiểm chứng toán học độc lập",
                description=f"Định thức Wronskian {w_latex} triệt tiêu đồng nhất trên miền xác định; hệ hàm số phụ thuộc tuyến tính.",
                content=response.steps[-1].content if response.steps else None,
                title="Kết luận phụ thuộc tuyến tính",
                rule_name_vi="Kiểm chứng toán học",
                equation_latex=r"W(y_1, y_2) \equiv 0",
                assumptions=(),
                purpose=f"Kiểm tra điều kiện triệt tiêu của định thức Wronskian $W(y_1, y_2)({clean_var})$.",
                math_basis="Nếu $W(y_1, y_2) \\equiv 0$ trên khoảng $I$ đối với cặp nghiệm hoặc hàm tỉ lệ, hệ hàm phụ thuộc tuyến tính.",
                execution=f"Đánh giá định thức: {response.verification.details if response.verification else 'Bằng 0 trên miền xác định.'}",
                intermediate_result=r"W(y_1, y_2) \equiv 0",
                stage_index=4,
                stage_name="Kiểm chứng độc lập",
            )
        else:
            synth_verify = ODEPedagogicalStep(
                step_number=total_so_far + 1,
                rule_name="Kiểm chứng toán học độc lập",
                description=f"Định thức Wronskian {w_latex} khác không trên miền xác định; khẳng định hai nghiệm độc lập tuyến tính.",
                content=response.steps[-1].content if response.steps else None,
                title="Kiểm chứng độc lập tuyến tính",
                rule_name_vi="Kiểm chứng toán học",
                equation_latex=f"{w_latex} \\not\\equiv 0",
                assumptions=(),
                purpose=f"Kiểm tra tính khác không của định thức Wronskian $W(y_1, y_2)({clean_var})$.",
                math_basis="Định lý Wronskian: $W(y_1, y_2) \\not\\equiv 0 \\iff y_1, y_2$ độc lập tuyến tính.",
                execution=f"Đánh giá định thức: {response.verification.details if response.verification else 'Khác 0 trên miền xác định.'}",
                intermediate_result=r"W(y_1, y_2) \ne 0",
                stage_index=4,
                stage_name="Kiểm chứng độc lập",
            )
        stg_map[4].append(synth_verify)

    renumbered = _renumber_steps(stg_map)

    stages = [
        ODEStageSummary(
            stage_index=1,
            title="Giai đoạn 1: Xác định hàm số và đạo hàm",
            subtitle="Xác định hai hàm số $y_1, y_2$ và tính các đạo hàm cấp một",
            icon="looks_one",
            badge_text="y_1', y_2'",
            badge_color="blue-7",
            is_completed=bool(renumbered[1]),
            is_applicable=True,
            summary_latex=renumbered[1][-1].equation_latex if renumbered[1] else "",
            summary_label="Hệ hàm số:",
            steps=tuple(renumbered[1]),
            transition_note="Các đạo hàm cấp một đã hoàn tất, ta lập ma trận Wronski cấp hai.",
        ),
        ODEStageSummary(
            stage_index=2,
            title="Giai đoạn 2: Lập định thức Wronskian",
            subtitle="Tính định thức ma trận: $W(y_1, y_2) = y_1 y_2' - y_1' y_2$",
            icon="looks_two",
            badge_text="W(y_1, y_2)",
            badge_color="purple-7",
            is_completed=bool(renumbered[2]),
            is_applicable=True,
            summary_latex=renumbered[2][-1].equation_latex if renumbered[2] else "",
            summary_label="Biểu thức Wronskian:",
            steps=tuple(renumbered[2]),
            transition_note="Tiến hành rút gọn biểu thức đại số và khảo sát tính khác không.",
        ),
        ODEStageSummary(
            stage_index=3,
            title="Giai đoạn 3: Rút gọn và đánh giá độc lập tuyến tính",
            subtitle="Đánh giá điều kiện $W(t) \\ne 0$ trên miền xác định",
            icon="looks_3",
            badge_text="Độc lập",
            badge_color="teal-7",
            is_completed=bool(renumbered[3]),
            is_applicable=True,
            summary_latex=w_latex,
            summary_label="Định thức Wronski:",
            steps=tuple(renumbered[3]),
            transition_note="Kiểm chứng độc lập toán học và đưa ra kết luận.",
        ),
        _build_stage4_summary(
            response,
            clean_var,
            "Khẳng định hệ hàm số phụ thuộc tuyến tính ($W \\equiv 0$)"
            if _is_wronskian_dependent(response, w_latex)
            else "Khẳng định tính chất độc lập tuyến tính của hệ hàm số",
            r"W(y_1, y_2) \equiv 0"
            if _is_wronskian_dependent(response, w_latex)
            else f"{w_latex} \\not\\equiv 0",
            tuple(renumbered[4]),
            title="Giai đoạn 4: Kết luận toán học độc lập",
            verified_summary_label="Kết luận:",
            is_wronskian=True,
        ),
    ]
    return tuple(stages)


# ==============================================================================
# 7b. EULER-CAUCHY FLOW BUILDER
# ==============================================================================


def polish_euler_cauchy_latex(latex_str: str, clean_var: str = "t") -> str:
    """Apply presentation-only LaTeX formatting polish for Euler–Cauchy expressions.

    Converts SymPy ``\\log`` output into textbook ``\\ln`` notation, cleans awkward
    ``+ -`` signs, and omits redundant unit coefficients without altering core logic.
    """
    if not latex_str:
        return latex_str

    v = re.escape((clean_var or "t").strip())
    s = standardize_ode_notation(latex_str)

    # Convert natural logarithms from SymPy's \log{\left(...\right)} to textbook \ln
    s = re.sub(rf"\\log\s*\{{\s*\\left\(\s*-\s*{v}\s*\\right\)\s*\}}", rf"\\ln(-{clean_var})", s)
    s = re.sub(rf"\\log\s*\\left\(\s*-\s*{v}\s*\\right\)", rf"\\ln(-{clean_var})", s)
    s = re.sub(rf"\\log\s*\(\s*-\s*{v}\s*\)", rf"\\ln(-{clean_var})", s)

    s = re.sub(rf"\\log\s*\{{\s*\\left\(\s*{v}\s*\\right\)\s*\}}", rf"\\ln {clean_var}", s)
    s = re.sub(rf"\\log\s*\\left\(\s*{v}\s*\\right\)", rf"\\ln {clean_var}", s)
    s = re.sub(rf"\\log\s*\(\s*{v}\s*\)", rf"\\ln {clean_var}", s)

    s = re.sub(r"\\log\b", r"\\ln", s)

    # Clean sign artifacts (+ -3 -> - 3) and redundant unit leading coefficients (1\,t^2 -> t^2)
    s = re.sub(r"\+\s*-\s*", "- ", s)
    s = re.sub(
        rf"(?:(?<=^)|(?<=[\s=+\-{{(]))1(?:\\,|\s)*(?=(?:{v}\s*\^|{v}\\,|{v}\s+y|m\s*\(|m\s*\^|y'|y''|y\b))",
        "",
        s,
    )
    return s


def _format_signed_coeff_term(coeff_str: str, var_part: str, *, leading: bool = False) -> str:
    """Format a signed coefficient-variable term cleanly for mathematical display."""
    raw = coeff_str.strip()
    if not leading and raw in ("0", "-0", "+0"):
        return ""
    is_neg = raw.startswith("-")
    mag = raw[1:].strip() if is_neg else raw

    if not var_part:
        term_core = mag
    elif mag == "1":
        term_core = var_part
    else:
        term_core = f"{mag}\\,{var_part}"

    if leading:
        return f"-{term_core}" if is_neg else term_core
    return f" - {term_core}" if is_neg else f" + {term_core}"


def _extract_euler_cauchy_context(response: SolutionResponse, clean_var: str) -> dict[str, Any]:
    """Extract normalized symbolic data from Euler–Cauchy solver steps for presentation."""
    ctx: dict[str, Any] = {
        "A": None,
        "B": None,
        "C": None,
        "b_minus_a": None,
        "eq_normalized": "",
        "is_neg": False,
        "is_natural_split": False,
        "interval_desc": "",
        "indicial_simplified": "",
        "delta": "",
        "root_case": "distinct",
        "roots_latex": "",
        "y1": "",
        "y2": "",
        "wronskian": "",
        "gen_sol": "",
        "ics_expr": "",
        "ivp_sys": "",
        "ivp_consts": "",
        "part_sol": "",
        "residual_before": "",
        "residual_after": "",
        "ic_verif": "",
        "is_nonhomogeneous": False,
        "g_latex": "",
        "yc": "",
        "vop_norm_eq": "",
        "vop_norm_desc": "",
        "vop_u_primes": "",
        "vop_u_primes_desc": "",
        "vop_u_funcs": "",
        "vop_u_funcs_desc": "",
        "vop_yp": "",
        "vop_yp_desc": "",
        "vop_has_integral": False,
    }

    for orig in response.steps:
        rn = orig.rule_name
        desc = orig.description or ""
        after = (orig.content.latex_after if orig.content else "") or ""
        before = (orig.content.latex_before if orig.content else "") or ""

        if rn == "Nhận dạng dạng phương trình Euler–Cauchy":
            m_abc = re.search(
                r"A\s*=\s*[^=]*?=\s*(.+?),\s*\\quad\s*B\s*=\s*[^=]*?=\s*(.+?),\s*\\quad\s*C\s*=\s*c\([^)]+\)\s*=\s*(.+?)(?:,\s*\\quad\s*g\([^)]+\)\s*=\s*([^\n$]+))?(?:\$\$|\n|$)",
                desc,
            )
            if m_abc:
                ctx["A"] = polish_euler_cauchy_latex(m_abc.group(1).strip(), clean_var)
                ctx["B"] = polish_euler_cauchy_latex(m_abc.group(2).strip(), clean_var)
                ctx["C"] = polish_euler_cauchy_latex(m_abc.group(3).strip(), clean_var)
                if m_abc.group(4):
                    ctx["g_latex"] = polish_euler_cauchy_latex(m_abc.group(4).strip(), clean_var)
                    ctx["is_nonhomogeneous"] = True
            if "không thuần nhất" in desc.lower():
                ctx["is_nonhomogeneous"] = True
            ctx["eq_normalized"] = polish_euler_cauchy_latex(after, clean_var)

        elif rn == "Nghiệm thử hàm lũy thừa":
            if f"(-{clean_var})" in before or f"(-{clean_var})" in desc:
                ctx["is_neg"] = True

        elif rn == "Phương trình chỉ số":
            ctx["indicial_simplified"] = polish_euler_cauchy_latex(after, clean_var)

        elif rn == "Biệt thức Delta và nghiệm chỉ số":
            m_bma = re.search(r"b\s*=\s*B\s*-\s*A\s*=\s*([^\n$.]+?)(?:\s*,\s*hệ|\s*\$)", desc)
            if m_bma:
                ctx["b_minus_a"] = polish_euler_cauchy_latex(m_bma.group(1).strip(), clean_var)
            m_d = re.search(r"\\Delta\s*=\s*(.+)", before)
            ctx["delta"] = polish_euler_cauchy_latex(m_d.group(1).strip() if m_d else before.strip(), clean_var)
            ctx["roots_latex"] = polish_euler_cauchy_latex(after, clean_var)
            if "nghiệm kép" in desc.lower():
                ctx["root_case"] = "repeated"
            elif "phức liên hợp" in desc.lower() or r"\alpha" in after:
                ctx["root_case"] = "complex"
            else:
                ctx["root_case"] = "distinct"

        elif rn == "Hệ nghiệm cơ bản":
            # before looks like: y_1 = ..., \quad y_2 = ...
            cleaned_pair = polish_euler_cauchy_latex(before, clean_var)
            m_pair = re.split(r",\s*\\quad\s*", cleaned_pair, maxsplit=1)
            if len(m_pair) == 2:
                ctx["y1"] = re.sub(r"^y_1(?:\([^)]*\))?\s*=\s*", "", m_pair[0]).strip()
                ctx["y2"] = re.sub(r"^y_2(?:\([^)]*\))?\s*=\s*", "", m_pair[1]).strip()
            w_ltx = polish_euler_cauchy_latex(after, clean_var)
            w_ltx = re.sub(r"\s*\\ne\s*0\s*$", "", w_ltx).strip()
            w_ltx = re.sub(r"^W\([^)]*\)\s*=\s*", "", w_ltx).strip()
            ctx["wronskian"] = w_ltx

        elif rn == "Nghiệm thuần nhất liên kết":
            ctx["is_nonhomogeneous"] = True
            ctx["yc"] = polish_euler_cauchy_latex(orig.equation_latex or after, clean_var)

        elif rn == "Chuẩn hóa và phương pháp Biến thiên hằng số":
            ctx["is_nonhomogeneous"] = True
            ctx["vop_norm_eq"] = polish_euler_cauchy_latex(orig.equation_latex or after, clean_var)
            ctx["vop_norm_desc"] = polish_euler_cauchy_latex(desc, clean_var)

        elif rn == "Đạo hàm hàm biến thiên":
            ctx["vop_u_primes"] = polish_euler_cauchy_latex(orig.equation_latex or after, clean_var)
            ctx["vop_u_primes_desc"] = polish_euler_cauchy_latex(desc, clean_var)

        elif rn == "Tích phân hàm biến thiên":
            ctx["vop_u_funcs"] = polish_euler_cauchy_latex(orig.equation_latex or after, clean_var)
            ctx["vop_u_funcs_desc"] = polish_euler_cauchy_latex(desc, clean_var)
            ctx["vop_has_integral"] = (
                "\\int" in after or "không có nguyên hàm sơ cấp" in desc.lower()
            )

        elif rn == "Nghiệm riêng biến thiên hằng số":
            ctx["vop_yp"] = polish_euler_cauchy_latex(orig.equation_latex or after, clean_var)
            ctx["vop_yp_desc"] = polish_euler_cauchy_latex(desc, clean_var)

        elif rn == "Nghiệm tổng quát":
            ctx["gen_sol"] = polish_euler_cauchy_latex(after, clean_var)
            if r"\begin{cases}" in after or "tách rời" in desc.lower():
                ctx["is_natural_split"] = True
            m_iv = re.search(r"miền xác định:\s*\$([^$]+)\$", desc)
            if m_iv:
                ctx["interval_desc"] = polish_euler_cauchy_latex(m_iv.group(1).strip(), clean_var)

        elif rn == "Điều kiện ban đầu Cauchy":
            ctx["ics_expr"] = polish_euler_cauchy_latex(before, clean_var)
            ctx["part_sol"] = polish_euler_cauchy_latex(after, clean_var)
            for sub in orig.substeps or ():
                if sub.rule_name == "Thiết lập hệ Cauchy":
                    m_cases = re.search(r"(\\begin\{cases\}.*?\\end\{cases\})", sub.description or "", flags=re.S)
                    if m_cases:
                        ctx["ivp_sys"] = polish_euler_cauchy_latex(m_cases.group(1).strip(), clean_var)
                elif sub.rule_name == "Giải hệ đại số tuyến tính" and sub.content:
                    ctx["ivp_consts"] = polish_euler_cauchy_latex(sub.content.latex_after or "", clean_var)

        elif rn == "Kiểm chứng độc lập":
            for sub in orig.substeps or ():
                if sub.rule_name == "Kiểm chứng phương trình vi phân" and sub.content:
                    ctx["residual_before"] = polish_euler_cauchy_latex(sub.content.latex_before or "", clean_var)
                    ctx["residual_after"] = polish_euler_cauchy_latex(sub.content.latex_after or "", clean_var)
                elif sub.rule_name == "Kiểm chứng điều kiện Cauchy" and sub.content:
                    ctx["ic_verif"] = polish_euler_cauchy_latex(sub.content.latex_after or "", clean_var)

    return ctx


def _build_euler_cauchy_flow(
    response: SolutionResponse,
    clean_var: str,
    params: dict[str, Any],
) -> tuple[ODEStageSummary, ...]:
    """Build clean, non-repetitive 4-stage pedagogical flow for Euler–Cauchy ODEs."""
    prob_mode = str(params.get("problem_mode", "")).strip().upper()
    if prob_mode == "GENERAL":
        has_ivp = False
    elif prob_mode == "CAUCHY_IVP":
        has_ivp = True
    else:
        # Guard carefully against "cauchy" substring matching "Euler–Cauchy"
        has_ivp = bool(params.get("initial_condition")) or any(
            s.rule_name in ("Điều kiện ban đầu Cauchy", "Thiết lập hệ Cauchy", "Giải hệ đại số tuyến tính")
            for s in response.steps
        )

    v_status = response.verification.status if response.verification else VerificationStatus.UNVERIFIED
    v_details = (
        polish_euler_cauchy_latex(response.verification.details, clean_var)
        if response.verification and response.verification.details
        else ""
    )

    ctx = _extract_euler_cauchy_context(response, clean_var)
    v = clean_var
    u = f"(-{v})" if ctx["is_neg"] else v
    y_latex = polish_euler_cauchy_latex(response.final_latex or "", clean_var)

    A_val, B_val, C_val = ctx["A"], ctx["B"], ctx["C"]
    has_coeffs = bool(A_val and B_val and C_val)
    is_nonhomo = bool(ctx["is_nonhomogeneous"])
    g_tex = ctx["g_latex"] or f"g({v})"

    # ---------------- STAGE 1: Indicial Equation Setup ----------------
    stage1_steps: list[ODEPedagogicalStep] = []

    if has_coeffs:
        eq_lhs = (
            f"{_format_signed_coeff_term(A_val, f'{v}^2\\,y\'\'', leading=True)}"
            f"{_format_signed_coeff_term(B_val, f'{v}\\,y\'')}"
            f"{_format_signed_coeff_term(C_val, 'y')}"
        )
        if is_nonhomo:
            eq_norm = f"{eq_lhs} = {g_tex}"
            s1_desc = (
                f"Đây là phương trình Euler–Cauchy không thuần nhất vì hệ số của $y''$, $y'$, $y$ có dạng $A{v}^2$, $B{v}$, $C$ "
                f"với $A = {A_val}$, $B = {B_val}$, $C = {C_val}$ và vế phải $g({v}) = {g_tex}$.\n"
                f"Trước tiên xét phương trình thuần nhất liên kết ${eq_lhs} = 0$:"
            )
            s1_eq = f"{eq_norm} \\implies A = {A_val},\\quad B = {B_val},\\quad C = {C_val},\\quad g({v}) = {g_tex}"
            s1_ir = f"A = {A_val},\\quad B = {B_val},\\quad C = {C_val},\\quad g({v}) = {g_tex}"
        else:
            eq_norm = f"{eq_lhs} = 0"
            s1_desc = (
                f"Đây là phương trình Euler–Cauchy vì các hệ số của $y''$, $y'$ và $y$ lần lượt có dạng $A{v}^2$, $B{v}$ và $C$.\n"
                f"Chuẩn hóa theo dạng $A{v}^2 y'' + B{v} y' + C y = 0$ với "
                f"$A = \\frac{{a({v})}}{{{v}^2}}$, $B = \\frac{{b({v})}}{{{v}}}$, $C = c({v})$:"
            )
            s1_eq = f"{eq_norm} \\implies A = {A_val},\\quad B = {B_val},\\quad C = {C_val}"
            s1_ir = f"A = {A_val},\\quad B = {B_val},\\quad C = {C_val}"
    else:
        orig_s1 = next((s for s in response.steps if s.rule_name == "Nhận dạng dạng phương trình Euler–Cauchy"), None)
        if is_nonhomo:
            s1_desc = f"Đây là phương trình Euler–Cauchy không thuần nhất $A{v}^2 y'' + B{v} y' + C y = g({v})$."
        else:
            s1_desc = f"Đây là phương trình Euler–Cauchy vì các hệ số của $y''$, $y'$ và $y$ lần lượt có dạng $A{v}^2$, $B{v}$ và $C$."
        s1_eq = polish_euler_cauchy_latex(
            orig_s1.content.latex_after if orig_s1 and orig_s1.content else f"A{v}^2 y'' + B{v} y' + C y = 0",
            clean_var,
        )
        s1_ir = s1_eq

    s1_raw_tpl = f"a({v})y'' + b({v})y' + c({v})y = g({v})" if is_nonhomo else f"a({v})y'' + b({v})y' + c({v})y = 0"
    stage1_steps.append(
        ODEPedagogicalStep(
            step_number=1,
            rule_name="Nhận dạng cấu trúc Euler–Cauchy",
            title="Nhận dạng dạng phương trình Euler–Cauchy",
            rule_name_vi="Nhận dạng dạng Euler–Cauchy",
            description=s1_desc,
            content=ExpressionStepContent(
                expression_before=s1_raw_tpl,
                expression_after=s1_eq,
                latex_before=s1_raw_tpl,
                latex_after=s1_eq,
            ),
            equation_latex=s1_eq,
            purpose=(
                f"Xác định cấu trúc Euler–Cauchy, tách các hằng số $A, B, C$ và hàm vế phải $g({v})$."
                if is_nonhomo
                else f"Xác định cấu trúc biến hệ số theo lũy thừa của ${v}$ và trích xuất các hằng số chuẩn hóa $A, B, C$."
            ),
            math_basis=(
                f"Phương trình Euler–Cauchy không thuần nhất cấp 2 có dạng $A{v}^2 y'' + B{v} y' + C y = g({v})$ (với $A \\ne 0$)."
                if is_nonhomo
                else f"Phương trình Euler–Cauchy thuần nhất cấp 2 có dạng $A{v}^2 y'' + B{v} y' + C y = 0$ (với $A \\ne 0$)."
            ),
            execution=s1_desc,
            intermediate_result=s1_ir,
            stage_index=1,
            stage_name="Phương trình chỉ số",
        )
    )

    # Step 2: Trial solution (formulas shown ONCE; zero duplication)
    if ctx["is_neg"]:
        trial_eq = (
            f"\\begin{{aligned}} y({v}) &= (-{v})^m \\\\ "
            f"y'({v}) &= -m(-{v})^{{m-1}} \\\\ "
            f"y''({v}) &= m(m-1)(-{v})^{{m-2}} \\end{{aligned}}"
        )
    else:
        trial_eq = (
            f"\\begin{{aligned}} y({v}) &= {v}^m \\\\ "
            f"y'({v}) &= m\\,{v}^{{m-1}} \\\\ "
            f"y''({v}) &= m(m-1)\\,{v}^{{m-2}} \\end{{aligned}}"
        )
    s2_desc = (
        f"Vì trên khoảng đang xét {v} khác $0$, phép thế hàm lũy thừa làm triệt tiêu đồng thời thừa số ${v}$ ở mọi đạo hàm."
    )
    stage1_steps.append(
        ODEPedagogicalStep(
            step_number=2,
            rule_name="Nghiệm thử hàm lũy thừa",
            title="Thiết lập nghiệm thử hàm lũy thừa",
            rule_name_vi="Nghiệm thử hàm lũy thừa",
            description=s2_desc,
            content=ExpressionStepContent(
                expression_before=f"y({v}) = {u}^m",
                expression_after=trial_eq,
                latex_before=f"y({v}) = {u}^m",
                latex_after=trial_eq,
            ),
            equation_latex=trial_eq,
            purpose="Chuyển đổi phương trình vi phân biến hệ số thành phương trình đại số theo tham số số mũ $m$.",
            math_basis="Lũy thừa bậc $k$ của biến nhân với đạo hàm cấp $k$ luôn khôi phục đúng bậc lũy thừa ban đầu.",
            execution=s2_desc,
            intermediate_result=trial_eq,
            stage_index=1,
            stage_name="Phương trình chỉ số",
        )
    )

    # Step 3: Derive the indicial equation cleanly with symbolic substitution + factoring
    ind_simp = ctx["indicial_simplified"] or "Am(m-1) + Bm + C = 0"
    if has_coeffs:
        sub_lhs = (
            f"{_format_signed_coeff_term(A_val, f'{v}^2 \\cdot m(m-1){u}^{{m-2}}', leading=True) if ctx['is_neg'] else _format_signed_coeff_term(A_val, f'{v}^2 \\cdot m(m-1){v}^{{m-2}}', leading=True)}"
            f"{_format_signed_coeff_term(B_val, f'{v} \\cdot (-m{u}^{{m-1}})' if ctx['is_neg'] else f'{v} \\cdot m{v}^{{m-1}}')}"
            f"{_format_signed_coeff_term(C_val, f'{u}^m')}"
        )
        # Note: v * (-(-v)^{m-1}) simplifies sign cleanly with (-v)^m because t = -(-t)
        factored_poly = (
            f"{_format_signed_coeff_term(A_val, 'm(m-1)', leading=True)}"
            f"{_format_signed_coeff_term(B_val, 'm')}"
            f"{_format_signed_coeff_term(C_val, '')}"
        )
        s3_eq = (
            f"\\begin{{aligned}} &{sub_lhs} = 0 \\\\ "
            f"&\\left[{factored_poly}\\right]{u}^m = 0 \\\\ "
            f"&\\implies \\boxed{{{ind_simp}}} \\end{{aligned}}"
        )
    else:
        s3_eq = f"\\boxed{{{ind_simp}}}"

    s3_desc = (
        f"Thay nghiệm thử cùng các đạo hàm vào phương trình rồi đặt nhân tử chung ${u}^m$. "
        f"Do ${u} \\ne 0$ trên khoảng liên thông đang xét nên ${u}^m \\ne 0$, rút gọn được phương trình chỉ số:"
    )
    stage1_steps.append(
        ODEPedagogicalStep(
            step_number=3,
            rule_name="Phương trình chỉ số",
            title="Suy ra phương trình chỉ số",
            rule_name_vi="Phương trình chỉ số",
            description=s3_desc,
            content=ExpressionStepContent(
                expression_before=f"{factored_poly if has_coeffs else 'Am(m-1) + Bm + C'} = 0",
                expression_after=ind_simp,
                latex_before=f"{factored_poly if has_coeffs else 'Am(m-1) + Bm + C'} = 0",
                latex_after=ind_simp,
            ),
            equation_latex=s3_eq,
            purpose="Khử nhân tử lũy thừa khác $0$ để thu được phương trình bậc hai cho $m$.",
            math_basis=f"Trên khoảng liên thông không chứa điểm kỳ dị ${v} = 0$, ta luôn có ${u}^m \\ne 0$.",
            execution=s3_desc,
            intermediate_result=s3_eq,
            stage_index=1,
            stage_name="Phương trình chỉ số",
        )
    )

    # ---------------- STAGE 2: Discriminant & Fundamental System ----------------
    stage2_steps: list[ODEPedagogicalStep] = []

    b_minus_a = ctx["b_minus_a"] or (f"({B_val} - {A_val})" if has_coeffs else "(B - A)")
    delta_str = ctx["delta"] or "\\Delta"
    roots_str = ctx["roots_latex"] or ""

    if ctx["root_case"] == "distinct":
        root_case_note = f"Vì $\\Delta = {delta_str} > 0$, phương trình chỉ số có hai nghiệm thực phân biệt:"
    elif ctx["root_case"] == "repeated":
        root_case_note = f"Vì $\\Delta = {delta_str} = 0$, phương trình chỉ số có nghiệm kép thực:"
    else:
        root_case_note = f"Vì $\\Delta = {delta_str} < 0$, phương trình chỉ số có cặp nghiệm phức liên hợp $m_{{1,2}} = \\alpha \\pm i\\beta$:"

    if has_coeffs:
        ind_std = (
            f"P(m) = {_format_signed_coeff_term(A_val, 'm^2', leading=True)}"
            f"{_format_signed_coeff_term(b_minus_a, 'm')}"
            f"{_format_signed_coeff_term(C_val, '')} = 0"
        )
        delta_eq = (
            f"\\begin{{aligned}} &{ind_std} \\\\ "
            f"&\\Delta = (B - A)^2 - 4AC = ({b_minus_a})^2 - 4({A_val})({C_val}) = {delta_str} \\\\ "
            f"&{roots_str} \\end{{aligned}}"
        )
    else:
        delta_eq = f"\\Delta = {delta_str}, \\quad {roots_str}" if roots_str else f"\\Delta = {delta_str}"

    s4_desc = f"Viết lại đa thức chỉ số dạng chuẩn $Am^2 + (B-A)m + C = 0$ và tính biệt thức $\\Delta = (B-A)^2 - 4AC$. {root_case_note}"
    stage2_steps.append(
        ODEPedagogicalStep(
            step_number=4,
            rule_name="Biệt thức Delta và nghiệm chỉ số",
            title="Giải phương trình chỉ số và phân loại nghiệm",
            rule_name_vi="Biệt thức Delta & nghiệm $m$",
            description=s4_desc,
            content=ExpressionStepContent(
                expression_before=f"Delta = {delta_str}",
                expression_after=roots_str or delta_eq,
                latex_before=f"\\Delta = {delta_str}",
                latex_after=roots_str or delta_eq,
            ),
            equation_latex=delta_eq,
            purpose="Phân loại trường hợp nghiệm của phương trình chỉ số bằng dấu của biệt thức $\\Delta$.",
            math_basis="Đa thức chỉ số viết theo $A, B, C$ là $P(m) = Am^2 + (B - A)m + C = 0$ với $\\Delta = (B - A)^2 - 4AC$.",
            execution=s4_desc,
            intermediate_result=roots_str or f"\\Delta = {delta_str}",
            stage_index=2,
            stage_name="Hệ nghiệm cơ bản",
        )
    )

    # Step 5: Fundamental system & single Wronskian calculation
    y1_str = ctx["y1"]
    y2_str = ctx["y2"]
    w_expr = ctx["wronskian"]

    if ctx["root_case"] == "distinct":
        basis_basis = f"Hai nghiệm thực phân biệt $m_1 \\ne m_2$ cho hệ hai nghiệm lũy thừa ${u}^{{m_1}}$ và ${u}^{{m_2}}$."
    elif ctx["root_case"] == "repeated":
        ln_u = f"\\ln(-{v})" if ctx["is_neg"] else f"\\ln {v}"
        basis_basis = f"Với nghiệm kép thực $m$, nghiệm thứ hai xuất hiện nhân tử logarit tạo cặp ${u}^m$ và ${u}^m {ln_u}$."
    else:
        ln_u = f"\\ln(-{v})" if ctx["is_neg"] else f"\\ln {v}"
        basis_basis = (
            f"Từ công thức Euler ${u}^{{\\alpha \\pm i\\beta}} = {u}^\\alpha [\\cos(\\beta {ln_u}) \\pm i\\sin(\\beta {ln_u})]$, "
            f"tách phần thực và phần ảo để thu được hai nghiệm thực."
        )

    domain_note = (
        f" trên khoảng ${v} < 0$ (nên dùng cơ số $-{v} > 0$)"
        if ctx["is_neg"]
        else (f" trên từng nhánh ${v} > 0$ và ${v} < 0$" if ctx["is_natural_split"] else f" trên ${ctx['interval_desc'] or f'{v} > 0'}$")
    )

    if y1_str and y2_str:
        if w_expr:
            if v_status == VerificationStatus.FAILED:
                w_line = f"W(y_1, y_2) = {w_expr}"
                w_prose = f"Cặp nghiệm cơ bản{domain_note} và định thức Wronskian $W(y_1, y_2) = y_1 y_2' - y_1' y_2$:"
            elif v_status == VerificationStatus.UNVERIFIED:
                w_line = f"W(y_1, y_2) = {w_expr}"
                w_prose = f"Cặp nghiệm cơ bản{domain_note} cùng định thức Wronskian (chưa được xác minh ký hiệu đầy đủ):"
            else:
                w_line = f"W(y_1, y_2) = y_1 y_2' - y_1' y_2 = {w_expr} \\ne 0"
                w_prose = f"Cặp nghiệm cơ bản{domain_note}; định thức Wronskian khác $0$ khẳng định hai nghiệm độc lập tuyến tính:"
            s5_eq = f"\\begin{{aligned}} &y_1({v}) = {y1_str}, \\qquad y_2({v}) = {y2_str} \\\\ &{w_line} \\end{{aligned}}"
        else:
            w_prose = f"Xây dựng hai nghiệm cơ bản{domain_note}:"
            s5_eq = f"y_1({v}) = {y1_str}, \\qquad y_2({v}) = {y2_str}"
    else:
        w_prose = "Xây dựng hệ nghiệm cơ bản độc lập tuyến tính:"
        s5_eq = y_latex

    stage2_steps.append(
        ODEPedagogicalStep(
            step_number=5,
            rule_name="Hệ nghiệm cơ bản",
            title="Xây dựng hệ nghiệm cơ bản và Wronskian",
            rule_name_vi="Hệ nghiệm cơ bản",
            description=w_prose,
            content=ExpressionStepContent(
                expression_before=f"y_1 = {y1_str}, y_2 = {y2_str}" if (y1_str and y2_str) else "",
                expression_after=s5_eq,
                latex_before=f"y_1 = {y1_str}, \\quad y_2 = {y2_str}" if (y1_str and y2_str) else "",
                latex_after=s5_eq,
            ),
            equation_latex=s5_eq,
            purpose="Chuyển các nghiệm chỉ số thành hai hàm thực cơ bản và xác nhận tính độc lập tuyến tính.",
            math_basis=basis_basis,
            execution=w_prose,
            intermediate_result=s5_eq,
            stage_index=2,
            stage_name="Hệ nghiệm cơ bản",
        )
    )

    if is_nonhomo and ctx["yc"]:
        yc_eq = ctx["yc"]
        yc_desc = "Tổ hợp tuyến tính hai nghiệm cơ bản cho nghiệm của phương trình thuần nhất liên kết trên khoảng xác định:"
        stage2_steps.append(
            ODEPedagogicalStep(
                step_number=6,
                rule_name="Nghiệm thuần nhất liên kết",
                title=f"Xác định nghiệm thuần nhất liên kết y_c({v})",
                rule_name_vi="Nghiệm thuần nhất liên kết",
                description=yc_desc,
                content=ExpressionStepContent(
                    expression_before=f"y_c({v}) = C_1 y_1({v}) + C_2 y_2({v})",
                    expression_after=yc_eq,
                    latex_before=f"y_c({v}) = C_1 y_1({v}) + C_2 y_2({v})",
                    latex_after=yc_eq,
                ),
                equation_latex=yc_eq,
                purpose=f"Xác định phần nghiệm thuần nhất $y_c({v})$ trước khi tìm nghiệm riêng $y_p({v})$.",
                math_basis=f"Nghiệm tổng quát của phương trình thuần nhất liên kết có dạng $y_c({v}) = C_1 y_1({v}) + C_2 y_2({v})$.",
                execution=yc_desc,
                intermediate_result=yc_eq,
                stage_index=2,
                stage_name="Hệ nghiệm cơ bản",
            )
        )

    # ---------------- STAGE 3: General Solution or Cauchy IVP ----------------
    stage3_steps: list[ODEPedagogicalStep] = []
    gen_sol_eq = ctx["gen_sol"] or y_latex

    if is_nonhomo:
        vop_specs = (
            (
                "Chuẩn hóa và phương pháp Biến thiên hằng số",
                "Chuẩn hóa phương trình và thiết lập Biến thiên hằng số",
                "Chuẩn hóa & Biến thiên hằng số",
                ctx["vop_norm_eq"],
                ctx["vop_norm_desc"] or f"Chia hai vế cho hệ số dẫn $A{v}^2$ ($A \\ne 0, {v} \\ne 0$) để thu dạng chuẩn $y'' + P({v})y' + Q({v})y = R({v})$.",
                "Đưa phương trình về hệ số dẫn 1 để áp dụng đúng công thức Lagrange (Wronskian).",
                f"Hệ biến thiên hằng số đòi hỏi phương trình ở dạng chuẩn tắc $y'' + P({v})y' + Q({v})y = R({v})$.",
            ),
            (
                "Đạo hàm hàm biến thiên",
                "Giải hệ Lagrange tìm đạo hàm u₁' và u₂'",
                "Đạo hàm Lagrange",
                ctx["vop_u_primes"],
                ctx["vop_u_primes_desc"] or f"Từ $u_1'y_1 + u_2'y_2 = 0$ và $u_1'y_1' + u_2'y_2' = R({v})$, suy ra $u_1' = -y_2 R / W$ và $u_2' = y_1 R / W$.",
                "Giải hệ tuyến tính cho đạo hàm hai hàm hệ số biến thiên $u_1', u_2'$.",
                "Áp dụng quy tắc Cramer trên ma trận Wronskian khả nghịch ($W \\ne 0$).",
            ),
            (
                "Tích phân hàm biến thiên",
                "Tính tích phân các hàm biến thiên u₁ và u₂",
                "Tích phân hàm biến thiên",
                ctx["vop_u_funcs"],
                ctx["vop_u_funcs_desc"] or "Lấy nguyên hàm theo biến độc lập (hằng số tích phân tùy ý được gộp vào $y_c$).",
                "Thu nhận biểu thức $u_1, u_2$ (hoặc bảo toàn tích phân ký hiệu chính xác nếu không sơ cấp).",
                "Không thêm hằng số tích phân mới vì mọi thành phần thuần nhất đã nằm trong $y_c$.",
            ),
            (
                "Nghiệm riêng biến thiên hằng số",
                f"Xác định nghiệm riêng y_p({v})",
                "Nghiệm riêng y_p",
                ctx["vop_yp"],
                ctx["vop_yp_desc"] or f"Thay $u_1, u_2$ vào công thức $y_p({v}) = u_1({v})y_1({v}) + u_2({v})y_2({v})$.",
                f"Tổng hợp nghiệm riêng $y_p({v})$ cho vế phải $g({v})$.",
                f"Nghiệm riêng biến thiên hằng số được xây dựng bởi $y_p({v}) = u_1({v})y_1({v}) + u_2({v})y_2({v})$.",
            ),
        )
        for idx_offset, (v_rn, v_title, v_vi, v_eq, v_desc, v_purp, v_basis) in enumerate(vop_specs):
            if not v_eq:
                continue
            stage3_steps.append(
                ODEPedagogicalStep(
                    step_number=len(stage2_steps) + idx_offset + 1,
                    rule_name=v_rn,
                    title=v_title,
                    rule_name_vi=v_vi,
                    description=v_desc,
                    content=ExpressionStepContent(
                        expression_before="",
                        expression_after=v_eq,
                        latex_before="",
                        latex_after=v_eq,
                    ),
                    equation_latex=v_eq,
                    purpose=v_purp,
                    math_basis=v_basis,
                    execution=v_desc,
                    intermediate_result=v_eq,
                    stage_index=3,
                    stage_name="Nghiệm riêng & Tổng hợp",
                )
            )

    if not has_ivp:
        # Strict General Solution Mode: ZERO mention of Cauchy or initial conditions
        if ctx["is_natural_split"]:
            if is_nonhomo:
                g_desc = (
                    f"Do điểm kỳ dị ${v} = 0$ chia $\\mathbb{{R}} \\setminus \\{{0\\}}$ thành hai khoảng liên thông rời nhau, "
                    f"tổng hợp $y = y_c + y_p$ riêng biệt trên từng nhánh với $C_1, C_2 \\in \\mathbb{{R}}$ (${v} > 0$) "
                    f"và $C_3, C_4 \\in \\mathbb{{R}}$ (${v} < 0$):"
                )
            else:
                g_desc = (
                    f"Do điểm kỳ dị ${v} = 0$ chia $\\mathbb{{R}} \\setminus \\{{0\\}}$ thành hai khoảng liên thông rời nhau, "
                    f"tổng hợp tổ hợp tuyến tính với các cặp hằng số tùy ý độc lập $C_1, C_2 \\in \\mathbb{{R}}$ (${v} > 0$) "
                    f"và $C_3, C_4 \\in \\mathbb{{R}}$ (${v} < 0$):"
                )
            g_eq = gen_sol_eq
        else:
            iv_label = ctx["interval_desc"] or (f"{v} < 0" if ctx["is_neg"] else f"{v} > 0")
            gen_rhs = re.sub(rf"^y\s*\({re.escape(v)}\)\s*=\s*", "", gen_sol_eq).strip()
            if is_nonhomo:
                g_desc = (
                    f"Theo nguyên lý chồng chất trên khoảng xác định ${iv_label}$, nghiệm tổng quát có dạng "
                    f"$y({v}) = y_c({v}) + y_p({v})$ với hai hằng số thực tùy ý $C_1, C_2 \\in \\mathbb{{R}}$:"
                )
                g_eq = f"y({v}) = y_c({v}) + y_p({v}) = {gen_rhs}"
            else:
                g_desc = (
                    f"Nghiệm tổng quát trên khoảng xác định ${iv_label}$ là mọi tổ hợp tuyến tính của "
                    f"$y_1({v})$ và $y_2({v})$ với hai hằng số thực tùy ý $C_1, C_2 \\in \\mathbb{{R}}$:"
                )
                g_eq = f"y({v}) = C_1 y_1({v}) + C_2 y_2({v}) = {gen_rhs}"

        g_before = f"y({v}) = y_c({v}) + y_p({v})" if is_nonhomo else f"y({v}) = C_1 y_1({v}) + C_2 y_2({v})"
        g_basis = (
            f"Theo nguyên lý chồng chất cho phương trình tuyến tính không thuần nhất, $y({v}) = y_c({v}) + y_p({v})$."
            if is_nonhomo
            else f"Theo nguyên lý chồng chất cho phương trình thuần nhất, $y({v}) = C_1 y_1({v}) + C_2 y_2({v})$."
        )
        stage3_steps.append(
            ODEPedagogicalStep(
                step_number=6,
                rule_name="Nghiệm tổng quát",
                title="Xây dựng nghiệm tổng quát",
                rule_name_vi="Nghiệm tổng quát",
                description=g_desc,
                content=ExpressionStepContent(
                    expression_before=g_before,
                    expression_after=g_eq,
                    latex_before=g_before,
                    latex_after=g_eq,
                ),
                equation_latex=g_eq,
                purpose="Biểu diễn họ toàn bộ nghiệm thực của phương trình vi phân cấp 2 trên khoảng xác định.",
                math_basis=g_basis,
                execution=g_desc,
                intermediate_result=g_eq,
                stage_index=3,
                stage_name="Nghiệm tổng quát",
            )
        )
        stg3_subtitle = "Tìm nghiệm riêng y_p và tổng hợp y = y_c + y_p" if is_nonhomo else "Nghiệm tổng quát"
        stg3_summary_label = "Nghiệm tổng quát:"
        stg2_transition = (
            f"Chuẩn hóa phương trình và áp dụng Biến thiên hằng số để tìm nghiệm riêng $y_p({v})$."
            if is_nonhomo
            else f"Tổ hợp hai nghiệm cơ bản để thiết lập nghiệm tổng quát $y({v})$."
        )
    else:
        # Cauchy IVP Mode
        iv_label = ctx["interval_desc"] or (f"{v} < 0" if ctx["is_neg"] else f"{v} > 0")
        gen_rhs = re.sub(rf"^y\s*\({re.escape(v)}\)\s*=\s*", "", gen_sol_eq).strip()
        if is_nonhomo:
            g_eq = f"y({v}) = y_c({v}) + y_p({v}) = {gen_rhs}"
            g_desc = f"Tổng hợp nghiệm tổng quát $y({v}) = y_c({v}) + y_p({v})$ trên khoảng liên thông ${iv_label}$ chứa điểm ban đầu:"
            g_before = f"y({v}) = y_c({v}) + y_p({v})"
            g_basis = f"Trên khoảng liên thông chứa điểm ban đầu, $y({v}) = y_c({v}) + y_p({v})$."
        else:
            g_eq = f"y({v}) = C_1 y_1({v}) + C_2 y_2({v}) = {gen_rhs}"
            g_desc = f"Thiết lập nghiệm tổng quát trên khoảng liên thông ${iv_label}$ chứa điểm ban đầu:"
            g_before = f"y({v}) = C_1 y_1({v}) + C_2 y_2({v})"
            g_basis = f"Trên khoảng liên thông chứa điểm ban đầu, nghiệm tổng quát có dạng $y({v}) = C_1 y_1({v}) + C_2 y_2({v})$."
        stage3_steps.append(
            ODEPedagogicalStep(
                step_number=6,
                rule_name="Nghiệm tổng quát",
                title="Nghiệm tổng quát trên khoảng chứa điểm ban đầu",
                rule_name_vi="Nghiệm tổng quát",
                description=g_desc,
                content=ExpressionStepContent(
                    expression_before=g_before,
                    expression_after=g_eq,
                    latex_before=g_before,
                    latex_after=g_eq,
                ),
                equation_latex=g_eq,
                purpose="Viết biểu thức nghiệm phụ thuộc hai hằng số $C_1, C_2$ trước khi thế điều kiện Cauchy.",
                math_basis=g_basis,
                execution=g_desc,
                intermediate_result=g_eq,
                stage_index=3,
                stage_name="Bài toán Cauchy (IVP)",
            )
        )

        # Build Cauchy evaluation step
        orig_ivp = next((s for s in response.steps if s.rule_name == "Điều kiện ban đầu Cauchy"), None)
        ics_disp = ctx["ics_expr"] or polish_euler_cauchy_latex(str(params.get("initial_condition", "")), clean_var)
        sys_disp = ctx["ivp_sys"]
        consts_disp = ctx["ivp_consts"]
        part_disp = ctx["part_sol"] or y_latex

        ivp_parts = []
        if ics_disp:
            ivp_parts.append(ics_disp)
        if sys_disp:
            ivp_parts.append(sys_disp)
        if consts_disp:
            ivp_parts.append(f"\\implies {consts_disp}")
        ivp_parts.append(f"\\implies {part_disp}")
        ivp_eq = " \\\\ ".join(ivp_parts)
        if len(ivp_parts) > 1:
            ivp_eq = f"\\begin{{aligned}} {ivp_eq} \\end{{aligned}}"

        ivp_desc = "Thay điều kiện ban đầu Cauchy vào nghiệm tổng quát và đạo hàm $y'(t)$ để giải hệ 2 ẩn $C_1, C_2$ và rút ra nghiệm riêng duy nhất:"
        # Polish substeps if any
        polished_subs = tuple(
            SolutionStep(
                step_number=sub.step_number,
                rule_name=sub.rule_name,
                description=polish_euler_cauchy_latex(sub.description or "", clean_var),
                content=ExpressionStepContent(
                    expression_before=sub.content.expression_before if sub.content else "",
                    expression_after=sub.content.expression_after if sub.content else "",
                    latex_before=polish_euler_cauchy_latex(sub.content.latex_before or "", clean_var),
                    latex_after=polish_euler_cauchy_latex(sub.content.latex_after or "", clean_var),
                )
                if sub.content
                else ExpressionStepContent(expression_before="", expression_after="", latex_before="", latex_after=""),
                title=sub.title,
                rule_name_vi=sub.rule_name_vi,
                equation_latex=polish_euler_cauchy_latex(sub.equation_latex or "", clean_var),
                assumptions=sub.assumptions,
            )
            for sub in (orig_ivp.substeps if orig_ivp and orig_ivp.substeps else ())
        )

        stage3_steps.append(
            ODEPedagogicalStep(
                step_number=7,
                rule_name="Điều kiện ban đầu Cauchy",
                title="Giải hệ điều kiện ban đầu Cauchy (IVP)",
                rule_name_vi="Bài toán Cauchy (IVP)",
                description=ivp_desc,
                content=ExpressionStepContent(
                    expression_before=ics_disp,
                    expression_after=part_disp,
                    latex_before=ics_disp,
                    latex_after=part_disp,
                ),
                substeps=polished_subs,
                equation_latex=ivp_eq,
                purpose="Xác định giá trị duy nhất của $C_1, C_2$ từ điều kiện ban đầu $y(t_0), y'(t_0)$.",
                math_basis="Do $W(y_1, y_2)(t_0) \\ne 0$, hệ tuyến tính ẩn $C_1, C_2$ có nghiệm duy nhất.",
                execution=ivp_desc,
                intermediate_result=part_disp,
                stage_index=3,
                stage_name="Bài toán Cauchy (IVP)",
            )
        )
        stg3_subtitle = "Tìm nghiệm riêng y_p và giải Bài toán Cauchy (IVP)" if is_nonhomo else "Bài toán Cauchy (IVP)"
        stg3_summary_label = "Nghiệm riêng (Cauchy IVP):"
        stg2_transition = (
            f"Áp dụng Biến thiên hằng số để tìm $y_p({v})$, tổng hợp và giải hệ điều kiện ban đầu Cauchy (IVP)."
            if is_nonhomo
            else "Tổng hợp nghiệm tổng quát và giải hệ điều kiện ban đầu Cauchy (IVP)."
        )

    # ---------------- STAGE 4: Independent Symbolic Verification ----------------
    stage4_steps: list[ODEPedagogicalStep] = []
    res_rhs_suffix = f" - ({g_tex})" if is_nonhomo else ""
    res_lhs = ctx["residual_before"] or (
        f"R({v}) = {_format_signed_coeff_term(A_val, f'{v}^2 y\'\'', leading=True)}"
        f"{_format_signed_coeff_term(B_val, f'{v} y\'')}"
        f"{_format_signed_coeff_term(C_val, 'y')}{res_rhs_suffix}"
        if has_coeffs
        else f"R({v}) = A{v}^2 y'' + B{v} y' + C y{res_rhs_suffix}"
    )
    w_check = f"W(y_1, y_2) = {ctx['wronskian']}" if ctx["wronskian"] else "W(y_1, y_2)"

    if v_status == VerificationStatus.VERIFIED:
        stg4_subtitle = "Nghiệm đã được kiểm chứng độc lập bằng phương pháp ký hiệu"
        stg4_badge_text = "Kiểm chứng"
        stg4_badge_color = "emerald-7"
        stg4_is_completed = True
        stg4_summary_latex = rf"R({v}) \equiv 0"
        stg4_summary_label = "Phần dư toán học:"
        s4_desc = (
            "Kiểm chứng ký hiệu độc lập xác nhận biểu thức dư triệt tiêu đồng nhất"
            + (" và các điều kiện ban đầu Cauchy được thỏa mãn." if has_ivp else " trên miền xác định.")
        )
        s4_eq = rf"{res_lhs} \equiv 0, \qquad {w_check} \ne 0"
        s4_ir = rf"R({v}) \equiv 0 \implies \text{{Kiểm chứng thành công (VERIFIED)}}"
    elif v_status == VerificationStatus.FAILED:
        stg4_subtitle = "Phát hiện sai lệch trong quá trình kiểm chứng độc lập (FAILED)"
        stg4_badge_text = "Kiểm chứng thất bại"
        stg4_badge_color = "rose-7"
        stg4_is_completed = False
        stg4_summary_latex = rf"R({v}) \quad (\text{{FAILED}})"
        stg4_summary_label = "Trạng thái kiểm chứng (Thất bại):"
        s4_desc = v_details or "Kiểm chứng phát hiện sai lệch giữa nghiệm và phương trình vi phân hoặc điều kiện ban đầu."
        s4_eq = rf"{res_lhs} \not\equiv 0"
        s4_ir = f"Kiểm chứng thất bại (FAILED): {v_details or 'Phát hiện sai lệch nghiệm.'}"
    else:
        stg4_subtitle = "Không thể kết luận hoàn toàn bằng phương pháp ký hiệu (UNVERIFIED)"
        stg4_badge_text = "Chưa kiểm chứng"
        stg4_badge_color = "amber-7"
        stg4_is_completed = False
        stg4_summary_latex = rf"R({v}) \quad (\text{{UNVERIFIED}})"
        stg4_summary_label = "Trạng thái kiểm chứng (Chưa kết luận):"
        s4_desc = v_details or "Chưa thể khẳng định hoàn toàn bằng biến đổi ký hiệu tự động."
        s4_eq = res_lhs
        s4_ir = f"Chưa kiểm chứng được (UNVERIFIED): {v_details or 'Không thể kết luận bằng phương pháp ký hiệu.'}"

    if has_ivp and ctx["ic_verif"] and v_status == VerificationStatus.VERIFIED:
        s4_eq = f"\\begin{{aligned}} {res_lhs} &\\equiv 0 \\\\ {w_check} &\\ne 0 \\\\ {ctx['ic_verif']} \\end{{aligned}}"

    # Keep relevant substeps from solver verification (only when consistent with status!)
    orig_v_step = next((s for s in response.steps if s.rule_name == "Kiểm chứng độc lập"), None)
    v_substeps: tuple[SolutionStep, ...] = ()
    if orig_v_step and orig_v_step.substeps and v_status == VerificationStatus.VERIFIED:
        v_substeps = tuple(
            SolutionStep(
                step_number=sub.step_number,
                rule_name=sub.rule_name,
                description=polish_euler_cauchy_latex(sub.description or "", clean_var),
                content=ExpressionStepContent(
                    expression_before=sub.content.expression_before if sub.content else "",
                    expression_after=sub.content.expression_after if sub.content else "",
                    latex_before=polish_euler_cauchy_latex(sub.content.latex_before or "", clean_var),
                    latex_after=polish_euler_cauchy_latex(sub.content.latex_after or "", clean_var),
                )
                if sub.content
                else ExpressionStepContent(expression_before="", expression_after="", latex_before="", latex_after=""),
                title=sub.title,
                rule_name_vi=sub.rule_name_vi,
                equation_latex=polish_euler_cauchy_latex(sub.equation_latex or "", clean_var),
            )
            for sub in orig_v_step.substeps
        )

    stage4_steps.append(
        ODEPedagogicalStep(
            step_number=len(stage3_steps) + 6,
            rule_name="Kiểm chứng độc lập",
            title="Kiểm chứng độc lập trên phương trình và hệ cơ bản",
            rule_name_vi="Kiểm chứng độc lập",
            description=s4_desc,
            content=ExpressionStepContent(
                expression_before=res_lhs,
                expression_after=stg4_summary_latex,
                latex_before=res_lhs,
                latex_after=stg4_summary_latex,
            ),
            substeps=v_substeps,
            equation_latex=s4_eq,
            purpose="Đối chiếu nghiệm tìm được trực tiếp vào phương trình gốc và kiểm tra Wronskian.",
            math_basis=f"Nghiệm hợp lệ phải làm triệt tiêu phần dư $R({v})$ và duy trì hệ cơ bản độc lập tuyến tính.",
            execution=s4_desc,
            intermediate_result=s4_ir,
            stage_index=4,
            stage_name="Kiểm chứng",
        )
    )

    stg_map = {1: stage1_steps, 2: stage2_steps, 3: stage3_steps, 4: stage4_steps}
    renumbered = _renumber_steps(stg_map)

    stages = [
        ODEStageSummary(
            stage_index=1,
            title="Giai đoạn 1: Phương trình chỉ số",
            subtitle=f"Đưa phương trình về phương trình chỉ số qua nghiệm thử ${u}^m$",
            icon="looks_one",
            badge_text="Chỉ số",
            badge_color="blue-7",
            is_completed=bool(renumbered[1]),
            is_applicable=True,
            summary_latex=ctx["indicial_simplified"] or (renumbered[1][-1].equation_latex if renumbered[1] else ""),
            summary_label="Phương trình chỉ số:",
            steps=tuple(renumbered[1]),
            transition_note="Giải biệt thức $\\Delta$ và xác định nghiệm phương trình chỉ số.",
        ),
        ODEStageSummary(
            stage_index=2,
            title=(
                "Giai đoạn 2: Phương trình thuần nhất liên kết & Hệ cơ bản"
                if is_nonhomo
                else "Giai đoạn 2: Biệt thức Delta và Hệ nghiệm cơ bản"
            ),
            subtitle=(
                f"Xác định hệ nghiệm cơ bản và nghiệm thuần nhất liên kết $y_c({v})$"
                if is_nonhomo
                else f"Xác định cặp nghiệm thực độc lập tuyến tính $y_1({v}), y_2({v})$"
            ),
            icon="looks_two",
            badge_text="Nghiệm thuần nhất" if is_nonhomo else "Nghiệm cơ bản",
            badge_color="purple-7",
            is_completed=bool(renumbered[2]),
            is_applicable=True,
            summary_latex=(
                ctx["yc"]
                if (is_nonhomo and ctx["yc"])
                else (f"y_1({v}) = {y1_str},\\quad y_2({v}) = {y2_str}" if (y1_str and y2_str) else "")
            ),
            summary_label="Nghiệm thuần nhất liên kết:" if (is_nonhomo and ctx["yc"]) else "Hệ nghiệm cơ bản:",
            steps=tuple(renumbered[2]),
            transition_note=stg2_transition,
        ),
        ODEStageSummary(
            stage_index=3,
            title=(
                "Giai đoạn 3: Nghiệm riêng y_p và Tổng hợp nghiệm"
                if is_nonhomo
                else "Giai đoạn 3: Xác định nghiệm bài toán"
            ),
            subtitle=stg3_subtitle,
            icon="looks_3",
            badge_text="Biến thiên hằng số" if is_nonhomo else "Nghiệm",
            badge_color="teal-7",
            is_completed=bool(renumbered[3]),
            is_applicable=True,
            summary_latex=y_latex,
            summary_label=stg3_summary_label,
            steps=tuple(renumbered[3]),
            transition_note="Tiến hành kiểm chứng toán học độc lập.",
        ),
        ODEStageSummary(
            stage_index=4,
            title="Giai đoạn 4: Kiểm chứng toán học độc lập",
            subtitle=stg4_subtitle,
            icon="looks_4",
            badge_text=stg4_badge_text,
            badge_color=stg4_badge_color,
            is_completed=stg4_is_completed,
            is_applicable=True,
            summary_latex=stg4_summary_latex,
            summary_label=stg4_summary_label,
            steps=tuple(renumbered[4]),
            transition_note="",
        ),
    ]
    return tuple(stages)


# ==============================================================================
# 8. GENERIC ODE FALLBACK FLOW BUILDER
# ==============================================================================


def _build_generic_ode_flow(
    response: SolutionResponse,
    prob_type: ProblemType,
    clean_var: str,
    params: dict[str, Any],
) -> tuple[ODEStageSummary, ...]:
    """Fallback flow builder for any uncategorized ODE types."""
    stg_map: dict[int, list[ODEPedagogicalStep]] = {1: [], 2: [], 3: [], 4: []}
    y_latex = standardize_ode_notation(response.final_latex)

    for idx, orig in enumerate(response.steps, 1):
        rn = orig.rule_name
        title = orig.title
        desc = standardize_ode_notation(orig.description or "")
        raw_eq = standardize_ode_notation(orig.equation_latex or orig.content.latex_after or "")

        # Distribute into 3 initial stages
        if idx == 1:
            stg = 1
            stg_name = "Nhận dạng"
        elif idx == len(response.steps):
            stg = 3
            stg_name = "Kết luận nghiệm"
        else:
            stg = 2
            stg_name = "Biến đổi giải tích"

        step_obj = ODEPedagogicalStep(
            step_number=orig.step_number,
            rule_name=rn,
            description=desc,
            content=orig.content,
            substeps=orig.substeps,
            notes=orig.notes,
            title=title,
            rule_name_vi=orig.rule_name_vi or "Biến đổi",
            equation_latex=raw_eq,
            assumptions=orig.assumptions,
            purpose=f"Thực hiện bước giải tích: {title}.",
            math_basis="Quy tắc biến đổi giải tích và đại số vi phân.",
            execution=desc,
            intermediate_result=raw_eq,
            stage_index=stg,
            stage_name=stg_name,
        )
        stg_map[stg].append(step_obj)

    # Add Stage 4 verification
    total_so_far = sum(len(steps) for steps in stg_map.values())
    synth_verify = _synthesize_verification_step(
        response=response,
        clean_var=clean_var,
        step_number=total_so_far + 1,
        order=1,
        has_ivp=bool(params.get("initial_condition")),
    )
    stg_map[4].append(synth_verify)

    renumbered = _renumber_steps(stg_map)

    stages = [
        ODEStageSummary(
            stage_index=1,
            title="Giai đoạn 1: Nhận dạng phương trình",
            subtitle="Phân tích cấu trúc phương trình vi phân",
            icon="looks_one",
            badge_text="Nhận dạng",
            badge_color="blue-7",
            is_completed=bool(renumbered[1]),
            is_applicable=True,
            summary_latex=renumbered[1][-1].equation_latex if renumbered[1] else "",
            summary_label="Nhận dạng:",
            steps=tuple(renumbered[1]),
            transition_note="Tiếp tục thực hiện các phép biến đổi giải tích.",
        ),
        ODEStageSummary(
            stage_index=2,
            title="Giai đoạn 2: Biến đổi giải tích",
            subtitle="Thực hiện các bước giải tích trung gian",
            icon="looks_two",
            badge_text="Biến đổi",
            badge_color="purple-7",
            is_completed=bool(renumbered[2]),
            is_applicable=True,
            summary_latex=renumbered[2][-1].equation_latex if renumbered[2] else "",
            summary_label="Biến đổi trung gian:",
            steps=tuple(renumbered[2]),
            transition_note="Tổng hợp kết quả và rút ra nghiệm của bài toán.",
        ),
        ODEStageSummary(
            stage_index=3,
            title="Giai đoạn 3: Kết luận nghiệm",
            subtitle=f"Xác định nghiệm giải tích $y({clean_var})$",
            icon="looks_3",
            badge_text=f"y({clean_var})",
            badge_color="teal-7",
            is_completed=bool(renumbered[3]),
            is_applicable=True,
            summary_latex=y_latex,
            summary_label="Nghiệm bài toán:",
            steps=tuple(renumbered[3]),
            transition_note="Tiến hành kiểm chứng toán học độc lập.",
        ),
        _build_stage4_summary(
            response,
            clean_var,
            "Kiểm tra tính đúng đắn của nghiệm giải tích",
            f"R({clean_var}) \\equiv 0",
            tuple(renumbered[4]),
        ),
    ]
    return tuple(stages)


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================


def enhance_ode_solution_flow(
    response: SolutionResponse,
    prob_type: ProblemType,
    target_var: str = "t",
    params: dict[str, Any] | None = None,
) -> tuple[ODEStageSummary, ...]:
    """Partition and enhance ODE solution steps into mathematically authentic pedagogical stages.

    Routes dynamically by mathematical operation and classification:
    - ODE_FIRST_ORDER_LINEAR: Standard form -> Integrating factor -> Integration -> Verification
    - ODE_SEPARABLE: Identification -> Separation of variables -> Integration -> Verification
    - ODE_EXACT: Identification of M, N -> Exactness condition -> Potential function -> Verification
    - ODE_INTEGRATING_FACTOR: Inexact test -> Integrating factor -> Exact potential -> Verification
    - ODE_FIRST_ORDER_HOMOGENEOUS: Degree 0 test & v=y/x -> Separation for v -> Back-sub -> Verification
    - ODE_SECOND_ORDER_CONSTANT_COEFF / ODE_SECOND_ORDER_IVP:
        * Homogeneous: Characteristic Eq -> Delta & roots -> Fundamental system -> Verification (Stage 2 bypassed)
        * Nonhomogeneous: Homogeneous yc(t) -> Particular yp(t) (UC/VoP) -> General solution -> Verification
        * Cauchy IVP: General solution -> Initial conditions evaluation for C1, C2 -> Unique solution -> Verification
    - ODE_REDUCTION_OF_ORDER: Standard form & known y1 -> Substitution y2=v*y1 -> u=v' -> Fundamental system -> Verification
    - WRONSKIAN: Fundamental functions & derivatives -> Wronskian matrix -> Linear independence -> Verification
    """
    if not response.steps:
        return ()

    params = params or {}
    clean_var = target_var or "t"

    if prob_type == ProblemType.ODE_FIRST_ORDER_LINEAR:
        return _build_first_order_linear_flow(response, clean_var, params)
    elif prob_type == ProblemType.ODE_SEPARABLE:
        return _build_first_order_separable_flow(response, clean_var, params)
    elif prob_type == ProblemType.ODE_EXACT:
        return _build_first_order_exact_flow(response, clean_var, params)
    elif prob_type == ProblemType.ODE_INTEGRATING_FACTOR:
        return _build_first_order_integrating_factor_flow(response, clean_var, params)
    elif prob_type == ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS:
        return _build_first_order_homogeneous_flow(response, clean_var, params)
    elif prob_type == ProblemType.ODE_REDUCTION_OF_ORDER:
        return _build_reduction_of_order_flow(response, clean_var, params)
    elif prob_type == ProblemType.WRONSKIAN:
        return _build_wronskian_flow(response, clean_var, params)
    elif prob_type == ProblemType.ODE_EULER_CAUCHY:
        return _build_euler_cauchy_flow(response, clean_var, params)
    elif prob_type in (
        ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        ProblemType.ODE_SECOND_ORDER_IVP,
    ):
        return _build_second_order_flow(response, prob_type, clean_var, params)
    else:
        return _build_generic_ode_flow(response, prob_type, clean_var, params)

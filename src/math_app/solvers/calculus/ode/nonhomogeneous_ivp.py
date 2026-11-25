"""Nonhomogeneous Cauchy Initial Value Problem (IVP) Engine for Second-Order Linear ODEs.

Handles:
- Exact symbolic domain and singularity validation of initial point t0 against g(t).
- Evaluation of particular solution Y_p(t0) and derivative Y_p'(t0).
- Special canonical simplification for anchored Variation of Parameters:
    u1(t0) = u2(t0) = 0 => Y_p(t0) = 0 and Y_p'(t0) = 0.
- Exact solution of the 2x2 linear system for arbitrary constants C1, C2:
    [y1(t0)   y2(t0) ] [C1] = [y0 - Y_p(t0) ]
    [y1'(t0)  y2'(t0)] [C2]   [v0 - Y_p'(t0)]
- Step-by-step pedagogical derivations formatted in Vietnamese with LaTeX.
- Assembly of unique Cauchy solution y(t) = C1*y1(t) + C2*y2(t) + Y_p(t).
"""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp

from math_app.application.dtos import SolutionStep
from math_app.domain.step_content import ExpressionStepContent
from math_app.rendering.latex.formatter import expr_to_latex


@dataclass(frozen=True)
class NonhomogeneousCauchyResult:
    """Result of solving a second-order nonhomogeneous Cauchy IVP system."""

    is_valid: bool
    c1_value: sp.Expr = sp.Integer(0)
    c2_value: sp.Expr = sp.Integer(0)
    y_ivp_solution: sp.Expr = sp.Integer(0)
    particular_solution: sp.Expr = sp.Integer(0)
    d_particular_solution: sp.Expr = sp.Integer(0)
    yp_at_t0: sp.Expr = sp.Integer(0)
    dyp_at_t0: sp.Expr = sp.Integer(0)
    matrix_a: tuple[tuple[sp.Expr, sp.Expr], tuple[sp.Expr, sp.Expr]] = (
        (sp.Integer(0), sp.Integer(0)),
        (sp.Integer(0), sp.Integer(0)),
    )
    vector_b: tuple[sp.Expr, sp.Expr] = (sp.Integer(0), sp.Integer(0))
    steps: tuple[SolutionStep, ...] = ()
    error_reason: str | None = None


def validate_initial_point_against_domain(
    t0: sp.Expr,
    g_expr: sp.Expr,
    var: sp.Symbol,
    domain_restrictions: tuple[str, ...] = (),
    interval_str: str | None = None,
) -> tuple[bool, str | None]:
    """Validate whether the Cauchy initial point t0 lies in the valid domain of the ODE."""
    # Check finiteness and reality of t0
    if t0.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or t0.is_finite is False:
        return False, f"Điểm ban đầu {var}0 = {t0} không phải là số thực hữu hạn."
    if t0.is_real is False or (t0.has(sp.I) and not sp.simplify(t0).is_real):
        return False, f"Điểm ban đầu {var}0 = {t0} chứa phần ảo hoặc không phải là số thực."

    if g_expr == 0:
        return True, None

    # Inspect g(t) AST for singularities at t = t0
    for node in sp.preorder_traversal(g_expr):
        if isinstance(node, sp.log):
            arg = node.args[0]
            val = sp.simplify(arg.subs(var, t0))
            if val.is_number and val <= 0:
                return False, (
                    f"Điểm ban đầu {var}0 = {t0} vi phạm điều kiện xác định của hàm logarit: "
                    f"biểu thức {arg} = {val} <= 0."
                )
        elif isinstance(node, sp.Pow):
            base, exp_val = node.as_base_exp()
            if exp_val.is_negative:
                b_val = sp.simplify(base.subs(var, t0))
                if b_val == 0:
                    return False, (
                        f"Điểm ban đầu {var}0 = {t0} làm triệt tiêu mẫu số của phương trình: "
                        f"{base} = 0."
                    )
            elif exp_val.is_Rational and exp_val.q % 2 == 0:
                b_val = sp.simplify(base.subs(var, t0))
                if b_val.is_number and b_val < 0:
                    return False, (
                        f"Điểm ban đầu {var}0 = {t0} vi phạm điều kiện căn bậc chẵn: "
                        f"{base} = {b_val} < 0."
                    )
        elif isinstance(node, (sp.tan, sp.sec)):
            arg = node.args[0]
            cos_val = sp.simplify(sp.cos(arg).subs(var, t0))
            if cos_val == 0:
                return False, (
                    f"Điểm ban đầu {var}0 = {t0} là điểm cực (pole) của hàm tan/sec: "
                    f"cos({arg}) = 0."
                )
        elif isinstance(node, (sp.cot, sp.csc)):
            arg = node.args[0]
            sin_val = sp.simplify(sp.sin(arg).subs(var, t0))
            if sin_val == 0:
                return False, (
                    f"Điểm ban đầu {var}0 = {t0} là điểm cực (pole) của hàm cot/csc: "
                    f"sin({arg}) = 0."
                )

    return True, None


def _format_linear_comb(
    k1: sp.Expr,
    k2: sp.Expr,
    k1_ltx: str,
    k2_ltx: str,
) -> str:
    """Format k1*C_1 + k2*C_2 cleanly in LaTeX."""
    if k1 == 0:
        term1 = ""
    elif k1 == 1:
        term1 = "C_1"
    elif k1 == -1:
        term1 = "-C_1"
    elif "+" in k1_ltx or ("-" in k1_ltx and not k1_ltx.startswith("-")):
        term1 = f"\\left({k1_ltx}\\right) C_1"
    elif k1_ltx.startswith("-") and ("+" in k1_ltx or r"\sqrt" in k1_ltx):
        term1 = f"\\left({k1_ltx}\\right) C_1"
    else:
        term1 = f"{k1_ltx}\\,C_1"

    if k2 == 0:
        return term1 if term1 else "0"
    if not term1:
        if k2 == 1:
            return "C_2"
        if k2 == -1:
            return "-C_2"
        return f"{k2_ltx}\\,C_2"

    if k2 == 1:
        return f"{term1} + C_2"
    if k2 == -1:
        return f"{term1} - C_2"
    if "+" in k2_ltx or ("-" in k2_ltx and not k2_ltx.startswith("-")):
        return f"{term1} + \\left({k2_ltx}\\right) C_2"
    elif k2_ltx.startswith("-"):
        if "+" in k2_ltx or r"\sqrt" in k2_ltx:
            return f"{term1} + \\left({k2_ltx}\\right) C_2"
        pos_k2_ltx = k2_ltx.lstrip("-")
        return f"{term1} - {pos_k2_ltx}\\,C_2"
    else:
        return f"{term1} + {k2_ltx}\\,C_2"


def solve_nonhomogeneous_cauchy_system(
    y1: sp.Expr,
    y2: sp.Expr,
    yp: sp.Expr,
    t0: sp.Expr,
    y0: sp.Expr,
    v0: sp.Expr,
    var: sp.Symbol,
    start_step_num: int = 1,
    is_anchored_vop: bool = False,
    method_name: str = "Hệ số bất định",
) -> NonhomogeneousCauchyResult:
    """Solve the 2x2 Cauchy system to determine arbitrary constants C1, C2 for a nonhomogeneous ODE."""
    c1_sym = sp.Symbol("C1")
    c2_sym = sp.Symbol("C2")

    # 1. Fundamental solutions and derivatives at t0
    dy1 = sp.diff(y1, var)
    dy2 = sp.diff(y2, var)
    dyp = sp.diff(yp, var)

    c11 = sp.simplify(y1.subs(var, t0))
    c12 = sp.simplify(y2.subs(var, t0))
    c21 = sp.simplify(dy1.subs(var, t0))
    c22 = sp.simplify(dy2.subs(var, t0))

    # Evaluate particular solution and derivative at t0
    if is_anchored_vop:
        yp_at_t0 = sp.Integer(0)
        dyp_at_t0 = sp.Integer(0)
    else:
        yp_at_t0 = sp.simplify(yp.subs(var, t0))
        dyp_at_t0 = sp.simplify(dyp.subs(var, t0))

    b1 = sp.simplify(y0 - yp_at_t0)
    b2 = sp.simplify(v0 - dyp_at_t0)

    # 2. Wronskian determinant at initial point
    w_t0 = sp.simplify(c11 * c22 - c12 * c21)
    if w_t0 == 0:
        return NonhomogeneousCauchyResult(
            is_valid=False,
            error_reason=(
                f"Định thức Wronskian tại điểm ban đầu W({t0}) = {w_t0} triệt tiêu; "
                "ma trận hệ Cauchy suy biến, không xác định được nghiệm duy nhất."
            ),
        )

    # 3. Solve for C1 and C2 via Cramer's rule
    c1_val = sp.simplify((b1 * c22 - b2 * c12) / w_t0)
    c2_val = sp.simplify((c11 * b2 - c21 * b1) / w_t0)

    # 4. Unique Cauchy solution
    y_ivp = sp.simplify(c1_val * y1 + c2_val * y2) + yp

    # 5. Pedagogical derivations
    steps: list[SolutionStep] = []
    cur_step = start_step_num

    # Step: Derivative of General Solution
    d_gen_sol = c1_sym * dy1 + c2_sym * dy2 + dyp
    deriv_eq_latex = f"y'({var}) = {expr_to_latex(d_gen_sol)}"
    if is_anchored_vop:
        deriv_desc = (
            f"Tính đạo hàm cấp một của nghiệm tổng quát theo biến ${var}$:\n"
            f"$$y'({var}) = C_1 y_1'({var}) + C_2 y_2'({var}) + Y_p'({var})$$\n"
            f"với $Y_p({var})$ là nghiệm riêng xây dựng bằng tích phân biến thiên hằng số neo tại điểm ban đầu "
            f"${var}_0 = {expr_to_latex(t0)}$:\n"
            f"Do cận tích phân xuất phát từ ${var}_0$, theo định lý cơ bản của giải tích và điều kiện phụ trợ Lagrange:\n"
            f"$$Y_p({expr_to_latex(t0)}) = 0, \\quad Y_p'({expr_to_latex(t0)}) = 0.$$"
        )
    else:
        deriv_desc = (
            f"Tính đạo hàm cấp một của nghiệm tổng quát theo biến ${var}$:\n"
            f"$$y'({var}) = \\frac{{d}}{{d{var}}}[y({var})] = "
            f"C_1 \\left({expr_to_latex(dy1)}\\right) + C_2 \\left({expr_to_latex(dy2)}\\right) + "
            f"\\left({expr_to_latex(dyp)}\\right) = {expr_to_latex(d_gen_sol)}$$."
        )

    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Đạo hàm nghiệm tổng quát",
            title="Tính đạo hàm cấp một của nghiệm tổng quát",
            description=deriv_desc,
            content=ExpressionStepContent(
                expression_before=f"y({var}) = C1*y1 + C2*y2 + Y_p",
                expression_after=f"y'({var}) = {d_gen_sol}",
                latex_before=r"y(t) = C_1 y_1(t) + C_2 y_2(t) + Y_p(t)",
                latex_after=deriv_eq_latex,
            ),
            equation_latex=deriv_eq_latex,
        )
    )
    cur_step += 1

    # Step: Cauchy Linear System Formation
    c11_ltx = expr_to_latex(c11)
    c12_ltx = expr_to_latex(c12)
    c21_ltx = expr_to_latex(c21)
    c22_ltx = expr_to_latex(c22)

    eq1_lhs_latex = _format_linear_comb(c11, c12, c11_ltx, c12_ltx)
    eq2_lhs_latex = _format_linear_comb(c21, c22, c21_ltx, c22_ltx)

    b1_ltx = expr_to_latex(b1)
    b2_ltx = expr_to_latex(b2)

    matrix_system_latex = (
        f"\\begin{{pmatrix}} {c11_ltx} & {c12_ltx} \\\\ {c21_ltx} & {c22_ltx} \\end{{pmatrix}} "
        f"\\begin{{pmatrix}} C_1 \\\\ C_2 \\end{{pmatrix}} = "
        f"\\begin{{pmatrix}} {b1_ltx} \\\\ {b2_ltx} \\end{{pmatrix}}"
    )
    system_cases_latex = (
        f"\\begin{{cases}} "
        f"{eq1_lhs_latex} = {b1_ltx} \\\\ "
        f"{eq2_lhs_latex} = {b2_ltx} "
        f"\\end{{cases}}"
    )

    if is_anchored_vop:
        step_cauchy_desc = (
            f"Áp dụng hệ điều kiện ban đầu Cauchy tại điểm ${var} = {expr_to_latex(t0)}$:\n\n"
            f"1. Điều kiện giá trị ban đầu $y({expr_to_latex(t0)}) = {expr_to_latex(y0)}$:\n"
            f"$$C_1 y_1({expr_to_latex(t0)}) + C_2 y_2({expr_to_latex(t0)}) + Y_p({expr_to_latex(t0)}) = {expr_to_latex(y0)}$$\n"
            f"Do $Y_p({expr_to_latex(t0)}) = 0$, phương trình trở thành:\n"
            f"$${eq1_lhs_latex} = {b1_ltx}$$\n\n"
            f"2. Điều kiện đạo hàm ban đầu $y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}$:\n"
            f"$$C_1 y_1'({expr_to_latex(t0)}) + C_2 y_2'({expr_to_latex(t0)}) + Y_p'({expr_to_latex(t0)}) = {expr_to_latex(v0)}$$\n"
            f"Do $Y_p'({expr_to_latex(t0)}) = 0$, phương trình trở thành:\n"
            f"$${eq2_lhs_latex} = {b2_ltx}$$\n\n"
            f"3. Hệ phương trình đại số tuyến tính xác định $C_1, C_2$:\n"
            f"$${system_cases_latex}$$"
        )
    else:
        step_cauchy_desc = (
            f"Áp dụng hệ điều kiện ban đầu Cauchy tại điểm ${var} = {expr_to_latex(t0)}$:\n\n"
            f"1. Điều kiện giá trị ban đầu $y({expr_to_latex(t0)}) = {expr_to_latex(y0)}$:\n"
            f"$$C_1 y_1({expr_to_latex(t0)}) + C_2 y_2({expr_to_latex(t0)}) + Y_p({expr_to_latex(t0)}) = {expr_to_latex(y0)}$$\n"
            f"Thay $Y_p({expr_to_latex(t0)}) = {expr_to_latex(yp_at_t0)}$, ta chuyển vế:\n"
            f"$${eq1_lhs_latex} = {expr_to_latex(y0)} - \\left({expr_to_latex(yp_at_t0)}\\right) = {b1_ltx}$$\n\n"
            f"2. Điều kiện đạo hàm ban đầu $y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}$:\n"
            f"$$C_1 y_1'({expr_to_latex(t0)}) + C_2 y_2'({expr_to_latex(t0)}) + Y_p'({expr_to_latex(t0)}) = {expr_to_latex(v0)}$$\n"
            f"Thay $Y_p'({expr_to_latex(t0)}) = {expr_to_latex(dyp_at_t0)}$, ta chuyển vế:\n"
            f"$${eq2_lhs_latex} = {expr_to_latex(v0)} - \\left({expr_to_latex(dyp_at_t0)}\\right) = {b2_ltx}$$\n\n"
            f"3. Hệ phương trình đại số tuyến tính xác định $C_1, C_2$:\n"
            f"$${system_cases_latex}$$"
        )

    sub_step1 = SolutionStep(
        step_number=1,
        rule_name="Thay điều kiện y(t0) = y0",
        title=f"Thay điều kiện ban đầu y({t0}) = {y0}",
        description=f"Thay điều kiện hàm số tại ${var} = {expr_to_latex(t0)}$ thu được $${eq1_lhs_latex} = {b1_ltx}$$.",
        content=ExpressionStepContent(
            expression_before=f"y({t0}) = {y0}",
            expression_after=f"{c11}*C1 + {c12}*C2 = {b1}",
            latex_before=f"y({expr_to_latex(t0)}) = {expr_to_latex(y0)}",
            latex_after=f"{eq1_lhs_latex} = {b1_ltx}",
        ),
        equation_latex=f"{eq1_lhs_latex} = {b1_ltx}",
    )
    sub_step2 = SolutionStep(
        step_number=2,
        rule_name="Thay điều kiện y'(t0) = v0",
        title=f"Thay điều kiện đạo hàm y'({t0}) = {v0}",
        description=f"Thay điều kiện đạo hàm tại ${var} = {expr_to_latex(t0)}$ thu được $${eq2_lhs_latex} = {b2_ltx}$$.",
        content=ExpressionStepContent(
            expression_before=f"y'({t0}) = {v0}",
            expression_after=f"{c21}*C1 + {c22}*C2 = {b2}",
            latex_before=f"y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}",
            latex_after=f"{eq2_lhs_latex} = {b2_ltx}",
        ),
        equation_latex=f"{eq2_lhs_latex} = {b2_ltx}",
    )
    sub_step3 = SolutionStep(
        step_number=3,
        rule_name="Hệ ma trận 2x2",
        title="Biểu diễn hệ phương trình dạng ma trận 2x2",
        description=f"Biểu diễn hệ phương trình dưới dạng ma trận $A \\mathbf{{C}} = \\mathbf{{B}}$:\n$${matrix_system_latex}$$",
        content=ExpressionStepContent(
            expression_before=f"{c11}*C1 + {c12}*C2 = {b1}, {c21}*C1 + {c22}*C2 = {b2}",
            expression_after=f"[{c11}, {c12}; {c21}, {c22}] * [C1; C2] = [{b1}; {b2}]",
            latex_before=f"{eq1_lhs_latex} = {b1_ltx}, \\quad {eq2_lhs_latex} = {b2_ltx}",
            latex_after=matrix_system_latex,
        ),
        equation_latex=matrix_system_latex,
    )

    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Áp dụng điều kiện ban đầu",
            title="Thiết lập hệ phương trình xác định hằng số C1, C2",
            description=step_cauchy_desc,
            content=ExpressionStepContent(
                expression_before=f"y({t0}) = {y0}, y'({t0}) = {v0}",
                expression_after=f"{c11}*C1 + {c12}*C2 = {b1}, {c21}*C1 + {c22}*C2 = {b2}",
                latex_before=f"y({expr_to_latex(t0)}) = {expr_to_latex(y0)}, \\quad y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}",
                latex_after=system_cases_latex,
            ),
            equation_latex=system_cases_latex,
            substeps=(sub_step1, sub_step2, sub_step3),
        )
    )
    cur_step += 1

    # Step: Solve System for C1, C2
    c1_ltx = expr_to_latex(c1_val)
    c2_ltx = expr_to_latex(c2_val)
    w_t0_ltx = expr_to_latex(w_t0)

    solve_desc = (
        f"Giải hệ phương trình đại số tuyến tính $2 \\times 2$ bằng quy tắc Cramer:\n\n"
        f"1. Định thức ma trận hệ số:\n"
        f"$$\\det(A) = W({expr_to_latex(t0)}) = "
        f"\\left({c11_ltx}\\right)\\left({c22_ltx}\\right) - "
        f"\\left({c12_ltx}\\right)\\left({c21_ltx}\\right) = {w_t0_ltx} \\ne 0$$\n\n"
        f"2. Nghiệm của hệ:\n"
        f"$$C_1 = \\frac{{\\left({b1_ltx}\\right)\\left({c22_ltx}\\right) - "
        f"\\left({c12_ltx}\\right)\\left({b2_ltx}\\right)}}{{{w_t0_ltx}}} = {c1_ltx}$$\n\n"
        f"$$C_2 = \\frac{{\\left({c11_ltx}\\right)\\left({b2_ltx}\\right) - "
        f"\\left({b1_ltx}\\right)\\left({c21_ltx}\\right)}}{{{w_t0_ltx}}} = {c2_ltx}$$"
    )

    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Giải hệ xác định hằng số",
            title="Giải hệ đại số xác định nghiệm duy nhất của C1 và C2",
            description=solve_desc,
            content=ExpressionStepContent(
                expression_before=f"[{c11}, {c12}; {c21}, {c22}] * [C1; C2] = [{b1}; {b2}]",
                expression_after=f"C1 = {c1_val}, C2 = {c2_val}",
                latex_before=matrix_system_latex,
                latex_after=f"C_1 = {c1_ltx}, \\quad C_2 = {c2_ltx}",
            ),
            equation_latex=f"C_1 = {c1_ltx}, \\quad C_2 = {c2_ltx}",
        )
    )
    cur_step += 1

    # Step: Assemble Unique Cauchy Particular Solution
    y_ivp_ltx = expr_to_latex(y_ivp)
    assemble_desc = (
        f"Thay các giá trị hằng số $C_1 = {c1_ltx}$ và $C_2 = {c2_ltx}$ "
        f"vào dạng nghiệm tổng quát thu được nghiệm duy nhất của bài toán Cauchy:\n"
        f"$$y({var}) = {y_ivp_ltx}$$\n\n"
        f"Nghiệm này thỏa mãn đồng thời phương trình vi phân và cả hai điều kiện ban đầu "
        f"$y({expr_to_latex(t0)}) = {expr_to_latex(y0)}$ và $y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}$."
    )

    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Nghiệm duy nhất bài toán Cauchy",
            title="Tổng hợp nghiệm duy nhất của bài toán Cauchy",
            description=assemble_desc,
            content=ExpressionStepContent(
                expression_before=f"y({var}) = C1*y1 + C2*y2 + Y_p",
                expression_after=f"y({var}) = {y_ivp}",
                latex_before=r"y(t) = C_1 y_1(t) + C_2 y_2(t) + Y_p(t)",
                latex_after=f"y({var}) = {y_ivp_ltx}",
            ),
            equation_latex=f"y({var}) = {y_ivp_ltx}",
        )
    )

    return NonhomogeneousCauchyResult(
        is_valid=True,
        c1_value=c1_val,
        c2_value=c2_val,
        y_ivp_solution=y_ivp,
        particular_solution=yp,
        d_particular_solution=dyp,
        yp_at_t0=yp_at_t0,
        dyp_at_t0=dyp_at_t0,
        matrix_a=((c11, c12), (c21, c22)),
        vector_b=(b1, b2),
        steps=tuple(steps),
    )

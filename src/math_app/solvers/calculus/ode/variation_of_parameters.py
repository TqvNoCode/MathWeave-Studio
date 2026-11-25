"""Method of Variation of Parameters (Lagrange) Engine for Second-Order Linear ODEs.

Solves:
    a*y'' + b*y' + c*y = g(t),  a != 0, g(t) != 0,
using the fundamental pair {y1, y2} of the associated homogeneous equation,
evaluating the Wronskian W(y1, y2) = y1*y2' - y1'*y2 != 0,
solving the Lagrange auxiliary system:
    u1'*y1  + u2'*y2  = 0
    u1'*y1' + u2'*y2' = g(t)/a = f(t)
integrating:
    u1(t) = -Integral( y2(t)*g(t) / (a*W(t)), t )
    u2(t) =  Integral( y1(t)*g(t) / (a*W(t)), t )
and constructing the particular solution:
    Yp(t) = u1(t)*y1(t) + u2(t)*y2(t),
with exact symbolic closed forms or exact unevaluated Integral representations,
domain singularity tracking, and comprehensive Vietnamese pedagogical derivations.
"""

from __future__ import annotations

from dataclasses import dataclass
import sympy as sp

from math_app.application.dtos import SolutionStep
from math_app.domain.step_content import ExpressionStepContent
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.solvers.calculus.ode.undetermined_coefficients import evaluate_zero_state


class VariationOfParametersError(Exception):
    """Base exception for failures in the Method of Variation of Parameters."""


class WronskianZeroError(VariationOfParametersError):
    """Raised when the Wronskian vanishes identically or is linearly dependent."""


@dataclass(frozen=True)
class VariationOfParametersResult:
    """Structured result returned by the Variation of Parameters engine."""

    is_supported: bool
    particular_solution: sp.Expr = sp.Integer(0)
    u1_expr: sp.Expr = sp.Integer(0)
    u2_expr: sp.Expr = sp.Integer(0)
    u1_prime: sp.Expr = sp.Integer(0)
    u2_prime: sp.Expr = sp.Integer(0)
    wronskian: sp.Expr = sp.Integer(0)
    is_integral_form: bool = False
    steps: tuple[SolutionStep, ...] = ()
    domain_restrictions: tuple[str, ...] = ()
    domain_interval: tuple[sp.Expr | float, sp.Expr | float] | str | None = None
    unsupported_reason: str | None = None
    initial_point: sp.Expr | None = None


def extract_domain_restrictions_from_expr(
    expr: sp.Expr,
    var: sp.Symbol,
) -> list[str]:
    """Inspect mathematical expression AST to detect implicit domain restrictions."""
    restrictions: list[str] = []

    for node in sp.preorder_traversal(expr):
        if isinstance(node, sp.log):
            arg = node.args[0]
            if arg.has(var):
                restrictions.append(f"{arg} > 0")
        elif isinstance(node, sp.Pow):
            base, exp_val = node.as_base_exp()
            if base.has(var):
                if exp_val.is_negative:
                    restrictions.append(f"{base} != 0")
                elif exp_val.is_Rational and exp_val.q % 2 == 0:
                    restrictions.append(f"{base} >= 0")
        elif isinstance(node, sp.tan):
            arg = node.args[0]
            if arg.has(var):
                restrictions.append(f"{arg} != pi/2 + k*pi")
        elif isinstance(node, sp.sec):
            arg = node.args[0]
            if arg.has(var):
                restrictions.append(f"{arg} != pi/2 + k*pi")
        elif isinstance(node, (sp.cot, sp.csc)):
            arg = node.args[0]
            if arg.has(var):
                restrictions.append(f"{arg} != k*pi")

    # Deduplicate while preserving order
    dedup: list[str] = []
    for r in restrictions:
        if r not in dedup:
            dedup.append(r)
    return dedup


def solve_variation_of_parameters(
    a: sp.Expr,
    b: sp.Expr,
    c: sp.Expr,
    g_expr: sp.Expr,
    y1: sp.Expr,
    y2: sp.Expr,
    var: sp.Symbol,
    start_step_num: int = 5,
    domain_restrictions: tuple[str, ...] = (),
    domain_interval: tuple[sp.Expr | float, sp.Expr | float] | str | None = None,
    initial_point: sp.Expr | None = None,
) -> VariationOfParametersResult:
    """Execute the Method of Variation of Parameters for a*y'' + b*y' + c*y = g(t).

    Parameters:
        a, b, c: Coefficients of the second-order linear ODE.
        g_expr: Forcing function g(t) = -rem_expr.
        y1, y2: Linearly independent fundamental solutions of the homogeneous equation.
        var: Independent target variable symbol (e.g. t or x).
        start_step_num: Step number to start pedagogical derivations from.
        domain_restrictions: Existing domain restrictions from parsing.
        domain_interval: Solution interval if specified.
        initial_point: Optional initial point t0 for Cauchy IVP canonical anchoring.

    Returns:
        VariationOfParametersResult containing particular solution, u1, u2,
        Wronskian, derivation steps, and status metadata.
    """
    if a == 0:
        return VariationOfParametersResult(
            is_supported=False,
            unsupported_reason="Hệ số của y'' bằng 0 (a != 0 required).",
        )

    # 1. First derivatives of fundamental solutions
    dy1 = sp.diff(y1, var)
    dy2 = sp.diff(y2, var)

    # 2. Wronskian computation and validation
    w_raw = y1 * dy2 - dy1 * y2
    w_simp = sp.simplify(sp.trigsimp(sp.simplify(w_raw)))

    w_zero = evaluate_zero_state(w_simp)
    if w_zero is True:
        return VariationOfParametersResult(
            is_supported=False,
            unsupported_reason=(
                f"Định thức Wronskian W(y1, y2) = {w_simp} triệt tiêu đồng nhất; "
                "hai nghiệm không độc lập tuyến tính."
            ),
        )
    elif w_zero is None:
        return VariationOfParametersResult(
            is_supported=False,
            unsupported_reason=(
                f"Định thức Wronskian W(y1, y2) = {w_simp} chứa tham số chưa xác định được tính khác không."
            ),
        )

    # 3. Normalized forcing function f(t) = g(t) / a
    f_expr = sp.simplify(g_expr / a)

    # 4. Auxiliary Lagrange system equations:
    # u1'*y1  + u2'*y2  = 0
    # u1'*y1' + u2'*y2' = f(t)
    # Cramer's formulas:
    # u1' = -y2 * f / W = -y2 * g / (a * W)
    # u2' =  y1 * f / W =  y1 * g / (a * W)
    u1_prime_raw = -y2 * f_expr / w_simp
    u2_prime_raw = y1 * f_expr / w_simp

    u1_prime = sp.simplify(sp.trigsimp(u1_prime_raw))
    u2_prime = sp.simplify(sp.trigsimp(u2_prime_raw))

    # 5. Symbolic Integration for u1(t) and u2(t)
    is_integral_form = False
    u1_sol: sp.Expr
    u2_sol: sp.Expr

    if initial_point is not None:
        # Canonical initial-point-anchored definite integrals for Cauchy IVP:
        # u1(t) = -Integral( y2(s)*g(s) / (a*W(s)), (s, t0, t) )
        # u2(t) =  Integral( y1(s)*g(s) / (a*W(s)), (s, t0, t) )
        # such that u1(t0) = 0 and u2(t0) = 0 => Y_p(t0) = 0 and Y_p'(t0) = 0.
        s = sp.Symbol("s") if var.name != "s" else sp.Symbol("tau")
        integrand1 = sp.simplify(-y2.subs(var, s) * f_expr.subs(var, s) / w_simp.subs(var, s))
        integrand2 = sp.simplify(y1.subs(var, s) * f_expr.subs(var, s) / w_simp.subs(var, s))
        u1_sol = sp.Integral(integrand1, (s, initial_point, var))
        u2_sol = sp.Integral(integrand2, (s, initial_point, var))
        is_integral_form = True
    else:
        # Attempt symbolic integration for u1
        try:
            u1_int = sp.integrate(u1_prime, var)
            if u1_int.has(sp.Integral) or u1_int.has(sp.meijerg):
                is_integral_form = True
                u1_sol = -sp.Integral(sp.simplify(y2 * f_expr / w_simp), var)
            else:
                u1_sol = sp.simplify(u1_int)
        except Exception:
            is_integral_form = True
            u1_sol = -sp.Integral(sp.simplify(y2 * f_expr / w_simp), var)

        # Attempt symbolic integration for u2
        try:
            u2_int = sp.integrate(u2_prime, var)
            if u2_int.has(sp.Integral) or u2_int.has(sp.meijerg):
                is_integral_form = True
                u2_sol = sp.Integral(sp.simplify(y1 * f_expr / w_simp), var)
            else:
                u2_sol = sp.simplify(u2_int)
        except Exception:
            is_integral_form = True
            u2_sol = sp.Integral(sp.simplify(y1 * f_expr / w_simp), var)

    # 6. Assemble Particular Solution Yp(t) = u1(t)*y1(t) + u2(t)*y2(t)
    if is_integral_form:
        yp_sol = u1_sol * y1 + u2_sol * y2
    else:
        yp_raw = u1_sol * y1 + u2_sol * y2
        yp_simp = sp.simplify(yp_raw)
        if yp_simp != 0:
            yp_sol = yp_simp
        else:
            yp_sol = yp_raw

    # 7. Verification of the particular solution against a*Yp'' + b*Yp' + c*Yp = g(t)
    d_yp = sp.diff(yp_sol, var)
    d2_yp = sp.diff(d_yp, var)
    residual = sp.simplify(a * d2_yp + b * d_yp + c * yp_sol - g_expr)
    if residual != 0:
        residual = sp.simplify(sp.trigsimp(residual))
    if residual != 0 and hasattr(residual, "doit"):
        residual = sp.simplify(residual.doit())

    if residual != 0 and not is_integral_form:
        # Fallback to exact unevaluated integral form if closed-form simplification failed
        is_integral_form = True
        u1_sol = -sp.Integral(sp.simplify(y2 * f_expr / w_simp), var)
        u2_sol = sp.Integral(sp.simplify(y1 * f_expr / w_simp), var)
        yp_sol = u1_sol * y1 + u2_sol * y2
        d_yp = sp.diff(yp_sol, var)
        d2_yp = sp.diff(d_yp, var)
        residual = sp.simplify(a * d2_yp + b * d_yp + c * yp_sol - g_expr)
        if residual != 0:
            residual = sp.simplify(sp.trigsimp(residual))

    if residual != 0:
        return VariationOfParametersResult(
            is_supported=False,
            unsupported_reason=(
                f"Nghiệm riêng Yp không triệt tiêu biểu thức dư: R({var}) = {residual} != 0."
            ),
        )

    # 8. Domain restrictions enrichment
    all_restrictions = list(domain_restrictions)
    detected_restrs = extract_domain_restrictions_from_expr(g_expr, var)
    for r in detected_restrs:
        if r not in all_restrictions:
            all_restrictions.append(r)

    # 9. Pedagogical Steps Generation
    steps: list[SolutionStep] = []
    cur_step = start_step_num

    # Step: Method Selection Explanation
    method_desc = (
        f"Phương trình có vế phải $g({var}) = {expr_to_latex(g_expr)}$. "
        f"Do hàm cưỡng bức $g({var})$ không thuộc các họ đa thức, mũ, lượng giác cơ bản "
        f"hoặc tích của chúng để áp dụng phương pháp Hệ số bất định, "
        f"ta sử dụng **phương pháp Biến thiên hằng số (phương pháp Lagrange)** để tìm nghiệm riêng toàn quát."
    )
    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Phương pháp Biến thiên hằng số",
            title="Lựa chọn phương pháp Biến thiên hằng số (Lagrange)",
            description=method_desc,
            content=ExpressionStepContent(
                expression_before=f"g({var}) = {g_expr}",
                expression_after="Lagrange method",
                latex_before=f"g({var}) = {expr_to_latex(g_expr)}",
                latex_after=r"\text{Method of Variation of Parameters (Lagrange)}",
            ),
            equation_latex=r"\text{Phương pháp Biến thiên hằng số (Lagrange)}",
        )
    )
    cur_step += 1

    # Step: Wronskian Calculation
    matrix_latex = (
        f"W(y_1, y_2)({var}) = "
        f"\\begin{{vmatrix}} y_1 & y_2 \\\\ y_1' & y_2' \\end{{vmatrix}} = "
        f"\\begin{{vmatrix}} {expr_to_latex(y1)} & {expr_to_latex(y2)} \\\\ "
        f"{expr_to_latex(dy1)} & {expr_to_latex(dy2)} \\end{{vmatrix}}"
    )
    wronskian_eval_latex = (
        f"{matrix_latex} = \\left({expr_to_latex(y1)}\\right)\\left({expr_to_latex(dy2)}\\right) - "
        f"\\left({expr_to_latex(dy1)}\\right)\\left({expr_to_latex(y2)}\\right) = {expr_to_latex(w_simp)}"
    )
    wronskian_desc = (
        f"Từ hai nghiệm cơ bản độc lập của phương trình thuần nhất:\n"
        f"$$y_1({var}) = {expr_to_latex(y1)}, \\quad y_2({var}) = {expr_to_latex(y2)}$$\n\n"
        f"Tính các đạo hàm cấp một:\n"
        f"$$y_1'({var}) = {expr_to_latex(dy1)}, \\quad y_2'({var}) = {expr_to_latex(dy2)}$$\n\n"
        f"Thiết lập và tính định thức Wronskian:\n"
        f"$${wronskian_eval_latex}$$\n\n"
        f"Vì $W({var}) = {expr_to_latex(w_simp)} \\neq 0$, hệ nghiệm $\\{{y_1, y_2\\}}$ độc lập tuyến tính trên miền xác định."
    )
    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Định thức Wronskian",
            title="Tính định thức Wronskian của hệ nghiệm cơ bản",
            description=wronskian_desc,
            content=ExpressionStepContent(
                expression_before=f"W = y1*y2' - y1'*y2 = {w_raw}",
                expression_after=f"W({var}) = {w_simp}",
                latex_before=matrix_latex,
                latex_after=f"W({var}) = {expr_to_latex(w_simp)}",
            ),
            equation_latex=f"W({var}) = {expr_to_latex(w_simp)}",
        )
    )
    cur_step += 1

    # Step: Particular solution form & Auxiliary condition
    ansatz_desc = (
        f"Giả sử nghiệm riêng của phương trình không thuần nhất có dạng:\n"
        f"$$Y_p({var}) = u_1({var})y_1({var}) + u_2({var})y_2({var}) = "
        f"u_1({var})\\left({expr_to_latex(y1)}\\right) + u_2({var})\\left({expr_to_latex(y2)}\\right)$$\n\n"
        f"trong đó $u_1({var}), u_2({var})$ là các hàm số cần tìm. "
        f"Để đơn giản hóa đạo hàm và không làm xuất hiện đạo hàm cấp hai $u_1'', u_2''$, "
        f"ta áp đặt điều kiện phụ trợ Lagrange:\n"
        f"$$u_1'({var})y_1({var}) + u_2'({var})y_2({var}) = 0$$"
    )
    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Dạng nghiệm riêng Lagrange",
            title="Đề xuất dạng nghiệm riêng biến thiên hằng số",
            description=ansatz_desc,
            content=ExpressionStepContent(
                expression_before="Y_p = C1*y1 + C2*y2",
                expression_after=f"Y_p({var}) = u1({var})*y1 + u2({var})*y2",
                latex_before=r"y_c(t) = C_1 y_1 + C_2 y_2",
                latex_after=f"Y_p({var}) = u_1({var})\\left({expr_to_latex(y1)}\\right) + u_2({var})\\left({expr_to_latex(y2)}\\right)",
            ),
            equation_latex=f"Y_p({var}) = u_1({var})y_1({var}) + u_2({var})y_2({var})",
        )
    )
    cur_step += 1

    # Step: Lagrange Auxiliary System
    f_latex = expr_to_latex(f_expr)
    system_latex = (
        f"\\begin{{cases}} "
        f"u_1'({var})\\left({expr_to_latex(y1)}\\right) + u_2'({var})\\left({expr_to_latex(y2)}\\right) = 0 \\\\ "
        f"u_1'({var})\\left({expr_to_latex(dy1)}\\right) + u_2'({var})\\left({expr_to_latex(dy2)}\\right) = {f_latex} "
        f"\\end{{cases}}"
    )
    system_desc = (
        f"Thay $Y_p$ cùng điều kiện phụ trợ vào phương trình vi phân ban đầu, "
        f"ta thu được hệ phương trình phụ trợ Lagrange xác định $u_1'({var})$ và $u_2'({var})$:\n"
        f"$${system_latex}$$\n\n"
        f"Lưu ý: vế phải phương trình thứ hai là hàm cưỡng bức đã chuẩn hóa $f({var}) = \\frac{{g({var})}}{{a}} = {f_latex}$."
    )
    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Hệ phương trình phụ trợ Lagrange",
            title="Thiết lập hệ phương trình phụ trợ xác định u1' và u2'",
            description=system_desc,
            content=ExpressionStepContent(
                expression_before="u1'*y1 + u2'*y2 = 0, u1'*y1' + u2'*y2' = g/a",
                expression_after=f"u1'*y1 + u2'*y2 = 0, u1'*y1' + u2'*y2' = {f_expr}",
                latex_before=r"\begin{cases} u_1' y_1 + u_2' y_2 = 0 \\ u_1' y_1' + u_2' y_2' = \frac{g(t)}{a} \end{cases}",
                latex_after=system_latex,
            ),
            equation_latex=system_latex,
        )
    )
    cur_step += 1

    # Step: Solving for u1' and u2'
    u1p_latex = expr_to_latex(u1_prime)
    u2p_latex = expr_to_latex(u2_prime)
    cramer_latex = (
        f"u_1'({var}) = -\\frac{{y_2({var})\\,g({var})}}{{a\\,W({var})}} = -\\frac{{\\left({expr_to_latex(y2)}\\right)\\left({expr_to_latex(g_expr)}\\right)}}{{{expr_to_latex(a)}\\left({expr_to_latex(w_simp)}\\right)}} = {u1p_latex}\n\n"
        f"u_2'({var}) = \\frac{{y_1({var})\\,g({var})}}{{a\\,W({var})}} = \\frac{{\\left({expr_to_latex(y1)}\\right)\\left({expr_to_latex(g_expr)}\\right)}}{{{expr_to_latex(a)}\\left({expr_to_latex(w_simp)}\\right)}} = {u2p_latex}"
    )
    deriv_desc = (
        f"Áp dụng quy tắc Cramer cho hệ phương trình phụ trợ Lagrange:\n"
        f"$${cramer_latex}$$"
    )
    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Đạo hàm hàm biến thiên",
            title="Giải hệ xác định biểu thức đạo hàm u1' và u2'",
            description=deriv_desc,
            content=ExpressionStepContent(
                expression_before="u1' = -y2*g/(a*W), u2' = y1*g/(a*W)",
                expression_after=f"u1' = {u1_prime}, u2' = {u2_prime}",
                latex_before=r"u_1' = -\frac{y_2 g}{a W}, \quad u_2' = \frac{y_1 g}{a W}",
                latex_after=f"u_1'({var}) = {u1p_latex}, \\quad u_2'({var}) = {u2p_latex}",
            ),
            equation_latex=f"u_1'({var}) = {u1p_latex}, \\quad u_2'({var}) = {u2p_latex}",
        )
    )
    cur_step += 1

    # Step: Integration to find u1 and u2
    u1_latex = expr_to_latex(u1_sol)
    u2_latex = expr_to_latex(u2_sol)
    if initial_point is not None:
        t0_ltx = expr_to_latex(initial_point)
        int_desc = (
            f"Để giải bài toán Cauchy tại điểm ban đầu ${var}_0 = {t0_ltx}$, "
            f"ta chọn dạng tích phân xác định neo tại điểm ban đầu với biến phụ $s$ "
            f"(nhằm thỏa mãn điều kiện chuẩn tắc $u_1({t0_ltx}) = 0$ và "
            f"$u_2({t0_ltx}) = 0$, dẫn đến $Y_p({t0_ltx}) = 0$ và $Y_p'({t0_ltx}) = 0$):\n\n"
            f"1. Hàm $u_1({var})$:\n"
            f"$$u_1({var}) = -\\int_{{{t0_ltx}}}^{{{var}}} \\frac{{y_2(s)\\,g(s)}}{{a\\,W(s)}}\\,ds = {u1_latex}$$\n\n"
            f"2. Hàm $u_2({var})$:\n"
            f"$$u_2({var}) = \\int_{{{t0_ltx}}}^{{{var}}} \\frac{{y_1(s)\\,g(s)}}{{a\\,W(s)}}\\,ds = {u2_latex}$$"
        )
    elif is_integral_form:
        int_type_desc = (
            "Một hoặc cả hai tích phân không có nguyên hàm biểu diễn dưới dạng hàm sơ cấp hữu hạn. "
            "Ta bảo toàn dạng tích phân xác định chính xác theo nguyên lý toán học:"
        )
        int_desc = (
            f"{int_type_desc}\n\n"
            f"1. Hàm $u_1({var})$:\n"
            f"$$u_1({var}) = \\int u_1'({var})\\,d{var} = \\int \\left({u1p_latex}\\right)\\,d{var} = {u1_latex}$$\n\n"
            f"2. Hàm $u_2({var})$:\n"
            f"$$u_2({var}) = \\int u_2'({var})\\,d{var} = \\int \\left({u2p_latex}\\right)\\,d{var} = {u2_latex}$$"
        )
    else:
        int_type_desc = "Tích phân các đạo hàm để tìm $u_1({var})$ và $u_2({var})$ (chọn hằng số tích phân bằng 0):"
        int_desc = (
            f"{int_type_desc}\n\n"
            f"1. Hàm $u_1({var})$:\n"
            f"$$u_1({var}) = \\int u_1'({var})\\,d{var} = \\int \\left({u1p_latex}\\right)\\,d{var} = {u1_latex}$$\n\n"
            f"2. Hàm $u_2({var})$:\n"
            f"$$u_2({var}) = \\int u_2'({var})\\,d{var} = \\int \\left({u2p_latex}\\right)\\,d{var} = {u2_latex}$$"
        )

    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Tích phân hàm biến thiên",
            title="Tích phân xác định các hàm u1 và u2",
            description=int_desc,
            content=ExpressionStepContent(
                expression_before=f"u1 = Integral({u1_prime}, {var}), u2 = Integral({u2_prime}, {var})",
                expression_after=f"u1 = {u1_sol}, u2 = {u2_sol}",
                latex_before=f"u_1 = \\int \\left({u1p_latex}\\right) d{var}, \\quad u_2 = \\int \\left({u2p_latex}\\right) d{var}",
                latex_after=f"u_1({var}) = {u1_latex}, \\quad u_2({var}) = {u2_latex}",
            ),
            equation_latex=f"u_1({var}) = {u1_latex}, \\quad u_2({var}) = {u2_latex}",
        )
    )
    cur_step += 1

    # Step: Particular solution construction
    yp_latex = expr_to_latex(yp_sol)
    yp_desc = (
        f"Thay $u_1({var})$ và $u_2({var})$ vào dạng nghiệm thử ban đầu thu được nghiệm riêng $Y_p({var})$:\n"
        f"$$Y_p({var}) = u_1({var})y_1({var}) + u_2({var})y_2({var}) = {yp_latex}$$\n\n"
        f"Biểu thức nghiệm riêng này thỏa mãn đồng nhất phương trình vi phân $a Y_p'' + b Y_p' + c Y_p = g({var})$."
    )
    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Nghiệm riêng biến thiên hằng số",
            title="Xác định nghiệm riêng Y_p(t) theo phương pháp Lagrange",
            description=yp_desc,
            content=ExpressionStepContent(
                expression_before="Y_p = u1*y1 + u2*y2",
                expression_after=f"Y_p({var}) = {yp_sol}",
                latex_before=f"Y_p({var}) = u_1({var})y_1({var}) + u_2({var})y_2({var})",
                latex_after=f"Y_p({var}) = {yp_latex}",
            ),
            equation_latex=f"Y_p({var}) = {yp_latex}",
        )
    )

    return VariationOfParametersResult(
        is_supported=True,
        particular_solution=yp_sol,
        u1_expr=u1_sol,
        u2_expr=u2_sol,
        u1_prime=u1_prime,
        u2_prime=u2_prime,
        wronskian=w_simp,
        is_integral_form=is_integral_form,
        steps=tuple(steps),
        domain_restrictions=tuple(all_restrictions),
        domain_interval=domain_interval,
        initial_point=initial_point,
    )

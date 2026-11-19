"""Homogeneous Linear Second-Order ODE Solver with Constant Coefficients & Initial Value Problems."""

from __future__ import annotations

import time
import sympy as sp

from math_app.application.dtos import (
    ProblemRequest,
    SolutionResponse,
    SolutionStep,
    VerificationResult,
)
from math_app.application.ports.solver import Solver
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.input.ode_parser import ParsedSecondOrderODE, parse_second_order_ode_input
from math_app.rendering.latex.formatter import expr_to_latex, format_quadratic_root_latex
from math_app.verification.calculus.ode_verifier import ODEVerifier


def _format_linear_comb(k1: sp.Expr, k2: sp.Expr, k1_ltx: str, k2_ltx: str) -> str:
    """Format k1*C1 + k2*C2 in LaTeX, suppressing zero terms and preserving clean signs."""
    if k1 == 0 and k2 == 0:
        return "0"
    if k1 == 0:
        if k2 == 1:
            return "C_2"
        if k2 == -1:
            return "-C_2"
        if "+" in k2_ltx or ("-" in k2_ltx and not k2_ltx.startswith("-")):
            return f"\\left({k2_ltx}\\right) C_2"
        return f"{k2_ltx}\\,C_2"
    if k2 == 0:
        if k1 == 1:
            return "C_1"
        if k1 == -1:
            return "-C_1"
        if "+" in k1_ltx or ("-" in k1_ltx and not k1_ltx.startswith("-")):
            return f"\\left({k1_ltx}\\right) C_1"
        return f"{k1_ltx}\\,C_1"

    # Both non-zero
    if k1 == 1:
        term1 = "C_1"
    elif k1 == -1:
        term1 = "-C_1"
    elif "+" in k1_ltx or ("-" in k1_ltx and not k1_ltx.startswith("-")):
        term1 = f"\\left({k1_ltx}\\right) C_1"
    elif k1_ltx.startswith("-") and ("+" in k1_ltx or r"\sqrt" in k1_ltx):
        term1 = f"\\left({k1_ltx}\\right) C_1"
    else:
        term1 = f"{k1_ltx}\\,C_1"

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


def _format_subst_term(coeff: sp.Expr, coeff_ltx: str, fund_ltx: str) -> str:
    """Format coeff * y_fund in LaTeX for substitution step."""
    if coeff == 0:
        return f"0\\,{fund_ltx}"
    if coeff == 1:
        return fund_ltx
    if coeff == -1:
        return f"-{fund_ltx}"
    if "+" in coeff_ltx or ("-" in coeff_ltx and not coeff_ltx.startswith("-")):
        return f"\\left({coeff_ltx}\\right) {fund_ltx}"
    if coeff_ltx.startswith("-") and ("+" in coeff_ltx or r"\sqrt" in coeff_ltx):
        return f"\\left({coeff_ltx}\\right) {fund_ltx}"
    if coeff_ltx.startswith("-"):
        return f"\\left({coeff_ltx}\\right) {fund_ltx}"
    return f"{coeff_ltx}\\,{fund_ltx}"


class ODESecondOrderConstantCoeffSolver(Solver):
    """Solver for homogeneous second-order linear ODEs with constant coefficients:

    a*y'' + b*y' + c*y = 0,  a != 0,
    with optional Cauchy initial conditions y(t0) = y0, y'(t0) = v0.
    """

    def __init__(self, verifier: ODEVerifier | None = None) -> None:
        self.verifier = verifier or ODEVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type in (
            ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
            ProblemType.ODE_SECOND_ORDER_IVP,
            ProblemType.SOLVE_EQUATION,
        )

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        t0_start = time.perf_counter()
        raw = request.raw_input.strip()
        if not raw:
            raise InvalidInputError("Phương trình vi phân không được để trống (Equation cannot be empty).")

        parsed: ParsedSecondOrderODE = parse_second_order_ode_input(
            raw,
            target_variable=request.target_variable,
            parameters=dict(request.parameters),
        )

        elapsed = (time.perf_counter() - t0_start) * 1000.0

        # Validate second order
        if sp.simplify(parsed.a_coeff) == 0:
            raise InvalidInputError("Hệ số của y'' bằng 0; không phải phương trình vi phân cấp 2 (a != 0).")

        # Validate Cauchy IVP conditions based on problem mode
        has_y_ic = parsed.initial_condition is not None
        has_yp_ic = parsed.initial_derivative is not None

        if request.problem_type == ProblemType.ODE_SECOND_ORDER_IVP:
            if not has_y_ic and not has_yp_ic:
                raise InvalidInputError(
                    "Bài toán Cauchy (IVP) cấp hai yêu cầu cung cấp đầy đủ hai điều kiện ban đầu: "
                    "y(t0) = y0 và y'(t0) = v0."
                )
            if not has_y_ic or not has_yp_ic:
                raise InvalidInputError(
                    "Bài toán Cauchy (IVP) cấp hai thiếu điều kiện ban đầu. "
                    "Cần cung cấp đầy đủ cả hai điều kiện: y(t0) = y0 và y'(t0) = v0 để xác định nghiệm duy nhất."
                )
        else:
            if (has_y_ic and not has_yp_ic) or (not has_y_ic and has_yp_ic):
                raise InvalidInputError(
                    "Phương trình vi phân cấp hai nhận được điều kiện ban đầu không hoàn chỉnh. "
                    "Vui lòng cung cấp đầy đủ cả hai điều kiện: y(t0) = y0 và y'(t0) = v0 để giải bài toán Cauchy, "
                    "hoặc không cung cấp điều kiện nào để tìm nghiệm tổng quát."
                )

        if has_y_ic and has_yp_ic:
            t0_cand, y0_cand = parsed.initial_condition  # type: ignore[misc]
            t1_cand, v0_cand = parsed.initial_derivative  # type: ignore[misc]
            if sp.simplify(t0_cand - t1_cand) != 0:
                raise InvalidInputError(
                    f"Bài toán Cauchy (IVP) cấp hai yêu cầu hai điều kiện tại cùng một điểm ban đầu t0: "
                    f"y({t0_cand}) và y'({t1_cand}) không cùng điểm khởi đầu."
                )
            for val_name, val_expr in (("t0", t0_cand), ("y0", y0_cand), ("v0", v0_cand)):
                if val_expr.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or val_expr.has(sp.I):
                    raise InvalidInputError(
                        f"Giá trị điều kiện ban đầu {val_name} = {val_expr} không phải là số thực hữu hạn "
                        "(Finite real numbers required for Cauchy initial conditions)."
                    )

        # Validate homogeneity
        if not parsed.is_homogeneous:
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="homogeneity_check",
                    details="Phương trình không thuần nhất (Nonhomogeneous ODE).",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=(
                    "Phương trình vi phân cấp 2 không thuần nhất chưa được hỗ trợ trong phiên bản này "
                    "(Nonhomogeneous second-order ODEs are unsupported in this milestone).",
                ),
                execution_time_ms=elapsed,
            )

        # Validate constant coefficients
        if not parsed.is_constant_coeff:
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="constant_coefficients_check",
                    details="Phương trình có hệ số phụ thuộc biến số (Variable-coefficient ODE).",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=(
                    "Phương trình này có hệ số phụ thuộc biến số. Vui lòng sử dụng phương pháp Hạ bậc (Reduction of Order) "
                    "nếu đã biết một nghiệm cơ bản (Variable-coefficient ODEs require Reduction of Order).",
                ),
                execution_time_ms=elapsed,
            )

        var = parsed.independent_var
        a = parsed.a_coeff
        b = parsed.b_coeff
        c = parsed.c_coeff

        steps: list[SolutionStep] = []
        step_num = 1

        # -------------------------------------------------------------------------
        # Step 1: Identification & Characteristic Equation
        # a*r^2 + b*r + c = 0
        # -------------------------------------------------------------------------
        r_sym = sp.Symbol("r")
        char_poly = a * r_sym**2 + b * r_sym + c
        delta = sp.simplify(b**2 - 4 * a * c)

        # Format standard linear ODE LHS cleanly
        b_term = f" + {expr_to_latex(b)}\\,y'" if b > 0 else (f" - {expr_to_latex(-b)}\\,y'" if b < 0 else "")
        c_term = f" + {expr_to_latex(c)}\\,y" if c > 0 else (f" - {expr_to_latex(-c)}\\,y" if c < 0 else "")
        ode_lhs_latex = f"{expr_to_latex(a)}\\,y''{b_term}{c_term}"

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Phương trình đặc trưng",
                title="Thiết lập phương trình đặc trưng",
                description=(
                    f"Xét phương trình vi phân tuyến tính thuần nhất hệ số hằng cấp hai: "
                    f"${ode_lhs_latex} = 0$. "
                    f"Giả thiết nghiệm có dạng $y = e^{{rt}}$, ta xây dựng phương trình đặc trưng: $ar^2 + br + c = 0$."
                ),
                content=ExpressionStepContent(
                    expression_before=f"{a}*y'' + {b}*y' + {c}*y = 0",
                    expression_after=f"{char_poly} = 0",
                    latex_before=f"{ode_lhs_latex} = 0",
                    latex_after=f"{expr_to_latex(char_poly)} = 0",
                ),
                equation_latex=f"{expr_to_latex(char_poly)} = 0",
            )
        )
        step_num += 1

        # -------------------------------------------------------------------------
        # Step 2: Discriminant Delta = b^2 - 4ac
        # -------------------------------------------------------------------------
        delta_str = f"Delta = ({b})^2 - 4*({a})*({c}) = {delta}"
        delta_latex = f"\\Delta = b^2 - 4ac = ({expr_to_latex(b)})^2 - 4({expr_to_latex(a)})({expr_to_latex(c)}) = {expr_to_latex(delta)}"

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Biệt thức Delta",
                title="Tính biệt thức Delta của phương trình đặc trưng",
                description=(
                    f"Tính biệt thức $\\Delta = b^2 - 4ac = ({expr_to_latex(b)})^2 - 4({expr_to_latex(a)})({expr_to_latex(c)}) = {expr_to_latex(delta)}$ "
                    "để xác định cấu trúc nghiệm của phương trình đặc trưng."
                ),
                content=ExpressionStepContent(
                    expression_before="ar^2 + br + c = 0",
                    expression_after=delta_str,
                    latex_before=f"{expr_to_latex(char_poly)} = 0",
                    latex_after=delta_latex,
                ),
                equation_latex=delta_latex,
            )
        )
        step_num += 1

        # Check if delta sign can be evaluated
        c1_sym = sp.Symbol("C1")
        c2_sym = sp.Symbol("C2")

        # Handle symbolic discriminant with undetermined sign
        if delta.is_number is False and not delta.is_real:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="undetermined_delta_sign",
                    details=f"Không xác định được dấu của biệt thức Delta: {delta}.",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=(
                    f"Biệt thức Delta = {delta} chứa tham số ký hiệu chưa xác định được dấu. "
                    "Cần bổ sung giả thiết về dấu của tham số (Please provide parameter assumptions for symbolic discriminant).",
                ),
                execution_time_ms=elapsed,
            )

        # -------------------------------------------------------------------------
        # Cases based on Delta
        # -------------------------------------------------------------------------
        y1_fund: sp.Expr
        y2_fund: sp.Expr
        gen_sol: sp.Expr
        r1_ltx: str = ""
        r2_ltx: str = ""

        if delta > 0:
            # Case 1: Two distinct real roots
            sqrt_delta = sp.sqrt(delta)
            r1 = sp.simplify((-b + sqrt_delta) / (2 * a))
            r2 = sp.simplify((-b - sqrt_delta) / (2 * a))

            r1_ltx = format_quadratic_root_latex(a, b, delta, +1)
            r2_ltx = format_quadratic_root_latex(a, b, delta, -1)

            y1_fund = sp.exp(r1 * var)
            y2_fund = sp.exp(r2 * var)
            gen_sol = c1_sym * y1_fund + c2_sym * y2_fund

            # Step 3: Real roots calculation
            roots_latex = (
                f"r_1 = \\frac{{-b + \\sqrt{{\\Delta}}}}{{2a}} = {r1_ltx}, \\quad "
                f"r_2 = \\frac{{-b - \\sqrt{{\\Delta}}}}{{2a}} = {r2_ltx}"
            )
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Hai nghiệm thực phân biệt",
                    title="Xác định hai nghiệm thực phân biệt (Delta > 0)",
                    description=(
                        f"Vì $\\Delta = {expr_to_latex(delta)} > 0$, phương trình đặc trưng có hai nghiệm thực phân biệt: "
                        f"$r_1 = \\frac{{-b + \\sqrt{{\\Delta}}}}{{2a}} = {r1_ltx}$ và "
                        f"$r_2 = \\frac{{-b - \\sqrt{{\\Delta}}}}{{2a}} = {r2_ltx}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"Delta = {delta} > 0",
                        expression_after=f"r1 = {r1}, r2 = {r2}",
                        latex_before=f"\\Delta = {expr_to_latex(delta)} > 0",
                        latex_after=roots_latex,
                    ),
                    equation_latex=roots_latex,
                )
            )
            step_num += 1

            # Step 4: Fundamental solutions & General solution
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Hệ nghiệm cơ bản",
                    title="Xây dựng hệ nghiệm cơ bản và nghiệm tổng quát",
                    description=(
                        f"Hai nghiệm cơ bản độc lập tuyến tính tương ứng là $y_1({var}) = e^{{r_1 {var}}} = {expr_to_latex(y1_fund)}$ "
                        f"và $y_2({var}) = e^{{r_2 {var}}} = {expr_to_latex(y2_fund)}$. "
                        f"Nghiệm tổng quát là tổ hợp tuyến tính: $y({var}) = C_1 y_1({var}) + C_2 y_2({var})$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"y1 = exp({r1}*{var}), y2 = exp({r2}*{var})",
                        expression_after=f"y({var}) = {gen_sol}",
                        latex_before=f"y_1({var}) = {expr_to_latex(y1_fund)}, \\quad y_2({var}) = {expr_to_latex(y2_fund)}",
                        latex_after=f"y({var}) = {expr_to_latex(gen_sol)}",
                    ),
                    equation_latex=f"y({var}) = {expr_to_latex(gen_sol)}",
                )
            )
            step_num += 1

        elif delta < 0:
            # Case 2: Complex conjugate roots r = alpha +- i*beta
            alpha = sp.simplify(-b / (2 * a))
            beta = sp.simplify(sp.sqrt(-delta) / (2 * sp.Abs(a)))

            if alpha == 0:
                y1_fund = sp.cos(beta * var)
                y2_fund = sp.sin(beta * var)
                gen_sol = c1_sym * y1_fund + c2_sym * y2_fund
            else:
                y1_fund = sp.exp(alpha * var) * sp.cos(beta * var)
                y2_fund = sp.exp(alpha * var) * sp.sin(beta * var)
                gen_sol = sp.exp(alpha * var) * (c1_sym * sp.cos(beta * var) + c2_sym * sp.sin(beta * var))

            # Step 3: Complex roots explanation
            complex_roots_latex = (
                f"r_{{1,2}} = \\alpha \\pm i\\beta = {expr_to_latex(alpha)} \\pm i\\left({expr_to_latex(beta)}\\right)"
            )
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Nghiệm phức liên hợp",
                    title="Xác định nghiệm phức liên hợp (Delta < 0)",
                    description=(
                        f"Vì $\\Delta = {expr_to_latex(delta)} < 0$, phương trình đặc trưng có cặp nghiệm phức liên hợp: "
                        f"$\\alpha = -\\frac{{b}}{{2a}} = {expr_to_latex(alpha)}$, "
                        f"$\\beta = \\frac{{\\sqrt{{-\\Delta}}}}{{2|a|}} = {expr_to_latex(beta)}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"Delta = {delta} < 0",
                        expression_after=f"r = {alpha} +- {beta}*i",
                        latex_before=f"\\Delta = {expr_to_latex(delta)} < 0",
                        latex_after=complex_roots_latex,
                    ),
                    equation_latex=complex_roots_latex,
                )
            )
            step_num += 1

            # Step 4: Real-valued fundamental solutions via Euler's formula
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Hệ nghiệm cơ bản",
                    title="Biến đổi qua công thức Euler sang hệ nghiệm thực",
                    description=(
                        f"Theo công thức Euler: $e^{{(\\alpha \\pm i\\beta){var}}} = e^{{\\alpha {var}}}(\\cos(\\beta {var}) \\pm i\\sin(\\beta {var}))$. "
                        f"Lấy phần thực và phần ảo, ta nhận được hệ nghiệm thực cơ bản độc lập: "
                        f"$y_1({var}) = {expr_to_latex(y1_fund)}$ và $y_2({var}) = {expr_to_latex(y2_fund)}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"y_complex = exp(({alpha} +- i*{beta})*{var})",
                        expression_after=f"y({var}) = {gen_sol}",
                        latex_before=f"y_{{1}}({var}) = {expr_to_latex(y1_fund)}, \\quad y_{{2}}({var}) = {expr_to_latex(y2_fund)}",
                        latex_after=f"y({var}) = {expr_to_latex(gen_sol)}",
                    ),
                    equation_latex=f"y({var}) = {expr_to_latex(gen_sol)}",
                )
            )
            step_num += 1

        else:
            # Case 3: Repeated real root Delta == 0
            r_rep = sp.simplify(-b / (2 * a))
            if r_rep == 0:
                y1_fund = sp.Integer(1)
                y2_fund = var
                gen_sol = c1_sym + c2_sym * var
            else:
                y1_fund = sp.exp(r_rep * var)
                y2_fund = var * sp.exp(r_rep * var)
                gen_sol = (c1_sym + c2_sym * var) * sp.exp(r_rep * var)

            # Step 3: Repeated root
            rep_root_latex = f"r = -\\frac{{b}}{{2a}} = {expr_to_latex(r_rep)}"
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Nghiệm kép thực",
                    title="Xác định nghiệm kép thực (Delta = 0)",
                    description=(
                        f"Vì $\\Delta = 0$, phương trình đặc trưng có một nghiệm kép: $r = -\\frac{{b}}{{2a}} = {expr_to_latex(r_rep)}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before="Delta = 0",
                        expression_after=f"r = {r_rep}",
                        latex_before=r"\Delta = 0",
                        latex_after=rep_root_latex,
                    ),
                    equation_latex=rep_root_latex,
                )
            )
            step_num += 1

            # Step 4: General solution with factor t
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Hệ nghiệm cơ bản",
                    title="Xây dựng hệ nghiệm cơ bản với thừa số nhân t",
                    description=(
                        f"Do $r$ là nghiệm kép, hàm $y_1({var}) = {expr_to_latex(y1_fund)}$ chỉ cung cấp một nghiệm độc lập. "
                        f"Theo phương pháp hạ bậc nghiệm, nghiệm cơ bản thứ hai độc lập tuyến tính là $y_2({var}) = {var}\\,{expr_to_latex(y1_fund)}$. "
                        f"Nghiệm tổng quát có dạng: $y({var}) = (C_1 + C_2 {var})e^{{{expr_to_latex(r_rep)} {var}}}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"y1 = {y1_fund}",
                        expression_after=f"y({var}) = {gen_sol}",
                        latex_before=f"y_1({var}) = {expr_to_latex(y1_fund)}, \\quad y_2({var}) = {expr_to_latex(y2_fund)}",
                        latex_after=f"y({var}) = {expr_to_latex(gen_sol)}",
                    ),
                    equation_latex=f"y({var}) = {expr_to_latex(gen_sol)}",
                )
            )
            step_num += 1

        # -------------------------------------------------------------------------
        # Initial Value Problem (IVP) Handling
        # -------------------------------------------------------------------------
        final_sol = gen_sol
        has_ivp = bool(parsed.initial_condition is not None and parsed.initial_derivative is not None)

        if has_ivp:
            t0, y0 = parsed.initial_condition  # type: ignore[misc]
            _, v0 = parsed.initial_derivative  # type: ignore[misc]

            # Differentiate general solution
            dy1_fund = sp.diff(y1_fund, var)
            dy2_fund = sp.diff(y2_fund, var)
            d_gen_sol = c1_sym * dy1_fund + c2_sym * dy2_fund

            # Step 5: Derivative of general solution
            deriv_eq_latex = f"y'({var}) = {expr_to_latex(d_gen_sol)}"
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Đạo hàm nghiệm tổng quát",
                    title="Tính đạo hàm cấp một của nghiệm tổng quát",
                    description=(
                        f"Tính đạo hàm cấp một của nghiệm tổng quát theo biến ${var}$:\n"
                        f"$$y'({var}) = \\frac{{d}}{{d{var}}}[y({var})] = "
                        f"C_1 \\frac{{d}}{{d{var}}}[{expr_to_latex(y1_fund)}] + "
                        f"C_2 \\frac{{d}}{{d{var}}}[{expr_to_latex(y2_fund)}] = {expr_to_latex(d_gen_sol)}$$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"y({var}) = {gen_sol}",
                        expression_after=f"y'({var}) = {d_gen_sol}",
                        latex_before=f"y({var}) = {expr_to_latex(gen_sol)}",
                        latex_after=deriv_eq_latex,
                    ),
                    equation_latex=deriv_eq_latex,
                )
            )
            step_num += 1

            # Evaluate fundamental solutions and their derivatives at t0
            c11 = sp.simplify(y1_fund.subs(var, t0))
            c12 = sp.simplify(y2_fund.subs(var, t0))
            c21 = sp.simplify(dy1_fund.subs(var, t0))
            c22 = sp.simplify(dy2_fund.subs(var, t0))

            # Format coefficients cleanly, preserving radicals like \sqrt{33} when present
            c11_ltx = expr_to_latex(c11)
            c12_ltx = expr_to_latex(c12)
            c21_ltx = r1_ltx if (delta > 0 and t0 == 0 and r1_ltx) else expr_to_latex(c21)
            c22_ltx = r2_ltx if (delta > 0 and t0 == 0 and r2_ltx) else expr_to_latex(c22)

            # Equation LHS formatting suppressing zero coefficients
            eq1_lhs_latex = _format_linear_comb(c11, c12, c11_ltx, c12_ltx)
            eq2_lhs_latex = _format_linear_comb(c21, c22, c21_ltx, c22_ltx)

            matrix_system_latex = (
                f"\\begin{{pmatrix}} {c11_ltx} & {c12_ltx} \\\\ {c21_ltx} & {c22_ltx} \\end{{pmatrix}} "
                f"\\begin{{pmatrix}} C_1 \\\\ C_2 \\end{{pmatrix}} = "
                f"\\begin{{pmatrix}} {expr_to_latex(y0)} \\\\ {expr_to_latex(v0)} \\end{{pmatrix}}"
            )
            system_cases_latex = (
                f"\\begin{{cases}} "
                f"{eq1_lhs_latex} = {expr_to_latex(y0)} \\\\ "
                f"{eq2_lhs_latex} = {expr_to_latex(v0)} "
                f"\\end{{cases}}"
            )

            # Step 6: Cauchy system derivation (Concise default presentation)
            step6_desc = (
                f"Để xác định hai hằng số tích phân $C_1$ và $C_2$, ta áp dụng hệ điều kiện ban đầu Cauchy vào nghiệm tổng quát và đạo hàm cấp một:\n\n"
                f"1. Nghiệm tổng quát và đạo hàm cấp một:\n"
                f"- Nghiệm tổng quát: $y({var}) = C_1 y_1({var}) + C_2 y_2({var})$\n"
                f"- Đạo hàm cấp một: $y'({var}) = C_1 y_1'({var}) + C_2 y_2'({var})$\n\n"
                f"2. Áp dụng điều kiện ban đầu:\n"
                f"- Điều kiện hàm số tại ${var} = {expr_to_latex(t0)}$: $y({expr_to_latex(t0)}) = {expr_to_latex(y0)}$ cho phương trình:\n"
                f"$${eq1_lhs_latex} = {expr_to_latex(y0)}$$\n"
                f"- Điều kiện đạo hàm tại ${var} = {expr_to_latex(t0)}$: $y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}$ cho phương trình:\n"
                f"$${eq2_lhs_latex} = {expr_to_latex(v0)}$$\n\n"
                f"3. Hệ phương trình thu được xác định $C_1, C_2$:\n"
                f"$${system_cases_latex}$$"
            )

            sub_step6_1 = SolutionStep(
                step_number=1,
                rule_name="Thay điều kiện y(t0) = y0",
                title=f"Thay điều kiện ban đầu y({t0}) = {y0} vào nghiệm tổng quát",
                description=(
                    f"Xuất phát từ nghiệm tổng quát $y({var}) = C_1 y_1({var}) + C_2 y_2({var})$, thay ${var} = {expr_to_latex(t0)}$:\n"
                    f"$$C_1 y_1({expr_to_latex(t0)}) + C_2 y_2({expr_to_latex(t0)}) = {expr_to_latex(y0)}$$\n"
                    f"Tính giá trị $y_1({expr_to_latex(t0)}) = {c11_ltx}, \\, y_2({expr_to_latex(t0)}) = {c12_ltx}$, ta được:\n"
                    f"$${eq1_lhs_latex} = {expr_to_latex(y0)}$$"
                ),
                content=ExpressionStepContent(
                    expression_before=f"y({t0}) = {y0}",
                    expression_after=f"{c11}*C1 + {c12}*C2 = {y0}",
                    latex_before=f"y({expr_to_latex(t0)}) = {expr_to_latex(y0)}",
                    latex_after=f"{eq1_lhs_latex} = {expr_to_latex(y0)}",
                ),
                equation_latex=f"{eq1_lhs_latex} = {expr_to_latex(y0)}",
            )
            sub_step6_2 = SolutionStep(
                step_number=2,
                rule_name="Thay điều kiện y'(t0) = v0",
                title=f"Thay điều kiện đạo hàm y'({t0}) = {v0} vào đạo hàm nghiệm tổng quát",
                description=(
                    f"Xuất phát từ đạo hàm cấp một $y'({var}) = C_1 y_1'({var}) + C_2 y_2'({var})$, thay ${var} = {expr_to_latex(t0)}$:\n"
                    f"$$C_1 y_1'({expr_to_latex(t0)}) + C_2 y_2'({expr_to_latex(t0)}) = {expr_to_latex(v0)}$$\n"
                    f"Tính giá trị $y_1'({expr_to_latex(t0)}) = {c21_ltx}, \\, y_2'({expr_to_latex(t0)}) = {c22_ltx}$, ta được:\n"
                    f"$${eq2_lhs_latex} = {expr_to_latex(v0)}$$"
                ),
                content=ExpressionStepContent(
                    expression_before=f"y'({t0}) = {v0}",
                    expression_after=f"{c21}*C1 + {c22}*C2 = {v0}",
                    latex_before=f"y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}",
                    latex_after=f"{eq2_lhs_latex} = {expr_to_latex(v0)}",
                ),
                equation_latex=f"{eq2_lhs_latex} = {expr_to_latex(v0)}",
            )
            sub_step6_3 = SolutionStep(
                step_number=3,
                rule_name="Hệ ma trận 2x2",
                title="Biểu diễn hệ phương trình dạng ma trận 2x2",
                description=(
                    f"Biểu diễn hệ phương trình trên dưới dạng phương trình ma trận $A \\mathbf{{C}} = \\mathbf{{Y}}_0$:\n"
                    f"$${matrix_system_latex}$$\n"
                    f"với ma trận hệ số và vectơ vế phải tương ứng chính xác với hai phương trình thu được."
                ),
                content=ExpressionStepContent(
                    expression_before=f"{c11}*C1 + {c12}*C2 = {y0}, {c21}*C1 + {c22}*C2 = {v0}",
                    expression_after=f"[{c11}, {c12}; {c21}, {c22}] * [C1; C2] = [{y0}; {v0}]",
                    latex_before=f"{eq1_lhs_latex} = {expr_to_latex(y0)}, \\quad {eq2_lhs_latex} = {expr_to_latex(v0)}",
                    latex_after=matrix_system_latex,
                ),
                equation_latex=matrix_system_latex,
            )

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Áp dụng điều kiện ban đầu",
                    title="Thiết lập hệ phương trình xác định hằng số C1, C2",
                    description=step6_desc,
                    content=ExpressionStepContent(
                        expression_before=f"y({t0}) = {y0}, y'({t0}) = {v0}",
                        expression_after=f"{c11}*C1 + {c12}*C2 = {y0}, {c21}*C1 + {c22}*C2 = {v0}",
                        latex_before=f"y({expr_to_latex(t0)}) = {expr_to_latex(y0)}, \\quad y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}",
                        latex_after=system_cases_latex,
                    ),
                    equation_latex=system_cases_latex,
                    substeps=(sub_step6_1, sub_step6_2, sub_step6_3),
                )
            )
            step_num += 1

            # Step 7: Solve linear system and determine particular solution
            step7_substeps: list[SolutionStep] = []

            # Solve system for C1, C2
            sys_eqs = [sp.Eq(c11 * c1_sym + c12 * c2_sym, y0), sp.Eq(c21 * c1_sym + c22 * c2_sym, v0)]
            sol_constants = sp.solve(sys_eqs, [c1_sym, c2_sym])
            if not (sol_constants and c1_sym in sol_constants and c2_sym in sol_constants):
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="singular_cauchy_system_check",
                        details="Hệ phương trình xác định hằng số Cauchy suy biến hoặc không có nghiệm duy nhất.",
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=("Hệ phương trình điều kiện ban đầu không xác định được duy nhất các hằng số tích phân.",),
                    execution_time_ms=(time.perf_counter() - t0_start) * 1000.0,
                )

            val_c1 = sp.simplify(sol_constants[c1_sym])
            val_c2 = sp.simplify(sol_constants[c2_sym])

            val_c1_ltx = expr_to_latex(val_c1)
            val_c2_ltx = expr_to_latex(val_c2)
            c_sol_latex = f"C_1 = {val_c1_ltx}, \\quad C_2 = {val_c2_ltx}"

            particular_sol = sp.simplify(gen_sol.subs([(c1_sym, val_c1), (c2_sym, val_c2)]))
            final_sol = particular_sol

            t1_subst = _format_subst_term(val_c1, val_c1_ltx, expr_to_latex(y1_fund))
            t2_subst = _format_subst_term(val_c2, val_c2_ltx, expr_to_latex(y2_fund))
            subst_combined = f"{t1_subst} + {t2_subst}"

            factored_sol = sp.factor(particular_sol)
            show_factored = bool(sp.simplify(factored_sol - particular_sol) == 0 and str(factored_sol) != str(particular_sol))

            # Adaptive substeps based on system structure
            if c12 == 0 and c21 == 0:
                # Decoupled system
                step7_substeps.append(
                    SolutionStep(
                        step_number=1,
                        rule_name="Giải tìm C1",
                        title="Xác định hằng số C1 từ phương trình thứ nhất",
                        description=f"Từ phương trình (1): ${eq1_lhs_latex} = {expr_to_latex(y0)}$, suy ra:\n$$C_1 = {val_c1_ltx}$$",
                        content=ExpressionStepContent(
                            expression_before=f"{c11}*C1 = {y0}",
                            expression_after=f"C1 = {val_c1}",
                            latex_before=f"{eq1_lhs_latex} = {expr_to_latex(y0)}",
                            latex_after=f"C_1 = {val_c1_ltx}",
                        ),
                        equation_latex=f"C_1 = {val_c1_ltx}",
                    )
                )
                step7_substeps.append(
                    SolutionStep(
                        step_number=2,
                        rule_name="Giải tìm C2",
                        title="Xác định hằng số C2 từ phương trình thứ hai",
                        description=f"Từ phương trình (2): ${eq2_lhs_latex} = {expr_to_latex(v0)}$, suy ra:\n$$C_2 = {val_c2_ltx}$$",
                        content=ExpressionStepContent(
                            expression_before=f"{c22}*C2 = {v0}",
                            expression_after=f"C2 = {val_c2}",
                            latex_before=f"{eq2_lhs_latex} = {expr_to_latex(v0)}",
                            latex_after=f"C_2 = {val_c2_ltx}",
                        ),
                        equation_latex=f"C_2 = {val_c2_ltx}",
                    )
                )
                step7_substeps.append(
                    SolutionStep(
                        step_number=3,
                        rule_name="Xác định nghiệm riêng",
                        title="Thay các hằng số vào nghiệm tổng quát và rút gọn",
                        description=(
                            f"Thay $C_1 = {val_c1_ltx}$ và $C_2 = {val_c2_ltx}$ vào nghiệm tổng quát:\n"
                            f"$$\\begin{{aligned}} y({var}) &= {subst_combined} \\\\ &= {expr_to_latex(particular_sol)} \\end{{aligned}}$$"
                            + (f"\n\nDạng thu gọn tương đương (đặt nhân tử chung):\n$$y({var}) = {expr_to_latex(factored_sol)}$$" if show_factored else "")
                        ),
                        content=ExpressionStepContent(
                            expression_before=c_sol_latex,
                            expression_after=f"y({var}) = {particular_sol}",
                            latex_before=c_sol_latex,
                            latex_after=f"y({var}) = {expr_to_latex(particular_sol)}",
                        ),
                        equation_latex=f"y({var}) = {expr_to_latex(particular_sol)}",
                    )
                )
            elif c12 == 0:
                # Triangular system (Eq 1 gives C1)
                step7_substeps.append(
                    SolutionStep(
                        step_number=1,
                        rule_name="Giải tìm C1",
                        title="Xác định hằng số C1 từ phương trình thứ nhất",
                        description=f"Từ phương trình (1): ${eq1_lhs_latex} = {expr_to_latex(y0)}$, suy ra:\n$$C_1 = {val_c1_ltx}$$",
                        content=ExpressionStepContent(
                            expression_before=f"{c11}*C1 = {y0}",
                            expression_after=f"C1 = {val_c1}",
                            latex_before=f"{eq1_lhs_latex} = {expr_to_latex(y0)}",
                            latex_after=f"C_1 = {val_c1_ltx}",
                        ),
                        equation_latex=f"C_1 = {val_c1_ltx}",
                    )
                )
                step7_substeps.append(
                    SolutionStep(
                        step_number=2,
                        rule_name="Thế C1 tìm C2",
                        title="Thế C1 vào phương trình thứ hai để tìm C2",
                        description=(
                            f"Thay $C_1 = {val_c1_ltx}$ vào phương trình (2): ${eq2_lhs_latex} = {expr_to_latex(v0)}$:\n"
                            f"$$\\left({c21_ltx}\\right)\\left({val_c1_ltx}\\right) + \\left({c22_ltx}\\right) C_2 = {expr_to_latex(v0)} \\implies C_2 = {val_c2_ltx}$$"
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"{c21}*({val_c1}) + {c22}*C2 = {v0}",
                            expression_after=f"C2 = {val_c2}",
                            latex_before=f"{eq2_lhs_latex} = {expr_to_latex(v0)}",
                            latex_after=f"C_2 = {val_c2_ltx}",
                        ),
                        equation_latex=f"C_2 = {val_c2_ltx}",
                    )
                )
                step7_substeps.append(
                    SolutionStep(
                        step_number=3,
                        rule_name="Xác định nghiệm riêng",
                        title="Thay các hằng số vào nghiệm tổng quát và rút gọn",
                        description=(
                            f"Thay $C_1 = {val_c1_ltx}$ và $C_2 = {val_c2_ltx}$ vào nghiệm tổng quát:\n"
                            f"$$\\begin{{aligned}} y({var}) &= {subst_combined} \\\\ &= {expr_to_latex(particular_sol)} \\end{{aligned}}$$"
                            + (f"\n\nDạng thu gọn tương đương (đặt nhân tử chung):\n$$y({var}) = {expr_to_latex(factored_sol)}$$" if show_factored else "")
                        ),
                        content=ExpressionStepContent(
                            expression_before=c_sol_latex,
                            expression_after=f"y({var}) = {particular_sol}",
                            latex_before=c_sol_latex,
                            latex_after=f"y({var}) = {expr_to_latex(particular_sol)}",
                        ),
                        equation_latex=f"y({var}) = {expr_to_latex(particular_sol)}",
                    )
                )
            elif c11 == 0:
                # Triangular system (Eq 1 gives C2)
                step7_substeps.append(
                    SolutionStep(
                        step_number=1,
                        rule_name="Giải tìm C2",
                        title="Xác định hằng số C2 từ phương trình thứ nhất",
                        description=f"Từ phương trình (1): ${eq1_lhs_latex} = {expr_to_latex(y0)}$, suy ra:\n$$C_2 = {val_c2_ltx}$$",
                        content=ExpressionStepContent(
                            expression_before=f"{c12}*C2 = {y0}",
                            expression_after=f"C2 = {val_c2}",
                            latex_before=f"{eq1_lhs_latex} = {expr_to_latex(y0)}",
                            latex_after=f"C_2 = {val_c2_ltx}",
                        ),
                        equation_latex=f"C_2 = {val_c2_ltx}",
                    )
                )
                step7_substeps.append(
                    SolutionStep(
                        step_number=2,
                        rule_name="Thế C2 tìm C1",
                        title="Thế C2 vào phương trình thứ hai để tìm C1",
                        description=(
                            f"Thay $C_2 = {val_c2_ltx}$ vào phương trình (2): ${eq2_lhs_latex} = {expr_to_latex(v0)}$:\n"
                            f"$$\\left({c21_ltx}\\right) C_1 + \\left({c22_ltx}\\right)\\left({val_c2_ltx}\\right) = {expr_to_latex(v0)} \\implies C_1 = {val_c1_ltx}$$"
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"{c21}*C1 + {c22}*({val_c2}) = {v0}",
                            expression_after=f"C1 = {val_c1}",
                            latex_before=f"{eq2_lhs_latex} = {expr_to_latex(v0)}",
                            latex_after=f"C_1 = {val_c1_ltx}",
                        ),
                        equation_latex=f"C_1 = {val_c1_ltx}",
                    )
                )
                step7_substeps.append(
                    SolutionStep(
                        step_number=3,
                        rule_name="Xác định nghiệm riêng",
                        title="Thay các hằng số vào nghiệm tổng quát và rút gọn",
                        description=(
                            f"Thay $C_1 = {val_c1_ltx}$ và $C_2 = {val_c2_ltx}$ vào nghiệm tổng quát:\n"
                            f"$$\\begin{{aligned}} y({var}) &= {subst_combined} \\\\ &= {expr_to_latex(particular_sol)} \\end{{aligned}}$$"
                            + (f"\n\nDạng thu gọn tương đương (đặt nhân tử chung):\n$$y({var}) = {expr_to_latex(factored_sol)}$$" if show_factored else "")
                        ),
                        content=ExpressionStepContent(
                            expression_before=c_sol_latex,
                            expression_after=f"y({var}) = {particular_sol}",
                            latex_before=c_sol_latex,
                            latex_after=f"y({var}) = {expr_to_latex(particular_sol)}",
                        ),
                        equation_latex=f"y({var}) = {expr_to_latex(particular_sol)}",
                    )
                )
            else:
                # Coupled 2x2 system: Method of substitution
                c1_expr = sp.simplify((y0 - c12 * c2_sym) / c11)
                sub_into_eq2_lhs = sp.expand(c21 * c1_expr + c22 * c2_sym)
                c1_term_ltx = f"\\left({expr_to_latex(c1_expr)}\\right)"
                c1_unsub_ltx = (
                    f"{expr_to_latex(y0)} - \\left({expr_to_latex(c12 * val_c2)}\\right)"
                    if (c11 == 1 and c12 != 1)
                    else (f"{expr_to_latex(y0)} - \\left({expr_to_latex(val_c2)}\\right)" if (c11 == 1 and c12 == 1) else f"\\frac{{{expr_to_latex(y0)} - \\left({expr_to_latex(c12 * val_c2)}\\right)}}{{{c11_ltx}}}")
                )

                step7_substeps.append(
                    SolutionStep(
                        step_number=1,
                        rule_name="Biểu diễn C1",
                        title="Biểu diễn C1 theo C2 từ phương trình thứ nhất",
                        description=f"Từ phương trình (1): ${eq1_lhs_latex} = {expr_to_latex(y0)}$, cô lập hằng số $C_1$:\n$$C_1 = {expr_to_latex(c1_expr)}$$",
                        content=ExpressionStepContent(
                            expression_before=f"{c11}*C1 + {c12}*C2 = {y0}",
                            expression_after=f"C1 = {c1_expr}",
                            latex_before=f"{eq1_lhs_latex} = {expr_to_latex(y0)}",
                            latex_after=f"C_1 = {expr_to_latex(c1_expr)}",
                        ),
                        equation_latex=f"C_1 = {expr_to_latex(c1_expr)}",
                    )
                )
                step7_substeps.append(
                    SolutionStep(
                        step_number=2,
                        rule_name="Thế và giải tìm C2",
                        title="Thế C1 vào phương trình thứ hai và giải tìm C2",
                        description=(
                            f"Thay biểu thức $C_1 = {expr_to_latex(c1_expr)}$ vào phương trình (2): ${eq2_lhs_latex} = {expr_to_latex(v0)}$:\n"
                            f"$${c21_ltx}{c1_term_ltx} + \\left({c22_ltx}\\right) C_2 = {expr_to_latex(v0)}$$\n"
                            f"Khai triển và thu gọn:\n"
                            f"$${expr_to_latex(sub_into_eq2_lhs)} = {expr_to_latex(v0)}$$\n"
                            f"Giải phương trình bậc nhất tìm được giá trị của $C_2$:\n"
                            f"$$C_2 = {val_c2_ltx}$$"
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"{c21}*({c1_expr}) + {c22}*C2 = {v0}",
                            expression_after=f"C2 = {val_c2}",
                            latex_before=f"{c21_ltx}{c1_term_ltx} + \\left({c22_ltx}\\right) C_2 = {expr_to_latex(v0)}",
                            latex_after=f"C_2 = {val_c2_ltx}",
                        ),
                        equation_latex=f"C_2 = {val_c2_ltx}",
                    )
                )
                step7_substeps.append(
                    SolutionStep(
                        step_number=3,
                        rule_name="Xác định C1",
                        title="Thay ngược C2 để xác định hằng số C1",
                        description=(
                            f"Thay giá trị $C_2 = {val_c2_ltx}$ trở lại biểu thức của $C_1$:\n"
                            f"$$C_1 = {c1_unsub_ltx} = {val_c1_ltx}$$"
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"C2 = {val_c2}",
                            expression_after=f"C1 = {val_c1}",
                            latex_before=f"C_2 = {val_c2_ltx}",
                            latex_after=f"C_1 = {val_c1_ltx}",
                        ),
                        equation_latex=f"C_1 = {val_c1_ltx}",
                    )
                )
                step7_substeps.append(
                    SolutionStep(
                        step_number=4,
                        rule_name="Xác định nghiệm riêng",
                        title="Thay các hằng số vào nghiệm tổng quát và rút gọn",
                        description=(
                            f"Thay các hằng số $C_1 = {val_c1_ltx}$ và $C_2 = {val_c2_ltx}$ vào nghiệm tổng quát:\n"
                            f"$$\\begin{{aligned}} y({var}) &= {subst_combined} \\\\ &= {expr_to_latex(particular_sol)} \\end{{aligned}}$$"
                            + (f"\n\nDạng thu gọn tương đương (đặt nhân tử chung):\n$$y({var}) = {expr_to_latex(factored_sol)}$$" if show_factored else "")
                        ),
                        content=ExpressionStepContent(
                            expression_before=c_sol_latex,
                            expression_after=f"y({var}) = {particular_sol}",
                            latex_before=c_sol_latex,
                            latex_after=f"y({var}) = {expr_to_latex(particular_sol)}",
                        ),
                        equation_latex=f"y({var}) = {expr_to_latex(particular_sol)}",
                    )
                )

            step7_desc = (
                f"Quá trình xác định nghiệm riêng thỏa mãn bài toán Cauchy (IVP):\n\n"
                f"1. Nhắc lại hệ phương trình thu được từ Bước 6:\n"
                f"$${system_cases_latex}$$\n\n"
                f"2. Giải hệ phương trình xác định các hằng số tích phân:\n"
                f"$${c_sol_latex}$$\n\n"
                f"3. Thay giá trị $C_1, C_2$ vào nghiệm tổng quát:\n"
                f"$$y({var}) = {subst_combined}$$\n\n"
                f"4. Nghiệm riêng của bài toán Cauchy:\n"
                f"$$y({var}) = {expr_to_latex(particular_sol)}$$"
                + (f"\n\nDạng thu gọn tương đương (đặt nhân tử chung):\n$$y({var}) = {expr_to_latex(factored_sol)}$$" if show_factored else "")
            )

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Nghiệm riêng",
                    title="Xác định nghiệm riêng thỏa mãn bài toán Cauchy (IVP)",
                    description=step7_desc,
                    content=ExpressionStepContent(
                        expression_before=f"C1 = {val_c1}, C2 = {val_c2}",
                        expression_after=f"y({var}) = {particular_sol}",
                        latex_before=c_sol_latex,
                        latex_after=f"y({var}) = {expr_to_latex(particular_sol)}",
                    ),
                    equation_latex=f"y({var}) = {expr_to_latex(particular_sol)}",
                    substeps=tuple(step7_substeps),
                )
            )
            step_num += 1

        # -------------------------------------------------------------------------
        # Step 8: Independent Mathematical Verification (Kiểm chứng nghiệm)
        # -------------------------------------------------------------------------
        # Section A: Verify ODE Differential Equation
        dy = sp.diff(final_sol, var)
        d2y = sp.diff(dy, var)
        ode_lhs = a * d2y + b * dy + c * final_sol
        residual = sp.simplify(ode_lhs)
        if residual != 0:
            residual = sp.simplify(sp.expand(ode_lhs))
        if residual != 0:
            residual = sp.simplify(sp.trigsimp(residual))

        is_ode_verified = bool(residual == 0)
        if not is_ode_verified and not has_ivp and (c1_sym in residual.free_symbols or c2_sym in residual.free_symbols):
            coeff_c1 = sp.simplify(residual.coeff(c1_sym, 1))
            coeff_c2 = sp.simplify(residual.coeff(c2_sym, 1))
            rem = sp.simplify(residual.subs([(c1_sym, 0), (c2_sym, 0)]))
            if coeff_c1 == 0 and coeff_c2 == 0 and rem == 0:
                is_ode_verified = True

        # Section B: Verify Cauchy Initial Conditions (if IVP)
        is_y0_verified = True
        is_v0_verified = True
        val_y0_check: sp.Expr | None = None
        val_v0_check: sp.Expr | None = None

        if has_ivp:
            val_y0_check = sp.simplify(final_sol.subs(var, t0))
            is_y0_verified = bool(sp.simplify(val_y0_check - y0) == 0)

            val_v0_check = sp.simplify(dy.subs(var, t0))
            is_v0_verified = bool(sp.simplify(val_v0_check - v0) == 0)

        # Determine verification status
        if has_ivp:
            if is_ode_verified and is_y0_verified and is_v0_verified:
                v_status = VerificationStatus.VERIFIED
                v_method = "second_order_ode_residual_and_dual_ic_zero_check"
                v_details = (
                    f"Kiểm chứng độc lập thành công: Biểu thức dư R({var}) ≡ 0 và "
                    f"hệ điều kiện Cauchy y({t0}) = {y0}, y'({t0}) = {v0} nghiệm đúng."
                )
            elif not is_ode_verified:
                v_status = VerificationStatus.FAILED
                v_method = "ode_residual_mismatch"
                v_details = f"Phương trình vi phân không thỏa mãn: Biểu thức dư R({var}) = {residual} != 0."
            elif not is_y0_verified:
                v_status = VerificationStatus.FAILED
                v_method = "initial_condition_mismatch"
                v_details = f"Nghiệm không thỏa mãn điều kiện ban đầu y({t0}): nhận được {val_y0_check}, kỳ vọng {y0}."
            else:
                v_status = VerificationStatus.FAILED
                v_method = "initial_derivative_mismatch"
                v_details = f"Nghiệm không thỏa mãn điều kiện đạo hàm ban đầu y'({t0}): nhận được {val_v0_check}, kỳ vọng {v0}."
        else:
            if is_ode_verified:
                v_status = VerificationStatus.VERIFIED
                v_method = "second_order_ode_residual_zero_check"
                v_details = f"Kiểm chứng độc lập thành công: Biểu thức dư R({var}) ≡ 0."
            else:
                v_status = VerificationStatus.FAILED
                v_method = "ode_residual_mismatch"
                v_details = f"Phương trình vi phân không thỏa mãn: Biểu thức dư R({var}) = {residual} != 0."

        verification_result = VerificationResult(
            status=v_status,
            method=v_method,
            details=v_details,
        )

        status_ode_text = "Thỏa mãn (R ≡ 0) — Thỏa mãn đồng nhất" if is_ode_verified else "Chưa xác nhận"
        step8_desc_lines = [
            "Bước này không tìm nghiệm mới. Ta thay nghiệm vừa tìm được "
            "trở lại phương trình vi phân ban đầu và kiểm tra các điều kiện ban đầu để xác nhận rằng nghiệm thực sự đúng.\n",
            "A. Kiểm chứng phương trình vi phân:",
            f"Tính biểu thức dư của phương trình vi phân theo biến ${var}$:",
            f"$$R({var}) = {ode_lhs_latex}$$",
            f"Thay nghiệm $y({var}) = {expr_to_latex(final_sol)}$ cùng các đạo hàm cấp một và cấp hai vào vế trái:",
            f"- Đạo hàm cấp một: $y'({var}) = {expr_to_latex(dy)}$",
            f"- Đạo hàm cấp hai: $y''({var}) = {expr_to_latex(d2y)}$",
            "Rút gọn biểu thức thu được:",
            f"$$R({var}) = {expr_to_latex(residual)}" + (r" \equiv 0" if is_ode_verified else r" \neq 0") + "$$",
        ]

        if has_ivp and val_y0_check is not None and val_v0_check is not None:
            y0_comp_ltx = f"y({expr_to_latex(t0)}) = {expr_to_latex(val_y0_check)}" + (f" = {expr_to_latex(y0)}" if is_y0_verified else f" \\neq {expr_to_latex(y0)}")
            v0_comp_ltx = f"y'({expr_to_latex(t0)}) = {expr_to_latex(val_v0_check)}" + (f" = {expr_to_latex(v0)}" if is_v0_verified else f" \\neq {expr_to_latex(v0)}")
            status_y0_text = f"Thỏa mãn ({expr_to_latex(val_y0_check)} = {expr_to_latex(y0)})" if is_y0_verified else "Sai lệch"
            status_v0_text = f"Thỏa mãn ({expr_to_latex(val_v0_check)} = {expr_to_latex(v0)})" if is_v0_verified else "Sai lệch"
            step8_desc_lines.extend([
                "\nB. Kiểm chứng hệ điều kiện ban đầu:",
                f"1. Kiểm tra điều kiện hàm số tại ${var} = {expr_to_latex(t0)}$:",
                f"$${y0_comp_ltx}$$",
                f"2. Kiểm tra điều kiện đạo hàm tại ${var} = {expr_to_latex(t0)}$:",
                f"$${v0_comp_ltx}$$",
                "\nTổng kết kết quả kiểm chứng:",
                f"- Biểu thức dư phương trình vi phân: {status_ode_text}",
                f"- Điều kiện ban đầu hàm số y({expr_to_latex(t0)}): {status_y0_text}",
                f"- Điều kiện đạo hàm ban đầu y'({expr_to_latex(t0)}): {status_v0_text}",
            ])
        else:
            step8_desc_lines.extend([
                "\nTổng kết kết quả kiểm chứng:",
                f"- Biểu thức dư phương trình vi phân: {status_ode_text}",
            ])

        step8_description = "\n".join(step8_desc_lines)

        if has_ivp:
            if v_status == VerificationStatus.VERIFIED:
                eq8_latex = (
                    f"\\begin{{aligned}} "
                    f"R({var}) &= {ode_lhs_latex} \\equiv 0 \\\\ "
                    f"y({expr_to_latex(t0)}) &= {expr_to_latex(y0)}, \\quad y'({expr_to_latex(t0)}) = {expr_to_latex(v0)} "
                    f"\\end{{aligned}}"
                )
            else:
                eq8_latex = (
                    f"\\begin{{aligned}} "
                    f"R({var}) &= {expr_to_latex(residual)} \\\\ "
                    f"y({expr_to_latex(t0)}) &= {expr_to_latex(val_y0_check)}, \\quad y'({expr_to_latex(t0)}) = {expr_to_latex(val_v0_check)} "
                    f"\\end{{aligned}}"
                )
            step8_substeps = (
                SolutionStep(
                    step_number=1,
                    rule_name="Kiểm chứng phương trình",
                    title="Kiểm chứng vế trái phương trình vi phân",
                    description=f"Thay nghiệm vào phương trình vi phân ban đầu thu được $R({var}) = {ode_lhs_latex} = {expr_to_latex(residual)}$.",
                    content=ExpressionStepContent(
                        expression_before=f"R({var}) = {a}*y'' + {b}*y' + {c}*y",
                        expression_after=f"R({var}) = {residual}",
                        latex_before=f"R({var}) = {ode_lhs_latex}",
                        latex_after=f"R({var}) = {expr_to_latex(residual)}" + (r" \equiv 0" if is_ode_verified else ""),
                    ),
                    equation_latex=f"R({var}) = {expr_to_latex(residual)}" + (r" \equiv 0" if is_ode_verified else ""),
                ),
                SolutionStep(
                    step_number=2,
                    rule_name="Kiểm chứng điều kiện ban đầu",
                    title="Kiểm chứng các điều kiện ban đầu Cauchy",
                    description=f"Thay điểm ban đầu: $y({expr_to_latex(t0)}) = {expr_to_latex(val_y0_check)}$, $y'({expr_to_latex(t0)}) = {expr_to_latex(val_v0_check)}$.",
                    content=ExpressionStepContent(
                        expression_before=f"y({t0}) = {val_y0_check}, y'({t0}) = {val_v0_check}",
                        expression_after=f"y({t0}) = {y0}, y'({t0}) = {v0}",
                        latex_before=f"y({expr_to_latex(t0)}) = {expr_to_latex(val_y0_check)}, \\quad y'({expr_to_latex(t0)}) = {expr_to_latex(val_v0_check)}",
                        latex_after=f"y({expr_to_latex(t0)}) = {expr_to_latex(y0)}, \\quad y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}",
                    ),
                    equation_latex=f"y({expr_to_latex(t0)}) = {expr_to_latex(y0)}, \\quad y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}",
                ),
            )
        else:
            eq8_latex = f"R({var}) = {ode_lhs_latex} \\equiv 0" if is_ode_verified else f"R({var}) = {expr_to_latex(residual)}"
            step8_substeps = ()

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Kiểm chứng nghiệm",
                title="Kiểm chứng nghiệm",
                description=step8_description,
                content=ExpressionStepContent(
                    expression_before=f"R({var}) = {a}*y'' + {b}*y' + {c}*y",
                    expression_after=f"R({var}) = 0" if v_status == VerificationStatus.VERIFIED else f"R({var}) = {residual}",
                    latex_before=f"R({var}) = {ode_lhs_latex}",
                    latex_after=eq8_latex,
                ),
                equation_latex=eq8_latex,
                substeps=step8_substeps,
                notes=verification_result.details,
            )
        )

        status = SolutionStatus.SUCCESS if v_status == VerificationStatus.VERIFIED else (
            SolutionStatus.DISCREPANCY_DETECTED if v_status == VerificationStatus.FAILED else SolutionStatus.UNVERIFIED
        )
        elapsed = (time.perf_counter() - t0_start) * 1000.0

        return SolutionResponse(
            status=status,
            verification=verification_result,
            raw_input=request.raw_input,
            canonical_input=parsed.canonical_eq,
            final_result=f"y({var}) = {final_sol}",
            final_latex=f"y({var}) = {expr_to_latex(final_sol)}",
            steps=tuple(steps),
            domain_restrictions=(),
            warnings=(),
            execution_time_ms=elapsed,
        )

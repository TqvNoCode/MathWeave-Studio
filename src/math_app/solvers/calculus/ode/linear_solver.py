"""First-order linear differential equation solver (Constant & Variable Coefficients)."""

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
from math_app.input.ode_parser import ParsedODE, parse_ode_input
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.verification.calculus.ode_verifier import (
    ODEVerifier,
    validate_initial_point_in_domain,
)


class ODELinearSolver(Solver):
    """Solver for first-order linear ODEs: y' = ay + b and y' + p(t)y = g(t)."""

    def __init__(self, verifier: ODEVerifier | None = None) -> None:
        self.verifier = verifier or ODEVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type in (
            ProblemType.ODE_FIRST_ORDER_LINEAR,
            ProblemType.SOLVE_EQUATION,
        )

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        t0_start = time.perf_counter()
        raw = request.raw_input.strip()
        if not raw:
            raise InvalidInputError("Phương trình vi phân không được để trống (Equation cannot be empty).")

        # Parse and validate equation
        parsed: ParsedODE = parse_ode_input(
            raw,
            target_variable=request.target_variable,
            parameters=dict(request.parameters),
        )

        if not parsed.is_linear:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="linearity_check",
                    details="Phương trình không phải là phương trình vi phân tuyến tính cấp 1.",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=(
                    "Phương trình này phi tuyến tính theo y hoặc y' và không thể giải bằng thuật toán tuyến tính cấp 1 "
                    "(Nonlinear ODE is unsupported by ODELinearSolver).",
                ),
                execution_time_ms=elapsed,
            )

        var = parsed.independent_var
        dep_var = parsed.dependent_var
        p_expr = parsed.p_expr if parsed.p_expr is not None else sp.Integer(0)
        g_expr = parsed.g_expr if parsed.g_expr is not None else sp.Integer(0)
        c_sym = sp.Symbol("C")
        user_warnings: list[str] = []

        if not parsed.is_homogeneous:
            user_warnings.append(
                "Lưu ý phạm vi: MathWeave Studio hiện đang chuẩn hóa hệ thống phương trình thuần nhất. "
                "Chức năng giải không thuần nhất sẽ được nâng cấp toàn diện trong phiên bản tiếp theo."
            )

        # Validate initial point in domain of linear equation
        if parsed.initial_condition is not None:
            t0, y0 = parsed.initial_condition

            # Check original unsimplified denominators and leading coefficients
            is_valid_orig, orig_err = validate_initial_point_in_domain(
                None,
                var,
                dep_var,
                t0,
                y0,
                original_denominators=parsed.original_denominators,
                leading_coeffs=parsed.leading_coeffs,
            )
            if not is_valid_orig:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.INVALID_INPUT,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="initial_point_domain_validation",
                        details=f"Điểm ban đầu ({t0}, {y0}) vi phạm điều kiện xác định ban đầu: {orig_err}",
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=(
                        f"Điều kiện ban đầu ({t0}, {y0}) không hợp lệ: {orig_err}",
                    ),
                    execution_time_ms=elapsed,
                )

            is_valid_p, p_err = validate_initial_point_in_domain(
                p_expr,
                var,
                dep_var,
                t0,
                y0,
                original_denominators=parsed.original_denominators,
                leading_coeffs=parsed.leading_coeffs,
            )
            if not is_valid_p:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.INVALID_INPUT,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="initial_point_domain_validation",
                        details=f"Điểm ban đầu t0 = {t0} là điểm kỳ dị của hệ số p({var}) = {p_expr}: {p_err}",
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=(
                        f"Điều kiện ban đầu ({t0}, {y0}) không hợp lệ: Hệ số p({var}) = {p_expr} "
                        f"có điểm kỳ dị hoặc không xác định tại {var} = {t0} ({p_err}).",
                    ),
                    execution_time_ms=elapsed,
                )

            is_valid_g, g_err = validate_initial_point_in_domain(
                g_expr,
                var,
                dep_var,
                t0,
                y0,
                original_denominators=parsed.original_denominators,
                leading_coeffs=parsed.leading_coeffs,
            )
            if not is_valid_g:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.INVALID_INPUT,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="initial_point_domain_validation",
                        details=f"Điểm ban đầu t0 = {t0} là điểm kỳ dị của hàm tự do g({var}) = {g_expr}: {g_err}",
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=(
                        f"Điều kiện ban đầu ({t0}, {y0}) không hợp lệ: Hàm tự do g({var}) = {g_expr} "
                        f"có điểm kỳ dị hoặc không xác định tại {var} = {t0} ({g_err}).",
                    ),
                    execution_time_ms=elapsed,
                )

        steps: list[SolutionStep] = []
        step_num = 1
        domain_restrictions: list[str] = []

        # =========================================================================
        # Case 1: First-order Linear ODE with Constant Coefficients (Phase A)
        # Equation: y' = a*y + b
        # =========================================================================
        if parsed.is_constant_coeff and parsed.a_coeff is not None and parsed.b_coeff is not None:
            a_val = parsed.a_coeff
            b_val = parsed.b_coeff

            # Step 1: Standard form identification
            eq_latex = f"\\frac{{d{dep_var}}}{{d{var}}} = {expr_to_latex(a_val * sp.Symbol(str(dep_var)) + b_val)}"
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Nhận dạng dạng phương trình",
                    title="Nhận dạng phương trình vi phân tuyến tính hệ số hằng",
                    description=(
                        f"Phương trình đưa về dạng chuẩn $y' = a\\,y + b$ với hệ số hằng "
                        f"$a = {expr_to_latex(a_val)}$ và $b = {expr_to_latex(b_val)}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=parsed.canonical_eq,
                        expression_after=f"y' = {a_val}*y + {b_val}",
                        latex_before=expr_to_latex(parsed.lhs_expr) + " = " + expr_to_latex(parsed.rhs_expr),
                        latex_after=eq_latex,
                    ),
                )
            )
            step_num += 1

            # Subcase A1: a == 0 -> y' = b -> y(t) = b*t + C
            if a_val == 0:
                gen_sol = b_val * var + c_sym
                gen_sol_latex = f"{dep_var}({var}) = {expr_to_latex(b_val * var)} + C" if b_val != 0 else f"{dep_var}({var}) = C"

                steps.append(
                    SolutionStep(
                        step_number=step_num,
                        rule_name="Tích phân hai vế",
                        title="Tích phân trực tiếp khi hệ số a = 0",
                        description=(
                            f"Vì $a = 0$, phương trình trở thành $y' = {expr_to_latex(b_val)}$. "
                            f"Tích phân hai vế theo biến ${var}$ thu được nghiệm tổng quát $y = {expr_to_latex(b_val)}\\,{var} + C$."
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"y' = {b_val}",
                            expression_after=f"y({var}) = {gen_sol}",
                            latex_before=f"\\frac{{d{dep_var}}}{{d{var}}} = {expr_to_latex(b_val)}",
                            latex_after=gen_sol_latex,
                        ),
                    )
                )
                step_num += 1

                final_sol = gen_sol
                final_latex_sol = gen_sol_latex

                # Initial condition handling
                if parsed.initial_condition is not None:
                    t0, y0 = parsed.initial_condition
                    c_val = sp.simplify(y0 - b_val * t0)
                    part_sol = sp.simplify(b_val * var + c_val)
                    part_sol_latex = f"{dep_var}({var}) = {expr_to_latex(part_sol)}"

                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name="Áp dụng điều kiện ban đầu",
                            title="Xác định hằng số C từ điều kiện ban đầu",
                            description=(
                                f"Thay {var} = {t0} và {dep_var} = {y0} vào nghiệm tổng quát: "
                                f"{y0} = {b_val}*({t0}) + C => C = {c_val}."
                            ),
                            content=ExpressionStepContent(
                                expression_before=f"{y0} = {b_val}*{t0} + C",
                                expression_after=f"C = {c_val}",
                                latex_before=f"{expr_to_latex(y0)} = {expr_to_latex(b_val)}\\cdot {expr_to_latex(t0)} + C",
                                latex_after=f"C = {expr_to_latex(c_val)}",
                            ),
                        )
                    )
                    step_num += 1

                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name="Nghiệm riêng",
                            title="Nghiệm riêng của bài toán Cauchy (IVP)",
                            description="Thế giá trị hằng số C vừa tìm được vào nghiệm tổng quát để kết luận nghiệm riêng.",
                            content=ExpressionStepContent(
                                expression_before=f"y({var}) = {gen_sol}",
                                expression_after=f"y({var}) = {part_sol}",
                                latex_before=gen_sol_latex,
                                latex_after=part_sol_latex,
                            ),
                        )
                    )
                    final_sol = part_sol
                    final_latex_sol = part_sol_latex

            # Subcase A2: a != 0 -> y(t) = C*exp(a*t) - b/a
            else:
                # Equilibrium solution: y' = 0 => y_eq = -b/a
                y_eq = sp.simplify(-b_val / a_val)
                y_eq_latex = f"{dep_var}_{{eq}} = {expr_to_latex(y_eq)}"

                steps.append(
                    SolutionStep(
                        step_number=step_num,
                        rule_name="Nghiệm cân bằng",
                        title="Xác định nghiệm cân bằng (Equilibrium Solution)",
                        description=(
                            f"Cho y' = 0 ta có {a_val}*y + {b_val} = 0 => nghiệm cân bằng duy nhất y = {y_eq}."
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"{a_val}*y + {b_val} = 0",
                            expression_after=f"y_eq = {y_eq}",
                            latex_before=f"{expr_to_latex(a_val)}{dep_var} + {expr_to_latex(b_val)} = 0",
                            latex_after=y_eq_latex,
                        ),
                    )
                )
                step_num += 1

                if a_val.is_symbol:
                    domain_restrictions.append(f"Giả định tham số {a_val} khác 0 để tránh phép chia cho 0.")

                # Integrating factor for y' - a*y = b: mu(t) = exp(-a*t)
                mu_expr = sp.exp(-a_val * var)
                gen_sol = sp.simplify(c_sym * sp.exp(a_val * var) - b_val / a_val)
                gen_sol_latex = f"{dep_var}({var}) = {expr_to_latex(gen_sol)}"

                steps.append(
                    SolutionStep(
                        step_number=step_num,
                        rule_name="Thừa số tích phân",
                        title="Tìm thừa số tích phân và dẫn xuất nghiệm tổng quát",
                        description=(
                            f"Đưa phương trình về dạng $y' - {expr_to_latex(a_val)}y = {expr_to_latex(b_val)}$. "
                            f"Thừa số tích phân là $\\mu({var}) = e^{{\\int (-{expr_to_latex(a_val)})\\,d{var}}} = {expr_to_latex(mu_expr)}$. "
                            f"Nhân hai vế và tích phân suy ra nghiệm tổng quát: $y({var}) = {expr_to_latex(gen_sol)}$."
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"y' - {a_val}*y = {b_val}",
                            expression_after=f"y({var}) = {gen_sol}",
                            latex_before=f"\\frac{{d{dep_var}}}{{d{var}}} - {expr_to_latex(a_val)}{dep_var} = {expr_to_latex(b_val)}",
                            latex_after=gen_sol_latex,
                        ),
                    )
                )
                step_num += 1

                final_sol = gen_sol
                final_latex_sol = gen_sol_latex

                # Initial condition handling
                if parsed.initial_condition is not None:
                    t0, y0 = parsed.initial_condition
                    # y0 = C*exp(a*t0) - b/a => C = (y0 + b/a)*exp(-a*t0)
                    c_val = sp.simplify((y0 + b_val / a_val) * sp.exp(-a_val * t0))
                    part_sol = sp.simplify((y0 + b_val / a_val) * sp.exp(a_val * (var - t0)) - b_val / a_val)
                    part_sol_latex = f"{dep_var}({var}) = {expr_to_latex(part_sol)}"

                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name="Áp dụng điều kiện ban đầu",
                            title="Xác định hằng số C từ điều kiện ban đầu",
                            description=(
                                f"Thay {var} = {t0} và {dep_var} = {y0} vào nghiệm tổng quát: "
                                f"{y0} = C*exp({a_val}*{t0}) - {b_val}/{a_val} => C = {c_val}."
                            ),
                            content=ExpressionStepContent(
                                expression_before=f"{y0} = C*exp({a_val}*{t0}) - {b_val}/{a_val}",
                                expression_after=f"C = {c_val}",
                                latex_before=f"{expr_to_latex(y0)} = {expr_to_latex(sp.simplify(c_sym * sp.exp(a_val * t0) - b_val / a_val))}",
                                latex_after=f"C = {expr_to_latex(c_val)}",
                            ),
                        )
                    )
                    step_num += 1

                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name="Nghiệm riêng",
                            title="Nghiệm riêng của bài toán Cauchy (IVP)",
                            description="Thế giá trị hằng số C cụ thể vào nghiệm tổng quát để thu được nghiệm riêng duy nhất.",
                            content=ExpressionStepContent(
                                expression_before=f"y({var}) = {gen_sol}",
                                expression_after=f"y({var}) = {part_sol}",
                                latex_before=gen_sol_latex,
                                latex_after=part_sol_latex,
                            ),
                        )
                    )
                    final_sol = part_sol
                    final_latex_sol = part_sol_latex

        # =========================================================================
        # Case 2: First-order Linear ODE with Variable Coefficients (Phase B)
        # Equation: y' + p(t)*y = g(t)
        # =========================================================================
        else:
            # Check domain restrictions on denominators of p(x) and g(x)
            try:
                _, p_denom = sp.fraction(p_expr)
                if p_denom != 1 and var in p_denom.free_symbols:
                    domain_restrictions.append(f"Điều kiện xác định của hệ số p({var}): {p_denom} khác 0.")
            except Exception:
                pass
            try:
                _, g_denom = sp.fraction(g_expr)
                if g_denom != 1 and var in g_denom.free_symbols:
                    domain_restrictions.append(f"Điều kiện xác định của hàm g({var}): {g_denom} khác 0.")
            except Exception:
                pass

            # Step 1: Identify p(t) and g(t)
            eq_std_latex = f"\\frac{{d{dep_var}}}{{d{var}}} + \\left( {expr_to_latex(p_expr)} \\right) {dep_var} = {expr_to_latex(g_expr)}"
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Xác định hệ số",
                    title="Nhận dạng dạng chuẩn y' + p(t)y = g(t)",
                    description=(
                        f"Phương trình vi phân tuyến tính cấp 1 có hệ số $p({var}) = {expr_to_latex(p_expr)}$ "
                        f"và hàm tự do (forcing term) $g({var}) = {expr_to_latex(g_expr)}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=parsed.canonical_eq,
                        expression_after=f"y' + ({p_expr})*y = {g_expr}",
                        latex_before=expr_to_latex(parsed.lhs_expr) + " = " + expr_to_latex(parsed.rhs_expr),
                        latex_after=eq_std_latex,
                    ),
                )
            )
            step_num += 1

            # Step 2: Compute integrating factor mu(t) = exp(int(p(t) dt))
            int_p = sp.integrate(p_expr, var)
            if any(isinstance(node, sp.Integral) for node in sp.preorder_traversal(int_p)):
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="integrating_factor",
                        details=f"Tích phân int(p({var}) d{var}) không thể biểu diễn dưới dạng hàm sơ cấp.",
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=(
                        f"Tích phân của hàm p({var}) = {p_expr} không có nguyên hàm sơ cấp "
                        "(Non-elementary antiderivative for integrating factor).",
                    ),
                    execution_time_ms=elapsed,
                )

            mu_expr = sp.simplify(sp.exp(int_p))
            mu_latex = f"\\mu({var}) = e^{{\\int \\left( {expr_to_latex(p_expr)} \\right) d{var}}} = {expr_to_latex(mu_expr)}"

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Thừa số tích phân",
                    title="Tính thừa số tích phân \\mu(t)",
                    description=(
                        f"Tính thừa số tích phân theo công thức $\\mu({var}) = e^{{\\int p({var})\\,d{var}}}$: "
                        f"$\\int ({expr_to_latex(p_expr)})\\,d{var} = {expr_to_latex(int_p)} \\implies \\mu({var}) = {expr_to_latex(mu_expr)}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"int({p_expr}) d{var} = {int_p}",
                        expression_after=f"mu({var}) = {mu_expr}",
                        latex_before=f"\\int \\left( {expr_to_latex(p_expr)} \\right) d{var} = {expr_to_latex(int_p)}",
                        latex_after=mu_latex,
                    ),
                )
            )
            step_num += 1

            # Step 3: Multiply both sides by mu(t)
            lhs_mult = f"\\left( {expr_to_latex(mu_expr)} \\right) \\frac{{d{dep_var}}}{{d{var}}} + \\left( {expr_to_latex(sp.simplify(mu_expr * p_expr))} \\right) {dep_var}"
            rhs_mult = expr_to_latex(sp.simplify(mu_expr * g_expr))

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Nhân thừa số tích phân",
                    title="Nhân hai vế của phương trình với thừa số tích phân",
                    description=(
                        f"Nhân hai vế của phương trình vi phân với $\\mu({var}) = {expr_to_latex(mu_expr)}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"y' + ({p_expr})*y = {g_expr}",
                        expression_after=f"({mu_expr})*y' + ({sp.simplify(mu_expr * p_expr)})*y = {sp.simplify(mu_expr * g_expr)}",
                        latex_before=eq_std_latex,
                        latex_after=f"{lhs_mult} = {rhs_mult}",
                    ),
                )
            )
            step_num += 1

            # Step 4: Product rule transformation
            prod_lhs_latex = f"\\frac{{d}}{{d{var}}} \\left[ \\left( {expr_to_latex(mu_expr)} \\right) {dep_var} \\right]"
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Quy tắc đạo hàm của tích (ODE)",
                    title="Biến đổi vế trái theo quy tắc đạo hàm của tích",
                    description=(
                        f"Theo quy tắc đạo hàm của tích, $\\frac{{d}}{{d{var}}}[\\mu({var})\\,y] = \\mu\\,y' + \\mu'\\,y$. "
                        f"Vì $\\mu' = \\mu\\,p({var})$, vế trái chính là đạo hàm $\\frac{{d}}{{d{var}}}\\left[{expr_to_latex(mu_expr)}\\,{dep_var}\\right]$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"({mu_expr})*y' + ({sp.simplify(mu_expr * p_expr)})*y",
                        expression_after=f"d/d{var}[({mu_expr})*y] = {sp.simplify(mu_expr * g_expr)}",
                        latex_before=f"{lhs_mult} = {rhs_mult}",
                        latex_after=f"{prod_lhs_latex} = {rhs_mult}",
                    ),
                )
            )
            step_num += 1

            # Step 5: Integrate both sides
            rhs_integrand = sp.simplify(mu_expr * g_expr)
            rhs_integral = sp.integrate(rhs_integrand, var)
            if any(isinstance(node, sp.Integral) for node in sp.preorder_traversal(rhs_integral)):
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="integrating_factor",
                        details=f"Tích phân int(\u03bc({var}) * g({var}) d{var}) không thể biểu diễn dưới dạng hàm sơ cấp.",
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=(
                        f"Tích phân int(\u03bc({var}) * g({var}) d{var}) = int({rhs_integrand} d{var}) không có nguyên hàm sơ cấp "
                        "(Non-elementary integral on RHS).",
                    ),
                    execution_time_ms=elapsed,
                )

            integrated_latex = f"\\left( {expr_to_latex(mu_expr)} \\right) {dep_var} = {expr_to_latex(rhs_integral)} + C"

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Tích phân hai vế",
                    title="Lấy tích phân hai vế và bổ sung hằng số C",
                    description=(
                        f"Tích phân vế phải: $\\int ({expr_to_latex(rhs_integrand)})\\,d{var} = {expr_to_latex(rhs_integral)} + C$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"d/d{var}[({mu_expr})*y] = {rhs_integrand}",
                        expression_after=f"({mu_expr})*y = {rhs_integral} + C",
                        latex_before=f"{prod_lhs_latex} = {rhs_mult}",
                        latex_after=integrated_latex,
                    ),
                )
            )
            step_num += 1

            # Step 6: Derive general solution
            gen_sol = sp.simplify((rhs_integral + c_sym) / mu_expr)
            gen_sol_latex = f"{dep_var}({var}) = {expr_to_latex(gen_sol)}"

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Rút ra nghiệm tổng quát",
                    title="Rút ra nghiệm tổng quát y(t)",
                    description=(
                        f"Chia hai vế cho $\\mu({var}) = {expr_to_latex(mu_expr)}$ để thu được nghiệm tổng quát $y({var}) = {expr_to_latex(gen_sol)}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"({mu_expr})*y = {rhs_integral} + C",
                        expression_after=f"y({var}) = {gen_sol}",
                        latex_before=integrated_latex,
                        latex_after=gen_sol_latex,
                    ),
                )
            )
            step_num += 1

            final_sol = gen_sol
            final_latex_sol = gen_sol_latex

            # Step 7: Initial condition if given
            if parsed.initial_condition is not None:
                t0, y0 = parsed.initial_condition
                # Evaluate mu(t0) and rhs_integral(t0)
                try:
                    mu_t0 = sp.simplify(mu_expr.subs(var, t0))
                    int_t0 = sp.simplify(rhs_integral.subs(var, t0))
                    c_val = sp.simplify(y0 * mu_t0 - int_t0)
                    part_sol = sp.simplify((rhs_integral + c_val) / mu_expr)
                    part_sol_latex = f"{dep_var}({var}) = {expr_to_latex(part_sol)}"

                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name="Áp dụng điều kiện ban đầu",
                            title="Xác định hằng số C từ điều kiện ban đầu",
                            description=(
                                f"Thay {var} = {t0} và {dep_var} = {y0} vào hệ thức: "
                                f"{y0} = ({int_t0} + C) / {mu_t0} => C = {c_val}."
                            ),
                            content=ExpressionStepContent(
                                expression_before=f"{y0} = ({int_t0} + C) / {mu_t0}",
                                expression_after=f"C = {c_val}",
                                latex_before=f"{expr_to_latex(y0)} = \\frac{{{expr_to_latex(int_t0)} + C}}{{{expr_to_latex(mu_t0)}}}",
                                latex_after=f"C = {expr_to_latex(c_val)}",
                            ),
                        )
                    )
                    step_num += 1

                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name="Nghiệm riêng",
                            title="Nghiệm riêng của bài toán giá trị ban đầu",
                            description="Thế giá trị hằng số C cụ thể vào biểu thức nghiệm để kết luận nghiệm riêng duy nhất.",
                            content=ExpressionStepContent(
                                expression_before=f"y({var}) = {gen_sol}",
                                expression_after=f"y({var}) = {part_sol}",
                                latex_before=gen_sol_latex,
                                latex_after=part_sol_latex,
                            ),
                        )
                    )
                    final_sol = part_sol
                    final_latex_sol = part_sol_latex
                except Exception as exc:
                    domain_restrictions.append(f"Không thể áp dụng điều kiện ban đầu: {exc}")

        # Verification
        verif_res = self.verifier.verify_explicit(
            solution=final_sol,
            variable=var,
            p_expr=p_expr,
            g_expr=g_expr,
            initial_condition=parsed.initial_condition,
            integration_constant=c_sym,
        )

        # Determine overall solution status
        warnings_list: list[str] = list(user_warnings)
        if verif_res.status == VerificationStatus.FAILED:
            sol_status = SolutionStatus.DISCREPANCY_DETECTED
            warnings_list.append(f"Cảnh báo kiểm định toán học: {verif_res.details}")
        elif verif_res.status == VerificationStatus.UNVERIFIED:
            sol_status = SolutionStatus.UNVERIFIED
            warnings_list.append(f"Không thể kiểm chứng độc lập hoàn toàn: {verif_res.details}")
        else:
            sol_status = SolutionStatus.SUCCESS

        elapsed = (time.perf_counter() - t0_start) * 1000.0
        return SolutionResponse(
            status=sol_status,
            verification=verif_res,
            raw_input=request.raw_input,
            canonical_input=parsed.canonical_eq,
            final_result=f"{dep_var}({var}) = {final_sol}",
            final_latex=final_latex_sol,
            steps=tuple(steps),
            domain_restrictions=tuple(domain_restrictions),
            warnings=tuple(warnings_list),
            execution_time_ms=elapsed,
        )

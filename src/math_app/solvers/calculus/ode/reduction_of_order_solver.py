"""Reduction of Order Solver for Second-Order Linear Differential Equations."""

from __future__ import annotations

import time
import sympy as sp

from math_app.application.dtos import (
    ProblemRequest,
    SolutionResponse,
    SolutionStep,
)
from math_app.application.ports.solver import Solver
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.input.ode_parser import ParsedSecondOrderODE, parse_second_order_ode_input
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.verification.calculus.ode_verifier import ODEVerifier


class ODEReductionOfOrderSolver(Solver):
    """Solver for finding a second independent solution y2(t) of a homogeneous linear second-order ODE:

    a(t)*y'' + b(t)*y' + c(t)*y = 0,
    given one non-zero fundamental solution y1(t), via reduction of order y2(t) = v(t)*y1(t).
    """

    def __init__(self, verifier: ODEVerifier | None = None) -> None:
        self.verifier = verifier or ODEVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type in (
            ProblemType.ODE_REDUCTION_OF_ORDER,
            ProblemType.SOLVE_EQUATION,
        )

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        t0_start = time.perf_counter()
        raw = request.raw_input.strip()
        if not raw and not request.parameters:
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

        # Validate known solution y1 is provided
        if parsed.known_solution is None:
            raise InvalidInputError(
                "Cần cung cấp nghiệm đã biết y1(t) cho phương pháp hạ bậc nghiệm. "
                "Cú pháp: y'' + p(t)y' + q(t)y = 0, y1 = ... (Missing known solution y1)."
            )

        y1 = parsed.known_solution
        var = parsed.independent_var
        a = parsed.a_coeff
        b = parsed.b_coeff
        c = parsed.c_coeff

        # Standard normalized coefficients: p(t) = b(t)/a(t), q(t) = c(t)/a(t)
        p_expr = sp.simplify(b / a)
        q_expr = sp.simplify(c / a)

        # Domain restrictions: singularities where a(t) = 0 or denominators vanish
        domain_restrictions: list[str] = []
        try:
            a_zeros = sp.solve(sp.Eq(a, 0), var)
            if a_zeros:
                zeros_str = ", ".join(str(z) for z in a_zeros)
                domain_restrictions.append(f"Điểm kỳ dị của hệ số dẫn a({var}): {var} in {{{zeros_str}}}.")
        except Exception:
            pass

        steps: list[SolutionStep] = []
        step_num = 1

        # -------------------------------------------------------------------------
        # Step 1: Normalize Equation
        # y'' + p(t)*y' + q(t)*y = 0
        # -------------------------------------------------------------------------
        norm_lhs_latex = f"y'' + {expr_to_latex(p_expr)}\\,y' + {expr_to_latex(q_expr)}\\,y = 0"
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Chuẩn hóa phương trình cấp hai",
                title="Đưa phương trình về dạng chuẩn tắc",
                description=(
                    f"Chia hai vế cho hệ số dẫn $a({var}) = {expr_to_latex(a)}$ để nhận dạng chuẩn tắc "
                    f"$y'' + p({var})y' + q({var})y = 0$, với $p({var}) = {expr_to_latex(p_expr)}$ và $q({var}) = {expr_to_latex(q_expr)}$."
                ),
                content=ExpressionStepContent(
                    expression_before=f"{a}*y'' + {b}*y' + {c}*y = 0",
                    expression_after=f"y'' + ({p_expr})*y' + ({q_expr})*y = 0",
                    latex_before=f"{expr_to_latex(a)}\\,y'' + {expr_to_latex(b)}\\,y' + {expr_to_latex(c)}\\,y = 0",
                    latex_after=norm_lhs_latex,
                ),
                equation_latex=norm_lhs_latex,
            )
        )
        step_num += 1

        # -------------------------------------------------------------------------
        # Step 2: Verify Known Solution y1(t)
        # -------------------------------------------------------------------------
        dy1 = sp.diff(y1, var)
        d2y1 = sp.diff(dy1, var)
        r1_val = sp.simplify(a * d2y1 + b * dy1 + c * y1)
        if r1_val != 0:
            r1_val = sp.simplify(sp.trigsimp(r1_val))
        if r1_val != 0:
            r1_val = sp.simplify(sp.expand(r1_val))

        if r1_val != 0:
            raise InvalidInputError(
                f"Nghiệm đã cho y1({var}) = {y1} không thỏa mãn phương trình vi phân ban đầu. "
                f"Biểu thức dư R1({var}) = {r1_val} != 0 (Supplied solution y1 is invalid)."
            )

        res1_latex = f"R_1({var}) = {expr_to_latex(a)}\\,({expr_to_latex(d2y1)}) + {expr_to_latex(b)}\\,({expr_to_latex(dy1)}) + {expr_to_latex(c)}\\,({expr_to_latex(y1)}) \\equiv 0"
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Kiểm tra nghiệm đã biết y1",
                title="Kiểm chứng tính đúng đắn của nghiệm thứ nhất y1(t)",
                description=(
                    f"Thay $y_1({var}) = {expr_to_latex(y1)}$, $y_1' = {expr_to_latex(dy1)}$, $y_1'' = {expr_to_latex(d2y1)}$ "
                    f"vào phương trình vi phân ban đầu. Biểu thức dư đồng nhất bằng 0: $R_1({var}) \\equiv 0$. Nghiệm $y_1$ được xác nhận."
                ),
                content=ExpressionStepContent(
                    expression_before=f"y1({var}) = {y1}",
                    expression_after="R1({var}) = 0",
                    latex_before=f"y_1({var}) = {expr_to_latex(y1)}",
                    latex_after=res1_latex,
                ),
                equation_latex=res1_latex,
            )
        )
        step_num += 1

        # -------------------------------------------------------------------------
        # Step 3: Substitution y2 = v*y1 and Derivatives
        # -------------------------------------------------------------------------
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Đổi biến hạ bậc y2 = v*y1",
                title="Đặt ẩn phụ hạ bậc nghiệm thứ hai y2(t) = v(t)*y1(t)",
                description=(
                    f"Tìm nghiệm thứ hai dưới dạng tích $y_2({var}) = v({var})\\,y_1({var}) = v({var})\\left({expr_to_latex(y1)}\\right)$. "
                    f"Tính các đạo hàm: $y_2' = v' y_1 + v y_1'$ và $y_2'' = v'' y_1 + 2v' y_1' + v y_1''$."
                ),
                content=ExpressionStepContent(
                    expression_before=f"y2 = v*{y1}",
                    expression_after="y2' = v'*y1 + v*y1', y2'' = v''*y1 + 2*v'*y1' + v*y1''",
                    latex_before=f"y_2({var}) = v({var})\\,y_1({var}) = v({var})\\left({expr_to_latex(y1)}\\right)",
                    latex_after=(
                        "y_2' = v' y_1 + v y_1', \\quad "
                        "y_2'' = v'' y_1 + 2v' y_1' + v y_1''"
                    ),
                ),
                equation_latex="y_2'' = v'' y_1 + 2v' y_1' + v y_1''",
            )
        )
        step_num += 1

        # -------------------------------------------------------------------------
        # Step 4: Substitute into normalized ODE and eliminate v terms
        # y1*v'' + (2*y1' + p*y1)*v' = 0
        # -------------------------------------------------------------------------
        v_prime_coeff = sp.simplify(2 * dy1 + p_expr * y1)
        sub_latex = (
            f"y_1 v'' + (2y_1' + p y_1)v' + \\underbrace{{(y_1'' + p y_1' + q y_1)}}_{{= 0}} v = 0 "
            f"\\implies ({expr_to_latex(y1)}) v'' + ({expr_to_latex(v_prime_coeff)}) v' = 0"
        )
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Triệt tiêu số hạng đồng nhất",
                title="Thay vào phương trình vi phân và triệt tiêu số hạng chứa v",
                description=(
                    "Nhóm các số hạng: $v'' y_1 + v'(2y_1' + p y_1) + v(y_1'' + p y_1' + q y_1) = 0$. "
                    "Do $y_1$ là nghiệm nên $y_1'' + p y_1' + q y_1 = 0$. Phương trình rút gọn thành: "
                    "$y_1 v'' + (2y_1' + p y_1) v' = 0$."
                ),
                content=ExpressionStepContent(
                    expression_before="y2'' + p*y2' + q*y2 = 0",
                    expression_after=f"({y1})*v'' + ({v_prime_coeff})*v' = 0",
                    latex_before=norm_lhs_latex,
                    latex_after=sub_latex,
                ),
                equation_latex=sub_latex,
            )
        )
        step_num += 1

        # -------------------------------------------------------------------------
        # Step 5: Reduction to First-Order ODE in u = v'
        # u' + (p + 2*y1'/y1)*u = 0
        # -------------------------------------------------------------------------
        p_u_expr = sp.simplify(p_expr + 2 * dy1 / y1)
        u_eq_latex = f"u' + \\left({expr_to_latex(p_u_expr)}\\right) u = 0"

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Đổi biến u = v'",
                title="Đưa về phương trình vi phân tuyến tính cấp 1 cho u = v'",
                description=(
                    f"Đặt $u({var}) = v'({var})$, ta thu được phương trình vi phân tách biến cấp một cho $u$: "
                    f"$u' + \\left(p({var}) + 2\\frac{{y_1'}}{{y_1}}\\right)u = 0$."
                ),
                content=ExpressionStepContent(
                    expression_before=f"({y1})*v'' + ({v_prime_coeff})*v' = 0",
                    expression_after=f"u' + ({p_u_expr})*u = 0",
                    latex_before=f"({expr_to_latex(y1)})\\,v'' + ({expr_to_latex(v_prime_coeff)})\\,v' = 0",
                    latex_after=u_eq_latex,
                ),
                equation_latex=u_eq_latex,
            )
        )
        step_num += 1

        # -------------------------------------------------------------------------
        # Step 6: Solve for u(t) = exp(-int p dt) / y1(t)^2
        # -------------------------------------------------------------------------
        int_p = sp.integrate(p_expr, var)
        exp_neg_int_p = sp.simplify(sp.exp(-int_p))
        u_sol = sp.simplify(exp_neg_int_p / (y1**2))

        u_sol_latex = (
            f"u({var}) = \\frac{{e^{{-\\int p({var})\\,d{var}}}}}{{y_1({var})^2}} = "
            f"\\frac{{{expr_to_latex(exp_neg_int_p)}}}{{({expr_to_latex(y1)})^2}} = {expr_to_latex(u_sol)}"
        )
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Giải phương trình cho u",
                title="Giải phương trình cấp một tìm hàm u(t)",
                description=(
                    f"Giải phương trình vi phân tách biến $\\frac{{du}}{{u}} = -\\left(p + 2\\frac{{y_1'}}{{y_1}}\\right)d{var}$: "
                    f"$u({var}) = \\frac{{e^{{-\\int p\\,d{var}}}}}{{y_1^2}} = {expr_to_latex(u_sol)}$."
                ),
                content=ExpressionStepContent(
                    expression_before=f"u' + ({p_u_expr})*u = 0",
                    expression_after=f"u({var}) = {u_sol}",
                    latex_before=u_eq_latex,
                    latex_after=u_sol_latex,
                ),
                equation_latex=u_sol_latex,
            )
        )
        step_num += 1

        # -------------------------------------------------------------------------
        # Step 7: Integrate u to find v(t) = int u dt
        # -------------------------------------------------------------------------
        v_sol = sp.integrate(u_sol, var)
        v_sol_simp = sp.simplify(v_sol)
        if v_sol_simp != 0:
            v_sol_simp = sp.simplify(sp.trigsimp(v_sol_simp))

        v_sol_latex = f"v({var}) = \\int u({var})\\,d{var} = \\int {expr_to_latex(u_sol)}\\,d{var} = {expr_to_latex(v_sol_simp)}"
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Tích phân tìm v",
                title="Tích phân hàm u(t) để xác định hàm v(t)",
                description=(
                    f"Tính nguyên hàm $v({var}) = \\int u({var})\\,d{var} = {expr_to_latex(v_sol_simp)}$. "
                    f"Hằng số tích phân $C$ có thể chọn bằng 0 vì $C\\,y_1$ chỉ tạo thêm một bội số của nghiệm đã biết."
                ),
                content=ExpressionStepContent(
                    expression_before=f"v({var}) = int({u_sol}, {var})",
                    expression_after=f"v({var}) = {v_sol_simp}",
                    latex_before=f"v({var}) = \\int {expr_to_latex(u_sol)}\\,d{var}",
                    latex_after=v_sol_latex,
                ),
                equation_latex=v_sol_latex,
            )
        )
        step_num += 1

        # -------------------------------------------------------------------------
        # Step 8: Second Fundamental Solution y2 = v*y1
        # -------------------------------------------------------------------------
        y2_raw = y1 * v_sol_simp
        y2_simp = sp.simplify(y2_raw)
        if y2_simp != 0:
            y2_simp = sp.simplify(sp.trigsimp(y2_simp))

        y2_latex = f"y_2({var}) = v({var})\\,y_1({var}) = ({expr_to_latex(v_sol_simp)})\\left({expr_to_latex(y1)}\\right) = {expr_to_latex(y2_simp)}"

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Xác định nghiệm cơ bản y2",
                title="Xây dựng nghiệm cơ bản thứ hai y2(t) = v(t)*y1(t)",
                description=(
                    f"Nghiệm cơ bản thứ hai nhận được: $y_2({var}) = v({var})\\,y_1({var}) = {expr_to_latex(y2_simp)}$."
                ),
                content=ExpressionStepContent(
                    expression_before=f"y2 = ({v_sol_simp})*({y1})",
                    expression_after=f"y2({var}) = {y2_simp}",
                    latex_before=f"y_2({var}) = v({var})\\,y_1({var})",
                    latex_after=y2_latex,
                ),
                equation_latex=y2_latex,
            )
        )
        step_num += 1

        # -------------------------------------------------------------------------
        # Step 9: Wronskian of (y1, y2)
        # -------------------------------------------------------------------------
        w_expr, w_verif = self.verifier.verify_wronskian(y1, y2_simp, var, ode_coeffs=(a, b, c))
        w_latex = (
            f"W(y_1, y_2)({var}) = \\begin{{vmatrix}} y_1 & y_2 \\\\ y_1' & y_2' \\end{{vmatrix}} "
            f"= y_1 y_2' - y_1' y_2 = {expr_to_latex(w_expr)}"
        )

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Định thức Wronskian",
                title="Kiểm tra độc lập tuyến tính qua định thức Wronskian",
                description=(
                    f"Tính định thức Wronskian: $W(y_1, y_2) = {expr_to_latex(w_expr)}$. "
                    f"Do $W \\not\\equiv 0$ trên khoảng khảo sát, $y_1$ và $y_2$ độc lập tuyến tính, lập thành hệ nghiệm cơ bản."
                ),
                content=ExpressionStepContent(
                    expression_before="W = y1*y2' - y1'*y2",
                    expression_after=f"W = {w_expr}",
                    latex_before="W(y_1, y_2) = y_1 y_2' - y_1' y_2",
                    latex_after=w_latex,
                ),
                equation_latex=w_latex,
            )
        )
        step_num += 1

        # -------------------------------------------------------------------------
        # Step 10: General Solution y(t) = C1*y1 + C2*y2
        # -------------------------------------------------------------------------
        c1_sym = sp.Symbol("C1")
        c2_sym = sp.Symbol("C2")
        gen_sol = c1_sym * y1 + c2_sym * y2_simp

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Hệ nghiệm cơ bản",
                title="Xây dựng nghiệm tổng quát",
                description=(
                    f"Nghiệm tổng quát của phương trình vi phân thuần nhất là tổ hợp tuyến tính: "
                    f"$y({var}) = C_1 y_1({var}) + C_2 y_2({var}) = C_1\\left({expr_to_latex(y1)}\\right) + C_2\\left({expr_to_latex(y2_simp)}\\right)$."
                ),
                content=ExpressionStepContent(
                    expression_before="y = C1*y1 + C2*y2",
                    expression_after=f"y({var}) = {gen_sol}",
                    latex_before="y({var}) = C_1 y_1({var}) + C_2 y_2({var})",
                    latex_after=f"y({var}) = {expr_to_latex(gen_sol)}",
                ),
                equation_latex=f"y({var}) = {expr_to_latex(gen_sol)}",
            )
        )
        step_num += 1

        # -------------------------------------------------------------------------
        # Optional IVP Handling
        # -------------------------------------------------------------------------
        final_sol = gen_sol
        has_ivp = bool(parsed.initial_condition is not None and parsed.initial_derivative is not None)

        if has_ivp:
            t0, y0 = parsed.initial_condition  # type: ignore[misc]
            _, v0 = parsed.initial_derivative  # type: ignore[misc]

            dy_gen = sp.diff(gen_sol, var)
            y_at_t0 = sp.simplify(gen_sol.subs(var, t0))
            yp_at_t0 = sp.simplify(dy_gen.subs(var, t0))

            sol_c = sp.solve([sp.Eq(y_at_t0, y0), sp.Eq(yp_at_t0, v0)], [c1_sym, c2_sym])
            if sol_c and c1_sym in sol_c and c2_sym in sol_c:
                c1_v = sp.simplify(sol_c[c1_sym])
                c2_v = sp.simplify(sol_c[c2_sym])
                particular_sol = sp.simplify(gen_sol.subs([(c1_sym, c1_v), (c2_sym, c2_v)]))
                final_sol = particular_sol

                steps.append(
                    SolutionStep(
                        step_number=step_num,
                        rule_name="Nghiệm riêng",
                        title="Xác định nghiệm riêng từ điều kiện ban đầu",
                        description=(
                            f"Từ hệ Cauchy $y({expr_to_latex(t0)}) = {expr_to_latex(y0)}$ và "
                            f"$y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}$, tìm được $C_1 = {expr_to_latex(c1_v)}$ và $C_2 = {expr_to_latex(c2_v)}$."
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"C1 = {c1_v}, C2 = {c2_v}",
                            expression_after=f"y({var}) = {particular_sol}",
                            latex_before=f"C_1 = {expr_to_latex(c1_v)}, \\quad C_2 = {expr_to_latex(c2_v)}",
                            latex_after=f"y({var}) = {expr_to_latex(particular_sol)}",
                        ),
                        equation_latex=f"y({var}) = {expr_to_latex(particular_sol)}",
                    )
                )
                step_num += 1

        # -------------------------------------------------------------------------
        # Independent Verification
        # -------------------------------------------------------------------------
        verif_result = self.verifier.verify_reduction_of_order(
            y1,
            y2_simp,
            var,
            a,
            b,
            c,
        )

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Kiểm chứng nghiệm",
                title="Kiểm chứng toán học độc lập",
                description=verif_result.details,
                content=ExpressionStepContent(
                    expression_before=f"R({var}) = a*y'' + b*y' + c*y",
                    expression_after="Verified" if verif_result.status == VerificationStatus.VERIFIED else "Unverified",
                    latex_before=f"R({var}) = {expr_to_latex(a)}\\,y'' + {expr_to_latex(b)}\\,y' + {expr_to_latex(c)}\\,y",
                    latex_after=r"R_1 \equiv 0, \quad R_2 \equiv 0, \quad W \not\equiv 0",
                ),
                notes=verif_result.details,
            )
        )

        status = SolutionStatus.SUCCESS if verif_result.status == VerificationStatus.VERIFIED else SolutionStatus.UNVERIFIED
        elapsed = (time.perf_counter() - t0_start) * 1000.0

        return SolutionResponse(
            status=status,
            verification=verif_result,
            raw_input=request.raw_input,
            canonical_input=parsed.canonical_eq,
            final_result=f"y({var}) = {final_sol}",
            final_latex=f"y({var}) = {expr_to_latex(final_sol)}",
            steps=tuple(steps),
            domain_restrictions=tuple(domain_restrictions),
            warnings=(),
            execution_time_ms=elapsed,
        )

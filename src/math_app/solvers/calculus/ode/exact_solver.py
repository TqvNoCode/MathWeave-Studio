"""Exact ordinary differential equations solver: M(x, y) dx + N(x, y) dy = 0."""

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
from math_app.verification.calculus.ode_verifier import ODEVerifier


class ODEExactSolver(Solver):
    """Solver for exact differential equations: M(x, y) dx + N(x, y) dy = 0."""

    def __init__(self, verifier: ODEVerifier | None = None) -> None:
        self.verifier = verifier or ODEVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type in (
            ProblemType.ODE_EXACT,
            ProblemType.SOLVE_EQUATION,
        )

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        t0_start = time.perf_counter()
        raw = request.raw_input.strip()
        if not raw:
            raise InvalidInputError("Phương trình vi phân không được để trống (Equation cannot be empty).")

        parsed: ParsedODE = parse_ode_input(
            raw,
            target_variable=request.target_variable,
            parameters=dict(request.parameters),
        )

        x_var = parsed.independent_var
        y_var = parsed.dependent_var
        yp_sym = sp.Symbol("y_prime")

        # Standard form: M(x, y) + N(x, y)*y' = 0
        expanded_std = sp.expand(parsed.standard_expr)
        N_cand = expanded_std.coeff(yp_sym, 1)
        M_cand = expanded_std.coeff(yp_sym, 0)

        if N_cand == 0:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="exactness_form_check",
                    details="Phương trình không có đạo hàm y' (hệ số N(x, y) = 0).",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=("Không tìm thấy thành phần N(x, y)*dy trong phương trình.",),
                execution_time_ms=elapsed,
            )

        M_expr = sp.simplify(M_cand)
        N_expr = sp.simplify(N_cand)

        steps: list[SolutionStep] = []
        step_num = 1
        domain_restrictions: list[str] = []

        # Track denominator restrictions
        try:
            _, m_denom = sp.fraction(M_expr)
            if m_denom != 1 and (x_var in m_denom.free_symbols or y_var in m_denom.free_symbols):
                domain_restrictions.append(f"Điều kiện xác định của M({x_var}, {y_var}): {m_denom} khác 0.")
        except Exception:
            pass
        try:
            _, n_denom = sp.fraction(N_expr)
            if n_denom != 1 and (x_var in n_denom.free_symbols or y_var in n_denom.free_symbols):
                domain_restrictions.append(f"Điều kiện xác định của N({x_var}, {y_var}): {n_denom} khác 0.")
        except Exception:
            pass

        # Check exactness: dM/dy == dN/dx
        dM_dy = sp.simplify(sp.diff(M_expr, y_var))
        dN_dx = sp.simplify(sp.diff(N_expr, x_var))
        exactness_diff = sp.simplify(dM_dy - dN_dx)

        if exactness_diff != 0:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="exactness_condition_failed",
                    details=f"dM/d{y_var} = {dM_dy} != dN/d{x_var} = {dN_dx}.",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=(
                    f"Phương trình không phải là phương trình vi phân toàn phần vì "
                    f"dM/d{y_var} = {dM_dy} khác dN/d{x_var} = {dN_dx} (Equation is not exact).",
                ),
                execution_time_ms=elapsed,
            )

        # Step 1: Verification of exactness condition
        check_latex = (
            f"\\frac{{\\partial M}}{{\\partial {y_var}}} = {expr_to_latex(dM_dy)}, \\quad "
            f"\\frac{{\\partial N}}{{\\partial {x_var}}} = {expr_to_latex(dN_dx)}"
        )
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Kiểm tra tính vi phân toàn phần",
                title="Kiểm tra điều kiện vi phân toàn phần (Exactness Condition)",
                description=(
                    f"Xác định M({x_var}, {y_var}) = {M_expr} và N({x_var}, {y_var}) = {N_expr}. "
                    f"Tính các đạo hàm riêng: dM/d{y_var} = {dM_dy} và dN/d{x_var} = {dN_dx}. "
                    f"Vì dM/d{y_var} = dN/d{x_var}, phương trình là vi phân toàn phần."
                ),
                content=ExpressionStepContent(
                    expression_before=f"M = {M_expr}, N = {N_expr}",
                    expression_after=f"dM/d{y_var} = {dM_dy} == dN/d{x_var} = {dN_dx}",
                    latex_before=f"M({x_var}, {y_var}) = {expr_to_latex(M_expr)}, \\quad N({x_var}, {y_var}) = {expr_to_latex(N_expr)}",
                    latex_after=check_latex,
                ),
            )
        )
        step_num += 1

        # Step 2: Integrate M(x, y) with respect to x: Psi(x, y) = int(M dx)
        psi_expr = sp.simplify(sp.integrate(M_expr, x_var))
        psi_latex = f"\\Psi({x_var}, {y_var}) = \\int \\left( {expr_to_latex(M_expr)} \\right) d{x_var} = {expr_to_latex(psi_expr)}"

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Tích phân hai vế",
                title=f"Tích phân hàm M({x_var}, {y_var}) theo biến {x_var}",
                description=(
                    f"Lấy nguyên hàm của M theo biến {x_var} (coi {y_var} là hằng số): "
                    f"Psi({x_var}, {y_var}) = int({M_expr}) d{x_var} = {psi_expr} + h({y_var})."
                ),
                content=ExpressionStepContent(
                    expression_before=f"int({M_expr}) d{x_var}",
                    expression_after=f"Psi = {psi_expr} + h({y_var})",
                    latex_before=f"\\int M({x_var}, {y_var})\\,d{x_var}",
                    latex_after=f"{psi_latex} + h({y_var})",
                ),
            )
        )
        step_num += 1

        # Step 3: Find h(y): dPsi/dy + h'(y) = N => h'(y) = N - dPsi/dy
        dpsi_dy = sp.simplify(sp.diff(psi_expr, y_var))
        h_prime = sp.simplify(N_expr - dpsi_dy)

        # Verify h_prime is independent of x
        if x_var in h_prime.free_symbols:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.ERROR,
                verification=VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="exact_potential_construction",
                    details="h'(y) vẫn phụ thuộc vào biến x; vi phạm tính giải tích.",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=("Không thể xây dựng hàm thế do sai lệch trong tích phân.",),
                execution_time_ms=elapsed,
            )

        h_expr = sp.simplify(sp.integrate(h_prime, y_var))
        h_latex = f"h'({y_var}) = {expr_to_latex(h_prime)} \\implies h({y_var}) = {expr_to_latex(h_expr)}"

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Xác định hệ số",
                title=f"Xác định hàm số phụ h({y_var})",
                description=(
                    f"Đạo hàm riêng theo {y_var}: dPsi/d{y_var} = {dpsi_dy}. "
                    f"So sánh với N({x_var}, {y_var}) ta có: h'({y_var}) = N - dPsi/d{y_var} = {h_prime}. "
                    f"Tích phân theo {y_var} suy ra: h({y_var}) = {h_expr}."
                ),
                content=ExpressionStepContent(
                    expression_before=f"h'({y_var}) = {N_expr} - ({dpsi_dy})",
                    expression_after=f"h({y_var}) = {h_expr}",
                    latex_before=f"h'({y_var}) = N({x_var}, {y_var}) - \\frac{{\\partial \\Psi}}{{\\partial {y_var}}}",
                    latex_after=h_latex,
                ),
            )
        )
        step_num += 1

        # Step 4: Construct potential function F(x, y) = Psi + h
        potential_F = sp.expand(psi_expr + h_expr)
        potential_latex = f"F({x_var}, {y_var}) = {expr_to_latex(potential_F)}"

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Xây dựng hàm thế",
                title="Xây dựng hàm thế vi phân toàn phần F(x, y)",
                description=(
                    f"Hàm thế vi phân toàn phần là F({x_var}, {y_var}) = Psi({x_var}, {y_var}) + h({y_var}) = {potential_F}. "
                    f"Nghiệm tổng quát của phương trình là F({x_var}, {y_var}) = C."
                ),
                content=ExpressionStepContent(
                    expression_before=f"F = ({psi_expr}) + ({h_expr})",
                    expression_after=f"F({x_var}, {y_var}) = {potential_F} = C",
                    latex_before=f"F({x_var}, {y_var}) = \\Psi({x_var}, {y_var}) + h({y_var})",
                    latex_after=f"{potential_latex} = C",
                ),
            )
        )
        step_num += 1

        final_sol_str = f"{potential_F} = C"
        final_latex_sol = f"{expr_to_latex(potential_F)} = C"

        # Step 5: Initial condition if provided
        if parsed.initial_condition is not None:
            x0, y0 = parsed.initial_condition
            c_val = sp.simplify(potential_F.subs([(x_var, x0), (y_var, y0)]))
            part_latex = f"{expr_to_latex(potential_F)} = {expr_to_latex(c_val)}"

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Áp dụng điều kiện ban đầu",
                    title="Xác định hằng số C từ điều kiện ban đầu",
                    description=(
                        f"Thay {x_var} = {x0} và {y_var} = {y0} vào hàm thế: "
                        f"C = F({x0}, {y0}) = {c_val} => Nghiệm riêng: {potential_F} = {c_val}."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"C = F({x0}, {y0})",
                        expression_after=f"{potential_F} = {c_val}",
                        latex_before=f"C = F({expr_to_latex(x0)}, {expr_to_latex(y0)})",
                        latex_after=part_latex,
                    ),
                )
            )
            step_num += 1
            final_sol_str = f"{potential_F} = {c_val}"
            final_latex_sol = part_latex

        # Verification of exactness potential gradient
        verif_res = self.verifier.verify_exact(
            potential_F=potential_F,
            M_expr=M_expr,
            N_expr=N_expr,
            x_sym=x_var,
            y_sym=y_var,
            initial_condition=parsed.initial_condition,
        )

        # Determine overall solution status
        warnings_list: list[str] = []
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
            final_result=final_sol_str,
            final_latex=final_latex_sol,
            steps=tuple(steps),
            domain_restrictions=tuple(domain_restrictions),
            warnings=tuple(warnings_list),
            execution_time_ms=elapsed,
        )

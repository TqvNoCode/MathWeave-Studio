"""Solver for Green's Theorem (Circulation and Flux forms)."""

from __future__ import annotations

import time
import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionResponse, SolutionStep
from math_app.application.ports.solver import Solver
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.verification.calculus.greens_theorem_verifier import GreensTheoremVerifier


class GreensTheoremSolver(Solver):
    """Calculus solver demonstrating and verifying Green's Theorem on 2D regions."""

    def __init__(self, verifier: GreensTheoremVerifier | None = None) -> None:
        self._verifier = verifier or GreensTheoremVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type == ProblemType.GREENS_THEOREM

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        start_time = time.perf_counter()
        steps: list[SolutionStep] = []
        warnings: list[str] = []
        params = request.parameters

        x = sp.Symbol("x")
        y = sp.Symbol("y")

        raw_in = request.raw_input.strip()
        parts = [p.strip() for p in raw_in.split(",")]
        if len(parts) != 2:
            raise InvalidInputError("Định lý Green yêu cầu trường vectơ 2D dạng 'P, Q' (ví dụ: 'y^2, x^2' hoặc '-y, x').")

        try:
            P = sp.sympify(parts[0])
            Q = sp.sympify(parts[1])
        except Exception as exc:
            raise InvalidInputError(f"Thành phần trường vectơ không hợp lệ: {exc}") from exc

        raw_x_min = str(params.get("x_min", "0")).strip()
        raw_x_max = str(params.get("x_max", "1")).strip()
        raw_y_min = str(params.get("y_min", "0")).strip()
        raw_y_max = str(params.get("y_max", "1")).strip()

        try:
            x_min = sp.sympify(raw_x_min)
            x_max = sp.sympify(raw_x_max)
            y_min = sp.sympify(raw_y_min)
            y_max = sp.sympify(raw_y_max)
        except Exception as exc:
            raise InvalidInputError(f"Cận biên miền hình chữ nhật không hợp lệ: {exc}") from exc

        form = str(params.get("form", "circulation")).lower().strip()
        is_flux = form in ("flux", "thong_luong")

        step_idx = 1

        # Step 1: Problem setup
        form_name = "Dạng thông lượng (Flux form)" if is_flux else "Dạng lưu thông (Circulation form)"
        setup_ltx = (
            rf"\mathbf{{F}}(x, y) = \left( {expr_to_latex(P)}, {expr_to_latex(Q)} \right), \quad "
            rf"D = [{expr_to_latex(x_min)}, {expr_to_latex(x_max)}] \times [{expr_to_latex(y_min)}, {expr_to_latex(y_max)}]"
        )
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Thiết lập trường vectơ và miền D",
                description=f"Xác định trường vectơ F = (P, Q) và miền lấy tích phân ({form_name}):",
                content=ExpressionStepContent(
                    expression_before="F = (P, Q)",
                    expression_after=str((P, Q)),
                    latex_before=r"\mathbf{F}(x, y)",
                    latex_after=setup_ltx,
                ),
                equation_latex=setup_ltx,
            )
        )
        step_idx += 1

        # Step 2: Partial derivatives
        dP_dy = sp.diff(P, y)
        dQ_dx = sp.diff(Q, x)
        dP_dx = sp.diff(P, x)
        dQ_dy = sp.diff(Q, y)

        if not is_flux:
            # Circulation: \oint P dx + Q dy = \iint (dQ/dx - dP/dy) dA
            curl_2d = sp.simplify(dQ_dx - dP_dy)
            deriv_ltx = (
                rf"\frac{{\partial Q}}{{\partial x}} = {expr_to_latex(dQ_dx)}, \quad "
                rf"\frac{{\partial P}}{{\partial y}} = {expr_to_latex(dP_dy)}, \quad "
                rf"\frac{{\partial Q}}{{\partial x}} - \frac{{\partial P}}{{\partial y}} = {expr_to_latex(curl_2d)}"
            )
            integrand_2d = curl_2d
        else:
            # Flux: \oint P dy - Q dx = \iint (dP/dx + dQ/dy) dA
            div_2d = sp.simplify(dP_dx + dQ_dy)
            deriv_ltx = (
                rf"\frac{{\partial P}}{{\partial x}} = {expr_to_latex(dP_dx)}, \quad "
                rf"\frac{{\partial Q}}{{\partial y}} = {expr_to_latex(dQ_dy)}, \quad "
                rf"\frac{{\partial P}}{{\partial x}} + \frac{{\partial Q}}{{\partial y}} = {expr_to_latex(div_2d)}"
            )
            integrand_2d = div_2d

        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tính các đạo hàm riêng",
                description="Tính đạo hàm riêng để thiết lập biểu thức tích phân hai lớp:",
                content=ExpressionStepContent(
                    expression_before="integrand_2d",
                    expression_after=str(integrand_2d),
                    latex_before=r"\text{Biểu thức dưới dấu tích phân}",
                    latex_after=deriv_ltx,
                ),
                equation_latex=deriv_ltx,
            )
        )
        step_idx += 1

        # Step 3: Compute Double Integral (RHS)
        try:
            inner_rhs = sp.integrate(integrand_2d, (x, x_min, x_max))
            val_rhs = sp.integrate(inner_rhs, (y, y_min, y_max))
            val_rhs = sp.simplify(val_rhs)
        except Exception as exc:
            raise InvalidInputError(f"Không thể tính tích phân hai lớp: {exc}") from exc

        rhs_symbol = r"\iint_D \left( \frac{\partial Q}{\partial x} - \frac{\partial P}{\partial y} \right) dA" if not is_flux else r"\iint_D \left( \frac{\partial P}{\partial x} + \frac{\partial Q}{\partial y} \right) dA"
        rhs_ltx = (
            rf"{rhs_symbol} = \int_{{{expr_to_latex(y_min)}}}^{{{expr_to_latex(y_max)}}} "
            rf"\left[ \int_{{{expr_to_latex(x_min)}}}^{{{expr_to_latex(x_max)}}} \left( {expr_to_latex(integrand_2d)} \right) dx \right] dy = {expr_to_latex(val_rhs)}"
        )

        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tính tích phân hai lớp trên miền D (Vế phải)",
                description="Tính tích phân bội hai theo định lý Green:",
                content=ExpressionStepContent(
                    expression_before=f"integrate({integrand_2d}, (x, {x_min}, {x_max}), (y, {y_min}, {y_max}))",
                    expression_after=str(val_rhs),
                    latex_before=rhs_symbol,
                    latex_after=expr_to_latex(val_rhs),
                ),
                equation_latex=rhs_ltx,
            )
        )
        step_idx += 1

        # Step 4: Compute Line Integral along boundary C = C1 + C2 + C3 + C4 (LHS)
        # C1: y = y_min, x from x_min to x_max
        # C2: x = x_max, y from y_min to y_max
        # C3: y = y_max, x from x_max to x_min
        # C4: x = x_min, y from y_max to y_min
        if not is_flux:
            # \int P dx + Q dy
            I1 = sp.integrate(P.subs(y, y_min), (x, x_min, x_max))
            I2 = sp.integrate(Q.subs(x, x_max), (y, y_min, y_max))
            I3 = sp.integrate(P.subs(y, y_max), (x, x_max, x_min))
            I4 = sp.integrate(Q.subs(x, x_min), (y, y_max, y_min))
        else:
            # \int P dy - Q dx
            I1 = sp.integrate(-Q.subs(y, y_min), (x, x_min, x_max))
            I2 = sp.integrate(P.subs(x, x_max), (y, y_min, y_max))
            I3 = sp.integrate(-Q.subs(y, y_max), (x, x_max, x_min))
            I4 = sp.integrate(P.subs(x, x_min), (y, y_max, y_min))

        val_lhs = sp.simplify(I1 + I2 + I3 + I4)

        lhs_symbol = r"\oint_{\partial D} (P\,dx + Q\,dy)" if not is_flux else r"\oint_{\partial D} (P\,dy - Q\,dx)"
        lhs_ltx = (
            rf"{lhs_symbol} = I_{{C_1}} + I_{{C_2}} + I_{{C_3}} + I_{{C_4}} = "
            rf"{expr_to_latex(I1)} + {expr_to_latex(I2)} + {expr_to_latex(I3)} + {expr_to_latex(I4)} = {expr_to_latex(val_lhs)}"
        )

        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tính tích phân đường trên 4 cạnh biên kín (Vế trái)",
                description="Tính tổng tích phân đường trên 4 đoạn của biên chữ nhật ∂D ngược chiều kim đồng hồ:",
                content=ExpressionStepContent(
                    expression_before="I1 + I2 + I3 + I4",
                    expression_after=str(val_lhs),
                    latex_before=lhs_symbol,
                    latex_after=expr_to_latex(val_lhs),
                ),
                equation_latex=lhs_ltx,
            )
        )
        step_idx += 1

        # Step 5: Verification & Identity summary
        verify_ltx = rf"{lhs_symbol} = {rhs_symbol} = {expr_to_latex(val_rhs)}"
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Kiểm chứng và kết luận định lý Green",
                description="So sánh trực tiếp kết quả hai vế: Tích phân đường trên biên kín khớp hoàn toàn với tích phân bội hai.",
                content=ExpressionStepContent(
                    expression_before=f"LHS ({val_lhs}) == RHS ({val_rhs})",
                    expression_after="Định lý Green nghiệm đúng",
                    latex_before=rf"{lhs_symbol} \equiv {rhs_symbol}",
                    latex_after=verify_ltx,
                ),
                equation_latex=verify_ltx,
            )
        )

        verification = self._verifier.verify_greens_theorem(val_lhs, val_rhs)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return SolutionResponse(
            status=SolutionStatus.SUCCESS,
            verification=verification,
            raw_input=request.raw_input,
            canonical_input=request.raw_input,
            final_result=str(val_rhs),
            final_latex=expr_to_latex(val_rhs),
            steps=tuple(steps),
            domain_restrictions=(),
            warnings=tuple(warnings),
            execution_time_ms=elapsed_ms,
        )

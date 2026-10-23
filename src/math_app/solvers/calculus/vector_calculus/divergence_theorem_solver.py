"""Solver demonstrating and verifying the Divergence (Gauss–Ostrogradsky) Theorem."""

from __future__ import annotations

import time
import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionResponse, SolutionStep
from math_app.application.ports.solver import Solver
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.input.parser import parse_safe_expression
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.verification.calculus.divergence_theorem_verifier import DivergenceTheoremVerifier


class DivergenceTheoremSolver(Solver):
    """Calculus solver verifying the Divergence Theorem: iiint_V (div F) dV = iint_dS F.dS."""

    def __init__(self, verifier: DivergenceTheoremVerifier | None = None) -> None:
        self._verifier = verifier or DivergenceTheoremVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type == ProblemType.DIVERGENCE_THEOREM

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        start_time = time.perf_counter()
        steps: list[SolutionStep] = []
        warnings: list[str] = []
        params = request.parameters

        x = sp.Symbol("x")
        y = sp.Symbol("y")
        z = sp.Symbol("z")

        raw_in = request.raw_input.strip()
        parts = [p.strip() for p in raw_in.split(",")]
        if len(parts) != 3:
            raise InvalidInputError("Định lý Divergence yêu cầu trường vectơ 3D dạng 'P, Q, R' (ví dụ: 'x, y, z' hoặc 'x^2, y^2, z^2').")

        try:
            allowed_xyz = {"x", "y", "z"}
            P = parse_safe_expression(parts[0], allowed_variables=allowed_xyz, evaluate=True)
            Q = parse_safe_expression(parts[1], allowed_variables=allowed_xyz, evaluate=True)
            R = parse_safe_expression(parts[2], allowed_variables=allowed_xyz, evaluate=True)
        except Exception as exc:
            raise InvalidInputError(f"Thành phần trường vectơ không hợp lệ: {exc}") from exc

        raw_x_min = str(params.get("x_min", "0")).strip()
        raw_x_max = str(params.get("x_max", "1")).strip()
        raw_y_min = str(params.get("y_min", "0")).strip()
        raw_y_max = str(params.get("y_max", "1")).strip()
        raw_z_min = str(params.get("z_min", "0")).strip()
        raw_z_max = str(params.get("z_max", "1")).strip()

        try:
            x_min = parse_safe_expression(raw_x_min, evaluate=True)
            x_max = parse_safe_expression(raw_x_max, evaluate=True)
            y_min = parse_safe_expression(raw_y_min, evaluate=True)
            y_max = parse_safe_expression(raw_y_max, evaluate=True)
            z_min = parse_safe_expression(raw_z_min, evaluate=True)
            z_max = parse_safe_expression(raw_z_max, evaluate=True)
        except Exception as exc:
            raise InvalidInputError(f"Cận khối hộp V không hợp lệ: {exc}") from exc

        step_idx = 1

        # Step 1: Problem setup
        setup_ltx = (
            rf"\mathbf{{F}}(x, y, z) = \left( {expr_to_latex(P)}, {expr_to_latex(Q)}, {expr_to_latex(R)} \right), \quad "
            rf"V = [{expr_to_latex(x_min)}, {expr_to_latex(x_max)}] \times [{expr_to_latex(y_min)}, {expr_to_latex(y_max)}] \times [{expr_to_latex(z_min)}, {expr_to_latex(z_max)}]"
        )
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Thiết lập trường vectơ và khối hộp V",
                description="Xác định trường vectơ F = (P, Q, R) và miền thể tích 3 chiều V với mặt biên kín định hướng ra ngoài:",
                content=ExpressionStepContent(
                    expression_before="F = (P, Q, R)",
                    expression_after=str((P, Q, R)),
                    latex_before=r"\mathbf{F}(x, y, z)",
                    latex_after=setup_ltx,
                ),
                equation_latex=setup_ltx,
            )
        )
        step_idx += 1

        # Step 2: Divergence calculation
        dP_dx = sp.diff(P, x)
        dQ_dy = sp.diff(Q, y)
        dR_dz = sp.diff(R, z)
        div_F = sp.simplify(dP_dx + dQ_dy + dR_dz)

        div_ltx = (
            rf"\nabla \cdot \mathbf{{F}} = \frac{{\partial P}}{{\partial x}} + \frac{{\partial Q}}{{\partial y}} + \frac{{\partial R}}{{\partial z}} = "
            rf"{expr_to_latex(dP_dx)} + {expr_to_latex(dQ_dy)} + {expr_to_latex(dR_dz)} = {expr_to_latex(div_F)}"
        )
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tính độ phân kỳ (Divergence)",
                description="Tính độ phân kỳ div(F) = ∇ · F:",
                content=ExpressionStepContent(
                    expression_before="div(F)",
                    expression_after=str(div_F),
                    latex_before=r"\nabla \cdot \mathbf{F}",
                    latex_after=div_ltx,
                ),
                equation_latex=div_ltx,
            )
        )
        step_idx += 1

        # Step 3: Compute Triple Integral of div F (RHS)
        try:
            int_x = sp.integrate(div_F, (x, x_min, x_max))
            int_y = sp.integrate(int_x, (y, y_min, y_max))
            val_rhs = sp.integrate(int_y, (z, z_min, z_max))
            val_rhs = sp.simplify(val_rhs)
        except Exception as exc:
            raise InvalidInputError(f"Không thể tính tích phân bội ba của div F: {exc}") from exc

        rhs_ltx = (
            rf"\iiint_V (\nabla \cdot \mathbf{{F}})\,dV = "
            rf"\int_{{{expr_to_latex(z_min)}}}^{{{expr_to_latex(z_max)}}} \int_{{{expr_to_latex(y_min)}}}^{{{expr_to_latex(y_max)}}} \int_{{{expr_to_latex(x_min)}}}^{{{expr_to_latex(x_max)}}} "
            rf"\left( {expr_to_latex(div_F)} \right) dx\,dy\,dz = {expr_to_latex(val_rhs)}"
        )
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tính tích phân bội ba của div F trên khối V (Vế phải)",
                description="Tính tích phân thể tích theo định lý Gauss–Ostrogradsky:",
                content=ExpressionStepContent(
                    expression_before=f"integrate({div_F})",
                    expression_after=str(val_rhs),
                    latex_before=r"\iiint_V (\nabla \cdot \mathbf{F})\,dV",
                    latex_after=expr_to_latex(val_rhs),
                ),
                equation_latex=rhs_ltx,
            )
        )
        step_idx += 1

        # Step 4: Compute Total Outward Flux through 6 boundary faces (LHS)
        # Face 1 (x = x_max, n = +i): P(x_max, y, z)
        flux_x2 = sp.integrate(sp.integrate(P.subs(x, x_max), (y, y_min, y_max)), (z, z_min, z_max))
        # Face 2 (x = x_min, n = -i): -P(x_min, y, z)
        flux_x1 = -sp.integrate(sp.integrate(P.subs(x, x_min), (y, y_min, y_max)), (z, z_min, z_max))

        # Face 3 (y = y_max, n = +j): Q(x, y_max, z)
        flux_y2 = sp.integrate(sp.integrate(Q.subs(y, y_max), (x, x_min, x_max)), (z, z_min, z_max))
        # Face 4 (y = y_min, n = -j): -Q(x, y_min, z)
        flux_y1 = -sp.integrate(sp.integrate(Q.subs(y, y_min), (x, x_min, x_max)), (z, z_min, z_max))

        # Face 5 (z = z_max, n = +k): R(x, y, z_max)
        flux_z2 = sp.integrate(sp.integrate(R.subs(z, z_max), (x, x_min, x_max)), (y, y_min, y_max))
        # Face 6 (z = z_min, n = -k): -R(x, y, z_min)
        flux_z1 = -sp.integrate(sp.integrate(R.subs(z, z_min), (x, x_min, x_max)), (y, y_min, y_max))

        flux_x = sp.simplify(flux_x2 + flux_x1)
        flux_y = sp.simplify(flux_y2 + flux_y1)
        flux_z = sp.simplify(flux_z2 + flux_z1)
        val_lhs = sp.simplify(flux_x + flux_y + flux_z)

        lhs_ltx = (
            rf"\iint_{{\partial V}} \mathbf{{F}} \cdot d\mathbf{{S}} = "
            rf"\Phi_{{x}} + \Phi_{{y}} + \Phi_{{z}} = "
            rf"{expr_to_latex(flux_x)} + {expr_to_latex(flux_y)} + {expr_to_latex(flux_z)} = {expr_to_latex(val_lhs)}"
        )
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tính tổng thông lượng qua 6 mặt biên kín (Vế trái)",
                description="Tính tổng thông lượng hướng ra ngoài qua các cặp mặt biên (x = c, y = c, z = c):",
                content=ExpressionStepContent(
                    expression_before="Phi_x + Phi_y + Phi_z",
                    expression_after=str(val_lhs),
                    latex_before=r"\iint_{\partial V} \mathbf{F} \cdot d\mathbf{S}",
                    latex_after=expr_to_latex(val_lhs),
                ),
                equation_latex=lhs_ltx,
            )
        )
        step_idx += 1

        # Step 5: Verification & Identity conclusion
        verify_ltx = rf"\iint_{{\partial V}} \mathbf{{F}} \cdot d\mathbf{{S}} = \iiint_V (\nabla \cdot \mathbf{{F}})\,dV = {expr_to_latex(val_rhs)}"
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Kiểm chứng và kết luận định lý Divergence",
                description="Đối chiếu kết quả hai vế: Thông lượng trường vectơ qua toàn bộ mặt kín bằng chính xác tích phân độ phân kỳ trên toàn khối.",
                content=ExpressionStepContent(
                    expression_before=f"LHS ({val_lhs}) == RHS ({val_rhs})",
                    expression_after="Định lý Divergence nghiệm đúng",
                    latex_before=r"\iint_{\partial V} \mathbf{F} \cdot d\mathbf{S} \equiv \iiint_V (\nabla \cdot \mathbf{F})\,dV",
                    latex_after=verify_ltx,
                ),
                equation_latex=verify_ltx,
            )
        )

        verification = self._verifier.verify_divergence_theorem(val_lhs, val_rhs)
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

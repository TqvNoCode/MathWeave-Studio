"""Solver demonstrating and verifying Stokes' Theorem."""

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
from math_app.verification.calculus.stokes_theorem_verifier import StokesTheoremVerifier


class StokesTheoremSolver(Solver):
    """Calculus solver demonstrating and verifying Stokes' Theorem: oint_C F.dr = iint_S (curl F).dS."""

    def __init__(self, verifier: StokesTheoremVerifier | None = None) -> None:
        self._verifier = verifier or StokesTheoremVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type == ProblemType.STOKES_THEOREM

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
            raise InvalidInputError("Định lý Stokes yêu cầu trường vectơ 3D dạng 'P, Q, R' (ví dụ: 'y, z, x' hoặc '2*y, 3*z, -x').")

        try:
            allowed_xyz = {"x", "y", "z"}
            P = parse_safe_expression(parts[0], allowed_variables=allowed_xyz, evaluate=True)
            Q = parse_safe_expression(parts[1], allowed_variables=allowed_xyz, evaluate=True)
            R = parse_safe_expression(parts[2], allowed_variables=allowed_xyz, evaluate=True)
        except Exception as exc:
            raise InvalidInputError(f"Thành phần trường vectơ không hợp lệ: {exc}") from exc

        raw_surf = str(params.get("surface_expr", "0")).strip()
        try:
            g_xy = parse_safe_expression(raw_surf, allowed_variables={"x", "y"}, evaluate=True)
        except Exception as exc:
            raise InvalidInputError(f"Hàm mặt cong z = g(x, y) không hợp lệ: {exc}") from exc

        raw_x_min = str(params.get("x_min", "0")).strip()
        raw_x_max = str(params.get("x_max", "1")).strip()
        raw_y_min = str(params.get("y_min", "0")).strip()
        raw_y_max = str(params.get("y_max", "1")).strip()

        try:
            x_min = parse_safe_expression(raw_x_min, evaluate=True)
            x_max = parse_safe_expression(raw_x_max, evaluate=True)
            y_min = parse_safe_expression(raw_y_min, evaluate=True)
            y_max = parse_safe_expression(raw_y_max, evaluate=True)
        except Exception as exc:
            raise InvalidInputError(f"Cận biên miền không hợp lệ: {exc}") from exc

        step_idx = 1

        # Step 1: Problem setup
        setup_ltx = (
            rf"\mathbf{{F}}(x, y, z) = \left( {expr_to_latex(P)}, {expr_to_latex(Q)}, {expr_to_latex(R)} \right), \quad "
            rf"S: z = g(x, y) = {expr_to_latex(g_xy)}, \quad (x, y) \in [{expr_to_latex(x_min)}, {expr_to_latex(x_max)}] \times [{expr_to_latex(y_min)}, {expr_to_latex(y_max)}]"
        )
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Thiết lập trường vectơ và mặt cong S",
                description="Xác định trường vectơ F = (P, Q, R), mặt cong S với pháp vectơ hướng lên và biên định hướng ∂S:",
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

        # Step 2: Curl of F
        curl_x = sp.simplify(sp.diff(R, y) - sp.diff(Q, z))
        curl_y = sp.simplify(sp.diff(P, z) - sp.diff(R, x))
        curl_z = sp.simplify(sp.diff(Q, x) - sp.diff(P, y))

        curl_ltx = (
            rf"\nabla \times \mathbf{{F}} = \left| \begin{{matrix}} \mathbf{{i}} & \mathbf{{j}} & \mathbf{{k}} \\ "
            rf"\frac{{\partial}}{{\partial x}} & \frac{{\partial}}{{\partial y}} & \frac{{\partial}}{{\partial z}} \\ "
            rf"P & Q & R \end{{matrix}} \right| = \left( {expr_to_latex(curl_x)}, {expr_to_latex(curl_y)}, {expr_to_latex(curl_z)} \right)"
        )
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tính curl của trường vectơ",
                description="Tính vectơ xoáy curl(F) = ∇ × F:",
                content=ExpressionStepContent(
                    expression_before="curl(F)",
                    expression_after=str((curl_x, curl_y, curl_z)),
                    latex_before=r"\nabla \times \mathbf{F}",
                    latex_after=curl_ltx,
                ),
                equation_latex=curl_ltx,
            )
        )
        step_idx += 1

        # Step 3: Compute Surface Integral of curl F (RHS)
        gx = sp.diff(g_xy, x)
        gy = sp.diff(g_xy, y)

        # Substitute z = g(x, y) into curl components
        cx_s = curl_x.subs(z, g_xy)
        cy_s = curl_y.subs(z, g_xy)
        cz_s = curl_z.subs(z, g_xy)

        # dS = (-gx, -gy, 1) dx dy
        flux_curl_integrand = sp.simplify(-cx_s * gx - cy_s * gy + cz_s)

        try:
            inner_rhs = sp.integrate(flux_curl_integrand, (x, x_min, x_max))
            val_rhs = sp.integrate(inner_rhs, (y, y_min, y_max))
            val_rhs = sp.simplify(val_rhs)
        except Exception as exc:
            raise InvalidInputError(f"Không thể tính tích phân thông lượng của curl: {exc}") from exc

        rhs_ltx = (
            rf"\iint_S (\nabla \times \mathbf{{F}}) \cdot d\mathbf{{S}} = "
            rf"\int_{{{expr_to_latex(y_min)}}}^{{{expr_to_latex(y_max)}}} \left[ \int_{{{expr_to_latex(x_min)}}}^{{{expr_to_latex(x_max)}}} "
            rf"\left( {expr_to_latex(flux_curl_integrand)} \right) dx \right] dy = {expr_to_latex(val_rhs)}"
        )
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tính tích phân mặt của curl F (Vế phải)",
                description="Tính thông lượng của curl(F) qua mặt cong S:",
                content=ExpressionStepContent(
                    expression_before=f"integrate({flux_curl_integrand})",
                    expression_after=str(val_rhs),
                    latex_before=r"\iint_S (\nabla \times \mathbf{F}) \cdot d\mathbf{S}",
                    latex_after=expr_to_latex(val_rhs),
                ),
                equation_latex=rhs_ltx,
            )
        )
        step_idx += 1

        # Step 4: Compute Line Integral along boundary curve ∂S (LHS)
        # Boundary has 4 segments in 3D:
        # C1: y = y_min, x: x_min -> x_max, z = g(x, y_min), dz = gx * dx
        z1 = g_xy.subs(y, y_min)
        dz1_dx = sp.diff(z1, x)
        P1 = P.subs([(y, y_min), (z, z1)])
        R1 = R.subs([(y, y_min), (z, z1)])
        I1 = sp.integrate(P1 + R1 * dz1_dx, (x, x_min, x_max))

        # C2: x = x_max, y: y_min -> y_max, z = g(x_max, y), dz = gy * dy
        z2 = g_xy.subs(x, x_max)
        dz2_dy = sp.diff(z2, y)
        Q2 = Q.subs([(x, x_max), (z, z2)])
        R2 = R.subs([(x, x_max), (z, z2)])
        I2 = sp.integrate(Q2 + R2 * dz2_dy, (y, y_min, y_max))

        # C3: y = y_max, x: x_max -> x_min, z = g(x, y_max), dz = gx * dx
        z3 = g_xy.subs(y, y_max)
        dz3_dx = sp.diff(z3, x)
        P3 = P.subs([(y, y_max), (z, z3)])
        R3 = R.subs([(y, y_max), (z, z3)])
        I3 = sp.integrate(P3 + R3 * dz3_dx, (x, x_max, x_min))

        # C4: x = x_min, y: y_max -> y_min, z = g(x_min, y), dz = gy * dy
        z4 = g_xy.subs(x, x_min)
        dz4_dy = sp.diff(z4, y)
        Q4 = Q.subs([(x, x_min), (z, z4)])
        R4 = R.subs([(x, x_min), (z, z4)])
        I4 = sp.integrate(Q4 + R4 * dz4_dy, (y, y_max, y_min))

        val_lhs = sp.simplify(I1 + I2 + I3 + I4)

        lhs_ltx = (
            rf"\oint_{{\partial S}} \mathbf{{F}} \cdot d\mathbf{{r}} = I_{{C_1}} + I_{{C_2}} + I_{{C_3}} + I_{{C_4}} = "
            rf"{expr_to_latex(I1)} + {expr_to_latex(I2)} + {expr_to_latex(I3)} + {expr_to_latex(I4)} = {expr_to_latex(val_lhs)}"
        )
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tính tích phân lưu thông trên biên kín ∂S (Vế trái)",
                description="Tính tổng tích phân đường trên 4 cung của đường cong biên kín trong không gian 3 chiều:",
                content=ExpressionStepContent(
                    expression_before="I1 + I2 + I3 + I4",
                    expression_after=str(val_lhs),
                    latex_before=r"\oint_{\partial S} \mathbf{F} \cdot d\mathbf{r}",
                    latex_after=expr_to_latex(val_lhs),
                ),
                equation_latex=lhs_ltx,
            )
        )
        step_idx += 1

        # Step 5: Verification & Identity conclusion
        verify_ltx = rf"\oint_{{\partial S}} \mathbf{{F}} \cdot d\mathbf{{r}} = \iint_S (\nabla \times \mathbf{{F}}) \cdot d\mathbf{{S}} = {expr_to_latex(val_rhs)}"
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Kiểm chứng và kết luận định lý Stokes",
                description="Đối chiếu kết quả hai vế: Tích phân lưu thông trên biên kín bằng chính xác thông lượng của curl qua mặt.",
                content=ExpressionStepContent(
                    expression_before=f"LHS ({val_lhs}) == RHS ({val_rhs})",
                    expression_after="Định lý Stokes nghiệm đúng",
                    latex_before=r"\oint_{\partial S} \mathbf{F} \cdot d\mathbf{r} \equiv \iint_S (\nabla \times \mathbf{F}) \cdot d\mathbf{S}",
                    latex_after=verify_ltx,
                ),
                equation_latex=verify_ltx,
            )
        )

        verification = self._verifier.verify_stokes_theorem(val_lhs, val_rhs)
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

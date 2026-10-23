"""Solver for triple integrals over 3D regions in Cartesian, Cylindrical, and Spherical coordinates."""

from __future__ import annotations

import time
import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionResponse, SolutionStep
from math_app.application.ports.solver import Solver
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.verification.calculus.triple_integral_verifier import TripleIntegralVerifier


def _substitute_coords(expr: sp.Expr, mapping: dict[str, sp.Expr]) -> sp.Expr:
    """Safely substitute coordinates by symbol name to prevent assumption mismatch."""
    subs_list = [(s, mapping[s.name]) for s in expr.free_symbols if s.name in mapping]
    return expr.subs(subs_list)


class TripleIntegralSolver(Solver):
    """Calculus solver for iterated triple integrals over 3D solids."""

    def __init__(self, verifier: TripleIntegralVerifier | None = None) -> None:
        self._verifier = verifier or TripleIntegralVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type == ProblemType.TRIPLE_INTEGRAL

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        start_time = time.perf_counter()
        steps: list[SolutionStep] = []
        warnings: list[str] = []

        params = request.parameters
        coord = str(params.get("coord_system", "cartesian")).lower()

        # Parse coordinate variables and bounds based on coordinate system
        if coord in ("cylindrical", "tru"):
            v_in_name = str(params.get("var_inner", "z")).strip()
            v_mid_name = str(params.get("var_middle", "r")).strip()
            v_out_name = str(params.get("var_outer", "theta")).strip()
            try:
                in_min = sp.sympify(str(params.get("z_min", params.get("inner_min", "0"))).strip())
                in_max = sp.sympify(str(params.get("z_max", params.get("inner_max", "1"))).strip())
                mid_min = sp.sympify(str(params.get("r_min", params.get("middle_min", "0"))).strip())
                mid_max = sp.sympify(str(params.get("r_max", params.get("middle_max", "1"))).strip())
                out_min = sp.sympify(str(params.get("th_min", params.get("theta_min", params.get("outer_min", "0")))).strip())
                out_max = sp.sympify(str(params.get("th_max", params.get("theta_max", params.get("outer_max", "2*pi")))).strip())
            except Exception as exc:
                raise InvalidInputError(f"Cận tích phân tọa độ trụ không hợp lệ: {exc}") from exc
        elif coord in ("spherical", "cau"):
            v_in_name = str(params.get("var_inner", "rho")).strip()
            v_mid_name = str(params.get("var_middle", "phi")).strip()
            v_out_name = str(params.get("var_outer", "theta")).strip()
            try:
                in_min = sp.sympify(str(params.get("rho_min", params.get("inner_min", "0"))).strip())
                in_max = sp.sympify(str(params.get("rho_max", params.get("inner_max", "1"))).strip())
                mid_min = sp.sympify(str(params.get("phi_min", params.get("middle_min", "0"))).strip())
                mid_max = sp.sympify(str(params.get("phi_max", params.get("middle_max", "pi"))).strip())
                out_min = sp.sympify(str(params.get("th_min", params.get("theta_min", params.get("outer_min", "0")))).strip())
                out_max = sp.sympify(str(params.get("th_max", params.get("theta_max", params.get("outer_max", "2*pi")))).strip())
            except Exception as exc:
                raise InvalidInputError(f"Cận tích phân tọa độ cầu không hợp lệ: {exc}") from exc
        else:
            v_in_name = str(params.get("var_inner", "z")).strip()
            v_mid_name = str(params.get("var_middle", "y")).strip()
            v_out_name = str(params.get("var_outer", "x")).strip()
            try:
                in_min = sp.sympify(str(params.get("z_min", params.get("inner_min", "0"))).strip())
                in_max = sp.sympify(str(params.get("z_max", params.get("inner_max", "1"))).strip())
                mid_min = sp.sympify(str(params.get("y_min", params.get("middle_min", "0"))).strip())
                mid_max = sp.sympify(str(params.get("y_max", params.get("middle_max", "1"))).strip())
                out_min = sp.sympify(str(params.get("x_min", params.get("outer_min", "0"))).strip())
                out_max = sp.sympify(str(params.get("x_max", params.get("outer_max", "1"))).strip())
            except Exception as exc:
                raise InvalidInputError(f"Cận tích phân ba lớp Descartes không hợp lệ: {exc}") from exc

        v_in = sp.Symbol(v_in_name)
        v_mid = sp.Symbol(v_mid_name)
        v_out = sp.Symbol(v_out_name)

        raw_in = request.raw_input.strip() or "1"
        try:
            raw_integrand = sp.sympify(raw_in)
        except Exception as exc:
            raise InvalidInputError(f"Hàm dưới dấu tích phân ba lớp không hợp lệ: {exc}") from exc

        step_idx = 1
        x_sym, y_sym, z_sym = sp.symbols("x y z")

        if coord in ("cylindrical", "tru"):
            # Cylindrical: x = r cos(theta), y = r sin(theta), z = z; Jacobian = r
            # Variables: v_in = z, v_mid = r, v_out = theta
            subs_dict = {"x": v_mid * sp.cos(v_out), "y": v_mid * sp.sin(v_out), "z": v_in}
            f_cyl = _substitute_coords(raw_integrand, subs_dict)
            jacobian = v_mid
            integrand_3d = sp.simplify(f_cyl * jacobian)

            coord_desc = (
                rf"x = {v_mid_name}\cos({v_out_name}), \; y = {v_mid_name}\sin({v_out_name}), \; z = {v_in_name} \implies "
                rf"dV = {v_mid_name}\,d{v_in_name}\,d{v_mid_name}\,d{v_out_name}"
            )
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Chuyển sang hệ tọa độ trụ (Cylindrical Coordinates)",
                    description="Thực hiện phép đổi biến sang tọa độ trụ với định thức ma trận Jacobi J = r:",
                    content=ExpressionStepContent(
                        expression_before="dV",
                        expression_after=f"{v_mid_name} d{v_in_name} d{v_mid_name} d{v_out_name}",
                        latex_before="dV",
                        latex_after=rf"{v_mid_name}\,d{v_in_name}d{v_mid_name}d{v_out_name}",
                    ),
                    equation_latex=coord_desc,
                )
            )
            step_idx += 1

        elif coord in ("spherical", "cau"):
            # Spherical: x = rho sin(phi) cos(theta), y = rho sin(phi) sin(theta), z = rho cos(phi); Jacobian = rho^2 sin(phi)
            # Variables: v_in = rho, v_mid = phi, v_out = theta
            subs_dict = {
                "x": v_in * sp.sin(v_mid) * sp.cos(v_out),
                "y": v_in * sp.sin(v_mid) * sp.sin(v_out),
                "z": v_in * sp.cos(v_mid),
            }
            f_sph = _substitute_coords(raw_integrand, subs_dict)
            jacobian = v_in**2 * sp.sin(v_mid)
            integrand_3d = sp.simplify(f_sph * jacobian)

            coord_desc = (
                rf"x = {v_in_name}\sin({v_mid_name})\cos({v_out_name}), \; y = {v_in_name}\sin({v_mid_name})\sin({v_out_name}), \; z = {v_in_name}\cos({v_mid_name}) \implies "
                rf"dV = {v_in_name}^2 \sin({v_mid_name})\,d{v_in_name}\,d{v_mid_name}\,d{v_out_name}"
            )
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Chuyển sang hệ tọa độ cầu (Spherical Coordinates)",
                    description="Thực hiện phép đổi biến sang tọa độ cầu với định thức ma trận Jacobi J = ρ² sin(φ):",
                    content=ExpressionStepContent(
                        expression_before="dV",
                        expression_after=f"{v_in_name}^2 sin({v_mid_name}) d{v_in_name} d{v_mid_name} d{v_out_name}",
                        latex_before="dV",
                        latex_after=rf"{v_in_name}^2 \sin({v_mid_name})\,d{v_in_name}d{v_mid_name}d{v_out_name}",
                    ),
                    equation_latex=coord_desc,
                )
            )
            step_idx += 1

        else:
            # Standard Cartesian
            integrand_3d = raw_integrand
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Thiết lập thứ tự tích phân trong hệ tọa độ Descartes",
                    description=f"Thiết lập tích phân lặp ba lớp theo thứ tự d{v_in_name} d{v_mid_name} d{v_out_name}:",
                    content=ExpressionStepContent(
                        expression_before="dV",
                        expression_after=f"d{v_in_name} d{v_mid_name} d{v_out_name}",
                        latex_before=r"\iiint_V f(x, y, z)\,dV",
                        latex_after=rf"\int d{v_out_name} \int d{v_mid_name} \int f\,d{v_in_name}",
                    ),
                    equation_latex=rf"dV = d{v_in_name}\,d{v_mid_name}\,d{v_out_name}",
                )
            )
            step_idx += 1

        # Layer 1: Innermost integration (v_in)
        try:
            int_layer1 = sp.integrate(integrand_3d, (v_in, in_min, in_max))
            int_layer1 = sp.simplify(int_layer1)
        except Exception as exc:
            raise InvalidInputError(f"Không thể tính tích phân lớp trong cùng theo {v_in_name}: {exc}") from exc

        l1_ltx = (
            rf"I_1({v_mid_name}, {v_out_name}) = "
            rf"\int_{{{expr_to_latex(in_min)}}}^{{{expr_to_latex(in_max)}}} \left( {expr_to_latex(integrand_3d)} \right) d{v_in_name} = "
            rf"{expr_to_latex(int_layer1)}"
        )
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name=f"Tích phân lớp 1 (trong cùng) theo {v_in_name}",
                description=f"Tính tích phân theo biến {v_in_name} với cận từ {in_min} đến {in_max}:",
                content=ExpressionStepContent(
                    expression_before=f"integrate({integrand_3d}, ({v_in}, {in_min}, {in_max}))",
                    expression_after=str(int_layer1),
                    latex_before=rf"\int_{{{expr_to_latex(in_min)}}}^{{{expr_to_latex(in_max)}}} {expr_to_latex(integrand_3d)}\,d{v_in_name}",
                    latex_after=expr_to_latex(int_layer1),
                ),
                equation_latex=l1_ltx,
            )
        )
        step_idx += 1

        # Layer 2: Middle integration (v_mid)
        try:
            int_layer2 = sp.integrate(int_layer1, (v_mid, mid_min, mid_max))
            int_layer2 = sp.simplify(int_layer2)
        except Exception as exc:
            raise InvalidInputError(f"Không thể tính tích phân lớp giữa theo {v_mid_name}: {exc}") from exc

        l2_ltx = (
            rf"I_2({v_out_name}) = "
            rf"\int_{{{expr_to_latex(mid_min)}}}^{{{expr_to_latex(mid_max)}}} \left( {expr_to_latex(int_layer1)} \right) d{v_mid_name} = "
            rf"{expr_to_latex(int_layer2)}"
        )
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name=f"Tích phân lớp 2 (lớp giữa) theo {v_mid_name}",
                description=f"Tính tích phân theo biến {v_mid_name} với cận từ {mid_min} đến {mid_max}:",
                content=ExpressionStepContent(
                    expression_before=f"integrate({int_layer1}, ({v_mid}, {mid_min}, {mid_max}))",
                    expression_after=str(int_layer2),
                    latex_before=rf"\int_{{{expr_to_latex(mid_min)}}}^{{{expr_to_latex(mid_max)}}} {expr_to_latex(int_layer1)}\,d{v_mid_name}",
                    latex_after=expr_to_latex(int_layer2),
                ),
                equation_latex=l2_ltx,
            )
        )
        step_idx += 1

        # Layer 3: Outermost integration (v_out)
        try:
            final_val = sp.integrate(int_layer2, (v_out, out_min, out_max))
            final_val = sp.simplify(final_val)
        except Exception as exc:
            raise InvalidInputError(f"Không thể tính tích phân lớp ngoài cùng theo {v_out_name}: {exc}") from exc

        l3_ltx = (
            rf"I = \int_{{{expr_to_latex(out_min)}}}^{{{expr_to_latex(out_max)}}} \left( {expr_to_latex(int_layer2)} \right) d{v_out_name} = "
            rf"{expr_to_latex(final_val)}"
        )
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name=f"Tích phân lớp 3 (ngoài cùng) theo {v_out_name}",
                description=f"Tính tích phân theo biến ngoài cùng {v_out_name} để thu được kết quả đại số chính xác:",
                content=ExpressionStepContent(
                    expression_before=f"integrate({int_layer2}, ({v_out}, {out_min}, {out_max}))",
                    expression_after=str(final_val),
                    latex_before=rf"\int_{{{expr_to_latex(out_min)}}}^{{{expr_to_latex(out_max)}}} {expr_to_latex(int_layer2)}\,d{v_out_name}",
                    latex_after=expr_to_latex(final_val),
                ),
                equation_latex=l3_ltx,
            )
        )

        verification = self._verifier.verify_triple_integral(
            final_val,
            integrand_3d,
            v_in,
            in_min,
            in_max,
            v_mid,
            mid_min,
            mid_max,
            v_out,
            out_min,
            out_max,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return SolutionResponse(
            status=SolutionStatus.SUCCESS,
            verification=verification,
            raw_input=request.raw_input,
            canonical_input=request.raw_input,
            final_result=str(final_val),
            final_latex=expr_to_latex(final_val),
            steps=tuple(steps),
            domain_restrictions=(),
            warnings=tuple(warnings),
            execution_time_ms=elapsed_ms,
        )

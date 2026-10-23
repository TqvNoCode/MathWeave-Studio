"""Solver for surface area of explicit and parametric surfaces."""

from __future__ import annotations

import time
import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionResponse, SolutionStep
from math_app.application.ports.solver import Solver
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.input.parser import parse_mathematical_input, parse_safe_expression
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.verification.calculus.surface_area_verifier import SurfaceAreaVerifier


class SurfaceAreaSolver(Solver):
    """Calculus solver for surface area of 3D surfaces."""

    def __init__(self, verifier: SurfaceAreaVerifier | None = None) -> None:
        self._verifier = verifier or SurfaceAreaVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type == ProblemType.SURFACE_AREA

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        start_time = time.perf_counter()
        steps: list[SolutionStep] = []
        warnings: list[str] = []
        params = request.parameters

        is_parametric = "param_x" in params or "param_y" in params

        step_idx = 1

        if is_parametric:
            # Parametric surface r(u, v) = (x(u, v), y(u, v), z(u, v))
            u_name = str(params.get("u_var", "u")).strip()
            v_name = str(params.get("v_var", "v")).strip()
            u = sp.Symbol(u_name)
            v = sp.Symbol(v_name)

            raw_u_min = str(params.get("u_min", "0")).strip()
            raw_u_max = str(params.get("u_max", "1")).strip()
            raw_v_min = str(params.get("v_min", "0")).strip()
            raw_v_max = str(params.get("v_max", "1")).strip()

            try:
                u_min = parse_safe_expression(raw_u_min, evaluate=True)
                u_max = parse_safe_expression(raw_u_max, evaluate=True)
                v_min = parse_safe_expression(raw_v_min, evaluate=True)
                v_max = parse_safe_expression(raw_v_max, evaluate=True)
            except Exception as exc:
                raise InvalidInputError(f"Cận của miền tham số u, v không hợp lệ: {exc}") from exc

            try:
                allowed_uv = {u_name, v_name}
                xu = parse_safe_expression(params.get("param_x", u_name), allowed_variables=allowed_uv, evaluate=True)
                yv = parse_safe_expression(params.get("param_y", v_name), allowed_variables=allowed_uv, evaluate=True)
                zw = parse_safe_expression(params.get("param_z", "0"), allowed_variables=allowed_uv, evaluate=True)
            except Exception as exc:
                raise InvalidInputError(f"Biểu thức tham số của mặt cong không hợp lệ: {exc}") from exc

            # Step 1: Surface parametrization
            r_ltx = (
                rf"\mathbf{{r}}({u_name}, {v_name}) = \left( {expr_to_latex(xu)}, {expr_to_latex(yv)}, {expr_to_latex(zw)} \right), \quad "
                rf"{u_name} \in [{expr_to_latex(u_min)}, {expr_to_latex(u_max)}], \; {v_name} \in [{expr_to_latex(v_min)}, {expr_to_latex(v_max)}]"
            )
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Xác định mặt tham số r(u, v)",
                    description="Xác định vectơ vị trí tham số hóa của mặt cong S:",
                    content=ExpressionStepContent(
                        expression_before="r(u, v)",
                        expression_after=str((xu, yv, zw)),
                        latex_before=r"\mathbf{r}(u, v)",
                        latex_after=r_ltx,
                    ),
                    equation_latex=r_ltx,
                )
            )
            step_idx += 1

            # Step 2: Tangent vectors ru, rv and cross product
            ru = (sp.diff(xu, u), sp.diff(yv, u), sp.diff(zw, u))
            rv = (sp.diff(xu, v), sp.diff(yv, v), sp.diff(zw, v))

            # Cross product ru x rv
            nx = sp.simplify(ru[1] * rv[2] - ru[2] * rv[1])
            ny = sp.simplify(ru[2] * rv[0] - ru[0] * rv[2])
            nz = sp.simplify(ru[0] * rv[1] - ru[1] * rv[0])

            n_ltx = rf"\mathbf{{r}}_{u_name} \times \mathbf{{r}}_{v_name} = \left( {expr_to_latex(nx)}, {expr_to_latex(ny)}, {expr_to_latex(nz)} \right)"
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Tính tích có hướng ru x rv",
                    description="Tính vectơ pháp tuyến thông qua tích có hướng của các vectơ tiếp tuyến:",
                    content=ExpressionStepContent(
                        expression_before="ru x rv",
                        expression_after=str((nx, ny, nz)),
                        latex_before=r"\mathbf{r}_u \times \mathbf{r}_v",
                        latex_after=n_ltx,
                    ),
                    equation_latex=n_ltx,
                )
            )
            step_idx += 1

            # Step 3: Area element dS = ||ru x rv|| du dv
            norm_sq = sp.trigsimp(sp.simplify(nx**2 + ny**2 + nz**2))
            norm_cross = sp.sqrt(norm_sq)

            ds_ltx = rf"dS = \|\mathbf{{r}}_{u_name} \times \mathbf{{r}}_{v_name}\|\,d{u_name}\,d{v_name} = {expr_to_latex(norm_cross)}\,d{u_name}\,d{v_name}"
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Thiết lập phần tử diện tích mặt dS",
                    description="Tính độ lớn vectơ pháp tuyến để được phần tử vi phân diện tích:",
                    content=ExpressionStepContent(
                        expression_before="dS",
                        expression_after=str(norm_cross),
                        latex_before="dS",
                        latex_after=expr_to_latex(norm_cross),
                    ),
                    equation_latex=ds_ltx,
                )
            )
            step_idx += 1

            # Step 4: Double integration
            try:
                inner_val = sp.integrate(norm_cross, (u, u_min, u_max))
                final_val = sp.integrate(inner_val, (v, v_min, v_max))
                final_val = sp.simplify(final_val)
            except Exception as exc:
                raise InvalidInputError(f"Không thể tính tích phân diện tích mặt cong: {exc}") from exc

            int_ltx = (
                rf"A = \int_{{{expr_to_latex(v_min)}}}^{{{expr_to_latex(v_max)}}} \left[ \int_{{{expr_to_latex(u_min)}}}^{{{expr_to_latex(u_max)}}} "
                rf"{expr_to_latex(norm_cross)}\,d{u_name} \right] d{v_name} = {expr_to_latex(final_val)}"
            )
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Tính tích phân bội hai tìm diện tích mặt",
                    description="Tính tích phân bội hai trên miền tham số để ra kết quả diện tích A:",
                    content=ExpressionStepContent(
                        expression_before=f"integrate({norm_cross}, ({u}, {u_min}, {u_max}), ({v}, {v_min}, {v_max}))",
                        expression_after=str(final_val),
                        latex_before=r"\iint_D \|\mathbf{r}_u \times \mathbf{r}_v\|\,du\,dv",
                        latex_after=expr_to_latex(final_val),
                    ),
                    equation_latex=int_ltx,
                )
            )

            verification = self._verifier.verify_surface_area(
                final_val, norm_cross, u, u_min, u_max, v, v_min, v_max
            )

        else:
            # Explicit surface z = f(x, y)
            x_name = str(params.get("u_var", "x")).strip()
            y_name = str(params.get("v_var", "y")).strip()
            x = sp.Symbol(x_name)
            y = sp.Symbol(y_name)

            raw_x_min = str(params.get("u_min", params.get("x_min", "0"))).strip()
            raw_x_max = str(params.get("u_max", params.get("x_max", "1"))).strip()
            raw_y_min = str(params.get("v_min", params.get("y_min", "0"))).strip()
            raw_y_max = str(params.get("v_max", params.get("y_max", "1"))).strip()

            try:
                x_min = parse_safe_expression(raw_x_min, evaluate=True)
                x_max = parse_safe_expression(raw_x_max, evaluate=True)
                y_min = parse_safe_expression(raw_y_min, evaluate=True)
                y_max = parse_safe_expression(raw_y_max, evaluate=True)
            except Exception as exc:
                raise InvalidInputError(f"Cận của miền x, y không hợp lệ: {exc}") from exc

            raw_surf = str(params.get("surface_expr", request.raw_input)).strip()
            try:
                allowed_xy = {x_name, y_name}
                z_f = parse_safe_expression(raw_surf, allowed_variables=allowed_xy, evaluate=True)
            except Exception as exc:
                raise InvalidInputError(f"Biểu thức hàm mặt cong z = f({x_name}, {y_name}) không hợp lệ: {exc}") from exc

            # Step 1: Function definition
            surf_ltx = (
                rf"S: z = f({x_name}, {y_name}) = {expr_to_latex(z_f)}, \quad "
                rf"{x_name} \in [{expr_to_latex(x_min)}, {expr_to_latex(x_max)}], \; {y_name} \in [{expr_to_latex(y_min)}, {expr_to_latex(y_max)}]"
            )
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Xác định mặt cong hiển z = f(x, y)",
                    description=f"Mặt cong xác định bởi hàm số z = f({x_name}, {y_name}) trên miền chữ nhật D:",
                    content=ExpressionStepContent(
                        expression_before=f"f({x_name}, {y_name})",
                        expression_after=str(z_f),
                        latex_before=r"z = f(x, y)",
                        latex_after=surf_ltx,
                    ),
                    equation_latex=surf_ltx,
                )
            )
            step_idx += 1

            # Step 2: Partial derivatives fx, fy
            fx = sp.diff(z_f, x)
            fy = sp.diff(z_f, y)

            derivs_ltx = (
                rf"\frac{{\partial z}}{{\partial {x_name}}} = {expr_to_latex(fx)}, \quad "
                rf"\frac{{\partial z}}{{\partial {y_name}}} = {expr_to_latex(fy)}"
            )
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Tính các đạo hàm riêng fx, fy",
                    description=f"Lấy đạo hàm riêng của z theo {x_name} và {y_name}:",
                    content=ExpressionStepContent(
                        expression_before="dz/dx, dz/dy",
                        expression_after=str((fx, fy)),
                        latex_before=r"\left(\frac{\partial z}{\partial x}, \frac{\partial z}{\partial y}\right)",
                        latex_after=derivs_ltx,
                    ),
                    equation_latex=derivs_ltx,
                )
            )
            step_idx += 1

            # Step 3: Area element dS = sqrt(1 + fx^2 + fy^2) dx dy
            sum_sq = sp.trigsimp(sp.simplify(1 + fx**2 + fy**2))
            norm_elem = sp.sqrt(sum_sq)

            ds_ltx = (
                rf"dS = \sqrt{{ 1 + \left(\frac{{\partial z}}{{\partial {x_name}}}\right)^2 + \left(\frac{{\partial z}}{{\partial {y_name}}}\right)^2 }}\,d{x_name}\,d{y_name} = "
                rf"{expr_to_latex(norm_elem)}\,d{x_name}\,d{y_name}"
            )
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Thiết lập phần tử diện tích dS",
                    description="Rút gọn biểu thức vi phân diện tích dS:",
                    content=ExpressionStepContent(
                        expression_before="dS",
                        expression_after=str(norm_elem),
                        latex_before="dS",
                        latex_after=expr_to_latex(norm_elem),
                    ),
                    equation_latex=ds_ltx,
                )
            )
            step_idx += 1

            # Step 4: Double integration
            try:
                inner_val = sp.integrate(norm_elem, (x, x_min, x_max))
                final_val = sp.integrate(inner_val, (y, y_min, y_max))
                final_val = sp.simplify(final_val)
            except Exception as exc:
                raise InvalidInputError(f"Không thể tính tích phân diện tích mặt cong: {exc}") from exc

            int_ltx = (
                rf"A = \int_{{{expr_to_latex(y_min)}}}^{{{expr_to_latex(y_max)}}} \left[ \int_{{{expr_to_latex(x_min)}}}^{{{expr_to_latex(x_max)}}} "
                rf"{expr_to_latex(norm_elem)}\,d{x_name} \right] d{y_name} = {expr_to_latex(final_val)}"
            )
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Tính tích phân bội hai tìm diện tích mặt",
                    description="Tính tích phân bội hai trên miền xác định để ra kết quả diện tích A:",
                    content=ExpressionStepContent(
                        expression_before=f"integrate({norm_elem}, ({x}, {x_min}, {x_max}), ({y}, {y_min}, {y_max}))",
                        expression_after=str(final_val),
                        latex_before=r"\iint_D \sqrt{1 + f_x^2 + f_y^2}\,dx\,dy",
                        latex_after=expr_to_latex(final_val),
                    ),
                    equation_latex=int_ltx,
                )
            )

            verification = self._verifier.verify_surface_area(
                final_val, norm_elem, x, x_min, x_max, y, y_min, y_max
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

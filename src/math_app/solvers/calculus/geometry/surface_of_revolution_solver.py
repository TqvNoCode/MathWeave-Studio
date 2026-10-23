"""Solver for surfaces and solids of revolution (area and volume)."""

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
from math_app.verification.calculus.surface_of_revolution_verifier import SurfaceOfRevolutionVerifier


class SurfaceOfRevolutionSolver(Solver):
    """Calculus solver for area and volume of revolution around x-axis or y-axis."""

    def __init__(self, verifier: SurfaceOfRevolutionVerifier | None = None) -> None:
        self._verifier = verifier or SurfaceOfRevolutionVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type == ProblemType.SURFACE_OF_REVOLUTION

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        start_time = time.perf_counter()
        steps: list[SolutionStep] = []
        warnings: list[str] = []
        params = request.parameters

        var_name = request.target_variable or "x"
        x = sp.Symbol(var_name)

        raw_a = str(params.get("lower_bound", "0")).strip()
        raw_b = str(params.get("upper_bound", "1")).strip()
        try:
            a_bound = parse_safe_expression(raw_a, evaluate=True)
            b_bound = parse_safe_expression(raw_b, evaluate=True)
        except Exception as exc:
            raise InvalidInputError(f"Cận tích phân không hợp lệ: {exc}") from exc

        try:
            fx, _ = parse_mathematical_input(request.raw_input, var_name)
        except Exception as exc:
            raise InvalidInputError(f"Biểu thức đường sinh y = f({var_name}) không hợp lệ: {exc}") from exc

        axis = str(params.get("axis", "x")).lower().strip()
        is_about_x = axis in ("x", "ox", "horizontal", "truc_ox")

        step_idx = 1

        # Step 1: Curve and rotation axis
        axis_str = "trục hoành Ox (y = 0)" if is_about_x else "trục tung Oy (x = 0)"
        setup_ltx = (
            rf"y = f({x.name}) = {expr_to_latex(fx)}, \quad "
            rf"{x.name} \in [{expr_to_latex(a_bound)}, {expr_to_latex(b_bound)}], \quad \text{{quay quanh }} {axis_str}"
        )
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Xác định đường sinh và trục quay",
                description=f"Đường sinh y = f({x.name}) quay quanh {axis_str}:",
                content=ExpressionStepContent(
                    expression_before=f"f({x.name})",
                    expression_after=str(fx),
                    latex_before=r"y = f(x)",
                    latex_after=setup_ltx,
                ),
                equation_latex=setup_ltx,
            )
        )
        step_idx += 1

        # Step 2: Derivative and arc length element
        dfx = sp.diff(fx, x)
        speed = sp.sqrt(sp.trigsimp(sp.simplify(1 + dfx**2)))

        ds_ltx = (
            rf"f'({x.name}) = {expr_to_latex(dfx)}, \quad "
            rf"ds = \sqrt{{1 + \left(f'({x.name})\right)^2}}\,d{x.name} = {expr_to_latex(speed)}\,d{x.name}"
        )
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tính đạo hàm và vi phân độ dài cung ds",
                description="Tính đạo hàm bậc một và vi phân cung ds của đường sinh:",
                content=ExpressionStepContent(
                    expression_before="ds",
                    expression_after=str(speed),
                    latex_before="ds",
                    latex_after=expr_to_latex(speed),
                ),
                equation_latex=ds_ltx,
            )
        )
        step_idx += 1

        # Step 3: Area of revolution
        if is_about_x:
            # S_x = 2 * pi * \int |f(x)| * ds
            radius_area = sp.Abs(fx)
            area_integrand = 2 * sp.pi * radius_area * speed
            area_formula_ltx = (
                rf"S_x = 2\pi \int_{{{expr_to_latex(a_bound)}}}^{{{expr_to_latex(b_bound)}}} |f({x.name})|\,ds = "
                rf"2\pi \int_{{{expr_to_latex(a_bound)}}}^{{{expr_to_latex(b_bound)}}} \left( {expr_to_latex(radius_area * speed)} \right) d{x.name}"
            )
        else:
            # S_y = 2 * pi * \int x * ds
            radius_area = x
            area_integrand = 2 * sp.pi * radius_area * speed
            area_formula_ltx = (
                rf"S_y = 2\pi \int_{{{expr_to_latex(a_bound)}}}^{{{expr_to_latex(b_bound)}}} {x.name}\,ds = "
                rf"2\pi \int_{{{expr_to_latex(a_bound)}}}^{{{expr_to_latex(b_bound)}}} \left( {expr_to_latex(radius_area * speed)} \right) d{x.name}"
            )

        try:
            val_area = sp.integrate(area_integrand, (x, a_bound, b_bound))
            val_area = sp.simplify(val_area)
        except Exception as exc:
            raise InvalidInputError(f"Không thể tính tích phân diện tích mặt tròn xoay: {exc}") from exc

        area_result_ltx = rf"{area_formula_ltx} = {expr_to_latex(val_area)}"
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tính diện tích mặt tròn xoay S",
                description=f"Thiết lập và tính tích phân diện tích mặt tròn xoay quanh {axis_str}:",
                content=ExpressionStepContent(
                    expression_before=f"integrate({area_integrand}, ({x}, {a_bound}, {b_bound}))",
                    expression_after=str(val_area),
                    latex_before=r"S = 2\pi \int r\,ds",
                    latex_after=expr_to_latex(val_area),
                ),
                equation_latex=area_result_ltx,
            )
        )
        step_idx += 1

        # Step 4: Volume of revolution
        if is_about_x:
            # V_x = pi * \int (f(x))^2 dx (Disk method)
            vol_integrand = sp.pi * (fx**2)
            vol_formula_ltx = (
                rf"V_x = \pi \int_{{{expr_to_latex(a_bound)}}}^{{{expr_to_latex(b_bound)}}} \left( f({x.name}) \right)^2 d{x.name} = "
                rf"\pi \int_{{{expr_to_latex(a_bound)}}}^{{{expr_to_latex(b_bound)}}} \left( {expr_to_latex(fx**2)} \right) d{x.name}"
            )
        else:
            # V_y = 2 * pi * \int x * |f(x)| dx (Cylindrical shells method)
            vol_integrand = 2 * sp.pi * x * sp.Abs(fx)
            vol_formula_ltx = (
                rf"V_y = 2\pi \int_{{{expr_to_latex(a_bound)}}}^{{{expr_to_latex(b_bound)}}} {x.name} |f({x.name})|\,d{x.name} = "
                rf"2\pi \int_{{{expr_to_latex(a_bound)}}}^{{{expr_to_latex(b_bound)}}} \left( {expr_to_latex(x * sp.Abs(fx))} \right) d{x.name}"
            )

        try:
            val_vol = sp.integrate(vol_integrand, (x, a_bound, b_bound))
            val_vol = sp.simplify(val_vol)
        except Exception as exc:
            raise InvalidInputError(f"Không thể tính tích phân thể tích khối tròn xoay: {exc}") from exc

        vol_result_ltx = rf"{vol_formula_ltx} = {expr_to_latex(val_vol)}"
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tính thể tích khối tròn xoay V",
                description=f"Thiết lập và tính tích phân thể tích khối tròn xoay quanh {axis_str}:",
                content=ExpressionStepContent(
                    expression_before=f"integrate({vol_integrand}, ({x}, {a_bound}, {b_bound}))",
                    expression_after=str(val_vol),
                    latex_before=r"V = \int dV",
                    latex_after=expr_to_latex(val_vol),
                ),
                equation_latex=vol_result_ltx,
            )
        )

        verification = self._verifier.verify_revolution(
            val_area, val_vol, area_integrand, vol_integrand, x, a_bound, b_bound
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        final_answer = f"S = {val_area}, V = {val_vol}"
        final_answer_latex = rf"S = {expr_to_latex(val_area)}, \quad V = {expr_to_latex(val_vol)}"

        return SolutionResponse(
            status=SolutionStatus.SUCCESS,
            verification=verification,
            raw_input=request.raw_input,
            canonical_input=request.raw_input,
            final_result=final_answer,
            final_latex=final_answer_latex,
            steps=tuple(steps),
            domain_restrictions=(),
            warnings=tuple(warnings),
            execution_time_ms=elapsed_ms,
        )

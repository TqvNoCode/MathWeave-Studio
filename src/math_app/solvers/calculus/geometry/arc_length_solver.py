"""Solver for arc length of explicit Cartesian curves and parametric curves."""

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
from math_app.verification.calculus.arc_length_verifier import ArcLengthVerifier


class ArcLengthSolver(Solver):
    """Calculus solver for curve arc length in 2D and 3D."""

    def __init__(self, verifier: ArcLengthVerifier | None = None) -> None:
        self._verifier = verifier or ArcLengthVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type in {ProblemType.ARC_LENGTH, ProblemType.PARAMETRIC_CURVE}

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        start_time = time.perf_counter()
        steps: list[SolutionStep] = []
        warnings: list[str] = []
        params = request.parameters

        is_parametric = (
            "param_x" in params
            or "param_var" in params
            or request.problem_type == ProblemType.PARAMETRIC_CURVE
            or "," in request.raw_input
        )

        step_idx = 1

        if is_parametric:
            # Parametric curve: r(t) = (x(t), y(t), z(t))
            param_var_name = str(params.get("param_var", "t")).strip()
            t = sp.Symbol(param_var_name)

            raw_a = str(params.get("t_min", params.get("lower_bound", "0"))).strip()
            raw_b = str(params.get("t_max", params.get("upper_bound", "1"))).strip()
            try:
                a_bound = parse_safe_expression(raw_a, evaluate=True)
                b_bound = parse_safe_expression(raw_b, evaluate=True)
            except Exception as exc:
                raise InvalidInputError(f"Cận tham số t không hợp lệ: {exc}") from exc

            # Coordinates
            if "," in request.raw_input and "param_x" not in params:
                parts = [p.strip() for p in request.raw_input.split(",")]
                raw_x = parts[0]
                raw_y = parts[1] if len(parts) > 1 else "0"
                raw_z = parts[2] if len(parts) > 2 else "0"
            else:
                raw_x = str(params.get("param_x", request.raw_input)).strip()
                raw_y = str(params.get("param_y", "0")).strip()
                raw_z = str(params.get("param_z", "0")).strip()

            try:
                xt, _ = parse_mathematical_input(raw_x, param_var_name)
                yt, _ = parse_mathematical_input(raw_y, param_var_name)
                zt, _ = parse_mathematical_input(raw_z, param_var_name)
            except Exception as exc:
                raise InvalidInputError(f"Biểu thức tham số hóa của đường cong không hợp lệ: {exc}") from exc

            # Step 1: Curve equations
            r_ltx = rf"\mathbf{{r}}({t.name}) = \left( {expr_to_latex(xt)}, {expr_to_latex(yt)}"
            if zt != 0:
                r_ltx += rf", {expr_to_latex(zt)}"
            r_ltx += rf" \right), \quad {t.name} \in [{expr_to_latex(a_bound)}, {expr_to_latex(b_bound)}]"

            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Thiết lập phương trình tham số",
                    description="Xác định phương trình vectơ tham số của đường cong trên đoạn xác định:",
                    content=ExpressionStepContent(
                        expression_before="r(t)",
                        expression_after=str((xt, yt, zt)),
                        latex_before=r"\mathbf{r}(t)",
                        latex_after=r_ltx,
                    ),
                    equation_latex=r_ltx,
                )
            )
            step_idx += 1

            # Step 2: Derivatives
            dxt = sp.diff(xt, t)
            dyt = sp.diff(yt, t)
            dzt = sp.diff(zt, t)

            dr_ltx = rf"\mathbf{{r}}'({t.name}) = \left( {expr_to_latex(dxt)}, {expr_to_latex(dyt)}"
            if zt != 0 or dzt != 0:
                dr_ltx += rf", {expr_to_latex(dzt)}"
            dr_ltx += r" \right)"

            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Tính đạo hàm vận tốc r'(t)",
                    description="Lấy đạo hàm từng thành phần theo tham số t:",
                    content=ExpressionStepContent(
                        expression_before="dr/dt",
                        expression_after=str((dxt, dyt, dzt)),
                        latex_before=r"\mathbf{r}'(t)",
                        latex_after=dr_ltx,
                    ),
                    equation_latex=dr_ltx,
                )
            )
            step_idx += 1

            # Step 3: Arc length differential ds = ||r'(t)|| dt
            sum_sq = sp.trigsimp(sp.simplify(dxt**2 + dyt**2 + dzt**2))
            integrand = sp.sqrt(sum_sq)

            ds_ltx = (
                rf"ds = \|\mathbf{{r}}'({t.name})\|\,d{t.name} = "
                rf"\sqrt{{ \left({expr_to_latex(dxt)}\right)^2 + \left({expr_to_latex(dyt)}\right)^2"
            )
            if zt != 0 or dzt != 0:
                ds_ltx += rf" + \left({expr_to_latex(dzt)}\right)^2"
            ds_ltx += rf" }}\,d{t.name} = {expr_to_latex(integrand)}\,d{t.name}"

            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Thiết lập vi phân độ dài cung ds",
                    description="Rút gọn vi phân độ dài cung ds = ||r'(t)|| dt:",
                    content=ExpressionStepContent(
                        expression_before="ds",
                        expression_after=str(integrand),
                        latex_before="ds",
                        latex_after=expr_to_latex(integrand),
                    ),
                    equation_latex=ds_ltx,
                )
            )
            step_idx += 1

            # Step 4: Integration
            try:
                final_val = sp.integrate(integrand, (t, a_bound, b_bound))
                final_val = sp.simplify(final_val)
            except Exception as exc:
                raise InvalidInputError(f"Không thể tính tích phân độ dài cung: {exc}") from exc

            int_ltx = (
                rf"L = \int_{{{expr_to_latex(a_bound)}}}^{{{expr_to_latex(b_bound)}}} {expr_to_latex(integrand)}\,d{t.name} = "
                rf"{expr_to_latex(final_val)}"
            )

            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Tính tích phân xác định tìm độ dài cung",
                    description="Thực hiện tích phân cận từ t_min đến t_max để ra kết quả độ dài cung L:",
                    content=ExpressionStepContent(
                        expression_before=f"integrate({integrand}, ({t}, {a_bound}, {b_bound}))",
                        expression_after=str(final_val),
                        latex_before=rf"\int_{{{expr_to_latex(a_bound)}}}^{{{expr_to_latex(b_bound)}}} {expr_to_latex(integrand)}\,d{t.name}",
                        latex_after=expr_to_latex(final_val),
                    ),
                    equation_latex=int_ltx,
                )
            )

            verification = self._verifier.verify_arc_length(
                final_val, integrand, t, a_bound, b_bound
            )

        else:
            # Explicit Cartesian curve: y = f(x)
            var_name = request.target_variable or "x"
            x = sp.Symbol(var_name)
            raw_a = str(params.get("lower_bound", "0")).strip()
            raw_b = str(params.get("upper_bound", "1")).strip()
            try:
                a_bound = parse_safe_expression(raw_a, evaluate=True)
                b_bound = parse_safe_expression(raw_b, evaluate=True)
            except Exception as exc:
                raise InvalidInputError(f"Cận x không hợp lệ: {exc}") from exc

            try:
                fx, _ = parse_mathematical_input(request.raw_input, var_name)
            except Exception as exc:
                raise InvalidInputError(f"Biểu thức hàm số y = f({var_name}) không hợp lệ: {exc}") from exc

            # Step 1: Function statement
            f_ltx = rf"y = f({x.name}) = {expr_to_latex(fx)}, \quad {x.name} \in [{expr_to_latex(a_bound)}, {expr_to_latex(b_bound)}]"
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Xác định hàm số đường cong",
                    description=f"Đường cong đồ thị y = f({x.name}) trên đoạn [{expr_to_latex(a_bound)}, {expr_to_latex(b_bound)}]:",
                    content=ExpressionStepContent(
                        expression_before=f"f({x.name})",
                        expression_after=str(fx),
                        latex_before=rf"f({x.name})",
                        latex_after=f_ltx,
                    ),
                    equation_latex=f_ltx,
                )
            )
            step_idx += 1

            # Step 2: Derivative f'(x)
            dfx = sp.diff(fx, x)
            df_ltx = rf"f'({x.name}) = \frac{{dy}}{{d{x.name}}} = {expr_to_latex(dfx)}"
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Tính đạo hàm f'(x)",
                    description=f"Tính đạo hàm bậc một của y theo {x.name}:",
                    content=ExpressionStepContent(
                        expression_before=f"diff(f, {x.name})",
                        expression_after=str(dfx),
                        latex_before=rf"\frac{{dy}}{{d{x.name}}}",
                        latex_after=df_ltx,
                    ),
                    equation_latex=df_ltx,
                )
            )
            step_idx += 1

            # Step 3: Arc length element ds = sqrt(1 + (f'(x))^2) dx
            sum_sq = sp.trigsimp(sp.simplify(1 + dfx**2))
            integrand = sp.sqrt(sum_sq)

            ds_ltx = (
                rf"ds = \sqrt{{1 + \left( f'({x.name}) \right)^2}}\,d{x.name} = "
                rf"\sqrt{{1 + \left({expr_to_latex(dfx)}\right)^2}}\,d{x.name} = {expr_to_latex(integrand)}\,d{x.name}"
            )
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Thiết lập vi phân độ dài cung ds",
                    description="Rút gọn biểu thức vi phân độ dài cung đồ thị:",
                    content=ExpressionStepContent(
                        expression_before="ds",
                        expression_after=str(integrand),
                        latex_before="ds",
                        latex_after=expr_to_latex(integrand),
                    ),
                    equation_latex=ds_ltx,
                )
            )
            step_idx += 1

            # Step 4: Definite integration
            try:
                final_val = sp.integrate(integrand, (x, a_bound, b_bound))
                final_val = sp.simplify(final_val)
            except Exception as exc:
                raise InvalidInputError(f"Không thể tính tích phân độ dài cung: {exc}") from exc

            int_ltx = (
                rf"L = \int_{{{expr_to_latex(a_bound)}}}^{{{expr_to_latex(b_bound)}}} {expr_to_latex(integrand)}\,d{x.name} = "
                rf"{expr_to_latex(final_val)}"
            )
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Tính tích phân xác định tìm độ dài cung",
                    description="Tính tích phân xác định để tìm độ dài cung cong L:",
                    content=ExpressionStepContent(
                        expression_before=f"integrate({integrand}, ({x}, {a_bound}, {b_bound}))",
                        expression_after=str(final_val),
                        latex_before=rf"\int_{{{expr_to_latex(a_bound)}}}^{{{expr_to_latex(b_bound)}}} {expr_to_latex(integrand)}\,d{x.name}",
                        latex_after=expr_to_latex(final_val),
                    ),
                    equation_latex=int_ltx,
                )
            )

            verification = self._verifier.verify_arc_length(
                final_val, integrand, x, a_bound, b_bound
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

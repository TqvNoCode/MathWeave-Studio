"""Solver for scalar and vector line integrals along parameterized curves."""

from __future__ import annotations

import time
import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionResponse, SolutionStep
from math_app.application.ports.solver import Solver
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.input.parser import parse_mathematical_input
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.verification.calculus.line_integral_verifier import LineIntegralVerifier


def _substitute_coords(expr: sp.Expr, mapping: dict[str, sp.Expr]) -> sp.Expr:
    """Safely substitute coordinates by symbol name to prevent assumption mismatch."""
    subs_list = [(s, mapping[s.name]) for s in expr.free_symbols if s.name in mapping]
    return expr.subs(subs_list)


class LineIntegralSolver(Solver):
    """Calculus solver for scalar and vector line integrals."""

    def __init__(self, verifier: LineIntegralVerifier | None = None) -> None:
        self._verifier = verifier or LineIntegralVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type == ProblemType.LINE_INTEGRAL

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        start_time = time.perf_counter()
        steps: list[SolutionStep] = []
        warnings: list[str] = []

        params = request.parameters
        param_var_name = str(params.get("param_var", "t")).strip()
        t = sp.Symbol(param_var_name, real=True)

        raw_t_min = str(params.get("t_min", "0")).strip()
        raw_t_max = str(params.get("t_max", "1")).strip()
        try:
            t_min = sp.sympify(raw_t_min)
            t_max = sp.sympify(raw_t_max)
        except Exception as exc:
            raise InvalidInputError(f"Cận tham số t không hợp lệ: {exc}") from exc

        # Parametric coordinates: x(t), y(t), z(t)
        raw_x = str(params.get("param_x", "t")).strip()
        raw_y = str(params.get("param_y", "0")).strip()
        raw_z = str(params.get("param_z", "0")).strip()

        try:
            xt, _ = parse_mathematical_input(raw_x, param_var_name)
            yt, _ = parse_mathematical_input(raw_y, param_var_name)
            zt, _ = parse_mathematical_input(raw_z, param_var_name)
        except Exception as exc:
            raise InvalidInputError(f"Biểu thức tham số hóa đường cong không hợp lệ: {exc}") from exc

        # Tangent derivatives
        dx_dt = sp.diff(xt, t)
        dy_dt = sp.diff(yt, t)
        dz_dt = sp.diff(zt, t)

        # Check mode: scalar or vector
        raw_in = request.raw_input.strip()
        mode = str(params.get("mode", "")).lower()
        is_vector = mode == "vector" or ("," in raw_in and mode != "scalar")

        step_idx = 1
        # Step 1: Parameterization setup
        r_vec_ltx = rf"\mathbf{{r}}({t.name}) = \left( {expr_to_latex(xt)}, {expr_to_latex(yt)}"
        if zt != 0 or dz_dt != 0:
            r_vec_ltx += rf", {expr_to_latex(zt)}"
        r_vec_ltx += rf" \right), \quad {t.name} \in [{expr_to_latex(t_min)}, {expr_to_latex(t_max)}]"

        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tham số hóa cung cong C",
                description="Xác định vectơ vị trí tham số hóa của đường cong C:",
                content=ExpressionStepContent(
                    expression_before="r(t)",
                    expression_after=str((xt, yt, zt)),
                    latex_before=r"\mathbf{r}(t)",
                    latex_after=r_vec_ltx,
                ),
                equation_latex=r_vec_ltx,
            )
        )
        step_idx += 1

        x_sym, y_sym, z_sym = sp.symbols("x y z")

        if is_vector:
            # Vector line integral: F = (P, Q) or (P, Q, R)
            parts = [p.strip() for p in raw_in.split(",")]
            if len(parts) < 2 or len(parts) > 3:
                raise InvalidInputError("Tích phân đường của trường vectơ yêu cầu 2 hoặc 3 thành phần phân tách bởi dấu phẩy: 'P, Q' hoặc 'P, Q, R'.")

            try:
                P = sp.sympify(parts[0])
                Q = sp.sympify(parts[1])
                R = sp.sympify(parts[2]) if len(parts) == 3 else sp.Integer(0)
            except Exception as exc:
                raise InvalidInputError(f"Hàm thành phần của trường vectơ không hợp lệ: {exc}") from exc

            # Step 2: Tangent vector and dot product F . dr
            tangent_ltx = rf"\mathbf{{r}}'({t.name}) = \left( {expr_to_latex(dx_dt)}, {expr_to_latex(dy_dt)}"
            if zt != 0 or dz_dt != 0:
                tangent_ltx += rf", {expr_to_latex(dz_dt)}"
            tangent_ltx += r" \right)"

            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Tính đạo hàm tiếp tuyến r'(t)",
                    description="Tính vectơ vận tốc / tiếp tuyến dọc theo đường cong:",
                    content=ExpressionStepContent(
                        expression_before="dr/dt",
                        expression_after=str((dx_dt, dy_dt, dz_dt)),
                        latex_before=r"\frac{d\mathbf{r}}{dt}",
                        latex_after=tangent_ltx,
                    ),
                    equation_latex=tangent_ltx,
                )
            )
            step_idx += 1

            # Substitution
            subs_dict = {"x": xt, "y": yt, "z": zt}
            Pt = _substitute_coords(P, subs_dict)
            Qt = _substitute_coords(Q, subs_dict)
            Rt = _substitute_coords(R, subs_dict)

            integrand_1d = sp.simplify(Pt * dx_dt + Qt * dy_dt + Rt * dz_dt)

            dot_ltx = (
                rf"\mathbf{{F}}(\mathbf{{r}}({t.name})) \cdot \mathbf{{r}}'({t.name})\,d{t.name} = "
                rf"\left( {expr_to_latex(Pt)} \right)\left( {expr_to_latex(dx_dt)} \right) + "
                rf"\left( {expr_to_latex(Qt)} \right)\left( {expr_to_latex(dy_dt)} \right)"
            )
            if zt != 0 or dz_dt != 0:
                dot_ltx += rf" + \left( {expr_to_latex(Rt)} \right)\left( {expr_to_latex(dz_dt)} \right)"
            dot_ltx += rf" = {expr_to_latex(integrand_1d)}"

            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Thay thế biến vào biểu thức vi phân công",
                    description="Tính tích vô hướng F(r(t)) · r'(t) để chuyển về tích phân một biến:",
                    content=ExpressionStepContent(
                        expression_before="F . dr",
                        expression_after=str(integrand_1d),
                        latex_before=r"\mathbf{F}\cdot d\mathbf{r}",
                        latex_after=expr_to_latex(integrand_1d),
                    ),
                    equation_latex=dot_ltx,
                )
            )
            step_idx += 1

            # Integration
            try:
                final_val = sp.integrate(integrand_1d, (t, t_min, t_max))
                final_val = sp.simplify(final_val)
            except Exception as exc:
                raise InvalidInputError(f"Không thể tính tích phân xác định theo tham số: {exc}") from exc

            integral_eval_ltx = (
                rf"\int_C \mathbf{{F}}\cdot d\mathbf{{r}} = "
                rf"\int_{{{expr_to_latex(t_min)}}}^{{{expr_to_latex(t_max)}}} \left( {expr_to_latex(integrand_1d)} \right) d{t.name} = "
                rf"{expr_to_latex(final_val)}"
            )

            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Tính tích phân xác định theo t",
                    description="Thực hiện tích phân cận từ t_min đến t_max để tìm kết quả công của trường lực:",
                    content=ExpressionStepContent(
                        expression_before=f"integrate({integrand_1d}, ({t}, {t_min}, {t_max}))",
                        expression_after=str(final_val),
                        latex_before=rf"\int_{{{expr_to_latex(t_min)}}}^{{{expr_to_latex(t_max)}}} {expr_to_latex(integrand_1d)}\,d{t.name}",
                        latex_after=expr_to_latex(final_val),
                    ),
                    equation_latex=integral_eval_ltx,
                )
            )
            step_idx += 1

            # Check orientation for vector line integral
            orientation = str(params.get("orientation", "forward")).lower()
            is_reverse = orientation in ("backward", "reverse", "nghich", "negative", "-")
            if is_reverse:
                final_val = -final_val
                steps.append(
                    SolutionStep(
                        step_number=step_idx,
                        rule_name="Đổi chiều đường cong (Hướng nghịch)",
                        description="Do đường cong C định hướng ngược chiều tham số (hướng nghịch), tích phân đổi dấu: ∫_{-C} F·dr = -∫_C F·dr",
                        content=ExpressionStepContent(
                            expression_before="int_C F . dr",
                            expression_after=str(final_val),
                            latex_before=r"\int_C \mathbf{F}\cdot d\mathbf{r}",
                            latex_after=rf"\int_{{-C}} \mathbf{{F}}\cdot d\mathbf{{r}} = -({expr_to_latex(-final_val)}) = {expr_to_latex(final_val)}",
                        ),
                        equation_latex=rf"\int_{{-C}} \mathbf{{F}}\cdot d\mathbf{{r}} = -({expr_to_latex(-final_val)}) = {expr_to_latex(final_val)}",
                    )
                )
                step_idx += 1
        else:
            is_reverse = False
            # Scalar line integral: \int_C f ds
            try:
                f_expr = sp.sympify(raw_in)
            except Exception as exc:
                raise InvalidInputError(f"Hàm dưới dấu tích phân đường vô hướng không hợp lệ: {exc}") from exc

            # ds = sqrt(x'^2 + y'^2 + z'^2) dt
            speed_sq = sp.trigsimp(sp.simplify(dx_dt**2 + dy_dt**2 + dz_dt**2))
            speed = sp.sqrt(speed_sq)
            ds_ltx = (
                rf"ds = \|\mathbf{{r}}'({t.name})\|\,d{t.name} = "
                rf"\sqrt{{ \left({expr_to_latex(dx_dt)}\right)^2 + \left({expr_to_latex(dy_dt)}\right)^2"
            )
            if zt != 0 or dz_dt != 0:
                ds_ltx += rf" + \left({expr_to_latex(dz_dt)}\right)^2"
            ds_ltx += rf" }}\,d{t.name} = {expr_to_latex(speed)}\,d{t.name}"

            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Tính vi phân độ dài cung ds",
                    description="Tính độ lớn vectơ tiếp tuyến ds = ||r'(t)|| dt:",
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

            # Substitute r(t) into f
            ft = _substitute_coords(f_expr, {"x": xt, "y": yt, "z": zt})
            integrand_1d = sp.simplify(ft * speed)

            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Thay thế biến vào hàm số f(x, y, z)",
                    description="Chuyển tích phân đường vô hướng thành tích phân xác định một biến theo t:",
                    content=ExpressionStepContent(
                        expression_before="f(r(t)) ds",
                        expression_after=str(integrand_1d),
                        latex_before=r"f(\mathbf{r}(t))\,ds",
                        latex_after=expr_to_latex(integrand_1d),
                    ),
                    equation_latex=rf"f(\mathbf{{r}}({t.name}))\|\mathbf{{r}}'({t.name})\| = {expr_to_latex(integrand_1d)}",
                )
            )
            step_idx += 1

            # Integration
            try:
                final_val = sp.integrate(integrand_1d, (t, t_min, t_max))
                final_val = sp.simplify(final_val)
            except Exception as exc:
                raise InvalidInputError(f"Không thể tính tích phân xác định theo tham số: {exc}") from exc

            integral_eval_ltx = (
                rf"\int_C f\,ds = \int_{{{expr_to_latex(t_min)}}}^{{{expr_to_latex(t_max)}}} \left( {expr_to_latex(integrand_1d)} \right) d{t.name} = "
                rf"{expr_to_latex(final_val)}"
            )

            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Tính tích phân xác định theo t",
                    description="Tính giá trị tích phân xác định trên đoạn tham số:",
                    content=ExpressionStepContent(
                        expression_before=f"integrate({integrand_1d}, ({t}, {t_min}, {t_max}))",
                        expression_after=str(final_val),
                        latex_before=rf"\int_{{{expr_to_latex(t_min)}}}^{{{expr_to_latex(t_max)}}} {expr_to_latex(integrand_1d)}\,d{t.name}",
                        latex_after=expr_to_latex(final_val),
                    ),
                    equation_latex=integral_eval_ltx,
                )
            )

        verification_integrand = (-integrand_1d if (is_vector and is_reverse) else integrand_1d)
        verification = self._verifier.verify_line_integral(
            final_val, verification_integrand, t, t_min, t_max, is_vector=is_vector
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

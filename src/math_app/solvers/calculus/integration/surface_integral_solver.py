"""Solver for scalar surface integrals and vector-field flux integrals."""

from __future__ import annotations

import time
import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionResponse, SolutionStep
from math_app.application.ports.solver import Solver
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.verification.calculus.surface_integral_verifier import SurfaceIntegralVerifier


def _substitute_coords(expr: sp.Expr, mapping: dict[str, sp.Expr]) -> sp.Expr:
    """Safely substitute coordinates by symbol name to prevent assumption mismatch."""
    subs_list = [(s, mapping[s.name]) for s in expr.free_symbols if s.name in mapping]
    return expr.subs(subs_list)


class SurfaceIntegralSolver(Solver):
    """Calculus solver for scalar and flux surface integrals over 2D surfaces in 3D."""

    def __init__(self, verifier: SurfaceIntegralVerifier | None = None) -> None:
        self._verifier = verifier or SurfaceIntegralVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type == ProblemType.SURFACE_INTEGRAL

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        start_time = time.perf_counter()
        steps: list[SolutionStep] = []
        warnings: list[str] = []

        params = request.parameters
        u_name = str(params.get("u_var", "x")).strip()
        v_name = str(params.get("v_var", "y")).strip()
        u = sp.Symbol(u_name)
        v = sp.Symbol(v_name)

        raw_u_min = str(params.get("u_min", "0")).strip()
        raw_u_max = str(params.get("u_max", "1")).strip()
        raw_v_min = str(params.get("v_min", "0")).strip()
        raw_v_max = str(params.get("v_max", "1")).strip()

        try:
            u_min = sp.sympify(raw_u_min)
            u_max = sp.sympify(raw_u_max)
            v_min = sp.sympify(raw_v_min)
            v_max = sp.sympify(raw_v_max)
        except Exception as exc:
            raise InvalidInputError(f"Cận của miền tham số u, v không hợp lệ: {exc}") from exc

        orientation = str(params.get("orientation", "upward")).lower()
        sign_orient = -1 if orientation in ("downward", "down", "negative", "-") else 1

        raw_in = request.raw_input.strip()
        mode = str(params.get("mode", "")).lower()
        is_flux = mode in ("flux", "vector") or ("," in raw_in and mode != "scalar")

        # Surface definition: explicit z = g(x, y) or parametric
        surf_type = str(params.get("surface_type", "explicit")).lower()
        raw_surf = str(params.get("surface_expr", "")).strip()
        if surf_type == "parametric" or ("param_x" in params and "param_y" in params and not raw_surf):
            is_explicit = False
        else:
            is_explicit = True

        step_idx = 1
        x_sym, y_sym, z_sym = sp.symbols("x y z")

        if is_explicit:
            # Explicit surface z = g(x, y)
            surface_str = raw_surf or "0"
            try:
                g_xy = sp.sympify(surface_str)
            except Exception as exc:
                raise InvalidInputError(f"Hàm mặt cong z = g({u_name}, {v_name}) không hợp lệ: {exc}") from exc

            gx = sp.diff(g_xy, u)
            gy = sp.diff(g_xy, v)

            surf_desc_ltx = (
                rf"S: z = g({u_name}, {v_name}) = {expr_to_latex(g_xy)}, \quad "
                rf"{u_name} \in [{expr_to_latex(u_min)}, {expr_to_latex(u_max)}], \; "
                rf"{v_name} \in [{expr_to_latex(v_min)}, {expr_to_latex(v_max)}]"
            )

            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Xác định phương trình mặt cong S",
                    description="Biểu diễn mặt cong dưới dạng đồ thị z = g(x, y) trên miền chữ nhật D:",
                    content=ExpressionStepContent(
                        expression_before="z = g(x, y)",
                        expression_after=str(g_xy),
                        latex_before="z = g(x, y)",
                        latex_after=surf_desc_ltx,
                    ),
                    equation_latex=surf_desc_ltx,
                )
            )
            step_idx += 1

            # Normal derivatives
            deriv_ltx = rf"\frac{{\partial g}}{{\partial {u_name}}} = {expr_to_latex(gx)}, \quad \frac{{\partial g}}{{\partial {v_name}}} = {expr_to_latex(gy)}"
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Tính các đạo hàm riêng",
                    description="Tính các đạo hàm riêng của hàm mặt cong theo từng biến tọa độ:",
                    content=ExpressionStepContent(
                        expression_before="grad g",
                        expression_after=str((gx, gy)),
                        latex_before=r"\nabla g",
                        latex_after=deriv_ltx,
                    ),
                    equation_latex=deriv_ltx,
                )
            )
            step_idx += 1

            if is_flux:
                # Vector field flux: F = (P, Q, R)
                parts = [p.strip() for p in raw_in.split(",")]
                if len(parts) != 3:
                    raise InvalidInputError("Thông lượng trường vectơ yêu cầu đúng 3 thành phần: 'P, Q, R'.")
                try:
                    P = sp.sympify(parts[0])
                    Q = sp.sympify(parts[1])
                    R = sp.sympify(parts[2])
                except Exception as exc:
                    raise InvalidInputError(f"Hàm thành phần của trường vectơ F không hợp lệ: {exc}") from exc

                # Substitute z = g(x, y) into P, Q, R
                subs_dict = {"x": u, "y": v, "z": g_xy}
                Pu = _substitute_coords(P, subs_dict)
                Qu = _substitute_coords(Q, subs_dict)
                Ru = _substitute_coords(R, subs_dict)

                # Upward normal element: dS_vec = (-gx, -gy, 1) dx dy
                # F . n dS = (-P gx - Q gy + R) dx dy
                integrand_2d = sp.simplify(sign_orient * (-Pu * gx - Qu * gy + Ru))

                orient_txt = "hướng lên (upward)" if sign_orient > 0 else "hướng xuống (downward)"
                flux_ltx = (
                    rf"d\mathbf{{S}} = {('+' if sign_orient > 0 else '-')}\left( -{expr_to_latex(gx)}\,\mathbf{{i}} - {expr_to_latex(gy)}\,\mathbf{{j}} + \mathbf{{k}} \right) d{u_name}\,d{v_name} \implies "
                    rf"\mathbf{{F}}\cdot d\mathbf{{S}} = \left( {expr_to_latex(integrand_2d)} \right) d{u_name}\,d{v_name}"
                )

                steps.append(
                    SolutionStep(
                        step_number=step_idx,
                        rule_name=f"Thiết lập vi phân thông lượng ({orient_txt})",
                        description=f"Tính tích vô hướng F · dS theo vectơ pháp tuyến định hướng:",
                        content=ExpressionStepContent(
                            expression_before="F . dS",
                            expression_after=str(integrand_2d),
                            latex_before=r"\mathbf{F}\cdot d\mathbf{S}",
                            latex_after=expr_to_latex(integrand_2d),
                        ),
                        equation_latex=flux_ltx,
                    )
                )
                step_idx += 1

            else:
                # Scalar surface integral: f(x, y, z) dS
                try:
                    f_xyz = sp.sympify(raw_in)
                except Exception as exc:
                    raise InvalidInputError(f"Hàm dưới dấu tích phân mặt vô hướng không hợp lệ: {exc}") from exc

                subs_dict = {"x": u, "y": v, "z": g_xy}
                fu = _substitute_coords(f_xyz, subs_dict)

                # dS = sqrt(1 + gx^2 + gy^2) dx dy
                norm_sq = sp.simplify(1 + gx**2 + gy**2)
                norm_N = sp.sqrt(norm_sq)
                integrand_2d = sp.simplify(fu * norm_N)

                ds_ltx = rf"dS = \sqrt{{ 1 + \left({expr_to_latex(gx)}\right)^2 + \left({expr_to_latex(gy)}\right)^2 }}\,d{u_name}\,d{v_name} = {expr_to_latex(norm_N)}\,d{u_name}\,d{v_name}"
                steps.append(
                    SolutionStep(
                        step_number=step_idx,
                        rule_name="Tính yếu tố diện tích vi phân dS",
                        description="Xác định vi phân diện tích dS = √(1 + gx² + gy²) dx dy:",
                        content=ExpressionStepContent(
                            expression_before="dS",
                            expression_after=str(norm_N),
                            latex_before="dS",
                            latex_after=expr_to_latex(norm_N),
                        ),
                        equation_latex=ds_ltx,
                    )
                )
                step_idx += 1

        else:
            # Parametric surface r(u, v) = (x(u,v), y(u,v), z(u,v))
            try:
                xu = sp.sympify(params.get("param_x", "u"))
                yu = sp.sympify(params.get("param_y", "v"))
                zu = sp.sympify(params.get("param_z", "0"))
            except Exception as exc:
                raise InvalidInputError(f"Tham số hóa mặt cong không hợp lệ: {exc}") from exc

            # Tangents ru, rv
            rx_u, ry_u, rz_u = sp.diff(xu, u), sp.diff(yu, u), sp.diff(zu, u)
            rx_v, ry_v, rz_v = sp.diff(xu, v), sp.diff(yu, v), sp.diff(zu, v)

            # Normal vector N = ru x rv
            Nx = ry_u * rz_v - rz_u * ry_v
            Ny = rz_u * rx_v - rx_u * rz_v
            Nz = rx_u * ry_v - ry_u * rx_v

            n_ltx = rf"\mathbf{{r}}_{u_name} \times \mathbf{{r}}_{v_name} = \left( {expr_to_latex(Nx)}, {expr_to_latex(Ny)}, {expr_to_latex(Nz)} \right)"
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Tính vectơ pháp tuyến ru × rv",
                    description="Tính tích có hướng của hai vectơ tiếp tuyến trên mặt tham số:",
                    content=ExpressionStepContent(
                        expression_before="ru x rv",
                        expression_after=str((Nx, Ny, Nz)),
                        latex_before=r"\mathbf{N} = \mathbf{r}_u \times \mathbf{r}_v",
                        latex_after=n_ltx,
                    ),
                    equation_latex=n_ltx,
                )
            )
            step_idx += 1

            if is_flux:
                parts = [p.strip() for p in raw_in.split(",")]
                if len(parts) != 3:
                    raise InvalidInputError("Thông lượng trường vectơ yêu cầu đúng 3 thành phần: 'P, Q, R'.")
                P = sp.sympify(parts[0])
                Q = sp.sympify(parts[1])
                R = sp.sympify(parts[2])

                subs_dict = {"x": xu, "y": yu, "z": zu}
                Pu = _substitute_coords(P, subs_dict)
                Qu = _substitute_coords(Q, subs_dict)
                Ru = _substitute_coords(R, subs_dict)

                integrand_2d = sp.simplify(sign_orient * (Pu * Nx + Qu * Ny + Ru * Nz))
            else:
                f_xyz = sp.sympify(raw_in)
                fu = _substitute_coords(f_xyz, {"x": xu, "y": yu, "z": zu})
                norm_N = sp.sqrt(sp.simplify(Nx**2 + Ny**2 + Nz**2))
                integrand_2d = sp.simplify(fu * norm_N)

        # Iterated integration over [v_min, v_max] then [u_min, u_max]
        try:
            inner_int = sp.integrate(integrand_2d, (v, v_min, v_max))
            final_val = sp.integrate(inner_int, (u, u_min, u_max))
            final_val = sp.simplify(final_val)
        except Exception as exc:
            raise InvalidInputError(f"Không thể tính tích phân lặp 2 lớp trên miền tham số: {exc}") from exc

        iter_ltx = (
            rf"\iint_S \dots = "
            rf"\int_{{{expr_to_latex(u_min)}}}^{{{expr_to_latex(u_max)}}} d{u_name} "
            rf"\int_{{{expr_to_latex(v_min)}}}^{{{expr_to_latex(v_max)}}} \left( {expr_to_latex(integrand_2d)} \right) d{v_name} = "
            rf"{expr_to_latex(final_val)}"
        )

        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tính tích phân bội hai lặp trên miền D",
                description="Thực hiện tích phân hai lớp lần lượt theo biến thứ nhất và biến thứ hai:",
                content=ExpressionStepContent(
                    expression_before=f"integrate({integrand_2d}, ({v}, {v_min}, {v_max}), ({u}, {u_min}, {u_max}))",
                    expression_after=str(final_val),
                    latex_before=rf"\iint_D {expr_to_latex(integrand_2d)}\,d{u_name}d{v_name}",
                    latex_after=expr_to_latex(final_val),
                ),
                equation_latex=iter_ltx,
            )
        )

        verification = self._verifier.verify_surface_integral(
            final_val, integrand_2d, u, u_min, u_max, v, v_min, v_max, is_flux=is_flux
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

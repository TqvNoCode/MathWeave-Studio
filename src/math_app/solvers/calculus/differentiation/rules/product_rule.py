"""Product rule for differentiation: d/dx(u * v) = u'v + uv'."""

from __future__ import annotations

from typing import Any
import sympy as sp

from math_app.rendering.latex.formatter import expr_to_latex
from math_app.solvers.calculus.differentiation.rules.base import DifferentiationRule


class ProductRule(DifferentiationRule):
    """Applies the product rule to products of variable terms."""

    def can_apply(self, expr: sp.Expr, var: sp.Symbol) -> bool:
        if not isinstance(expr, sp.Mul):
            return False
        var_factors = [arg for arg in expr.args if arg.has(var)]
        return len(var_factors) >= 2

    def apply(
        self,
        expr: sp.Expr,
        var: sp.Symbol,
        engine: Any,
        builder: Any,
    ) -> sp.Expr:
        # Split into first factor and rest of factors
        args = list(expr.args)
        u = args[0]
        v = sp.Mul(*args[1:])

        sub_builder_u = builder.create_sub_builder()
        du = engine.differentiate(u, var, sub_builder_u)

        sub_builder_v = builder.create_sub_builder()
        dv = engine.differentiate(v, var, sub_builder_v)

        result = du * v + u * dv

        combined_substeps = sub_builder_u.get_steps() + sub_builder_v.get_steps()

        u_ltx = expr_to_latex(u)
        v_ltx = expr_to_latex(v)
        du_ltx = expr_to_latex(du)
        dv_ltx = expr_to_latex(dv)
        res_ltx = expr_to_latex(result)

        aligned_eq = (
            f"\\begin{{aligned}}\n"
            f"  f'({var.name})\n"
            f"  &= \\frac{{d}}{{d{var.name}}}\\left({u_ltx} \\cdot {v_ltx}\\right) \\\\\n"
            f"  &= \\left(\\frac{{d}}{{d{var.name}}}({u_ltx})\\right){v_ltx} + {u_ltx}\\left(\\frac{{d}}{{d{var.name}}}({v_ltx})\\right) \\\\\n"
            f"  &= ({du_ltx}){v_ltx} + {u_ltx}({dv_ltx}) \\\\\n"
            f"  &= {res_ltx}\n"
            f"\\end{{aligned}}"
        )

        builder.add_step(
            rule_name="Product Rule",
            rule_name_vi="Quy tắc đạo hàm của tích",
            title="Áp dụng quy tắc đạo hàm của tích",
            description=(
                f"Áp dụng quy tắc đạo hàm của tích hai hàm số (u · v)' = u'v + uv' "
                f"với u = {u_ltx} và v = {v_ltx}:"
            ),
            before=expr,
            after=result,
            substeps=combined_substeps,
            notes="Tách thành các nhân tử và tính đạo hàm từng phần",
            equation_latex=aligned_eq,
        )
        return result

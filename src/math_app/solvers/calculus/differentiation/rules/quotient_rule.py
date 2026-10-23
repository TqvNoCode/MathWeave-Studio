"""Quotient rule for differentiation: d/dx(u / v) = (u'v - uv') / v^2."""

from __future__ import annotations

from typing import Any
import sympy as sp

from math_app.rendering.latex.formatter import expr_to_latex
from math_app.solvers.calculus.differentiation.rules.base import DifferentiationRule


class QuotientRule(DifferentiationRule):
    """Applies the quotient rule to rational expressions."""

    def can_apply(self, expr: sp.Expr, var: sp.Symbol) -> bool:
        if not isinstance(expr, sp.Mul):
            return False
        # Check if any factor has negative exponent containing var
        has_denominator_with_var = any(
            isinstance(arg, sp.Pow) and arg.exp.is_number and arg.exp < 0 and arg.base.has(var)
            for arg in expr.args
        )
        return has_denominator_with_var

    def apply(
        self,
        expr: sp.Expr,
        var: sp.Symbol,
        engine: Any,
        builder: Any,
    ) -> sp.Expr:
        num_factors = []
        den_factors = []

        for arg in expr.args:
            if isinstance(arg, sp.Pow) and arg.exp.is_number and arg.exp < 0:
                # e.g., (x + 1)**(-1) -> denominator factor (x + 1)**(1)
                den_factors.append(arg.base ** (-arg.exp))
            else:
                num_factors.append(arg)

        u = sp.Mul(*num_factors) if num_factors else sp.Integer(1)
        v = sp.Mul(*den_factors)

        sub_builder_u = builder.create_sub_builder()
        du = engine.differentiate(u, var, sub_builder_u)

        sub_builder_v = builder.create_sub_builder()
        dv = engine.differentiate(v, var, sub_builder_v)

        result = (du * v - u * dv) / (v ** 2)

        combined_substeps = sub_builder_u.get_steps() + sub_builder_v.get_steps()

        u_ltx = expr_to_latex(u)
        v_ltx = expr_to_latex(v)
        du_ltx = expr_to_latex(du)
        dv_ltx = expr_to_latex(dv)
        res_ltx = expr_to_latex(result)

        aligned_eq = (
            f"\\begin{{aligned}}\n"
            f"  f'({var.name})\n"
            f"  &= \\frac{{d}}{{d{var.name}}}\\left(\\frac{{{u_ltx}}}{{{v_ltx}}}\\right) \\\\\n"
            f"  &= \\frac{{\\left(\\frac{{d}}{{d{var.name}}}({u_ltx})\\right)({v_ltx}) - ({u_ltx})\\left(\\frac{{d}}{{d{var.name}}}({v_ltx})\\right)}}{{\\left({v_ltx}\\right)^2}} \\\\\n"
            f"  &= \\frac{{({du_ltx})({v_ltx}) - ({u_ltx})({dv_ltx})}}{{\\left({v_ltx}\\right)^2}} \\\\\n"
            f"  &= {res_ltx}\n"
            f"\\end{{aligned}}"
        )

        builder.add_step(
            rule_name="Quotient Rule",
            rule_name_vi="Quy tắc đạo hàm của thương",
            title="Áp dụng quy tắc đạo hàm của thương",
            description=(
                f"Áp dụng quy tắc đạo hàm của thương hai hàm số [u / v]' = (u'v - uv') / v^2 "
                f"với tử số u = {u_ltx} và mẫu số v = {v_ltx}:"
            ),
            before=expr,
            after=result,
            substeps=combined_substeps,
            notes="Điều kiện mẫu số xác định",
            assumptions=(f"{v_ltx} \\ne 0",),
            equation_latex=aligned_eq,
        )
        return result

"""Chain rule for differentiation: d/dx(f(g(x))) = f'(g(x)) * g'(x)."""

from __future__ import annotations

from typing import Any
import sympy as sp

from math_app.rendering.latex.formatter import expr_to_latex
from math_app.solvers.calculus.differentiation.rules.base import DifferentiationRule


class ChainRule(DifferentiationRule):
    """Applies the chain rule to composite functions and generalized powers."""

    COMPOSITE_FUNCS = (
        sp.sin, sp.cos, sp.tan, sp.sec, sp.csc, sp.cot,
        sp.asin, sp.acos, sp.atan,
        sp.exp, sp.log, sp.sqrt,
    )

    def can_apply(self, expr: sp.Expr, var: sp.Symbol) -> bool:
        # Composite elementary functions: e.g. sin(g(x)), cos(g(x)), exp(g(x)), log(g(x)) where g(x) != var
        if isinstance(expr, self.COMPOSITE_FUNCS):
            inner = expr.args[0]
            return inner != var and inner.has(var)

        # Generalized power rule: (g(x))^n where g(x) != var and n is constant
        if isinstance(expr, sp.Pow):
            base, exp = expr.args
            return base != var and base.has(var) and not exp.has(var)

        return False

    def apply(
        self,
        expr: sp.Expr,
        var: sp.Symbol,
        engine: Any,
        builder: Any,
    ) -> sp.Expr:
        u_sym = sp.Dummy("u")

        if isinstance(expr, self.COMPOSITE_FUNCS):
            inner = expr.args[0]
            outer_expr = type(expr)(u_sym)
        elif isinstance(expr, sp.Pow):
            inner, exp = expr.args
            outer_expr = u_sym ** exp
        else:
            raise ValueError(f"Chain rule cannot identify outer/inner structure of {expr}")

        # Compute outer derivative d/du [outer_expr]
        d_outer_du = sp.diff(outer_expr, u_sym)
        d_outer_at_inner = d_outer_du.subs(u_sym, inner)

        # Recursively compute inner derivative d/dx [inner]
        sub_builder = builder.create_sub_builder()
        d_inner = engine.differentiate(inner, var, sub_builder)

        result = d_outer_at_inner * d_inner

        outer_ltx = expr_to_latex(outer_expr)
        inner_ltx = expr_to_latex(inner)
        d_outer_ltx = expr_to_latex(d_outer_at_inner)
        d_inner_ltx = expr_to_latex(d_inner)
        res_ltx = expr_to_latex(result)

        aligned_eq = (
            f"\\begin{{aligned}}\n"
            f"  f'({var.name})\n"
            f"  &= \\frac{{d}}{{d{var.name}}}\\left({expr_to_latex(expr)}\\right) \\\\\n"
            f"  &= {d_outer_ltx} \\cdot \\frac{{d}}{{d{var.name}}}\\left({inner_ltx}\\right) \\\\\n"
            f"  &= {d_outer_ltx} \\cdot ({d_inner_ltx}) \\\\\n"
            f"  &= {res_ltx}\n"
            f"\\end{{aligned}}"
        )

        builder.add_step(
            rule_name="Chain Rule",
            rule_name_vi="Quy tắc đạo hàm của hàm hợp",
            title="Áp dụng quy tắc đạo hàm của hàm hợp",
            description=(
                f"Áp dụng quy tắc đạo hàm hàm hợp [f(g({var.name}))]' = f'(g({var.name})) · g'({var.name}) "
                f"với hàm ngoài f(u) = {outer_ltx} và biểu thức trong u = {inner_ltx}:"
            ),
            before=expr,
            after=result,
            substeps=sub_builder.get_steps(),
            notes=f"Hàm ngoài {outer_ltx}, hàm trong {inner_ltx}",
            equation_latex=aligned_eq,
        )
        return result

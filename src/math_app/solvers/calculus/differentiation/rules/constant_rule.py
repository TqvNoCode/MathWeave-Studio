"""Constant and Constant-Multiple differentiation rules."""

from __future__ import annotations

from typing import Any
import sympy as sp

from math_app.rendering.latex.formatter import expr_to_latex
from math_app.solvers.calculus.differentiation.rules.base import DifferentiationRule


class ConstantRule(DifferentiationRule):
    """Differentiates expressions that are constant with respect to the target variable."""

    def can_apply(self, expr: sp.Expr, var: sp.Symbol) -> bool:
        return not expr.has(var)

    def apply(
        self,
        expr: sp.Expr,
        var: sp.Symbol,
        engine: Any,
        builder: Any,
    ) -> sp.Expr:
        result = sp.Integer(0)
        builder.add_step(
            rule_name="Constant Rule",
            rule_name_vi="Quy tắc đạo hàm của hằng số",
            title="Áp dụng quy tắc đạo hàm của hằng số",
            description=f"Đạo hàm của hằng số không phụ thuộc vào biến {var.name} bằng 0: d/d{var.name}({expr}) = 0.",
            before=expr,
            after=result,
            equation_latex=f"\\frac{{d}}{{d{var.name}}}({expr_to_latex(expr)}) = 0",
        )
        return result


class ConstantMultipleRule(DifferentiationRule):
    """Pulls out constant factor: d/dx(c * u) = c * d/dx(u)."""

    def can_apply(self, expr: sp.Expr, var: sp.Symbol) -> bool:
        if not isinstance(expr, sp.Mul):
            return False
        const_factors, var_factors = [], []
        for factor in expr.args:
            if factor.has(var):
                var_factors.append(factor)
            else:
                const_factors.append(factor)
        return bool(const_factors) and bool(var_factors)

    def apply(
        self,
        expr: sp.Expr,
        var: sp.Symbol,
        engine: Any,
        builder: Any,
    ) -> sp.Expr:
        const_factors, var_factors = [], []
        for factor in expr.args:
            if factor.has(var):
                var_factors.append(factor)
            else:
                const_factors.append(factor)

        c = sp.Mul(*const_factors)
        u = sp.Mul(*var_factors)

        sub_builder = builder.create_sub_builder()
        du = engine.differentiate(u, var, sub_builder)
        result = c * du

        c_ltx = expr_to_latex(c)
        u_ltx = expr_to_latex(u)
        du_ltx = expr_to_latex(du)
        res_ltx = expr_to_latex(result)

        aligned_eq = (
            f"\\begin{{aligned}}\n"
            f"  f'({var.name})\n"
            f"  &= \\frac{{d}}{{d{var.name}}}\\left({c_ltx} \\cdot {u_ltx}\\right) \\\\\n"
            f"  &= {c_ltx} \\cdot \\frac{{d}}{{d{var.name}}}\\left({u_ltx}\\right) \\\\\n"
            f"  &= {c_ltx} \\cdot ({du_ltx}) \\\\\n"
            f"  &= {res_ltx}\n"
            f"\\end{{aligned}}"
        )

        builder.add_step(
            rule_name="Constant Multiple Rule",
            rule_name_vi="Quy tắc nhân với hằng số",
            title="Đưa hằng số ra ngoài dấu đạo hàm",
            description=f"Đưa hệ số hằng số {c_ltx} ra ngoài dấu đạo hàm theo công thức [c · u]' = c · u':",
            before=expr,
            after=result,
            substeps=sub_builder.get_steps(),
            notes=f"Hằng số nhân c = {c_ltx}",
            equation_latex=aligned_eq,
        )
        return result

"""Power rule for differentiation: d/dx(x^n) = n * x^(n - 1)."""

from __future__ import annotations

from typing import Any
import sympy as sp

from math_app.rendering.latex.formatter import expr_to_latex
from math_app.solvers.calculus.differentiation.rules.base import DifferentiationRule


class PowerRule(DifferentiationRule):
    """Applies the elementary power rule."""

    def can_apply(self, expr: sp.Expr, var: sp.Symbol) -> bool:
        if expr == var:
            return True
        if isinstance(expr, sp.Pow):
            base, exp = expr.args
            return base == var and not exp.has(var)
        return False

    def apply(
        self,
        expr: sp.Expr,
        var: sp.Symbol,
        engine: Any,
        builder: Any,
    ) -> sp.Expr:
        is_partial = getattr(engine, "is_partial", False)
        diff_op = rf"\frac{{\partial}}{{\partial {var.name}}}" if is_partial else rf"\frac{{d}}{{d{var.name}}}"
        lhs_op = rf"\frac{{\partial f}}{{\partial {var.name}}}" if is_partial else rf"f'({var.name})"

        if expr == var:
            result = sp.Integer(1)
            builder.add_step(
                rule_name="Identity Variable Rule",
                rule_name_vi="Quy tắc đạo hàm của hàm đồng nhất",
                title="Áp dụng quy tắc đạo hàm của biến số đồng nhất",
                description=f"Đạo hàm của biến số ${var.name}$ theo chính nó bằng $1$: ${diff_op}({var.name}) = 1$.",
                before=expr,
                after=result,
                equation_latex=f"{lhs_op} = {diff_op}({var.name}) = 1",
            )
            return result

        base, exp = expr.args
        result = exp * (base ** (exp - 1))
        builder.add_step(
            rule_name="Power Rule",
            rule_name_vi="Quy tắc đạo hàm của lũy thừa",
            title="Áp dụng quy tắc đạo hàm của lũy thừa",
            description=(
                f"Với hàm số dạng lũy thừa $u({var.name}) = {var.name}^n$, ta có $u'({var.name}) = n \\cdot {var.name}^{{n-1}}$. "
                f"Áp dụng quy tắc này cho hàm số đã cho:"
            ),
            before=expr,
            after=result,
            notes=f"Số mũ $n = {expr_to_latex(exp)}$",
            equation_latex=f"{lhs_op} = {diff_op}\\left({expr_to_latex(expr)}\\right) = {exp}{var.name}^{{{exp}-1}} = {expr_to_latex(result)}",
        )
        return result

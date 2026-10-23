"""Exponential, Logarithmic, and Radical differentiation rules."""

from __future__ import annotations

from typing import Any
import sympy as sp

from math_app.solvers.calculus.differentiation.rules.base import DifferentiationRule


class ExpLogRule(DifferentiationRule):
    """Differentiates elementary exponential, natural logarithm, and square root functions."""

    def can_apply(self, expr: sp.Expr, var: sp.Symbol) -> bool:
        if isinstance(expr, (sp.exp, sp.log)):
            return expr.args[0] == var
        if isinstance(expr, sp.Pow):
            base, exp = expr.args
            return base == var and exp == sp.Rational(1, 2)
        return False

    def apply(
        self,
        expr: sp.Expr,
        var: sp.Symbol,
        engine: Any,
        builder: Any,
    ) -> sp.Expr:
        if isinstance(expr, sp.exp):
            result = sp.exp(var)
            rule_name = "Exponential Rule"
            rule_name_vi = "Quy tắc đạo hàm của hàm mũ"
            title = "Áp dụng quy tắc đạo hàm của hàm mũ"
            desc = f"Đạo hàm của hàm mũ tự nhiên e^{var.name} là chính nó: d/d{var.name}(e^{var.name}) = e^{var.name}."
        elif isinstance(expr, sp.log):
            result = 1 / var
            rule_name = "Logarithmic Rule"
            rule_name_vi = "Quy tắc đạo hàm của hàm logarit"
            title = "Áp dụng quy tắc đạo hàm của hàm logarit"
            desc = f"Đạo hàm của hàm logarit tự nhiên ln({var.name}) là 1/{var.name}: d/d{var.name}(ln({var.name})) = 1/{var.name}."
        elif isinstance(expr, sp.Pow):
            result = 1 / (2 * sp.sqrt(var))
            rule_name = "Square Root Rule"
            rule_name_vi = "Quy tắc đạo hàm của căn bậc hai"
            title = "Áp dụng quy tắc đạo hàm của căn bậc hai"
            desc = f"Đạo hàm của căn bậc hai √{var.name} là 1 / (2√{var.name}): d/d{var.name}(√{var.name}) = 1/(2√{var.name})."
        else:
            result = sp.diff(expr, var)
            rule_name = "Elementary Rule"
            rule_name_vi = "Quy tắc đạo hàm hàm sơ cấp"
            title = "Áp dụng quy tắc đạo hàm hàm sơ cấp"
            desc = f"Tính đạo hàm của {expr} theo biến {var.name}."

        builder.add_step(
            rule_name=rule_name,
            rule_name_vi=rule_name_vi,
            title=title,
            description=desc,
            before=expr,
            after=result,
        )
        return result

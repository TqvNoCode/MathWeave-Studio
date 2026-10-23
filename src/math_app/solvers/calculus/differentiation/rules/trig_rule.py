"""Trigonometric differentiation rules: sin, cos, tan."""

from __future__ import annotations

from typing import Any
import sympy as sp

from math_app.solvers.calculus.differentiation.rules.base import DifferentiationRule


class TrigRule(DifferentiationRule):
    """Differentiates elementary trigonometric functions whose argument is the single target variable."""

    TRIG_FUNCS = (sp.sin, sp.cos, sp.tan, sp.sec, sp.csc, sp.cot, sp.asin, sp.acos, sp.atan)

    def can_apply(self, expr: sp.Expr, var: sp.Symbol) -> bool:
        if not isinstance(expr, self.TRIG_FUNCS):
            return False
        return expr.args[0] == var

    def apply(
        self,
        expr: sp.Expr,
        var: sp.Symbol,
        engine: Any,
        builder: Any,
    ) -> sp.Expr:
        arg = expr.args[0]

        if isinstance(expr, sp.sin):
            result = sp.cos(arg)
            desc = f"Đạo hàm của sin({var.name}) là cos({var.name}) [d/d{var.name}(sin) = cos]."
        elif isinstance(expr, sp.cos):
            result = -sp.sin(arg)
            desc = f"Đạo hàm của cos({var.name}) là -sin({var.name}) [d/d{var.name}(cos) = -sin]."
        elif isinstance(expr, sp.tan):
            result = 1 / (sp.cos(arg) ** 2)
            desc = f"Đạo hàm của tan({var.name}) là 1 / cos({var.name})^2 (hoặc sec({var.name})^2)."
        elif isinstance(expr, sp.sec):
            result = sp.sec(arg) * sp.tan(arg)
            desc = f"Đạo hàm của sec({var.name}) là sec({var.name}) * tan({var.name})."
        elif isinstance(expr, sp.csc):
            result = -sp.csc(arg) * sp.cot(arg)
            desc = f"Đạo hàm của csc({var.name}) là -csc({var.name}) * cot({var.name})."
        elif isinstance(expr, sp.cot):
            result = -1 / (sp.sin(arg) ** 2)
            desc = f"Đạo hàm của cot({var.name}) là -1 / sin({var.name})^2 (hoặc -csc({var.name})^2)."
        elif isinstance(expr, sp.asin):
            result = 1 / sp.sqrt(1 - arg ** 2)
            desc = f"Đạo hàm của arcsin({var.name}) là 1 / sqrt(1 - {var.name}^2)."
        elif isinstance(expr, sp.acos):
            result = -1 / sp.sqrt(1 - arg ** 2)
            desc = f"Đạo hàm của arccos({var.name}) là -1 / sqrt(1 - {var.name}^2)."
        elif isinstance(expr, sp.atan):
            result = 1 / (1 + arg ** 2)
            desc = f"Đạo hàm của arctan({var.name}) là 1 / (1 + {var.name}^2)."
        else:
            result = sp.diff(expr, var)
            desc = f"Differentiate {expr}."

        builder.add_step(
            rule_name="Trigonometric Rule",
            rule_name_vi="Quy tắc đạo hàm của hàm lượng giác",
            title="Áp dụng quy tắc đạo hàm của hàm lượng giác",
            description=desc,
            before=expr,
            after=result,
        )
        return result

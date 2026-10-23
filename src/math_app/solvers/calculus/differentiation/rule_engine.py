"""Rule engine for pattern matching and applying differentiation rules."""

from __future__ import annotations

import time
import sympy as sp

from math_app.domain.exceptions import ComputationTimeoutError
from math_app.solvers.calculus.differentiation.rules.base import DifferentiationRule
from math_app.solvers.calculus.differentiation.rules.chain_rule import ChainRule
from math_app.solvers.calculus.differentiation.rules.constant_rule import (
    ConstantMultipleRule,
    ConstantRule,
)
from math_app.solvers.calculus.differentiation.rules.exp_log_rule import ExpLogRule
from math_app.solvers.calculus.differentiation.rules.power_rule import PowerRule
from math_app.solvers.calculus.differentiation.rules.product_rule import ProductRule
from math_app.solvers.calculus.differentiation.rules.quotient_rule import QuotientRule
from math_app.solvers.calculus.differentiation.rules.sum_rule import SumRule
from math_app.solvers.calculus.differentiation.rules.trig_rule import TrigRule
from math_app.solvers.calculus.differentiation.step_builder import DifferentiationStepBuilder

SOFT_TIMEOUT_SECONDS = 2.0


class DifferentiationRuleEngine:
    """Dispatches symbolic expressions to pedagogical differentiation rules."""

    def __init__(self, rules: list[DifferentiationRule] | None = None) -> None:
        if rules is None:
            # Pedagogical dispatch order is critical:
            # 1. Pure constants
            # 2. Constant multiples
            # 3. Sums / differences (linearity)
            # 4. Quotients (before general products)
            # 5. Products
            # 6. Elementary trig (sin(x), cos(x))
            # 7. Powers (x^n, x)
            # 8. Chain rule (composite functions and (g(x))^n)
            self._rules: list[DifferentiationRule] = [
                ConstantRule(),
                ConstantMultipleRule(),
                SumRule(),
                QuotientRule(),
                ProductRule(),
                TrigRule(),
                ExpLogRule(),
                PowerRule(),
                ChainRule(),
            ]
        else:
            self._rules = rules

        self._fallback_occurred = False
        self._start_time = 0.0

    def differentiate(
        self,
        expr: sp.Expr,
        var: sp.Symbol,
        builder: DifferentiationStepBuilder,
    ) -> sp.Expr:
        if self._start_time == 0.0:
            self._start_time = time.perf_counter()
        elif (time.perf_counter() - self._start_time) > SOFT_TIMEOUT_SECONDS:
            raise ComputationTimeoutError(
                f"Differentiation exceeded soft execution limit of {SOFT_TIMEOUT_SECONDS}s."
            )

        # Match against configured rules
        for rule in self._rules:
            if rule.can_apply(expr, var):
                return rule.apply(expr, var, self, builder)

        # Fallback if no pedagogical rule matched
        self._fallback_occurred = True
        direct_result = sp.diff(expr, var)
        builder.add_step(
            rule_name="Symbolic Differentiation Engine",
            rule_name_vi="Tính toán ký hiệu trực tiếp",
            title="Tính đạo hàm trực tiếp bằng bộ giải ký hiệu",
            description=(
                f"Đạo hàm của biểu thức được tính toán trực tiếp bằng bộ giải ký hiệu toán học "
                f"do hệ thống chưa có quy tắc sư phạm phân rã chi tiết cho cấu trúc này."
            ),
            before=expr,
            after=direct_result,
            notes="Giới hạn phân rã sư phạm",
        )
        return direct_result

    @property
    def had_fallback(self) -> bool:
        return self._fallback_occurred

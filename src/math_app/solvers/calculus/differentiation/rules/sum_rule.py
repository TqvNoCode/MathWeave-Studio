"""Sum and difference rule for differentiation: d/dx(u + v) = u' + v'."""

from __future__ import annotations

from typing import Any
import sympy as sp

from math_app.solvers.calculus.differentiation.rules.base import DifferentiationRule
from math_app.solvers.calculus.pedagogical_derivation import (
    format_derivative_sum_decomposition,
    format_derivative_term_steps,
    sort_terms_pedagogical,
)


class SumRule(DifferentiationRule):
    """Applies linearity over sums and differences."""

    def can_apply(self, expr: sp.Expr, var: sp.Symbol) -> bool:
        return isinstance(expr, sp.Add)

    def apply(
        self,
        expr: sp.Expr,
        var: sp.Symbol,
        engine: Any,
        builder: Any,
    ) -> sp.Expr:
        terms = sort_terms_pedagogical(expr.args, var)
        decomposed_str, aligned_step1 = format_derivative_sum_decomposition(expr, terms, var)
        combined_raw, aligned_step2, result, term_substeps = format_derivative_term_steps(terms, var)

        # Step 1: Linearity / Sum and Difference Rule
        builder.add_step(
            rule_name="Sum / Difference Rule",
            rule_name_vi="Quy tắc đạo hàm của tổng và hiệu",
            title="Áp dụng quy tắc đạo hàm của tổng và hiệu",
            description="Đạo hàm của một tổng hoặc hiệu bằng tổng hoặc hiệu đạo hàm của từng số hạng theo tính chất tuyến tính. Vì vậy:",
            before=expr,
            after=decomposed_str,
            equation_latex=aligned_step1,
            substeps=tuple(term_substeps),
            notes=f"Phân tích biểu thức thành {len(terms)} số hạng độc lập",
        )

        # Step 2: Term-by-term Differentiation
        builder.add_step(
            rule_name="Power Rule",
            rule_name_vi="Áp dụng các quy tắc đạo hàm cho từng số hạng",
            title="Áp dụng các quy tắc đạo hàm cho từng số hạng",
            description="Tính đạo hàm cho từng số hạng độc lập và kết hợp các kết quả:",
            before=decomposed_str,
            after=result,
            equation_latex=aligned_step2,
            substeps=tuple(term_substeps),
            notes="Đạo hàm từng số hạng",
        )

        return result

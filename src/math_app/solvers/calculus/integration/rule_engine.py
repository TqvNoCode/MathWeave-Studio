"""Pedagogical integration rule engine."""

from __future__ import annotations

import time
import sympy as sp

from math_app.domain.exceptions import ComputationTimeoutError
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.solvers.calculus.integration.step_builder import IntegrationStepBuilder
from math_app.solvers.calculus.pedagogical_derivation import (
    format_integral_sum_decomposition,
    format_integral_term_steps,
    sort_terms_pedagogical,
)

SOFT_TIMEOUT_SECONDS = 3.0


class IntegrationRuleEngine:
    """Dispatches symbolic expressions to pedagogical integration rules."""

    def __init__(self) -> None:
        self._fallback_occurred = False
        self._start_time = 0.0

    def integrate(
        self,
        expr: sp.Expr,
        var: sp.Symbol,
        builder: IntegrationStepBuilder,
        is_definite: bool = False,
    ) -> sp.Expr:
        if self._start_time == 0.0:
            self._start_time = time.perf_counter()
        elif (time.perf_counter() - self._start_time) > SOFT_TIMEOUT_SECONDS:
            raise ComputationTimeoutError("Thời gian tính toán tích phân vượt quá giới hạn an toàn.")

        # 1. Constant rule: c -> c*x
        if not expr.has(var):
            res = expr * var
            latex_after = f"{expr_to_latex(res)} + C" if not is_definite else expr_to_latex(res)
            eq_latex = f"\\int {expr_to_latex(expr)}\\,d{var.name} = {latex_after}"
            builder.add_step(
                rule_name="Quy tắc hằng số và hằng số tích phân C" if not is_definite else "Quy tắc hằng số",
                title="Áp dụng quy tắc tích phân của hằng số",
                description=f"Tích phân của hằng số không phụ thuộc vào {var.name}:",
                before=expr,
                after=latex_after,
                equation_latex=eq_latex,
                notes="Hằng số C" if not is_definite else None,
            )
            return res

        # 2. Identity variable rule: x -> x^2 / 2
        if expr == var:
            res = (var ** 2) / 2
            latex_after = f"\\frac{{{var.name}^2}}{{2}} + C" if not is_definite else f"\\frac{{{var.name}^2}}{{2}}"
            eq_latex = f"\\int {var.name}\\,d{var.name} = \\frac{{{var.name}^2}}{{2}}" + (" + C" if not is_definite else "")
            builder.add_step(
                rule_name="Quy tắc lũy thừa và hằng số tích phân C" if not is_definite else "Quy tắc lũy thừa cơ bản",
                title="Áp dụng quy tắc tích phân của lũy thừa",
                description="Áp dụng công thức nguyên hàm cơ bản cho hàm số bậc nhất với n = 1:",
                before=expr,
                after=latex_after,
                equation_latex=eq_latex,
                assumptions=(f"Với n = 1: \\int {var.name}\\,d{var.name} = \\frac{{{var.name}^2}}{{2}} + C",) if not is_definite else (),
                notes="Hằng số C" if not is_definite else None,
            )
            return res

        # 3. Sum / Difference Rule: u + v -> ∫u + ∫v
        if isinstance(expr, sp.Add):
            terms = sort_terms_pedagogical(expr.args, var)
            decomposed_str, aligned_step1 = format_integral_sum_decomposition(expr, terms, var)
            combined_raw, aligned_step2, simplified_anti, term_substeps = format_integral_term_steps(terms, var)

            # Step 1: Linearity of Integration
            builder.add_step(
                rule_name="Quy tắc tuyến tính / Tổng hiệu",
                rule_name_vi="Tính chất tuyến tính của nguyên hàm",
                title="Áp dụng tính chất tuyến tính của nguyên hàm",
                description="Nguyên hàm của một tổng hoặc hiệu bằng tổng hoặc hiệu các nguyên hàm tương ứng. Ta có:",
                before=expr,
                after=decomposed_str,
                equation_latex=aligned_step1,
                substeps=tuple(term_substeps),
                notes=f"Phân tích biểu thức thành {len(terms)} số hạng độc lập",
            )

            # Step 2: Term-by-term integration
            has_power = any(t.has(var) for t in terms)
            assumptions = ("Với n \\ne -1: \\int x^n\\,dx = \\frac{x^{n+1}}{n+1} + C",) if has_power else ()

            builder.add_step(
                rule_name="Quy tắc lũy thừa và hằng số tích phân C",
                rule_name_vi="Áp dụng quy tắc nguyên hàm của lũy thừa",
                title="Áp dụng quy tắc nguyên hàm của lũy thừa",
                description="Áp dụng quy tắc nguyên hàm cho toàn bộ các số hạng và bổ sung hằng số tích phân C:",
                before=decomposed_str,
                after=f"{expr_to_latex(simplified_anti)} + C",
                equation_latex=aligned_step2,
                substeps=tuple(term_substeps),
                assumptions=assumptions,
                notes="Hằng số C",
            )
            return simplified_anti

        # 4. Constant multiple: c * u -> c * ∫u
        if isinstance(expr, sp.Mul):
            const_factors, var_factors = [], []
            for factor in expr.args:
                if factor.has(var):
                    var_factors.append(factor)
                else:
                    const_factors.append(factor)
            if const_factors and var_factors:
                c = sp.Mul(*const_factors)
                u = sp.Mul(*var_factors)
                sub_builder = builder.create_sub_builder()
                int_u = self.integrate(u, var, sub_builder, is_definite=is_definite)
                res = c * int_u
                c_ltx = expr_to_latex(c)
                u_ltx = expr_to_latex(u)
                res_ltx = expr_to_latex(res)
                latex_after = f"{res_ltx} + C" if not is_definite else res_ltx
                eq_latex = f"\\int \\left({c_ltx} \\cdot {u_ltx}\\right) d{var.name} = {c_ltx} \\int {u_ltx}\\,d{var.name} = {latex_after}"
                builder.add_step(
                    rule_name="Quy tắc nhân với hằng số và hằng số tích phân C" if not is_definite else "Quy tắc nhân với hằng số",
                    title="Đưa hằng số ra ngoài dấu tích phân",
                    description=f"Đưa hệ số hằng số {c_ltx} ra ngoài dấu tích phân:",
                    before=expr,
                    after=latex_after,
                    substeps=sub_builder.get_steps(),
                    equation_latex=eq_latex,
                    notes="Hằng số C" if not is_definite else None,
                )
                return res

        # 5. Power rule: x^n -> x^(n+1) / (n+1) (for n != -1)
        if isinstance(expr, sp.Pow):
            base, exp = expr.args
            if base == var and not exp.has(var):
                if exp == -1:
                    res = sp.log(sp.Abs(var))
                    latex_after = f"\\ln|{var.name}| + C" if not is_definite else f"\\ln|{var.name}|"
                    eq_latex = f"\\int \\frac{{1}}{{{var.name}}}\\,d{var.name} = {latex_after}"
                    builder.add_step(
                        rule_name="Quy tắc nghịch đảo và hằng số tích phân C" if not is_definite else "Quy tắc nghịch đảo",
                        title="Áp dụng quy tắc tích phân hàm phân thức",
                        description=f"Tích phân của 1/{var.name}: \\int \\frac{{1}}{{{var.name}}}\\,d{var.name} = {latex_after}",
                        before=expr,
                        after=latex_after,
                        equation_latex=eq_latex,
                        notes="Hằng số C" if not is_definite else None,
                    )
                    return res
                else:
                    new_exp = exp + 1
                    res = (var ** new_exp) / new_exp
                    res_ltx = expr_to_latex(res)
                    latex_after = f"{res_ltx} + C" if not is_definite else res_ltx
                    eq_latex = (
                        f"\\int {var.name}^{{{exp}}}\\,d{var.name} "
                        f"= \\frac{{{var.name}^{{{exp}+1}}}}{{{exp}+1}}"
                        + (" + C" if not is_definite else "")
                        + f" = {latex_after}"
                    )
                    builder.add_step(
                        rule_name="Quy tắc lũy thừa và hằng số tích phân C" if not is_definite else "Quy tắc lũy thừa",
                        title="Áp dụng quy tắc tích phân của lũy thừa",
                        description=f"Áp dụng công thức tích phân của hàm lũy thừa với số mũ n = {exp}:",
                        before=expr,
                        after=latex_after,
                        equation_latex=eq_latex,
                        assumptions=(f"Với n \\ne -1: \\int {var.name}^n\\,d{var.name} = \\frac{{{var.name}^{{n+1}}}}{{n+1}} + C",) if not is_definite else (),
                        notes="Hằng số C" if not is_definite else None,
                    )
                    return res

        # 6. Exponential rule: e^x -> e^x
        if isinstance(expr, sp.exp) and expr.args[0] == var:
            res = sp.exp(var)
            latex_after = f"e^{{{var.name}}} + C" if not is_definite else f"e^{{{var.name}}}"
            eq_latex = f"\\int e^{{{var.name}}}\\,d{var.name} = {latex_after}"
            builder.add_step(
                rule_name="Quy tắc hàm mũ cơ số e và hằng số tích phân C" if not is_definite else "Quy tắc hàm mũ cơ số e",
                title="Áp dụng quy tắc tích phân của hàm mũ",
                description=f"Tích phân của hàm mũ: \\int e^{{{var.name}}}\\,d{var.name} = {latex_after}",
                before=expr,
                after=latex_after,
                equation_latex=eq_latex,
                notes="Hằng số C" if not is_definite else None,
            )
            return res

        # 7. Trigonometric rules
        if isinstance(expr, sp.sin) and expr.args[0] == var:
            res = -sp.cos(var)
            latex_after = f"-\\cos({var.name}) + C" if not is_definite else f"-\\cos({var.name})"
            builder.add_step(
                rule_name="Quy tắc lượng giác và hằng số tích phân C" if not is_definite else "Quy tắc lượng giác",
                title="Áp dụng quy tắc tích phân hàm lượng giác",
                description=f"Tích phân của sin({var.name}): \\int \\sin({var.name})\\,d{var.name} = {latex_after}",
                before=expr,
                after=latex_after,
                equation_latex=f"\\int \\sin({var.name})\\,d{var.name} = {latex_after}",
                notes="Hằng số C" if not is_definite else None,
            )
            return res

        if isinstance(expr, sp.cos) and expr.args[0] == var:
            res = sp.sin(var)
            latex_after = f"\\sin({var.name}) + C" if not is_definite else f"\\sin({var.name})"
            builder.add_step(
                rule_name="Quy tắc lượng giác và hằng số tích phân C" if not is_definite else "Quy tắc lượng giác",
                title="Áp dụng quy tắc tích phân hàm lượng giác",
                description=f"Tích phân của cos({var.name}): \\int \\cos({var.name})\\,d{var.name} = {latex_after}",
                before=expr,
                after=latex_after,
                equation_latex=f"\\int \\cos({var.name})\\,d{var.name} = {latex_after}",
                notes="Hằng số C" if not is_definite else None,
            )
            return res

        # Fallback to SymPy integrate
        self._fallback_occurred = True
        direct_result = sp.integrate(expr, var)
        latex_after = f"{expr_to_latex(direct_result)} + C" if not is_definite else expr_to_latex(direct_result)
        builder.add_step(
            rule_name="Công cụ tích phân giải tích",
            title="Tính toán nguyên hàm bằng giải tích",
            description=(
                "Tính toán nguyên hàm trực tiếp cho biểu thức bằng công cụ giải tích toán học "
                "do hệ thống chưa có quy tắc sư phạm phân rã chi tiết cho cấu trúc này."
            ),
            before=expr,
            after=latex_after,
            equation_latex=f"\\int \\left({expr_to_latex(expr)}\\right) d{var.name} = {latex_after}",
            notes="Tích phân nâng cao",
        )
        return direct_result

    @property
    def had_fallback(self) -> bool:
        return self._fallback_occurred

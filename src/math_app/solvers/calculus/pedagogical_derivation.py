"""Pedagogical derivation helpers for calculus solutions."""

from __future__ import annotations

from typing import Any, Sequence
import sympy as sp

from math_app.application.dtos import SolutionStep
from math_app.domain.step_content import ExpressionStepContent
from math_app.rendering.latex.formatter import expr_to_latex


def sort_terms_pedagogical(terms: Sequence[sp.Expr], var: sp.Symbol) -> list[sp.Expr]:
    """Sort polynomial and general terms in standard textbook order (degree descending)."""
    def term_sort_key(t: sp.Expr) -> tuple[int | float, int]:
        t_clean = t.doit()
        if not t_clean.has(var):
            return (-999999, 0)
        try:
            p = t_clean.as_poly(var)
            if p is not None:
                return (p.degree(), 0)
        except Exception:
            pass
        try:
            return (sp.degree(t_clean, var), 0)
        except Exception:
            return (0, 0)

    return sorted([t.doit() for t in terms], key=term_sort_key, reverse=True)


def format_derivative_sum_decomposition(
    expr: sp.Expr,
    terms: list[sp.Expr],
    var: sp.Symbol,
    is_partial: bool = False,
) -> tuple[str, str]:
    """Generate Step 1 decomposition of sum/difference derivative into separate operators.

    Returns:
        (decomposed_terms_latex, aligned_latex)
    """
    diff_op = rf"\frac{{\partial}}{{\partial {var.name}}}" if is_partial else rf"\frac{{d}}{{d{var.name}}}"
    lhs_op = rf"\frac{{\partial f}}{{\partial {var.name}}}" if is_partial else rf"f'({var.name})"

    parts: list[str] = []
    for i, t in enumerate(terms):
        t_clean = t.doit()
        coeff, rest = t_clean.as_coeff_Mul()
        is_neg = coeff < 0
        c_abs = -coeff if is_neg else coeff
        mag = c_abs * rest
        mag_ltx = expr_to_latex(mag)
        op_str = f"{diff_op}({mag_ltx})"
        if i == 0:
            parts.append(f"-{op_str}" if is_neg else op_str)
        else:
            parts.append(f"- {op_str}" if is_neg else f"+ {op_str}")

    decomposed_str = " ".join(parts)
    aligned_latex = (
        f"\\begin{{aligned}}\n"
        f"  {lhs_op}\n"
        f"  &= {diff_op}\\left({expr_to_latex(expr)}\\right) \\\\\n"
        f"  &= {decomposed_str}\n"
        f"\\end{{aligned}}"
    )
    return decomposed_str, aligned_latex


def analyze_term_diff(t: sp.Expr, var: sp.Symbol, is_partial: bool = False) -> dict[str, Any]:
    """Analyze an individual term to produce its differentiation rule, formula, and substep."""
    t_clean = t.doit()
    coeff, rest = t_clean.as_coeff_Mul()
    is_neg = coeff < 0
    c_abs = -coeff if is_neg else coeff
    mag = c_abs * rest

    diff_op = rf"\frac{{\partial}}{{\partial {var.name}}}" if is_partial else rf"\frac{{d}}{{d{var.name}}}"

    # 1. Pure constant
    if not mag.has(var):
        if is_partial:
            expl = (
                f"Đang lấy đạo hàm riêng theo biến ${var.name}$; các biến còn lại được xem là hằng số. "
                f"Đạo hàm riêng của hằng số bằng 0:"
            )
            r_name = "Constant Rule (Partial Differentiation)"
            r_name_vi = "Quy tắc hằng số trong đạo hàm riêng"
        else:
            expl = "đạo hàm của hằng số bằng 0:"
            r_name = "Constant Rule"
            r_name_vi = "Quy tắc đạo hàm của hằng số"
        return {
            "term": t_clean,
            "is_neg": is_neg,
            "c_abs": c_abs,
            "raw_step": "0",
            "result_expr": sp.Integer(0),
            "explanation": expl,
            "equation_latex": f"{diff_op}({expr_to_latex(t_clean)}) = 0",
            "rule_name": r_name,
            "rule_name_vi": r_name_vi,
        }

    # 2. Linear term: c * x
    if rest == var:
        raw_s = f"{expr_to_latex(c_abs)}\\cdot 1" if c_abs != 1 else "1"
        res = coeff
        if is_neg:
            expl = (
                f"giữ nguyên hệ số ${expr_to_latex(coeff)}$, đạo hàm của ${var.name}$ theo ${var.name}$ bằng 1."
                if coeff != -1
                else f"đạo hàm của $-{var.name}$ theo ${var.name}$ bằng -1."
            )
            eq = f"{diff_op}({expr_to_latex(t_clean)}) = {expr_to_latex(res)}"
        else:
            expl = (
                f"đạo hàm của ${var.name}$ theo ${var.name}$ bằng 1, do đó:"
                if c_abs != 1
                else f"đạo hàm của ${var.name}$ theo ${var.name}$ bằng 1."
            )
            eq = (
                f"{diff_op}({expr_to_latex(t_clean)}) = {expr_to_latex(res)}"
                if c_abs != 1
                else f"{diff_op}({var.name}) = 1"
            )
        return {
            "term": t_clean,
            "is_neg": is_neg,
            "c_abs": c_abs,
            "raw_step": raw_s,
            "result_expr": res,
            "explanation": expl,
            "equation_latex": eq,
            "rule_name": "Constant Multiple Rule" if c_abs != 1 else "Identity Variable Rule",
            "rule_name_vi": "Quy tắc nhân với hằng số" if c_abs != 1 else "Quy tắc đạo hàm của hàm đồng nhất",
        }

    # 3. Power term: c * x^n
    if isinstance(rest, sp.Pow) and rest.args[0] == var and not rest.args[1].has(var):
        n = rest.args[1]
        n_minus_1 = n - 1
        x_pow = f"{var.name}^{{{n}-1}}"
        raw_s = f"{expr_to_latex(c_abs)}\\cdot {n}{x_pow}" if c_abs != 1 else f"{n}{x_pow}"
        res = coeff * n * (var ** n_minus_1)
        res_mag = c_abs * n * (var ** n_minus_1)

        if is_neg:
            expl = f"giữ nguyên hệ số ${expr_to_latex(coeff)}$, đưa số mũ ${expr_to_latex(n)}$ xuống nhân và giảm số mũ đi 1."
            raw_signed = f"({expr_to_latex(coeff)})\\cdot {n}{x_pow}" if coeff != -1 else f"-{n}{x_pow}"
            eq = f"{diff_op}({expr_to_latex(t_clean)}) = {raw_signed} = {expr_to_latex(res)}"
        else:
            if c_abs == 1:
                expl = f"đưa số mũ ${expr_to_latex(n)}$ xuống nhân và giảm số mũ đi 1."
                eq = f"{diff_op}({expr_to_latex(mag)}) = {raw_s} = {expr_to_latex(res_mag)}"
            else:
                expl = f"giữ nguyên hệ số ${expr_to_latex(c_abs)}$, đưa số mũ ${expr_to_latex(n)}$ xuống nhân và giảm số mũ đi 1."
                eq = f"{diff_op}({expr_to_latex(mag)}) = {raw_s} = {expr_to_latex(res_mag)}"

        rule_n = "Power Rule" if c_abs == 1 else "Constant Multiple + Power Rule"
        rule_vi = "Quy tắc đạo hàm của lũy thừa" if c_abs == 1 else "Quy tắc nhân với hằng số và lũy thừa"

        return {
            "term": t_clean,
            "is_neg": is_neg,
            "c_abs": c_abs,
            "raw_step": raw_s,
            "result_expr": res,
            "explanation": expl,
            "equation_latex": eq,
            "rule_name": rule_n,
            "rule_name_vi": rule_vi,
        }

    # 4. Trigonometric functions
    trig_funcs = (sp.sin, sp.cos, sp.tan, sp.sec, sp.csc, sp.cot, sp.asin, sp.acos, sp.atan)
    if isinstance(rest, trig_funcs):
        arg = rest.args[0]
        d_mag = sp.diff(mag, var)
        d_clean = sp.diff(t_clean, var)
        res = d_clean
        d_target = f"({expr_to_latex(t_clean)})" if is_neg else expr_to_latex(t_clean)
        eq = f"{diff_op}{d_target} = {expr_to_latex(res)}"

        if arg == var:
            if c_abs == 1:
                rule_n = "Trigonometric Rule"
                rule_vi = "Quy tắc đạo hàm của hàm lượng giác"
                expl = f"áp dụng quy tắc đạo hàm lượng giác cơ bản: đạo hàm của ${expr_to_latex(rest)}$ là ${expr_to_latex(d_mag)}$."
            else:
                rule_n = "Constant Multiple + Trigonometric Rule"
                rule_vi = "Quy tắc nhân với hằng số và đạo hàm lượng giác"
                expl = f"giữ nguyên hệ số ${expr_to_latex(coeff)}$, áp dụng quy tắc đạo hàm lượng giác cho ${expr_to_latex(rest)}$."
        else:
            if c_abs == 1:
                rule_n = "Chain Rule + Trigonometric Rule"
                rule_vi = "Quy tắc đạo hàm hàm hợp và hàm lượng giác"
                expl = f"áp dụng quy tắc hàm hợp cho hàm lượng giác ${expr_to_latex(rest)}$ với biểu thức trong là ${expr_to_latex(arg)}$."
            else:
                rule_n = "Constant Multiple + Chain Rule + Trigonometric Rule"
                rule_vi = "Quy tắc nhân với hằng số, hàm hợp và hàm lượng giác"
                expl = f"giữ nguyên hệ số ${expr_to_latex(coeff)}$, áp dụng quy tắc hàm hợp cho hàm lượng giác ${expr_to_latex(rest)}$."

        return {
            "term": t_clean,
            "is_neg": is_neg,
            "c_abs": c_abs,
            "raw_step": expr_to_latex(d_mag),
            "result_expr": res,
            "explanation": expl,
            "equation_latex": eq,
            "rule_name": rule_n,
            "rule_name_vi": rule_vi,
        }

    # 5. Exponential and Logarithmic functions
    exp_log_funcs = (sp.exp, sp.log)
    is_exp_pow = isinstance(rest, sp.Pow) and not rest.args[0].has(var) and rest.args[1].has(var)
    if isinstance(rest, exp_log_funcs) or is_exp_pow:
        arg = rest.args[0] if isinstance(rest, exp_log_funcs) else rest.args[1]
        d_mag = sp.diff(mag, var)
        d_clean = sp.diff(t_clean, var)
        res = d_clean
        d_target = f"({expr_to_latex(t_clean)})" if is_neg else expr_to_latex(t_clean)
        eq = f"{diff_op}{d_target} = {expr_to_latex(res)}"

        if arg == var:
            if c_abs == 1:
                rule_n = "Exponential / Logarithmic Rule"
                rule_vi = "Quy tắc đạo hàm của hàm mũ và logarit"
                expl = f"áp dụng quy tắc đạo hàm của hàm mũ/logarit cơ bản cho ${expr_to_latex(rest)}$."
            else:
                rule_n = "Constant Multiple + Exponential/Logarithmic Rule"
                rule_vi = "Quy tắc nhân với hằng số và hàm mũ/logarit"
                expl = f"giữ nguyên hệ số ${expr_to_latex(coeff)}$, áp dụng quy tắc hàm mũ/logarit cho ${expr_to_latex(rest)}$."
        else:
            if c_abs == 1:
                rule_n = "Chain Rule + Exponential/Logarithmic Rule"
                rule_vi = "Quy tắc đạo hàm hàm hợp và hàm mũ/logarit"
                expl = f"áp dụng quy tắc hàm hợp cho hàm mũ/logarit ${expr_to_latex(rest)}$ với biểu thức trong là ${expr_to_latex(arg)}$."
            else:
                rule_n = "Constant Multiple + Chain Rule + Exponential/Logarithmic Rule"
                rule_vi = "Quy tắc nhân với hằng số, hàm hợp và hàm mũ/logarit"
                expl = f"giữ nguyên hệ số ${expr_to_latex(coeff)}$, áp dụng quy tắc hàm hợp cho ${expr_to_latex(rest)}$."

        return {
            "term": t_clean,
            "is_neg": is_neg,
            "c_abs": c_abs,
            "raw_step": expr_to_latex(d_mag),
            "result_expr": res,
            "explanation": expl,
            "equation_latex": eq,
            "rule_name": rule_n,
            "rule_name_vi": rule_vi,
        }

    # 6. Composite powers: (g(x))^n
    if isinstance(rest, sp.Pow) and rest.args[0].has(var) and not rest.args[1].has(var):
        d_mag = sp.diff(mag, var)
        d_clean = sp.diff(t_clean, var)
        res = d_clean
        d_target = f"({expr_to_latex(t_clean)})" if is_neg else expr_to_latex(t_clean)
        eq = f"{diff_op}{d_target} = {expr_to_latex(res)}"
        if c_abs == 1:
            rule_n = "Chain Rule + Power Rule"
            rule_vi = "Quy tắc đạo hàm hàm hợp và lũy thừa"
            expl = f"áp dụng quy tắc hàm hợp cho lũy thừa với hàm trong $u = {expr_to_latex(rest.args[0])}$."
        else:
            rule_n = "Constant Multiple + Chain Rule + Power Rule"
            rule_vi = "Quy tắc nhân với hằng số, hàm hợp và lũy thừa"
            expl = f"giữ nguyên hệ số ${expr_to_latex(coeff)}$, áp dụng quy tắc hàm hợp cho lũy thừa."

        return {
            "term": t_clean,
            "is_neg": is_neg,
            "c_abs": c_abs,
            "raw_step": expr_to_latex(d_mag),
            "result_expr": res,
            "explanation": expl,
            "equation_latex": eq,
            "rule_name": rule_n,
            "rule_name_vi": rule_vi,
        }

    # 7. Product of variable expressions: u * v
    if isinstance(rest, sp.Mul):
        d_mag = sp.diff(mag, var)
        d_clean = sp.diff(t_clean, var)
        res = d_clean
        d_target = f"({expr_to_latex(t_clean)})" if is_neg else expr_to_latex(t_clean)
        eq = f"{diff_op}{d_target} = {expr_to_latex(res)}"
        if c_abs == 1:
            rule_n = "Product Rule"
            rule_vi = "Quy tắc đạo hàm của tích"
            expl = f"áp dụng quy tắc đạo hàm của tích $[u \\cdot v]' = u' v + u v'$ cho ${expr_to_latex(rest)}$."
        else:
            rule_n = "Constant Multiple + Product Rule"
            rule_vi = "Quy tắc nhân với hằng số và quy tắc tích"
            expl = f"giữ nguyên hệ số ${expr_to_latex(coeff)}$, áp dụng quy tắc tích cho ${expr_to_latex(rest)}$."

        return {
            "term": t_clean,
            "is_neg": is_neg,
            "c_abs": c_abs,
            "raw_step": expr_to_latex(d_mag),
            "result_expr": res,
            "explanation": expl,
            "equation_latex": eq,
            "rule_name": rule_n,
            "rule_name_vi": rule_vi,
        }

    # Fallback / General term
    d_mag = sp.diff(mag, var)
    d_clean = sp.diff(t_clean, var)
    res = d_clean
    d_target = f"({expr_to_latex(t_clean)})" if is_neg else expr_to_latex(t_clean)
    eq = f"{diff_op}{d_target} = {expr_to_latex(res)}"

    if c_abs != 1:
        rule_n = "Constant Multiple Rule"
        rule_vi = "Quy tắc nhân với hằng số"
        expl = f"giữ nguyên hệ số ${expr_to_latex(coeff)}$, tính đạo hàm của ${expr_to_latex(rest)}$ theo ${var.name}$."
    else:
        rule_n = "Differentiation Rule"
        rule_vi = "Quy tắc đạo hàm"
        expl = f"tính đạo hàm của số hạng ${expr_to_latex(t_clean)}$ theo ${var.name}$."

    return {
        "term": t_clean,
        "is_neg": is_neg,
        "c_abs": c_abs,
        "raw_step": expr_to_latex(d_mag),
        "result_expr": res,
        "explanation": expl,
        "equation_latex": eq,
        "rule_name": rule_n,
        "rule_name_vi": rule_vi,
    }


def format_derivative_term_steps(
    terms: list[sp.Expr],
    var: sp.Symbol,
    start_substep_idx: int = 1,
    is_partial: bool = False,
) -> tuple[str, str, sp.Expr, list[SolutionStep]]:
    """Generate Step 2 term-by-term transformation line, aligned equation, and Layer B substeps."""
    lhs_op = rf"\frac{{\partial f}}{{\partial {var.name}}}" if is_partial else rf"f'({var.name})"

    raw_parts: list[str] = []
    substeps: list[SolutionStep] = []
    term_results: list[sp.Expr] = []

    for i, t in enumerate(terms):
        t_clean = t.doit()
        info = analyze_term_diff(t_clean, var, is_partial=is_partial)
        raw_s = info["raw_step"]
        is_neg = info["is_neg"]
        res = info["result_expr"]
        term_results.append(res)

        if i == 0:
            raw_parts.append(f"-{raw_s}" if is_neg else raw_s)
        else:
            raw_parts.append(f"- {raw_s}" if is_neg else f"+ {raw_s}")

        # Layer B substep
        content = ExpressionStepContent(
            expression_before=str(t_clean),
            expression_after=str(res),
            latex_before=expr_to_latex(t_clean),
            latex_after=expr_to_latex(res),
        )
        step = SolutionStep(
            step_number=start_substep_idx + i,
            rule_name=info["rule_name"],
            rule_name_vi=info["rule_name_vi"],
            title=f"Số hạng ${expr_to_latex(t_clean)}$",
            description=info["explanation"],
            content=content,
            equation_latex=info["equation_latex"],
        )
        substeps.append(step)

    combined_raw = " ".join(raw_parts)
    combined_result = sp.Add(*term_results)
    simplified_result = sp.simplify(combined_result)

    aligned_latex = (
        f"\\begin{{aligned}}\n"
        f"  {lhs_op}\n"
        f"  &= {combined_raw} \\\\\n"
        f"  &= {expr_to_latex(simplified_result)}\n"
        f"\\end{{aligned}}"
    )
    return combined_raw, aligned_latex, simplified_result, substeps
    """Generate Step 2 term-by-term transformation line, aligned equation, and Layer B substeps."""
    raw_parts: list[str] = []
    substeps: list[SolutionStep] = []
    term_results: list[sp.Expr] = []

    for i, t in enumerate(terms):
        t_clean = t.doit()
        info = analyze_term_diff(t_clean, var)
        raw_s = info["raw_step"]
        is_neg = info["is_neg"]
        res = info["result_expr"]
        term_results.append(res)

        if i == 0:
            raw_parts.append(f"-{raw_s}" if is_neg else raw_s)
        else:
            raw_parts.append(f"- {raw_s}" if is_neg else f"+ {raw_s}")

        # Layer B substep
        content = ExpressionStepContent(
            expression_before=str(t_clean),
            expression_after=str(res),
            latex_before=expr_to_latex(t_clean),
            latex_after=expr_to_latex(res),
        )
        step = SolutionStep(
            step_number=start_substep_idx + i,
            rule_name=info["rule_name"],
            rule_name_vi=info["rule_name_vi"],
            title=f"Số hạng {expr_to_latex(t_clean)}",
            description=info["explanation"],
            content=content,
            equation_latex=info["equation_latex"],
        )
        substeps.append(step)

    combined_raw = " ".join(raw_parts)
    combined_result = sp.Add(*term_results)
    simplified_result = sp.simplify(combined_result)

    aligned_latex = (
        f"\\begin{{aligned}}\n"
        f"  f'({var.name})\n"
        f"  &= {combined_raw} \\\\\n"
        f"  &= {expr_to_latex(simplified_result)}\n"
        f"\\end{{aligned}}"
    )
    return combined_raw, aligned_latex, simplified_result, substeps


def format_integral_sum_decomposition(
    expr: sp.Expr,
    terms: list[sp.Expr],
    var: sp.Symbol,
) -> tuple[str, str]:
    """Generate Step 1 decomposition of sum/difference indefinite integral.

    Returns:
        (decomposed_terms_latex, aligned_latex)
    """
    parts: list[str] = []
    for i, t in enumerate(terms):
        t_clean = t.doit()
        coeff, rest = t_clean.as_coeff_Mul()
        is_neg = coeff < 0
        c_abs = -coeff if is_neg else coeff
        mag = c_abs * rest
        mag_ltx = expr_to_latex(mag)
        int_str = f"\\int {mag_ltx}\\,d{var.name}"
        if i == 0:
            parts.append(f"-{int_str}" if is_neg else int_str)
        else:
            parts.append(f"- {int_str}" if is_neg else f"+ {int_str}")

    decomposed_str = " ".join(parts)
    aligned_latex = (
        f"\\begin{{aligned}}\n"
        f"  \\int f({var.name})\\,d{var.name}\n"
        f"  &= \\int \\left( {expr_to_latex(expr)} \\right) d{var.name} \\\\\n"
        f"  &= {decomposed_str}\n"
        f"\\end{{aligned}}"
    )
    return decomposed_str, aligned_latex


def analyze_term_int(t: sp.Expr, var: sp.Symbol) -> dict[str, Any]:
    """Analyze an individual term to produce its integration rule, formula, and substep."""
    t_clean = t.doit()
    coeff, rest = t_clean.as_coeff_Mul()
    is_neg = coeff < 0
    c_abs = -coeff if is_neg else coeff
    mag = c_abs * rest

    # 1. Pure constant
    if not mag.has(var):
        simp = coeff * var
        expl = (
            "nguyên hàm của hằng số âm:"
            if is_neg
            else "nguyên hàm của hằng số:"
        )
        eq_lhs = f"\\int ({expr_to_latex(t_clean)})\\,d{var.name}" if is_neg else f"\\int {expr_to_latex(t_clean)}\\,d{var.name}"
        return {
            "term": t_clean,
            "is_neg": is_neg,
            "c_abs": c_abs,
            "raw_step": f"{expr_to_latex(mag)}{var.name}",
            "simplified_expr": simp,
            "explanation": expl,
            "equation_latex": f"{eq_lhs} = {expr_to_latex(simp)}",
            "rule_name": "Quy tắc hằng số",
            "rule_name_vi": "Quy tắc tích phân của hằng số",
        }

    # 2. Linear term: c * x
    if rest == var:
        raw_s = f"{expr_to_latex(c_abs)}\\cdot\\frac{{{var.name}^2}}{{2}}" if c_abs != 1 else f"\\frac{{{var.name}^2}}{{2}}"
        simp = coeff * (var ** 2) / 2
        expl = (
            f"đưa hệ số ${expr_to_latex(t_clean)}$ ra ngoài, áp dụng quy tắc nguyên hàm của lũy thừa:"
            if is_neg
            else (
                f"đưa hệ số ${expr_to_latex(c_abs)}$ ra ngoài, áp dụng quy tắc nguyên hàm của lũy thừa:"
                if c_abs != 1
                else "áp dụng quy tắc nguyên hàm của lũy thừa với số mũ 1:"
            )
        )
        eq_lhs = f"\\int ({expr_to_latex(t_clean)})\\,d{var.name}" if is_neg else f"\\int {expr_to_latex(t_clean)}\\,d{var.name}"
        eq = (
            f"{eq_lhs} = -{raw_s} = {expr_to_latex(simp)}"
            if is_neg
            else f"{eq_lhs} = {raw_s} = {expr_to_latex(simp)}"
        )
        return {
            "term": t_clean,
            "is_neg": is_neg,
            "c_abs": c_abs,
            "raw_step": raw_s,
            "simplified_expr": simp,
            "explanation": expl,
            "equation_latex": eq,
            "rule_name": "Quy tắc lũy thừa",
            "rule_name_vi": "Quy tắc tích phân của lũy thừa",
        }

    # 3. Power term: c * x^n
    if isinstance(rest, sp.Pow) and rest.args[0] == var and not rest.args[1].has(var):
        n = rest.args[1]
        n_plus_1 = n + 1
        x_pow = f"\\frac{{{var.name}^{{{n_plus_1}}}}}{{{n_plus_1}}}"
        raw_s = f"{expr_to_latex(c_abs)}\\cdot{x_pow}" if c_abs != 1 else x_pow
        simp = coeff * (var ** n_plus_1) / n_plus_1
        expl = (
            f"đưa hệ số ${expr_to_latex(t_clean)}$ ra ngoài, áp dụng quy tắc nguyên hàm của lũy thừa:"
            if is_neg
            else (
                f"đưa hệ số ${expr_to_latex(c_abs)}$ ra ngoài, áp dụng quy tắc nguyên hàm của lũy thừa:"
                if c_abs != 1
                else f"áp dụng quy tắc nguyên hàm của lũy thừa với số mũ {n}:"
            )
        )
        eq_lhs = f"\\int ({expr_to_latex(t_clean)})\\,d{var.name}" if is_neg else f"\\int {expr_to_latex(t_clean)}\\,d{var.name}"
        eq = (
            f"{eq_lhs} = -{raw_s} = {expr_to_latex(simp)}"
            if is_neg
            else f"{eq_lhs} = {raw_s} = {expr_to_latex(simp)}"
        )
        return {
            "term": t_clean,
            "is_neg": is_neg,
            "c_abs": c_abs,
            "raw_step": raw_s,
            "simplified_expr": simp,
            "explanation": expl,
            "equation_latex": eq,
            "rule_name": "Quy tắc lũy thừa",
            "rule_name_vi": "Quy tắc tích phân của lũy thừa",
        }

    # Fallback
    res = sp.integrate(mag, var)
    simp = coeff * res
    eq_lhs = f"\\int ({expr_to_latex(t_clean)})\\,d{var.name}" if is_neg else f"\\int {expr_to_latex(t_clean)}\\,d{var.name}"
    return {
        "term": t_clean,
        "is_neg": is_neg,
        "c_abs": c_abs,
        "raw_step": expr_to_latex(res),
        "simplified_expr": simp,
        "explanation": f"tính nguyên hàm của số hạng ${expr_to_latex(t_clean)}$.",
        "equation_latex": f"{eq_lhs} = {expr_to_latex(simp)}",
        "rule_name": "Quy tắc lũy thừa",
        "rule_name_vi": "Quy tắc tích phân",
    }


def format_integral_term_steps(
    terms: list[sp.Expr],
    var: sp.Symbol,
    start_substep_idx: int = 1,
) -> tuple[str, str, sp.Expr, list[SolutionStep]]:
    """Generate Step 2 term-by-term integration line, aligned equation, and Layer B substeps."""
    raw_parts: list[str] = []
    substeps: list[SolutionStep] = []
    term_results: list[sp.Expr] = []

    for i, t in enumerate(terms):
        t_clean = t.doit()
        info = analyze_term_int(t_clean, var)
        raw_s = info["raw_step"]
        is_neg = info["is_neg"]
        simp = info["simplified_expr"]
        term_results.append(simp)

        if i == 0:
            raw_parts.append(f"-{raw_s}" if is_neg else raw_s)
        else:
            raw_parts.append(f"- {raw_s}" if is_neg else f"+ {raw_s}")

        # Layer B substep
        content = ExpressionStepContent(
            expression_before=str(t_clean),
            expression_after=str(simp),
            latex_before=expr_to_latex(t_clean),
            latex_after=expr_to_latex(simp),
        )
        step = SolutionStep(
            step_number=start_substep_idx + i,
            rule_name=info["rule_name"],
            rule_name_vi=info["rule_name_vi"],
            title=f"Số hạng ${expr_to_latex(t_clean)}$",
            description=info["explanation"],
            content=content,
            equation_latex=info["equation_latex"],
        )
        substeps.append(step)

    combined_raw = " ".join(raw_parts) + " + C"
    # Keep textbook expanded polynomial form for sum
    combined_anti = sp.Add(*term_results)

    aligned_latex = (
        f"\\begin{{aligned}}\n"
        f"  \\int f({var.name})\\,d{var.name}\n"
        f"  &= {combined_raw} \\\\\n"
        f"  &= {expr_to_latex(combined_anti)} + C\n"
        f"\\end{{aligned}}"
    )
    return combined_raw, aligned_latex, combined_anti, substeps

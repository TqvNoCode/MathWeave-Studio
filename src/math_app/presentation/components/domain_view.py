"""Shared mathematical domain restrictions and condition renderer."""

from __future__ import annotations

import re
import sympy as sp
from nicegui import ui

from math_app.input.parser import parse_safe_expression
from math_app.presentation.components.math_view import ui_math
from math_app.rendering.latex.formatter import expr_to_latex


def format_domain_condition(res: str, var_name: str = "x") -> tuple[str, str, str]:
    """Parse raw condition string into (dedup_key, vietnamese_explanation, latex_formula)."""
    # 0. Disconnected domain union conditions (generic extraction without hardcoded intervals)
    if r"\mathcal{D}" in res or r"\cup" in res or "∪" in res or "khoảng liên thông" in res.lower():
        m_d = re.search(r"(\\mathcal\{D\}(?:_\{[^}]+\})?\s*=\s*.+?)(?:\.|$)", res)
        if m_d:
            formula = m_d.group(1).strip()
            if "với" in formula:
                formula = re.sub(r",\s*với\s*", r" \\quad (", formula)
                if not formula.endswith(")"):
                    formula += ")"
                formula = formula.replace(" và ", r", \; ")
        else:
            formula = res.strip()
        return (
            f"domain_union_{var_name}",
            "Miền xác định (hợp các khoảng liên thông):",
            formula,
        )

    # 1. Trigonometric conditions
    if "tan" in res.lower() or "sec" in res.lower():
        return (
            "cos",
            "Điều kiện hàm lượng giác tan / sec:",
            rf"\cos({var_name}) \ne 0 \iff {var_name} \ne \frac{{\pi}}{{2}} + k\pi \quad (k \in \mathbb{{Z}})",
        )
    if "cot" in res.lower() or "csc" in res.lower():
        return (
            "sin",
            "Điều kiện hàm lượng giác cot / csc:",
            rf"\sin({var_name}) \ne 0 \iff {var_name} \ne k\pi \quad (k \in \mathbb{{Z}})",
        )
    if "log" in res.lower() or "ln" in res.lower():
        m_arg = re.search(r":\s*([^.]+?)\s*(?:>|>=|\\ge)\s*0", res)
        arg_str = m_arg.group(1).strip() if m_arg else var_name
        try:
            arg_ltx = expr_to_latex(arg_str)
        except Exception:
            arg_ltx = arg_str
        return (
            f"ln_{arg_str}",
            "Điều kiện hàm số logarit tự nhiên:",
            rf"{arg_ltx} > 0",
        )
    if "căn bậc chẵn" in res.lower() or "sqrt" in res.lower():
        m_arg = re.search(r":\s*([^.]+?)\s*(?:>=|\\ge)\s*0", res)
        arg_str = m_arg.group(1).strip() if m_arg else var_name
        try:
            arg_ltx = expr_to_latex(arg_str)
        except Exception:
            arg_ltx = arg_str
        return (
            f"sqrt_{arg_str}",
            "Điều kiện biểu thức dưới căn bậc chẵn:",
            rf"{arg_ltx} \ge 0",
        )

    # 2. Integrating factor conditions (e.g. Điều kiện thừa số tích phân: μ = x khác 0.)
    if "thừa số tích phân" in res.lower():
        m_mu = re.search(r"[μ\u03bc]\s*=\s*([^:!=≠\n]+?)\s*(?:khác|!=|\\ne|≠)\s*0", res)
        if m_mu:
            raw_expr = m_mu.group(1).strip()
            expr_ltx = expr_to_latex(raw_expr)
            if expr_ltx == var_name:
                formula = rf"\mu = {expr_ltx},\quad {var_name} \ne 0"
            else:
                formula = rf"\mu = {expr_ltx} \ne 0"
            return (
                f"mu_{raw_expr}",
                "Điều kiện thừa số tích phân:",
                formula,
            )
        m_denom = re.search(r"(?:thừa số tích phân|xác định)[^:]*:\s*([^:!=≠\n]+?)\s*(?:khác|!=|\\ne|≠)\s*0", res)
        if m_denom:
            raw_expr = m_denom.group(1).strip()
            expr_ltx = expr_to_latex(raw_expr)
            return (
                f"mu_denom_{raw_expr}",
                "Điều kiện xác định của thừa số tích phân μ:",
                rf"{expr_ltx} \ne 0",
            )

    # 3. Denominator / inequality conditions (e.g. Mẫu số x + 1 != 0, x + 1 \ne 0, x khác 0)
    m = re.search(r"([^:!=≠\n]+?)\s*(?:!=|\\ne|≠|khác)\s*0", res)
    if m:
        raw_expr = m.group(1).strip()
        raw_expr = re.sub(r"^.*?(?:mẫu số|điều kiện)\s*", "", raw_expr, flags=re.IGNORECASE).strip()
        if raw_expr:
            try:
                var = sp.Symbol(var_name)
                expr = parse_safe_expression(raw_expr, target_variable=var_name, evaluate=True)
                base_denom = sp.sqf_part(expr)
                denom_ltx = expr_to_latex(base_denom)
                roots = sp.solve(sp.Eq(base_denom, 0), var)
                real_roots = [r for r in roots if r.is_real is True or (r.is_number and r.as_real_imag()[1] == 0)]
                if not real_roots:
                    formula = f"{denom_ltx} \\ne 0 \\implies \\mathcal{{D}} = \\mathbb{{R}}"
                    desc = "Điều kiện xác định của mẫu số:"
                else:
                    root_strs = [expr_to_latex(r) for r in sorted(real_roots, key=lambda val: float(val.evalf()))]
                    neq_str = ", ".join(f"{var_name} \\ne {rs}" for rs in root_strs)
                    roots_set = ", ".join(root_strs)
                    formula = (
                        f"{denom_ltx} \\ne 0 \\iff {neq_str} "
                        f"\\implies \\mathcal{{D}} = \\mathbb{{R}} \\setminus \\{{{roots_set}\\}}"
                    )
                    desc = "Điều kiện xác định của mẫu số:"
                return str(base_denom), desc, formula
            except Exception:
                ltx = expr_to_latex(raw_expr)
                return raw_expr, "Điều kiện xác định của mẫu số:", f"{ltx} \\ne 0"

    if any(ord(c) > 127 for c in res):
        return res, "Điều kiện xác định:", rf"\text{{{res.strip()}}}"

    return res, "Điều kiện xác định:", expr_to_latex(res)


def render_domain_restrictions(
    restrictions: tuple[str, ...],
    var_name: str = "x",
    original_domain_latex: str = "",
    normalized_domain_latex: str = "",
) -> None:
    """Render domain restrictions with pure Vietnamese prose and clean LaTeX formulas.

    Tautological conditions with no excluded real values are filtered out to keep the UI focused.
    """
    if not restrictions and not (
        original_domain_latex and normalized_domain_latex and original_domain_latex != normalized_domain_latex
    ):
        return

    # Parse and deduplicate
    seen_keys: set[str] = set()
    parsed_items: list[tuple[str, str]] = []

    # If original and normalized domains differ, render their explicit relationship
    if original_domain_latex and normalized_domain_latex and original_domain_latex != normalized_domain_latex:
        orig_formula = (
            original_domain_latex
            if original_domain_latex.startswith(r"\mathcal{D}")
            else rf"\mathcal{{D}}_{{\text{{orig}}}} = {original_domain_latex}"
        )
        norm_formula = (
            normalized_domain_latex
            if normalized_domain_latex.startswith(r"\mathcal{D}")
            else rf"\mathcal{{D}}_{{\text{{norm}}}} = {normalized_domain_latex}"
        )
        parsed_items.append(
            (
                "Miền xác định của phương trình vi phân gốc:",
                orig_formula,
            )
        )
        parsed_items.append(
            (
                "Miền xác định dạng chuẩn tắc sau khi chia cho hệ số dẫn đầu:",
                norm_formula,
            )
        )
        seen_keys.add("d_orig_norm_transition")

    for r in restrictions:
        key, desc, formula = format_domain_condition(r, var_name)
        # Omit tautological conditions that introduce no real exclusions (e.g. D = R)
        if r"\mathcal{D} = \mathbb{R}" in formula and r"\setminus" not in formula:
            continue
        if key not in seen_keys:
            seen_keys.add(key)
            parsed_items.append((desc, formula))

    if not parsed_items:
        return

    with ui.column().classes("w-full p-4 bg-amber-50/80 border border-amber-200 rounded-xl gap-2.5"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("rule", size="1.2rem").classes("text-amber-800")
            ui.label("Điều kiện xác định của bài toán:").classes(
                "text-xs font-bold text-amber-950 uppercase tracking-wider"
            )

        for desc, formula in parsed_items:
            with ui.column().classes("w-full pl-3 py-1 gap-1 border-l-2 border-amber-400"):
                ui.label(desc).classes("text-xs font-medium text-amber-900")
                ui_math(formula, block=False, classes="text-base font-semibold text-amber-950 py-0.5")

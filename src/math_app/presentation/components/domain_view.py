"""Shared mathematical domain restrictions and condition renderer."""

from __future__ import annotations

import re
import sympy as sp
from nicegui import ui

from math_app.presentation.components.math_view import ui_math
from math_app.rendering.latex.formatter import expr_to_latex


def format_domain_condition(res: str, var_name: str = "x") -> tuple[str, str, str]:
    """Parse raw condition string into (dedup_key, vietnamese_explanation, latex_formula)."""
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
        return (
            "ln",
            "Điều kiện hàm số logarit tự nhiên:",
            rf"u({var_name}) > 0",
        )

    # 2. Denominator / inequality conditions (e.g. Mẫu số x + 1 != 0, x + 1 \ne 0)
    m = re.search(r"([^:!=≠\n]+?)\s*(?:!=|\\ne|≠)\s*0", res)
    if m:
        raw_expr = m.group(1).strip()
        raw_expr = re.sub(r"^.*?(?:mẫu số|điều kiện)\s*", "", raw_expr, flags=re.IGNORECASE).strip()
        if raw_expr:
            try:
                var = sp.Symbol(var_name)
                expr = sp.sympify(raw_expr)
                base_denom = sp.sqf_part(expr)
                denom_ltx = expr_to_latex(base_denom)
                roots = sp.solve(sp.Eq(base_denom, 0), var)
                real_roots = [
                    r for r in roots
                    if r.is_real is True or (r.is_number and r.as_real_imag()[1] == 0)
                ]
                if not real_roots:
                    formula = f"{denom_ltx} \\ne 0 \\implies \\mathcal{{D}} = \\mathbb{{R}}"
                    desc = "Điều kiện xác định của mẫu số:"
                else:
                    root_strs = [
                        expr_to_latex(r)
                        for r in sorted(real_roots, key=lambda val: float(val.evalf()))
                    ]
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

    return res, "Điều kiện xác định:", expr_to_latex(res)


def render_domain_restrictions(restrictions: tuple[str, ...], var_name: str = "x") -> None:
    """Render domain restrictions with pure Vietnamese prose and clean LaTeX formulas.

    Tautological conditions with no excluded real values are filtered out to keep the UI focused.
    """
    if not restrictions:
        return

    # Parse and deduplicate
    seen_keys: set[str] = set()
    parsed_items: list[tuple[str, str]] = []
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

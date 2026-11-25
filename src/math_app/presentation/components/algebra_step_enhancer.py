"""Pedagogical algebra step enhancer for equation factorization explanations."""

from __future__ import annotations

import sympy as sp

from math_app.application.dtos import ExpressionStepContent, SolutionStep
from math_app.input.parser import parse_mathematical_input
from math_app.rendering.latex.formatter import expr_to_latex


def enhance_equation_factorization_steps(
    steps: tuple[SolutionStep, ...],
    raw_input: str,
    target_var: str = "x",
) -> tuple[SolutionStep, ...]:
    """Enhance factorization steps for factorable quadratic equations with pedagogical derivations.

    For quadratic equations with rational/integer factorizations (e.g. x^2 - 5x + 6 = 0),
    expands the jump into:
    1. Step — Find suitable numbers m, n (ac-method).
    2. Step — Split middle term and factor by grouping.
    3. Step — Apply the zero-product property.

    For non-factorable equations or higher-degree polynomials, preserves original steps.
    """
    if not steps:
        return steps

    try:
        # Check if the problem is a quadratic equation
        clean_input = raw_input.strip()
        lhs_str = clean_input.split("=")[0].strip() if "=" in clean_input else clean_input
        rhs_str = clean_input.split("=")[1].strip() if "=" in clean_input else "0"

        var = sp.Symbol(target_var)
        lhs_expr, _ = parse_mathematical_input(lhs_str, target_var)
        rhs_expr, _ = parse_mathematical_input(rhs_str, target_var)
        eq_poly = sp.Poly(sp.expand(lhs_expr - rhs_expr), var)

        if eq_poly.degree() != 2:
            return steps

        coeffs = eq_poly.all_coeffs()
        a, b, c = coeffs[0], coeffs[1], coeffs[2]

        if not (a.is_rational and b.is_rational and c.is_rational):
            return steps

        # Check discriminant
        delta = b**2 - 4 * a * c
        if delta < 0:
            return steps

        sqrt_delta = sp.sqrt(delta)
        if not sqrt_delta.is_rational:
            return steps

        # Roots exist and are rational
        r1 = (-b + sqrt_delta) / (2 * a)
        r2 = (-b - sqrt_delta) / (2 * a)

        # ac-method: find two numbers m, n such that m + n = b and m * n = a * c
        m_val = sp.nsimplify(-a * r1)
        n_val = sp.nsimplify(-a * r2)

        # If m_val and n_val are integers (common textbook case)
        if not (m_val.is_integer and n_val.is_integer and a.is_integer):
            return steps

        m_int = int(m_val)
        n_int = int(n_val)
        a_int = int(a)
        b_int = int(b)
        c_int = int(c)

        # Order m, n cleanly (e.g. -3, -2)
        if m_int > n_int:
            m_int, n_int = n_int, m_int

        # Generate the educational substeps
        enhanced: list[SolutionStep] = []
        step_idx = 1

        poly_expr = eq_poly.as_expr()
        poly_latex = expr_to_latex(poly_expr)

        # Keep initial canonicalization step if present
        if steps and "f(x) = 0" in (steps[0].description or ""):
            enhanced.append(
                SolutionStep(
                    step_number=step_idx,
                    title="Chuyển về dạng chuẩn",
                    rule_name="Dạng chuẩn f(x) = 0",
                    rule_name_vi="Dạng chuẩn f(x) = 0",
                    description=f"Chuyển tất cả các số hạng sang vế trái để đưa phương trình về dạng chuẩn ${poly_latex} = 0$.",
                    content=ExpressionStepContent(
                        expression_before=raw_input,
                        expression_after=f"{poly_expr} = 0",
                        latex_before=raw_input,
                        latex_after=f"{poly_latex} = 0",
                    ),
                    equation_latex=f"{poly_latex} = 0",
                )
            )
            step_idx += 1

        # Step 1: Find two numbers m, n
        ac_prod = a_int * c_int
        if a_int == 1:
            find_desc = (
                f"Tìm hai số $m, n$ thỏa mãn hệ thức:\n"
                f"$$\\begin{{cases}} m + n = b = {b_int} \\\\ m \\cdot n = c = {c_int} \\end{{cases}}$$\n"
                f"Ta tìm được cặp số thích hợp: $m = {m_int},\\quad n = {n_int}$."
            )
        else:
            find_desc = (
                f"Áp dụng phương pháp tách hạng tử ($ac$-method): Tìm hai số $m, n$ thỏa mãn:\n"
                f"$$\\begin{{cases}} m + n = b = {b_int} \\\\ m \\cdot n = a \\cdot c = {a_int} \\cdot ({c_int}) = {ac_prod} \\end{{cases}}$$\n"
                f"Ta tìm được cặp số thích hợp: $m = {m_int},\\quad n = {n_int}$."
            )

        step1_latex = rf"\begin{{cases}} m + n = {b_int} \\ m \cdot n = {ac_prod} \end{{cases}} \implies m = {m_int},\quad n = {n_int}"
        enhanced.append(
            SolutionStep(
                step_number=step_idx,
                title="Xác định cặp số phân tích",
                rule_name="Tách hạng tử (ac-method)",
                rule_name_vi="Phương pháp tách hạng tử",
                description=find_desc,
                content=ExpressionStepContent(
                    expression_before=f"{poly_expr} = 0",
                    expression_after=f"m = {m_int}, n = {n_int}",
                    latex_before=f"{poly_latex} = 0",
                    latex_after=step1_latex,
                ),
                equation_latex=step1_latex,
            )
        )
        step_idx += 1

        # Step 2: Split and factor by grouping
        m_term = f"{'+ ' if m_int >= 0 else '- '}{abs(m_int)}{target_var}"
        n_term = f"{'+ ' if n_int >= 0 else '- '}{abs(n_int)}{target_var}"
        c_term = f"{'+ ' if c_int >= 0 else '- '}{abs(c_int)}"
        first_term = f"{a_int if a_int != 1 else ''}{target_var}^2"

        factored_form = sp.factor(poly_expr)
        factored_latex = expr_to_latex(factored_form)

        group_desc = (
            f"Tách số hạng bậc nhất thành ${m_term} {n_term}$ và nhóm các số hạng để đặt nhân tử chung:\n"
            f"$${first_term} {m_term} {n_term} {c_term} = 0$$\n"
            f"Phân tích thành tích:\n"
            f"$${factored_latex} = 0$$"
        )

        step2_latex = f"{first_term} {m_term} {n_term} {c_term} = 0 \\implies {factored_latex} = 0"
        enhanced.append(
            SolutionStep(
                step_number=step_idx,
                title="Phân tích thành nhân tử bằng cách nhóm",
                rule_name="Nhóm nhân tử chung",
                rule_name_vi="Nhóm nhân tử chung",
                description=group_desc,
                content=ExpressionStepContent(
                    expression_before=f"{poly_expr} = 0",
                    expression_after=f"{factored_form} = 0",
                    latex_before=f"{poly_latex} = 0",
                    latex_after=f"{factored_latex} = 0",
                ),
                equation_latex=step2_latex,
            )
        )
        step_idx += 1

        # Step 3: Zero-product property
        roots_latex = f"{target_var} = {expr_to_latex(r1)},\\quad {target_var} = {expr_to_latex(r2)}"
        if r1 == r2:
            zero_prod_desc = (
                f"Áp dụng quy tắc nhân tử bằng 0 (nghiệm kép):\n"
                f"$${factored_latex} = 0 \\implies {target_var} = {expr_to_latex(r1)}$$"
            )
            step3_latex = f"{factored_latex} = 0 \\implies {target_var} = {expr_to_latex(r1)}"
        else:
            zero_prod_desc = (
                f"Áp dụng quy tắc tích bằng 0 (Zero-product property):\n"
                f"Tích của hai nhân tử bằng 0 khi và chỉ khi ít nhất một nhân tử bằng 0:\n"
                f"$${factored_latex} = 0 \\iff {target_var} = {expr_to_latex(r1)} \\quad\\text{{hoặc}}\\quad {target_var} = {expr_to_latex(r2)}$$"
            )
            step3_latex = f"{factored_latex} = 0 \\implies {target_var} = {expr_to_latex(r1)} \\quad\\text{{hoặc}}\\quad {target_var} = {expr_to_latex(r2)}"

        enhanced.append(
            SolutionStep(
                step_number=step_idx,
                title="Quy tắc tích bằng 0 & Kết luận nghiệm",
                rule_name="Quy tắc tích bằng 0",
                rule_name_vi="Quy tắc tích bằng 0",
                description=zero_prod_desc,
                content=ExpressionStepContent(
                    expression_before=f"{factored_form} = 0",
                    expression_after=f"{target_var} = {r1}, {target_var} = {r2}",
                    latex_before=f"{factored_latex} = 0",
                    latex_after=roots_latex,
                ),
                equation_latex=step3_latex,
            )
        )

        return tuple(enhanced)

    except Exception:
        # On any exception, safely preserve original steps
        return steps

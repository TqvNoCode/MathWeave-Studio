"""Golden acceptance tests for unified, continuous pedagogical mathematical derivations."""

import sympy as sp
import pytest

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.presentation.components.problem_statement import format_final_answer_latex
from math_app.solvers.calculus.differentiation.rule_engine import DifferentiationRuleEngine
from math_app.solvers.calculus.differentiation.rules.power_rule import PowerRule
from math_app.solvers.calculus.differentiation.solver import DerivativeSolver
from math_app.solvers.calculus.differentiation.step_builder import DifferentiationStepBuilder
from math_app.solvers.calculus.integration.solver import IntegralSolver


def test_mandatory_derivative_regression_unified_derivation():
    """Mandatory Regression 1: f(x) = 2x^3 + 6x - 8 -> f'(x) = 6x^2 + 6.

    Verifies:
    - Final first derivative is 6x^2 + 6.
    - Main derivation shows full original expression.
    - Sum/difference rule applied at whole-expression level.
    - Three terms handled correctly with constant contributing zero.
    - Detailed substeps correspond to main derivation.
    - Continuous derivation readable without expanding optional detail.
    - Displayed formulas use proper LaTeX without programming syntax.
    """
    solver = DerivativeSolver()
    request = ProblemRequest("2*x^3 + 6*x - 8", ProblemType.DERIVATIVE, target_variable="x")
    response = solver.solve(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED

    # Check symbolic equivalence
    x = sp.Symbol("x")
    expected = 6 * (x ** 2) + 6
    actual = sp.sympify(response.final_result)
    assert sp.simplify(actual - expected) == 0

    # Main derivation has exactly 2 coherent steps (whole expression decomposition, then term transformations)
    assert len(response.steps) == 2

    # Step 1: Whole-expression Sum and Difference Linearity
    step1 = response.steps[0]
    assert step1.display_rule_name == "Quy tắc đạo hàm của tổng và hiệu"
    assert "tổng và hiệu" in step1.display_title.lower()
    assert step1.equation_latex != ""
    assert "\\begin{aligned}" in step1.equation_latex
    assert "f'(x)" in step1.equation_latex
    # Full original expression displayed
    assert "2 x^{3} + 6 x - 8" in step1.equation_latex or "2x^3 + 6x - 8" in step1.equation_latex
    # Decomposed into derivative operators
    assert "\\frac{d}{dx}(2 x^{3})" in step1.equation_latex or "\\frac{d}{dx}(2x^3)" in step1.equation_latex
    assert "\\frac{d}{dx}(6 x)" in step1.equation_latex or "\\frac{d}{dx}(6x)" in step1.equation_latex
    assert "\\frac{d}{dx}(8)" in step1.equation_latex
    # No programming syntax
    assert "**" not in step1.equation_latex

    # Step 2: Term-by-term Differentiation
    step2 = response.steps[1]
    assert "từng số hạng" in step2.display_title.lower()
    assert step2.equation_latex != ""
    assert "\\begin{aligned}" in step2.equation_latex
    # Shows simultaneous transformation
    assert "2\\cdot 3x^{3-1}" in step2.equation_latex
    assert "6\\cdot 1" in step2.equation_latex
    assert "- 0" in step2.equation_latex
    assert "6 x^{2} + 6" in step2.equation_latex or "6x^2 + 6" in step2.equation_latex

    # Optional Layer B Substeps under Step 2
    assert len(step2.substeps) == 3

    # Substep for 2x^3
    sub1 = step2.substeps[0]
    assert "2 x^{3}" in sub1.title or "2x^3" in sub1.title
    assert "giảm số mũ" in sub1.description or "lũy thừa" in sub1.description
    assert "\\frac{d}{dx}(2 x^{3}) = 2\\cdot 3x^{3-1} = 6 x^{2}" in sub1.equation_latex

    # Substep for 6x
    sub2 = step2.substeps[1]
    assert "6 x" in sub2.title or "6x" in sub2.title
    assert "bằng 1" in sub2.description
    assert "\\frac{d}{dx}(6 x) = 6" in sub2.equation_latex or "\\frac{d}{dx}(6x) = 6" in sub2.equation_latex

    # Substep for -8 (constant contributes zero)
    sub3 = step2.substeps[2]
    assert "8" in sub3.title
    assert "hằng số bằng 0" in sub3.description
    assert "\\frac{d}{dx}(-8) = 0" in sub3.equation_latex or "\\frac{d}{dx}(8) = 0" in sub3.equation_latex

    # Final boxed conclusion
    final_lhs = format_final_answer_latex(response.final_latex, ProblemType.DERIVATIVE, "x", {"order": 1})
    assert "f'(x) = 6 x^{2} + 6" in final_lhs or "f'(x) = 6x^2 + 6" in final_lhs


def test_mandatory_indefinite_integral_regression_unified_derivation():
    """Mandatory Regression 2: f(x) = 2x^3 + 6x - 8 -> F(x) = x^4/2 + 3x^2 - 8x + C.

    Verifies:
    - Final antiderivative is x^4/2 + 3x^2 - 8x + C.
    - Linearity applied to full integrand.
    - Power rule applied to each term with assumption n != -1.
    - Exactly one arbitrary constant C.
    - Differentiating antiderivative recovers 2x^3 + 6x - 8.
    - Main solution continuous and understandable collapsed.
    """
    solver = IntegralSolver()
    request = ProblemRequest("2*x^3 + 6*x - 8", ProblemType.INDEFINITE_INTEGRAL, target_variable="x")
    response = solver.solve(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED

    # Check symbolic antiderivative differentiation recovers original
    x = sp.Symbol("x")
    anti_without_c = sp.sympify(response.final_result.replace("+ C", "").strip())
    recovered = sp.diff(anti_without_c, x)
    assert sp.simplify(recovered - (2 * (x ** 3) + 6 * x - 8)) == 0

    # Final latex contains x^4/2 + 3x^2 - 8x + C
    assert "\\frac{x^{4}}{2} + 3 x^{2} - 8 x + C" in response.final_latex
    assert response.final_latex.count("+ C") == 1

    # Main derivation has exactly 2 steps
    assert len(response.steps) == 2

    # Step 1: Linearity of Integration
    step1 = response.steps[0]
    assert "tuyến tính" in step1.display_title.lower()
    assert step1.equation_latex != ""
    assert "\\begin{aligned}" in step1.equation_latex
    assert "\\int f(x)\\,dx" in step1.equation_latex
    assert "\\int 2 x^{3}\\,dx + \\int 6 x\\,dx - \\int 8\\,dx" in step1.equation_latex
    assert "**" not in step1.equation_latex

    # Step 2: Power Rule with condition n != -1
    step2 = response.steps[1]
    assert "lũy thừa" in step2.display_title.lower()
    assert step2.equation_latex != ""
    assert "\\begin{aligned}" in step2.equation_latex
    assert "2\\cdot\\frac{x^{4}}{4} + 6\\cdot\\frac{x^2}{2} - 8x + C" in step2.equation_latex
    assert "\\frac{x^{4}}{2} + 3 x^{2} - 8 x + C" in step2.equation_latex

    # Assumptions explicitly noted
    assert any("n \\ne -1" in a for a in step2.assumptions)

    # Optional Layer B Substeps under Step 2
    assert len(step2.substeps) == 3
    sub1 = step2.substeps[0]
    assert "\\int 2 x^{3}\\,dx = 2\\cdot\\frac{x^{4}}{4} = \\frac{x^{4}}{2}" in sub1.equation_latex

    sub2 = step2.substeps[1]
    assert "\\int 6 x\\,dx = 6\\cdot\\frac{x^2}{2} = 3 x^{2}" in sub2.equation_latex

    sub3 = step2.substeps[2]
    assert "-8" in sub3.equation_latex
    assert "- 8 x" in sub3.equation_latex or "-8 x" in sub3.equation_latex or "-8x" in sub3.equation_latex

    # Final answer notation with LHS
    final_lhs = format_final_answer_latex(response.final_latex, ProblemType.INDEFINITE_INTEGRAL, "x")
    assert "\\int f(x)\\,dx =" in final_lhs


def test_generalization_polynomial_multiple_positive_negative_terms():
    """Generalization: f(x) = 4x^5 - 3x^3 + 7x - 2."""
    d_solver = DerivativeSolver()
    req_d = ProblemRequest("4*x^5 - 3*x^3 + 7*x - 2", ProblemType.DERIVATIVE, "x")
    resp_d = d_solver.solve(req_d)

    assert resp_d.status == SolutionStatus.SUCCESS
    assert resp_d.verification.status == VerificationStatus.VERIFIED
    x = sp.Symbol("x")
    assert sp.simplify(sp.sympify(resp_d.final_result) - (20 * x**4 - 9 * x**2 + 7)) == 0
    assert len(resp_d.steps) == 2
    assert len(resp_d.steps[1].substeps) == 4

    # Indefinite Integral
    i_solver = IntegralSolver()
    req_i = ProblemRequest("4*x^5 - 3*x^3 + 7*x - 2", ProblemType.INDEFINITE_INTEGRAL, "x")
    resp_i = i_solver.solve(req_i)

    assert resp_i.status == SolutionStatus.SUCCESS
    assert resp_i.verification.status == VerificationStatus.VERIFIED
    anti_without_c = sp.sympify(resp_i.final_result.replace("+ C", "").strip())
    assert sp.simplify(sp.diff(anti_without_c, x) - (4 * x**5 - 3 * x**3 + 7 * x - 2)) == 0
    assert len(resp_i.steps) == 2
    assert len(resp_i.steps[1].substeps) == 4


def test_generalization_product_rule_continuous_derivation():
    """Generalization: f(x) = x^2 * sin(x) uses continuous Product Rule derivation."""
    solver = DerivativeSolver()
    req = ProblemRequest("x^2 * sin(x)", ProblemType.DERIVATIVE, "x")
    resp = solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    prod_step = next(s for s in resp.steps if s.rule_name == "Product Rule")
    assert prod_step.equation_latex != ""
    assert "\\begin{aligned}" in prod_step.equation_latex
    assert "u'v + uv'" in prod_step.description or "u · v" in prod_step.description
    assert len(prod_step.substeps) >= 2


def test_generalization_chain_rule_continuous_derivation():
    """Generalization: f(x) = sin(x^2) uses continuous Chain Rule derivation."""
    solver = DerivativeSolver()
    req = ProblemRequest("sin(x^2)", ProblemType.DERIVATIVE, "x")
    resp = solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    chain_step = next(s for s in resp.steps if s.rule_name == "Chain Rule")
    assert chain_step.equation_latex != ""
    assert "\\begin{aligned}" in chain_step.equation_latex
    assert "\\cos" in chain_step.equation_latex and "x^{2}" in chain_step.equation_latex


def test_generalization_integrand_multiple_powers():
    """Generalization: int(3*x^4 - 2*x^2 + 5 dx) has clean power rules and recovers integrand."""
    solver = IntegralSolver()
    req = ProblemRequest("3*x^4 - 2*x^2 + 5", ProblemType.INDEFINITE_INTEGRAL, "x")
    resp = solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    x = sp.Symbol("x")
    anti = sp.sympify(resp.final_result.replace("+ C", "").strip())
    assert sp.simplify(sp.diff(anti, x) - (3 * x**4 - 2 * x**2 + 5)) == 0


def test_generalization_unsupported_rule_honest_limitation():
    """Generalization: engine honestly reports limitation without fabricating misleading steps."""
    builder = DifferentiationStepBuilder()
    engine = DifferentiationRuleEngine(rules=[PowerRule()])  # Only power rule configured
    x = sp.Symbol("x")
    expr = sp.sin(x)

    res = engine.differentiate(expr, x, builder)
    assert sp.simplify(res - sp.cos(x)) == 0
    assert engine.had_fallback

    steps = builder.get_steps()
    assert len(steps) == 1
    fallback = steps[0]
    assert fallback.rule_name == "Symbolic Differentiation Engine"
    assert "chưa có quy tắc sư phạm" in fallback.description
    assert fallback.notes == "Giới hạn phân rã sư phạm"

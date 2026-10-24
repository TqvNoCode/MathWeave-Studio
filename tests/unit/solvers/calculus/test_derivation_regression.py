"""Regression tests verifying structured Vietnamese derivations, rules, and mathematical correctness."""

import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.differentiation.solver import DerivativeSolver


def test_derivation_x_squared():
    """Requirement: f(x) = x^2 produces f'(x) = 2x with Vietnamese pedagogical steps."""
    solver = DerivativeSolver()
    request = ProblemRequest("x^2", ProblemType.DERIVATIVE, target_variable="x")
    response = solver.solve(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED

    # Symbolic equivalence: 2*x
    x = sp.Symbol("x")
    expected = 2 * x
    actual = sp.sympify(response.final_result)
    assert sp.simplify(actual - expected) == 0

    # Steps verification
    assert len(response.steps) >= 1
    step1 = response.steps[0]
    assert step1.rule_name == "Power Rule"
    assert step1.display_rule_name == "Quy tắc đạo hàm của lũy thừa"
    assert "lũy thừa" in step1.display_title.lower()
    # Vietnamese explanation must be present
    assert any(w in step1.description for w in ("lũy thừa", "hàm số", "quy tắc"))


def test_derivation_product_rule_x2_sin_x():
    """Requirement: f(x) = x^2 * sin(x) generates valid product-rule steps in Vietnamese."""
    solver = DerivativeSolver()
    request = ProblemRequest("x^2 * sin(x)", ProblemType.DERIVATIVE, target_variable="x")
    response = solver.solve(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED

    # Check rule name in Vietnamese
    prod_step = next(s for s in response.steps if s.rule_name == "Product Rule")
    assert prod_step.display_rule_name == "Quy tắc đạo hàm của tích"
    assert "tích" in prod_step.display_title.lower()
    assert "u · v" in prod_step.description or "u'v + uv'" in prod_step.description
    assert len(prod_step.substeps) >= 2

    # Check intermediate factors in substeps
    substep_rules = [s.display_rule_name for s in prod_step.substeps]
    assert "Quy tắc đạo hàm của lũy thừa" in substep_rules
    assert "Quy tắc đạo hàm của hàm lượng giác" in substep_rules


def test_derivation_chain_rule_sin_x2():
    """Requirement: f(x) = sin(x^2) generates valid chain-rule steps in Vietnamese."""
    solver = DerivativeSolver()
    request = ProblemRequest("sin(x^2)", ProblemType.DERIVATIVE, target_variable="x")
    response = solver.solve(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED

    chain_step = next(s for s in response.steps if s.rule_name == "Chain Rule")
    assert chain_step.display_rule_name == "Quy tắc đạo hàm của hàm hợp"
    assert "hợp" in chain_step.display_title.lower()
    assert "hàm hợp" in chain_step.description.lower()
    assert len(chain_step.substeps) >= 1


def test_all_visible_rules_in_vietnamese():
    """Verify that every supported rule produces a natural, accurate Vietnamese name and title."""
    solver = DerivativeSolver()
    test_expressions = [
        "x^3",
        "5*x",
        "x + 3",
        "x * cos(x)",
        "x / (x + 2)",
        "cos(x^2)",
        "sin(x)",
        "exp(x)",
        "log(x)",
    ]
    for expr_str in test_expressions:
        req = ProblemRequest(expr_str, ProblemType.DERIVATIVE, target_variable="x")
        resp = solver.solve(req)
        assert resp.status == SolutionStatus.SUCCESS
        for step in resp.steps:
            assert step.display_rule_name.startswith("Quy tắc") or "đạo hàm" in step.display_rule_name.lower() or "hằng số" in step.display_rule_name.lower()
            assert step.display_title != ""


def test_unsupported_rule_limitations_labeled_honestly():
    """Unsupported operations should not fabricate steps, and must state limitation honestly in Vietnamese."""
    from math_app.solvers.calculus.differentiation.rule_engine import DifferentiationRuleEngine
    from math_app.solvers.calculus.differentiation.step_builder import DifferentiationStepBuilder

    # Empty engine without rules forces fallback
    engine = DifferentiationRuleEngine(rules=[])
    builder = DifferentiationStepBuilder()
    x = sp.Symbol("x")
    expr = sp.besselj(0, x)  # Special function not in standard curriculum rules

    res = engine.differentiate(expr, x, builder)
    assert res is not None
    assert engine.had_fallback is True

    steps = builder.get_steps()
    assert len(steps) == 1
    fallback_step = steps[0]
    assert fallback_step.display_rule_name == "Tính toán ký hiệu trực tiếp"
    assert "ký hiệu" in fallback_step.description or "sư phạm" in fallback_step.description

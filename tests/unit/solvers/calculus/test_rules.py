"""Unit tests for individual differentiation transformation rules."""

import sympy as sp

from math_app.solvers.calculus.differentiation.rule_engine import DifferentiationRuleEngine
from math_app.solvers.calculus.differentiation.rules.chain_rule import ChainRule
from math_app.solvers.calculus.differentiation.rules.constant_rule import (
    ConstantMultipleRule,
    ConstantRule,
)
from math_app.solvers.calculus.differentiation.rules.power_rule import PowerRule
from math_app.solvers.calculus.differentiation.rules.product_rule import ProductRule
from math_app.solvers.calculus.differentiation.rules.quotient_rule import QuotientRule
from math_app.solvers.calculus.differentiation.rules.sum_rule import SumRule
from math_app.solvers.calculus.differentiation.rules.trig_rule import TrigRule
from math_app.solvers.calculus.differentiation.step_builder import DifferentiationStepBuilder


def test_constant_rule():
    rule = ConstantRule()
    x = sp.Symbol("x")
    expr = sp.Integer(42)
    assert rule.can_apply(expr, x)

    builder = DifferentiationStepBuilder()
    engine = DifferentiationRuleEngine()
    result = rule.apply(expr, x, engine, builder)

    assert result == 0
    steps = builder.get_steps()
    assert len(steps) == 1
    assert steps[0].rule_name == "Constant Rule"


def test_power_rule():
    rule = PowerRule()
    x = sp.Symbol("x")
    expr = x ** 3
    assert rule.can_apply(expr, x)

    builder = DifferentiationStepBuilder()
    engine = DifferentiationRuleEngine()
    result = rule.apply(expr, x, engine, builder)

    assert result == 3 * (x ** 2)
    steps = builder.get_steps()
    assert len(steps) == 1
    assert steps[0].rule_name == "Power Rule"


def test_constant_multiple_rule():
    rule = ConstantMultipleRule()
    x = sp.Symbol("x")
    expr = 5 * (x ** 2)
    assert rule.can_apply(expr, x)

    builder = DifferentiationStepBuilder()
    engine = DifferentiationRuleEngine()
    result = rule.apply(expr, x, engine, builder)

    assert sp.simplify(result - 10 * x) == 0
    steps = builder.get_steps()
    assert steps[0].rule_name == "Constant Multiple Rule"
    assert len(steps[0].substeps) >= 1


def test_sum_rule():
    rule = SumRule()
    x = sp.Symbol("x")
    expr = (x ** 2) + (3 * x)
    assert rule.can_apply(expr, x)

    builder = DifferentiationStepBuilder()
    engine = DifferentiationRuleEngine()
    result = rule.apply(expr, x, engine, builder)

    assert sp.simplify(result - (2 * x + 3)) == 0
    steps = builder.get_steps()
    assert steps[0].rule_name == "Sum / Difference Rule"
    assert len(steps[0].substeps) == 2


def test_product_rule():
    rule = ProductRule()
    x = sp.Symbol("x")
    expr = (x ** 2) * sp.sin(x)
    assert rule.can_apply(expr, x)

    builder = DifferentiationStepBuilder()
    engine = DifferentiationRuleEngine()
    result = rule.apply(expr, x, engine, builder)

    expected = 2 * x * sp.sin(x) + (x ** 2) * sp.cos(x)
    assert sp.simplify(result - expected) == 0
    steps = builder.get_steps()
    assert steps[0].rule_name == "Product Rule"
    assert len(steps[0].substeps) >= 2


def test_quotient_rule():
    rule = QuotientRule()
    x = sp.Symbol("x")
    expr = x * ((x + 1) ** (-1))  # x / (x + 1)
    assert rule.can_apply(expr, x)

    builder = DifferentiationStepBuilder()
    engine = DifferentiationRuleEngine()
    result = rule.apply(expr, x, engine, builder)

    expected = 1 / ((x + 1) ** 2)
    assert sp.simplify(result - expected) == 0
    steps = builder.get_steps()
    assert steps[0].rule_name == "Quotient Rule"
    assert any(term in (steps[0].notes or "") for term in ("Điều kiện mẫu số xác định", "Requires denominator"))


def test_chain_rule():
    rule = ChainRule()
    x = sp.Symbol("x")
    expr = sp.sin(x ** 2)
    assert rule.can_apply(expr, x)

    builder = DifferentiationStepBuilder()
    engine = DifferentiationRuleEngine()
    result = rule.apply(expr, x, engine, builder)

    expected = 2 * x * sp.cos(x ** 2)
    assert sp.simplify(result - expected) == 0
    steps = builder.get_steps()
    assert steps[0].rule_name == "Chain Rule"
    assert len(steps[0].substeps) >= 1

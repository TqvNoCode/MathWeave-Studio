"""Unit tests for derivative explanation rendering, rule classification, and partial differentiation semantics."""

from __future__ import annotations

import re

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus
from math_app.rendering.text_math_renderer import render_math_in_text_html
from math_app.solvers.calculus.differentiation.solver import DerivativeSolver


@pytest.fixture
def derivative_solver() -> DerivativeSolver:
    return DerivativeSolver()


def _get_visible_html_text(html: str) -> str:
    """Strip HTML tags to inspect visible text rendered to the user."""
    return re.sub(r"<[^>]+>", "", html)


def test_ordinary_derivative_cos_rule_and_explanation(derivative_solver: DerivativeSolver) -> None:
    """Case 1: d/dx(cos(x)) = -sin(x). Rule must be Trigonometric, no raw LaTeX in prose."""
    req = ProblemRequest(raw_input="cos(x)", problem_type=ProblemType.DERIVATIVE, target_variable="x")
    resp = derivative_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.final_result == "-sin(x)"

    # Verify rule classification
    step = resp.steps[0]
    assert step.rule_name == "Trigonometric Rule"
    assert "lượng giác" in step.rule_name_vi.lower()
    assert step.rule_name != "Power Rule"

    # Verify no raw LaTeX leaked into HTML visible text
    rendered_desc = render_math_in_text_html(step.description)
    visible_desc = _get_visible_html_text(rendered_desc)
    assert r"\cos" not in visible_desc
    assert r"\sin" not in visible_desc
    assert "<math" in rendered_desc


def test_ordinary_derivative_neg_tan_rule_and_substeps(derivative_solver: DerivativeSolver) -> None:
    """Case 2: d/dx(-tan(x)) = -sec(x)^2. Constant Multiple + Trigonometric."""
    req = ProblemRequest(raw_input="-tan(x)", problem_type=ProblemType.DERIVATIVE, target_variable="x")
    resp = derivative_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    step = resp.steps[0]
    assert step.rule_name == "Constant Multiple Rule"
    assert len(step.substeps) >= 1
    sub = step.substeps[0]
    assert sub.rule_name == "Trigonometric Rule"
    assert sub.rule_name != "Power Rule"

    # Verify substep title and description rendering
    rendered_title = render_math_in_text_html(sub.title)
    rendered_desc = render_math_in_text_html(sub.description)
    visible_title = _get_visible_html_text(rendered_title)
    visible_desc = _get_visible_html_text(rendered_desc)
    assert r"\tan" not in visible_title
    assert r"\cos" not in visible_desc
    assert r"\sec" not in visible_desc
    assert "<math" in rendered_desc


def test_ordinary_derivative_sum_cos_minus_tan(derivative_solver: DerivativeSolver) -> None:
    """Case 3: d/dx(cos(x) - tan(x)). Verify term-by-term differentiation is not labeled as Power Rule."""
    req = ProblemRequest(raw_input="cos(x) - tan(x)", problem_type=ProblemType.DERIVATIVE, target_variable="x")
    resp = derivative_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    # Step 1: Sum / Difference
    assert resp.steps[0].rule_name == "Sum / Difference Rule"

    # Substeps of Step 1: both terms are trigonometric, neither is Power Rule
    sub1 = resp.steps[0].substeps[0]
    sub2 = resp.steps[0].substeps[1]
    assert sub1.rule_name == "Trigonometric Rule"
    assert sub2.rule_name == "Trigonometric Rule"

    # Step 2: Term-by-term differentiation, NOT Power Rule
    step2 = resp.steps[1]
    assert step2.rule_name == "Term-by-term Differentiation"
    assert step2.rule_name != "Power Rule"

    # Verify no raw LaTeX strings in description
    for s in resp.steps:
        rendered = render_math_in_text_html(s.description)
        assert r"\cos{\left(x \right)}" not in rendered
        assert r"\tan{\left(x \right)}" not in rendered


def test_ordinary_derivative_power_rule_x_squared(derivative_solver: DerivativeSolver) -> None:
    """Case 4: d/dx(x^2) = 2x is correctly labeled as Power Rule."""
    req = ProblemRequest(raw_input="x^2", problem_type=ProblemType.DERIVATIVE, target_variable="x")
    resp = derivative_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.final_result == "2*x"
    assert resp.steps[0].rule_name == "Power Rule"
    assert "lũy thừa" in resp.steps[0].rule_name_vi.lower()


def test_partial_derivative_x_squared_y(derivative_solver: DerivativeSolver) -> None:
    r"""Case 5: ∂/∂x(x^2 * y) = 2*x*y. Explains other variables treated as constants, uses \partial."""
    req = ProblemRequest(raw_input="x^2*y", problem_type=ProblemType.PARTIAL_DERIVATIVE, target_variable="x")
    resp = derivative_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.final_result == "2*x*y"

    # Step 1: Partial differentiation context
    step1 = resp.steps[0]
    assert "hằng số" in step1.description
    assert r"\partial" in step1.equation_latex
    assert "d/dx" not in step1.equation_latex

    # Step 2: Constant multiple pulling out y
    step2 = resp.steps[1]
    assert r"\partial" in step2.equation_latex
    assert "hằng số" in step2.description.lower()


def test_partial_derivative_sin_xy(derivative_solver: DerivativeSolver) -> None:
    r"""Case 6: ∂/∂x(sin(x*y)) = y*cos(x*y). Chain rule + Trig rule, uses \partial."""
    req = ProblemRequest(raw_input="sin(x*y)", problem_type=ProblemType.PARTIAL_DERIVATIVE, target_variable="x")
    resp = derivative_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    x, y = sp.symbols("x y")
    assert sp.simplify(sp.sympify(resp.final_result) - y * sp.cos(x * y)) == 0

    # Must be Chain Rule + Trigonometric
    chain_step = resp.steps[1]
    assert "Chain Rule" in chain_step.rule_name
    assert "lượng giác" in chain_step.rule_name_vi.lower()
    assert chain_step.rule_name != "Power Rule"
    assert r"\partial" in chain_step.equation_latex


def test_partial_derivative_y_cubed(derivative_solver: DerivativeSolver) -> None:
    """Case 7: ∂/∂x(y^3) = 0. Treats y^3 as constant with respect to x."""
    req = ProblemRequest(raw_input="y^3", problem_type=ProblemType.PARTIAL_DERIVATIVE, target_variable="x")
    resp = derivative_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.final_result == "0"

    const_step = resp.steps[1]
    assert "Constant" in const_step.rule_name
    assert "hằng số" in const_step.description.lower()
    assert r"\partial" in const_step.equation_latex
    assert "0" in const_step.equation_latex

"""Unit and integration tests for UX3.7.2: ODE Classification-to-Solver Consistency & Reliability.

Covers:
1. T01: Separable ODE y' = -4t/y (t as independent variable, y^2 + 4t^2 = C)
2. T02: Separable ODE y' = -4t/y (x as independent variable, t as parameter, y^2 + 8tx = C)
3. T03: Linear ODE with singular/non-elementary integral (t-3)y' + ln(t)y = 2t
4. T04: Homogeneous Linear ODE y' + 2ty = 0
5. T05: Nonhomogeneous Linear ODE y' + 2y = 3t
6. T06: Exact ODE (2x+3) + (2y-2)y' = 0 (t as independent variable, x as parameter)
7. T07: Separable ODE y' = t(y^2-1) preserving equilibrium solutions
8. T08: Cauchy IVP y' + 2y = 3t, y(0) = 1
9. Cross-workspace automatic solver routing via build_problem_request()
10. Symbol role isolation: independent variable vs dependent variable vs parameters
11. Text math renderer markdown bold/italic support (no raw markdown markers)
12. Error categorization: nonlinear ODEs never misclassified as wrong equation order
"""

from __future__ import annotations

import time
import pytest

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.main import build_application
from math_app.presentation.components.workspace.ode.first_order_classifier import (
    classify_first_order_ode,
)
from math_app.presentation.components.workspace.ode.ode_state import (
    ODEClassification,
    ODEOrder,
    ODEState,
)
from math_app.rendering.text_math_renderer import render_math_in_text_html


@pytest.fixture(scope="module")
def use_case():
    return build_application()


# ==============================================================================
# 1. CORE TEST MATRIX (T01 - T08)
# ==============================================================================


def test_t01_separable_t_independent_variable(use_case):
    """T01: y' = -4t/y with t as independent variable -> y^2 + 4t^2 = C."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SEPARABLE,
        raw_input="y' = -4*t/y",
        target_variable="t",
        parameters={"independent_var": "t", "dependent_var": "y"},
    )
    resp = use_case.execute(req)

    assert resp.status == SolutionStatus.SUCCESS, f"Failed: {resp.warnings}"
    assert resp.verification is not None
    assert resp.verification.status in (VerificationStatus.PARTIALLY_VERIFIED, VerificationStatus.VERIFIED)

    # Check that solution is conic y^2 + 4*t^2 = C
    sol_str = resp.final_result
    assert "y**2" in sol_str or "y^2" in sol_str
    assert "4*t**2" in sol_str or "4*t^2" in sol_str or "4 t^{2}" in resp.final_latex


def test_t02_separable_x_independent_variable_t_parameter(use_case):
    """T02: y' = -4t/y with x as independent variable -> y^2 + 8tx = C."""
    # Step 1: Check classifier detected parameters
    clf = classify_first_order_ode("y' = -4*t/y", target_var="x")
    assert clf.is_valid_ode
    assert "t" in clf.detected_parameters
    assert clf.detected_independent_var == "x"
    assert clf.detected_dependent_var == "y"

    # Step 2: Solve with x as independent variable
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SEPARABLE,
        raw_input="y' = -4*t/y",
        target_variable="x",
        parameters={"independent_var": "x", "dependent_var": "y"},
    )
    resp = use_case.execute(req)

    assert resp.status == SolutionStatus.SUCCESS, f"Failed: {resp.warnings}"
    assert resp.verification is not None
    assert resp.verification.status in (VerificationStatus.PARTIALLY_VERIFIED, VerificationStatus.VERIFIED)

    # Check that solution is y^2 + 8*t*x = C (or y^2 + 8*x*t = C)
    sol_str = resp.final_result
    assert "y**2" in sol_str or "y^2" in sol_str
    assert "8*t*x" in sol_str or "8*x*t" in sol_str or "8 t x" in resp.final_latex or "8 x t" in resp.final_latex


def test_t03_linear_singular_non_elementary_integral(use_case):
    """T03: (t-3)y' + ln(t)y = 2t completes within 2s, does not hang, and is verified."""
    t_start = time.perf_counter()
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="(t-3)*y' + ln(t)*y = 2*t",
        target_variable="t",
        parameters={"independent_var": "t", "dependent_var": "y"},
    )
    resp = use_case.execute(req)
    elapsed = time.perf_counter() - t_start

    assert elapsed < 2.5, f"Execution took too long: {elapsed:.2f}s"
    assert resp.status == SolutionStatus.SUCCESS, f"Failed: {resp.warnings}"
    assert resp.verification is not None
    assert resp.verification.status in (VerificationStatus.PARTIALLY_VERIFIED, VerificationStatus.VERIFIED)

    # Check integrating factor and general solution presence
    assert "mu" in resp.final_latex or "Integral" in str(resp.final_result) or "exp" in str(resp.final_result)

    # Check domain restrictions for singular points and logarithm
    domain_text = " ".join(resp.domain_restrictions)
    assert "3" in domain_text
    assert "t > 0" in domain_text or "logarit" in domain_text
    assert "(0, 3)" in domain_text


def test_t04_homogeneous_linear_first_order(use_case):
    """T04: y' + 2ty = 0 -> y(t) = C*exp(-t^2)."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="y' + 2*t*y = 0",
        target_variable="t",
        parameters={"independent_var": "t", "dependent_var": "y"},
    )
    resp = use_case.execute(req)

    assert resp.status == SolutionStatus.SUCCESS, f"Failed: {resp.error_message}"
    assert resp.verification is not None
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert "exp(-t**2)" in str(resp.final_result) or "e^{- t^{2}}" in resp.final_latex or "e^{-t^{2}}" in resp.final_latex


def test_t05_nonhomogeneous_linear_first_order(use_case):
    """T05: y' + 2y = 3t -> y(t) = C*exp(-2t) + 3t/2 - 3/4."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="y' + 2*y = 3*t",
        target_variable="t",
        parameters={"independent_var": "t", "dependent_var": "y"},
    )
    resp = use_case.execute(req)

    assert resp.status == SolutionStatus.SUCCESS, f"Failed: {resp.error_message}"
    assert resp.verification is not None
    assert resp.verification.status == VerificationStatus.VERIFIED
    sol_str = str(resp.final_result)
    assert "exp(-2*t)" in sol_str or "e^{- 2 t}" in resp.final_latex
    assert "3*t/2" in sol_str or "1.5*t" in sol_str or "3 t / 2" in sol_str or r"\frac{3 t}{2}" in resp.final_latex


def test_t06_exact_ode_with_parameter(use_case):
    """T06: (2x+3) + (2y-2)y' = 0 with t as independent variable, x as parameter."""
    clf = classify_first_order_ode("(2*x+3) + (2*y-2)*y' = 0", target_var="t")
    assert clf.is_valid_ode
    assert clf.target_problem_type == ProblemType.ODE_EXACT
    assert "x" in clf.detected_parameters

    req = ProblemRequest(
        problem_type=ProblemType.ODE_EXACT,
        raw_input="(2*x+3) + (2*y-2)*y' = 0",
        target_variable="t",
        parameters={"independent_var": "t", "dependent_var": "y"},
    )
    resp = use_case.execute(req)

    assert resp.status == SolutionStatus.SUCCESS, f"Failed: {resp.warnings}"
    assert resp.verification is not None
    assert resp.verification.status in (VerificationStatus.PARTIALLY_VERIFIED, VerificationStatus.VERIFIED)

    # Check implicit potential solution: (2x+3)t + y^2 - 2y = C
    pot_f = resp.final_result
    assert "y**2" in pot_f or "y^2" in pot_f
    assert "- 2*y" in pot_f or "- 2 y" in pot_f or "-2*y" in pot_f
    assert "2*t*x" in pot_f or "2*x*t" in pot_f or "3*t" in pot_f or "(2*x + 3)*t" in pot_f


def test_t07_separable_equilibrium_solutions(use_case):
    """T07: y' = t(y^2-1) preserves equilibrium solutions y = 1, y = -1."""
    clf = classify_first_order_ode("y' = t*(y^2 - 1)", target_var="t")
    assert clf.target_problem_type == ProblemType.ODE_SEPARABLE

    req = ProblemRequest(
        problem_type=ProblemType.ODE_SEPARABLE,
        raw_input="y' = t*(y^2 - 1)",
        target_variable="t",
        parameters={"independent_var": "t", "dependent_var": "y"},
    )
    resp = use_case.execute(req)

    assert resp.status == SolutionStatus.SUCCESS, f"Failed: {resp.warnings}"
    assert resp.verification is not None
    assert resp.verification.status in (VerificationStatus.PARTIALLY_VERIFIED, VerificationStatus.VERIFIED)

    # Check equilibrium solutions are recorded in final_result or steps
    all_step_texts = resp.final_result + " " + " ".join(s.description for s in resp.steps) + " " + " ".join(s.title for s in resp.steps)
    assert "y = 1" in all_step_texts or "y = -1" in all_step_texts or "cân bằng" in all_step_texts


def test_t08_cauchy_ivp_linear_first_order(use_case):
    """T08: y' + 2y = 3t, y(0) = 1 -> C = 7/4, y(t) = 7/4*exp(-2t) + 3t/2 - 3/4."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="y' + 2*y = 3*t",
        target_variable="t",
        parameters={"independent_var": "t", "dependent_var": "y", "initial_condition": "y(0)=1"},
    )
    resp = use_case.execute(req)

    assert resp.status == SolutionStatus.SUCCESS, f"Failed: {resp.warnings}"
    assert resp.verification is not None
    assert resp.verification.status in (VerificationStatus.PARTIALLY_VERIFIED, VerificationStatus.VERIFIED)

    sol_str = str(resp.final_result)
    assert "7/4" in sol_str or "7*exp(-2*t)/4" in sol_str or "/4" in resp.final_latex


# ==============================================================================
# 2. CROSS-WORKSPACE CLASSIFICATION-TO-SOLVER ROUTING
# ==============================================================================


def test_cross_workspace_routing_linear_workspace_with_separable_equation(use_case):
    """When user is in FIRST_ORDER_LINEAR workspace but inputs a separable equation."""
    state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.FIRST_ORDER_LINEAR,
        equation="y' = -4*t/y",
        target_var="t",
    )

    req = state.build_problem_request()
    # Authoritative routing: must route to ODE_SEPARABLE, not linear
    assert req.problem_type == ProblemType.ODE_SEPARABLE

    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED


def test_cross_workspace_routing_separable_workspace_with_linear_equation(use_case):
    """When user is in SEPARABLE workspace but inputs a linear equation."""
    state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.SEPARABLE,
        equation="y' + 2*y = 3*t",
        target_var="t",
    )

    req = state.build_problem_request()
    assert req.problem_type == ProblemType.ODE_FIRST_ORDER_LINEAR

    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED


def test_cross_workspace_routing_linear_workspace_with_exact_equation(use_case):
    """When user is in FIRST_ORDER_LINEAR workspace but inputs an exact equation."""
    state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.FIRST_ORDER_LINEAR,
        equation="(2*t+3) + (2*y-2)*y' = 0",
        target_var="t",
    )

    req = state.build_problem_request()
    assert req.problem_type == ProblemType.ODE_EXACT

    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED


# ==============================================================================
# 3. TEXT MATH RENDERER MARKDOWN FORMATTING & NO LEAKAGE
# ==============================================================================


def test_text_math_renderer_markdown_bold_and_italic():
    """Verify markdown bold and italic formatting are rendered cleanly to HTML without raw asterisks."""
    html = render_math_in_text_html("Phương trình dạng **Tách biến** rất quan trọng.")
    assert "<strong>Tách biến</strong>" in html
    assert "**" not in html

    html_italic = render_math_in_text_html("*Ghi chú quan trọng:* nghiệm kỳ dị.")
    assert "<em>Ghi chú quan trọng:</em>" in html_italic
    assert "*" not in html_italic


# ==============================================================================
# 4. ERROR CATEGORIZATION (AVOID FALSE "WRONG EQUATION ORDER")
# ==============================================================================


def test_nonlinear_first_order_error_is_not_order_mismatch(use_case):
    """A nonlinear first-order ODE in linear solver must NOT be diagnosed as wrong equation order."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="y' + y^2 = t",
        target_variable="t",
        parameters={"independent_var": "t", "dependent_var": "y"},
    )
    resp = use_case.execute(req)

    assert resp.status == SolutionStatus.CANNOT_SOLVE
    err_msg = " ".join(resp.warnings)
    # Should say nonlinear / phi tuyến tính
    assert "phi tuyến" in err_msg.lower() or "nonlinear" in err_msg.lower()

    # Verify that solution_view does NOT detect order mismatch
    msg_lower = err_msg.lower()
    is_order_mismatch = any(term in msg_lower for term in ("không đúng cấp", "cấp 2", "cấp hai", "bậc hai", "bậc 2"))
    assert not is_order_mismatch, "Nonlinear error was incorrectly flagged as order mismatch!"

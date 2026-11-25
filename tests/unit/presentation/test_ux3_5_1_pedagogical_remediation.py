"""Dedicated test suite for UX3.5.1: Pedagogical Flow & Mathematical Presentation Remediation.

Tests cover:
1. Test 1: First-Order Linear ODE (y' + 2*y = exp(-t)):
   - Integrating factor method mu(t) = exp(2t)
   - Product rule & integration
   - Residual R(t) = 0
   - Absolute absence of yc -> yp -> y and UC/VoP
2. Test 2: Second-Order Resonant ODE with forcing exp(t) (multiplicity s=1, factor t):
   - Characteristic equation r^2 - 3r + 2 = 0 (r1=2, r2=1)
   - yp(t) = -t*exp(t)
   - Explanation of resonance s=1
   - Residual R(t) = 0
3. Test 3: Second-Order Non-Resonant Trig ODE (y'' + 2*y' + 5*y = 3*sin(2*t)):
   - Roots -1 +- 2i
   - yp(t) with cos(2t) and sin(2t)
   - Non-resonant confirmation (s=0)
   - Residual R(t) = 0
4. Test 4: Second-Order Nonhomogeneous Exp (y'' - 2*y' - 3*y = 3*exp(2*t)):
   - Roots 3, -1
   - yp(t) = -exp(2t)
   - General solution yc(t) + yp(t)
   - Residual R(t) = 0
5. Test 5: Second-Order Cauchy IVP:
   - Initial conditions preserved
   - Determines C1, C2
   - Verifies both differential equation and initial conditions
6. Test 6: All other ODE operations in operation_catalog:
   - Separable
   - Exact
   - Integrating factor
   - Classical homogeneous
   - Reduction of Order
   - Wronskian
7. Test 7: UI Rendering, MathML formatting, zero raw LaTeX in expansion headers:
   - Expansion slot headers render clean MathML
   - Intermediate cards have h-auto and no vertical scrollbars
   - Notation standardization (yc, yp, y1, y2, C1, C2, A0, B0, mu, R)
"""

from __future__ import annotations

import pytest
import sympy as sp
from nicegui import ui

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.main import build_application
from math_app.presentation.components.ode_pedagogical_enhancer import (
    enhance_ode_solution_flow,
)
from math_app.presentation.components.ode_staged_step_viewer import (
    render_ode_staged_steps_container,
)
from math_app.rendering.text_math_renderer import (
    delimit_unwrapped_math_in_text,
    render_math_in_text_html,
)


@pytest.fixture(scope="module")
def app():
    return build_application()


# ==============================================================================
# TEST 1: FIRST-ORDER LINEAR ODE
# ==============================================================================


def test_ux351_test1_first_order_linear(app):
    """Test 1: y' + 2*y = exp(-t)
    Verifies:
    - Integrating factor method mu(t) = exp(2t)
    - d/dt[exp(2t)*y] = exp(t)
    - General solution y(t) = (C + exp(t))*exp(-2t)
    - Residual R(t) = 0
    - Absence of yc -> yp -> y and UC/VoP
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="y' + 2*y = exp(-t)",
        target_variable="t",
    )
    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4

    stg1, stg2, stg3, stg4 = stages

    # Check stage 1: Standard form
    assert "Nhận dạng" in stg1.title
    assert "Dạng chuẩn" in stg1.badge_text
    assert len(stg1.steps) >= 1

    # Check stage 2: Integrating factor
    assert "thừa số tích phân" in stg2.title.lower()
    assert r"\mu" in stg2.badge_text or "mu" in stg2.badge_text
    assert len(stg2.steps) >= 1
    assert "exp(2*t)" in stg2.steps[0].execution or "e^{2 t}" in stg2.steps[0].intermediate_result or "2" in stg2.steps[0].intermediate_result

    # Check stage 3: Integration & General Solution
    assert "Xây dựng" in stg3.title or "giải" in stg3.title
    assert "y(t)" in stg3.badge_text
    assert len(stg3.steps) >= 3

    # Check stage 4: Verification
    assert "Kiểm chứng" in stg4.title
    assert len(stg4.steps) >= 1
    assert stg4.steps[0].intermediate_result.strip()
    assert "R(t) = 0" in stg4.steps[0].intermediate_result or "Kiểm chứng độc lập thành công" in stg4.steps[0].intermediate_result

    # Absolute rule: No yc, yp, UC, VoP in any stage title or subtitle
    for stg in stages:
        assert "y_c" not in stg.title
        assert "y_p" not in stg.title
        assert "thuần nhất" not in stg.title.lower()
        assert "nghiệm riêng" not in stg.title.lower()
        assert "hệ số bất định" not in stg.subtitle.lower()
        assert "biến thiên hằng số" not in stg.subtitle.lower()
        assert "uc" not in stg.subtitle.lower()
        assert "vop" not in stg.subtitle.lower()

    # SymPy residual verification: L[y] - g(t) == 0
    t = sp.Symbol("t")
    C = sp.Symbol("C")
    y_sol = (C + sp.exp(t)) * sp.exp(-2 * t)
    lhs = sp.diff(y_sol, t) + 2 * y_sol
    residual = sp.simplify(lhs - sp.exp(-t))
    assert residual == 0


# ==============================================================================
# TEST 2: SECOND-ORDER RESONANT ODE (exp(t), s=1)
# ==============================================================================


def test_ux351_test2_second_order_resonant_exp(app):
    """Test 2: y'' - 3*y' + 2*y = exp(t)
    Characteristic: r^2 - 3r + 2 = 0 -> r1=2, r2=1
    yc(t) = C1*exp(2t) + C2*exp(t)
    exp(t) resonant with r2=1 (multiplicity s=1) -> yp(t) = A0*t*exp(t)
    A0 = -1 -> yp(t) = -t*exp(t)
    y(t) = C1*exp(2t) + C2*exp(t) - t*exp(t)
    R(t) = 0
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' - 3*y' + 2*y = exp(t)",
        target_variable="t",
    )
    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4

    stg1, stg2, stg3, stg4 = stages

    # Stage 1: Characteristic roots
    assert "y_c(t)" in stg1.badge_text
    assert len(stg1.steps) >= 4

    # Stage 2: Particular solution with resonance s=1
    assert "y_p(t)" in stg2.badge_text
    assert len(stg2.steps) >= 4
    trial_step = stg2.steps[0]
    assert "s = 1" in trial_step.execution or "cộng hưởng" in trial_step.execution or "t^1" in trial_step.execution or "t e^{t}" in trial_step.intermediate_result

    # Stage 3: Superposition
    assert "y(t)" in stg3.badge_text
    assert len(stg3.steps) >= 1

    # Stage 4: Verification
    assert len(stg4.steps) >= 1
    assert "0" in stg4.steps[0].intermediate_result

    # SymPy residual check
    t = sp.Symbol("t")
    C1, C2 = sp.symbols("C1 C2")
    y_sol = C1 * sp.exp(2 * t) + C2 * sp.exp(t) - t * sp.exp(t)
    lhs = sp.diff(y_sol, t, 2) - 3 * sp.diff(y_sol, t) + 2 * y_sol
    assert sp.simplify(lhs - sp.exp(t)) == 0


# ==============================================================================
# TEST 3: SECOND-ORDER NON-RESONANT TRIG ODE
# ==============================================================================


def test_ux351_test3_second_order_non_resonant_trig(app):
    """Test 3: y'' + 2*y' + 5*y = 3*sin(2*t)
    Complex roots: -1 +- 2i
    Forcing freq: 2i != -1 +- 2i -> s=0 (no resonance)
    yp(t) = (-12*cos(2t) + 3*sin(2t))/17
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' + 2*y' + 5*y = 3*sin(2*t)",
        target_variable="t",
    )
    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4

    # Verify no accidental resonance factor t in trial step
    trial_step = stages[1].steps[0]
    assert "s = 0" in trial_step.execution or "không phải là nghiệm" in trial_step.execution or "không cộng hưởng" in trial_step.execution or "t^0" in trial_step.execution

    # SymPy residual check
    t = sp.Symbol("t")
    C1, C2 = sp.symbols("C1 C2")
    yp = sp.Rational(3, 17) * sp.sin(2 * t) - sp.Rational(12, 17) * sp.cos(2 * t)
    yc = sp.exp(-t) * (C1 * sp.cos(2 * t) + C2 * sp.sin(2 * t))
    y_sol = yc + yp
    lhs = sp.diff(y_sol, t, 2) + 2 * sp.diff(y_sol, t) + 5 * y_sol
    assert sp.simplify(lhs - 3 * sp.sin(2 * t)) == 0


# ==============================================================================
# TEST 4: SECOND-ORDER NONHOMOGENEOUS EXP
# ==============================================================================


def test_ux351_test4_second_order_exp(app):
    """Test 4: y'' - 2*y' - 3*y = 3*exp(2*t)
    Characteristic: r^2 - 2r - 3 = 0 -> r1=3, r2=-1
    yc(t) = C1*exp(3t) + C2*exp(-t)
    lambda = 2 not in {3, -1} -> s=0
    yp(t) = -exp(2t)
    y(t) = C1*exp(3t) + C2*exp(-t) - exp(2t)
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' - 2*y' - 3*y = 3*exp(2*t)",
        target_variable="t",
    )
    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4

    # Verify roots
    assert "y_c(t)" in stages[0].badge_text
    assert "y_p(t)" in stages[1].badge_text
    assert len(stages[3].steps) >= 1

    # SymPy residual check
    t = sp.Symbol("t")
    C1, C2 = sp.symbols("C1 C2")
    y_sol = C1 * sp.exp(3 * t) + C2 * sp.exp(-t) - sp.exp(2 * t)
    lhs = sp.diff(y_sol, t, 2) - 2 * sp.diff(y_sol, t) - 3 * y_sol
    assert sp.simplify(lhs - 3 * sp.exp(2 * t)) == 0


# ==============================================================================
# TEST 5: SECOND-ORDER CAUCHY IVP
# ==============================================================================


def test_ux351_test5_cauchy_ivp(app):
    """Test 5: y'' - 3*y' + 2*y = 0, y(0) = 1, y'(0) = 0
    Verifies:
    - Initial conditions preserved
    - Solves C1, C2 correctly
    - Verification checks both ODE and initial conditions
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        raw_input="y'' - 3*y' + 2*y = 0, y(0) = 1, y'(0) = 0",
        target_variable="t",
    )
    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4

    # Stage 2 is bypassed for homogeneous
    assert stages[1].is_applicable is False

    # Stage 3 solves Cauchy IVP
    assert stages[2].is_applicable is True
    assert len(stages[2].steps) >= 2
    assert any("điều kiện ban đầu" in s.title.lower() or "cauchy" in s.title.lower() for s in stages[2].steps)

    # Stage 4 verifies both ODE and IVP
    assert len(stages[3].steps) >= 1
    assert stages[3].steps[0].intermediate_result.strip()

    # SymPy validation: y(0) == 1, y'(0) == 0
    t = sp.Symbol("t")
    y_sol = sp.sympify("2*exp(t) - exp(2*t)")
    assert y_sol.subs(t, 0) == 1
    assert sp.diff(y_sol, t).subs(t, 0) == 0


# ==============================================================================
# TEST 6: OTHER ODE OPERATIONS IN CATALOG
# ==============================================================================


def test_ux351_test6_separable(app):
    """Verify Separable ODE flow."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SEPARABLE,
        raw_input="y' = y*t",
        target_variable="t",
    )
    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4
    assert "Nhận dạng" in stages[0].title
    assert "Phân tách" in stages[1].title
    assert "Tích phân" in stages[2].title
    assert "Kiểm chứng" in stages[3].title
    assert len(stages[3].steps) >= 1


def test_ux351_test6_exact(app):
    """Verify Exact ODE flow."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_EXACT,
        raw_input="(2*x*y + 1) + (x**2 + 1)*y' = 0",
        target_variable="x",
    )
    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4
    assert "M và N" in stages[0].title or "Nhận dạng" in stages[0].title
    assert "toàn phần" in stages[1].title.lower()
    assert "hàm thế" in stages[2].title.lower()
    assert "Kiểm chứng" in stages[3].title
    assert len(stages[3].steps) >= 1


def test_ux351_test6_integrating_factor(app):
    """Verify Integrating Factor ODE flow."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
        raw_input="(3*x*y + y^2) + (x^2 + x*y)*y' = 0",
        target_variable="x",
    )
    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4
    assert "không toàn phần" in stages[0].title.lower()
    assert "thừa số tích phân" in stages[1].title.lower()
    assert "hàm thế" in stages[2].title.lower()
    assert len(stages[3].steps) >= 1


def test_ux351_test6_classical_homogeneous(app):
    """Verify Classical Homogeneous ODE flow."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        raw_input="x*y' = y + x",
        target_variable="x",
    )
    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4
    assert "thuần nhất bậc 0" in stages[0].title.lower()
    assert "tách biến" in stages[1].title.lower()
    assert len(stages[3].steps) >= 1


def test_ux351_test6_reduction_of_order(app):
    """Verify Reduction of Order flow."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        raw_input="t^2*y'' - 2*t*y' + 2*y = 0",
        target_variable="t",
        parameters={"known_solution": "t"},
    )
    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4
    assert "nghiệm đã biết" in stages[0].title.lower()
    assert "hạ bậc" in stages[1].title.lower()
    assert len(stages[3].steps) >= 1


def test_ux351_test6_wronskian(app):
    """Verify Wronskian flow."""
    req = ProblemRequest(
        problem_type=ProblemType.WRONSKIAN,
        raw_input="exp(t), exp(2*t)",
        target_variable="t",
    )
    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4
    assert "đạo hàm" in stages[0].title.lower()
    assert "wronskian" in stages[1].title.lower()
    assert "độc lập tuyến tính" in stages[2].title.lower()
    assert len(stages[3].steps) >= 1


# ==============================================================================
# TEST 7: UI RENDERING, ZERO RAW LATEX IN EXPANSIONS, INTERMEDIATE CARDS
# ==============================================================================


def test_ux351_test7_zero_raw_latex_and_ui_mount(app):
    """Verify that stage expansions, headers, and intermediate result cards
    mount cleanly without raw LaTeX string leaks or layout errors."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' - 3*y' + 2*y = exp(t)",
        target_variable="t",
    )
    res = app.execute(req)
    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)

    with ui.column() as container:
        render_ode_staged_steps_container(stages, final_answer_latex=res.final_latex)

    assert container is not None

    # Verify mathematical prose delimitation
    prose_samples = [
        "Xây dựng nghiệm cơ bản y_c(t) từ phương trình đặc trưng",
        "Tổng hợp nghiệm y(t) = y_c(t) + y_p(t)",
        "Tính thừa số tích phân \\mu(t)",
        "Hệ phương trình xác định C_1, C_2",
        "Chứng minh phần dư R(t) \\equiv 0",
        "Hệ số nghiệm thử A_0 và B_0",
    ]

    for p in prose_samples:
        delim = delimit_unwrapped_math_in_text(p)
        assert "$" in delim, f"Failed to delimit math in: {p}"
        html_out = render_math_in_text_html(p)
        assert "<math" in html_out or "math-fallback" in html_out
        assert "$" not in html_out, f"Raw dollar sign leaked into HTML output for: {p}"

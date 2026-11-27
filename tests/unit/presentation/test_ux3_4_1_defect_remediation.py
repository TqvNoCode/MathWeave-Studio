"""Regression and acceptance tests for UX3.4.1 Manual Acceptance Defect Remediation."""

from __future__ import annotations

from typing import Any
from nicegui import Client, ui
import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionStatus
from math_app.domain.models import ProblemType
from math_app.main import build_application
from math_app.presentation.components.algebra_step_enhancer import enhance_equation_factorization_steps
from math_app.presentation.components.domain_view import format_domain_condition
from math_app.presentation.components.operation_catalog import get_operation_by_type
from math_app.presentation.components.problem_statement import format_final_answer_latex
from math_app.presentation.components.solution_view import (
    _compute_approximate_roots,
    _filter_ui_warnings,
)
from math_app.presentation.components.workspace.ode.ode_mode_selector import render_ode_mode_selector
from math_app.presentation.components.workspace.ode.ode_state import ODEClassification, ODEMode, ODEOrder
from math_app.presentation.components.workspace.ode.ode_workspace import render_ode_workspace
from math_app.presentation.components.workspace.variable_selector import (
    render_adaptive_variable_selector,
)
from math_app.solvers.algebra.equation_solver import EquationSolver
from math_app.solvers.calculus.limit.solver import LimitSolver
from math_app.solvers.calculus.ode.integrating_factor_solver import ODEIntegratingFactorSolver
from math_app.solvers.calculus.ode.linear_solver import ODELinearSolver


# =============================================================================
# 1. VARIABLE SELECTOR INTEGRITY (Item 1)
# =============================================================================

def test_variable_selector_visible_labels_and_styling():
    """Verify variable selector chips always have visible labels and distinct active/inactive styling."""
    client = Client(ui.page("/test_var_selector_ux3_4_1"))
    with client:
        op = get_operation_by_type(ProblemType.DERIVATIVE)
        var_input = ui.input(value="x")
        render_adaptive_variable_selector(op, var_input)

        chips = {
            el.text: el
            for el in client.elements.values()
            if isinstance(el, ui.button) and el.text in ("x", "t", "y", "u")
        }
        # All chips must be present with non-empty text
        assert set(chips.keys()) == {"x", "t", "y", "u"}
        for name, chip in chips.items():
            assert chip.text == name
            assert chip.text.strip() != ""

        # Active chip (x) has blue styling
        assert "bg-blue-600" in chips["x"]._classes
        assert "!bg-blue-600" in chips["x"]._classes
        assert "!text-white" in chips["x"]._classes

        # Inactive chips have slate text and white background
        for v in ("t", "y", "u"):
            assert "!bg-white" in chips[v]._classes
            assert "!text-slate-700" in chips[v]._classes


def test_variable_selector_interactive_switch_and_reset():
    """Verify switching variables updates classes dynamically and reset restores default."""
    client = Client(ui.page("/test_var_switch_ux3_4_1"))
    with client:
        op = get_operation_by_type(ProblemType.INDEFINITE_INTEGRAL)
        var_input = ui.input(value="x")
        render_adaptive_variable_selector(op, var_input)

        chips = {
            el.text: el
            for el in client.elements.values()
            if isinstance(el, ui.button) and el.text in ("x", "t", "y", "u")
        }

        # Switch to 't'
        var_input.set_value("t")
        assert "!bg-blue-600" in chips["t"]._classes
        assert "!text-slate-700" in chips["x"]._classes

        # Reset to 'x'
        var_input.set_value("x")
        assert "!bg-blue-600" in chips["x"]._classes
        assert "!text-slate-700" in chips["t"]._classes


# =============================================================================
# 2. LIMIT DIRECTION & INFINITY NOTATION (Item 2)
# =============================================================================

def test_limit_notation_and_infinity_handling():
    """Verify limit direction labels use mathematical notation and infinity points are parsed."""
    solver = LimitSolver()

    # Two-sided limit at infinity
    req_inf = ProblemRequest(
        raw_input="1/x",
        target_variable="x",
        problem_type=ProblemType.LIMIT,
        parameters={"limit_point": "oo", "direction": "+-"},
    )
    res_inf = solver.solve(req_inf)
    assert res_inf.status == SolutionStatus.SUCCESS
    assert res_inf.final_result == "0"

    # Negative infinity
    req_neg_inf = ProblemRequest(
        raw_input="exp(x)",
        target_variable="x",
        problem_type=ProblemType.LIMIT,
        parameters={"limit_point": "-oo", "direction": "+-"},
    )
    res_neg_inf = solver.solve(req_neg_inf)
    assert res_neg_inf.status == SolutionStatus.SUCCESS
    assert res_neg_inf.final_result == "0"

    # One-sided right-hand limit at 0: 1/x -> +oo
    req_right = ProblemRequest(
        raw_input="1/x",
        target_variable="x",
        problem_type=ProblemType.LIMIT,
        parameters={"limit_point": "0", "direction": "+"},
    )
    res_right = solver.solve(req_right)
    assert res_right.status == SolutionStatus.SUCCESS
    assert "oo" in res_right.final_result or "\\infty" in res_right.final_latex


# =============================================================================
# 3. EQUATION FACTORIZATION PEDAGOGICAL DERIVATION (Item 3)
# =============================================================================

def test_quadratic_factorization_educational_steps():
    """Verify x^2 - 5x + 6 = 0 decomposes into Viète/ac-method, grouping, and zero-product steps."""
    solver = EquationSolver()
    req = ProblemRequest(
        raw_input="x^2 - 5*x + 6 = 0",
        target_variable="x",
        problem_type=ProblemType.SOLVE_EQUATION,
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS

    enhanced = enhance_equation_factorization_steps(res.steps, req.raw_input, req.target_variable)
    assert len(enhanced) >= 3

    # Step 1: Finding m, n
    step_find = next(s for s in enhanced if "Xác định cặp số" in s.title or "ac-method" in s.rule_name)
    assert "m + n = b = -5" in step_find.description
    assert "m = -3" in step_find.description or "m = -2" in step_find.description

    # Step 2: Grouping
    step_group = next(s for s in enhanced if "nhóm" in s.title.lower() or "nhân tử" in s.title.lower())
    assert "(x - 3)" in step_group.description or "\\left(x - 3\\right)" in step_group.description
    assert "(x - 2)" in step_group.description or "\\left(x - 2\\right)" in step_group.description

    # Step 3: Zero-product property
    step_zero = next(s for s in enhanced if "tích bằng 0" in s.title.lower() or "tích bằng 0" in s.rule_name.lower())
    assert "x = 3" in step_zero.description or "x = 2" in step_zero.description


def test_non_factorable_equation_preserves_original_steps():
    """Verify non-factorable equations or cubic equations preserve their original solver steps."""
    solver = EquationSolver()
    req = ProblemRequest(
        raw_input="x^2 + x + 1 = 0",
        target_variable="x",
        problem_type=ProblemType.SOLVE_EQUATION,
    )
    res = solver.solve(req)
    enhanced = enhance_equation_factorization_steps(res.steps, req.raw_input, req.target_variable)
    # Discriminant < 0, steps must be preserved unmodified
    assert len(enhanced) == len(res.steps)


# =============================================================================
# 4. LATEX TEXT SPACING & INTEGRATING FACTOR ODE AUDIT (Item 4)
# =============================================================================

def test_integrating_factor_domain_condition_latex_formatting():
    """Verify integrating factor domain condition does not strip Vietnamese spaces in KaTeX."""
    raw_cond = "Điều kiện thừa số tích phân: μ = x khác 0."
    key, desc, formula = format_domain_condition(raw_cond, var_name="x")

    assert desc == "Điều kiện thừa số tích phân:"
    assert "\\mu = x" in formula
    assert "\\ne 0" in formula
    assert "khác 0" not in formula  # properly transformed to \ne 0
    assert "Điềukiện" not in formula  # Vietnamese words are NOT dumped raw into KaTeX math mode


def test_integrating_factor_solver_mathematical_consistency():
    """Verify mathematical consistency of integrating factor ODE derivation:
    (3xy + y^2)dx + (x^2 + xy)dy = 0 with mu(x) = x and implicit solution x^3*y + x^2*y^2/2 = C.
    """
    solver = ODEIntegratingFactorSolver()
    req = ProblemRequest(
        raw_input="(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0",
        target_variable="x",
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS

    # Mathematical checks
    x, y, C = sp.symbols("x y C")
    phi = x**3 * y + sp.Rational(1, 2) * x**2 * y**2

    # Check dPhi/dx = mu * M = x * (3xy + y^2) = 3x^2*y + x*y^2
    dphi_dx = sp.diff(phi, x)
    assert sp.simplify(dphi_dx - (3 * x**2 * y + x * y**2)) == 0

    # Check dPhi/dy = mu * N = x * (x^2 + xy) = x^3 + x^2*y
    dphi_dy = sp.diff(phi, y)
    assert sp.simplify(dphi_dy - (x**3 + x**2 * y)) == 0

    # Verify status
    assert res.verification is not None
    assert "Kiểm chứng thành công" in res.verification.details


# =============================================================================
# 5. CAUCHY INITIAL-CONDITION CLEAR BUTTON (Item 5)
# =============================================================================

def test_cauchy_clear_button_disabled_state_and_clearing():
    """Verify Cauchy clear button distinguishes disabled/enabled states and clears input reactively."""
    client = Client(ui.page("/test_cauchy_clear_ux3_4_1"))
    with client:
        ic_value = ["y(0) = 1"]
        ic_inputs: list[Any] = []

        render_ode_mode_selector(
            order=ODEOrder.FIRST_ORDER,
            classification=ODEClassification.FIRST_ORDER_LINEAR,
            selected_mode=ODEMode.CAUCHY_IVP,
            initial_condition="y(0) = 1",
            on_mode_change=lambda _: None,
            on_ic_change=lambda val: ic_value.__setitem__(0, val),
            on_ic_input_created=lambda inp: ic_inputs.append(inp),
        )

        buttons = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "Xóa điều kiện"]
        assert len(buttons) == 1
        clear_btn = buttons[0]

        # Initial state with condition: button is enabled
        assert clear_btn.enabled is True
        assert "border-rose-300" in clear_btn._classes

        # Click clear
        for listener in list(clear_btn._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)
                break

        # Value cleared
        assert ic_value[0] == ""
        assert ic_inputs[0].value == ""
        assert clear_btn.enabled is False
        assert "border-slate-300" in clear_btn._classes


# =============================================================================
# 6. REDUNDANT ODE ORDER SELECTION REMOVED FROM VISUAL UI (Item 6)
# =============================================================================

def test_ode_workspace_visual_hierarchy_has_no_visible_order_step():
    """Verify ODE workspace presents semantic sections directly without redundant visual order cards."""
    use_case = build_application()
    client = Client(ui.page("/test_ode_visual_hierarchy"))
    with client:
        op = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)
        render_ode_workspace(op, use_case)

        # First-order guided workflow must present semantic sections directly without numbered analysis badges
        badges = [el.text for el in client.elements.values() if isinstance(el, ui.badge) and el.text]
        assert "BƯỚC 2" not in badges
        assert "BƯỚC 3" not in badges
        assert "BƯỚC 4" not in badges

        all_text = " ".join([el.text for el in client.elements.values() if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text])
        assert "NHẬP BÀI TOÁN" in all_text
        assert "PHÂN TÍCH TỰ ĐỘNG" in all_text
        assert "CƠ SỞ PHÂN LOẠI" in all_text
        assert "PHƯƠNG PHÁP ĐỀ XUẤT" in all_text


# =============================================================================
# 7. RESPONSIVE CONTAINER & MULTI-ROOT VERTICAL ALIGNMENT (Item 8)
# =============================================================================

def test_cubic_equation_multi_root_aligned_formatting():
    """Verify cubic equation solutions format multiple Cardano roots vertically in aligned environment."""
    solver = EquationSolver()
    req = ProblemRequest(
        raw_input="x^3 + 2*x^2 - 5*x + 1 = 0",
        target_variable="x",
        problem_type=ProblemType.SOLVE_EQUATION,
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS

    formatted_latex = format_final_answer_latex(
        res.final_latex,
        ProblemType.SOLVE_EQUATION,
        target_var="x",
    )

    # Must be structured in aligned environment, not one horizontal run
    assert "\\begin{aligned}" in formatted_latex
    assert "\\end{aligned}" in formatted_latex
    assert "x_{1}" in formatted_latex
    assert "x_{2}" in formatted_latex
    assert "x_{3}" in formatted_latex


def test_approximate_numerical_roots_for_cubic():
    """Verify approximate numerical roots are computed concisely for cubic equations."""
    approx = _compute_approximate_roots("x^3 + 2*x^2 - 5*x + 1 = 0", "x")
    assert approx is not None
    assert "0.2219" in approx or "1.2851" in approx or "-3.507" in approx


# =============================================================================
# 8. REMOVE OBSOLETE NONHOMOGENEOUS ODE WARNING (Item 9)
# =============================================================================

def test_nonhomogeneous_linear_ode_has_no_obsolete_warning_in_view():
    """Verify nonhomogeneous first-order linear ODE displays without obsolete future-version notice."""
    solver = ODELinearSolver()
    req = ProblemRequest(
        raw_input="y' + 1/2*y = t + 2",
        target_variable="t",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS

    clean_warns = _filter_ui_warnings(res.warnings)
    # The obsolete warning must be filtered out
    assert not any("nâng cấp toàn diện trong phiên bản tiếp theo" in w for w in clean_warns)

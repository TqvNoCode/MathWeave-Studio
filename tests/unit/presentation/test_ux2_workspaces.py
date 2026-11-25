"""Unit, presentation, and interaction tests for UX2 — Calculus & Algebra Unification.

Verifies:
1. Workspace components: Adaptive variable selector & Matrix helper panel.
2. Calculus 1D & Algebra workspaces (dynamic parameter fields, inputs, reset action).
3. Multivariable & Vector Calculus workspaces (Line, Surface, Triple integral coordinate switching, Green, Stokes, Divergence).
4. Linear Algebra workspaces (Matrix helper, syntax hints, templates, binary/system ops).
5. State isolation across operations and catalog navigation.
6. Backend ProblemRequest contract verification across all 24 non-ODE operations.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock
import pytest
from nicegui import Client, app, core, ui

from math_app.application.dtos import ProblemRequest, SolutionResponse
from math_app.domain.models import ProblemType, SolutionStatus
from math_app.main import build_application
from math_app.presentation.app import create_app
from math_app.presentation.components.operation_catalog import (
    get_operation_by_type,
)
from math_app.presentation.components.workspace.matrix_helper import (
    render_matrix_helper_panel,
)
from math_app.presentation.components.workspace.variable_selector import (
    get_variable_pool_for_operation,
    render_adaptive_variable_selector,
)


# =========================================================================
# 1. Workspace Unit Tests
# =========================================================================

def test_variable_pool_operation_mapping():
    """Verify adaptive variable pool mapping matches mathematical contexts."""
    # Partial derivative needs 3D coordinate variables
    op_partial = get_operation_by_type(ProblemType.PARTIAL_DERIVATIVE)
    assert get_variable_pool_for_operation(op_partial) == ["x", "y", "z"]

    # Solve equation prioritizes standard unknowns
    op_solve = get_operation_by_type(ProblemType.SOLVE_EQUATION)
    assert get_variable_pool_for_operation(op_solve) == ["x", "y", "t"]

    # 1D calculus uses standard single-variable pool
    for pt in (
        ProblemType.DERIVATIVE,
        ProblemType.INDEFINITE_INTEGRAL,
        ProblemType.DEFINITE_INTEGRAL,
        ProblemType.LIMIT,
        ProblemType.ARC_LENGTH,
        ProblemType.SURFACE_OF_REVOLUTION,
    ):
        op = get_operation_by_type(pt)
        assert get_variable_pool_for_operation(op) == ["x", "t", "y", "u"]


def test_adaptive_variable_selector_interaction():
    """Verify adaptive variable selector renders buttons and updates target input."""
    client = Client(ui.page("/test_adaptive_var_unit"))
    with client:
        op = get_operation_by_type(ProblemType.DERIVATIVE)
        var_input = ui.input(value="x")
        row = render_adaptive_variable_selector(op, var_input)
        assert row is not None

        # Find the button for 't'
        t_btn = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "t"][0]
        for listener in list(t_btn._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)

        assert var_input.value == "t"


def test_matrix_helper_panel_rendering_and_templates():
    """Verify matrix helper panel renders templates and updates expression input."""
    client = Client(ui.page("/test_matrix_helper_unit"))
    with client:
        # 1. Non-matrix returns None
        op_calc = get_operation_by_type(ProblemType.DERIVATIVE)
        dummy_input = ui.input(value="")
        assert render_matrix_helper_panel(op_calc, dummy_input) is None

        # 2. Unary Matrix (Determinant)
        op_det = get_operation_by_type(ProblemType.MATRIX_DETERMINANT)
        det_input = ui.input(value="")
        panel_det = render_matrix_helper_panel(op_det, det_input)
        assert panel_det is not None

        # Find template button "Đơn vị 2×2 (I₂)" and click it
        btn_i2 = [el for el in client.elements.values() if isinstance(el, ui.button) and "I₂" in el.text][0]
        for listener in list(btn_i2._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)
        assert det_input.value == "[[1, 0], [0, 1]]"

        # 3. Binary Matrix (Multiply)
        op_mul = get_operation_by_type(ProblemType.MATRIX_MULTIPLY)
        mul_input = ui.input(value="")
        panel_mul = render_matrix_helper_panel(op_mul, mul_input)
        assert panel_mul is not None

        btn_mul2 = [el for el in client.elements.values() if isinstance(el, ui.button) and "2×2 (*)" in el.text][0]
        for listener in list(btn_mul2._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)
        assert mul_input.value == "[[1, 2], [3, 4]] * [[5, 6], [7, 8]]"

        # 4. System of linear equations
        op_sys = get_operation_by_type(ProblemType.MATRIX_SOLVE_SYSTEM)
        sys_input = ui.input(value="")
        panel_sys = render_matrix_helper_panel(op_sys, sys_input)
        assert panel_sys is not None

        btn_sys2 = [el for el in client.elements.values() if isinstance(el, ui.button) and "Hệ 2 ẩn" in el.text][0]
        for listener in list(btn_sys2._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)
        assert sys_input.value == "[[2, 1], [1, -1]] = [5, 1]"


# =========================================================================
# Helper functions for Client Screen B navigation
# =========================================================================

def _setup_app_client(page_path: str) -> Client:
    create_app(build_application())
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page(page_path))
    with client:
        route.endpoint.__wrapped__()
    return client


def _navigate_to_operation(client: Client, problem_type: ProblemType) -> None:
    # Secondary multivariable integration workflows reachable via Definite Integral banner
    if problem_type in (
        ProblemType.LINE_INTEGRAL,
        ProblemType.SURFACE_INTEGRAL,
        ProblemType.TRIPLE_INTEGRAL,
    ):
        _navigate_to_operation(client, ProblemType.DEFINITE_INTEGRAL)
        label_map = {
            ProblemType.LINE_INTEGRAL: "Tích phân đường",
            ProblemType.SURFACE_INTEGRAL: "Tích phân mặt",
            ProblemType.TRIPLE_INTEGRAL: "Tích phân khối",
        }
        target_label = label_map[problem_type]
        for el in client.elements.values():
            if isinstance(el, ui.button) and el.text == target_label:
                for listener in list(el._event_listeners.values()):
                    if listener.type in ("click", None):
                        with client:
                            listener.handler(None)
                        return
        raise RuntimeError(f"Subtype button for {target_label} not found")

    for el in client.elements.values():
        for listener in list(el._event_listeners.values()):
            defaults = getattr(listener.handler, "__defaults__", ())
            if defaults:
                for d in defaults:
                    if hasattr(d, "problem_type") and d.problem_type == problem_type:
                        with client:
                            listener.handler(None)
                        return
    raise RuntimeError(f"Operation card for {problem_type} not found")


def _trigger_button_by_text(client: Client, text: str) -> bool:
    for el in client.elements.values():
        if isinstance(el, ui.button) and el.text == text:
            for listener in list(el._event_listeners.values()):
                if listener.type in ("click", None):
                    with client:
                        listener.handler(None)
                    return True
    return False


# =========================================================================
# 2. UX2.1: Calculus 1D & Algebra Workspaces
# =========================================================================

def test_ux2_1_derivative_workspace():
    """Verify Derivative workspace: order input, adaptive variable selector, reset button."""
    client = _setup_app_client("/test_ux2_1_derivative")
    _navigate_to_operation(client, ProblemType.DERIVATIVE)

    # 1. Main expression input
    expr_inputs = [el for el in client.elements.values() if isinstance(el, ui.input) and "f(x)" in el._props.get("label", "")]
    assert len(expr_inputs) == 1
    expr_input = expr_inputs[0]
    op = get_operation_by_type(ProblemType.DERIVATIVE)
    assert expr_input.value == op.default_input

    # 2. Derivative order input
    number_inputs = [el for el in client.elements.values() if isinstance(el, ui.number) and "Cấp đạo hàm" in el._props.get("label", "")]
    assert len(number_inputs) == 1
    order_input = number_inputs[0]
    assert order_input.value == 1

    # 3. Adaptive variable selector
    var_inputs = [el for el in client.elements.values() if isinstance(el, ui.input) and "Biến số" in el._props.get("label", "")]
    assert len(var_inputs) == 1
    var_input = var_inputs[0]
    assert var_input.value == "x"

    # 4. Action toolbar
    reset_btns = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "Nhập lại"]
    assert len(reset_btns) == 1

    # Modify input and reset
    expr_input.set_value("x^4")
    assert expr_input.value == "x^4"
    for listener in list(reset_btns[0]._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
    assert expr_input.value == op.default_input


def test_ux2_1_definite_integral_workspace():
    """Verify Definite Integral workspace: lower and upper bounds, subtype banner."""
    client = _setup_app_client("/test_ux2_1_def_integral")
    _navigate_to_operation(client, ProblemType.DEFINITE_INTEGRAL)

    # 1. Subtype selector banner exists
    subtype_banner_labels = [el.text for el in client.elements.values() if isinstance(el, ui.label) and "CHỌN DẠNG TÍCH PHÂN" in el.text]
    assert len(subtype_banner_labels) == 1

    # 2. Bounds inputs
    lower_inputs = [el for el in client.elements.values() if isinstance(el, ui.input) and "Cận dưới" in el._props.get("label", "")]
    upper_inputs = [el for el in client.elements.values() if isinstance(el, ui.input) and "Cận trên" in el._props.get("label", "")]
    assert len(lower_inputs) == 1
    assert len(upper_inputs) == 1
    assert lower_inputs[0].value == "0"
    assert upper_inputs[0].value == "1"


def test_ux2_1_limit_workspace():
    """Verify Limit workspace: limit point and direction controls."""
    client = _setup_app_client("/test_ux2_1_limit")
    _navigate_to_operation(client, ProblemType.LIMIT)

    pt_inputs = [el for el in client.elements.values() if isinstance(el, ui.input) and "Điểm tiến tới" in el._props.get("label", "")]
    assert len(pt_inputs) == 1
    assert pt_inputs[0].value == "0"

    dir_selects = [el for el in client.elements.values() if isinstance(el, ui.select) and "Hướng tiến tới" in el._props.get("label", "")]
    assert len(dir_selects) == 1
    assert "+- (Hai phía)" in dir_selects[0].value


def test_ux2_1_solve_equation_workspace():
    """Verify Solve Equation workspace: label, variable selector, calculator icon."""
    client = _setup_app_client("/test_ux2_1_solve_eq")
    _navigate_to_operation(client, ProblemType.SOLVE_EQUATION)

    expr_inputs = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình đại số" in el._props.get("label", "")]
    assert len(expr_inputs) == 1

    # Unknown variable selector
    labels = [el.text for el in client.elements.values() if isinstance(el, ui.label) and "Ẩn số cần tìm" in el.text]
    assert len(labels) == 1


# =========================================================================
# 3. UX2.2: Multivariable & Vector Calculus Workspaces
# =========================================================================

def test_ux2_2_line_integral_workspace():
    """Verify Line Integral workspace: mode, orientation, parameterization."""
    client = _setup_app_client("/test_ux2_2_line_int")
    _navigate_to_operation(client, ProblemType.LINE_INTEGRAL)

    selects = [el for el in client.elements.values() if isinstance(el, ui.select)]
    mode_sel = [s for s in selects if "Kiểu tích phân" in s._props.get("label", "")][0]
    orient_sel = [s for s in selects if "Định hướng" in s._props.get("label", "")][0]

    assert "Vô hướng" in mode_sel.value
    assert "Hướng thuận" in orient_sel.value

    inputs = [el for el in client.elements.values() if isinstance(el, ui.input)]
    t_min = [inp for inp in inputs if inp._props.get("label") == "t_min"][0]
    t_max = [inp for inp in inputs if inp._props.get("label") == "t_max"][0]
    assert t_min.value == "0"
    assert t_max.value == "1"


def test_ux2_2_surface_integral_dynamic_geometry_switching():
    """Verify Surface Integral switches dynamically between Graph and Parametric geometry."""
    client = _setup_app_client("/test_ux2_2_surf_int")
    _navigate_to_operation(client, ProblemType.SURFACE_INTEGRAL)

    selects = [el for el in client.elements.values() if isinstance(el, ui.select)]
    surf_type = [s for s in selects if "Hình học mặt S" in s._props.get("label", "")][0]
    assert "Mặt đồ thị" in surf_type.value

    # Graph mode has z = g(x, y) input
    inputs_graph = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình mặt" in el._props.get("label", "")]
    assert len(inputs_graph) == 1

    # Switch to Parametric mode
    with client:
        surf_type.set_value("Mặt tham số: r(u, v)")

    # Parametric mode has x(u, v), y(u, v), z(u, v)
    inputs_param = [el for el in client.elements.values() if isinstance(el, ui.input) and "x(u, v)" in el._props.get("label", "")]
    assert len(inputs_param) == 1


def test_ux2_2_triple_integral_coordinate_switching():
    """Verify Triple Integral coordinate selector switches Cartesian, Cylindrical, and Spherical bounds."""
    client = _setup_app_client("/test_ux2_2_triple_int")
    _navigate_to_operation(client, ProblemType.TRIPLE_INTEGRAL)

    selects = [el for el in client.elements.values() if isinstance(el, ui.select)]
    coord_sel = [s for s in selects if "Hệ tọa độ" in s._props.get("label", "")][0]
    assert "Descartes" in coord_sel.value

    # Initial Cartesian inputs: x_min, y_min, z_min
    inputs_cart = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "x_min"]
    assert len(inputs_cart) == 1

    # Switch to Cylindrical
    with client:
        coord_sel.set_value("Tọa độ trụ (r, θ, z)")

    inputs_cyl = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "r_min"]
    assert len(inputs_cyl) == 1

    # Switch to Spherical
    with client:
        coord_sel.set_value("Tọa độ cầu (ρ, φ, θ)")

    inputs_sph = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "ρ_min"]
    assert len(inputs_sph) == 1


def test_ux2_2_vector_theorems_workspaces():
    """Verify Green's, Stokes', and Divergence theorem workspaces."""
    # 1. Green's Theorem
    client_green = _setup_app_client("/test_ux2_2_green")
    _navigate_to_operation(client_green, ProblemType.GREENS_THEOREM)
    green_forms = [el for el in client_green.elements.values() if isinstance(el, ui.select) and "Dạng định lý" in el._props.get("label", "")]
    assert len(green_forms) == 1
    assert "Lưu thông" in green_forms[0].value

    # 2. Stokes' Theorem
    client_stokes = _setup_app_client("/test_ux2_2_stokes")
    _navigate_to_operation(client_stokes, ProblemType.STOKES_THEOREM)
    stokes_surfs = [el for el in client_stokes.elements.values() if isinstance(el, ui.input) and "Mặt cong S" in el._props.get("label", "")]
    assert len(stokes_surfs) == 1

    # 3. Divergence Theorem
    client_div = _setup_app_client("/test_ux2_2_divergence")
    _navigate_to_operation(client_div, ProblemType.DIVERGENCE_THEOREM)
    z_max = [el for el in client_div.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "z_max"]
    assert len(z_max) == 1


# =========================================================================
# 4. UX2.3: Linear Algebra Workspaces
# =========================================================================

def test_ux2_3_matrix_workspace_and_button_label():
    """Verify matrix operations display matrix helper panel and 'GIẢI PHÉP TOÁN MA TRẬN' button."""
    client = _setup_app_client("/test_ux2_3_matrix_det")
    _navigate_to_operation(client, ProblemType.MATRIX_DETERMINANT)

    # Matrix guidance label exists
    labels = [el.text for el in client.elements.values() if isinstance(el, ui.label) and "HƯỚNG DẪN NHẬP DỮ LIỆU MA TRẬN" in el.text]
    assert len(labels) == 1

    # Solve button has matrix label
    btns = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "GIẢI PHÉP TOÁN MA TRẬN"]
    assert len(btns) == 1


# =========================================================================
# 5. State Isolation & Catalog Navigation
# =========================================================================

def test_ux2_state_isolation_and_back_navigation():
    """Verify navigating between operations and back to catalog preserves clean state without leaks."""
    client = _setup_app_client("/test_ux2_isolation")

    # 1. Start at Catalog (Screen A)
    cards_a = [el for el in client.elements.values() if isinstance(el, ui.card)]
    assert len(cards_a) >= 23

    # 2. Go to Derivative (Screen B)
    _navigate_to_operation(client, ProblemType.DERIVATIVE)
    assert any(isinstance(el, ui.number) for el in client.elements.values())

    # 3. Back to Catalog
    back_btn = [
        el for el in client.elements.values()
        if isinstance(el, ui.button) and (el.text == "Chọn dạng toán khác" or "arrow_back" in el._props.get("icon", ""))
    ][0]
    for listener in list(back_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)

    # 4. Now on Screen A again
    labels_catalog = [el.text for el in client.elements.values() if isinstance(el, ui.label) and "Chọn dạng toán cần giải quyết" in el.text]
    assert len(labels_catalog) >= 1

    # 5. Go to Matrix Determinant
    _navigate_to_operation(client, ProblemType.MATRIX_DETERMINANT)
    # Ensure no derivative order input leaked into matrix workspace
    number_inputs = [el for el in client.elements.values() if isinstance(el, ui.number)]
    assert len(number_inputs) == 0


# =========================================================================
# 6. Absolute Functionality Preservation across 24 Non-ODE Operations
# =========================================================================

@pytest.mark.parametrize(
    "op_type",
    [
        ProblemType.DERIVATIVE,
        ProblemType.PARTIAL_DERIVATIVE,
        ProblemType.INDEFINITE_INTEGRAL,
        ProblemType.DEFINITE_INTEGRAL,
        ProblemType.LINE_INTEGRAL,
        ProblemType.SURFACE_INTEGRAL,
        ProblemType.TRIPLE_INTEGRAL,
        ProblemType.LIMIT,
        ProblemType.ARC_LENGTH,
        ProblemType.SURFACE_AREA,
        ProblemType.SURFACE_OF_REVOLUTION,
        ProblemType.SOLVE_EQUATION,
        ProblemType.GREENS_THEOREM,
        ProblemType.STOKES_THEOREM,
        ProblemType.DIVERGENCE_THEOREM,
        ProblemType.MATRIX_DETERMINANT,
        ProblemType.MATRIX_INVERSE,
        ProblemType.MATRIX_REF,
        ProblemType.MATRIX_RREF,
        ProblemType.MATRIX_TRANSPOSE,
        ProblemType.MATRIX_RANK,
        ProblemType.MATRIX_ADD_SUB,
        ProblemType.MATRIX_MULTIPLY,
        ProblemType.MATRIX_SOLVE_SYSTEM,
    ],
)
def test_all_24_non_ode_operations_solve_successfully(op_type: ProblemType):
    """Verify backend execution for all 24 non-ODE operations in the UX2 scope."""
    use_case = build_application()
    op = get_operation_by_type(op_type)

    params: dict[str, Any] = {}
    if "order" in op.extra_fields:
        params["order"] = 1
    if "lower_bound" in op.extra_fields:
        params["lower_bound"] = "0"
        params["upper_bound"] = "1"
    if "limit_point" in op.extra_fields:
        params["limit_point"] = "0"
        params["direction"] = "+-"
    if "axis" in op.extra_fields:
        params["axis"] = "Ox"
    if op_type == ProblemType.LINE_INTEGRAL:
        params["mode"] = "scalar"
        params["orientation"] = "forward"
        params["param_var"] = "t"
        params["t_min"] = "0"
        params["t_max"] = "1"
        params["param_x"] = "3*t"
        params["param_y"] = "4*t"
        params["param_z"] = "0"
    elif op_type == ProblemType.SURFACE_INTEGRAL:
        params["mode"] = "scalar"
        params["orientation"] = "upward"
        params["surface_type"] = "graph"
        params["surface_expr"] = "1 - x - y"
        params["u_var"] = "x"
        params["u_min"] = "0"
        params["u_max"] = "1"
        params["v_var"] = "y"
        params["v_min"] = "0"
        params["v_max"] = "1"
    elif op_type == ProblemType.TRIPLE_INTEGRAL:
        params["coord_system"] = "cartesian"
        params["x_min"] = "0"
        params["x_max"] = "1"
        params["y_min"] = "0"
        params["y_max"] = "2"
        params["z_min"] = "0"
        params["z_max"] = "3"
    elif op_type == ProblemType.SURFACE_AREA:
        params["u_min"] = "0"
        params["u_max"] = "1"
        params["v_min"] = "0"
        params["v_max"] = "1"
    elif op_type == ProblemType.GREENS_THEOREM:
        params["form"] = "circulation"
        params["x_min"] = "0"
        params["x_max"] = "1"
        params["y_min"] = "0"
        params["y_max"] = "1"
    elif op_type == ProblemType.STOKES_THEOREM:
        params["surface_expr"] = "0"
        params["x_min"] = "0"
        params["x_max"] = "1"
        params["y_min"] = "0"
        params["y_max"] = "1"
    elif op_type == ProblemType.DIVERGENCE_THEOREM:
        params["x_min"] = "0"
        params["x_max"] = "1"
        params["y_min"] = "0"
        params["y_max"] = "1"
        params["z_min"] = "0"
        params["z_max"] = "1"

    req = ProblemRequest(
        raw_input=op.default_input,
        problem_type=op.problem_type,
        target_variable=op.target_var,
        parameters=params,
    )

    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS, (
        f"Operation {op.title} ({op_type}) failed with status {resp.status}: {resp.warnings}"
    )
    assert resp.final_result.strip()
    assert resp.final_latex.strip()


# =========================================================================
# 7. UX2.4 Corrections: Reactive Variable Selector
# =========================================================================

def test_ux2_4_reactive_variable_selector_interactive_and_programmatic():
    """Verify variable selector chip styling reacts dynamically to clicks and programmatic updates."""
    client = Client(ui.page("/test_ux2_4_var_reactive"))
    with client:
        op = get_operation_by_type(ProblemType.DERIVATIVE)
        var_input = ui.input(value="x")
        render_adaptive_variable_selector(op, var_input)

        # Get the chips
        chips = {
            el.text: el
            for el in client.elements.values()
            if isinstance(el, ui.button) and el.text in ("x", "t", "y", "u")
        }
        assert len(chips) == 4

        # 1. Initial state: 'x' is active (has bg-blue-600), others are inactive
        assert "bg-blue-600" in chips["x"]._classes
        assert "bg-blue-600" not in chips["t"]._classes
        assert "bg-blue-600" not in chips["y"]._classes

        # 2. Click 't'
        for listener in list(chips["t"]._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)
        assert var_input.value == "t"
        assert "bg-blue-600" not in chips["x"]._classes
        assert "bg-blue-600" in chips["t"]._classes
        assert "bg-blue-600" not in chips["y"]._classes

        # 3. Click 'y'
        for listener in list(chips["y"]._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)
        assert var_input.value == "y"
        assert "bg-blue-600" not in chips["x"]._classes
        assert "bg-blue-600" not in chips["t"]._classes
        assert "bg-blue-600" in chips["y"]._classes

        # 4. Programmatically update var_input
        var_input.set_value("u")
        assert "bg-blue-600" in chips["u"]._classes
        assert "bg-blue-600" not in chips["y"]._classes

        # 5. Programmatically reset to 'x'
        var_input.set_value("x")
        assert "bg-blue-600" in chips["x"]._classes
        assert "bg-blue-600" not in chips["u"]._classes


# =========================================================================
# 8. UX2.4 Corrections: Complete Reset Action
# =========================================================================

def test_ux2_4_complete_reset_action_across_operations():
    """Verify Reset restores expression, number inputs, bounds, dynamic modes, and clears results."""
    # Test on Derivative
    client_der = _setup_app_client("/test_ux2_4_reset_der")
    _navigate_to_operation(client_der, ProblemType.DERIVATIVE)

    expr_in = [el for el in client_der.elements.values() if isinstance(el, ui.input) and "f(x)" in el._props.get("label", "")][0]
    order_in = [el for el in client_der.elements.values() if isinstance(el, ui.number) and "Cấp đạo hàm" in el._props.get("label", "")][0]
    var_in = [el for el in client_der.elements.values() if isinstance(el, ui.input) and "Biến số" in el._props.get("label", "")][0]
    reset_btn = [el for el in client_der.elements.values() if isinstance(el, ui.button) and el.text == "Nhập lại"][0]

    # Mutate values
    expr_in.set_value("x^5 + 3*x")
    order_in.set_value(4)
    var_in.set_value("t")

    # Trigger reset
    for listener in list(reset_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client_der:
                listener.handler(None)

    assert expr_in.value == get_operation_by_type(ProblemType.DERIVATIVE).default_input
    assert order_in.value == 1
    assert var_in.value == "x"

    # Test on Definite Integral bounds
    client_int = _setup_app_client("/test_ux2_4_reset_int")
    _navigate_to_operation(client_int, ProblemType.DEFINITE_INTEGRAL)
    low_in = [el for el in client_int.elements.values() if isinstance(el, ui.input) and "Cận dưới" in el._props.get("label", "")][0]
    up_in = [el for el in client_int.elements.values() if isinstance(el, ui.input) and "Cận trên" in el._props.get("label", "")][0]
    reset_int = [el for el in client_int.elements.values() if isinstance(el, ui.button) and el.text == "Nhập lại"][0]

    low_in.set_value("5")
    up_in.set_value("10")
    for listener in list(reset_int._event_listeners.values()):
        if listener.type in ("click", None):
            with client_int:
                listener.handler(None)

    assert low_in.value == "0"
    assert up_in.value == "1"

    # Test on Surface Integral (parametric -> reset to graph)
    client_surf = _setup_app_client("/test_ux2_4_reset_surf")
    _navigate_to_operation(client_surf, ProblemType.SURFACE_INTEGRAL)
    surf_type = [el for el in client_surf.elements.values() if isinstance(el, ui.select) and "Hình học mặt S" in el._props.get("label", "")][0]
    with client_surf:
        surf_type.set_value("Mặt tham số: r(u, v)")

    assert any(isinstance(el, ui.input) and "x(u, v)" in el._props.get("label", "") for el in client_surf.elements.values())

    reset_surf = [el for el in client_surf.elements.values() if isinstance(el, ui.button) and el.text == "Nhập lại"][0]
    for listener in list(reset_surf._event_listeners.values()):
        if listener.type in ("click", None):
            with client_surf:
                listener.handler(None)

    assert "Mặt đồ thị" in surf_type.value
    assert any(isinstance(el, ui.input) and "Phương trình mặt" in el._props.get("label", "") for el in client_surf.elements.values())
    assert not any(isinstance(el, ui.input) and "x(u, v)" in el._props.get("label", "") for el in client_surf.elements.values())


# =========================================================================
# 9. UX2.4 Corrections: Dynamic Parameter State Isolation & UI Submissions
# =========================================================================

@pytest.mark.anyio
async def test_ux2_4_surface_integral_geometry_isolation_and_submission():
    """Verify switching Surface Integral geometry cleanly isolates parameters without leakage."""
    core.loop = asyncio.get_running_loop()
    captured_requests: list[ProblemRequest] = []

    def _record_exec(req: ProblemRequest, *args: Any, **kwargs: Any) -> SolutionResponse:
        captured_requests.append(req)
        return SolutionResponse(
            status=SolutionStatus.SUCCESS,
            raw_input=req.raw_input,
            canonical_input=req.raw_input,
            final_result="42",
            final_latex="42",
            steps=(),
        )

    mock_use_case = MagicMock()
    mock_use_case.execute.side_effect = _record_exec

    create_app(mock_use_case)
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page("/test_ux2_4_surf_isolation"))
    with client:
        route.endpoint.__wrapped__()

    _navigate_to_operation(client, ProblemType.SURFACE_INTEGRAL)
    surf_type = [el for el in client.elements.values() if isinstance(el, ui.select) and "Hình học mặt S" in el._props.get("label", "")][0]
    solve_btn = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "GIẢI PHƯƠNG TRÌNH"][0]

    # 1. Submit initial Graph mode
    captured_requests.clear()
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
    await asyncio.sleep(0.08)
    assert len(captured_requests) == 1
    req1 = captured_requests[0]
    assert req1.parameters["surface_type"] == "explicit"
    assert "surface_expr" in req1.parameters
    assert "param_x" not in req1.parameters
    assert "param_y" not in req1.parameters
    assert "param_z" not in req1.parameters

    # 2. Switch to Parametric mode and submit
    with client:
        surf_type.set_value("Mặt tham số: r(u, v)")

    captured_requests.clear()
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
    await asyncio.sleep(0.08)
    assert len(captured_requests) == 1
    req2 = captured_requests[0]
    assert req2.parameters["surface_type"] == "parametric"
    assert "surface_expr" not in req2.parameters
    assert "param_x" in req2.parameters
    assert "param_y" in req2.parameters
    assert "param_z" in req2.parameters

    # 3. Switch back to Graph mode and submit
    with client:
        surf_type.set_value("Mặt đồ thị: z = g(x, y)")

    captured_requests.clear()
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
    await asyncio.sleep(0.08)
    assert len(captured_requests) == 1
    req3 = captured_requests[0]
    assert req3.parameters["surface_type"] == "explicit"
    assert "surface_expr" in req3.parameters
    assert "param_x" not in req3.parameters
    assert "param_y" not in req3.parameters
    assert "param_z" not in req3.parameters


@pytest.mark.anyio
async def test_ux2_4_triple_integral_coordinate_isolation_and_submission():
    """Verify switching Triple Integral coordinates cleanly isolates bounds parameters."""
    core.loop = asyncio.get_running_loop()
    captured_requests: list[ProblemRequest] = []

    def _record_exec(req: ProblemRequest, *args: Any, **kwargs: Any) -> SolutionResponse:
        captured_requests.append(req)
        return SolutionResponse(
            status=SolutionStatus.SUCCESS,
            raw_input=req.raw_input,
            canonical_input=req.raw_input,
            final_result="42",
            final_latex="42",
            steps=(),
        )

    mock_use_case = MagicMock()
    mock_use_case.execute.side_effect = _record_exec

    create_app(mock_use_case)
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page("/test_ux2_4_triple_isolation"))
    with client:
        route.endpoint.__wrapped__()

    _navigate_to_operation(client, ProblemType.TRIPLE_INTEGRAL)
    coord_sel = [el for el in client.elements.values() if isinstance(el, ui.select) and "Hệ tọa độ" in el._props.get("label", "")][0]
    solve_btn = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "GIẢI PHƯƠNG TRÌNH"][0]

    # 1. Cartesian mode
    captured_requests.clear()
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
    await asyncio.sleep(0.08)
    assert len(captured_requests) == 1
    req_cart = captured_requests[0]
    assert req_cart.parameters["coord_system"] == "cartesian"
    assert "x_min" in req_cart.parameters and "x_max" in req_cart.parameters
    assert "y_min" in req_cart.parameters and "y_max" in req_cart.parameters
    assert "z_min" in req_cart.parameters and "z_max" in req_cart.parameters
    assert "th_min" not in req_cart.parameters
    assert "r_min" not in req_cart.parameters
    assert "phi_min" not in req_cart.parameters

    # 2. Switch Cartesian -> Cylindrical
    with client:
        coord_sel.set_value("Tọa độ trụ (r, θ, z)")

    captured_requests.clear()
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
    await asyncio.sleep(0.08)
    assert len(captured_requests) == 1
    req_cyl = captured_requests[0]
    assert req_cyl.parameters["coord_system"] == "cylindrical"
    assert "th_min" in req_cyl.parameters and "th_max" in req_cyl.parameters
    assert "r_min" in req_cyl.parameters and "r_max" in req_cyl.parameters
    assert "z_min" in req_cyl.parameters and "z_max" in req_cyl.parameters
    assert "x_min" not in req_cyl.parameters
    assert "y_min" not in req_cyl.parameters
    assert "phi_min" not in req_cyl.parameters
    assert "rho_min" not in req_cyl.parameters

    # 3. Switch Cylindrical -> Spherical
    with client:
        coord_sel.set_value("Tọa độ cầu (ρ, φ, θ)")

    captured_requests.clear()
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
    await asyncio.sleep(0.08)
    assert len(captured_requests) == 1
    req_sph = captured_requests[0]
    assert req_sph.parameters["coord_system"] == "spherical"
    assert "th_min" in req_sph.parameters and "th_max" in req_sph.parameters
    assert "phi_min" in req_sph.parameters and "phi_max" in req_sph.parameters
    assert "rho_min" in req_sph.parameters and "rho_max" in req_sph.parameters
    assert "x_min" not in req_sph.parameters
    assert "y_min" not in req_sph.parameters
    assert "z_min" not in req_sph.parameters
    assert "r_min" not in req_sph.parameters

    # 4. Switch Spherical -> Cartesian
    with client:
        coord_sel.set_value("Tọa độ Descartes (x, y, z)")

    captured_requests.clear()
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
    await asyncio.sleep(0.08)
    assert len(captured_requests) == 1
    req_back = captured_requests[0]
    assert req_back.parameters["coord_system"] == "cartesian"
    assert "x_min" in req_back.parameters and "z_max" in req_back.parameters
    assert "th_min" not in req_back.parameters
    assert "phi_min" not in req_back.parameters
    assert "rho_min" not in req_back.parameters


@pytest.mark.anyio
@pytest.mark.parametrize(
    "op_type,expected_check",
    [
        (ProblemType.DERIVATIVE, lambda r: r.problem_type == ProblemType.DERIVATIVE and r.target_variable == "x" and r.parameters.get("order") == 1),
        (ProblemType.DEFINITE_INTEGRAL, lambda r: r.problem_type == ProblemType.DEFINITE_INTEGRAL and r.parameters.get("lower_bound") == "0" and r.parameters.get("upper_bound") == "1"),
        (ProblemType.LIMIT, lambda r: r.problem_type == ProblemType.LIMIT and r.parameters.get("limit_point") == "0" and r.parameters.get("direction") == "+-"),
        (ProblemType.LINE_INTEGRAL, lambda r: r.problem_type == ProblemType.LINE_INTEGRAL and r.parameters.get("mode") == "scalar" and r.parameters.get("orientation") == "forward"),
        (ProblemType.GREENS_THEOREM, lambda r: r.problem_type == ProblemType.GREENS_THEOREM and r.parameters.get("form") == "circulation" and r.parameters.get("x_min") == "0"),
        (ProblemType.STOKES_THEOREM, lambda r: r.problem_type == ProblemType.STOKES_THEOREM and r.parameters.get("surface_expr") == "0" and r.parameters.get("x_min") == "0"),
        (ProblemType.DIVERGENCE_THEOREM, lambda r: r.problem_type == ProblemType.DIVERGENCE_THEOREM and r.parameters.get("x_min") == "0" and r.parameters.get("z_max") == "1"),
        (ProblemType.MATRIX_DETERMINANT, lambda r: r.problem_type == ProblemType.MATRIX_DETERMINANT and r.raw_input == "[[1, 2], [3, 4]]"),
        (ProblemType.MATRIX_ADD_SUB, lambda r: r.problem_type == ProblemType.MATRIX_ADD_SUB and "+" in r.raw_input),
        (ProblemType.MATRIX_MULTIPLY, lambda r: r.problem_type == ProblemType.MATRIX_MULTIPLY and "*" in r.raw_input),
        (ProblemType.MATRIX_SOLVE_SYSTEM, lambda r: r.problem_type == ProblemType.MATRIX_SOLVE_SYSTEM and "=" in r.raw_input),
    ],
)
async def test_ux2_4_real_ui_submission_problem_request_capture(op_type: ProblemType, expected_check):
    """Verify that clicking solve button generates exact ProblemRequest contracts for representative operations."""
    core.loop = asyncio.get_running_loop()
    captured_requests: list[ProblemRequest] = []

    def _record_exec(req: ProblemRequest, *args: Any, **kwargs: Any) -> SolutionResponse:
        captured_requests.append(req)
        return SolutionResponse(
            status=SolutionStatus.SUCCESS,
            raw_input=req.raw_input,
            canonical_input=req.raw_input,
            final_result="ok",
            final_latex="ok",
            steps=(),
        )

    mock_use_case = MagicMock()
    mock_use_case.execute.side_effect = _record_exec

    create_app(mock_use_case)
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page(f"/test_ux2_4_submit_{op_type.value}"))
    with client:
        route.endpoint.__wrapped__()

    _navigate_to_operation(client, op_type)
    solve_btn = [
        el for el in client.elements.values()
        if isinstance(el, ui.button) and el.text in ("GIẢI PHƯƠNG TRÌNH", "GIẢI PHÉP TOÁN MA TRẬN")
    ][0]

    captured_requests.clear()
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)

    await asyncio.sleep(0.08)
    assert len(captured_requests) == 1, f"Expected exactly 1 request for {op_type}, got {len(captured_requests)}"
    assert expected_check(captured_requests[0])


@pytest.mark.anyio
async def test_ux2_4_1_surface_integral_reset_scenarios_graph_and_parametric():
    """Verify Surface Integral Reset restores defaults and purges stale params in both Graph and Parametric scenarios."""
    core.loop = asyncio.get_running_loop()
    captured_requests: list[ProblemRequest] = []

    def _record_exec(req: ProblemRequest, *args: Any, **kwargs: Any) -> SolutionResponse:
        captured_requests.append(req)
        return SolutionResponse(
            status=SolutionStatus.SUCCESS,
            raw_input=req.raw_input,
            canonical_input=req.raw_input,
            final_result="42",
            final_latex="42",
            steps=(),
        )

    mock_use_case = MagicMock()
    mock_use_case.execute.side_effect = _record_exec

    create_app(mock_use_case)
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page("/test_ux2_4_1_surf_reset"))
    with client:
        route.endpoint.__wrapped__()

    _navigate_to_operation(client, ProblemType.SURFACE_INTEGRAL)

    # Common workspace controls
    reset_btn = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "Nhập lại"][0]
    solve_btn = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "GIẢI PHƯƠNG TRÌNH"][0]
    surf_type = [el for el in client.elements.values() if isinstance(el, ui.select) and "Hình học mặt S" in el._props.get("label", "")][0]

    # =========================================================================
    # Scenario A: Reset from Graph mode
    # =========================================================================
    u_min_in = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "x_min"][0]
    u_max_in = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "x_max"][0]
    v_min_in = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "y_min"][0]
    v_max_in = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "y_max"][0]
    surf_expr_in = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình mặt" in el._props.get("label", "")][0]

    with client:
        u_min_in.set_value("5")
        u_max_in.set_value("10")
        v_min_in.set_value("3")
        v_max_in.set_value("8")
        surf_expr_in.set_value("2*x + 3*y")

    # Click Reset
    for listener in list(reset_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
    await asyncio.sleep(0.05)

    # Verify elements re-created or reset to exact defaults
    surf_expr_post = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình mặt" in el._props.get("label", "")][0]
    u_min_post = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "x_min"][0]
    u_max_post = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "x_max"][0]
    v_min_post = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "y_min"][0]
    v_max_post = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "y_max"][0]

    assert "Mặt đồ thị" in surf_type.value
    assert surf_expr_post.value == "1 - x - y"
    assert u_min_post.value == "0"
    assert u_max_post.value == "1"
    assert v_min_post.value == "0"
    assert v_max_post.value == "1"
    assert not any(isinstance(el, ui.input) and "x(u, v)" in el._props.get("label", "") for el in client.elements.values())

    # Submit and verify captured ProblemRequest for Scenario A
    captured_requests.clear()
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
    await asyncio.sleep(0.08)
    assert len(captured_requests) == 1
    req_a = captured_requests[0]
    assert req_a.parameters["surface_type"] == "explicit"
    assert req_a.parameters["surface_expr"] == "1 - x - y"
    assert req_a.parameters["u_min"] == "0"
    assert req_a.parameters["u_max"] == "1"
    assert req_a.parameters["v_min"] == "0"
    assert req_a.parameters["v_max"] == "1"
    assert "param_x" not in req_a.parameters
    assert "param_y" not in req_a.parameters
    assert "param_z" not in req_a.parameters

    # =========================================================================
    # Scenario B: Reset from Parametric mode
    # =========================================================================
    with client:
        surf_type.set_value("Mặt tham số: r(u, v)")
    await asyncio.sleep(0.05)

    px_in = [el for el in client.elements.values() if isinstance(el, ui.input) and "x(u, v)" in el._props.get("label", "")][0]
    py_in = [el for el in client.elements.values() if isinstance(el, ui.input) and "y(u, v)" in el._props.get("label", "")][0]
    pz_in = [el for el in client.elements.values() if isinstance(el, ui.input) and "z(u, v)" in el._props.get("label", "")][0]
    pu_min = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "u_min"][0]
    pu_max = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "u_max"][0]
    pv_min = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "v_min"][0]
    pv_max = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "v_max"][0]

    with client:
        px_in.set_value("2*u")
        py_in.set_value("3*v")
        pz_in.set_value("u*v")
        pu_min.set_value("5")
        pu_max.set_value("10")
        pv_min.set_value("3")
        pv_max.set_value("8")

    # Click Reset
    for listener in list(reset_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
    await asyncio.sleep(0.05)

    # Verify Graph mode restored
    assert "Mặt đồ thị" in surf_type.value
    surf_expr_b = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình mặt" in el._props.get("label", "")][0]
    u_min_b = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "x_min"][0]
    u_max_b = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "x_max"][0]
    v_min_b = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "y_min"][0]
    v_max_b = [el for el in client.elements.values() if isinstance(el, ui.input) and el._props.get("label") == "y_max"][0]

    assert surf_expr_b.value == "1 - x - y"
    assert u_min_b.value == "0"
    assert u_max_b.value == "1"
    assert v_min_b.value == "0"
    assert v_max_b.value == "1"
    assert not any(isinstance(el, ui.input) and "x(u, v)" in el._props.get("label", "") for el in client.elements.values())

    # Submit and verify ProblemRequest for Scenario B
    captured_requests.clear()
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
    await asyncio.sleep(0.08)

    assert len(captured_requests) == 1
    req_b = captured_requests[0]
    assert req_b.parameters["surface_type"] == "explicit"
    assert req_b.parameters["surface_expr"] == "1 - x - y"
    assert req_b.parameters["u_min"] == "0"
    assert req_b.parameters["u_max"] == "1"
    assert req_b.parameters["v_min"] == "0"
    assert req_b.parameters["v_max"] == "1"
    assert "param_x" not in req_b.parameters
    assert "param_y" not in req_b.parameters
    assert "param_z" not in req_b.parameters


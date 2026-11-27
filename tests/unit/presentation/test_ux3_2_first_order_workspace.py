"""Comprehensive unit and integration test suite for UX3.2:
First-Order ODE Workspace Refactoring & Integration.

Verifies:
Category A: State and Request Contracts across all 5 First-Order classifications:
            - Correct operation mapping, default equations, target variables.
            - General mode zero parameter leakage and inline IC detection.
            - Cauchy mode dedicated, inline, and conflicting IC validation.
            - Draft preservation across General <-> Cauchy mode switches.
            - Non-ODE operation rejection (F2).
Category B: Component Rendering and Progressive Disclosure:
            - Dynamic header identity (F3) matching active classification.
            - 5 first-order classification selector buttons and active states.
            - Contextual Cauchy initial condition inputs and placeholders.
            - Contextual pedagogical guidance notices for each first-order type.
            - Adaptive variable selector chips.
Category C: Full Workspace Integration and Solver Dispatch:
            - Simulated end-to-end user actions (preset chip, reset, solve).
            - Verification of exact ProblemRequest payload reaching use case.
Category D: Screen B Navigation and Order Delegation:
            - Routing of all 5 First-Order ODE operations to render_ode_workspace.
            - Delegation of Step 1 Cấp 2 selection to legacy Second-Order route (F4).
            - Return navigation from Second-Order toolbar to First-Order route.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock
import pytest
from nicegui import Client, app, core, ui

from math_app.application.dtos import (
    ProblemRequest,
    SolutionResponse,
    VerificationResult,
)
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.main import build_application
from math_app.presentation.app import create_app
from math_app.presentation.components.operation_catalog import (
    get_operation_by_type,
)
from math_app.presentation.components.workspace.ode import (
    DEFAULT_CONFIGS,
    ODEClassification,
    ODEMode,
    ODEOrder,
    ODEState,
    render_ode_workspace,
)

FIRST_ORDER_TYPES = [
    ProblemType.ODE_FIRST_ORDER_LINEAR,
    ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
    ProblemType.ODE_SEPARABLE,
    ProblemType.ODE_EXACT,
    ProblemType.ODE_INTEGRATING_FACTOR,
]


# =============================================================================
# CATEGORY A: State & Request Contracts
# =============================================================================

def test_ux3_2_first_order_all_classifications_mapping_and_defaults():
    """Verify state initialization, default equations, and target variables for all 5 first-order types."""
    expected_vars = {
        ProblemType.ODE_FIRST_ORDER_LINEAR: "t",
        ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS: "x",
        ProblemType.ODE_SEPARABLE: "t",
        ProblemType.ODE_EXACT: "x",
        ProblemType.ODE_INTEGRATING_FACTOR: "x",
    }

    for pt in FIRST_ORDER_TYPES:
        op = get_operation_by_type(pt)
        assert op is not None, f"Operation for {pt} must exist in catalog"
        state = ODEState.from_operation(op)

        assert state.order == ODEOrder.FIRST_ORDER
        assert state.mode == ODEMode.GENERAL
        assert state.target_var == expected_vars[pt]
        assert len(state.equation) > 0
        assert state.initial_condition == ""
        assert state.initial_condition_draft == ""

        # Verify ProblemRequest in General mode
        req = state.build_problem_request()
        assert req.problem_type == pt
        assert req.target_variable == expected_vars[pt]
        assert "initial_condition" not in req.parameters
        assert len(req.parameters) == 0


def test_ux3_2_first_order_cauchy_ivp_mode_and_draft_preservation():
    """Verify Cauchy IVP mode, parameter inclusion, draft preservation, and zero parameter leakage."""
    for pt in FIRST_ORDER_TYPES:
        op = get_operation_by_type(pt)
        state = ODEState.from_operation(op)

        # 1. Provide dedicated initial condition
        state_cauchy = state.with_initial_condition("y(0) = 5")
        assert state_cauchy.mode == ODEMode.CAUCHY_IVP
        assert state_cauchy.is_cauchy is True
        assert state_cauchy.initial_condition == "y(0) = 5"
        assert state_cauchy.initial_condition_draft == "y(0) = 5"

        req_cauchy = state_cauchy.build_problem_request()
        assert req_cauchy.problem_type == pt
        assert req_cauchy.parameters.get("initial_condition") == "y(0) = 5"

        # 2. Switch back to GENERAL mode
        state_gen = state_cauchy.with_mode(ODEMode.GENERAL)
        assert state_gen.mode == ODEMode.GENERAL
        assert state_gen.is_cauchy is False
        assert state_gen.initial_condition == ""
        assert state_gen.initial_condition_draft == "y(0) = 5"  # Draft retained!

        req_gen = state_gen.build_problem_request()
        assert "initial_condition" not in req_gen.parameters, "Zero parameter leakage violation!"
        assert len(req_gen.parameters) == 0

        # 3. Switch back to CAUCHY_IVP mode
        state_restored = state_gen.with_mode(ODEMode.CAUCHY_IVP)
        assert state_restored.mode == ODEMode.CAUCHY_IVP
        assert state_restored.initial_condition == "y(0) = 5"

        # 4. Reset completely clears the draft
        state_reset = state_restored.reset()
        assert state_reset.mode == ODEMode.GENERAL
        assert state_reset.initial_condition == ""
        assert state_reset.initial_condition_draft == ""


def test_ux3_2_first_order_cauchy_missing_ic_rejection():
    """Verify InvalidInputError is raised if Cauchy IVP mode has neither dedicated nor inline IC."""
    for pt in FIRST_ORDER_TYPES:
        op = get_operation_by_type(pt)
        state = ODEState.from_operation(op).with_mode(ODEMode.CAUCHY_IVP)
        # Dedicated IC is empty, equation has no inline IC
        with pytest.raises(InvalidInputError, match="y\\(t0\\) = y0"):
            state.build_problem_request()


def test_ux3_2_first_order_general_mode_inline_ic_rejection():
    """Verify InvalidInputError is raised in General mode if equation contains inline IC."""
    op = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)
    state = ODEState.from_operation(op).with_equation("y' + y = 2, y(0) = 1")
    assert state.mode == ODEMode.GENERAL

    with pytest.raises(InvalidInputError, match="Tìm nghiệm tổng quát"):
        state.build_problem_request()


def test_ux3_2_first_order_cauchy_inline_and_dedicated_ic_conflict():
    """Verify conflict detection when inline and dedicated ICs differ."""
    op = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)
    state = (
        ODEState.from_operation(op)
        .with_mode(ODEMode.CAUCHY_IVP)
        .with_equation("y' + y = 2, y(0) = 1")
        .with_initial_condition("y(0) = 5")
    )

    with pytest.raises(InvalidInputError, match="xung đột điều kiện ban đầu"):
        state.build_problem_request()


def test_ux3_2_first_order_cauchy_inline_and_dedicated_ic_matching():
    """Verify matching inline and dedicated ICs are accepted without error."""
    op = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)
    state = (
        ODEState.from_operation(op)
        .with_mode(ODEMode.CAUCHY_IVP)
        .with_equation("y' + y = 2, y(0) = 1")
        .with_initial_condition("y(0) = 1")
    )

    req = state.build_problem_request()
    assert req.raw_input == "y' + y = 2"
    assert req.parameters["initial_condition"] == "y(0) = 1"


def test_ux3_2_reject_non_ode_operation():
    """Verify F2: Non-ODE operations are rejected with ValueError."""
    for non_ode_pt in (
        ProblemType.DERIVATIVE,
        ProblemType.DEFINITE_INTEGRAL,
        ProblemType.MATRIX_MULTIPLY,
        ProblemType.LIMIT,
    ):
        op = get_operation_by_type(non_ode_pt)
        with pytest.raises(ValueError, match="không phải là phương trình vi phân"):
            ODEState.from_operation(op)


def test_ux3_2_preserve_cauchy_defaults_from_operation_def():
    """Verify F1: OperationDef default inputs with initial conditions are preserved."""
    # Second-order IVP has catalog default: "y'' - 3*y' - 4*y = 3*exp(2*t), y(0) = 1, y'(0) = 0"
    op_ivp = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_IVP)
    state_ivp = ODEState.from_operation(op_ivp)
    assert state_ivp.mode == ODEMode.CAUCHY_IVP
    assert state_ivp.initial_condition == "y(0) = 1, y'(0) = 0"
    assert state_ivp.initial_condition_draft == "y(0) = 1, y'(0) = 0"
    assert state_ivp.equation == "y'' - 3*y' - 4*y = 3*exp(2*t)"  # Inline IC cleaned from equation


# =============================================================================
# CATEGORY B: Component Rendering & Dynamic Identity (F3)
# =============================================================================

def test_ux3_2_dynamic_workspace_identity_on_classification_change():
    """Verify F3: Workspace header updates dynamically when classification is changed."""
    client = Client(ui.page("/test_dynamic_identity"))
    mock_use_case = MagicMock()

    with client:
        op_linear = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)
        render_ode_workspace(op_linear, mock_use_case)

        # Initial header title should be Linear First-Order
        labels = [el.text for el in client.elements.values() if isinstance(el, ui.label)]
        assert op_linear.title in labels

        # Input a separable equation, triggering the module consistency sync banner
        eq_inputs = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")]
        assert len(eq_inputs) >= 1
        eq_inputs[-1].set_value("y' = y*(1 - y)")

        # Click the smart sync button "Đồng bộ sang Tách biến"
        sync_buttons = [el for el in client.elements.values() if isinstance(el, ui.button) and "Đồng bộ sang Tách biến" in el.text]
        assert len(sync_buttons) >= 1
        for listener in list(sync_buttons[0]._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)

        # After clicking sync, header title must update to Separable
        op_sep = get_operation_by_type(ProblemType.ODE_SEPARABLE)
        updated_labels = [el.text for el in client.elements.values() if isinstance(el, ui.label)]
        assert op_sep.title in updated_labels


def test_ux3_2_contextual_pedagogical_guidance_for_all_first_order_classes():
    """Verify contextual pedagogical guidance for each of the 5 First-Order classifications."""
    guidance_keywords = {
        ODEClassification.FIRST_ORDER_LINEAR: (ProblemType.ODE_FIRST_ORDER_LINEAR, "thừa số tích phân"),
        ODEClassification.FIRST_ORDER_HOMOGENEOUS: (ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS, "thuần nhất"),
        ODEClassification.SEPARABLE: (ProblemType.ODE_SEPARABLE, "tách biến"),
        ODEClassification.EXACT: (ProblemType.ODE_EXACT, "vi phân toàn phần"),
        ODEClassification.INTEGRATING_FACTOR: (ProblemType.ODE_INTEGRATING_FACTOR, "thừa số tích phân"),
    }

    for cls, (pt, keyword) in guidance_keywords.items():
        op = get_operation_by_type(pt)
        client = Client(ui.page(f"/test_guidance_{cls.value}"))
        with client:
            render_ode_workspace(op, MagicMock())
            labels = [el.text.lower() for el in client.elements.values() if isinstance(el, ui.label)]
            assert any(keyword in lbl for lbl in labels), f"Missing guidance for {cls}"


# =============================================================================
# CATEGORY C: Actual Workspace Integration & Solver Execution
# =============================================================================

@pytest.mark.anyio
async def test_ux3_2_real_first_order_ui_submission_all_classifications():
    """Simulate complete UI interactions across all 5 First-Order operations and verify ProblemRequest contracts."""
    core.loop = asyncio.get_running_loop()

    for pt in FIRST_ORDER_TYPES:
        op = get_operation_by_type(pt)
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = SolutionResponse(
            status=SolutionStatus.SUCCESS,
            verification=VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="symbolic_substitution",
                details="Kiểm chứng thành công",
            ),
            raw_input=op.default_input,
            canonical_input=op.default_input,
            final_result="y(t) = C*exp(t)",
            final_latex=r"y(t) = C e^t",
            steps=(),
        )

        client = Client(ui.page(f"/test_sub_{pt.value}"))
        with client:
            render_ode_workspace(op, mock_use_case)

            # 1. Verify equation input has default
            eq_inputs = [
                el for el in client.elements.values()
                if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")
            ]
            assert len(eq_inputs) >= 1
            main_eq_input = eq_inputs[-1]
            assert main_eq_input.value == DEFAULT_CONFIGS[ODEState.from_operation(op).classification]["equation"]

            # 2. Click an example chip
            ex_chips = [el for el in client.elements.values() if isinstance(el, ui.chip)]
            assert len(ex_chips) >= 1
            first_chip = ex_chips[0]
            for listener in list(first_chip._event_listeners.values()):
                if listener.type in ("click", None):
                    listener.handler(None)

            # Equation input should be modified
            assert main_eq_input.value != ""

            # 3. Click "Nhập lại" (Reset)
            reset_btns = [el for el in client.elements.values() if isinstance(el, ui.button) and "Nhập lại" in el.text]
            assert len(reset_btns) >= 1
            for listener in list(reset_btns[-1]._event_listeners.values()):
                if listener.type in ("click", None):
                    listener.handler(None)

            # 4. Click Solve ("GIẢI PHƯƠNG TRÌNH")
            solve_btns = [el for el in client.elements.values() if isinstance(el, ui.button) and "GIẢI PHƯƠNG TRÌNH" in el.text]
            assert len(solve_btns) >= 1
            for listener in list(solve_btns[-1]._event_listeners.values()):
                if listener.type in ("click", None):
                    listener.handler(None)

            for _ in range(25):
                if mock_use_case.execute.called:
                    break
                await asyncio.sleep(0.02)

            # Exactly one request must reach use case
            mock_use_case.execute.assert_called_once()
            req_sent: ProblemRequest = mock_use_case.execute.call_args[0][0]
            assert req_sent.problem_type == pt
            assert "initial_condition" not in req_sent.parameters


# =============================================================================
# CATEGORY D: Screen B Navigation & Order Delegation (F4)
# =============================================================================

def _setup_app_client(page_path: str) -> Client:
    create_app(build_application())
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page(page_path))
    with client:
        route.endpoint.__wrapped__()
    return client


def _navigate_to_operation(client: Client, problem_type: ProblemType) -> None:
    # Secondary first-order classifications reachable through entering their canonical equations
    if problem_type in (
        ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        ProblemType.ODE_SEPARABLE,
        ProblemType.ODE_EXACT,
        ProblemType.ODE_INTEGRATING_FACTOR,
    ):
        _navigate_to_operation(client, ProblemType.ODE_FIRST_ORDER_LINEAR)
        from math_app.presentation.components.workspace.ode.ode_state import DEFAULT_CONFIGS, ODEClassification
        pt_to_cls = {
            ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS: ODEClassification.FIRST_ORDER_HOMOGENEOUS,
            ProblemType.ODE_SEPARABLE: ODEClassification.SEPARABLE,
            ProblemType.ODE_EXACT: ODEClassification.EXACT,
            ProblemType.ODE_INTEGRATING_FACTOR: ODEClassification.INTEGRATING_FACTOR,
        }
        cls_enum = pt_to_cls[problem_type]
        eq_val = DEFAULT_CONFIGS[cls_enum]["equation"]
        for el in client.elements.values():
            if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", ""):
                el.set_value(eq_val)
                return
        raise RuntimeError(f"Equation input for {problem_type} not found")

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


def test_ux3_2_screen_b_routes_all_five_first_order_operations_to_unified_workspace():
    """Verify Screen B mounts the unified ODE workspace for all 5 First-Order operations."""
    for pt in FIRST_ORDER_TYPES:
        client = _setup_app_client(f"/test_screen_b_{pt.value}")
        _navigate_to_operation(client, pt)

        # Verify Step 1 Order cards are rendered with role="button"
        order_cards = [
            el for el in client.elements.values()
            if isinstance(el, ui.card) and el._props.get("role") == "button"
        ]
        assert len(order_cards) == 2, f"Expected 2 order selection cards for {pt}"

        # Verify First-Order guided workflow renders semantic analysis sections without manual override buttons
        all_text = " ".join([
            el.text for el in client.elements.values()
            if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
        ])
        assert "NHẬP BÀI TOÁN" in all_text
        assert "PHÂN TÍCH TỰ ĐỘNG" in all_text
        assert "CƠ SỞ PHÂN LOẠI" in all_text
        assert "PHƯƠNG PHÁP ĐỀ XUẤT" in all_text

        # Verify Solve button is "GIẢI PHƯƠNG TRÌNH"
        buttons = [el.text for el in client.elements.values() if isinstance(el, ui.button)]
        assert any("GIẢI PHƯƠNG TRÌNH" in b for b in buttons)


def test_ux3_2_screen_b_delegates_to_second_order_route_on_order_switch():
    """Verify UX3.3: Clicking Cấp 2 in Step 1 switches to Second-Order inside the unified workspace."""
    client = _setup_app_client("/test_screen_b_order_delegation")
    _navigate_to_operation(client, ProblemType.ODE_FIRST_ORDER_LINEAR)

    # Find the Cấp 2 card in Step 1
    order_cards = [
        el for el in client.elements.values()
        if isinstance(el, ui.card) and el._props.get("role") == "button"
    ]
    assert len(order_cards) == 2
    second_order_card = order_cards[1]

    # Click Second-Order card
    for listener in list(second_order_card._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
            break

    # In the unified workspace, Second-Order classification buttons/cards should now be rendered
    buttons = [el.text for el in client.elements.values() if isinstance(el, ui.button)]
    assert "Thuần nhất" in buttons or "Phương trình thuần nhất" in buttons
    assert "Không thuần nhất" in buttons or "Phương trình không thuần nhất" in buttons
    assert "Hạ bậc nghiệm" in buttons
    assert "Định thức Wronskian" in buttons


def test_ux3_2_screen_b_second_order_returns_to_first_order_route():
    """Verify UX3.3: In Second-Order workspace, clicking Cấp 1 card transitions seamlessly to First-Order."""
    client = _setup_app_client("/test_screen_b_return_to_fo")
    _navigate_to_operation(client, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)

    # Find Step 1 order cards (first two button-cards in document order)
    order_cards = [
        el for el in client.elements.values()
        if isinstance(el, ui.card) and el._props.get("role") == "button"
    ]
    assert len(order_cards) >= 2
    first_order_card = order_cards[0]

    # Click First-Order card
    for listener in list(first_order_card._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
            break

    # Screen B should now render the First-Order unified guided workspace with semantic headers
    all_text = " ".join([el.text for el in client.elements.values() if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text])
    assert "NHẬP BÀI TOÁN" in all_text
    assert "PHÂN TÍCH TỰ ĐỘNG" in all_text
    assert "PHƯƠNG PHÁP ĐỀ XUẤT" in all_text

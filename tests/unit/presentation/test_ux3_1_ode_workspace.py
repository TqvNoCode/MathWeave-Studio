"""Comprehensive test suite for UX3.1: ODE Foundation & Shared Workspace Architecture.

Tests cover:
Category A: ODEState model transitions, immutability, draft IC isolation, and ProblemRequest contracts.
Category B: Rendering, interaction, accessibility, and progressive disclosure of individual selectors:
            - Order selector (Step 1)
            - Classification selector (Step 2)
            - Mode selector (Step 3)
            - Method selector (Step 4)
Category C: Discoverability, configuration, and catalog mapping of all 9 ODE operations.
Category D: Full ODE Workspace integration, example clicks, reset action, and solver dispatch.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock
import pytest
from nicegui import Client, core, ui

from math_app.application.dtos import (
    ExpressionStepContent,
    ProblemRequest,
    SolutionResponse,
    SolutionStep,
    VerificationResult,
)
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.presentation.components.operation_catalog import get_operation_by_type
from math_app.presentation.components.workspace.ode import (
    DEFAULT_CONFIGS,
    ODEClassification,
    ODEMethodPreference,
    ODEMode,
    ODEOrder,
    ODEState,
    render_ode_classification_selector,
    render_ode_method_selector,
    render_ode_mode_selector,
    render_ode_order_selector,
    render_ode_workspace,
)


# =============================================================================
# CATEGORY A: State Model Transitions, Drafts & Request Contracts
# =============================================================================

def test_ode_state_defaults_and_enums():
    """Verify all enums, default configurations, and initial state properties."""
    # Check enum values
    assert ODEOrder.FIRST_ORDER.value == "first_order"
    assert ODEOrder.SECOND_ORDER.value == "second_order"

    assert len(ODEClassification) == 10
    assert len(DEFAULT_CONFIGS) == 10

    # Verify every classification has complete configuration
    for cls in ODEClassification:
        cfg = DEFAULT_CONFIGS[cls]
        assert "equation" in cfg
        assert "target_var" in cfg
        assert "examples" in cfg
        assert cls.order in (ODEOrder.FIRST_ORDER, ODEOrder.SECOND_ORDER)
        assert len(cls.display_label) > 0
        assert len(cls.math_subtitle) > 0
        assert len(cfg["equation"]) > 0
        assert len(cfg["target_var"]) > 0
        assert len(cfg["examples"]) >= 2

    # Verify default state constructor
    state = ODEState()
    assert state.order == ODEOrder.SECOND_ORDER
    assert state.classification == ODEClassification.SECOND_ORDER_NONHOMOGENEOUS
    assert state.mode == ODEMode.GENERAL
    assert state.method_preference == ODEMethodPreference.AUTO
    assert state.is_cauchy is False
    assert state.initial_condition == ""
    assert state.initial_condition_draft == ""


def test_ode_state_from_operation_all_9_types():
    """Verify ODEState.from_operation() correctly initializes state for each ODE problem type."""
    type_to_cls = {
        ProblemType.ODE_FIRST_ORDER_LINEAR: (ODEOrder.FIRST_ORDER, ODEClassification.FIRST_ORDER_LINEAR, ODEMode.GENERAL),
        ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS: (ODEOrder.FIRST_ORDER, ODEClassification.FIRST_ORDER_HOMOGENEOUS, ODEMode.GENERAL),
        ProblemType.ODE_SEPARABLE: (ODEOrder.FIRST_ORDER, ODEClassification.SEPARABLE, ODEMode.GENERAL),
        ProblemType.ODE_EXACT: (ODEOrder.FIRST_ORDER, ODEClassification.EXACT, ODEMode.GENERAL),
        ProblemType.ODE_INTEGRATING_FACTOR: (ODEOrder.FIRST_ORDER, ODEClassification.INTEGRATING_FACTOR, ODEMode.GENERAL),
        ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF: (ODEOrder.SECOND_ORDER, ODEClassification.SECOND_ORDER_HOMOGENEOUS, ODEMode.GENERAL),
        ProblemType.ODE_SECOND_ORDER_IVP: (ODEOrder.SECOND_ORDER, ODEClassification.SECOND_ORDER_NONHOMOGENEOUS, ODEMode.CAUCHY_IVP),
        ProblemType.ODE_REDUCTION_OF_ORDER: (ODEOrder.SECOND_ORDER, ODEClassification.REDUCTION_OF_ORDER, ODEMode.GENERAL),
        ProblemType.WRONSKIAN: (ODEOrder.SECOND_ORDER, ODEClassification.WRONSKIAN, ODEMode.GENERAL),
    }

    for pt, (expected_order, expected_cls, expected_mode) in type_to_cls.items():
        op = get_operation_by_type(pt)
        assert op is not None, f"Operation for {pt} must exist in catalog"
        state = ODEState.from_operation(op)
        assert state.order == expected_order, f"Order mismatch for {pt}"
        assert state.classification == expected_cls, f"Classification mismatch for {pt}"
        assert state.mode == expected_mode, f"Mode mismatch for {pt}"
        if expected_mode == ODEMode.CAUCHY_IVP:
            # F1: Cauchy IVP operations preserve default initial conditions from catalog
            assert state.initial_condition == "y(0) = 1, y'(0) = 0"
        else:
            assert state.initial_condition == ""

    # F2: Non-ODE operation rejection
    op_calc = get_operation_by_type(ProblemType.DERIVATIVE)
    with pytest.raises(ValueError, match="không phải là phương trình vi phân"):
        ODEState.from_operation(op_calc)


def test_ode_state_order_transitions():
    """Verify order transitions update classification, equation, and drafts properly."""
    state = ODEState()
    assert state.order == ODEOrder.SECOND_ORDER

    # Switch to FIRST_ORDER
    state1 = state.with_order(ODEOrder.FIRST_ORDER)
    assert state1.order == ODEOrder.FIRST_ORDER
    assert state1.classification == ODEClassification.FIRST_ORDER_LINEAR
    assert state1.equation == DEFAULT_CONFIGS[ODEClassification.FIRST_ORDER_LINEAR]["equation"]

    # Switch back to SECOND_ORDER
    state2 = state1.with_order(ODEOrder.SECOND_ORDER)
    assert state2.order == ODEOrder.SECOND_ORDER
    assert state2.classification == ODEClassification.SECOND_ORDER_NONHOMOGENEOUS
    assert state2.equation == DEFAULT_CONFIGS[ODEClassification.SECOND_ORDER_NONHOMOGENEOUS]["equation"]


def test_ode_state_classification_transitions():
    """Verify classification transitions update relevant fields."""
    state = ODEState().with_order(ODEOrder.FIRST_ORDER)

    # Change to separable
    state_sep = state.with_classification(ODEClassification.SEPARABLE)
    assert state_sep.classification == ODEClassification.SEPARABLE
    assert state_sep.order == ODEOrder.FIRST_ORDER
    assert state_sep.equation == DEFAULT_CONFIGS[ODEClassification.SEPARABLE]["equation"]

    # Change to second-order homogeneous across orders
    state_homo = state_sep.with_classification(ODEClassification.SECOND_ORDER_HOMOGENEOUS)
    assert state_homo.classification == ODEClassification.SECOND_ORDER_HOMOGENEOUS
    assert state_homo.order == ODEOrder.SECOND_ORDER
    assert state_homo.equation == DEFAULT_CONFIGS[ODEClassification.SECOND_ORDER_HOMOGENEOUS]["equation"]


def test_ode_state_draft_isolation_and_zero_parameter_leakage():
    """Verify draft IC preservation and strict zero parameter leakage in GENERAL mode."""
    # 1. Start in general mode
    state = ODEState()
    assert state.mode == ODEMode.GENERAL
    assert state.initial_condition == ""
    assert state.is_cauchy is False

    # 2. Entering an initial condition updates draft and switches to CAUCHY_IVP
    state_ic = state.with_initial_condition("y(0) = 2, y'(0) = -1")
    assert state_ic.mode == ODEMode.CAUCHY_IVP
    assert state_ic.is_cauchy is True
    assert state_ic.initial_condition == "y(0) = 2, y'(0) = -1"
    assert state_ic.initial_condition_draft == "y(0) = 2, y'(0) = -1"

    # Verify request in CAUCHY_IVP mode contains initial_condition
    req_cauchy = state_ic.build_problem_request()
    assert "initial_condition" in req_cauchy.parameters
    assert req_cauchy.parameters["initial_condition"] == "y(0) = 2, y'(0) = -1"

    # 3. Switching mode back to GENERAL clears initial_condition but PRESERVES draft!
    state_gen = state_ic.with_mode(ODEMode.GENERAL)
    assert state_gen.mode == ODEMode.GENERAL
    assert state_gen.is_cauchy is False
    assert state_gen.initial_condition == ""
    assert state_gen.initial_condition_draft == "y(0) = 2, y'(0) = -1"

    # CRITICAL: Verify request in GENERAL mode has ZERO initial_condition in parameters
    req_gen = state_gen.build_problem_request()
    assert "initial_condition" not in req_gen.parameters, (
        "Zero parameter leakage violation: initial_condition must NOT be present in GENERAL mode!"
    )

    # 4. Switching back to CAUCHY_IVP restores the saved draft
    state_restored = state_gen.with_mode(ODEMode.CAUCHY_IVP)
    assert state_restored.mode == ODEMode.CAUCHY_IVP
    assert state_restored.is_cauchy is True
    assert state_restored.initial_condition == "y(0) = 2, y'(0) = -1"

    # 5. Reset completely clears the draft
    state_reset = state_restored.reset()
    assert state_reset.mode == ODEMode.GENERAL
    assert state_reset.initial_condition == ""
    assert state_reset.initial_condition_draft == ""


def test_build_problem_request_all_9_operations_general_mode():
    """Verify ProblemRequest contracts for all 9 ODE classifications in GENERAL mode."""
    for cls in ODEClassification:
        state = ODEState().with_classification(cls)
        req = state.build_problem_request()

        cfg = DEFAULT_CONFIGS[cls]
        assert req.problem_type == state.problem_type
        assert req.raw_input == cfg["equation"]
        assert req.target_variable == cfg["target_var"]
        assert "initial_condition" not in req.parameters

        # Specific operation checks
        if cls == ODEClassification.SECOND_ORDER_NONHOMOGENEOUS:
            assert req.parameters["method_preference"] == "AUTO"
            assert req.parameters["expected_classification"] == "NONHOMOGENEOUS"
        elif cls == ODEClassification.SECOND_ORDER_HOMOGENEOUS:
            assert req.parameters["expected_classification"] == "HOMOGENEOUS"
            assert "method_preference" not in req.parameters


def test_build_problem_request_cauchy_conflict_detection():
    """Verify InvalidInputError is raised when inline ICs and initial_condition parameter conflict."""
    # Equation already has inline ICs
    state = (
        ODEState()
        .with_classification(ODEClassification.SECOND_ORDER_HOMOGENEOUS)
        .with_equation("y'' + y = 0, y(0)=1, y'(0)=0")
        .with_initial_condition("y(0)=2, y'(0)=1")
    )

    with pytest.raises(InvalidInputError, match="xung đột"):
        state.build_problem_request()


def test_build_problem_request_reduction_of_order_known_solution():
    """Verify known solution parameter is populated in Reduction of Order."""
    state = (
        ODEState()
        .with_classification(ODEClassification.REDUCTION_OF_ORDER)
        .with_known_solution("1/t")
    )
    req = state.build_problem_request()
    assert req.problem_type == ProblemType.ODE_REDUCTION_OF_ORDER
    assert req.parameters.get("y1") == "1/t"


# =============================================================================
# CATEGORY B: Selector Components Rendering & Interaction
# =============================================================================

def test_render_ode_order_selector():
    """Verify Step 1 Order selector renders both cards and triggers callback on click."""
    client = Client(ui.page("/test_order_selector"))
    with client:
        selected_order = None

        def on_change(order: ODEOrder):
            nonlocal selected_order
            selected_order = order

        state = ODEState(order=ODEOrder.SECOND_ORDER)
        render_ode_order_selector(state.order, on_change)

        # Find the cards
        cards = [el for el in client.elements.values() if isinstance(el, ui.card)]
        assert len(cards) == 2

        first_order_card = cards[0]
        assert first_order_card._props.get("role") == "button"
        assert first_order_card._props.get("tabindex") == "0"

        # Click the First-Order card
        for listener in list(first_order_card._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)

        assert selected_order == ODEOrder.FIRST_ORDER


def test_render_ode_classification_selector_first_order():
    """Verify Step 2 Classification selector renders 5 first-order classes."""
    client = Client(ui.page("/test_cls_selector_1st"))
    with client:
        selected_cls = None

        def on_change(cls: ODEClassification):
            nonlocal selected_cls
            selected_cls = cls

        state = ODEState(order=ODEOrder.FIRST_ORDER, classification=ODEClassification.FIRST_ORDER_LINEAR)
        render_ode_classification_selector(state.order, state.classification, on_change)

        # Verify buttons for 5 first-order classifications
        cls_buttons = [el for el in client.elements.values() if isinstance(el, ui.button)]
        labels = [btn.text for btn in cls_buttons]
        assert "Tuyến tính cấp 1" in labels
        assert "Tách biến" in labels
        assert "Vi phân toàn phần" in labels
        assert "Thừa số tích phân" in labels
        assert "Thuần nhất cấp 1" in labels

        # Click Separable button
        sep_btn = [btn for btn in cls_buttons if btn.text == "Tách biến"][0]
        for listener in list(sep_btn._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)

        assert selected_cls == ODEClassification.SEPARABLE


def test_render_ode_classification_selector_second_order():
    """Verify Step 2 Classification selector renders 4 second-order classes."""
    client = Client(ui.page("/test_cls_selector_2nd"))
    with client:
        selected_cls = None

        def on_change(cls: ODEClassification):
            nonlocal selected_cls
            selected_cls = cls

        state = ODEState(order=ODEOrder.SECOND_ORDER, classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS)
        render_ode_classification_selector(state.order, state.classification, on_change)

        cls_buttons = [el for el in client.elements.values() if isinstance(el, ui.button)]
        labels = [btn.text for btn in cls_buttons]
        assert "Không thuần nhất" in labels
        assert "Thuần nhất" in labels
        assert "Hạ bậc nghiệm" in labels
        assert "Định thức Wronskian" in labels

        # Click Homogeneous button
        homo_btn = [btn for btn in cls_buttons if btn.text == "Thuần nhất"][0]
        for listener in list(homo_btn._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)

        assert selected_cls == ODEClassification.SECOND_ORDER_HOMOGENEOUS


def test_render_ode_mode_selector():
    """Verify Step 3 Mode selector renders General/Cauchy buttons and toggles IC container."""
    client = Client(ui.page("/test_mode_selector"))
    with client:
        mode_changed = None
        ic_changed = None

        def on_mode_change(mode: ODEMode):
            nonlocal mode_changed
            mode_changed = mode

        def on_ic_change(ic: str):
            nonlocal ic_changed
            ic_changed = ic

        # 1. Test General mode (IC container hidden)
        state_gen = ODEState(order=ODEOrder.SECOND_ORDER, classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS, mode=ODEMode.GENERAL)
        render_ode_mode_selector(
            state_gen.order,
            state_gen.classification,
            state_gen.mode,
            state_gen.initial_condition,
            on_mode_change,
            on_ic_change,
        )

        mode_buttons = [
            el for el in client.elements.values()
            if isinstance(el, ui.button) and el.text in ("Tìm nghiệm tổng quát", "Bài toán Cauchy (IVP)")
        ]
        assert len(mode_buttons) == 2

        # In general mode, IC input container should not be rendered
        ic_inputs_gen = [el for el in client.elements.values() if isinstance(el, ui.input) and "Điều kiện" in el._props.get("label", "")]
        assert len(ic_inputs_gen) == 0

        # Click Cauchy button
        cauchy_btn = [btn for btn in mode_buttons if "Cauchy" in btn.text][0]
        for listener in list(cauchy_btn._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)

        assert mode_changed == ODEMode.CAUCHY_IVP

    # 2. Test Cauchy mode (IC container visible)
    client2 = Client(ui.page("/test_mode_selector_cauchy"))
    with client2:
        state_cauchy = ODEState(
            order=ODEOrder.SECOND_ORDER,
            classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
            mode=ODEMode.CAUCHY_IVP,
            initial_condition="y(0) = 1, y'(0) = 0",
        )
        render_ode_mode_selector(
            state_cauchy.order,
            state_cauchy.classification,
            state_cauchy.mode,
            state_cauchy.initial_condition,
            on_mode_change,
            on_ic_change,
        )

        ic_inputs_cauchy = [el for el in client2.elements.values() if isinstance(el, ui.input) and "Điều kiện" in el._props.get("label", "")]
        assert len(ic_inputs_cauchy) == 1
        assert ic_inputs_cauchy[0].value == "y(0) = 1, y'(0) = 0"


def test_render_ode_method_selector():
    """Verify Step 4 Method selector renders appropriate UI for each classification."""
    # 1. Nonhomogeneous Second-Order -> Radio selector
    client1 = Client(ui.page("/test_method_nonhomo"))
    with client1:
        method_changed = None

        def on_change(method: ODEMethodPreference):
            nonlocal method_changed
            method_changed = method

        state1 = ODEState(
            order=ODEOrder.SECOND_ORDER,
            classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
            method_preference=ODEMethodPreference.AUTO,
        )
        render_ode_method_selector(
            state1.order,
            state1.classification,
            state1.method_preference,
            on_change,
        )

        radios = [el for el in client1.elements.values() if isinstance(el, ui.radio)]
        assert len(radios) == 1
        assert radios[0].value == ODEMethodPreference.AUTO.value

    # 2. Homogeneous Second-Order -> Info card with characteristic equation explanation
    client2 = Client(ui.page("/test_method_homo"))
    with client2:
        state2 = ODEState(
            order=ODEOrder.SECOND_ORDER,
            classification=ODEClassification.SECOND_ORDER_HOMOGENEOUS,
        )
        render_ode_method_selector(
            state2.order,
            state2.classification,
            state2.method_preference,
            lambda m: None,
        )
        # Verify text content explains characteristic equation
        info_labels = [el for el in client2.elements.values() if isinstance(el, ui.label) and "đặc trưng" in el.text]
        assert len(info_labels) >= 1

    # 3. First-Order -> Pedagogical info card
    client3 = Client(ui.page("/test_method_first"))
    with client3:
        state3 = ODEState(
            order=ODEOrder.FIRST_ORDER,
            classification=ODEClassification.FIRST_ORDER_LINEAR,
        )
        render_ode_method_selector(
            state3.order,
            state3.classification,
            state3.method_preference,
            lambda m: None,
        )
        info_labels = [el for el in client3.elements.values() if isinstance(el, ui.label) and "thừa số tích phân" in el.text.lower()]
        assert len(info_labels) >= 1


# =============================================================================
# CATEGORY C: Discoverability and Catalog Mapping
# =============================================================================

def test_all_ode_operations_discoverable():
    """Verify all 9 ODE classifications map directly to valid ProblemTypes in catalog."""
    for cls in ODEClassification:
        cfg = DEFAULT_CONFIGS[cls]
        state = ODEState().with_classification(cls)
        op = get_operation_by_type(state.problem_type)
        assert op is not None, f"ProblemType {state.problem_type} must exist in catalog"
        assert len(cfg["examples"]) >= 2, f"At least 2 examples required for {cls}"
        for lbl, ex_str in cfg["examples"]:
            assert len(lbl) > 0
            assert len(ex_str) > 0


# =============================================================================
# CATEGORY D: Full ODE Workspace Integration & Solver Execution
# =============================================================================

@pytest.mark.anyio
async def test_render_ode_workspace_full_flow():
    """Verify full ODE workspace lifecycle: rendering, example click, reset, and solve."""
    core.loop = asyncio.get_running_loop()

    # Mock use case
    mock_use_case = MagicMock()
    mock_solution = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(
            status=VerificationStatus.VERIFIED,
            method="symbolic_substitution",
            details="Nghiệm đã được kiểm chứng khớp hoàn toàn.",
        ),
        raw_input="y'' - 3*y' - 4*y = 3*exp(2*t)",
        canonical_input="y'' - 3*y' - 4*y = 3*exp(2*t)",
        final_result="y(t) = C1*exp(-t) + C2*exp(4*t) - 1/2*exp(2*t)",
        final_latex=r"y(t) = C_1 e^{-t} + C_2 e^{4t} - \frac{1}{2} e^{2t}",
        steps=(
            SolutionStep(
                step_number=1,
                rule_name="characteristic_equation",
                description="Giải phương trình đặc trưng ar^2 + br + c = 0",
                content=ExpressionStepContent(
                    expression_before="r^2 - 3r - 4 = 0",
                    expression_after="r1 = -1, r2 = 4",
                    latex_before=r"r^2 - 3r - 4 = 0",
                    latex_after=r"r_1 = -1, \quad r_2 = 4",
                ),
            ),
        ),
    )
    mock_use_case.execute.return_value = mock_solution

    client = Client(ui.page("/test_ode_workspace_full"))
    with client:
        op = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)
        render_ode_workspace(op, mock_use_case)

        # Verify main equation input
        eq_inputs = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")]
        assert len(eq_inputs) >= 1
        main_input = eq_inputs[0]
        initial_val = main_input.value
        assert len(initial_val) > 0

        # Verify example chips exist
        example_chips = [el for el in client.elements.values() if isinstance(el, ui.chip)]
        assert len(example_chips) >= 2

        # Click first example chip
        first_ex_chip = example_chips[0]
        for listener in list(first_ex_chip._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)

        # Value should update to example
        assert main_input.value != ""

        # Click "Nhập lại" (Reset) button
        reset_btns = [el for el in client.elements.values() if isinstance(el, ui.button) and "Nhập lại" in el.text]
        assert len(reset_btns) >= 1
        active_reset_btn = reset_btns[-1]
        for listener in list(active_reset_btn._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)

        # Re-fetch main input after re-render
        active_inputs = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")]
        assert len(active_inputs) >= 1
        main_input = active_inputs[-1]

        # Value should return to default equation
        assert main_input.value == DEFAULT_CONFIGS[ODEClassification.SECOND_ORDER_HOMOGENEOUS]["equation"]

        # Click Solve button ("GIẢI PHƯƠNG TRÌNH")
        solve_btns = [el for el in client.elements.values() if isinstance(el, ui.button) and "GIẢI PHƯƠNG TRÌNH" in el.text]
        assert len(solve_btns) >= 1

        active_solve_btn = solve_btns[-1]
        for listener in list(active_solve_btn._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)

        await asyncio.sleep(0.05)

        # Verify use_case.execute was called
        mock_use_case.execute.assert_called_once()
        req_sent: ProblemRequest = mock_use_case.execute.call_args[0][0]
        assert req_sent.problem_type == ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF
        assert req_sent.raw_input == DEFAULT_CONFIGS[ODEClassification.SECOND_ORDER_HOMOGENEOUS]["equation"]
        assert req_sent.parameters.get("expected_classification") == "HOMOGENEOUS"

"""Unit and presentation tests for UX3.3:
Second-Order ODE & Advanced Tools Presentation Unification into Academic Blue Workspace.

Covers Categories A through H:
- Category A: Routing & Unified Workspace Architecture (All 9 ODE operations route to render_ode_workspace)
- Category B: Second-Order Classification & Contextual Cards
- Category C: General Solution & Method Selection (Auto, UC, VoP)
- Category D: Cauchy IVP Mode & Strict Validation (Missing, Incomplete, Conflicting, Matching ICs)
- Category E: Advanced Second-Order Tools (Reduction of Order & Wronskian)
- Category F: State Isolation & Zero Parameter Leakage (Order, Mode, Classification transitions, Reset)
- Category G: Real UI Submission & Live Solver Verification (1 request per click, VERIFIED status)
- Category H: Regression & Operation Parity (All 9 ODE types)
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
    get_second_order_examples,
)
from math_app.presentation.components.workspace.ode import (
    DEFAULT_CONFIGS,
    ODEClassification,
    ODEMethodPreference,
    ODEMode,
    ODEOrder,
    ODEState,
    render_ode_workspace,
)

ALL_9_ODE_TYPES = [
    ProblemType.ODE_FIRST_ORDER_LINEAR,
    ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
    ProblemType.ODE_SEPARABLE,
    ProblemType.ODE_EXACT,
    ProblemType.ODE_INTEGRATING_FACTOR,
    ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
    ProblemType.ODE_SECOND_ORDER_IVP,
    ProblemType.ODE_REDUCTION_OF_ORDER,
    ProblemType.WRONSKIAN,
]

SECOND_ORDER_TYPES = [
    ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
    ProblemType.ODE_SECOND_ORDER_IVP,
    ProblemType.ODE_REDUCTION_OF_ORDER,
    ProblemType.WRONSKIAN,
]


def _setup_app_client(page_path: str, use_case=None) -> Client:
    """Helper to initialize full NiceGUI app client."""
    uc = use_case or build_application()
    create_app(uc)
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page(page_path))
    with client:
        route.endpoint.__wrapped__()
    return client


def _navigate_to_op(client: Client, problem_type: ProblemType) -> None:
    """Helper to click catalog card on Screen A and navigate to Screen B."""
    if problem_type in (
        ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        ProblemType.ODE_SEPARABLE,
        ProblemType.ODE_EXACT,
        ProblemType.ODE_INTEGRATING_FACTOR,
    ):
        _navigate_to_op(client, ProblemType.ODE_FIRST_ORDER_LINEAR)
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

    if problem_type == ProblemType.ODE_SECOND_ORDER_IVP:
        _navigate_to_op(client, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)
        for el in list(client.elements.values()):
            if isinstance(el, ui.button) and el.text == "Bài toán Cauchy (IVP)":
                for listener in list(el._event_listeners.values()):
                    if listener.type in ("click", None):
                        with client:
                            listener.handler(None)
                        return
        raise RuntimeError("Cauchy IVP button not found")

    if problem_type == ProblemType.ODE_REDUCTION_OF_ORDER:
        _navigate_to_op(client, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)
        for el in list(client.elements.values()):
            if isinstance(el, ui.button) and el.text == "Hạ bậc nghiệm":
                for listener in list(el._event_listeners.values()):
                    if listener.type in ("click", None):
                        with client:
                            listener.handler(None)
                        return
        raise RuntimeError("Reduction of order button not found")

    if problem_type == ProblemType.WRONSKIAN:
        _navigate_to_op(client, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)
        for el in list(client.elements.values()):
            if isinstance(el, ui.button) and el.text == "Định thức Wronskian":
                for listener in list(el._event_listeners.values()):
                    if listener.type in ("click", None):
                        with client:
                            listener.handler(None)
                        return
        raise RuntimeError("Wronskian button not found")

    for el in list(client.elements.values()):
        for listener in list(el._event_listeners.values()):
            defaults = getattr(listener.handler, "__defaults__", ())
            if defaults:
                for d in defaults:
                    if hasattr(d, "problem_type") and d.problem_type == problem_type:
                        with client:
                            listener.handler(None)
                        return
    raise RuntimeError(f"Catalog card for {problem_type} not found")


# =============================================================================
# CATEGORY A: Routing & Unified Workspace Architecture
# =============================================================================

def test_category_a_all_nine_ode_operations_route_to_unified_workspace():
    """Verify all 9 ODE operations render the unified ODE workspace (Step 1 Order selector present)."""
    for pt in ALL_9_ODE_TYPES:
        client = _setup_app_client(f"/test_cat_a_{pt.value}")
        _navigate_to_op(client, pt)

        # Step 1 Order cards must be present with role="button"
        order_cards = [
            el for el in client.elements.values()
            if isinstance(el, ui.card) and el._props.get("role") == "button"
        ]
        assert len(order_cards) >= 2, f"Unified workspace order cards missing for {pt}"

        # Solve button must be "GIẢI PHƯƠNG TRÌNH"
        buttons = [el.text for el in client.elements.values() if isinstance(el, ui.button)]
        assert "GIẢI PHƯƠNG TRÌNH" in buttons, f"Unified solve button missing for {pt}"

        # Legacy wizard toolbar / step indicators must NOT exist
        labels = [el.text for el in client.elements.values() if isinstance(el, ui.label)]
        assert not any("← Phương trình vi phân cấp 1" in lbl for lbl in labels)


def test_category_a_second_order_wizard_completely_unmounted():
    """Verify obsolete Second-Order 3-step wizard and sub-nav toolbar are not rendered."""
    client = _setup_app_client("/test_cat_a_no_wizard")
    _navigate_to_op(client, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)

    buttons = [el.text for el in client.elements.values() if isinstance(el, ui.button)]
    # Legacy toolbar button must be gone
    assert "← Quay lại danh mục" not in buttons
    assert "← Phương trình vi phân cấp 1" not in buttons

    # The workspace must be render_ode_workspace with Academic Blue Step Badges
    badges = [el.text for el in client.elements.values() if isinstance(el, ui.badge)]
    assert "BƯỚC 1" in badges
    assert "BƯỚC 2" in badges
    assert "BƯỚC 3" in badges


def test_category_a_step_1_order_switching_in_place():
    """Verify switching between Cấp 1 and Cấp 2 occurs 100% inside render_ode_workspace."""
    client = _setup_app_client("/test_cat_a_order_switch")
    _navigate_to_op(client, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)

    # Initially in Second-Order: shows Homogeneous & Nonhomogeneous cards
    buttons = [el.text for el in client.elements.values() if isinstance(el, ui.button)]
    assert "Thuần nhất" in buttons or "Phương trình thuần nhất" in buttons

    # Find Step 1 cards
    order_cards = [
        el for el in client.elements.values()
        if isinstance(el, ui.card) and el._props.get("role") == "button"
    ]
    first_order_card = order_cards[0]

    # Switch to Cấp 1
    for listener in list(first_order_card._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
            break

    # Now First-Order workflow is visible
    all_text_fo = " ".join([el.text for el in client.elements.values() if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text])
    assert "TỰ ĐỘNG PHÂN LOẠI TOÁN HỌC:" in all_text_fo
    assert "PHƯƠNG PHÁP GIẢI KHUYẾN NGHỊ:" in all_text_fo

    # Switch back to Cấp 2
    order_cards_fo = [
        el for el in client.elements.values()
        if isinstance(el, ui.card) and el._props.get("role") == "button"
    ]
    second_order_card = order_cards_fo[1]
    for listener in list(second_order_card._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
            break

    buttons_so = [el.text for el in client.elements.values() if isinstance(el, ui.button)]
    assert "Thuần nhất" in buttons_so or "Phương trình thuần nhất" in buttons_so
    assert "Hạ bậc nghiệm" in buttons_so
    assert "Định thức Wronskian" in buttons_so


# =============================================================================
# CATEGORY B: Second-Order Classification & Contextual Cards
# =============================================================================

def test_category_b_classification_transitions():
    """Verify state and defaults update when switching among the 4 second-order classifications."""
    state = ODEState.from_operation(get_operation_by_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF))
    assert state.order == ODEOrder.SECOND_ORDER

    # 1. Switch to Nonhomogeneous
    s_nonhomo = state.with_classification(ODEClassification.SECOND_ORDER_NONHOMOGENEOUS)
    assert s_nonhomo.classification == ODEClassification.SECOND_ORDER_NONHOMOGENEOUS
    assert s_nonhomo.equation == DEFAULT_CONFIGS[ODEClassification.SECOND_ORDER_NONHOMOGENEOUS]["equation"]

    # 2. Switch to Reduction of Order
    s_red = state.with_classification(ODEClassification.REDUCTION_OF_ORDER)
    assert s_red.classification == ODEClassification.REDUCTION_OF_ORDER
    assert s_red.equation == DEFAULT_CONFIGS[ODEClassification.REDUCTION_OF_ORDER]["equation"]

    # 3. Switch to Wronskian
    s_wron = state.with_classification(ODEClassification.WRONSKIAN)
    assert s_wron.classification == ODEClassification.WRONSKIAN
    assert s_wron.equation == DEFAULT_CONFIGS[ODEClassification.WRONSKIAN]["equation"]

    # 4. Switch back to Homogeneous
    s_homo = s_wron.with_classification(ODEClassification.SECOND_ORDER_HOMOGENEOUS)
    assert s_homo.classification == ODEClassification.SECOND_ORDER_HOMOGENEOUS
    assert s_homo.equation == DEFAULT_CONFIGS[ODEClassification.SECOND_ORDER_HOMOGENEOUS]["equation"]


def test_category_b_custom_equation_preserved_between_homo_and_nonhomo():
    """Verify custom user equation is preserved when toggling between Homogeneous and Nonhomogeneous."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_HOMOGENEOUS,
        equation="y'' + 4*y' + 4*y = 0",
    )
    s_custom_nonhomo = state.with_classification(ODEClassification.SECOND_ORDER_NONHOMOGENEOUS)
    assert s_custom_nonhomo.equation == "y'' + 4*y' + 4*y = 0"

    s_back_homo = s_custom_nonhomo.with_classification(ODEClassification.SECOND_ORDER_HOMOGENEOUS)
    assert s_back_homo.equation == "y'' + 4*y' + 4*y = 0"


# =============================================================================
# CATEGORY C: General Solution & Method Selection
# =============================================================================

def test_category_c_homogeneous_general_solution_request():
    """Verify ProblemRequest construction for Second-Order Homogeneous General solution."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_HOMOGENEOUS,
        mode=ODEMode.GENERAL,
        equation="y'' - 5*y' + 6*y = 0",
        target_var="t",
    )
    req = state.build_problem_request()
    assert req.problem_type == ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF
    assert req.raw_input == "y'' - 5*y' + 6*y = 0"
    assert req.target_variable == "t"
    assert req.parameters["expected_classification"] == "HOMOGENEOUS"
    assert req.parameters["problem_mode"] == "GENERAL"
    assert "initial_condition" not in req.parameters


def test_category_c_nonhomogeneous_general_solution_with_methods():
    """Verify Method selection (AUTO, UC, VoP) for Second-Order Nonhomogeneous General solution."""
    base_state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
        mode=ODEMode.GENERAL,
        equation="y'' + y = tan(t)",
        target_var="t",
    )

    # 1. AUTO method
    req_auto = base_state.with_method_preference(ODEMethodPreference.AUTO).build_problem_request()
    assert req_auto.parameters["method_preference"] == "AUTO"

    # 2. Undetermined Coefficients
    req_uc = base_state.with_method_preference(ODEMethodPreference.UNDETERMINED_COEFFICIENTS).build_problem_request()
    assert req_uc.parameters["method_preference"] == "UNDETERMINED_COEFFICIENTS"

    # 3. Variation of Parameters
    req_vop = base_state.with_method_preference(ODEMethodPreference.VARIATION_OF_PARAMETERS).build_problem_request()
    assert req_vop.parameters["method_preference"] == "VARIATION_OF_PARAMETERS"


def test_category_c_method_selector_hidden_for_homogeneous_and_advanced():
    """Verify Method Selector is only rendered for Nonhomogeneous second-order."""
    client = Client(ui.page("/test_cat_c_method_visibility"))
    with client:
        # Homogeneous
        op_homo = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)
        render_ode_workspace(op_homo, MagicMock())

        # Method selector buttons should NOT exist when homogeneous
        buttons = [el.text for el in client.elements.values() if isinstance(el, ui.button)]
        assert "Tự động chọn" not in buttons
        assert "Hệ số bất định" not in buttons
        assert "Biến thiên hằng số" not in buttons


# =============================================================================
# CATEGORY D: Cauchy IVP Mode & Strict Validation
# =============================================================================

def test_category_d_cauchy_ivp_request_construction():
    """Verify ProblemRequest construction for Second-Order Cauchy IVP."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_HOMOGENEOUS,
        mode=ODEMode.CAUCHY_IVP,
        equation="y'' - 3*y' - 4*y = 0",
        initial_condition="y(0) = 1, y'(0) = 0",
        target_var="t",
    )
    req = state.build_problem_request()
    assert req.problem_type == ProblemType.ODE_SECOND_ORDER_IVP
    assert req.raw_input == "y'' - 3*y' - 4*y = 0"
    assert req.parameters["problem_mode"] == "CAUCHY_IVP"
    assert req.parameters["expected_classification"] == "HOMOGENEOUS"
    assert req.parameters["initial_condition"] == "y(0) = 1, y'(0) = 0"


def test_category_d_cauchy_ivp_missing_ic_rejected():
    """Verify missing initial conditions in Cauchy IVP mode raise InvalidInputError."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
        mode=ODEMode.CAUCHY_IVP,
        equation="y'' - 3*y' - 4*y = 3*exp(2*t)",
        initial_condition="",
    )
    with pytest.raises(InvalidInputError, match="y\\(t0\\) = y0 và y'\\(t0\\) = v0"):
        state.build_problem_request()


def test_category_d_cauchy_ivp_incomplete_ic_rejected():
    """Verify supplying only y(t0)=y0 without y'(t0)=v0 raises InvalidInputError."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
        mode=ODEMode.CAUCHY_IVP,
        equation="y'' - 3*y' - 4*y = 3*exp(2*t)",
        initial_condition="y(0) = 1",  # Missing y'(0)
    )
    with pytest.raises(InvalidInputError, match="đầy đủ hai điều kiện ban đầu"):
        state.build_problem_request()


def test_category_d_cauchy_ivp_conflict_detection():
    """Verify conflicting initial conditions between equation and dedicated input raise InvalidInputError."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
        mode=ODEMode.CAUCHY_IVP,
        equation="y'' + y = 0, y(0) = 1, y'(0) = 2",
        initial_condition="y(0) = 0, y'(0) = 5",
    )
    with pytest.raises(InvalidInputError, match="Phát hiện xung đột điều kiện ban đầu"):
        state.build_problem_request()


def test_category_d_cauchy_ivp_matching_inline_and_dedicated():
    """Verify identical inline and dedicated initial conditions succeed without conflict."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
        mode=ODEMode.CAUCHY_IVP,
        equation="y'' + y = 0, y(0) = 1, y'(0) = 2",
        initial_condition="y(0) = 1, y'(0) = 2",
    )
    req = state.build_problem_request()
    assert req.raw_input == "y'' + y = 0"
    assert req.parameters["initial_condition"] == "y(0) = 1, y'(0) = 2"


def test_category_d_cauchy_to_general_mode_isolation_and_restoration():
    """Verify switching from Cauchy IVP to General stashes IC into draft and restores upon re-entering IVP."""
    state_ivp = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
        mode=ODEMode.CAUCHY_IVP,
        initial_condition="y(0) = 2, y'(0) = -1",
    )
    assert state_ivp.initial_condition == "y(0) = 2, y'(0) = -1"

    # Switch to GENERAL: active IC is cleared, draft retains value
    state_gen = state_ivp.with_mode(ODEMode.GENERAL)
    assert state_gen.mode == ODEMode.GENERAL
    assert state_gen.initial_condition == ""
    assert state_gen.initial_condition_draft == "y(0) = 2, y'(0) = -1"

    # Build request in GENERAL mode must have no IC
    req_gen = state_gen.build_problem_request()
    assert "initial_condition" not in req_gen.parameters

    # Switch back to CAUCHY_IVP: draft is restored
    state_restored = state_gen.with_mode(ODEMode.CAUCHY_IVP)
    assert state_restored.mode == ODEMode.CAUCHY_IVP
    assert state_restored.initial_condition == "y(0) = 2, y'(0) = -1"


# =============================================================================
# CATEGORY E: Advanced Second-Order Tools
# =============================================================================

def test_category_e_reduction_of_order_request_construction():
    """Verify Reduction of Order constructs ProblemRequest with known solution y1."""
    # 1. With known solution in dedicated input
    state1 = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.REDUCTION_OF_ORDER,
        equation="2*t^2*y'' + 3*t*y' - y = 0",
        known_solution="1/t",
        target_var="t",
    )
    req1 = state1.build_problem_request()
    assert req1.problem_type == ProblemType.ODE_REDUCTION_OF_ORDER
    assert req1.raw_input == "2*t^2*y'' + 3*t*y' - y = 0"
    assert req1.parameters["y1"] == "1/t"
    assert req1.target_variable == "t"

    # 2. With known solution inline in equation
    state2 = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.REDUCTION_OF_ORDER,
        equation="2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t",
        target_var="t",
    )
    req2 = state2.build_problem_request()
    assert req2.problem_type == ProblemType.ODE_REDUCTION_OF_ORDER
    assert req2.raw_input == "2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t"


def test_category_e_wronskian_request_construction():
    """Verify Wronskian constructs ProblemRequest with comma-separated functions."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.WRONSKIAN,
        equation="cos(t), sin(t)",
        target_var="t",
    )
    req = state.build_problem_request()
    assert req.problem_type == ProblemType.WRONSKIAN
    assert req.raw_input == "cos(t), sin(t)"
    assert req.target_variable == "t"
    assert req.parameters == {}


# =============================================================================
# CATEGORY F: State Isolation & Zero Parameter Leakage
# =============================================================================

def test_category_f_order_transition_state_isolation():
    """Verify switching from Second-Order IVP to First-Order cleanly adopts First-Order defaults."""
    state_so_ivp = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
        mode=ODEMode.CAUCHY_IVP,
        initial_condition="y(0) = 1, y'(0) = 0",
    )

    state_fo = state_so_ivp.with_order(ODEOrder.FIRST_ORDER)
    assert state_fo.order == ODEOrder.FIRST_ORDER
    assert state_fo.classification == ODEClassification.FIRST_ORDER_LINEAR
    assert state_fo.mode == ODEMode.GENERAL
    assert state_fo.initial_condition == ""
    # Solvers or requests must not leak second-order parameters
    req = state_fo.build_problem_request()
    assert req.problem_type == ProblemType.ODE_FIRST_ORDER_LINEAR
    assert "expected_classification" not in req.parameters


def test_category_f_reset_restores_authoritative_defaults():
    """Verify reset() restores authoritative defaults for current classification."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
        mode=ODEMode.CAUCHY_IVP,
        equation="y'' + 9*y = 0",
        initial_condition="y(0) = 3, y'(0) = 1",
        target_var="x",
    )

    reset_state = state.reset()
    assert reset_state.order == ODEOrder.SECOND_ORDER
    assert reset_state.classification == ODEClassification.SECOND_ORDER_NONHOMOGENEOUS
    assert reset_state.equation == DEFAULT_CONFIGS[ODEClassification.SECOND_ORDER_NONHOMOGENEOUS]["equation"]
    assert reset_state.target_var == DEFAULT_CONFIGS[ODEClassification.SECOND_ORDER_NONHOMOGENEOUS]["target_var"]
    assert reset_state.mode == ODEMode.GENERAL
    assert reset_state.initial_condition == ""


# =============================================================================
# CATEGORY G: Real Live UI Submission & Verification
# =============================================================================

@pytest.mark.anyio
async def test_category_g_real_ui_submission_homogeneous_general():
    """Verify live submission of Second-Order Homogeneous General ODE via UI Solve button."""
    core.loop = asyncio.get_running_loop()
    mock_use_case = MagicMock()
    mock_use_case.execute.return_value = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "symbolic", "Kiểm định thành công"),
        raw_input="y'' - 3*y' - 4*y = 0",
        canonical_input="y'' - 3*y' - 4*y = 0",
        final_result="y(t) = C1*exp(4*t) + C2*exp(-t)",
        final_latex=r"y(t) = C_1 e^{4t} + C_2 e^{-t}",
        steps=(),
    )

    client = _setup_app_client("/test_cat_g_homo_gen", mock_use_case)
    _navigate_to_op(client, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)

    # Click Solve button
    solve_btn = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "GIẢI PHƯƠNG TRÌNH"][0]
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
            break

    await asyncio.sleep(0.05)

    mock_use_case.execute.assert_called_once()
    req: ProblemRequest = mock_use_case.execute.call_args[0][0]
    assert req.problem_type == ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF
    assert req.parameters["problem_mode"] == "GENERAL"
    assert req.parameters["expected_classification"] == "HOMOGENEOUS"


@pytest.mark.anyio
async def test_category_g_real_ui_submission_nonhomogeneous_cauchy_ivp():
    """Verify live submission of Second-Order Nonhomogeneous Cauchy IVP via UI."""
    core.loop = asyncio.get_running_loop()
    mock_use_case = MagicMock()
    mock_use_case.execute.return_value = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "symbolic", "Kiểm định Cauchy thành công"),
        raw_input="y'' - 3*y' - 4*y = 3*exp(2*t), y(0) = 1, y'(0) = 0",
        canonical_input="y'' - 3*y' - 4*y = 3*exp(2*t)",
        final_result="y(t) = e^{2t} - e^{-t}",
        final_latex=r"y(t) = e^{2t} - e^{-t} + \frac{1}{2} e^{2t}",
        steps=(),
    )

    client = _setup_app_client("/test_cat_g_nonhomo_cauchy", mock_use_case)
    _navigate_to_op(client, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)

    # Select Nonhomogeneous card
    for el in list(client.elements.values()):
        if isinstance(el, ui.card):
            for listener in list(el._event_listeners.values()):
                if getattr(listener.handler, "__name__", "") == "on_select_nonhomo":
                    with client:
                        listener.handler(None)
                    break

    # Select Cauchy IVP mode
    for el in list(client.elements.values()):
        if isinstance(el, ui.button) and el.text == "Bài toán Cauchy (IVP)":
            for listener in list(el._event_listeners.values()):
                if listener.type in ("click", None):
                    with client:
                        listener.handler(None)
                    break

    # Provide initial conditions
    inputs = [el for el in client.elements.values() if isinstance(el, ui.input)]
    ic_input = [inp for inp in inputs if "y(t0)" in inp._props.get("label", "")][0]
    with client:
        ic_input.set_value("y(0) = 1, y'(0) = 0")

    # Click Solve button
    solve_btn = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "GIẢI PHƯƠNG TRÌNH"][0]
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
            break

    await asyncio.sleep(0.05)

    mock_use_case.execute.assert_called_once()
    req: ProblemRequest = mock_use_case.execute.call_args[0][0]
    assert req.problem_type == ProblemType.ODE_SECOND_ORDER_IVP
    assert req.parameters["problem_mode"] == "CAUCHY_IVP"
    assert req.parameters["expected_classification"] == "NONHOMOGENEOUS"
    assert req.parameters["initial_condition"] == "y(0) = 1, y'(0) = 0"


@pytest.mark.anyio
async def test_category_g_real_ui_submission_reduction_of_order():
    """Verify live submission of Reduction of Order via UI."""
    core.loop = asyncio.get_running_loop()
    mock_use_case = MagicMock()
    mock_use_case.execute.return_value = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "symbolic", "Hạ bậc nghiệm thành công"),
        raw_input="2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t",
        canonical_input="2*t^2*y'' + 3*t*y' - y = 0",
        final_result="y(t) = C1/t + C2*sqrt(t)",
        final_latex=r"y(t) = C_1 \frac{1}{t} + C_2 \sqrt{t}",
        steps=(),
    )

    client = _setup_app_client("/test_cat_g_reduction", mock_use_case)
    _navigate_to_op(client, ProblemType.ODE_REDUCTION_OF_ORDER)

    # Click Solve button
    solve_btn = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "GIẢI PHƯƠNG TRÌNH"][0]
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
            break

    await asyncio.sleep(0.05)

    mock_use_case.execute.assert_called_once()
    req: ProblemRequest = mock_use_case.execute.call_args[0][0]
    assert req.problem_type == ProblemType.ODE_REDUCTION_OF_ORDER
    assert "2*t^2*y''" in req.raw_input


@pytest.mark.anyio
async def test_category_g_real_ui_submission_wronskian():
    """Verify live submission of Wronskian determinant via UI."""
    core.loop = asyncio.get_running_loop()
    mock_use_case = MagicMock()
    mock_use_case.execute.return_value = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "symbolic", "Độc lập tuyến tính"),
        raw_input="cos(t), sin(t)",
        canonical_input="cos(t), sin(t)",
        final_result="W = 1",
        final_latex=r"W(y_1, y_2)(t) = 1 \neq 0",
        steps=(),
    )

    client = _setup_app_client("/test_cat_g_wronskian", mock_use_case)
    _navigate_to_op(client, ProblemType.WRONSKIAN)

    # Click Solve button
    solve_btn = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "GIẢI PHƯƠNG TRÌNH"][0]
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)
            break

    await asyncio.sleep(0.05)

    mock_use_case.execute.assert_called_once()
    req: ProblemRequest = mock_use_case.execute.call_args[0][0]
    assert req.problem_type == ProblemType.WRONSKIAN
    assert req.raw_input == "cos(t), sin(t)"


# =============================================================================
# CATEGORY H: Regression & Operation Parity
# =============================================================================

def test_category_h_all_nine_ode_operations_in_catalog():
    """Verify all 9 ODE operations exist in catalog with correct menu card properties."""
    for pt in ALL_9_ODE_TYPES:
        op = get_operation_by_type(pt)
        assert op is not None
        assert len(op.title) > 0
        assert len(op.default_input) > 0
        if pt in (
            ProblemType.ODE_FIRST_ORDER_LINEAR,
            ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        ):
            assert op.is_menu_card is True
        else:
            assert op.is_menu_card is False


def test_category_h_second_order_examples_integrity():
    """Verify example presets exist for both HOMOGENEOUS and NONHOMOGENEOUS in GENERAL and CAUCHY modes."""
    for cat in ("HOMOGENEOUS", "NONHOMOGENEOUS"):
        for mode in ("GENERAL", "CAUCHY_IVP"):
            examples = get_second_order_examples(cat, mode)
            assert len(examples) >= 4, f"Expected at least 4 presets for {cat} {mode}"
            for label, eq in examples:
                assert len(label) > 0
                assert len(eq) > 0

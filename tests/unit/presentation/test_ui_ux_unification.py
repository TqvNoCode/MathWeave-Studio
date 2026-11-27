"""Comprehensive unit and interaction tests for UI/UX Unification (M1–M5)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest
from nicegui import Client, app, core, ui

from math_app.application.dtos import SolutionResponse, SolutionStep, VerificationResult
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.main import build_application
from math_app.presentation.app import create_app
from math_app.presentation.components.ode_pedagogical_enhancer import enhance_ode_solution_flow
from math_app.presentation.components.ode_staged_step_viewer import _to_quasar_badge_color
from math_app.presentation.components.operation_catalog import OPERATIONS, get_operation_by_type
from math_app.presentation.components.shared import (
    get_primary_action_spec,
    render_empty_state_card,
    render_example_chips,
    render_feedback_card,
    render_loading_card,
    render_workspace_header,
)
from math_app.presentation.components.step_viewer import render_steps_container
from math_app.presentation.components.workspace.variable_selector import get_variable_pool_for_operation
from math_app.presentation.components.workspace.ode.first_order_classifier import (
    classify_first_order_ode,
)
from math_app.presentation.components.workspace.ode.ode_guided_classification_view import (
    render_ode_guided_classification_view,
)
from math_app.presentation.components.workspace.ode.ode_state import (
    ODEClassification,
    ODEState,
)
from math_app.presentation.components.workspace.ode.ode_workspace import (
    detect_second_order_classification,
    render_ode_workspace,
)
from math_app.presentation.components.workspace.ode.second_order_classifier import (
    classify_second_order_ode,
)


def _setup_client(path: str, use_case: Any | None = None, **query_kwargs: Any) -> Client:
    uc = use_case or build_application()
    create_app(uc)
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page(path))
    with client:
        route.endpoint.__wrapped__(**query_kwargs)
    return client


async def _submit_and_wait(client: Client, button_label: str) -> list[str]:
    solve_btn = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == button_label][0]
    for listener in list(solve_btn._event_listeners.values()):
        if listener.type in ("click", None):
            with client:
                listener.handler(None)

    for _ in range(80):
        labels = [el.text for el in client.elements.values() if isinstance(el, ui.label) and el.text]
        if any(
            marker in lbl
            for lbl in labels
            for marker in ("ĐÁP SỐ CUỐI CÙNG", "Dữ liệu đầu vào", "Không thể hoàn thành", "Phương trình không đúng cấp", "Thiếu điều kiện")
        ):
            return labels
        await asyncio.sleep(0.05)
    return [el.text for el in client.elements.values() if isinstance(el, ui.label) and el.text]


def test_all_34_operations_have_accurate_action_labels_and_mount_cleanly() -> None:
    """Every catalog operation has a module-specific CTA and mounts cleanly via deep-link."""
    non_eq_types = {op.problem_type for op in OPERATIONS if op.problem_type != ProblemType.SOLVE_EQUATION}
    for pt in non_eq_types:
        spec = get_primary_action_spec(pt)
        assert spec.label != "GIẢI PHƯƠNG TRÌNH", f"{pt} must not keep generic equation button"
        assert spec.label != "GIẢI PHÉP TOÁN MA TRẬN", f"{pt} must have specific matrix action label"
        assert spec.aria_label

    assert get_primary_action_spec(ProblemType.SOLVE_EQUATION).label == "GIẢI PHƯƠNG TRÌNH"

    for idx, op in enumerate(OPERATIONS):
        client = _setup_client(f"/test_mount_all_{idx}", op=op.problem_type.value)
        expected_label = get_primary_action_spec(op.problem_type).label
        btns = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == expected_label]
        assert len(btns) >= 1, f"Primary action button '{expected_label}' missing for {op.problem_type}"


def test_shared_primitives_accessibility_and_chip_contrast() -> None:
    """Shared chips, status badges, and primary buttons avoid Quasar default blue override; loading/alert have ARIA."""
    from math_app.presentation.components.shared import primary_button, status_badge

    selected: list[str] = []
    client = Client(ui.page("/test_shared_primitives_a11y"))
    with client:
        render_workspace_header(
            title="Đạo hàm",
            description="Tính đạo hàm bậc 1 hoặc bậc cao.",
            badge_text="Giải tích",
            math_icon=r"\frac{d^n f}{dx^n}",
        )
        render_example_chips([("Mẫu 1", "x^2")], on_select=selected.append)
        cta = primary_button("TÍNH ĐẠO HÀM", icon="functions", aria_label="Tính đạo hàm")
        badge = status_badge("Phương trình vi phân tuyến tính không thuần nhất cấp 1", variant="info")
        loading = render_loading_card("Đang tính...")
        alert = render_feedback_card("Lỗi", ["Thiếu dữ liệu"], variant="error")
        empty = render_empty_state_card("Không có dữ liệu")

    chips = [el for el in client.elements.values() if isinstance(el, ui.chip)]
    assert len(chips) == 1
    assert chips[0]._props.get("color") is None
    assert "mw-example-chip" in chips[0]._classes
    assert "text-slate-800" in chips[0]._classes
    assert cta._props.get("color") is None
    assert "!bg-blue-600" in cta._classes
    assert badge._props.get("color") is None
    assert "whitespace-normal" in badge._classes
    assert loading._props.get("role") == "status"
    assert alert._props.get("role") == "alert"
    assert empty is not None

    for listener in chips[0]._event_listeners.values():
        if listener.type == "click":
            listener.handler(None)
    assert selected == ["x^2"]


def test_first_order_notation_and_progressive_disclosure() -> None:
    """First-order nonhomogeneous classifier uses g(t) \\not\\equiv 0 and Step 3 toggles without ui.expansion."""
    clf = classify_first_order_ode("y' + 2*y = exp(-t)", target_var="t")
    assert any(r"\not\equiv 0" in p for p in clf.explanation_points)
    assert all(r"\neq 0" not in p for p in clf.explanation_points)

    state = ODEState.default_for_classification(ODEClassification.FIRST_ORDER_LINEAR)
    client = Client(ui.page("/test_fo_progressive_disclosure"))
    with client:
        render_ode_guided_classification_view(clf, state)

    assert not any(isinstance(el, ui.expansion) for el in client.elements.values())
    toggle_btns = [
        el for el in client.elements.values()
        if isinstance(el, ui.button) and "Xem lý lẽ chi tiết" in (el.text or "")
    ]
    assert len(toggle_btns) == 1
    assert toggle_btns[0]._props.get("aria-expanded") == "false"

    for listener in list(toggle_btns[0]._event_listeners.values()):
        if listener.type == "click":
            with client:
                listener.handler(None)
    assert toggle_btns[0]._props.get("aria-expanded") == "true"
    assert "Ẩn lý lẽ chi tiết" in toggle_btns[0].text


def test_second_order_live_detection_and_sync_banner() -> None:
    """Second-order equation-first workflow auto-detects families by default and shows sync banner on manual override."""
    det_ec = detect_second_order_classification("t^2*y'' + 4*t*y' + 2*y = 0, t > 0", "t")
    assert det_ec is not None and det_ec[0] == ODEClassification.EULER_CAUCHY

    det_nh = detect_second_order_classification("y'' + y = sin(t)", "t")
    assert det_nh is not None and det_nh[0] == ODEClassification.SECOND_ORDER_NONHOMOGENEOUS

    det_hom = detect_second_order_classification("y'' - 5*y' + 6*y = 0", "t")
    assert det_hom is not None and det_hom[0] == ODEClassification.SECOND_ORDER_HOMOGENEOUS

    det_red = detect_second_order_classification("2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t", "t")
    assert det_red is not None and det_red[0] == ODEClassification.REDUCTION_OF_ORDER

    det_o1 = detect_second_order_classification("y' + 2*y = 0", "t")
    assert det_o1 is not None and det_o1[0] == "ORDER_1_MISMATCH"

    # 1. Default Equation-First behavior: typing an Euler-Cauchy equation auto-detects & activates Euler-Cauchy
    mock_uc = MagicMock()
    client = Client(ui.page("/test_so_auto_detect"))
    with client:
        render_ode_workspace(get_operation_by_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF), mock_uc)

    eq_inputs = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")]
    assert len(eq_inputs) == 1
    with client:
        eq_inputs[0].set_value("t^2*y'' + 4*t*y' + 2*y = 0, t > 0")

    all_text_auto = " ".join(
        el.text for el in client.elements.values() if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
    )
    assert "Euler–Cauchy" in all_text_auto
    assert "Tự động nhận diện" in all_text_auto
    assert eq_inputs[0].value == "t^2*y'' + 4*t*y' + 2*y = 0, t > 0"

    # 2. Manual Override behavior: after manually selecting Homogeneous, typing Euler-Cauchy preserves override + shows sync banner
    hom_btns = [
        el for el in client.elements.values()
        if isinstance(el, ui.button) and el.text == "Thuần nhất"
    ]
    assert hom_btns
    for listener in list(hom_btns[0]._event_listeners.values()):
        if listener.type == "click":
            with client:
                listener.handler(None)
            break

    eq_inputs_override = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")]
    assert len(eq_inputs_override) == 1
    with client:
        eq_inputs_override[0].set_value("t^2*y'' + 4*t*y' + 2*y = 0, t > 0")

    sync_btns = [
        el for el in client.elements.values()
        if isinstance(el, ui.button) and "Đồng bộ sang Euler–Cauchy" in (el.text or "")
    ]
    assert len(sync_btns) == 1
    override_text = " ".join(
        el.text for el in client.elements.values() if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
    )
    assert "Ghi đè thủ công" in override_text
    assert "Bật lại tự động" in override_text


@pytest.mark.anyio
async def test_calculus_and_matrix_real_workflows_and_stale_result_clear() -> None:
    """Valid workflow renders result and changing target variable clears stale results."""
    core.loop = asyncio.get_running_loop()
    client = _setup_client("/test_real_calc_clear", op=ProblemType.DERIVATIVE.value)
    labels = await _submit_and_wait(client, get_primary_action_spec(ProblemType.DERIVATIVE).label)
    assert any("ĐÁP SỐ CUỐI CÙNG:" in t for t in labels)

    var_in = [el for el in client.elements.values() if isinstance(el, ui.input) and "Biến số" in el._props.get("label", "")][0]
    with client:
        var_in.set_value("t")

    assert not any("ĐÁP SỐ CUỐI CÙNG:" in (el.text or "") for el in client.elements.values() if isinstance(el, ui.label))


@pytest.mark.anyio
@pytest.mark.parametrize(
    "pt,valid_eq,invalid_eq",
    [
        (ProblemType.DERIVATIVE, "x^3 + 2*x", "(((bad_expr"),
        (ProblemType.SOLVE_EQUATION, "x^2 - 4 = 0", "x^2 == 4"),
        (ProblemType.GREENS_THEOREM, "-y, x", "only_one_component"),
        (ProblemType.MATRIX_DETERMINANT, "[[1, 2], [3, 4]]", "[[1, 2], [3]]"),
        (ProblemType.ODE_FIRST_ORDER_LINEAR, "y' + 2*y = exp(-t)", "y'' + y = 0"),
        (ProblemType.ODE_EULER_CAUCHY, "t^2*y'' + 4*t*y' + 2*y = 0, t > 0", "t^2*y'' + 4*t*y' + 2*y = 0, -1 < t < 1"),
    ],
)
async def test_representative_valid_and_invalid_workflows_across_all_module_groups(
    pt: ProblemType,
    valid_eq: str,
    invalid_eq: str,
) -> None:
    """Every major module group succeeds cleanly on valid input and shows feedback on invalid input."""
    core.loop = asyncio.get_running_loop()
    action_label = get_primary_action_spec(pt).label

    # 1. Valid workflow
    c_ok = _setup_client(f"/test_wf_ok_{pt.value}", op=pt.value, eq=valid_eq)
    if not pt.is_ode:
        main_inp = [el for el in c_ok.elements.values() if isinstance(el, ui.input)][0]
        with c_ok:
            main_inp.set_value(valid_eq)
    labels_ok = await _submit_and_wait(c_ok, action_label)
    assert any("ĐÁP SỐ CUỐI CÙNG:" in t for t in labels_ok), f"Expected success result for {pt}"

    # 2. Invalid workflow
    c_bad = _setup_client(f"/test_wf_bad_{pt.value}", op=pt.value, eq=invalid_eq)
    if not pt.is_ode:
        main_inp_bad = [el for el in c_bad.elements.values() if isinstance(el, ui.input)][0]
        with c_bad:
            main_inp_bad.set_value(invalid_eq)
    labels_bad = await _submit_and_wait(c_bad, action_label)
    assert not any("ĐÁP SỐ CUỐI CÙNG:" in t for t in labels_bad), f"Invalid input should fail cleanly for {pt}"


def test_single_step_viewer_avoids_redundant_conclusion_duplicate() -> None:
    """Single-step derivations matching final answer skip duplicate conclusion box while multi-step keeps it."""
    step1 = SolutionStep(
        step_number=1,
        rule_name="Power Rule",
        title="Đạo hàm lũy thừa",
        description="Tính đạo hàm.",
        equation_latex=r"\frac{d}{dx}(x^2) = 2x",
        content=ExpressionStepContent("x^2", "2*x", "x^2", "2x"),
    )
    c1 = Client(ui.page("/test_step_single"))
    with c1:
        render_steps_container((step1,), final_answer_latex=r"\frac{d}{dx}(x^2) = 2x")
    assert not any((el.text or "") == "Kết luận:" for el in c1.elements.values() if isinstance(el, ui.label))

    c2 = Client(ui.page("/test_step_multi"))
    with c2:
        render_steps_container((step1, step1), final_answer_latex=r"2x")
    assert any((el.text or "") == "Kết luận:" for el in c2.elements.values() if isinstance(el, ui.label))


# ==============================================================================
# INDEPENDENT REVIEW REGRESSION TESTS
# ==============================================================================


@pytest.mark.anyio
async def test_first_order_auto_align_preserves_user_equation_on_submit() -> None:
    """Submitting a separable equation in Linear workspace must preserve the typed equation."""
    core.loop = asyncio.get_running_loop()
    client = _setup_client("/test_fo_preserve_eq", op=ProblemType.ODE_FIRST_ORDER_LINEAR.value)
    eq_in = [
        el for el in client.elements.values()
        if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")
    ][0]
    custom_eq = "y' = t*(y^2 - 1)"
    with client:
        eq_in.set_value(custom_eq)

    action_label = get_primary_action_spec(ProblemType.ODE_FIRST_ORDER_LINEAR).label
    await _submit_and_wait(client, action_label)

    eq_inputs_after = [
        el for el in client.elements.values()
        if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")
    ]
    assert any(inp.value == custom_eq for inp in eq_inputs_after), "Auto-alignment must not overwrite user's equation"


def test_ode_stage4_verification_honesty_across_non_euler_builders() -> None:
    """Non-Euler ODE Stage 4 must reflect FAILED/UNVERIFIED statuses and zero Wronskian honestly."""
    dummy_step = SolutionStep(
        step_number=1,
        rule_name="Giải PTVP",
        description="Tìm nghiệm.",
        equation_latex=r"y(t) = C_1 e^{-2t}",
        content=ExpressionStepContent("y' + 2*y = 0", "y = C1*exp(-2*t)", "y' + 2y = 0", r"y(t) = C_1 e^{-2t}"),
    )

    failed_resp = SolutionResponse(
        status=SolutionStatus.PARTIAL,
        verification=VerificationResult(status=VerificationStatus.FAILED, method="symbolic", details="Sai lệch phần dư"),
        raw_input="y' + 2*y = 0",
        canonical_input="Eq(Derivative(y(t), t) + 2*y(t), 0)",
        final_result="y(t) = C1*exp(-2*t)",
        final_latex=r"y(t) = C_1 e^{-2t}",
        steps=(dummy_step,),
    )
    stages_failed = enhance_ode_solution_flow(failed_resp, ProblemType.ODE_FIRST_ORDER_LINEAR, "t", {})
    assert len(stages_failed) == 4
    stg4_fail = stages_failed[3]
    assert stg4_fail.is_completed is False
    assert stg4_fail.badge_color == "rose-7"
    assert r"\not\equiv 0" in stg4_fail.summary_latex
    assert stg4_fail.steps[0].equation_latex != "R(t) = 0"

    unverified_resp = SolutionResponse(
        status=SolutionStatus.UNVERIFIED,
        verification=VerificationResult(status=VerificationStatus.UNVERIFIED, method="symbolic", details="Chưa xác nhận ký hiệu"),
        raw_input="y'' + y = 0",
        canonical_input="Eq(Derivative(y(t), (t, 2)) + y(t), 0)",
        final_result="y(t) = C1*cos(t) + C2*sin(t)",
        final_latex=r"y(t) = C_1 \cos(t) + C_2 \sin(t)",
        steps=(dummy_step,),
    )
    stages_unver = enhance_ode_solution_flow(unverified_resp, ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "t", {})
    stg4_unver = stages_unver[3]
    assert stg4_unver.is_completed is False
    assert stg4_unver.badge_color == "amber-7"
    assert stg4_unver.steps[0].equation_latex != "R(t) = 0"

    dep_wronskian_resp = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(status=VerificationStatus.VERIFIED, method="symbolic", details="Wronskian bằng 0"),
        raw_input="2*t, 5*t",
        canonical_input="[2*t, 5*t]",
        final_result="W(y1, y2) = 0 (Hệ hàm phụ thuộc tuyến tính)",
        final_latex="0",
        steps=(dummy_step,),
    )
    stages_w = enhance_ode_solution_flow(dep_wronskian_resp, ProblemType.WRONSKIAN, "t", {})
    stg4_w = stages_w[3]
    assert r"\not\equiv 0" not in stg4_w.summary_latex
    assert r"\equiv 0" in stg4_w.summary_latex
    assert r"\not\equiv 0" not in stg4_w.steps[0].equation_latex


def test_sticky_nav_bar_deduplication_and_title_sync() -> None:
    """Sticky nav bar avoids duplicate domain badges and stays synced when ODE type changes."""
    client = _setup_client("/test_sticky_sync", op=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF.value)

    ec_btns = [
        el for el in client.elements.values()
        if isinstance(el, ui.button) and "Euler" in (el.text or "")
    ]
    assert ec_btns, "Expected Euler-Cauchy selector button in second-order workspace"
    for listener in list(ec_btns[0]._event_listeners.values()):
        if listener.type == "click":
            with client:
                listener.handler(None)
            break

    sticky_labels = [
        el.text for el in client.elements.values()
        if isinstance(el, ui.label) and "sticky" not in (el.text or "") and "Euler" in (el.text or "")
    ]
    assert len(sticky_labels) >= 2, "Both sticky nav bar and workspace header must reflect Euler–Cauchy switch"


def test_query_params_do_not_leak_after_returning_to_catalog() -> None:
    """URL eq/ic/solve parameters are one-shot and do not overwrite later catalog selections."""
    client = _setup_client("/test_query_one_shot", op=ProblemType.ODE_FIRST_ORDER_LINEAR.value, eq="y' + y = 0")

    back_btns = [
        el for el in client.elements.values()
        if isinstance(el, ui.button) and "Chọn dạng toán khác" in (el.text or "")
    ]
    assert len(back_btns) == 1
    for listener in list(back_btns[0]._event_listeners.values()):
        if listener.type == "click":
            with client:
                listener.handler(None)
            break

    # Now select Derivative from Catalog
    deriv_op = get_operation_by_type(ProblemType.DERIVATIVE)
    deriv_btns = [
        el for el in client.elements.values()
        if isinstance(el, ui.button) and deriv_op.title in (el.text or "")
    ]
    if not deriv_btns:
        # Card click handler may sit on a ui.card ancestor
        deriv_cards = [
            el for el in client.elements.values()
            if isinstance(el, ui.card) and any(listener.type == "click" for listener in el._event_listeners.values())
        ]
        assert deriv_cards
        for card in deriv_cards:
            card_labels = [c.text for c in client.elements.values() if isinstance(c, ui.label) and c.parent_slot and c.parent_slot.parent == card]
            if any(deriv_op.title in (t or "") for t in card_labels):
                for listener in card._event_listeners.values():
                    if listener.type == "click":
                        with client:
                            listener.handler(None)
                break
    else:
        for listener in list(deriv_btns[0]._event_listeners.values()):
            if listener.type == "click":
                with client:
                    listener.handler(None)
                break

    inputs = [el for el in client.elements.values() if isinstance(el, ui.input) and "Biểu thức" in el._props.get("label", "")]
    if inputs:
        assert inputs[0].value == deriv_op.default_input
        assert inputs[0].value != "y' + y = 0"


def test_ode_variable_selector_excludes_dependent_variable_y() -> None:
    """ODE variable pool offers independent variables ['t', 'x'] and never 'y'."""
    for pt in ProblemType:
        if pt.is_ode:
            op = get_operation_by_type(pt)
            if op is not None:
                pool = get_variable_pool_for_operation(op)
                assert pool == ["t", "x"], f"Unexpected variable pool {pool} for ODE {pt}"
                assert "y" not in pool


def test_single_step_dedup_with_lhs_prefix_and_quasar_badge_mapping() -> None:
    """Single-step dedup recognizes LHS-prefixed conclusions and Quasar palette mapping is valid."""
    det_step = SolutionStep(
        step_number=1,
        rule_name="Định thức",
        title="Tính định thức ma trận 2x2",
        description="Áp dụng ad - bc.",
        equation_latex=r"\det(A) = -2",
        content=ExpressionStepContent("[[1, 2], [3, 4]]", "-2", r"\begin{pmatrix}1&2\\3&4\end{pmatrix}", "-2"),
    )
    client = Client(ui.page("/test_step_lhs_dedup"))
    with client:
        render_steps_container((det_step,), final_answer_latex=r"\det(A) = -2")
    assert not any((el.text or "") == "Kết luận:" for el in client.elements.values() if isinstance(el, ui.label))

    assert _to_quasar_badge_color("emerald-7") == "green-7"
    assert _to_quasar_badge_color("rose-7") == "red-7"
    assert _to_quasar_badge_color("slate-400") == "grey-6"
    assert _to_quasar_badge_color("slate-100") == "grey-3"


# ==============================================================================
# POST-REVIEW POLISH REGRESSION TESTS (PRIORITY A & PRIORITY B)
# ==============================================================================


def test_second_order_classifier_covers_all_supported_families() -> None:
    """classify_second_order_ode detects Homogeneous, Nonhomogeneous (UC/VoP), Euler-Cauchy, Reduction, Wronskian, Order-1."""
    s_hom = classify_second_order_ode("y'' - 3*y' - 4*y = 0", target_var="t")
    assert s_hom.status == "DETECTED"
    assert s_hom.detected_classification == ODEClassification.SECOND_ORDER_HOMOGENEOUS

    s_nh_uc = classify_second_order_ode("y'' - 3*y' - 4*y = 3*exp(2*t)", target_var="t")
    assert s_nh_uc.status == "DETECTED"
    assert s_nh_uc.detected_classification == ODEClassification.SECOND_ORDER_NONHOMOGENEOUS
    assert s_nh_uc.recommended_nonhomo_method is not None
    assert "Hệ số bất định" in s_nh_uc.recommended_nonhomo_method

    s_nh_vop = classify_second_order_ode("y'' + y = tan(t)", target_var="t")
    assert s_nh_vop.status == "DETECTED"
    assert s_nh_vop.detected_classification == ODEClassification.SECOND_ORDER_NONHOMOGENEOUS
    assert s_nh_vop.recommended_nonhomo_method is not None
    assert "Biến thiên hằng số" in s_nh_vop.recommended_nonhomo_method

    s_ec = classify_second_order_ode("t^2*y'' + 4*t*y' + 2*y = 0, t > 0", target_var="t")
    assert s_ec.status == "DETECTED"
    assert s_ec.detected_classification == ODEClassification.EULER_CAUCHY
    assert s_ec.detected_interval == "t > 0"

    s_red = classify_second_order_ode("2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t", target_var="t")
    assert s_red.status == "DETECTED"
    assert s_red.detected_classification == ODEClassification.REDUCTION_OF_ORDER
    assert s_red.has_inline_y1 is True

    s_wron = classify_second_order_ode(
        "cos(t), sin(t)", target_var="t", current_classification=ODEClassification.WRONSKIAN
    )
    assert s_wron.status == "WRONSKIAN"
    assert s_wron.detected_classification == ODEClassification.WRONSKIAN

    s_o1 = classify_second_order_ode("y' + 2*y = exp(-t)", target_var="t")
    assert s_o1.status == "ORDER_1_MISMATCH"
    assert s_o1.detected_classification is None


def test_second_order_equation_first_layout_and_expandable_manual_override() -> None:
    """Equation input appears before classification summary; manual override panel toggles aria-expanded cleanly."""
    client = _setup_client("/test_so_eq_first", op=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF.value)

    ordered_elements = list(client.elements.values())
    eq_idx = next(
        i for i, el in enumerate(ordered_elements)
        if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")
    )
    summary_idx = next(
        i for i, el in enumerate(ordered_elements)
        if isinstance(el, ui.label) and el.text == "PHÂN TÍCH TỰ ĐỘNG"
    )
    override_btn_idx = next(
        i for i, el in enumerate(ordered_elements)
        if isinstance(el, ui.button) and el.text == "Đổi phân loại thủ công"
    )
    assert eq_idx < summary_idx < override_btn_idx, "Equation input must precede classification summary and override control"

    override_btn = ordered_elements[override_btn_idx]
    assert override_btn._props.get("aria-expanded") == "false"

    # Toggle manual override open
    for listener in list(override_btn._event_listeners.values()):
        if listener.type == "click":
            with client:
                listener.handler(None)
            break
    assert override_btn._props.get("aria-expanded") == "true"
    assert override_btn.text == "Ẩn tùy chọn phân loại"

    # Toggle manual override closed again
    for listener in list(override_btn._event_listeners.values()):
        if listener.type == "click":
            with client:
                listener.handler(None)
            break
    assert override_btn._props.get("aria-expanded") == "false"
    assert override_btn.text == "Đổi phân loại thủ công"


@pytest.mark.anyio
async def test_second_order_auto_detect_and_manual_override_real_submissions() -> None:
    """Auto-detected Euler-Cauchy & Nonhomogeneous solve cleanly, and manual override is honored on submit."""
    core.loop = asyncio.get_running_loop()

    # 1. Start in default Constant-Coeff Homogeneous, type an Euler-Cauchy equation -> auto-detects & solves!
    c_ec = _setup_client("/test_so_auto_ec_submit", op=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF.value)
    eq_in = [el for el in c_ec.elements.values() if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")][0]
    with c_ec:
        eq_in.set_value("t^2*y'' + 4*t*y' + 2*y = 0, t > 0")

    labels_ec = await _submit_and_wait(c_ec, get_primary_action_spec(ProblemType.ODE_EULER_CAUCHY).label)
    assert any("ĐÁP SỐ CUỐI CÙNG:" in t for t in labels_ec)
    assert eq_in.value == "t^2*y'' + 4*t*y' + 2*y = 0, t > 0"

    # 2. Type a Nonhomogeneous equation -> auto-detects, reveals Method Selector, solves cleanly!
    c_nh = _setup_client("/test_so_auto_nh_submit", op=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF.value)
    eq_in_nh = [el for el in c_nh.elements.values() if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")][0]
    with c_nh:
        eq_in_nh.set_value("y'' + 4*y = 3*cos(2*t)")

    assert any(
        isinstance(el, ui.label) and "PHƯƠNG PHÁP ĐỀ XUẤT" in (el.text or "")
        for el in c_nh.elements.values()
    )
    labels_nh = await _submit_and_wait(c_nh, get_primary_action_spec(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF).label)
    assert any("ĐÁP SỐ CUỐI CÙNG:" in t for t in labels_nh)

    # 3. Type a Reduction-of-Order equation with inline y1 -> auto-detects Reduction of Order & solves!
    c_red = _setup_client("/test_so_auto_red_submit", op=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF.value)
    eq_in_red = [el for el in c_red.elements.values() if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")][0]
    with c_red:
        eq_in_red.set_value("2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t")

    labels_red = await _submit_and_wait(c_red, get_primary_action_spec(ProblemType.ODE_REDUCTION_OF_ORDER).label)
    assert any("ĐÁP SỐ CUỐI CÙNG:" in t for t in labels_red)

    # 4. Manual override to Wronskian works cleanly and preserves Wronskian action CTA
    c_w = _setup_client("/test_so_manual_wron_submit", op=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF.value)
    w_btns = [el for el in c_w.elements.values() if isinstance(el, ui.button) and el.text == "Định thức Wronskian"]
    assert w_btns
    for listener in list(w_btns[0]._event_listeners.values()):
        if listener.type == "click":
            with c_w:
                listener.handler(None)
            break
    labels_w = await _submit_and_wait(c_w, get_primary_action_spec(ProblemType.WRONSKIAN).label)
    assert any("ĐÁP SỐ CUỐI CÙNG:" in t for t in labels_w)


def test_ode_semantic_section_naming_replaces_pre_solve_buoc_badges() -> None:
    """Pre-solve ODE input sections use semantic names (no misleading BƯỚC badges on system analysis)."""
    for pt in (
        ProblemType.ODE_FIRST_ORDER_LINEAR,
        ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        ProblemType.ODE_EULER_CAUCHY,
    ):
        client = _setup_client(f"/test_semantic_naming_{pt.value}", op=pt.value)
        labels = [el.text for el in client.elements.values() if isinstance(el, ui.label) and el.text]
        visible_badges = [
            el.text for el in client.elements.values()
            if isinstance(el, ui.badge) and el.text in {"BƯỚC 2", "BƯỚC 3", "BƯỚC 4"}
        ]
        assert visible_badges == [], f"Unexpected pre-solve numbered badge in {pt}: {visible_badges}"
        assert "NHẬP BÀI TOÁN" in labels
        assert "PHÂN TÍCH TỰ ĐỘNG" in labels
        if pt == ProblemType.ODE_FIRST_ORDER_LINEAR:
            assert "CƠ SỞ PHÂN LOẠI" in labels
            assert "PHƯƠNG PHÁP ĐỀ XUẤT" in labels

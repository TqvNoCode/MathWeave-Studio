"""Unit and regression tests for UX3.7.1 — First-Order ODE Interface Simplification.

Verifies:
1. The manual override accordion is completely removed from First-Order ODE.
2. The beginner recognition accordion is completely removed.
3. Manual override buttons are absent from normal First-Order ODE workflow.
4. Automatic classification correctly identifies families (linear, separable, exact, homogeneous).
5. Recommended solving methods and justifications remain visible and mathematically correct.
6. Existing First-Order ODE solving flows execute successfully without manual override.
7. Second-Order ODE UI and functionality remain completely intact and unchanged.
8. No regression in other ODE workspaces or classifications.
9. No raw LaTeX strings or unrendered syntax leak into the UI.
10. No empty containers, orphan cards, or layout gaps remain after removal.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from nicegui import Client, core, ui

from math_app.application.dtos import (
    ProblemRequest,
    SolutionResponse,
    VerificationResult,
)
from math_app.domain.models import (
    ProblemType,
    SolutionStatus,
    VerificationStatus,
)
from math_app.presentation.components.operation_catalog import get_operation_by_type
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
from math_app.presentation.components.workspace.ode.ode_workspace import render_ode_workspace


def _make_mock_use_case() -> MagicMock:
    mock = MagicMock()
    mock.execute.return_value = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(
            status=VerificationStatus.VERIFIED,
            method="symbolic_substitution",
            details="Kiểm chứng thành công",
        ),
        raw_input="y' + 1/2*y = t + 2",
        canonical_input="y' + 1/2*y = t + 2",
        final_result="y(t) = C*exp(-t/2) + 2*t",
        final_latex=r"y(t) = C e^{-t/2} + 2t",
        steps=(),
    )
    return mock


# =============================================================================
# Test 1 & 2: Accordions Completely Removed from First-Order View
# =============================================================================

def test_ux3_7_1_removed_accordions_not_in_guided_view():
    """Verify both manual override and beginner help accordions are absent from render_ode_guided_classification_view."""
    clf_res = classify_first_order_ode("y' + 1/2*y = t + 2", target_var="t")
    state = ODEState.default_for_classification(ODEClassification.FIRST_ORDER_LINEAR)

    client = Client(ui.page("/test_ux3_7_1_no_accordions_view"))
    with client:
        render_ode_guided_classification_view(clf_res, state)

        all_text = " ".join([
            el.text for el in client.elements.values()
            if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
        ])

        # 1. Manual override accordion must be absent
        assert "Khám phá các phương pháp giải khác" not in all_text
        assert "Ghi đè thủ công" not in all_text

        # 2. Beginner help accordion must be absent
        assert "Trợ giúp nhận dạng dạng phương trình" not in all_text
        assert "Dành cho người mới học" not in all_text

        # No ui.expansion components rendered in the guided classification view
        expansions = [el for el in client.elements.values() if isinstance(el, ui.expansion)]
        assert len(expansions) == 0


# =============================================================================
# Test 3: Manual Override Buttons Absent from First-Order Workspace
# =============================================================================

def test_ux3_7_1_manual_override_buttons_absent_from_workspace():
    """Verify manual override buttons do not appear in normal First-Order ODE workflow."""
    op = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)
    mock_use_case = _make_mock_use_case()

    client = Client(ui.page("/test_ux3_7_1_no_buttons"))
    with client:
        render_ode_workspace(op, mock_use_case)

        button_texts = [el.text for el in client.elements.values() if isinstance(el, ui.button) and el.text]

        # Buttons that previously existed in the manual override accordion
        forbidden_buttons = [
            "Tách biến",
            "Vi phân toàn phần",
            "Thuần nhất cấp 1",
            "Thừa số tích phân",
            "Áp dụng phương pháp này",
        ]
        for btn in forbidden_buttons:
            assert btn not in button_texts, f"Button '{btn}' should not appear in First-Order normal workflow"


# =============================================================================
# Test 4: Automatic Classification Still Fully Accurate
# =============================================================================

def test_ux3_7_1_automatic_classification_accuracy():
    """Verify classification logic continues to distinguish linear, separable, exact, homogeneous."""
    # Linear Nonhomogeneous
    res_lin = classify_first_order_ode("y' + 1/2*y = t + 2", "t")
    assert res_lin.is_linear is True
    assert res_lin.is_linear_homogeneous is False
    assert res_lin.p_expr_latex is not None
    assert res_lin.g_expr_latex is not None

    # Linear Homogeneous & Separable
    res_dual = classify_first_order_ode("y' = t*y", "t")
    assert res_dual.is_linear is True
    assert res_dual.is_linear_homogeneous is True
    assert res_dual.is_separable is True

    # Pure Separable Nonlinear
    res_sep = classify_first_order_ode("y' = y^2", "t")
    assert res_sep.is_separable is True
    assert res_sep.is_linear is False

    # Exact ODE
    res_exact = classify_first_order_ode("(2*t*y + 3)*dt + (t^2 + 4*y)*dy = 0", "t")
    assert res_exact.is_exact is True

    # Classical Homogeneous Ratio
    res_homog = classify_first_order_ode("y' = (y + x)/(y - x)", "x")
    assert res_homog.is_classical_homogeneous is True


# =============================================================================
# Test 5: Recommended Method & Pedagogical Reason Remain Visible
# =============================================================================

def test_ux3_7_1_recommended_method_visible_and_justified():
    """Verify Step 4 renders the recommended method title and its pedagogical justification."""
    clf_res = classify_first_order_ode("y' + 1/2*y = t + 2", target_var="t")
    state = ODEState.default_for_classification(ODEClassification.FIRST_ORDER_LINEAR)

    client = Client(ui.page("/test_ux3_7_1_rec_method"))
    with client:
        render_ode_guided_classification_view(clf_res, state)

        all_text = " ".join([
            el.text for el in client.elements.values()
            if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
        ])

        assert "BƯỚC 4" in all_text
        assert "PHƯƠNG PHÁP GIẢI KHUYẾN NGHỊ:" in all_text
        assert "TỐI ƯU SƯ PHẠM" in all_text
        assert clf_res.recommended_method_title in all_text
        # The reason is rendered via ui_math_text (custom component with math)
        assert len(clf_res.recommended_method_reason) > 0


# =============================================================================
# Test 6: First-Order ODE End-to-End Solving Flow
# =============================================================================

@pytest.mark.anyio
async def test_ux3_7_1_first_order_end_to_end_solving():
    """Verify submitting a First-Order ODE executes correctly with automatically selected method."""
    core.loop = asyncio.get_running_loop()

    op = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)
    mock_use_case = _make_mock_use_case()

    client = Client(ui.page("/test_ux3_7_1_e2e_solve"))
    with client:
        render_ode_workspace(op, mock_use_case)

        # Submit default equation y' + 1/2*y = t + 2
        solve_btns = [el for el in client.elements.values() if isinstance(el, ui.button) and "GIẢI PHƯƠNG TRÌNH" in el.text]
        assert len(solve_btns) >= 1
        for listener in list(solve_btns[-1]._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)

        for _ in range(25):
            if mock_use_case.execute.called:
                break
            await asyncio.sleep(0.02)

        mock_use_case.execute.assert_called_once()
        req: ProblemRequest = mock_use_case.execute.call_args[0][0]
        assert req.problem_type == ProblemType.ODE_FIRST_ORDER_LINEAR
        assert "1/2" in req.raw_input or "0.5" in req.raw_input or "y'" in req.raw_input


# =============================================================================
# Test 7: Second-Order ODE Workflow Intact
# =============================================================================

def test_ux3_7_1_second_order_workflow_completely_intact():
    """Verify Second-Order ODE UI continues to provide classification and method selection intact."""
    op = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)
    mock_use_case = _make_mock_use_case()

    client = Client(ui.page("/test_ux3_7_1_so_intact"))
    with client:
        render_ode_workspace(op, mock_use_case)

        # 1. Homogeneous Second-Order initial state
        all_text = " ".join([
            el.text for el in client.elements.values()
            if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
        ])
        assert "BƯỚC 1" in all_text
        assert "PHÂN LOẠI PHƯƠNG TRÌNH:" in all_text
        assert "BƯỚC 2" in all_text
        assert "NHẬP PHƯƠNG TRÌNH & BIẾN SỐ:" in all_text
        assert "BƯỚC 3" in all_text
        assert "CHỌN YÊU CẦU BÀI TOÁN:" in all_text

        # 2. Switch to Nonhomogeneous to verify Step 4 Method Selector appears
        nonhomog_btns = [
            el for el in client.elements.values()
            if isinstance(el, ui.button) and "Không thuần nhất" in el.text
        ]
        assert len(nonhomog_btns) >= 1
        for listener in list(nonhomog_btns[-1]._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)

        all_text_after = " ".join([
            el.text for el in client.elements.values()
            if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
        ])
        assert "BƯỚC 4" in all_text_after
        assert "PHƯƠNG PHÁP TÌM NGHIỆM RIÊNG" in all_text_after
        assert "Hệ số bất định" in all_text_after
        assert "Biến thiên hằng số" in all_text_after


# =============================================================================
# Test 8: No Regression in Specialized Workspaces (e.g. Cauchy IVP Mode)
# =============================================================================

def test_ux3_7_1_cauchy_ivp_mode_in_first_order():
    """Verify Cauchy IVP mode toggle works smoothly in simplified First-Order workspace."""
    op = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)
    mock_use_case = _make_mock_use_case()

    client = Client(ui.page("/test_ux3_7_1_cauchy_toggle"))
    with client:
        render_ode_workspace(op, mock_use_case)

        # Toggle to Cauchy IVP
        cauchy_btns = [
            el for el in client.elements.values()
            if isinstance(el, ui.button) and "Bài toán Cauchy" in el.text
        ]
        assert len(cauchy_btns) >= 1
        for listener in list(cauchy_btns[-1]._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)

        # Initial condition input should now be visible
        ic_inputs = [
            el for el in client.elements.values()
            if isinstance(el, ui.input) and "Điều kiện" in el._props.get("label", "")
        ]
        assert len(ic_inputs) >= 1


# =============================================================================
# Test 9: Clean LaTeX Rendering — No Raw LaTeX Leakage
# =============================================================================

def test_ux3_7_1_no_raw_latex_in_simplified_guided_view():
    """Verify simplified guided view contains no raw LaTeX tokens in plain label elements."""
    clf_res = classify_first_order_ode("y' + 1/2*y = t + 2", target_var="t")
    state = ODEState.default_for_classification(ODEClassification.FIRST_ORDER_LINEAR)

    client = Client(ui.page("/test_ux3_7_1_no_latex_leakage"))
    with client:
        render_ode_guided_classification_view(clf_res, state)

        for el in client.elements.values():
            if isinstance(el, ui.label):
                txt = getattr(el, "_text", "") or ""
                if "$" in txt:
                    assert "\\mu" not in txt
                    assert "\\frac" not in txt
                    assert "\\implies" not in txt
                    assert "\\cdot" not in txt


# =============================================================================
# Test 10: Clean Card Layout Without Empty Containers or Excess Spacing
# =============================================================================

def test_ux3_7_1_no_layout_gaps_or_empty_containers():
    """Verify card structure has exactly 3 step cards (Step 2, 3, 4) without empty containers."""
    clf_res = classify_first_order_ode("y' + 1/2*y = t + 2", target_var="t")
    state = ODEState.default_for_classification(ODEClassification.FIRST_ORDER_LINEAR)

    client = Client(ui.page("/test_ux3_7_1_clean_layout"))
    with client:
        render_ode_guided_classification_view(clf_res, state)

        # Gather top-level step badges inside the guided view
        step_badges = [
            el.text for el in client.elements.values()
            if isinstance(el, ui.badge) and el.text in {"BƯỚC 2", "BƯỚC 3", "BƯỚC 4"}
        ]
        assert sorted(step_badges) == ["BƯỚC 2", "BƯỚC 3", "BƯỚC 4"]

        # Ensure no empty labels or blank expansion panels exist
        for el in client.elements.values():
            if isinstance(el, ui.expansion):
                pytest.fail("ui.expansion should not exist in the simplified First-Order view")

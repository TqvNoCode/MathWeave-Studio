"""Comprehensive integration test suite for UX3.6:
First-Order ODE Guided Classification & Intelligent Method Selection.

Verifies:
1. Automatic classification rendering for Linear Homogeneous (y' + 2*y = 0).
2. Automatic classification rendering for Linear Nonhomogeneous (y' + 2*y = exp(-t))
   with reference homogeneous counterpart card.
3. Dual classification rendering for y' = t*y (Linear Homogeneous + Separable badges).
4. Separable nonlinear rendering (y' = y*(1 - y)) with factor extraction and method.
5. Classical homogeneous ratio rendering (y' = (y + x)/(y - x)) with y = v*x substitution.
6. Exact differential equation rendering ((2*t*y + 3)*dt + (t^2 + 4*y)*dy = 0)
   with partial derivatives ∂M/∂y == ∂N/∂t.
7. Non-exact differential equation ((3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0) failing exactness test
   and recommending integrating factor μ.
8. Second-order ODE in first-order workspace (y'' + 4*y = 4*t) rendering amber
   order mismatch card with "Chuyển sang PTVP cấp 2" action button.
9. Manual classification override and alternative method selection preserving equation.
10. General solution vs Cauchy IVP modes working cleanly in guided workflow.
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
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.presentation.components.operation_catalog import (
    get_operation_by_type,
)
from math_app.presentation.components.workspace.ode import (
    ODEClassification,
    ODEOrder,
    render_ode_workspace,
)
from math_app.presentation.components.workspace.ode.first_order_classifier import (
    classify_first_order_ode,
)
from math_app.presentation.components.workspace.ode.ode_guided_classification_view import (
    render_ode_guided_classification_view,
)
from math_app.presentation.components.workspace.ode.ode_state import ODEState


def _make_mock_use_case():
    mock = MagicMock()
    mock.execute.return_value = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(
            status=VerificationStatus.VERIFIED,
            method="symbolic_substitution",
            details="Kiểm chứng thành công",
        ),
        raw_input="y' + 2*y = 0",
        canonical_input="y' + 2*y = 0",
        final_result="y(t) = C*exp(-2*t)",
        final_latex=r"y(t) = C e^{-2t}",
        steps=(),
    )
    return mock


# =============================================================================
# Test 1: Linear Homogeneous Rendering
# =============================================================================

def test_ux3_6_linear_homogeneous_rendering():
    """Verify linear homogeneous ODE displays correct badges, p(t), g(t)=0, and no reference counterpart."""
    clf = classify_first_order_ode("y' + 2*y = 0", "t")
    state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.FIRST_ORDER_LINEAR,
        equation="y' + 2*y = 0",
        target_var="t",
    )

    client = Client(ui.page("/test_ux3_6_lin_homog"))
    with client:
        render_ode_guided_classification_view(
            result=clf,
            state=state,
            on_select_classification=MagicMock(),
        )

        elements_text = [
            el.text for el in client.elements.values()
            if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
        ]
        all_text = " ".join(elements_text)

        assert clf.is_linear is True
        assert clf.is_linear_homogeneous is True
        assert "tuyến tính thuần nhất" in clf.primary_title.lower()
        assert "p(t)" in all_text or "Hệ số" in all_text
        # Reference counterpart card must NOT appear for already homogeneous ODE
        assert "Đối chứng sư phạm: Phương trình thuần nhất liên kết" not in all_text


# =============================================================================
# Test 2: Linear Nonhomogeneous with Reference Counterpart
# =============================================================================

def test_ux3_6_linear_nonhomogeneous_rendering_with_reference_counterpart():
    """Verify linear nonhomogeneous ODE displays pedagogical reference homogeneous counterpart card."""
    clf = classify_first_order_ode("y' + 2*y = exp(-t)", "t")
    state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.FIRST_ORDER_LINEAR,
        equation="y' + 2*y = exp(-t)",
        target_var="t",
    )

    client = Client(ui.page("/test_ux3_6_lin_nonhomog"))
    with client:
        render_ode_guided_classification_view(
            result=clf,
            state=state,
            on_select_classification=MagicMock(),
        )

        elements_text = [
            el.text for el in client.elements.values()
            if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
        ]
        all_text = " ".join(elements_text)

        assert clf.is_linear is True
        assert clf.is_linear_homogeneous is False
        assert "không thuần nhất" in clf.primary_title.lower()
        # Reference counterpart MUST be present
        assert "Đối chứng sư phạm: Phương trình thuần nhất liên kết" in all_text
        assert "triệt tiêu hàm tự do vế phải" in all_text
        assert clf.reference_homogeneous_latex is not None
        assert "= 0" in clf.reference_homogeneous_latex
        assert "thừa số tích phân" in clf.recommended_method_title.lower()


# =============================================================================
# Test 3: Dual Linear and Separable Rendering
# =============================================================================

def test_ux3_6_dual_linear_and_separable_rendering():
    """Verify y' = t*y is recognized as both Linear Homogeneous and Separable."""
    clf = classify_first_order_ode("y' = t*y", "t")
    state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.FIRST_ORDER_LINEAR,
        equation="y' = t*y",
        target_var="t",
    )

    client = Client(ui.page("/test_ux3_6_dual"))
    with client:
        render_ode_guided_classification_view(
            result=clf,
            state=state,
            on_select_classification=MagicMock(),
        )

        elements_text = [
            el.text for el in client.elements.values()
            if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
        ]
        all_text = " ".join(elements_text)

        assert clf.is_linear is True
        assert clf.is_separable is True
        # Dual classification badge
        assert "Đồng thời là" in all_text
        assert "Tách biến" in all_text or "tách biến" in all_text
        # Alternative methods should present Separable
        assert len(clf.alternative_methods) >= 1
        assert clf.alternative_methods[0]["problem_type"] == ProblemType.ODE_SEPARABLE


# =============================================================================
# Test 4: Separable Nonlinear Rendering
# =============================================================================

def test_ux3_6_nonlinear_separable_rendering():
    """Verify nonlinear separable ODE y' = y*(1 - y) extracts f(t), g(y) and recommends separation."""
    clf = classify_first_order_ode("y' = y*(1 - y)", "t")
    state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.SEPARABLE,
        equation="y' = y*(1 - y)",
        target_var="t",
    )

    client = Client(ui.page("/test_ux3_6_sep_nonlinear"))
    with client:
        render_ode_guided_classification_view(
            result=clf,
            state=state,
            on_select_classification=MagicMock(),
        )

        elements_text = [
            el.text for el in client.elements.values()
            if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
        ]
        all_text = " ".join(elements_text)

        assert clf.is_linear is False
        assert clf.is_separable is True
        assert "tách biến" in clf.primary_title.lower()
        assert "Thành phần theo biến độc lập" in all_text
        assert "Thành phần theo hàm số" in all_text
        assert "tách biến" in clf.recommended_method_title.lower()


# =============================================================================
# Test 5: Classical Homogeneous Ratio Rendering
# =============================================================================

def test_ux3_6_classical_homogeneous_ratio_rendering():
    """Verify ratio homogeneous ODE y' = (y + x)/(y - x) explains substitution y = v*x."""
    clf = classify_first_order_ode("y' = (y + x)/(y - x)", "x")
    state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.FIRST_ORDER_HOMOGENEOUS,
        equation="y' = (y + x)/(y - x)",
        target_var="x",
    )

    client = Client(ui.page("/test_ux3_6_ratio_homog"))
    with client:
        render_ode_guided_classification_view(
            result=clf,
            state=state,
            on_select_classification=MagicMock(),
        )

        elements_text = [
            el.text for el in client.elements.values()
            if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
        ]
        all_text = " ".join(elements_text)

        assert clf.is_classical_homogeneous is True
        assert "thuần nhất cấp 1" in clf.primary_title.lower()
        assert "tỷ số" in clf.primary_title.lower() or "tỉ số" in clf.primary_title.lower()
        assert "thuần nhất" in all_text.lower()
        # Explanation must clarify substitution y = v*x
        assert any("frac{y}{x}" in p or "v =" in p or "v\\cdot x" in p or "y = v" in p for p in clf.explanation_points)
        assert "đổi biến" in clf.recommended_method_title.lower()


# =============================================================================
# Test 6: Exact Differential Equation Rendering
# =============================================================================

def test_ux3_6_exact_ode_rendering():
    """Verify exact ODE displays M, N and verifies partial derivatives condition ∂M/∂y == ∂N/∂t."""
    clf = classify_first_order_ode("(2*t*y + 3)*dt + (t^2 + 4*y)*dy = 0", "t")
    state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.EXACT,
        equation="(2*t*y + 3)*dt + (t^2 + 4*y)*dy = 0",
        target_var="t",
    )

    client = Client(ui.page("/test_ux3_6_exact"))
    with client:
        render_ode_guided_classification_view(
            result=clf,
            state=state,
            on_select_classification=MagicMock(),
        )

        elements_text = [
            el.text for el in client.elements.values()
            if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
        ]
        all_text = " ".join(elements_text)

        assert clf.is_exact_form is True
        assert clf.is_exact is True
        assert "toàn phần" in clf.primary_title.lower()
        assert "Hàm M(t, y):" in all_text
        assert "Hàm N(t, y):" in all_text
        assert "Đạo hàm riêng ∂M/∂y:" in all_text
        assert "Đạo hàm riêng ∂N/∂t:" in all_text
        assert any("thỏa mãn" in p.lower() for p in clf.explanation_points)
        assert "thế vị" in clf.recommended_method_title.lower()


# =============================================================================
# Test 7: Non-exact Equation Recommends Integrating Factor
# =============================================================================

def test_ux3_6_non_exact_ode_recommends_integrating_factor():
    """Verify non-exact ODE fails Euler-Cauchy test and recommends integrating factor μ."""
    clf = classify_first_order_ode("(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0", "x")
    state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.INTEGRATING_FACTOR,
        equation="(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0",
        target_var="x",
    )

    client = Client(ui.page("/test_ux3_6_non_exact"))
    with client:
        render_ode_guided_classification_view(
            result=clf,
            state=state,
            on_select_classification=MagicMock(),
        )

        elements_text = [
            el.text for el in client.elements.values()
            if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
        ]
        all_text = " ".join(elements_text)

        assert clf.is_exact_form is True
        assert clf.is_exact is False
        assert clf.primary_category == "INTEGRATING_FACTOR"
        assert clf.target_problem_type == ProblemType.ODE_INTEGRATING_FACTOR
        assert "thừa số tích phân" in all_text.lower()
        assert any("thất bại" in p.lower() for p in clf.explanation_points)
        assert "thừa số tích phân" in clf.recommended_method_title.lower()


# =============================================================================
# Test 8: Second-Order Mismatch Guidance in First-Order Workspace
# =============================================================================

def test_ux3_6_second_order_mismatch_guided_action():
    """Verify entering y'' + 4*y = 4*t in first-order workspace renders order mismatch card with switch button."""
    op = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)
    mock_use_case = _make_mock_use_case()

    client = Client(ui.page("/test_ux3_6_order_mismatch"))
    with client:
        render_ode_workspace(op, mock_use_case)

        # Enter second-order equation
        eq_inputs = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")]
        assert len(eq_inputs) >= 1
        main_eq = eq_inputs[-1]
        main_eq.set_value("y'' + 4*y = 4*t")

        # Check for order mismatch card and switch button
        elements_text = [
            el.text for el in client.elements.values()
            if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
        ]
        all_text = " ".join(elements_text)
        assert "Phương trình không đúng cấp" in all_text
        assert "phương trình vi phân cấp 2" in all_text

        switch_btns = [el for el in client.elements.values() if isinstance(el, ui.button) and "Chuyển sang PTVP cấp 2" in el.text]
        assert len(switch_btns) >= 1

        # Click switch button
        for listener in list(switch_btns[-1]._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)

        # After switch, equation is preserved in second-order workspace
        eq_inputs_after = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")]
        assert len(eq_inputs_after) >= 1
        assert "y'' + 4*y = 4*t" in eq_inputs_after[-1].value


# =============================================================================
# Test 9: Interface Simplification — Absence of Redundant Override & Help Panels
# =============================================================================

@pytest.mark.anyio
async def test_ux3_6_manual_override_and_alternative_method_selection():
    """Verify UX3.7.1 removes manual override buttons and beginner help accordions from First-Order workflow."""
    core.loop = asyncio.get_running_loop()

    op = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)
    mock_use_case = _make_mock_use_case()

    client = Client(ui.page("/test_ux3_6_manual_override"))
    with client:
        render_ode_workspace(op, mock_use_case)

        # Set custom equation
        eq_inputs = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")]
        main_eq = eq_inputs[-1]
        main_eq.set_value("y' = 3*y")

        all_text = " ".join([
            el.text for el in client.elements.values()
            if isinstance(el, (ui.label, ui.badge, ui.button)) and el.text
        ])

        # 1. Manual override accordion & beginner help must NOT appear
        assert "Khám phá các phương pháp giải khác" not in all_text
        assert "Ghi đè thủ công" not in all_text
        assert "Trợ giúp nhận dạng dạng phương trình" not in all_text

        # 2. Manual override buttons must be completely absent from the normal First-Order workflow
        override_btn_labels = {"Vi phân toàn phần", "Thuần nhất cấp 1", "Thừa số tích phân"}
        rendered_buttons = [el.text for el in client.elements.values() if isinstance(el, ui.button) and el.text]
        for btn_lbl in override_btn_labels:
            assert btn_lbl not in rendered_buttons

        # 3. Automatic solving still executes without manual intervention
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
        assert "y' = 3*y" in req.raw_input


# =============================================================================
# Test 10: General Solution vs Cauchy IVP in Guided Workflow
# =============================================================================

@pytest.mark.anyio
async def test_ux3_6_general_vs_cauchy_ivp_in_guided_workflow():
    """Verify Cauchy IVP mode displays dedicated initial condition input and attaches IC to request."""
    core.loop = asyncio.get_running_loop()

    op = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)
    mock_use_case = _make_mock_use_case()

    client = Client(ui.page("/test_ux3_6_cauchy_flow"))
    with client:
        render_ode_workspace(op, mock_use_case)

        # Switch to Cauchy IVP mode
        cauchy_btns = [
            el for el in client.elements.values()
            if isinstance(el, ui.button) and "Bài toán Cauchy" in el.text
        ]
        assert len(cauchy_btns) >= 1
        for listener in list(cauchy_btns[-1]._event_listeners.values()):
            if listener.type in ("click", None):
                listener.handler(None)

        # Dedicated IC input should appear with label containing "Điều kiện"
        ic_inputs = [
            el for el in client.elements.values()
            if isinstance(el, ui.input) and "Điều kiện" in el._props.get("label", "")
        ]
        assert len(ic_inputs) >= 1
        ic_inputs[-1].set_value("y(0) = 5")

        # Solve
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
        assert req.parameters.get("initial_condition") == "y(0) = 5"

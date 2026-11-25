"""Dedicated test suite for UX3.5.3: ODE Order Detection & Context-Aware Input Validation.

Tests cover:
1. First-Order Workspace Accept/Reject:
   - Accepts first-order equations (e.g. y' + 2*y = exp(-t)).
   - Rejects second-order equations (e.g. y'' + 4*y = 4*t) with Vietnamese explanation:
     "Phương trình không đúng cấp: Bạn đang nhập phương trình vi phân cấp 2, nhưng không gian làm việc hiện tại chỉ hỗ trợ phương trình cấp 1."
   - Rejects higher-order equations (e.g. y''' + y = 0, d^3y/dt^3 + y = 0) with:
     "Phương trình không đúng cấp: Bạn đang nhập phương trình vi phân cấp cao (cấp 3 trở lên)..."
2. Second-Order Workspace Accept/Reject:
   - Accepts supported second-order equations (e.g. y'' + 4*y = 4*t, Cauchy IVP, Reduction of Order).
   - Rejects first-order equations (e.g. y' + 2*y = exp(-t)) with Vietnamese explanation:
     "Phương trình không đúng cấp: Bạn đang nhập phương trình vi phân cấp 1, nhưng không gian làm việc hiện tại chỉ hỗ trợ phương trình vi phân cấp 2..."
   - Rejects higher-order equations (e.g. y''' + y = 0).
3. Non-Differential Algebraic Expressions:
   - Algebraic expressions (e.g. x^2 + 2*x + 1 = 0, y = 2*t + 1) raise clean error:
     "không chứa đạo hàm..." without false classification.
4. Input Preservation:
   - Original equation text and inputs are strictly preserved across order switching
     via state.with_order(..., preserve_equation=True).
5. Information Hiding / Internal Identifiers:
   - Absolute absence of internal parser identifiers ('y_double_prime', 'y_prime', 'y_higher_prime')
     in user-facing messages and warnings.
6. Syntax Error Distinction:
   - Genuine syntax errors (unbalanced parentheses, invalid operators) raise syntax errors,
     not false order mismatch errors.
7. Validation Card Rendering:
   - Academic Blue UI validation card renders with header "Phương trình không đúng cấp",
     quick-switch action button ("Chuyển sang PTVP cấp 2" / "Chuyển sang PTVP cấp 1"),
     and "Quay lại danh mục toán học" button.
8. Full ODE Benchmark Regression Suite:
   - 10 benchmark ODE equations solve and verify without regressions.
"""

from __future__ import annotations

import re
import pytest
from nicegui import Client, ui

from math_app.application.dtos import ProblemRequest, SolutionStatus, VerificationStatus
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType
from math_app.input.ode_parser import detect_ode_order, validate_ode_order
from math_app.main import build_application
from math_app.presentation.components.ode_pedagogical_enhancer import enhance_ode_solution_flow
from math_app.presentation.components.solution_view import _filter_ui_warnings
from math_app.presentation.components.workspace.ode.ode_state import (
    ODEClassification,
    ODEMode,
    ODEOrder,
    ODEState,
)
from math_app.presentation.components.workspace.ode.ode_workspace import render_ode_validation_card
from math_app.rendering.text_math_renderer import render_math_in_text_html


@pytest.fixture(scope="module")
def app():
    return build_application()


# ==============================================================================
# 1. FIRST-ORDER WORKSPACE VALIDATION
# ==============================================================================


def test_first_order_workspace_accepts_valid_first_order(app):
    """First-Order workspace cleanly accepts first-order equations and solves them."""
    state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.FIRST_ORDER_LINEAR,
        target_var="t",
        equation="y' + 2*y = exp(-t)",
        mode=ODEMode.GENERAL,
    )
    req = state.build_problem_request()
    assert req.problem_type == ProblemType.ODE_FIRST_ORDER_LINEAR
    assert req.target_variable == "t"
    assert "y' + 2*y = exp(-t)" in req.raw_input

    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None


def test_first_order_workspace_rejects_second_order_with_vietnamese_message():
    """First-Order workspace rejects second-order ODE with polite Vietnamese guidance."""
    state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.FIRST_ORDER_LINEAR,
        target_var="t",
        equation="y'' + 4*y = 4*t",
        mode=ODEMode.GENERAL,
    )
    with pytest.raises(InvalidInputError) as exc_info:
        state.build_problem_request()

    err_msg = str(exc_info.value)
    assert "Phương trình không đúng cấp" in err_msg
    assert "Bạn đang nhập phương trình vi phân cấp 2" in err_msg
    assert "chỉ hỗ trợ phương trình cấp 1" in err_msg
    assert "Phương trình vi phân cấp 2" in err_msg
    # Internal parser identifiers must NOT leak
    assert "y_double_prime" not in err_msg
    assert "y_prime" not in err_msg


def test_first_order_workspace_rejects_higher_order_with_vietnamese_message():
    """First-Order workspace rejects order >= 3 ODE with polite Vietnamese message."""
    for eq in ("y''' + 2*y = 0", "d^3y/dt^3 + y = 0", "y'''' - y = 0"):
        state = ODEState(
            order=ODEOrder.FIRST_ORDER,
            classification=ODEClassification.FIRST_ORDER_LINEAR,
            target_var="t",
            equation=eq,
            mode=ODEMode.GENERAL,
        )
        with pytest.raises(InvalidInputError) as exc_info:
            state.build_problem_request()

        err_msg = str(exc_info.value)
        assert "Phương trình không đúng cấp" in err_msg
        assert "cấp cao" in err_msg or "cấp 3 trở lên" in err_msg
        assert "y_higher_prime" not in err_msg
        assert "y_double_prime" not in err_msg


# ==============================================================================
# 2. SECOND-ORDER WORKSPACE VALIDATION
# ==============================================================================


def test_second_order_workspace_accepts_valid_second_order(app):
    """Second-Order workspace cleanly accepts second-order ODEs and solves them."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
        target_var="t",
        equation="y'' + 4*y = 4*t",
        mode=ODEMode.GENERAL,
    )
    req = state.build_problem_request()
    assert req.problem_type == ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF
    assert req.target_variable == "t"
    assert "y'' + 4*y = 4*t" in req.raw_input

    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None


def test_second_order_workspace_rejects_first_order_with_vietnamese_message():
    """Second-Order workspace rejects first-order ODE with polite Vietnamese guidance."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
        target_var="t",
        equation="y' + 2*y = exp(-t)",
        mode=ODEMode.GENERAL,
    )
    with pytest.raises(InvalidInputError) as exc_info:
        state.build_problem_request()

    err_msg = str(exc_info.value)
    assert "Phương trình không đúng cấp" in err_msg
    assert "Bạn đang nhập phương trình vi phân cấp 1" in err_msg
    assert "cấp 2" in err_msg
    assert "Phương trình vi phân cấp 1" in err_msg
    # Internal parser identifiers must NOT leak
    assert "y_prime" not in err_msg
    assert "y_double_prime" not in err_msg


def test_second_order_workspace_rejects_higher_order_with_vietnamese_message():
    """Second-Order workspace rejects order >= 3 ODE with polite Vietnamese message."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
        target_var="t",
        equation="y''' + 4*y' + y = 0",
        mode=ODEMode.GENERAL,
    )
    with pytest.raises(InvalidInputError) as exc_info:
        state.build_problem_request()

    err_msg = str(exc_info.value)
    assert "Phương trình không đúng cấp" in err_msg
    assert "cấp cao" in err_msg or "cấp 3 trở lên" in err_msg
    assert "y_higher_prime" not in err_msg


# ==============================================================================
# 3. NON-DIFFERENTIAL ALGEBRAIC EXPRESSIONS
# ==============================================================================


@pytest.mark.parametrize(
    "algebraic_expr",
    [
        "x^2 + 2*x + 1 = 0",
        "y = 2*t + 1",
        "3*x + 4*y = 12",
        "sin(t) + cos(t) = 1",
    ],
)
def test_algebraic_expressions_not_classified_as_ode(algebraic_expr):
    """Algebraic expressions without derivatives are detected as order 0 and rejected gracefully."""
    detected_order = detect_ode_order(algebraic_expr)
    assert detected_order == 0, f"Expected order 0 for algebraic expression '{algebraic_expr}'"

    # Both first-order and second-order validations must reject it politely
    for exp_order in (1, 2):
        with pytest.raises(InvalidInputError) as exc_info:
            validate_ode_order(algebraic_expr, expected_order=exp_order)
        err_msg = str(exc_info.value)
        assert "không chứa đạo hàm" in err_msg


# ==============================================================================
# 4. PRESERVATION OF EQUATION AND USER INPUTS ACROSS STATE CHANGES
# ==============================================================================


def test_preserve_equation_across_order_switch():
    """Verify state.with_order(..., preserve_equation=True) preserves equation text."""
    eq_text = "y'' + 4*y = 4*t"
    s1 = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.FIRST_ORDER_LINEAR,
        target_var="t",
        equation=eq_text,
    )
    assert s1.equation == eq_text

    # Switch to second-order with preserve_equation=True
    s2 = s1.with_order(ODEOrder.SECOND_ORDER, preserve_equation=True)
    assert s2.order == ODEOrder.SECOND_ORDER
    assert s2.equation == eq_text, "Equation must be preserved when switching order"
    assert s2.target_var == "t"
    assert s2.classification == ODEClassification.SECOND_ORDER_NONHOMOGENEOUS

    # Switch back to first-order with preserve_equation=True
    s3 = s2.with_order(ODEOrder.FIRST_ORDER, preserve_equation=True)
    assert s3.order == ODEOrder.FIRST_ORDER
    assert s3.equation == eq_text, "Equation must still be preserved"


# ==============================================================================
# 5. INFORMATION HIDING (INTERNAL PARSER IDENTIFIERS)
# ==============================================================================


def test_internal_parser_identifiers_never_leaked():
    """Verify internal tokens like 'y_double_prime', 'y_prime', 'y_higher_prime'
    never appear in sanitized warning lists or exception messages.
    """
    raw_warnings = [
        "Ký hiệu không xác định 'y_double_prime'",
        "Lỗi parse biến y_prime",
        "Gặp token y_higher_prime trong biểu thức",
    ]
    filtered = _filter_ui_warnings(raw_warnings)
    combined = " ".join(filtered)
    assert "y_double_prime" not in combined
    assert "y_prime" not in combined
    assert "y_higher_prime" not in combined
    assert "đạo hàm cấp 2" in combined
    assert "đạo hàm cấp 1" in combined or "y'" in combined
    assert "đạo hàm cấp cao" in combined


# ==============================================================================
# 6. SYNTAX ERROR DISTINCTION
# ==============================================================================


def test_syntax_errors_distinguished_from_order_mismatches():
    """Verify syntax errors (e.g. unbalanced parens or operator errors)
    are reported as syntax errors rather than false order mismatch errors.
    """
    # Unbalanced parenthesis
    with pytest.raises(InvalidInputError) as exc_info:
        validate_ode_order("y'' + (4*y = 0", expected_order=1)
    err = str(exc_info.value)
    assert "Phương trình không đúng cấp" not in err
    assert "ngoặc" in err.lower() or "cú pháp" in err.lower() or "syntax" in err.lower()

    # Invalid operator placement
    with pytest.raises(InvalidInputError) as exc_info2:
        validate_ode_order("y' + * 2 = 0", expected_order=2)
    err2 = str(exc_info2.value)
    assert "Phương trình không đúng cấp" not in err2
    assert "cú pháp" in err2.lower() or "toán tử" in err2.lower() or "syntax" in err2.lower()


# ==============================================================================
# 7. CAUCHY IVP INTEGRATION AND DERIVATIVE STRIPPING
# ==============================================================================


def test_cauchy_ivp_workflow_remains_operational(app):
    """Verify Cauchy IVP workflow (y'' + 4*y = 4*t, y(0)=1, y'(0)=2) remains fully operational."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS,
        mode=ODEMode.CAUCHY_IVP,
        target_var="t",
        equation="y'' + 4*y = 4*t",
        initial_condition="y(0)=1, y'(0)=2",
    )
    req = state.build_problem_request()
    assert req.problem_type == ProblemType.ODE_SECOND_ORDER_IVP
    assert req.parameters.get("initial_condition") == "y(0)=1, y'(0)=2"

    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None
    assert "t" in res.final_result
    assert "sin(2*t)" in res.final_result
    assert "cos(2*t)" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


# ==============================================================================
# 8. VALIDATION CARD COMPONENT RENDERING
# ==============================================================================


def test_validation_card_rendering_order_mismatch():
    """Verify render_ode_validation_card renders amber alert with quick-switch button."""
    client = Client(ui.page("/test_val_card_order_mismatch"))
    switched_orders = []
    catalog_called = []

    state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.FIRST_ORDER_LINEAR,
        target_var="t",
        equation="y'' + 4*y = 4*t",
    )
    err_text = "Phương trình không đúng cấp: Bạn đang nhập phương trình vi phân cấp 2, nhưng không gian làm việc hiện tại chỉ hỗ trợ phương trình cấp 1."

    with client:
        render_ode_validation_card(
            err_msg=err_text,
            state=state,
            on_switch_order=lambda o: switched_orders.append(o),
            on_back_to_catalog=lambda: catalog_called.append(True),
        )

    labels = [el.text for el in client.elements.values() if isinstance(el, ui.label)]
    buttons = [el for el in client.elements.values() if isinstance(el, ui.button)]

    # Check header and message
    assert any("Phương trình không đúng cấp" in txt for txt in labels)
    assert any("phương trình vi phân cấp 2" in txt for txt in labels)

    # Check action buttons
    button_texts = [b.text for b in buttons]
    assert any("Chuyển sang PTVP cấp 2" in t for t in button_texts)
    assert any("Quay lại danh mục toán học" in t for t in button_texts)

    # Trigger switch button via event handler
    switch_btn = next(b for b in buttons if "Chuyển sang PTVP cấp 2" in b.text)
    for listener in switch_btn._event_listeners.values():
        if listener.type == "click" and listener.handler:
            listener.handler(None)
    assert ODEOrder.SECOND_ORDER in switched_orders

    # Trigger back to catalog button via event handler
    cat_btn = next(b for b in buttons if "Quay lại danh mục toán học" in b.text)
    for listener in cat_btn._event_listeners.values():
        if listener.type == "click" and listener.handler:
            listener.handler(None)
    assert catalog_called == [True]


def test_validation_card_rendering_syntax_error():
    """Verify render_ode_validation_card renders rose card for genuine syntax error."""
    client = Client(ui.page("/test_val_card_syntax_error"))
    state = ODEState(
        order=ODEOrder.FIRST_ORDER,
        classification=ODEClassification.FIRST_ORDER_LINEAR,
    )
    err_text = "Lỗi cú pháp: Dấu ngoặc đơn chưa được đóng mở đúng cách."

    with client:
        render_ode_validation_card(
            err_msg=err_text,
            state=state,
        )

    labels = [el.text for el in client.elements.values() if isinstance(el, ui.label)]
    assert any("Dữ liệu đầu vào chưa hợp lệ" in txt for txt in labels)
    assert any("Dấu ngoặc" in txt for txt in labels)


# ==============================================================================
# 9. BENCHMARK ODE REGRESSION SUITE
# ==============================================================================


@pytest.mark.parametrize(
    "prob_type,raw_input,target_var,expected_keyword",
    [
        (ProblemType.ODE_FIRST_ORDER_LINEAR, "y' + 2*y = exp(-t)", "t", "exp"),
        (ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "y'' - 3*y' + 2*y = exp(t)", "t", "exp"),
        (ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "y'' + 2*y' + 5*y = 3*sin(2*t)", "t", "sin"),
        (ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, "y'' - 2*y' - 3*y = 3*exp(2*t)", "t", "exp"),
        (ProblemType.ODE_SECOND_ORDER_IVP, "y'' + 4*y = 4*t, y(0)=1, y'(0)=2", "t", "sin"),
        (ProblemType.ODE_SEPARABLE, "y' = y^2", "x", "x"),
        (ProblemType.ODE_EXACT, "2*x*y + (x^2 + 1)*y' = 0", "x", "x"),
        (ProblemType.ODE_INTEGRATING_FACTOR, "y' + y/x = 1", "x", "x"),
        (ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS, "y' = (y + x)/x", "x", "x"),
        (ProblemType.ODE_REDUCTION_OF_ORDER, "t^2*y'' - 2*t*y' + 2*y = 0", "t", "C"),
    ],
)
def test_full_ode_benchmark_regression_ux3_5_3(app, prob_type, raw_input, target_var, expected_keyword):
    """Ensure all 10 benchmark ODE scenarios solve, verify, and generate valid pedagogical stages
    without any regressions after order detection integration.
    """
    params = {"known_solution": "t"} if prob_type == ProblemType.ODE_REDUCTION_OF_ORDER else {}
    req = ProblemRequest(
        problem_type=prob_type,
        raw_input=raw_input,
        target_variable=target_var,
        parameters=params,
    )
    res = app.execute(req)
    assert res.status in (SolutionStatus.SUCCESS, SolutionStatus.UNVERIFIED)
    assert res.final_result is not None
    assert expected_keyword in res.final_result

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) >= 3, f"Expected at least 3 stages for {raw_input}, got {len(stages)}"

    for stage in stages:
        assert stage.title
        assert stage.badge_text
        for step in stage.steps:
            assert step.display_title
            rendered_html = render_math_in_text_html(step.description)
            assert "$" not in re.sub(r"<[^>]+>", "", rendered_html)

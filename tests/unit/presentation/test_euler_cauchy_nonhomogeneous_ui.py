"""Presentation, classifier, pedagogical enhancer, and NiceGUI client tests for nonhomogeneous Euler–Cauchy ODEs."""

from __future__ import annotations

from nicegui import Client, ui

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, VerificationStatus
from math_app.main import build_application
from math_app.presentation.components.ode_pedagogical_enhancer import enhance_ode_solution_flow
from math_app.presentation.components.ode_staged_step_viewer import render_ode_staged_steps_container
from math_app.presentation.components.operation_catalog import get_operation_by_type
from math_app.presentation.components.solution_view import render_ode_classification_card
from math_app.presentation.components.workspace.ode.ode_state import ODEClassification
from math_app.presentation.components.workspace.ode.ode_workspace import render_ode_workspace
from math_app.presentation.components.workspace.ode.second_order_classifier import classify_second_order_ode


def _collect_texts(root: ui.element) -> list[str]:
    """Recursively collect visible text/content strings from a NiceGUI element tree."""
    out: list[str] = []

    def _walk(el: ui.element) -> None:
        for attr in ("text", "content"):
            val = getattr(el, attr, None)
            if isinstance(val, str) and val.strip():
                out.append(val.strip())
        for child in el.default_slot.children:
            if isinstance(child, ui.element):
                _walk(child)

    _walk(root)
    return out


# ==============================================================================
# 1. Second-Order Classifier: Nonhomogeneous Euler–Cauchy Detection
# ==============================================================================


def test_classifier_detects_nonhomogeneous_euler_cauchy_variants() -> None:
    """Detect nonhomogeneous Euler–Cauchy, separated forcing g(t), sign, domain, and IVP/rescaled cases."""
    summary = classify_second_order_ode("t^2*y'' - t*y' + y = t^2, t > 0", target_var="t")
    assert summary.status == "DETECTED"
    assert summary.detected_classification == ODEClassification.EULER_CAUCHY
    assert summary.badge_label == "Phương trình Euler–Cauchy không thuần nhất"
    assert summary.is_nonhomogeneous is True
    assert summary.associated_homogeneous_latex is not None
    assert "= 0" in summary.associated_homogeneous_latex
    assert summary.forcing_term_latex == r"g(t) = t^{2}"
    assert "-t^{2}" not in (summary.forcing_term_latex or "")
    assert summary.domain_hint is not None and "t > 0" in summary.domain_hint
    assert summary.recommended_nonhomo_method == "Phương pháp tự động (Khuyến nghị)"

    neg_summary = classify_second_order_ode("t^2*y'' - t*y' + y = t^2, t < 0", target_var="t")
    assert neg_summary.is_nonhomogeneous is True
    assert neg_summary.detected_interval == "t < 0"
    assert neg_summary.domain_hint is not None and "t < 0" in neg_summary.domain_hint

    rescaled = classify_second_order_ode("t*y'' + y' = t, t > 0", target_var="t")
    assert rescaled.status == "DETECTED"
    assert rescaled.detected_classification == ODEClassification.EULER_CAUCHY
    assert rescaled.is_nonhomogeneous is True
    assert rescaled.forcing_term_latex == r"g(t) = t^{2}"

    ivp = classify_second_order_ode("t^2*y'' - t*y' + y = t^2, t > 0, y(1) = 0, y'(1) = 0", target_var="t")
    assert ivp.status == "DETECTED"
    assert ivp.detected_classification == ODEClassification.EULER_CAUCHY
    assert ivp.is_nonhomogeneous is True
    assert ivp.has_inline_ic is True


def test_classifier_does_not_misclassify_constant_coeff_or_non_euler_or_homogeneous() -> None:
    """Guard constant-coeff, general variable-coeff, and homogeneous Euler–Cauchy classification."""
    cc1 = classify_second_order_ode("y'' - 3*y' + 2*y = t^2", target_var="t")
    assert cc1.status == "DETECTED"
    assert cc1.detected_classification == ODEClassification.SECOND_ORDER_NONHOMOGENEOUS

    cc2 = classify_second_order_ode("y'' + y = tan(t)", target_var="t")
    assert cc2.status == "DETECTED"
    assert cc2.detected_classification == ODEClassification.SECOND_ORDER_NONHOMOGENEOUS

    non_ec = classify_second_order_ode("t*y'' + y' + y = t", target_var="t")
    assert non_ec.detected_classification != ODEClassification.EULER_CAUCHY

    homo = classify_second_order_ode("t^2*y'' + 4*t*y' + 2*y = 0, t > 0", target_var="t")
    assert homo.status == "DETECTED"
    assert homo.detected_classification == ODEClassification.EULER_CAUCHY
    assert homo.is_nonhomogeneous is False
    assert homo.badge_label == "Euler–Cauchy"


# ==============================================================================
# 2. Pedagogical Enhancer: 4-Stage Nonhomogeneous Flow
# ==============================================================================


def test_enhancer_nonhomogeneous_four_stages_general_ivp_neg_and_integral() -> None:
    """Verify 4 pedagogical stages for general, IVP, negative domain, and non-elementary integral forcing."""
    uc = build_application()

    # General mode
    req_gen = ProblemRequest(
        raw_input="t^2*y'' - t*y' + y = t^2, t > 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "GENERAL"},
    )
    resp_gen = uc.execute(req_gen)
    stages_gen = enhance_ode_solution_flow(
        resp_gen, ProblemType.ODE_EULER_CAUCHY, "t", {"problem_mode": "GENERAL"}
    )
    assert len(stages_gen) == 4
    stage2_rules = [s.rule_name for s in stages_gen[1].steps]
    stage3_rules = [s.rule_name for s in stages_gen[2].steps]
    assert "Nghiệm thuần nhất liên kết" in stage2_rules
    assert "Chuẩn hóa và phương pháp Biến thiên hằng số" in stage3_rules
    assert "Đạo hàm hàm biến thiên" in stage3_rules
    assert "Tích phân hàm biến thiên" in stage3_rules
    assert "Nghiệm riêng biến thiên hằng số" in stage3_rules
    assert "Nghiệm tổng quát" in stage3_rules
    assert "y_c(t) + y_p(t)" in stages_gen[2].steps[-1].equation_latex
    assert "\\ln" in stages_gen[2].summary_latex
    assert "\\log" not in stages_gen[2].summary_latex
    assert stages_gen[3].badge_text == "Kiểm chứng"
    assert resp_gen.verification.status == VerificationStatus.VERIFIED

    # Cauchy IVP mode
    req_ivp = ProblemRequest(
        raw_input="t^2*y'' - t*y' + y = t^2, t > 0, y(1) = 0, y'(1) = 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    resp_ivp = uc.execute(req_ivp)
    stages_ivp = enhance_ode_solution_flow(
        resp_ivp, ProblemType.ODE_EULER_CAUCHY, "t", {"problem_mode": "CAUCHY_IVP"}
    )
    assert "Điều kiện ban đầu Cauchy" in [s.rule_name for s in stages_ivp[2].steps]
    assert resp_ivp.verification.status == VerificationStatus.VERIFIED

    # Negative domain t < 0
    req_neg = ProblemRequest(
        raw_input="t^2*y'' - t*y' + y = t^2, t < 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "GENERAL"},
    )
    resp_neg = uc.execute(req_neg)
    stages_neg = enhance_ode_solution_flow(
        resp_neg, ProblemType.ODE_EULER_CAUCHY, "t", {"problem_mode": "GENERAL"}
    )
    assert "\\ln(-t)" in stages_neg[2].summary_latex
    assert resp_neg.verification.status == VerificationStatus.VERIFIED

    # Non-elementary exp(t^2)
    req_non_el = ProblemRequest(
        raw_input="t^2*y'' - t*y' + y = exp(t^2), t > 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "GENERAL"},
    )
    resp_non_el = uc.execute(req_non_el)
    stages_non_el = enhance_ode_solution_flow(
        resp_non_el, ProblemType.ODE_EULER_CAUCHY, "t", {"problem_mode": "GENERAL"}
    )
    integ_step = next(s for s in stages_non_el[2].steps if s.rule_name == "Tích phân hàm biến thiên")
    assert "\\int" in integ_step.equation_latex
    assert stages_non_el[3].badge_text == "Kiểm chứng"


# ==============================================================================
# 3. NiceGUI Client Tests: Workspace & Classification Card
# ==============================================================================


def test_workspace_and_solution_card_render_nonhomogeneous_euler_cauchy() -> None:
    """Verify UI renders nonhomogeneous classification, method panel, yc/yp card, and toggles cleanly."""
    uc = build_application()
    op = get_operation_by_type(ProblemType.ODE_EULER_CAUCHY)

    ws_client = Client(ui.page("/test_ec_nonhomo_ws"))
    with ws_client:
        render_ode_workspace(op, uc)

    inputs = [el for el in ws_client.elements.values() if isinstance(el, ui.input)]
    eq_input = inputs[0]

    # Trigger input change to nonhomogeneous Euler–Cauchy
    with ws_client:
        eq_input.set_value("t^2*y'' - t*y' + y = t^2, t > 0")

    ws_texts = "\n".join(_collect_texts(ws_client.layout))
    assert "Phương trình Euler–Cauchy không thuần nhất" in ws_texts
    assert "Thuần nhất liên kết:" in ws_texts
    assert "Vế phải:" in ws_texts
    assert "Phương pháp tự động (Khuyến nghị)" in ws_texts

    # Toggle back to homogeneous Euler–Cauchy and ensure nonhomogeneous selector disappears
    with ws_client:
        eq_input.set_value("t^2*y'' + 4*t*y' + 2*y = 0, t > 0")

    ws_texts_homo = "\n".join(_collect_texts(ws_client.layout))
    assert "Phương trình Euler–Cauchy không thuần nhất" not in ws_texts_homo
    assert "PHƯƠNG PHÁP ĐỀ XUẤT — EULER–CAUCHY KHÔNG THUẦN NHẤT:" not in ws_texts_homo

    # Classification card + staged step viewer render yc / yp separation
    req = ProblemRequest(
        raw_input="t^2*y'' - t*y' + y = t^2, t > 0",
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        target_variable="t",
        parameters={"problem_mode": "GENERAL"},
    )
    resp = uc.execute(req)
    sol_client = Client(ui.page("/test_ec_nonhomo_card"))
    with sol_client:
        render_ode_classification_card(resp, ProblemType.ODE_EULER_CAUCHY, {"problem_mode": "GENERAL"}, "t")
        stages = enhance_ode_solution_flow(resp, ProblemType.ODE_EULER_CAUCHY, "t", {"problem_mode": "GENERAL"})
        render_ode_staged_steps_container(stages, "t")

    sol_texts = "\n".join(_collect_texts(sol_client.layout))
    assert "Cấp 2 • Euler–Cauchy" in sol_texts
    assert "Không thuần nhất" in sol_texts
    assert "Biến thiên hằng số (Euler–Cauchy)" in sol_texts
    assert "CẤU TRÚC NGHIỆM:" in sol_texts
    assert "y_c(t)" in sol_texts
    assert "y_p(t)" in sol_texts

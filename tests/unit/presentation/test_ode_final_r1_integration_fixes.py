"""Targeted regression tests for ODE-FINAL-R1 presentation & workspace integration fixes."""

from __future__ import annotations

import pytest
import sympy as sp
from nicegui import Client, app, ui

from math_app.application.dtos import BranchSolution, ProblemRequest, VerificationResult
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.main import build_application
from math_app.presentation.app import create_app
from math_app.presentation.components.domain_view import format_domain_condition, render_domain_restrictions
from math_app.presentation.components.operation_catalog import get_operation_by_type
from math_app.presentation.components.solution_view import render_branch_solutions, render_solution_view
from math_app.presentation.components.workspace.ode.ode_mode_selector import render_ode_mode_selector
from math_app.presentation.components.workspace.ode.ode_state import (
    DEFAULT_CONFIGS,
    ODEClassification,
    ODEMode,
    ODEOrder,
    ODEState,
)
from math_app.presentation.components.workspace.ode.ode_workspace import (
    render_ode_validation_card,
    render_ode_workspace,
)


def _collect_texts(root_or_client: Client | ui.element) -> list[str]:
    texts: list[str] = []
    elements = (
        root_or_client.elements.values()
        if isinstance(root_or_client, Client)
        else [root_or_client, *root_or_client.descendants()]
    )
    for el in elements:
        txt = getattr(el, "text", None)
        if isinstance(txt, str) and txt.strip():
            texts.append(txt.strip())
        lbl = getattr(el, "_props", {}).get("label")
        if isinstance(lbl, str) and lbl.strip():
            texts.append(lbl.strip())
    return texts


def _has_balanced_parens(latex_str: str) -> bool:
    depth = 0
    for ch in latex_str:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


# ==============================================================================
# BLOCKER 1: Scoped Euler-Cauchy Domain Presentation & Non-EC Preservation
# ==============================================================================


def test_blocker1_domain_condition_scoped_correctly_across_ode_types() -> None:
    """Euler-Cauchy singular formatting must never hijack non-Euler-Cauchy ODEs."""
    uc = build_application()

    # 1. Euler-Cauchy with t = 0 and x = 0
    res_ec_t = uc.execute(
        ProblemRequest(
            raw_input="t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
            problem_type=ProblemType.ODE_EULER_CAUCHY,
            target_variable="t",
        )
    )
    fmt_ec_t = [
        format_domain_condition(r, "t", prob_type=ProblemType.ODE_EULER_CAUCHY)
        for r in res_ec_t.domain_restrictions
    ]
    assert any("At²" in desc and "t = 0" in desc for _, desc, _ in fmt_ec_t)
    assert any(r"\mathcal{D}_{\text{chính quy}} = (-\infty, 0) \cup (0, +\infty)" in f for _, _, f in fmt_ec_t)

    res_ec_x = uc.execute(
        ProblemRequest(
            raw_input="x^2*y'' + 4*x*y' + 2*y = 0, x > 0",
            problem_type=ProblemType.ODE_EULER_CAUCHY,
            target_variable="x",
        )
    )
    fmt_ec_x = [
        format_domain_condition(r, "x", prob_type=ProblemType.ODE_EULER_CAUCHY)
        for r in res_ec_x.domain_restrictions
    ]
    assert any("Ax²" in desc and "x = 0" in desc for _, desc, _ in fmt_ec_x)

    # 2. Reduction of Order with singular point t = 2
    res_roo = uc.execute(
        ProblemRequest(
            raw_input="(t - 2)*y'' + y' = 0, y1 = 1",
            problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
            target_variable="t",
        )
    )
    fmt_roo = [
        format_domain_condition(r, "t", prob_type=ProblemType.ODE_REDUCTION_OF_ORDER)
        for r in res_roo.domain_restrictions
    ]
    assert any("2" in formula and "t = 0" not in desc and "At²" not in desc for _, desc, formula in fmt_roo)
    assert all("t = 0" not in desc and "At²" not in desc for _, desc, _ in fmt_roo)
    assert all(_has_balanced_parens(formula) for _, _, formula in fmt_roo)

    # 3. First-Order Linear with singular point t = 2
    res_fol = uc.execute(
        ProblemRequest(
            raw_input="(t - 2)*y' + y = 0",
            problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
            target_variable="t",
        )
    )
    fmt_fol = [
        format_domain_condition(r, "t", prob_type=ProblemType.ODE_FIRST_ORDER_LINEAR)
        for r in res_fol.domain_restrictions
    ]
    assert any(r"t \ne 2" in formula for _, _, formula in fmt_fol)
    assert all("t = 0" not in desc and "At²" not in desc for _, desc, _ in fmt_fol)
    assert all(_has_balanced_parens(formula) for _, _, formula in fmt_fol)

    # 4. Classical Homogeneous with x != 0 (must produce balanced LaTeX without 0))
    res_ch = uc.execute(
        ProblemRequest(
            raw_input="y' = (x + y)/x",
            problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
            target_variable="x",
        )
    )
    fmt_ch = [
        format_domain_condition(r, "x", prob_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS)
        for r in res_ch.domain_restrictions
    ]
    assert any(r"x \ne 0" in formula for _, _, formula in fmt_ch)
    assert all("0)" not in formula and "At²" not in desc for _, desc, formula in fmt_ch)
    assert all(_has_balanced_parens(formula) for _, _, formula in fmt_ch)

    # 5. Generic restrictions without prob_type remain intact
    _, d_den, f_den = format_domain_condition("Mẫu số x + 1 != 0", "x")
    assert "x + 1" in f_den and "mẫu số" in d_den.lower()
    _, d_log, f_log = format_domain_condition("Điều kiện logarit: t > 0.", "t")
    assert "logarit" in d_log.lower() and "t > 0" in f_log
    _, d_sqrt, f_sqrt = format_domain_condition("Điều kiện xác định ban đầu: x >= 0 (căn bậc chẵn).", "x")
    assert "căn bậc chẵn" in d_sqrt.lower() and f_sqrt == r"x \ge 0"

    # Mount UI render_domain_restrictions with prob_type
    client = Client(ui.page("/test_r1_domain_view"))
    with client:
        render_domain_restrictions(
            res_roo.domain_restrictions,
            "t",
            res_roo.original_domain_latex,
            res_roo.normalized_domain_latex,
            prob_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        )
    rendered = " | ".join(_collect_texts(client))
    assert "At²" not in rendered


# ==============================================================================
# BLOCKER 2: Preserve Interval Constraints Across Workspace & State Transitions
# ==============================================================================


@pytest.mark.parametrize(
    ("interval_str", "t0_val", "expected_interval"),
    [
        ("t > 0", "1", (sp.Integer(0), sp.oo)),
        ("t < 0", "-1", (-sp.oo, sp.Integer(0))),
        ("t > 2", "3", (sp.Integer(2), sp.oo)),
        ("t < -1", "-2", (-sp.oo, sp.Integer(-1))),
        ("1 < t < 5", "2", (sp.Integer(1), sp.Integer(5))),
        ("-5 < t < -1", "-2", (sp.Integer(-5), sp.Integer(-1))),
    ],
)
def test_blocker2_state_mode_switch_and_cauchy_request_preserve_intervals(
    interval_str: str,
    t0_val: str,
    expected_interval: tuple[sp.Expr, sp.Expr],
) -> None:
    """Mode switches and Cauchy IVP ProblemRequest building must preserve explicit intervals."""
    uc = build_application()
    eq = f"t^2*y'' + 4*t*y' + 2*y = 0, {interval_str}"
    ic = f"y({t0_val}) = 3, y'({t0_val}) = 0"

    state_gen = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.EULER_CAUCHY,
        mode=ODEMode.GENERAL,
        equation=eq,
        target_var="t",
    )

    # Switch General -> Cauchy IVP -> General -> Cauchy IVP
    state_ivp = state_gen.with_mode(ODEMode.CAUCHY_IVP).with_initial_condition(ic)
    assert interval_str in state_ivp.equation

    state_back_gen = state_ivp.with_mode(ODEMode.GENERAL)
    assert interval_str in state_back_gen.equation
    assert state_back_gen.initial_condition == ""

    state_again_ivp = state_back_gen.with_mode(ODEMode.CAUCHY_IVP)
    assert interval_str in state_again_ivp.equation
    assert state_again_ivp.initial_condition == ic

    req = state_again_ivp.build_problem_request()
    assert interval_str in req.raw_input
    assert req.parameters["problem_mode"] == "CAUCHY_IVP"
    assert req.parameters["initial_condition"] == ic

    res = uc.execute(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 1
    assert res.branch_solutions[0].domain_interval == expected_interval


def test_blocker2_shifted_interval_rejects_outside_cauchy_point() -> None:
    """t > 2 paired with t0 = 1 in UI state must reach the solver and fail domain check."""
    uc = build_application()
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.EULER_CAUCHY,
        mode=ODEMode.CAUCHY_IVP,
        equation="t^2*y'' + 4*t*y' + 2*y = 0, t > 2",
        target_var="t",
        initial_condition="y(1) = 3, y'(1) = 0",
    )
    req = state.build_problem_request()
    assert "t > 2" in req.raw_input
    res = uc.execute(req)
    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert res.verification.method == "initial_condition_domain_mismatch"


def test_blocker2_euler_cauchy_example_chips_preserve_intervals_and_var() -> None:
    """Clicking every Euler-Cauchy example chip in General mode preserves its interval."""
    uc = build_application()
    op = get_operation_by_type(ProblemType.ODE_EULER_CAUCHY)
    client = Client(ui.page("/test_r1_ec_chips"))
    with client:
        render_ode_workspace(op, uc)

    chips = [el for el in client.elements.values() if isinstance(el, ui.chip)]
    inputs = [el for el in client.elements.values() if isinstance(el, ui.input)]
    eq_input = inputs[0]

    chip_by_label = {c.text: c for c in chips}
    for label, raw_val in DEFAULT_CONFIGS[ODEClassification.EULER_CAUCHY]["examples"]:
        chip = chip_by_label[label]
        with client:
            for listener in chip._event_listeners.values():
                if listener.type in ("click", None):
                    listener.handler(None)
        if "t < 0" in raw_val:
            assert "t < 0" in eq_input.value
        elif "t > 0" in raw_val:
            assert "t > 0" in eq_input.value
        else:
            # Cauchy example chip in General mode strips ICs while keeping equation
            assert "t^2*y'' + 4*t*y' + 2*y = 0" in eq_input.value

    # Verify non-Euler-Cauchy workspace state preserves equation & target variable
    cc_state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.SECOND_ORDER_HOMOGENEOUS,
        mode=ODEMode.GENERAL,
        equation="y'' + 4*y = 0",
        target_var="x",
    ).with_mode(ODEMode.CAUCHY_IVP).with_initial_condition("y(0) = 1, y'(0) = 2")
    assert cc_state.target_var == "x"
    assert cc_state.build_problem_request().problem_type == ProblemType.ODE_SECOND_ORDER_IVP


# ==============================================================================
# BLOCKER 3: Euler-Cauchy Deep-Link Routing
# ==============================================================================


@pytest.mark.parametrize(
    ("op_param", "expect_ode_workspace"),
    [
        ("ode_euler_cauchy", True),
        ("ode_second_order_constant_coeff", True),
        ("ode_second_order_ivp", True),
        ("ode_reduction_of_order", True),
        ("ode_first_order_linear", True),
        ("derivative", False),
    ],
)
def test_blocker3_deep_link_routing(op_param: str, expect_ode_workspace: bool) -> None:
    """/?op=ode_euler_cauchy must open the shared ODE workspace, never generic f(x)."""
    create_app(build_application())
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page(f"/test_r1_route_{op_param}"))
    with client:
        route.endpoint.__wrapped__(op=op_param)

    all_text = " | ".join(_collect_texts(client))
    if expect_ode_workspace:
        assert "Biểu thức toán học f(x)" not in all_text
        assert "NHẬP PHƯƠNG TRÌNH" in all_text or "Cấp 1" in all_text or "Cấp 2" in all_text
        if op_param == "ode_euler_cauchy":
            assert "Euler–Cauchy" in all_text
            assert "PHÂN LOẠI PHƯƠNG TRÌNH:" in all_text
    else:
        assert "Biểu thức toán học f(x)" in all_text


# ==============================================================================
# BLOCKER 4: Cauchy IVP Validation Card Classification & Verified Branch Badges
# ==============================================================================


def test_blocker4_validation_card_distinguishes_cauchy_errors_from_order_mismatch() -> None:
    """Missing IC and mismatched initial points must never trigger 'Phương trình không đúng cấp'."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.EULER_CAUCHY,
        mode=ODEMode.CAUCHY_IVP,
        equation="t^2*y'' + 4*t*y' + 2*y = 0",
        target_var="t",
    )

    # Case B: Missing second initial condition
    with pytest.raises(InvalidInputError) as exc_missing:
        state.with_initial_condition("y(1) = 3").build_problem_request()

    c_missing = Client(ui.page("/test_r1_case_b"))
    with c_missing:
        render_ode_validation_card(str(exc_missing.value), state)
    txt_missing = " | ".join(_collect_texts(c_missing))
    assert "Thiếu điều kiện ban đầu Cauchy (IVP)" in txt_missing
    assert "Phương trình không đúng cấp" not in txt_missing
    assert "Cần chuyển không gian làm việc" not in txt_missing

    # Case C: Mismatched initial points
    with pytest.raises(InvalidInputError) as exc_mismatch:
        state.with_initial_condition("y(1) = 3, y'(2) = 0").build_problem_request()

    c_mismatch = Client(ui.page("/test_r1_case_c"))
    with c_mismatch:
        render_ode_validation_card(str(exc_mismatch.value), state)
    txt_mismatch = " | ".join(_collect_texts(c_mismatch))
    assert "Điểm ban đầu Cauchy không nhất quán" in txt_mismatch
    assert "Phương trình không đúng cấp" not in txt_mismatch
    assert "Cần chuyển không gian làm việc" not in txt_mismatch

    # Genuine order mismatch must still render order-mismatch card
    c_order = Client(ui.page("/test_r1_genuine_order"))
    with c_order:
        render_ode_validation_card(
            "Phương trình không đúng cấp: Bạn đang nhập phương trình vi phân cấp 1, "
            "nhưng không gian làm việc hiện tại chỉ hỗ trợ phương trình vi phân cấp 2.",
            state,
        )
    txt_order = " | ".join(_collect_texts(c_order))
    assert "Phương trình không đúng cấp" in txt_order
    assert "Cần chuyển không gian làm việc" in txt_order


@pytest.mark.parametrize(
    ("v_status", "expected_color"),
    [
        (VerificationStatus.VERIFIED, "positive"),
        (VerificationStatus.UNVERIFIED, "amber-8"),
        (VerificationStatus.FAILED, "negative"),
    ],
)
def test_blocker4_branch_ic_badge_reflects_verification_status(
    v_status: VerificationStatus,
    expected_color: str,
) -> None:
    """Verified Cauchy IVP branch badge must be positive even when integration_constant_val is None."""
    t = sp.Symbol("t")
    branch = BranchSolution(
        expression=6 / t - 3 / (t**2),
        solution_str="y(t) = 6/t - 3/t**2",
        solution_latex=r"y(t) = \frac{6}{t} - \frac{3}{t^{2}}",
        branch_identity="Nhánh t > 0 (Cauchy IVP)",
        integration_constant=None,
        integration_constant_val=None,
        domain_interval=(sp.Integer(0), sp.oo),
        verification=VerificationResult(status=v_status, method="test", details="test"),
        initial_condition_status="y(1) = 3, y'(1) = 0",
    )
    client = Client(ui.page(f"/test_r1_branch_badge_{v_status.value}"))
    with client:
        render_branch_solutions((branch,), target_var="t")

    ic_badges = [
        el
        for el in client.elements.values()
        if isinstance(el, ui.badge) and el.text == "y(1) = 3, y'(1) = 0"
    ]
    assert len(ic_badges) == 1
    assert ic_badges[0]._props.get("color") == expected_color


def test_blocker4_end_to_end_valid_cauchy_and_singular_ui_rendering() -> None:
    """Case A renders verified green badges; Case D renders singular-point notice."""
    uc = build_application()
    op = get_operation_by_type(ProblemType.ODE_EULER_CAUCHY)

    # Case A: Valid Cauchy IVP
    req_a = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.EULER_CAUCHY,
        mode=ODEMode.CAUCHY_IVP,
        equation="t^2*y'' + 4*t*y' + 2*y = 0",
        target_var="t",
        initial_condition="y(1) = 3, y'(1) = 0",
    ).build_problem_request()
    res_a = uc.execute(req_a)
    assert res_a.status == SolutionStatus.SUCCESS
    assert res_a.verification.status == VerificationStatus.VERIFIED

    c_a = Client(ui.page("/test_r1_case_a_view"))
    with c_a:
        render_solution_view(res_a, op, "t", req_a.parameters)
    ic_badges = [
        el
        for el in c_a.elements.values()
        if isinstance(el, ui.badge) and el.text == "y(1) = 3, y'(1) = 0"
    ]
    assert len(ic_badges) == 1
    assert ic_badges[0]._props.get("color") == "positive"

    # Case D: Singular point t0 = 0
    req_d = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.EULER_CAUCHY,
        mode=ODEMode.CAUCHY_IVP,
        equation="t^2*y'' + 4*t*y' + 2*y = 0",
        target_var="t",
        initial_condition="y(0) = 3, y'(0) = 0",
    ).build_problem_request()
    res_d = uc.execute(req_d)
    assert res_d.status == SolutionStatus.CANNOT_SOLVE

    c_d = Client(ui.page("/test_r1_case_d_view"))
    with c_d:
        render_solution_view(res_d, op, "t", req_d.parameters)
    txt_d = " | ".join(_collect_texts(c_d))
    assert "kỳ dị" in txt_d.lower()
    assert "Phương trình không đúng cấp" not in txt_d
    assert "không tồn tại" not in txt_d.lower()


def test_blocker4_clear_condition_button_retains_icon_and_functionality() -> None:
    """Clear button preserves icon, border class compatibility, and clear behavior."""
    client = Client(ui.page("/test_r1_clear_btn"))
    ic_vals = ["y(1) = 3, y'(1) = 0"]
    with client:
        render_ode_mode_selector(
            order=ODEOrder.SECOND_ORDER,
            classification=ODEClassification.EULER_CAUCHY,
            selected_mode=ODEMode.CAUCHY_IVP,
            initial_condition=ic_vals[0],
            on_mode_change=lambda _: None,
            on_ic_change=lambda v: ic_vals.__setitem__(0, v),
        )
    btn = next(el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "Xóa điều kiện")
    assert btn.enabled is True
    assert btn._props.get("icon") == "delete_outline"
    assert "!text-slate-700" in btn._classes
    for listener in list(btn._event_listeners.values()):
        if listener.type in ("click", None):
            listener.handler(None)
    assert ic_vals[0] == ""
    assert btn.enabled is False

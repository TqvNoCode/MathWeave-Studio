"""Regression tests for ODE-UX1 Euler–Cauchy mathematical presentation & learning UX."""

from __future__ import annotations

from dataclasses import replace

import pytest
from nicegui import ui

from math_app.application.dtos import ProblemRequest, VerificationResult
from math_app.application.use_cases.solve_problem import SolveProblemUseCase
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.main import build_application
from math_app.presentation.components.domain_view import format_domain_condition, render_domain_restrictions
from math_app.presentation.components.ode_pedagogical_enhancer import (
    enhance_ode_solution_flow,
    polish_euler_cauchy_latex,
)
from math_app.presentation.components.ode_staged_step_viewer import (
    _is_meaningful_intermediate_result,
    render_ode_staged_steps_container,
)
from math_app.presentation.components.operation_catalog import get_operation_by_type
from math_app.presentation.components.problem_statement import (
    format_final_answer_latex,
    format_problem_statement_latex,
)
from math_app.presentation.components.solution_view import (
    render_ode_classification_card,
    render_solution_view,
)
from math_app.presentation.components.workspace.ode.ode_state import (
    ODEClassification,
    ODEMode,
    ODEOrder,
    ODEState,
)


@pytest.fixture
def use_case() -> SolveProblemUseCase:
    return build_application()


def test_polish_euler_cauchy_latex_converts_logs_and_signs() -> None:
    """Verify \\log becomes \\ln t / \\ln(-t) and + - / 1\\,t artifacts are cleaned."""
    assert polish_euler_cauchy_latex(r"C_{1} \cos{\left(\log{\left(t \right)} \right)}", "t") == r"C_{1} \cos{\left(\ln t \right)}"
    assert polish_euler_cauchy_latex(r"C_{2} \log{\left(- t \right)}", "t") == r"C_{2} \ln(-t)"
    assert polish_euler_cauchy_latex(r"1\,t^2\,y'' + -3\,t\,y' + 4\,y = 0", "t") == r"t^2\,y'' - 3\,t\,y' + 4\,y = 0"


def _collect_ui_labels_and_badges(root: ui.element) -> list[str]:
    texts: list[str] = []

    def _walk(el: ui.element) -> None:
        txt = getattr(el, "text", None)
        if isinstance(txt, str) and txt.strip():
            texts.append(txt.strip())
        for child in el.default_slot.children:
            if isinstance(child, ui.element):
                _walk(child)
        for slot in el.slots.values():
            for child in slot.children:
                if isinstance(child, ui.element):
                    _walk(child)

    _walk(root)
    return texts


def test_general_solution_mode_has_zero_cauchy_ivp_leakage(use_case: SolveProblemUseCase) -> None:
    """Items 1 & 3: General Solution mode shows 'Nghiệm tổng quát' and never 'Bài toán Cauchy (IVP)'."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
        target_variable="t",
        parameters={"problem_mode": "GENERAL"},
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable, req.parameters)
    assert len(stages) == 4
    stg2, stg3 = stages[1], stages[2]
    assert "Cauchy" not in stg2.transition_note
    assert stg3.subtitle == "Nghiệm tổng quát"
    assert "Bài toán Cauchy" not in stg3.subtitle
    assert stg3.summary_label == "Nghiệm tổng quát:"
    for s in stg3.steps:
        assert "Cauchy" not in s.title
        assert "điều kiện ban đầu" not in s.purpose.lower()

    with ui.column() as card:
        render_ode_classification_card(res, req.problem_type, req.parameters, target_var="t")
    badge_texts = _collect_ui_labels_and_badges(card)
    assert "Nghiệm tổng quát" in badge_texts
    assert "Bài toán Cauchy (IVP)" not in badge_texts
    assert "Cấp 2 • Euler–Cauchy" in badge_texts


def test_cauchy_ivp_mode_displays_cauchy_labels_and_linear_system(use_case: SolveProblemUseCase) -> None:
    """Item 2: Cauchy IVP mode displays 'Bài toán Cauchy (IVP)', ICs, and C1/C2 system."""
    params = {"problem_mode": "CAUCHY_IVP", "initial_condition": "y(1) = 1, y'(1) = 0"}
    req = ProblemRequest(
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
        target_variable="t",
        parameters=params,
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable, params)
    stg3 = stages[2]
    assert stg3.subtitle == "Bài toán Cauchy (IVP)"
    assert any("C_1" in s.equation_latex and "C_2" in s.equation_latex for s in stg3.steps)
    assert any(r"\begin{cases}" in s.equation_latex for s in stg3.steps)

    with ui.column() as card:
        render_ode_classification_card(res, req.problem_type, params, target_var="t")
    badge_texts = _collect_ui_labels_and_badges(card)
    assert "Bài toán Cauchy (IVP)" in badge_texts


def test_mode_switch_clears_stale_ivp_state(use_case: SolveProblemUseCase) -> None:
    """Item 3: Switching CAUCHY_IVP -> GENERAL leaves no stale initial condition or IVP subtitle."""
    state = ODEState(
        order=ODEOrder.SECOND_ORDER,
        classification=ODEClassification.EULER_CAUCHY,
        mode=ODEMode.CAUCHY_IVP,
        equation="t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
        target_var="t",
        initial_condition="y(1) = 1, y'(1) = 0",
    )
    gen_state = state.with_mode(ODEMode.GENERAL)
    assert gen_state.mode == ODEMode.GENERAL
    assert gen_state.initial_condition == ""
    req = gen_state.build_problem_request()
    assert req.parameters.get("problem_mode") == "GENERAL"
    assert "initial_condition" not in req.parameters

    res = use_case.execute(req)
    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable, req.parameters)
    assert stages[2].subtitle == "Nghiệm tổng quát"
    assert "Bài toán Cauchy" not in stages[2].subtitle


def test_ln_notation_positive_and_negative_domains(use_case: SolveProblemUseCase) -> None:
    """Items 4 & 5: \\ln t for positive domains and \\ln(-t)/(-t)^m for negative domains; no raw \\log."""
    # Scenario B: Repeated roots on positive domain
    req_rep = ProblemRequest(
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        raw_input="t^2*y'' - 3*t*y' + 4*y = 0, t > 0",
        target_variable="t",
        parameters={"problem_mode": "GENERAL"},
    )
    res_rep = use_case.execute(req_rep)
    ans_rep = format_final_answer_latex(res_rep.final_latex, req_rep.problem_type, "t", req_rep.parameters)
    assert r"\ln t" in ans_rep
    assert r"\log" not in ans_rep

    stages_rep = enhance_ode_solution_flow(res_rep, req_rep.problem_type, "t", req_rep.parameters)
    for stg in stages_rep:
        assert r"\log" not in stg.summary_latex
        for s in stg.steps:
            assert r"\log" not in s.equation_latex
            assert r"\log" not in s.description

    # Scenario C: Complex roots on positive domain
    req_cmp = ProblemRequest(
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        raw_input="t^2*y'' + t*y' + y = 0, t > 0",
        target_variable="t",
        parameters={"problem_mode": "GENERAL"},
    )
    res_cmp = use_case.execute(req_cmp)
    ans_cmp = format_final_answer_latex(res_cmp.final_latex, req_cmp.problem_type, "t", req_cmp.parameters)
    assert r"\ln t" in ans_cmp
    assert r"\log" not in ans_cmp

    # Complex roots on negative domain t < 0 -> \ln(-t) and (-t)^m
    req_neg = ProblemRequest(
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        raw_input="t^2*y'' + t*y' + y = 0, t < 0",
        target_variable="t",
        parameters={"problem_mode": "GENERAL"},
    )
    res_neg = use_case.execute(req_neg)
    ans_neg = format_final_answer_latex(res_neg.final_latex, req_neg.problem_type, "t", req_neg.parameters)
    assert r"\ln(-t)" in ans_neg
    assert r"\log" not in ans_neg

    stages_neg = enhance_ode_solution_flow(res_neg, req_neg.problem_type, "t", req_neg.parameters)
    assert "(-t)^m" in stages_neg[0].steps[1].equation_latex


def test_pedagogical_deduplication_and_symbol_consistency(use_case: SolveProblemUseCase) -> None:
    """Items 6, 7 & 8: No duplicate derivatives/Wronskian; consistent A, B, C, m, \\Delta symbols."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
        target_variable="t",
        parameters={"problem_mode": "GENERAL"},
    )
    res = use_case.execute(req)
    stages = enhance_ode_solution_flow(res, req.problem_type, "t", req.parameters)

    # Item 6: Step 2 derivative formulas appear once in equation_latex and NOT repeated in description
    step2 = stages[0].steps[1]
    assert step2.equation_latex.count("y'(t)") == 1
    assert "y'(t)" not in step2.description
    assert "y''(t)" not in step2.description
    assert _is_meaningful_intermediate_result(step2) is False
    assert _is_meaningful_intermediate_result(stages[0].steps[2]) is False

    # Item 7: Step 4 uses A, B, C, m, Delta consistently (no ambiguous a = ..., b = B - A, c = ...)
    step4 = stages[1].steps[0]
    assert "$a =" not in step4.description
    assert "$b =" not in step4.description
    assert "$c =" not in step4.description
    assert r"\Delta = (B - A)^2 - 4AC" in step4.equation_latex

    # Item 8: Step 5 Wronskian shown once in equation_latex and not duplicated in description
    step5 = stages[1].steps[1]
    assert step5.equation_latex.count("W(y_1, y_2)") == 1
    assert step5.description.count("W(y_1, y_2)") == 0
    assert _is_meaningful_intermediate_result(step5) is False


@pytest.mark.parametrize(
    ("v_status", "expected_completed", "expected_has_equiv_zero"),
    [
        (VerificationStatus.VERIFIED, True, True),
        (VerificationStatus.UNVERIFIED, False, False),
        (VerificationStatus.FAILED, False, False),
    ],
)
def test_verification_status_propagation_preserved(
    use_case: SolveProblemUseCase,
    v_status: VerificationStatus,
    expected_completed: bool,
    expected_has_equiv_zero: bool,
) -> None:
    """Item 9: EC1-R1 verification states remain strictly faithful."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
        target_variable="t",
        parameters={"problem_mode": "GENERAL"},
    )
    base_res = use_case.execute(req)
    patched = replace(
        base_res,
        verification=VerificationResult(
            status=v_status,
            method="mock",
            details=f"Status {v_status.value}",
        ),
    )
    stages = enhance_ode_solution_flow(patched, req.problem_type, "t", req.parameters)
    stg4 = stages[3]
    assert stg4.is_completed is expected_completed
    assert (r"\equiv 0" in stg4.summary_latex) is expected_has_equiv_zero
    if v_status == VerificationStatus.FAILED:
        assert r"\not\equiv 0" in stg4.steps[-1].equation_latex
    elif v_status == VerificationStatus.UNVERIFIED:
        assert r"\equiv 0" not in stg4.steps[-1].equation_latex


def test_domain_explanation_distinguishes_singular_point_and_interval(use_case: SolveProblemUseCase) -> None:
    """Item 10: Domain explanation avoids absolute non-continuity overstatement."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
        target_variable="t",
        parameters={"problem_mode": "GENERAL"},
    )
    res = use_case.execute(req)
    formatted = [format_domain_condition(d, "t") for d in res.domain_restrictions]
    descs = " | ".join(item[1] for item in formatted)
    assert "Điểm kỳ dị tại t = 0" in descs
    assert "không liên tục qua điểm này" not in descs
    assert any(item[2] == "t > 0" for item in formatted)

    # Also verify UI mounting of domain view
    with ui.column() as dom_box:
        render_domain_restrictions(
            res.domain_restrictions,
            "t",
            res.original_domain_latex,
            res.normalized_domain_latex,
        )
    assert dom_box is not None


def test_ui_renders_all_scenarios_with_stage1_expanded_and_minimal_badges(use_case: SolveProblemUseCase) -> None:
    """Item 11: Full UI mounting across distinct, repeated, complex, negative, IVP, and unsupported cases."""
    scenarios = [
        ("t^2*y'' + 4*t*y' + 2*y = 0, t > 0", {"problem_mode": "GENERAL"}),
        ("t^2*y'' - 3*t*y' + 4*y = 0, t > 0", {"problem_mode": "GENERAL"}),
        ("t^2*y'' + t*y' + y = 0, t > 0", {"problem_mode": "GENERAL"}),
        ("t^2*y'' + 4*t*y' + 2*y = 0, t < 0", {"problem_mode": "GENERAL"}),
        ("t^2*y'' + 4*t*y' + 2*y = 0, t > 0", {"problem_mode": "CAUCHY_IVP", "initial_condition": "y(1)=1, y'(1)=0"}),
        ("t^2*y'' + 4*t*y' + 2*y = 0, -1 < t < 1", {"problem_mode": "GENERAL"}),
    ]
    op = get_operation_by_type(ProblemType.ODE_EULER_CAUCHY)
    for raw_eq, params in scenarios:
        req = ProblemRequest(
            problem_type=ProblemType.ODE_EULER_CAUCHY,
            raw_input=raw_eq,
            target_variable="t",
            parameters=params,
        )
        res = use_case.execute(req)
        with ui.column() as container:
            render_solution_view(res, op, "t", params)
        assert container is not None

        if res.status == SolutionStatus.SUCCESS:
            stages = enhance_ode_solution_flow(res, req.problem_type, "t", params)
            with ui.column() as stage_box:
                render_ode_staged_steps_container(stages, final_answer_latex=res.final_latex)
            expansions = [
                el
                for el in stage_box.descendants()
                if isinstance(el, ui.expansion) and "Mở rộng" not in getattr(el, "text", "")
            ]
            # First 4 stage expansions: Stage 1 open, Stages 2-4 collapsed by default
            stage_exps = [e for e in expansions if any("looks_" in getattr(c, "_props", {}).get("name", "") for c in e.descendants())]
            assert len(stage_exps) == 4
            assert stage_exps[0].value is True
            assert all(e.value is False for e in stage_exps[1:])

            # Statement includes explicit interval when given
            stmt = format_problem_statement_latex(raw_eq, ProblemType.ODE_EULER_CAUCHY, "t", params)
            assert ">" in stmt or "<" in stmt

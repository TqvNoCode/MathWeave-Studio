"""Unit and presentation tests for Milestone 4 (M4 & M4.1-A2):
Second-Order ODE Method Selection UI, Screen B State Integrity & Request Reliability.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock
import pytest
from nicegui import Client, app, core, ui
import sympy as sp

from math_app.application.dtos import (
    ExpressionStepContent,
    ProblemRequest,
    SolutionResponse,
    SolutionStep,
    VerificationResult,
)
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.input.ode_parser import extract_second_order_ics_from_string
from math_app.main import build_application
from math_app.presentation.app import (
    build_second_order_problem_request,
    create_app,
)
from math_app.presentation.components.operation_catalog import (
    get_operation_by_type,
    get_second_order_examples,
)
from math_app.solvers.calculus.ode.second_order_constant_coeff_solver import (
    ODESecondOrderConstantCoeffSolver,
)
from math_app.presentation.components.problem_statement import (
    format_problem_statement_latex,
    get_result_card_title,
)
from math_app.presentation.components.solution_view import (
    render_solution_view,
)


def test_operation_2_catalog_definition():
    """Verify Operation 2 card is fully upgraded for Milestone 4."""
    op = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)
    assert op.is_menu_card is True
    assert op.math_icon == r"ay'' + by' + cy = g(t)"
    assert op.default_input == "y'' - 3*y' - 4*y = 3*exp(2*t)"
    assert "thuần nhất và không thuần nhất" in op.description
    assert "hệ số bất định" in op.description
    assert "biến thiên hằng số" in op.description
    assert "bài toán cauchy" in op.description.lower()
    assert "initial_condition" in op.extra_fields
    assert "method_preference" in op.extra_fields

    # Verify all representative examples exist
    example_labels = [lbl for lbl, _ in op.examples]
    assert any("đa thức" in lbl.lower() for lbl in example_labels)
    assert any("mũ" in lbl.lower() for lbl in example_labels)
    assert any("cộng hưởng mũ" in lbl.lower() for lbl in example_labels)
    assert any("cộng hưởng lượng giác" in lbl.lower() for lbl in example_labels)
    assert any("tan" in lbl.lower() for lbl in example_labels)
    assert any("ln" in lbl.lower() for lbl in example_labels)
    assert any("1/t" in lbl.lower() for lbl in example_labels)
    assert any("cauchy" in lbl.lower() or "ivp" in lbl.lower() for lbl in example_labels)
    assert any("delta > 0" in lbl.lower() for lbl in example_labels)
    assert any("phức" in lbl.lower() for lbl in example_labels)
    assert len(op.examples) >= 10


def test_operation_ivp_catalog_definition():
    """Verify Cauchy IVP operation card configuration."""
    op = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_IVP)
    assert op.is_menu_card is False
    assert "cauchy" in op.title.lower() or "ivp" in op.title.lower()
    assert "initial_condition" in op.extra_fields
    assert "method_preference" in op.extra_fields
    assert len(op.examples) >= 5


def test_screen_b_ode_problem_statement_formatting():
    """Verify clean LaTeX problem statement for second-order ODE and IVP."""
    # General nonhomogeneous ODE
    stmt1 = format_problem_statement_latex(
        raw_input="y'' - 3*y' - 4*y = 3*exp(2*t)",
        op_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_var="t",
    )
    assert "\\frac{d^2y}{dt^2}" in stmt1
    assert "\\frac{dy}{dt}" in stmt1

    # Cauchy IVP inline
    stmt2 = format_problem_statement_latex(
        raw_input="y'' - 3*y' - 4*y = 3*exp(2*t), y(0) = 1, y'(0) = 0",
        op_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_var="t",
    )
    assert "\\frac{d^2y}{dt^2}" in stmt2
    assert "y(0) = 1" in stmt2
    assert "y'(0) = 0" in stmt2

    # Result card title
    assert get_result_card_title(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF) == "KẾT QUẢ PHƯƠNG TRÌNH VI PHÂN CẤP 2"
    assert get_result_card_title(ProblemType.ODE_SECOND_ORDER_IVP) == "KẾT QUẢ BÀI TOÁN CAUCHY CẤP 2"


def test_screen_b_ode_solution_view_rendering_uc():
    """Verify Screen B solution view rendering for Undetermined Coefficients solution."""
    op = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)
    steps = (
        SolutionStep(
            step_number=1,
            rule_name="Hệ nghiệm cơ bản",
            title="Xây dựng hệ nghiệm cơ bản",
            description="Nghiệm thuần nhất",
            content=ExpressionStepContent(
                expression_before="char_eq",
                expression_after="y(t) = C1*exp(-t) + C2*exp(4*t)",
                latex_before="r^2 - 3r - 4 = 0",
                latex_after=r"y(t) = C_{1} e^{-t} + C_{2} e^{4 t}",
            ),
        ),
        SolutionStep(
            step_number=2,
            rule_name="Phương pháp hệ số bất định",
            title="Tìm nghiệm riêng bằng phương pháp Hệ số bất định",
            description="Tìm nghiệm riêng Y_p",
            content=ExpressionStepContent(
                expression_before="Y_p dự kiến",
                expression_after="Y_p = -1/2*exp(2*t)",
                latex_before="Y_p(t) = A e^{2t}",
                latex_after=r"Y_p(t) = -\frac{1}{2} e^{2 t}",
            ),
        ),
    )
    response = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "ODEVerifier", "R(t) = 0"),
        raw_input="y'' - 3*y' - 4*y = 3*exp(2*t)",
        canonical_input="y'' - 3*y' - 4*y = 3*exp(2*t)",
        final_result="y(t) = C1*exp(-t) + C2*exp(4*t) - 1/2*exp(2*t)",
        final_latex=r"y(t) = C_{1} e^{-t} + C_{2} e^{4 t} - \frac{1}{2} e^{2 t}",
        steps=steps,
    )
    with ui.card():
        render_solution_view(response, op, "t", {"method_preference": "AUTO"})


def test_screen_b_ode_solution_view_rendering_vop():
    """Verify Screen B solution view rendering for Variation of Parameters solution."""
    op = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)
    steps = (
        SolutionStep(
            step_number=1,
            rule_name="Hệ nghiệm cơ bản",
            title="Xây dựng hệ nghiệm cơ bản",
            description="Nghiệm thuần nhất",
            content=ExpressionStepContent(
                expression_before="char_eq",
                expression_after="y(t) = C1*cos(t) + C2*sin(t)",
                latex_before="r^2 + 1 = 0",
                latex_after=r"y(t) = C_{1} \cos(t) + C_{2} \sin(t)",
            ),
        ),
        SolutionStep(
            step_number=2,
            rule_name="Phương pháp biến thiên hằng số",
            title="Tìm nghiệm riêng bằng phương pháp Biến thiên hằng số",
            description="Tính Wronskian và tích phân u1, u2",
            content=ExpressionStepContent(
                expression_before="Wronskian",
                expression_after="Y_p = -cos(t)*log(sec(t) + tan(t))",
                latex_before="W(y_1, y_2) = 1",
                latex_after=r"Y_p(t) = -\cos(t) \ln|\sec(t) + \tan(t)|",
            ),
        ),
    )
    response = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "ODEVerifier", "R(t) = 0"),
        raw_input="y'' + y = tan(t)",
        canonical_input="y'' + y = tan(t)",
        final_result="y(t) = C1*cos(t) + C2*sin(t) - cos(t)*log(sec(t) + tan(t))",
        final_latex=r"y(t) = C_{1} \cos(t) + C_{2} \sin(t) - \cos(t) \ln|\sec(t) + \tan(t)|",
        steps=steps,
    )
    with ui.card():
        render_solution_view(response, op, "t", {"method_preference": "VARIATION_OF_PARAMETERS"})


def test_screen_b_ode_solution_view_rendering_cauchy_ivp():
    """Verify Screen B solution view rendering for Cauchy Initial Value Problem."""
    op = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_IVP)
    steps = (
        SolutionStep(
            step_number=1,
            rule_name="Hệ nghiệm cơ bản",
            title="Xây dựng hệ nghiệm cơ bản",
            description="Nghiệm thuần nhất",
            content=ExpressionStepContent(
                expression_before="char_eq",
                expression_after="y(t) = C1*exp(-t) + C2*exp(4*t)",
                latex_before="r^2 - 3r - 4 = 0",
                latex_after=r"y(t) = C_{1} e^{-t} + C_{2} e^{4 t}",
            ),
        ),
        SolutionStep(
            step_number=2,
            rule_name="Phương pháp hệ số bất định",
            title="Nghiệm riêng Y_p",
            description="Tìm nghiệm riêng",
            content=ExpressionStepContent(
                expression_before="Y_p dự kiến",
                expression_after="Y_p = -1/2*exp(2*t)",
                latex_before="Y_p",
                latex_after=r"Y_p(t) = -\frac{1}{2} e^{2 t}",
            ),
        ),
        SolutionStep(
            step_number=3,
            rule_name="Giải hệ Cauchy",
            title="Xác định các hằng số C1, C2 từ điều kiện ban đầu Cauchy",
            description="Hệ đại số tuyến tính",
            content=ExpressionStepContent(
                expression_before="y(0) = 1, y'(0) = 0",
                expression_after="C1 = 6/5, C2 = 3/10",
                latex_before=r"y(0) = 1, \quad y'(0) = 0",
                latex_after=r"C_1 = \frac{6}{5}, \quad C_2 = \frac{3}{10}",
            ),
        ),
    )
    response = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "ODEVerifier", "R(t) = 0, y(0) = 1, y'(0) = 0"),
        raw_input="y'' - 3*y' - 4*y = 3*exp(2*t), y(0) = 1, y'(0) = 0",
        canonical_input="y'' - 3*y' - 4*y = 3*exp(2*t)",
        final_result="y(t) = 6/5*exp(-t) + 3/10*exp(4*t) - 1/2*exp(2*t)",
        final_latex=r"y(t) = \frac{6}{5} e^{-t} + \frac{3}{10} e^{4 t} - \frac{1}{2} e^{2 t}",
        steps=steps,
    )
    with ui.card():
        render_solution_view(response, op, "t", {"initial_condition": "y(0) = 1, y'(0) = 0"})


def test_screen_b_ode_solution_view_cannot_solve():
    """Verify Screen B rendering for CANNOT_SOLVE response."""
    op = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)
    response = SolutionResponse(
        status=SolutionStatus.CANNOT_SOLVE,
        verification=VerificationResult(
            VerificationStatus.NOT_APPLICABLE,
            "undetermined_coefficients_unsupported",
            "tan(t) không thuộc dạng hàm thích hợp cho hệ số bất định.",
        ),
        raw_input="y'' + y = tan(t)",
        canonical_input="y'' + y = tan(t)",
        final_result="",
        final_latex="",
        warnings=("Vế phải tan(t) không giải được bằng phương pháp hệ số bất định.",),
    )
    with ui.card():
        render_solution_view(response, op, "t", {"method_preference": "UNDETERMINED_COEFFICIENTS"})


def test_get_second_order_examples_all_modes():
    """Verify get_second_order_examples returns appropriate examples for all 4 combinations."""
    # 1. Homogeneous + General
    homo_gen = get_second_order_examples("HOMOGENEOUS", "GENERAL")
    assert len(homo_gen) >= 5
    for label, eq in homo_gen:
        assert "= 0" in eq
        assert "y(" not in eq  # No initial conditions in general mode

    # 2. Homogeneous + Cauchy IVP
    homo_ivp = get_second_order_examples("HOMOGENEOUS", "CAUCHY_IVP")
    assert len(homo_ivp) >= 3
    for label, eq in homo_ivp:
        assert "= 0" in eq
        assert "y(" in eq  # Must include initial conditions

    # 3. Nonhomogeneous + General
    nonhomo_gen = get_second_order_examples("NONHOMOGENEOUS", "GENERAL")
    assert len(nonhomo_gen) >= 6
    for label, eq in nonhomo_gen:
        assert "= 0" not in eq  # Forcing term present
        assert "y(" not in eq  # No initial conditions in general mode

    # 4. Nonhomogeneous + Cauchy IVP
    nonhomo_ivp = get_second_order_examples("NONHOMOGENEOUS", "CAUCHY_IVP")
    assert len(nonhomo_ivp) >= 3
    for label, eq in nonhomo_ivp:
        eq_part = eq.split(",")[0]
        assert "= 0" not in eq_part  # Forcing term present in differential equation
        assert "y(" in eq  # Must include initial conditions


def test_second_order_classification_mismatch_solver():
    """Verify solver properly flags classification mismatches with Vietnamese guidance."""
    solver = ODESecondOrderConstantCoeffSolver()

    # Case A: User in Homogeneous mode but passes nonhomogeneous equation
    req_a = ProblemRequest(
        raw_input="y'' - 3*y' - 4*y = 3*exp(2*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
        parameters={"expected_classification": "HOMOGENEOUS", "problem_mode": "GENERAL"},
    )
    res_a = solver.solve(req_a)
    assert res_a.status == SolutionStatus.CANNOT_SOLVE
    assert res_a.verification.method == "classification_mismatch"
    assert "chế độ 'Phương trình vi phân cấp 2 thuần nhất'" in res_a.warnings[0]
    assert "khác 0" in res_a.warnings[0]

    # Case B: User in Nonhomogeneous mode but passes homogeneous equation
    req_b = ProblemRequest(
        raw_input="y'' - 3*y' - 4*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
        parameters={"expected_classification": "NONHOMOGENEOUS", "problem_mode": "GENERAL"},
    )
    res_b = solver.solve(req_b)
    assert res_b.status == SolutionStatus.CANNOT_SOLVE
    assert res_b.verification.method == "classification_mismatch"
    assert "chế độ 'Phương trình vi phân cấp 2 không thuần nhất'" in res_b.warnings[0]
    assert "vế phải bằng 0" in res_b.warnings[0]


def test_screen_b_ode_solution_view_rendering_homogeneous_general():
    """Verify Screen B rendering for homogeneous general solution."""
    op = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)
    steps = (
        SolutionStep(
            step_number=1,
            rule_name="Hệ nghiệm cơ bản",
            title="Xây dựng hệ nghiệm cơ bản",
            description="Nghiệm thuần nhất",
            content=ExpressionStepContent(
                expression_before="char_eq",
                expression_after="y(t) = C1*exp(-t) + C2*exp(4*t)",
                latex_before="r^2 - 3r - 4 = 0",
                latex_after=r"y(t) = C_{1} e^{-t} + C_{2} e^{4 t}",
            ),
        ),
    )
    response = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "ODEVerifier", "R(t) = 0"),
        raw_input="y'' - 3*y' - 4*y = 0",
        canonical_input="y'' - 3*y' - 4*y = 0",
        final_result="y(t) = C1*exp(-t) + C2*exp(4*t)",
        final_latex=r"y(t) = C_{1} e^{-t} + C_{2} e^{4 t}",
        steps=steps,
    )
    with ui.card():
        render_solution_view(
            response,
            op,
            "t",
            {"expected_classification": "HOMOGENEOUS", "problem_mode": "GENERAL"},
        )


def test_screen_b_ode_solution_view_rendering_homogeneous_cauchy():
    """Verify Screen B rendering for homogeneous Cauchy IVP."""
    op = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_IVP)
    steps = (
        SolutionStep(
            step_number=1,
            rule_name="Hệ nghiệm cơ bản",
            title="Xây dựng hệ nghiệm cơ bản",
            description="Nghiệm thuần nhất",
            content=ExpressionStepContent(
                expression_before="char_eq",
                expression_after="y(t) = C1*cos(2*t) + C2*sin(2*t)",
                latex_before="r^2 + 4 = 0",
                latex_after=r"y(t) = C_{1} \cos(2t) + C_{2} \sin(2t)",
            ),
        ),
        SolutionStep(
            step_number=2,
            rule_name="Giải hệ Cauchy",
            title="Xác định C1, C2 từ điều kiện ban đầu",
            description="Hệ đại số Cauchy",
            content=ExpressionStepContent(
                expression_before="y(0) = 0, y'(0) = 2",
                expression_after="C1 = 0, C2 = 1",
                latex_before=r"y(0) = 0, \quad y'(0) = 2",
                latex_after=r"C_1 = 0, \quad C_2 = 1",
            ),
        ),
    )
    response = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "ODEVerifier", "R(t) = 0, y(0) = 0, y'(0) = 2"),
        raw_input="y'' + 4*y = 0, y(0) = 0, y'(0) = 2",
        canonical_input="y'' + 4*y = 0",
        final_result="y(t) = sin(2*t)",
        final_latex=r"y(t) = \sin(2 t)",
        steps=steps,
    )
    with ui.card():
        render_solution_view(
            response,
            op,
            "t",
            {
                "expected_classification": "HOMOGENEOUS",
                "problem_mode": "CAUCHY_IVP",
                "initial_condition": "y(0) = 0, y'(0) = 2",
            },
        )


def test_screen_b_navigation_and_crash_prevention():
    """Verify navigating from Screen A to Screen B for ODE_SECOND_ORDER_CONSTANT_COEFF
    executes cleanly without UnboundLocalError (solve_button scoping fix).
    """
    use_case = build_application()
    create_app(use_case)

    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page("/test_nav"))
    with client:
        route.endpoint.__wrapped__()

    # Find the catalog card for second-order ODE and trigger its navigation handler
    found = False
    for eid, el in client.elements.items():
        for listener in el._event_listeners.values():
            defaults = getattr(listener.handler, "__defaults__", ())
            if defaults:
                for d in defaults:
                    if hasattr(d, "problem_type") and d.problem_type == ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF:
                        with client:
                            listener.handler(None)
                        found = True
                        break
            if found:
                break
        if found:
            break

    assert found is True, "Catalog card for ODE_SECOND_ORDER_CONSTANT_COEFF was not found"


def _navigate_to_screen_b(client: Client) -> None:
    for eid, el in list(client.elements.items()):
        for listener in list(el._event_listeners.values()):
            defaults = getattr(listener.handler, "__defaults__", ())
            if defaults:
                for d in defaults:
                    if hasattr(d, "problem_type") and d.problem_type == ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF:
                        with client:
                            listener.handler(None)
                        return
    raise RuntimeError("Catalog card for ODE_SECOND_ORDER_CONSTANT_COEFF was not found")


def _trigger_card_handler(client: Client, handler_name: str) -> bool:
    for el in client.elements.values():
        if isinstance(el, ui.card):
            for listener in list(el._event_listeners.values()):
                if getattr(listener.handler, "__name__", "") == handler_name:
                    with client:
                        listener.handler(None)
                    return True
    return False


def _trigger_button_by_text(client: Client, text: str) -> bool:
    for el in client.elements.values():
        if isinstance(el, ui.button) and el.text == text:
            for listener in list(el._event_listeners.values()):
                if listener.type in ("click", None):
                    with client:
                        listener.handler(None)
                    return True
    return False


def test_build_second_order_problem_request_all_modes():
    """Verify build_second_order_problem_request produces exact ProblemRequests for all 4 combinations."""
    # 1. Homogeneous + General
    r1 = build_second_order_problem_request("y'' - 3*y' - 4*y = 0", "HOMOGENEOUS", "GENERAL", "", "AUTO", "t")
    assert r1.raw_input == "y'' - 3*y' - 4*y = 0"
    assert r1.problem_type == ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF
    assert r1.target_variable == "t"
    assert r1.parameters == {"expected_classification": "HOMOGENEOUS", "problem_mode": "GENERAL"}

    # 2. Homogeneous + Cauchy IVP
    r2 = build_second_order_problem_request("y'' + 4*y = 0", "HOMOGENEOUS", "CAUCHY_IVP", "y(0) = 0, y'(0) = 2", "AUTO", "t")
    assert r2.raw_input == "y'' + 4*y = 0"
    assert r2.problem_type == ProblemType.ODE_SECOND_ORDER_IVP
    assert r2.target_variable == "t"
    assert r2.parameters["expected_classification"] == "HOMOGENEOUS"
    assert r2.parameters["problem_mode"] == "CAUCHY_IVP"
    assert r2.parameters["initial_condition"] == "y(0) = 0, y'(0) = 2"

    # 3. Nonhomogeneous + General
    r3 = build_second_order_problem_request("y'' + y = tan(t)", "NONHOMOGENEOUS", "GENERAL", "", "VARIATION_OF_PARAMETERS", "x")
    assert r3.raw_input == "y'' + y = tan(t)"
    assert r3.problem_type == ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF
    assert r3.target_variable == "x"
    assert r3.parameters["method_preference"] == "VARIATION_OF_PARAMETERS"

    # 4. Nonhomogeneous + Cauchy IVP
    r4 = build_second_order_problem_request(
        "y'' - 3*y' - 4*y = 3*exp(2*t)",
        "NONHOMOGENEOUS",
        "CAUCHY_IVP",
        "y(0) = 1, y'(0) = 0",
        "UNDETERMINED_COEFFICIENTS",
        "t",
    )
    assert r4.raw_input == "y'' - 3*y' - 4*y = 3*exp(2*t)"
    assert r4.problem_type == ProblemType.ODE_SECOND_ORDER_IVP
    assert r4.parameters["method_preference"] == "UNDETERMINED_COEFFICIENTS"
    assert r4.parameters["initial_condition"] == "y(0) = 1, y'(0) = 0"


def test_build_second_order_problem_request_mandatory_conflict_rejection():
    """Verify that conflicting inline conditions and dedicated input field conditions
    are caught and rejected with explicit Vietnamese validation error (mandatory regression case).
    """
    with pytest.raises(InvalidInputError) as exc_info:
        build_second_order_problem_request(
            equation="y'' + y = tan(t), y(0) = 0, y'(0) = 2",
            category="NONHOMOGENEOUS",
            mode="CAUCHY_IVP",
            initial_condition="y(0) = 1, y'(0) = 0",
            method_pref="AUTO",
            target_var="t",
        )
    err_msg = str(exc_info.value)
    assert "xung đột" in err_msg.lower()
    assert "y(0) = 0, y'(0) = 2" in err_msg
    assert "y(0) = 1, y'(0) = 0" in err_msg


def test_build_second_order_problem_request_inline_import_when_dedicated_empty():
    """Verify that if dedicated initial condition is empty, complete inline conditions
    are cleanly imported into parameters['initial_condition'] and raw_input is normalized.
    """
    req = build_second_order_problem_request(
        equation="y'' + 4*y = 0, y(0) = 0, y'(0) = 2",
        category="HOMOGENEOUS",
        mode="CAUCHY_IVP",
        initial_condition="",
        method_pref="AUTO",
        target_var="t",
    )
    assert req.raw_input == "y'' + 4*y = 0"
    assert req.problem_type == ProblemType.ODE_SECOND_ORDER_IVP
    assert req.parameters["initial_condition"] == "y(0) = 0, y'(0) = 2"


def test_build_second_order_problem_request_missing_ic_rejected():
    """Verify that Cauchy IVP mode rejects missing or incomplete conditions."""
    # Empty everywhere
    with pytest.raises(InvalidInputError) as exc_info1:
        build_second_order_problem_request(
            equation="y'' + 4*y = 0",
            category="HOMOGENEOUS",
            mode="CAUCHY_IVP",
            initial_condition="",
        )
    assert "y(t0) = y0 và y'(t0) = v0" in str(exc_info1.value)

    # Incomplete dedicated condition
    with pytest.raises(InvalidInputError) as exc_info2:
        build_second_order_problem_request(
            equation="y'' + 4*y = 0",
            category="HOMOGENEOUS",
            mode="CAUCHY_IVP",
            initial_condition="y(0) = 1",
        )
    assert "y(t0) = y0 và y'(t0) = v0" in str(exc_info2.value)

    # Empty equation
    with pytest.raises(InvalidInputError):
        build_second_order_problem_request(
            equation="   ",
            category="HOMOGENEOUS",
            mode="GENERAL",
        )


def test_screen_b_real_rendering_all_four_configurations():
    """Verify true Client rendering across all four Screen B states:
    1. Homogeneous + General
    2. Nonhomogeneous + General
    3. Nonhomogeneous + Cauchy IVP
    4. Homogeneous + Cauchy IVP
    """
    create_app(build_application())
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page("/test_screen_b_all_4_states"))
    with client:
        route.endpoint.__wrapped__()

    _navigate_to_screen_b(client)

    # State 1: Homogeneous + General
    radios_1 = [el for el in client.elements.values() if isinstance(el, ui.radio)]
    assert len(radios_1) == 0, "Homogeneous mode should not render method radio"
    inputs_1 = [el for el in client.elements.values() if isinstance(el, ui.input)]
    assert len(inputs_1) == 2, f"Expected 2 inputs (eq, var), got {len(inputs_1)}"
    labels_1 = [el.text for el in client.elements.values() if isinstance(el, ui.label)]
    assert any("Phương trình thuần nhất" in text_lbl for text_lbl in labels_1)

    # State 2: Nonhomogeneous + General
    assert _trigger_card_handler(client, "on_select_nonhomo") is True
    radios_2 = [el for el in client.elements.values() if isinstance(el, ui.radio)]
    assert len(radios_2) == 1, "Nonhomogeneous mode must render method preference radio"
    assert radios_2[0].value == "AUTO"
    inputs_2 = [el for el in client.elements.values() if isinstance(el, ui.input)]
    assert len(inputs_2) == 2, "General mode should not render initial condition input"

    # State 3: Nonhomogeneous + Cauchy IVP
    assert _trigger_button_by_text(client, "Bài toán Cauchy (IVP)") is True
    radios_3 = [el for el in client.elements.values() if isinstance(el, ui.radio)]
    assert len(radios_3) == 1, "Nonhomogeneous Cauchy mode must render method preference radio"
    inputs_3 = [el for el in client.elements.values() if isinstance(el, ui.input)]
    assert len(inputs_3) == 3, f"Expected 3 inputs (eq, var, ic), got {len(inputs_3)}"
    ic_input = [inp for inp in inputs_3 if "y(t0)" in inp._props.get("label", "")][0]
    assert ic_input.value == "", "New Cauchy mode should start with empty initial conditions (no stale default)"
    assert "Ví dụ: y(0) = 1, y'(0) = 0" in ic_input._props.get("placeholder", "")

    # State 4: Homogeneous + Cauchy IVP
    assert _trigger_card_handler(client, "on_select_homo") is True
    radios_4 = [el for el in client.elements.values() if isinstance(el, ui.radio)]
    assert len(radios_4) == 0, "Homogeneous Cauchy mode should not render method radio"
    inputs_4 = [el for el in client.elements.values() if isinstance(el, ui.input)]
    assert len(inputs_4) == 3, "Homogeneous Cauchy mode must keep initial condition input visible"


def test_screen_b_scenario_a_method_preference_persistence():
    """Scenario A: Method preference persistence across GENERAL <-> CAUCHY_IVP rerenders."""
    create_app(build_application())
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page("/test_scenario_a"))
    with client:
        route.endpoint.__wrapped__()

    _navigate_to_screen_b(client)
    _trigger_card_handler(client, "on_select_nonhomo")

    # Select Variation of Parameters
    radio = [el for el in client.elements.values() if isinstance(el, ui.radio)][0]
    with client:
        radio.set_value("VARIATION_OF_PARAMETERS")

    # Switch GENERAL -> CAUCHY_IVP
    _trigger_button_by_text(client, "Bài toán Cauchy (IVP)")
    radio_ivp = [el for el in client.elements.values() if isinstance(el, ui.radio)][0]
    assert radio_ivp.value == "VARIATION_OF_PARAMETERS", "Method preference must persist into Cauchy mode"

    # Switch CAUCHY_IVP -> GENERAL
    _trigger_button_by_text(client, "Tìm nghiệm tổng quát")
    radio_gen = [el for el in client.elements.values() if isinstance(el, ui.radio)][0]
    assert radio_gen.value == "VARIATION_OF_PARAMETERS", "Method preference must persist back into General mode"


def test_screen_b_scenario_b_cauchy_conditions_persistence():
    """Scenario B: Cauchy conditions persistence across category transitions."""
    create_app(build_application())
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page("/test_scenario_b"))
    with client:
        route.endpoint.__wrapped__()

    _navigate_to_screen_b(client)
    _trigger_card_handler(client, "on_select_nonhomo")
    _trigger_button_by_text(client, "Bài toán Cauchy (IVP)")

    ic_input = [el for el in client.elements.values() if isinstance(el, ui.input) and "y(t0)" in el._props.get("label", "")][0]
    with client:
        ic_input.set_value("y(1) = 2, y'(1) = 3")

    # Switch NONHOMOGENEOUS -> HOMOGENEOUS
    _trigger_card_handler(client, "on_select_homo")
    ic_input_homo = [el for el in client.elements.values() if isinstance(el, ui.input) and "y(t0)" in el._props.get("label", "")][0]
    assert ic_input_homo.value == "y(1) = 2, y'(1) = 3", "Cauchy conditions must be preserved across category switch"

    # Switch back to NONHOMOGENEOUS
    _trigger_card_handler(client, "on_select_nonhomo")
    ic_input_nonhomo = [el for el in client.elements.values() if isinstance(el, ui.input) and "y(t0)" in el._props.get("label", "")][0]
    assert ic_input_nonhomo.value == "y(1) = 2, y'(1) = 3", "Cauchy conditions must remain preserved"


def test_screen_b_scenario_c_independent_variable_persistence():
    """Scenario C: Independent variable persistence (t -> x) across workflow switches."""
    create_app(build_application())
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page("/test_scenario_c"))
    with client:
        route.endpoint.__wrapped__()

    _navigate_to_screen_b(client)
    var_input = [el for el in client.elements.values() if isinstance(el, ui.input) and "Biến số" in el._props.get("label", "")][0]
    with client:
        var_input.set_value("x")

    # Switch to Cauchy IVP
    _trigger_button_by_text(client, "Bài toán Cauchy (IVP)")
    var_input_ivp = [el for el in client.elements.values() if isinstance(el, ui.input) and "Biến số" in el._props.get("label", "")][0]
    assert var_input_ivp.value == "x", "Target variable 'x' must persist in Cauchy mode"

    # Switch to Nonhomogeneous
    _trigger_card_handler(client, "on_select_nonhomo")
    var_input_nonhomo = [el for el in client.elements.values() if isinstance(el, ui.input) and "Biến số" in el._props.get("label", "")][0]
    assert var_input_nonhomo.value == "x", "Target variable 'x' must persist in Nonhomogeneous mode"


def test_screen_b_scenario_d_category_transition_equation_persistence():
    """Scenario D: User-typed equation persistence across category switch."""
    create_app(build_application())
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page("/test_scenario_d"))
    with client:
        route.endpoint.__wrapped__()

    _navigate_to_screen_b(client)
    expr_input = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")][0]
    with client:
        expr_input.set_value("y'' + 2*y' + y = exp(t)")

    # Change category
    _trigger_card_handler(client, "on_select_nonhomo")
    expr_input_after = [el for el in client.elements.values() if isinstance(el, ui.input) and "Phương trình" in el._props.get("label", "")][0]
    assert expr_input_after.value == "y'' + 2*y' + y = exp(t)", "Custom equation must persist across category transition"


def test_screen_b_scenario_e_reset_stays_cleared():
    """Scenario E: Clearing Cauchy conditions remains cleared across rerenders (no stale default restored)."""
    create_app(build_application())
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page("/test_scenario_e"))
    with client:
        route.endpoint.__wrapped__()

    _navigate_to_screen_b(client)
    _trigger_button_by_text(client, "Bài toán Cauchy (IVP)")

    ic_input = [el for el in client.elements.values() if isinstance(el, ui.input) and "y(t0)" in el._props.get("label", "")][0]
    with client:
        ic_input.set_value("y(0) = 5, y'(0) = 6")

    # Click Xóa điều kiện
    assert _trigger_button_by_text(client, "Xóa điều kiện") is True
    assert ic_input.value == "", "Clear button must immediately clear input field"

    # Switch category and back
    _trigger_card_handler(client, "on_select_nonhomo")
    ic_input_rerendered = [el for el in client.elements.values() if isinstance(el, ui.input) and "y(t0)" in el._props.get("label", "")][0]
    assert ic_input_rerendered.value == "", "Cleared conditions must remain empty and not restore stale defaults"


def test_screen_b_mocked_use_case_submission_all_cauchy_presets():
    """Verify that clicking any Cauchy example chip submits the exact clean ODE
    and authoritative initial condition to use_case.execute without stale defaults.
    """
    async def _runner():
        core.loop = asyncio.get_running_loop()
        captured_requests: list[ProblemRequest] = []

        def dummy_execute(req: ProblemRequest, timeout: float = 8.0) -> SolutionResponse:
            captured_requests.append(req)
            return SolutionResponse(
                status=SolutionStatus.SUCCESS,
                verification=VerificationResult(VerificationStatus.VERIFIED, "ODEVerifier", "R(t) = 0"),
                raw_input=req.raw_input,
                canonical_input=req.raw_input,
                final_result="y(t) = dummy",
                final_latex=r"y(t) = \text{dummy}",
                steps=(),
            )

        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = dummy_execute
        create_app(mock_use_case)

        route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
        client = Client(ui.page("/test_all_presets_submission"))
        with client:
            route.endpoint.__wrapped__()

        _navigate_to_screen_b(client)

        def click_solve() -> None:
            solve_btn = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "GIẢI PHƯƠNG TRÌNH"][0]
            for listener in list(solve_btn._event_listeners.values()):
                if listener.type == "click":
                    with client:
                        listener.handler(None)

        # 1. Homogeneous Cauchy IVP Presets
        _trigger_card_handler(client, "on_select_homo")
        _trigger_button_by_text(client, "Bài toán Cauchy (IVP)")

        homo_expected = [
            ("Dao động điều hòa: y'' + 4y = 0, y(0)=0, y'(0)=2", "y'' + 4*y = 0", "y(0) = 0, y'(0) = 2"),
            ("Nghiệm thực: y'' - 3y' + 2y = 0, y(0)=1, y'(0)=0", "y'' - 3*y' + 2*y = 0", "y(0) = 1, y'(0) = 0"),
            ("Tắt dần: y'' + 2y' + 2y = 0, y(0)=1, y'(0)=1", "y'' + 2*y' + 2*y = 0", "y(0) = 1, y'(0) = 1"),
            ("Nghiệm kép: y'' - 4y' + 4y = 0, y(0)=2, y'(0)=1", "y'' - 4*y' + 4*y = 0", "y(0) = 2, y'(0) = 1"),
        ]

        homo_presets = get_second_order_examples("HOMOGENEOUS", "CAUCHY_IVP")
        assert len(homo_presets) == len(homo_expected)
        for label, exp_clean_eq, exp_ic in homo_expected:
            captured_requests.clear()
            chips = [el for el in client.elements.values() if isinstance(el, ui.chip) and el.text == label]
            assert len(chips) == 1, f"Chip not found for {label}"
            with client:
                for listener in list(chips[0]._event_listeners.values()):
                    if listener.type == "click":
                        listener.handler(None)

            click_solve()
            await asyncio.sleep(0.05)

            assert len(captured_requests) == 1, f"Submission failed for {label}"
            req = captured_requests[0]
            assert req.problem_type == ProblemType.ODE_SECOND_ORDER_IVP
            assert req.raw_input == exp_clean_eq, f"Raw input mismatch for {label}: got {req.raw_input}, expected {exp_clean_eq}"
            assert req.target_variable == "t"
            assert req.parameters["problem_mode"] == "CAUCHY_IVP"
            assert req.parameters["expected_classification"] == "HOMOGENEOUS"
            assert req.parameters["initial_condition"] == exp_ic, f"Initial condition mismatch for {label}: got {req.parameters['initial_condition']}, expected {exp_ic}"

        # 2. Nonhomogeneous Cauchy IVP Presets
        _trigger_card_handler(client, "on_select_nonhomo")
        _trigger_button_by_text(client, "Bài toán Cauchy (IVP)")

        nonhomo_expected = [
            ("IVP Mũ: y'' - 3y' - 4y = 3e^(2t), y(0)=1, y'(0)=0", "y'' - 3*y' - 4*y = 3*exp(2*t)", "y(0) = 1, y'(0) = 0", "AUTO"),
            ("IVP Đa thức: y'' + 4y = 4t, y(0)=1, y'(0)=2", "y'' + 4*y = 4*t", "y(0) = 1, y'(0) = 2", "AUTO"),
            ("IVP Lượng giác: y'' + y = tan(t), y(0)=1, y'(0)=0", "y'' + y = tan(t)", "y(0) = 1, y'(0) = 0", "AUTO"),
            ("IVP Cộng hưởng: y'' - 2y' + y = t*e^t, y(0)=0, y'(0)=1", "y'' - 2*y' + y = t*exp(t)", "y(0) = 0, y'(0) = 1", "AUTO"),
        ]

        nonhomo_presets = get_second_order_examples("NONHOMOGENEOUS", "CAUCHY_IVP")
        assert len(nonhomo_presets) == len(nonhomo_expected)
        for label, exp_clean_eq, exp_ic, exp_pref in nonhomo_expected:
            captured_requests.clear()
            chips = [el for el in client.elements.values() if isinstance(el, ui.chip) and el.text == label]
            assert len(chips) == 1, f"Chip not found for {label}"
            with client:
                for listener in list(chips[0]._event_listeners.values()):
                    if listener.type == "click":
                        listener.handler(None)

            click_solve()
            await asyncio.sleep(0.05)

            assert len(captured_requests) == 1, f"Submission failed for {label}"
            req = captured_requests[0]
            assert req.problem_type == ProblemType.ODE_SECOND_ORDER_IVP
            assert req.raw_input == exp_clean_eq, f"Raw input mismatch for {label}: got {req.raw_input}, expected {exp_clean_eq}"
            assert req.target_variable == "t"
            assert req.parameters["problem_mode"] == "CAUCHY_IVP"
            assert req.parameters["expected_classification"] == "NONHOMOGENEOUS"
            assert req.parameters["method_preference"] == exp_pref
            assert req.parameters["initial_condition"] == exp_ic, f"Initial condition mismatch for {label}: got {req.parameters['initial_condition']}, expected {exp_ic}"

    asyncio.run(_runner())


def test_screen_b_submission_conflict_ui_warning():
    """Verify that entering conflicting initial conditions renders an amber warning card
    and does not trigger use_case.execute or raise an unhandled exception.
    """
    async def _runner():
        core.loop = asyncio.get_running_loop()
        mock_use_case = MagicMock()
        create_app(mock_use_case)

        route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
        client = Client(ui.page("/test_conflict_warning_ui"))
        with client:
            route.endpoint.__wrapped__()

        _navigate_to_screen_b(client)
        _trigger_card_handler(client, "on_select_nonhomo")
        _trigger_button_by_text(client, "Bài toán Cauchy (IVP)")

        inputs = [el for el in client.elements.values() if isinstance(el, ui.input)]
        expr_inp = inputs[0]
        ic_inp = inputs[2]
        with client:
            expr_inp.set_value("y'' + y = tan(t), y(0) = 0, y'(0) = 2")
            ic_inp.set_value("y(0) = 1, y'(0) = 0")

        # Click GIẢI PHƯƠNG TRÌNH
        solve_btn = [el for el in client.elements.values() if isinstance(el, ui.button) and el.text == "GIẢI PHƯƠNG TRÌNH"][0]
        for listener in list(solve_btn._event_listeners.values()):
            if listener.type == "click":
                with client:
                    listener.handler(None)

        await asyncio.sleep(0.05)

        assert mock_use_case.execute.call_count == 0, "Execution must not be triggered on conflicting inputs"
        labels = [el.text for el in client.elements.values() if isinstance(el, ui.label)]
        warning_labels = [text_lbl for text_lbl in labels if "xung đột" in text_lbl.lower()]
        assert len(warning_labels) == 1, "Must render exactly one conflict warning label"
        assert "y(0) = 0, y'(0) = 2" in warning_labels[0]
        assert "y(0) = 1, y'(0) = 0" in warning_labels[0]

    asyncio.run(_runner())


def test_cauchy_example_synchronization_authoritative():
    """Verify that clicking Cauchy example chips separates the differential equation
    into expr_input and the initial conditions into ic_input, overriding stale defaults.
    """
    ivp_examples = [
        ("y'' + 4*y = 0, y(0) = 0, y'(0) = 2", "y'' + 4*y = 0", "y(0) = 0", "y'(0) = 2"),
        ("y'' - 3*y' + 2*y = 0, y(0) = 1, y'(0) = 0", "y'' - 3*y' + 2*y = 0", "y(0) = 1", "y'(0) = 0"),
        ("y'' + 4*y = 4*t, y(0) = 1, y'(0) = 2", "y'' + 4*y = 4*t", "y(0) = 1", "y'(0) = 2"),
        ("y'' + y = tan(t), y(0) = 1, y'(0) = 0", "y'' + y = tan(t)", "y(0) = 1", "y'(0) = 0"),
    ]

    for raw, exp_clean, exp_y_ic, exp_yp_ic in ivp_examples:
        clean_eq, y_ic, yp_ic, _ = extract_second_order_ics_from_string(raw)
        assert clean_eq == exp_clean, f"Clean equation mismatch for {raw}: got {clean_eq}"
        assert y_ic == exp_y_ic, f"y_ic mismatch for {raw}: got {y_ic}"
        assert yp_ic == exp_yp_ic, f"yp_ic mismatch for {raw}: got {yp_ic}"
        comb = f"{y_ic}, {yp_ic}"
        assert "y(" in comb and "y'(" in comb


def test_problem_mode_consistency_solver():
    """Verify problem_mode parameter contract in second-order solver:
    - GENERAL mode rejects equations with initial conditions (returns problem_mode_mismatch).
    - CAUCHY_IVP mode strictly requires both initial conditions (raises InvalidInputError).
    """
    solver = ODESecondOrderConstantCoeffSolver()

    # Case 1: GENERAL mode with initial conditions embedded in raw_input
    req_gen_with_ic = ProblemRequest(
        raw_input="y'' + 4*y = 0, y(0) = 0, y'(0) = 2",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
        parameters={"problem_mode": "GENERAL"},
    )
    res_gen = solver.solve(req_gen_with_ic)
    assert res_gen.status == SolutionStatus.CANNOT_SOLVE
    assert res_gen.verification.method == "problem_mode_mismatch"
    assert "chế độ 'Tìm nghiệm tổng quát'" in res_gen.warnings[0]
    assert "điều kiện ban đầu Cauchy" in res_gen.warnings[0]

    # Case 2: CAUCHY_IVP mode with completely missing initial conditions
    req_ivp_no_ic = ProblemRequest(
        raw_input="y'' + 4*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    with pytest.raises(InvalidInputError) as exc_info:
        solver.solve(req_ivp_no_ic)
    assert "y(t0) = y0 và y'(t0) = v0" in str(exc_info.value)

    # Case 3: CAUCHY_IVP mode with only one initial condition
    req_ivp_one_ic = ProblemRequest(
        raw_input="y'' + 4*y = 0, y(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
        parameters={"problem_mode": "CAUCHY_IVP"},
    )
    with pytest.raises(InvalidInputError) as exc_info_one:
        solver.solve(req_ivp_one_ic)
    assert "thiếu điều kiện ban đầu" in str(exc_info_one.value) or "y(t0) = y0 và y'(t0) = v0" in str(exc_info_one.value)


def test_e2e_benchmark_a_homogeneous_general():
    """Test A: Homogeneous General Solution
    y'' - 3*y' - 4*y = 0 -> y(t) = C1*e^(-t) + C2*e^(4t), R(t) = 0
    """
    solver = ODESecondOrderConstantCoeffSolver()
    req = ProblemRequest(
        raw_input="y'' - 3*y' - 4*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
        parameters={"problem_mode": "GENERAL", "expected_classification": "HOMOGENEOUS"},
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "R(t) = 0" in res.verification.details or "≡ 0" in res.verification.details

    # Exact symbolic verification of residual
    t, C1, C2 = sp.symbols("t C1 C2")
    y = C1 * sp.exp(-t) + C2 * sp.exp(4 * t)
    R = sp.diff(y, t, 2) - 3 * sp.diff(y, t, 1) - 4 * y
    assert sp.simplify(R) == 0


def test_e2e_benchmark_b_homogeneous_cauchy():
    """Test B: Homogeneous Cauchy IVP
    y'' + 4*y = 0, y(0) = 0, y'(0) = 2 -> y(t) = sin(2t), R(t) = 0
    """
    solver = ODESecondOrderConstantCoeffSolver()
    req = ProblemRequest(
        raw_input="y'' + 4*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
        parameters={
            "problem_mode": "CAUCHY_IVP",
            "expected_classification": "HOMOGENEOUS",
            "initial_condition": "y(0) = 0, y'(0) = 2",
        },
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "sin(2*t)" in res.final_result

    # Exact symbolic verification
    t = sp.Symbol("t")
    y = sp.sin(2 * t)
    R = sp.diff(y, t, 2) + 4 * y
    assert sp.simplify(R) == 0
    assert y.subs(t, 0) == 0
    assert sp.diff(y, t, 1).subs(t, 0) == 2


def test_e2e_benchmark_c_nonhomogeneous_general_uc():
    """Test C: Nonhomogeneous General Solution (Undetermined Coefficients)
    y'' - 3*y' - 4*y = 3*exp(2*t) -> y(t) = C1*e^(-t) + C2*e^(4t) - 1/2*e^(2t), R(t) = 0
    """
    solver = ODESecondOrderConstantCoeffSolver()
    req = ProblemRequest(
        raw_input="y'' - 3*y' - 4*y = 3*exp(2*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
        parameters={
            "problem_mode": "GENERAL",
            "expected_classification": "NONHOMOGENEOUS",
            "method_preference": "UNDETERMINED_COEFFICIENTS",
        },
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(2*t)" in res.final_result

    # Exact symbolic verification
    t, C1, C2 = sp.symbols("t C1 C2")
    y = C1 * sp.exp(-t) + C2 * sp.exp(4 * t) - sp.Rational(1, 2) * sp.exp(2 * t)
    R = sp.diff(y, t, 2) - 3 * sp.diff(y, t, 1) - 4 * y - 3 * sp.exp(2 * t)
    assert sp.simplify(R) == 0


def test_e2e_benchmark_d_nonhomogeneous_cauchy_uc():
    """Test D: Nonhomogeneous Cauchy IVP (Undetermined Coefficients)
    y'' + 4*y = 4*t, y(0) = 1, y'(0) = 2 -> y(t) = cos(2t) + 1/2*sin(2t) + t
    """
    solver = ODESecondOrderConstantCoeffSolver()
    req = ProblemRequest(
        raw_input="y'' + 4*y = 4*t",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
        parameters={
            "problem_mode": "CAUCHY_IVP",
            "expected_classification": "NONHOMOGENEOUS",
            "method_preference": "UNDETERMINED_COEFFICIENTS",
            "initial_condition": "y(0) = 1, y'(0) = 2",
        },
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "cos(2*t)" in res.final_result
    assert "sin(2*t)" in res.final_result

    # Exact symbolic verification
    t = sp.Symbol("t")
    y = sp.cos(2 * t) + sp.Rational(1, 2) * sp.sin(2 * t) + t
    R = sp.diff(y, t, 2) + 4 * y - 4 * t
    assert sp.simplify(R) == 0
    assert y.subs(t, 0) == 1
    assert sp.diff(y, t, 1).subs(t, 0) == 2


def test_e2e_benchmark_e_nonhomogeneous_general_vop():
    """Test E: Nonhomogeneous General Solution (Variation of Parameters)
    y'' + y = tan(t) -> y(t) = C1*cos(t) + C2*sin(t) - cos(t)*ln|sec(t) + tan(t)|
    """
    solver = ODESecondOrderConstantCoeffSolver()
    req = ProblemRequest(
        raw_input="y'' + y = tan(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
        parameters={
            "problem_mode": "GENERAL",
            "expected_classification": "NONHOMOGENEOUS",
            "method_preference": "VARIATION_OF_PARAMETERS",
        },
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "cos(t)" in res.final_result
    assert "sin(t)" in res.final_result


def test_e2e_benchmark_f_nonhomogeneous_cauchy_vop():
    """Test F: Nonhomogeneous Cauchy IVP (Variation of Parameters)
    y'' + y = tan(t), y(0) = 1, y'(0) = 0
    """
    solver = ODESecondOrderConstantCoeffSolver()
    req = ProblemRequest(
        raw_input="y'' + y = tan(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
        parameters={
            "problem_mode": "CAUCHY_IVP",
            "expected_classification": "NONHOMOGENEOUS",
            "method_preference": "VARIATION_OF_PARAMETERS",
            "initial_condition": "y(0) = 1, y'(0) = 0",
        },
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "cos(t)" in res.final_result


def test_screen_b_cauchy_to_general_mode_isolation_and_restoration():
    """Verify that switching from CAUCHY_IVP to GENERAL mode strictly isolates the request
    (no stale initial_condition in parameters) allowing General solves to succeed,
    while UI draft state is preserved when switching back to CAUCHY_IVP.
    Tested for both Nonhomogeneous and Homogeneous categories.
    """
    solver = ODESecondOrderConstantCoeffSolver()
    create_app(build_application())
    route = [r for r in app.routes if getattr(r, "path", None) == "/"][0]
    client = Client(ui.page("/test_cauchy_gen_isolation"))
    with client:
        route.endpoint.__wrapped__()

    _navigate_to_screen_b(client)

    # -------------------------------------------------------------
    # Cycle 1: NONHOMOGENEOUS Mode
    # -------------------------------------------------------------
    assert _trigger_card_handler(client, "on_select_nonhomo") is True
    assert _trigger_button_by_text(client, "Bài toán Cauchy (IVP)") is True

    inputs = [el for el in client.elements.values() if isinstance(el, ui.input)]
    expr_inp = [inp for inp in inputs if "Phương trình" in inp._props.get("label", "")][0]
    ic_inp = [inp for inp in inputs if "y(t0)" in inp._props.get("label", "")][0]

    with client:
        expr_inp.set_value("y'' - 3*y' - 4*y = 3*exp(2*t)")
        ic_inp.set_value("y(0) = 1, y'(0) = 0")

    # Transition to GENERAL mode
    assert _trigger_button_by_text(client, "Tìm nghiệm tổng quát") is True

    # Build request via build_second_order_problem_request simulating what handle_ode2_submit builds
    req_nonhomo_gen = build_second_order_problem_request(
        equation=expr_inp.value,
        category="NONHOMOGENEOUS",
        mode="GENERAL",
        initial_condition=ic_inp.value,  # Draft condition still present in UI state
        method_pref="AUTO",
        target_var="t",
    )
    assert req_nonhomo_gen.problem_type == ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF
    assert req_nonhomo_gen.parameters["problem_mode"] == "GENERAL"
    assert "initial_condition" not in req_nonhomo_gen.parameters, "initial_condition must NOT leak into GENERAL request"

    # Solve with real solver - must succeed and NOT raise problem_mode_mismatch
    res_nonhomo_gen = solver.solve(req_nonhomo_gen)
    assert res_nonhomo_gen.status == SolutionStatus.SUCCESS
    assert res_nonhomo_gen.verification.status == VerificationStatus.VERIFIED

    # Transition back to CAUCHY_IVP mode
    assert _trigger_button_by_text(client, "Bài toán Cauchy (IVP)") is True
    ic_inputs_after = [el for el in client.elements.values() if isinstance(el, ui.input) and "y(t0)" in el._props.get("label", "")]
    assert len(ic_inputs_after) == 1
    assert ic_inputs_after[0].value == "y(0) = 1, y'(0) = 0", "Cauchy draft must be restored"

    # Solve Cauchy IVP with real solver
    req_nonhomo_ivp = build_second_order_problem_request(
        equation=expr_inp.value,
        category="NONHOMOGENEOUS",
        mode="CAUCHY_IVP",
        initial_condition=ic_inputs_after[0].value,
        method_pref="AUTO",
        target_var="t",
    )
    assert req_nonhomo_ivp.problem_type == ProblemType.ODE_SECOND_ORDER_IVP
    assert req_nonhomo_ivp.parameters["problem_mode"] == "CAUCHY_IVP"
    assert req_nonhomo_ivp.parameters["initial_condition"] == "y(0) = 1, y'(0) = 0"
    res_nonhomo_ivp = solver.solve(req_nonhomo_ivp)
    assert res_nonhomo_ivp.status == SolutionStatus.SUCCESS
    assert res_nonhomo_ivp.verification.status == VerificationStatus.VERIFIED

    # -------------------------------------------------------------
    # Cycle 2: HOMOGENEOUS Mode
    # -------------------------------------------------------------
    assert _trigger_card_handler(client, "on_select_homo") is True
    inputs_homo = [el for el in client.elements.values() if isinstance(el, ui.input)]
    expr_inp_homo = [inp for inp in inputs_homo if "Phương trình" in inp._props.get("label", "")][0]
    ic_inp_homo = [inp for inp in inputs_homo if "y(t0)" in inp._props.get("label", "")][0]

    with client:
        expr_inp_homo.set_value("y'' + 4*y = 0")
        ic_inp_homo.set_value("y(0) = 0, y'(0) = 2")

    # Transition to GENERAL mode
    assert _trigger_button_by_text(client, "Tìm nghiệm tổng quát") is True

    req_homo_gen = build_second_order_problem_request(
        equation=expr_inp_homo.value,
        category="HOMOGENEOUS",
        mode="GENERAL",
        initial_condition=ic_inp_homo.value,
        method_pref="AUTO",
        target_var="t",
    )
    assert req_homo_gen.problem_type == ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF
    assert req_homo_gen.parameters["problem_mode"] == "GENERAL"
    assert "initial_condition" not in req_homo_gen.parameters, "initial_condition must NOT leak into GENERAL request"

    res_homo_gen = solver.solve(req_homo_gen)
    assert res_homo_gen.status == SolutionStatus.SUCCESS
    assert res_homo_gen.verification.status == VerificationStatus.VERIFIED

    # Transition back to CAUCHY_IVP mode
    assert _trigger_button_by_text(client, "Bài toán Cauchy (IVP)") is True
    ic_inputs_homo_after = [el for el in client.elements.values() if isinstance(el, ui.input) and "y(t0)" in el._props.get("label", "")]
    assert len(ic_inputs_homo_after) == 1
    assert ic_inputs_homo_after[0].value == "y(0) = 0, y'(0) = 2", "Cauchy draft must be restored"

    req_homo_ivp = build_second_order_problem_request(
        equation=expr_inp_homo.value,
        category="HOMOGENEOUS",
        mode="CAUCHY_IVP",
        initial_condition=ic_inputs_homo_after[0].value,
        method_pref="AUTO",
        target_var="t",
    )
    assert req_homo_ivp.problem_type == ProblemType.ODE_SECOND_ORDER_IVP
    assert req_homo_ivp.parameters["problem_mode"] == "CAUCHY_IVP"
    assert req_homo_ivp.parameters["initial_condition"] == "y(0) = 0, y'(0) = 2"
    res_homo_ivp = solver.solve(req_homo_ivp)
    assert res_homo_ivp.status == SolutionStatus.SUCCESS
    assert res_homo_ivp.verification.status == VerificationStatus.VERIFIED




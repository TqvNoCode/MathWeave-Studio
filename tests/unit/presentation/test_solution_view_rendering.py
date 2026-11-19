"""Tests exercising solution view fallback branches and plotting callbacks."""

from nicegui import ui

from math_app.application.dtos import SolutionResponse, VerificationResult
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.presentation.components.operation_catalog import get_operation_by_type
from math_app.presentation.components.solution_view import (
    determine_contextual_tools,
    render_solution_view,
)


def test_determine_contextual_tools_matrix_always_false():
    """Verify matrix operations never activate 2D/3D plot or variation table."""
    t2, t3, tt = determine_contextual_tools(ProblemType.MATRIX_DETERMINANT, "[[1, 2], [3, 4]]")
    assert (t2, t3, tt) == (False, False, False)


def test_determine_contextual_tools_calculus():
    """Verify calculus operations properly activate tools."""
    t2, t3, tt = determine_contextual_tools(ProblemType.DERIVATIVE, "x^2 + 1", "x")
    assert t2 is True
    assert tt is True


def test_solution_view_surface_and_3d_tools():
    """Verify solution view renders 3D surface parameters without NameError."""
    op = get_operation_by_type(ProblemType.SURFACE_AREA)
    response = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "test", "OK"),
        raw_input="1 - x - y",
        canonical_input="1 - x - y",
        final_result="sqrt(3)",
        final_latex=r"\sqrt{3}",
        steps=(),
    )
    params = {
        "surface_expr": "1 - x - y",
        "u_var": "x",
        "v_var": "y",
        "u_min": "0",
        "u_max": "1",
        "v_min": "0",
        "v_max": "1",
    }
    with ui.card():
        render_solution_view(response, op, "x", params)


def test_solution_view_parametric_surface_rendering():
    """Verify solution view handles parametric surface parameters correctly."""
    op = get_operation_by_type(ProblemType.SURFACE_AREA)
    response = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "test", "OK"),
        raw_input="cos(u), sin(u), v",
        canonical_input="cos(u), sin(u), v",
        final_result="4*pi",
        final_latex=r"4\pi",
        steps=(),
    )
    params = {
        "surface_type": "parametric",
        "param_x": "cos(u)",
        "param_y": "sin(u)",
        "param_z": "v",
        "u_var": "u",
        "v_var": "v",
        "u_min": "0",
        "u_max": "2*pi",
        "v_min": "0",
        "v_max": "2",
    }
    with ui.card():
        render_solution_view(response, op, "u", params)


def test_solution_view_timeout_card_rendering():
    """Verify SolutionStatus.TIMEOUT renders informative timeout alert card."""
    op = get_operation_by_type(ProblemType.DERIVATIVE)
    response = SolutionResponse(
        status=SolutionStatus.TIMEOUT,
        verification=VerificationResult(VerificationStatus.FAILED, "timeout", "Timed out"),
        raw_input="slow_computation",
        canonical_input="slow_computation",
        final_result="",
        final_latex="",
        warnings=("Quá trình giải toán vượt quá thời gian cho phép (8.0 giây).",),
        steps=(),
    )
    with ui.card():
        render_solution_view(response, op, "x", {})


def test_solution_view_equation_solving_rendering():
    """Verify solution view renders equation solving result properly."""
    op = get_operation_by_type(ProblemType.SOLVE_EQUATION)
    response = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "algebraic_root_substitution", "Verified"),
        raw_input="x^2 - 4 = 0",
        canonical_input="x^2 - 4 = 0",
        final_result="x = -2, x = 2",
        final_latex="x = -2, \\quad x = 2",
        steps=(),
    )
    with ui.card():
        render_solution_view(response, op, "x", {})


def test_solution_view_ode_rendering():
    """Verify solution view renders differential equations results properly."""
    op = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)
    response = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "ode_residual_symbolic_zero_check", "Verified"),
        raw_input="y' + 1/2*y = t + 2",
        canonical_input="y' + 1/2*y = t + 2",
        final_result="y(t) = C*exp(-t/2) + 2*t",
        final_latex="y(t) = C e^{-t/2} + 2t",
        steps=(),
    )
    with ui.card():
        render_solution_view(response, op, "t", {})


def test_solution_view_cross_application_math_in_steps():
    """Verify solution view renders steps with embedded math across Calculus, LinAlg, ODE 1, and ODE 2."""
    from math_app.application.dtos import SolutionStep
    from math_app.domain.step_content import ExpressionStepContent
    from math_app.rendering.text_math_renderer import render_math_in_text_html

    sample_steps = (
        SolutionStep(
            step_number=1,
            rule_name="Calculus Differentiation",
            title="Đạo hàm lũy thừa",
            description="Với hàm số $u(x) = x^n$, đạo hàm là $u'(x) = n \\cdot x^{n-1}$.",
            content=ExpressionStepContent(
                expression_before="x^3",
                expression_after="3*x^2",
                latex_before="x^3",
                latex_after="3x^2",
            ),
        ),
        SolutionStep(
            step_number=2,
            rule_name="Linear Algebra Determinant",
            title="Định thức cấp hai",
            description="Áp dụng công thức $\\det(A) = ad - bc = (1)\\cdot(4) - (2)\\cdot(3) = -2$.",
            content=ExpressionStepContent(
                expression_before="|A|",
                expression_after="-2",
                latex_before="|A|",
                latex_after="-2",
            ),
        ),
        SolutionStep(
            step_number=3,
            rule_name="ODE 1 Integrating Factor",
            title="Thừa số tích phân",
            description="Xác định thừa số tích phân $\\mu(t) = e^{\\int P(t)\\,dt} = e^{2t}$.",
            content=ExpressionStepContent(
                expression_before="mu(t)",
                expression_after="e^(2t)",
                latex_before=r"\mu(t)",
                latex_after=r"e^{2t}",
            ),
        ),
        SolutionStep(
            step_number=4,
            rule_name="ODE 2 Characteristic Equation",
            title="Nghiệm đặc trưng",
            description="Căn bậc hai discriminant $\\sqrt{\\Delta} = \\sqrt{33}$ cho nghiệm $r_1 = \\frac{-1 + \\sqrt{33}}{4}$.",
            content=ExpressionStepContent(
                expression_before="2*r^2 + r - 4 = 0",
                expression_after="r = (-1 + sqrt(33))/4",
                latex_before="2r^2 + r - 4 = 0",
                latex_after=r"r_1 = \frac{-1 + \sqrt{33}}{4}",
            ),
        ),
    )

    op = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)
    response = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "test", "OK"),
        raw_input="2y'' + y' - 4y = 0",
        canonical_input="2y'' + y' - 4y = 0",
        final_result="y(t) = C1*exp(...) + C2*exp(...)",
        final_latex="y(t) = C_1 e^{r_1 t} + C_2 e^{r_2 t}",
        steps=sample_steps,
    )

    with ui.card():
        render_solution_view(response, op, "t", {})

    # Also verify that the MathML conversion succeeds on all step descriptions
    for step in sample_steps:
        html = render_math_in_text_html(step.description)
        assert "<math" in html
        assert "</math>" in html

    # Verify specific math elements
    calc_html = render_math_in_text_html(sample_steps[0].description)
    assert "<msup>" in calc_html

    ode2_html = render_math_in_text_html(sample_steps[3].description)
    assert "<msqrt>" in ode2_html
    assert "<mfrac>" in ode2_html


def test_solution_view_ode_5_workflows_presentation():
    """Verify presentation rendering across the 5 core ODE workflows including odd roots."""
    from math_app.main import build_application
    from math_app.application.dtos import ProblemRequest
    from math_app.rendering.text_math_renderer import render_math_in_text_html

    app = build_application()
    workflows = [
        ("Separable ODE", "y' = 2*x*y, y(0) = 3", ProblemType.ODE_SEPARABLE, "x"),
        ("Exact Equation", "(2*x + y) + (x + 2*y)*y' = 0", ProblemType.ODE_EXACT, "x"),
        ("Integrating Factor", "(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0", ProblemType.ODE_INTEGRATING_FACTOR, "x"),
        ("Classical Homogeneous", "y' = y/x + x^2/(3*y^2), y(1) = -2", ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS, "x"),
        ("Second-order Cauchy IVP", "y'' - 5*y' + 6*y = 0, y(0) = 1, y'(0) = 0", ProblemType.ODE_SECOND_ORDER_IVP, "x"),
    ]

    for name, raw, pt, var in workflows:
        req = ProblemRequest(raw_input=raw, problem_type=pt, target_variable=var)
        res = app.execute(req)
        assert res.status == SolutionStatus.SUCCESS, f"{name} failed status: {res.status}"
        assert res.verification.status == VerificationStatus.VERIFIED, f"{name} verification failed"

        # Verify no raw python tokens in final_latex
        for bad_tok in ("**", "zoo", "nan"):
            assert bad_tok not in res.final_latex, f"{name}: raw token {bad_tok} in {res.final_latex}"

        # Render in NiceGUI component card
        op = get_operation_by_type(pt)
        with ui.card():
            render_solution_view(res, op, var, {})

        # Test MathML generation for step descriptions
        for step in res.steps:
            if step.description and "$" in step.description:
                html = render_math_in_text_html(step.description)
                assert "<math" in html, f"{name}: step MathML missing in {step.description}"
                assert "</math>" in html

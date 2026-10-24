"""Regression and audit tests for the complete problem submission and result rendering pipeline."""

from nicegui import Client, ui
import pytest

from math_app.application.dtos import (
    ProblemRequest,
    SolutionResponse,
    SolutionStep,
    VerificationResult,
)
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.main import build_application
from math_app.presentation.components.operation_catalog import (
    OPERATIONS,
    get_operation_by_type,
)
from math_app.presentation.components.problem_statement import (
    format_final_answer_latex,
    format_problem_statement_latex,
    get_result_card_title,
)
from math_app.presentation.components.solution_view import (
    determine_contextual_tools,
    render_solution_view,
)


def test_problem_type_domain_classification():
    """Verify that every ProblemType correctly reports is_matrix and is_calculus."""
    matrix_types = {
        ProblemType.MATRIX_ADD_SUB,
        ProblemType.MATRIX_MULTIPLY,
        ProblemType.MATRIX_TRANSPOSE,
        ProblemType.MATRIX_DETERMINANT,
        ProblemType.MATRIX_INVERSE,
        ProblemType.MATRIX_RANK,
        ProblemType.MATRIX_REF,
        ProblemType.MATRIX_RREF,
        ProblemType.MATRIX_SOLVE_SYSTEM,
    }

    for pt in ProblemType:
        if pt in matrix_types:
            assert pt.is_matrix is True
            assert pt.is_calculus is False
        else:
            assert pt.is_matrix is False
            assert pt.is_calculus is True


def test_operation_catalog_domain_classification():
    """Verify that every OperationDef in catalog correctly reflects domain properties."""
    for op in OPERATIONS:
        assert op.is_matrix == op.problem_type.is_matrix
        assert op.is_calculus == op.problem_type.is_calculus
        # Mutually exclusive
        assert op.is_matrix != op.is_calculus


def test_determine_contextual_tools_matrix_operations_never_plot():
    """Verify that all linear algebra operations NEVER expose 2D, 3D or variation table tools."""
    for op in OPERATIONS:
        if op.is_matrix:
            tool_2d, tool_3d, tool_table = determine_contextual_tools(
                op.problem_type,
                op.default_input,
                target_var="x",
                is_success=True,
            )
            assert tool_2d is False, f"Matrix operation {op.title} must not enable 2D plotting."
            assert tool_3d is False, f"Matrix operation {op.title} must not enable 3D plotting."
            assert tool_table is False, f"Matrix operation {op.title} must not enable variation table."


def test_determine_contextual_tools_calculus_operations():
    """Verify calculus operations enable appropriate tools based on dimension and input."""
    # 1. Standard 1D polynomial for derivative: 2D plot and variation table
    t2d, t3d, ttable = determine_contextual_tools(
        ProblemType.DERIVATIVE,
        "2*x^3 + 6*x - 8",
        target_var="x",
        is_success=True,
    )
    assert t2d is True
    assert t3d is False
    assert ttable is True

    # 2. 2-variable function for partial derivative: 3D plot
    t2d_p, t3d_p, ttable_p = determine_contextual_tools(
        ProblemType.PARTIAL_DERIVATIVE,
        "x^2*y + y^3",
        target_var="x",
        is_success=True,
    )
    assert t2d_p is False
    assert t3d_p is True
    assert ttable_p is False

    # 3. Unsuccessful status disables all tools
    t2d_err, t3d_err, ttable_err = determine_contextual_tools(
        ProblemType.DERIVATIVE,
        "2*x^3 + 6*x - 8",
        target_var="x",
        is_success=False,
    )
    assert t2d_err is False
    assert t3d_err is False
    assert ttable_err is False


def test_render_solution_view_calculus_runs_without_name_error():
    """Verify render_solution_view on calculus operation executes without NameError or unhandled exception."""
    step = SolutionStep(
        step_number=1,
        rule_name="Power Rule",
        description="d/dx(2x^3) = 6x^2",
        content=ExpressionStepContent("2*x^3", "6*x^2", "2x^3", "6x^2"),
    )
    response = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "probe", "Verified"),
        raw_input="2*x^3 + 6*x - 8",
        canonical_input="2*x^3 + 6*x - 8",
        final_result="6*x^2 + 6",
        final_latex="6 x^{2} + 6",
        steps=(step,),
        domain_restrictions=(),
        warnings=(),
        execution_time_ms=12.4,
    )

    deriv_op = get_operation_by_type(ProblemType.DERIVATIVE)

    client = Client(ui.page("/test_solution_calculus"))
    with client:
        # Must execute cleanly without NameError: name 'is_matrix_op' is not defined
        render_solution_view(
            response,
            op=deriv_op,
            target_var="x",
            params={"order": 1},
        )


def test_render_solution_view_matrix_runs_without_name_error():
    """Verify render_solution_view on matrix operation executes without NameError or unhandled exception."""
    step = SolutionStep(
        step_number=1,
        rule_name="Công thức định thức cấp 2",
        description="det = ad - bc",
        content=ExpressionStepContent("1*4 - 2*3", "-2", "1*4 - 2*3", "-2"),
    )
    response = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=VerificationResult(VerificationStatus.VERIFIED, "exact", "Verified"),
        raw_input="[[1, 2], [3, 4]]",
        canonical_input="[[1, 2], [3, 4]]",
        final_result="-2",
        final_latex="-2",
        steps=(step,),
        domain_restrictions=(),
        warnings=(),
        execution_time_ms=8.1,
    )

    matrix_op = get_operation_by_type(ProblemType.MATRIX_DETERMINANT)

    client = Client(ui.page("/test_solution_matrix"))
    with client:
        # Must execute cleanly without NameError and without displaying graphing tools
        render_solution_view(
            response,
            op=matrix_op,
            target_var="x",
            params={},
        )


def test_render_solution_view_invalid_input_card():
    """Verify render_solution_view handles invalid input or error status gracefully."""
    response = SolutionResponse(
        status=SolutionStatus.INVALID_INPUT,
        verification=VerificationResult(VerificationStatus.NOT_APPLICABLE, "none", ""),
        raw_input="[invalid",
        canonical_input="",
        final_result="",
        final_latex="",
        warnings=("Dữ liệu ma trận không hợp lệ.",),
        execution_time_ms=1.0,
    )

    client = Client(ui.page("/test_solution_invalid"))
    with client:
        render_solution_view(response, op=ProblemType.MATRIX_DETERMINANT)


def test_audit_complete_submission_pipeline_all_operations():
    """Audit the complete submission pipeline across all 13 supported operations in the catalog.

    Verifies:
    1. Solver resolution
    2. Successful mathematical execution
    3. Non-empty results and LaTeX
    4. Statement and answer formatting
    5. Clean tool determination
    """
    use_case = build_application()

    for op in OPERATIONS:
        params = {}
        if "order" in op.extra_fields:
            params["order"] = 1
        if "lower_bound" in op.extra_fields:
            params["lower_bound"] = "0"
            params["upper_bound"] = "1"
        if "limit_point" in op.extra_fields:
            params["limit_point"] = "0"
            params["direction"] = "+-"

        request = ProblemRequest(
            raw_input=op.default_input,
            problem_type=op.problem_type,
            target_variable=op.target_var,
            parameters=params,
        )

        response = use_case.execute(request)

        # 1. Status must be SUCCESS
        assert response.status == SolutionStatus.SUCCESS, (
            f"Operation {op.title} ({op.problem_type}) failed with status {response.status}: {response.warnings}"
        )

        # 2. Must produce non-empty result and LaTeX
        assert response.final_result.strip(), f"Empty final_result for {op.title}"
        assert response.final_latex.strip(), f"Empty final_latex for {op.title}"

        # 3. Card title
        title = get_result_card_title(op.problem_type)
        assert title and title.startswith("KẾT QUẢ"), f"Unexpected card title for {op.title}: {title}"

        # 4. Problem statement LaTeX formatting
        stmt_latex = format_problem_statement_latex(
            response.raw_input,
            op.problem_type,
            op.target_var,
            params,
        )
        assert stmt_latex.strip(), f"Empty statement latex for {op.title}"

        # 5. Final answer LaTeX formatting
        ans_latex = format_final_answer_latex(
            response.final_latex,
            op.problem_type,
            op.target_var,
            params,
        )
        assert ans_latex.strip(), f"Empty final answer latex for {op.title}"

        # 6. Tool gating: matrix operations never enable 2D/3D/table
        t2d, t3d, ttable = determine_contextual_tools(
            op.problem_type,
            response.raw_input,
            op.target_var,
            is_success=True,
        )
        if op.is_matrix:
            assert (t2d, t3d, ttable) == (False, False, False)


@pytest.mark.anyio
async def test_simulated_ui_submission_flow_calculus_and_matrix():
    """Simulate the exact handle_submit async workflow on Client for both Calculus and Matrix operations."""
    import asyncio

    use_case = build_application()
    client = Client(ui.page("/test_async_flow"))

    with client:
        results_container = ui.column()

        # 1. Calculus Submission Workflow (Derivative)
        current_op = get_operation_by_type(ProblemType.DERIVATIVE)
        target_var = "x"
        params = {"order": 1}
        request = ProblemRequest(
            raw_input="2*x^3 + 6*x - 8",
            problem_type=current_op.problem_type,
            target_variable=target_var,
            parameters=params,
        )
        response = await asyncio.to_thread(use_case.execute, request)
        assert response.status == SolutionStatus.SUCCESS

        results_container.clear()
        with results_container:
            # Must execute without NameError: name 'is_matrix_op' is not defined
            render_solution_view(response, current_op, target_var, params)

        # Ensure UI cards and elements were rendered
        assert len(results_container.default_slot.children) > 0

        # 2. Matrix Submission Workflow (Matrix Determinant)
        current_op_m = get_operation_by_type(ProblemType.MATRIX_DETERMINANT)
        request_m = ProblemRequest(
            raw_input="[[1, 2], [3, 4]]",
            problem_type=current_op_m.problem_type,
            target_variable="x",
            parameters={},
        )
        response_m = await asyncio.to_thread(use_case.execute, request_m)
        assert response_m.status == SolutionStatus.SUCCESS

        results_container.clear()
        with results_container:
            # Must execute without NameError
            render_solution_view(response_m, current_op_m, "x", {})

        # Ensure UI cards were rendered
        assert len(results_container.default_slot.children) > 0

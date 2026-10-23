"""Full pipeline tests for multivariable calculus, geometry, and vector calculus in MathWeave Studio."""

import pytest
import sympy as sp
from math_app.application.dtos import ProblemRequest, SolutionResponse
from math_app.application.use_cases.solve_problem import SolveProblemUseCase
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.main import build_application
from math_app.presentation.components.operation_catalog import OPERATIONS, get_operation_by_type
from math_app.presentation.components.problem_statement import (
    format_final_answer_latex,
    format_problem_statement_latex,
    get_result_card_title,
)
from math_app.presentation.components.solution_view import determine_contextual_tools


@pytest.fixture
def use_case() -> SolveProblemUseCase:
    return build_application()


def test_catalog_completeness():
    """Verify all required problem types are present in catalog with valid descriptions and icons."""
    required_types = [
        ProblemType.DEFINITE_INTEGRAL,
        ProblemType.LINE_INTEGRAL,
        ProblemType.SURFACE_INTEGRAL,
        ProblemType.TRIPLE_INTEGRAL,
        ProblemType.ARC_LENGTH,
        ProblemType.SURFACE_AREA,
        ProblemType.SURFACE_OF_REVOLUTION,
        ProblemType.GREENS_THEOREM,
        ProblemType.STOKES_THEOREM,
        ProblemType.DIVERGENCE_THEOREM,
    ]
    for pt in required_types:
        op = get_operation_by_type(pt)
        assert op.problem_type == pt
        assert len(op.title) > 0
        assert len(op.description) > 0
        assert op.math_icon is not None


def test_definite_integral_1d_pipeline(use_case: SolveProblemUseCase):
    req = ProblemRequest(
        raw_input="x^2",
        problem_type=ProblemType.DEFINITE_INTEGRAL,
        target_variable="x",
        parameters={"lower_bound": "0", "upper_bound": "1"},
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == sp.Rational(1, 3)

    title = get_result_card_title(req.problem_type)
    assert "TÍCH PHÂN XÁC ĐỊNH" in title

    stmt = format_problem_statement_latex(req.raw_input, req.problem_type, req.target_variable, req.parameters)
    assert "\\int" in stmt

    final_ltx = format_final_answer_latex(resp.final_latex, req.problem_type, req.target_variable, req.parameters)
    assert "\\int" in final_ltx


def test_line_integral_pipeline(use_case: SolveProblemUseCase):
    req = ProblemRequest(
        raw_input="x + y",
        problem_type=ProblemType.LINE_INTEGRAL,
        parameters={
            "mode": "scalar",
            "param_var": "t",
            "t_min": "0",
            "t_max": "1",
            "param_x": "3*t",
            "param_y": "4*t",
            "param_z": "0",
        },
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == sp.Rational(35, 2)

    title = get_result_card_title(req.problem_type)
    assert "TÍCH PHÂN ĐƯỜNG" in title


def test_surface_integral_pipeline(use_case: SolveProblemUseCase):
    req = ProblemRequest(
        raw_input="1",
        problem_type=ProblemType.SURFACE_INTEGRAL,
        parameters={
            "mode": "scalar",
            "surface_expr": "1 - x - y",
            "u_var": "x",
            "v_var": "y",
            "u_min": "0",
            "u_max": "1",
            "v_min": "0",
            "v_max": "1",
        },
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.simplify(sp.sympify(resp.final_result) - sp.sqrt(3)) == 0


def test_triple_integral_pipeline(use_case: SolveProblemUseCase):
    req = ProblemRequest(
        raw_input="x*y*z",
        problem_type=ProblemType.TRIPLE_INTEGRAL,
        parameters={
            "x_min": "0",
            "x_max": "1",
            "y_min": "0",
            "y_max": "2",
            "z_min": "0",
            "z_max": "3",
        },
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == sp.Rational(9, 2)  # (1/2) * 2 * (9/2) = 9/2


def test_arc_length_pipeline(use_case: SolveProblemUseCase):
    req = ProblemRequest(
        raw_input="2*x",
        problem_type=ProblemType.ARC_LENGTH,
        target_variable="x",
        parameters={"lower_bound": "0", "upper_bound": "3"},
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.simplify(sp.sympify(resp.final_result) - 3 * sp.sqrt(5)) == 0


def test_surface_area_pipeline(use_case: SolveProblemUseCase):
    req = ProblemRequest(
        raw_input="1 - x - y",
        problem_type=ProblemType.SURFACE_AREA,
        parameters={
            "u_var": "x",
            "v_var": "y",
            "u_min": "0",
            "u_max": "1",
            "v_min": "0",
            "v_max": "1",
        },
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.simplify(sp.sympify(resp.final_result) - sp.sqrt(3)) == 0


def test_surface_of_revolution_pipeline(use_case: SolveProblemUseCase):
    req = ProblemRequest(
        raw_input="x",
        problem_type=ProblemType.SURFACE_OF_REVOLUTION,
        target_variable="x",
        parameters={"axis": "x", "lower_bound": "0", "upper_bound": "1"},
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED


def test_greens_theorem_pipeline(use_case: SolveProblemUseCase):
    req = ProblemRequest(
        raw_input="-y, x",
        problem_type=ProblemType.GREENS_THEOREM,
        parameters={"form": "circulation", "x_min": "0", "x_max": "1", "y_min": "0", "y_max": "1"},
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == 2


def test_stokes_theorem_pipeline(use_case: SolveProblemUseCase):
    req = ProblemRequest(
        raw_input="y, -x, 0",
        problem_type=ProblemType.STOKES_THEOREM,
        parameters={"surface_expr": "0", "x_min": "0", "x_max": "1", "y_min": "0", "y_max": "1"},
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == -2


def test_divergence_theorem_pipeline(use_case: SolveProblemUseCase):
    req = ProblemRequest(
        raw_input="x, y, z",
        problem_type=ProblemType.DIVERGENCE_THEOREM,
        parameters={"x_min": "0", "x_max": "1", "y_min": "0", "y_max": "1", "z_min": "0", "z_max": "1"},
    )
    resp = use_case.execute(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == 3


def test_tools_behavior_across_problem_types():
    """Verify tool_2d, tool_3d, tool_table behavior does not crash on new types."""
    for op in OPERATIONS:
        t2d, t3d, tbl = determine_contextual_tools(op.problem_type, op.default_input, op.target_var, is_success=True)
        assert isinstance(t2d, bool)
        assert isinstance(t3d, bool)
        assert isinstance(tbl, bool)
        if op.is_matrix:
            assert (t2d, t3d, tbl) == (False, False, False)

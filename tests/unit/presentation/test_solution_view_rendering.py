"""Tests exercising solution view fallback branches and plotting callbacks."""

import pytest
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

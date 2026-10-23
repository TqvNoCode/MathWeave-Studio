"""Unit tests for Phase 4 geometry solvers: ArcLength, SurfaceArea, SurfaceOfRevolution."""

import sympy as sp
from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.geometry.arc_length_solver import ArcLengthSolver
from math_app.solvers.calculus.geometry.surface_area_solver import SurfaceAreaSolver
from math_app.solvers.calculus.geometry.surface_of_revolution_solver import SurfaceOfRevolutionSolver


def test_arc_length_explicit_line():
    """Verify arc length of y = 2x from 0 to 3 is 3*sqrt(5)."""
    solver = ArcLengthSolver()
    req = ProblemRequest(
        raw_input="2*x",
        problem_type=ProblemType.ARC_LENGTH,
        target_variable="x",
        parameters={"lower_bound": "0", "upper_bound": "3"},
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.simplify(sp.sympify(resp.final_result) - 3 * sp.sqrt(5)) == 0


def test_arc_length_parametric_semicircle():
    """Verify arc length of semicircle r(t) = (cos(t), sin(t)) from 0 to pi is pi."""
    solver = ArcLengthSolver()
    req = ProblemRequest(
        raw_input="cos(t), sin(t)",
        problem_type=ProblemType.ARC_LENGTH,
        parameters={
            "param_var": "t",
            "lower_bound": "0",
            "upper_bound": "pi",
            "param_x": "cos(t)",
            "param_y": "sin(t)",
            "param_z": "0",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.simplify(sp.sympify(resp.final_result) - sp.pi) == 0


def test_surface_area_explicit_plane():
    """Verify surface area of z = 1 - x - y over [0, 1] x [0, 1] is sqrt(3)."""
    solver = SurfaceAreaSolver()
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
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.simplify(sp.sympify(resp.final_result) - sp.sqrt(3)) == 0


def test_surface_area_parametric_cylinder():
    """Verify surface area of cylinder r(u, v) = (cos(u), sin(u), v) for u in [0, 2*pi], v in [0, 2] is 4*pi."""
    solver = SurfaceAreaSolver()
    req = ProblemRequest(
        raw_input="",
        problem_type=ProblemType.SURFACE_AREA,
        parameters={
            "u_var": "u",
            "v_var": "v",
            "u_min": "0",
            "u_max": "2*pi",
            "v_min": "0",
            "v_max": "2",
            "param_x": "cos(u)",
            "param_y": "sin(u)",
            "param_z": "v",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.simplify(sp.sympify(resp.final_result) - 4 * sp.pi) == 0


def test_surface_and_volume_of_revolution_cone():
    """Verify cone from y = x on [0, 1] rotated about x-axis: V = pi/3, S = sqrt(2)*pi."""
    solver = SurfaceOfRevolutionSolver()
    req = ProblemRequest(
        raw_input="x",
        problem_type=ProblemType.SURFACE_OF_REVOLUTION,
        target_variable="x",
        parameters={
            "axis": "x",
            "lower_bound": "0",
            "upper_bound": "1",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert "S = sqrt(2)*pi" in resp.final_result or "sqrt(2)*pi" in resp.final_result
    assert "V = pi/3" in resp.final_result or "pi/3" in resp.final_result

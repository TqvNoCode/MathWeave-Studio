"""Unit tests for scalar and vector surface integrals."""

import sympy as sp
from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.integration.surface_integral_solver import SurfaceIntegralSolver


def test_scalar_surface_integral_flat_plane():
    r"""Verify scalar surface integral \iint_S 1 dS over rectangle [0, 2] x [0, 3] on plane z = 0 equals area 6."""
    solver = SurfaceIntegralSolver()
    req = ProblemRequest(
        raw_input="1",
        problem_type=ProblemType.SURFACE_INTEGRAL,
        parameters={
            "mode": "scalar",
            "surface_expr": "0",
            "u_var": "x",
            "u_min": "0",
            "u_max": "2",
            "v_var": "y",
            "v_min": "0",
            "v_max": "3",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == 6


def test_scalar_surface_integral_slanted_plane():
    """Verify scalar surface integral of f = z on z = 2 - x - y over [0, 1] x [0, 1]."""
    # gx = -1, gy = -1 => dS = sqrt(1 + 1 + 1) dx dy = sqrt(3) dx dy
    # \iint (2 - x - y) sqrt(3) dx dy = sqrt(3) * (2 - 1/2 - 1/2) = sqrt(3)
    solver = SurfaceIntegralSolver()
    req = ProblemRequest(
        raw_input="z",
        problem_type=ProblemType.SURFACE_INTEGRAL,
        parameters={
            "mode": "scalar",
            "surface_expr": "2 - x - y",
            "u_var": "x",
            "u_min": "0",
            "u_max": "1",
            "v_var": "y",
            "v_min": "0",
            "v_max": "1",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.simplify(sp.sympify(resp.final_result) - sp.sqrt(3)) == 0


def test_vector_flux_integral_upward():
    """Verify upward flux of uniform field F = (0, 0, 1) across paraboloid z = 1 - x^2 - y^2 over [0, 1] x [0, 1]."""
    # F = (0, 0, 1), z = 1 - x^2 - y^2
    # gx = -2x, gy = -2y
    # Upward dS_vec = (-gx, -gy, 1) dx dy = (2x, 2y, 1) dx dy
    # F . dS_vec = 1 dx dy
    # \iint_D 1 dx dy = 1 * 1 = 1
    solver = SurfaceIntegralSolver()
    req = ProblemRequest(
        raw_input="0, 0, 1",
        problem_type=ProblemType.SURFACE_INTEGRAL,
        parameters={
            "mode": "flux",
            "surface_expr": "1 - x^2 - y^2",
            "orientation": "upward",
            "u_var": "x",
            "u_min": "0",
            "u_max": "1",
            "v_var": "y",
            "v_min": "0",
            "v_max": "1",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == 1

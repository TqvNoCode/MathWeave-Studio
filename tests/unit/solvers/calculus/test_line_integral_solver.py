"""Unit tests for scalar and vector line integrals."""

import sympy as sp
from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.integration.line_integral_solver import LineIntegralSolver


def test_scalar_line_integral_line_segment():
    r"""Verify scalar line integral \int_C (x + y) ds along line segment from (0,0) to (3,4)."""
    # r(t) = (3t, 4t), t in [0, 1]
    # ||r'(t)|| = sqrt(3^2 + 4^2) = 5
    # \int_0^1 (3t + 4t) * 5 dt = 35 * \int_0^1 t dt = 35 / 2
    solver = LineIntegralSolver()
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
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == sp.Rational(35, 2)
    assert len(resp.steps) >= 3


def test_scalar_line_integral_circle_perimeter():
    r"""Verify scalar line integral \int_C 1 ds on unit circle equals 2*pi."""
    # r(t) = (cos(t), sin(t)), t in [0, 2*pi]
    # ||r'(t)|| = 1
    # \int_0^{2*pi} 1 dt = 2*pi
    solver = LineIntegralSolver()
    req = ProblemRequest(
        raw_input="1",
        problem_type=ProblemType.LINE_INTEGRAL,
        parameters={
            "mode": "scalar",
            "param_var": "t",
            "t_min": "0",
            "t_max": "2*pi",
            "param_x": "cos(t)",
            "param_y": "sin(t)",
            "param_z": "0",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.simplify(sp.sympify(resp.final_result) - 2 * sp.pi) == 0


def test_vector_line_integral_work():
    r"""Verify vector line integral \int_C (y, -x) . dr along parabola y = x^2 from x=0 to x=1."""
    # r(t) = (t, t^2), t in [0, 1], r'(t) = (1, 2t)
    # F(r(t)) = (t^2, -t)
    # F . r' = t^2 * 1 + (-t) * 2t = -t^2
    # \int_0^1 -t^2 dt = -1/3
    solver = LineIntegralSolver()
    req = ProblemRequest(
        raw_input="y, -x",
        problem_type=ProblemType.LINE_INTEGRAL,
        parameters={
            "mode": "vector",
            "param_var": "t",
            "t_min": "0",
            "t_max": "1",
            "param_x": "t",
            "param_y": "t^2",
            "param_z": "0",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == sp.Rational(-1, 3)

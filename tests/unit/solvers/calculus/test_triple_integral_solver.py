"""Unit tests for triple integrals over 3D regions."""

import sympy as sp
from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.integration.triple_integral_solver import TripleIntegralSolver


def test_triple_integral_cartesian_box():
    """Verify triple integral of x*y*z on [0, 1] x [0, 2] x [0, 3] equals (1/2)*(4/2)*(9/2) = 9/2."""
    solver = TripleIntegralSolver()
    req = ProblemRequest(
        raw_input="x*y*z",
        problem_type=ProblemType.TRIPLE_INTEGRAL,
        parameters={
            "coord_system": "cartesian",
            "var_inner": "z",
            "inner_min": "0",
            "inner_max": "3",
            "var_middle": "y",
            "middle_min": "0",
            "middle_max": "2",
            "var_outer": "x",
            "outer_min": "0",
            "outer_max": "1",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == sp.Rational(9, 2)
    assert len(resp.steps) >= 3


def test_triple_integral_cylindrical_volume():
    """Verify volume of cylinder with radius 2 and height 5 using cylindrical coordinates equals 20*pi."""
    # \int_0^{2*pi} dtheta \int_0^2 r dr \int_0^5 dz = 2*pi * (4/2) * 5 = 20*pi
    solver = TripleIntegralSolver()
    req = ProblemRequest(
        raw_input="1",
        problem_type=ProblemType.TRIPLE_INTEGRAL,
        parameters={
            "coord_system": "cylindrical",
            "var_inner": "z",
            "inner_min": "0",
            "inner_max": "5",
            "var_middle": "r",
            "middle_min": "0",
            "middle_max": "2",
            "var_outer": "theta",
            "outer_min": "0",
            "outer_max": "2*pi",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.simplify(sp.sympify(resp.final_result) - 20 * sp.pi) == 0


def test_triple_integral_spherical_volume():
    """Verify volume of unit sphere using spherical coordinates equals (4/3)*pi."""
    # \int_0^{2*pi} dtheta \int_0^{pi} dphi \int_0^1 rho^2 sin(phi) drho = (4/3)*pi
    solver = TripleIntegralSolver()
    req = ProblemRequest(
        raw_input="1",
        problem_type=ProblemType.TRIPLE_INTEGRAL,
        parameters={
            "coord_system": "spherical",
            "var_inner": "rho",
            "inner_min": "0",
            "inner_max": "1",
            "var_middle": "phi",
            "middle_min": "0",
            "middle_max": "pi",
            "var_outer": "theta",
            "outer_min": "0",
            "outer_max": "2*pi",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.simplify(sp.sympify(resp.final_result) - sp.Rational(4, 3) * sp.pi) == 0

"""Unit tests for Phase 5 vector calculus solvers: Green, Stokes, and Divergence."""

import sympy as sp
from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.vector_calculus.greens_theorem_solver import GreensTheoremSolver
from math_app.solvers.calculus.vector_calculus.stokes_theorem_solver import StokesTheoremSolver
from math_app.solvers.calculus.vector_calculus.divergence_theorem_solver import DivergenceTheoremSolver


def test_greens_theorem_circulation():
    """Verify Green's theorem on F = (-y, x) over [0, 1] x [0, 1] yields 2."""
    solver = GreensTheoremSolver()
    req = ProblemRequest(
        raw_input="-y, x",
        problem_type=ProblemType.GREENS_THEOREM,
        parameters={
            "form": "circulation",
            "x_min": "0",
            "x_max": "1",
            "y_min": "0",
            "y_max": "1",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == 2


def test_greens_theorem_flux():
    """Verify Green's theorem flux form on F = (x, y) over [0, 1] x [0, 1] yields 2."""
    solver = GreensTheoremSolver()
    req = ProblemRequest(
        raw_input="x, y",
        problem_type=ProblemType.GREENS_THEOREM,
        parameters={
            "form": "flux",
            "x_min": "0",
            "x_max": "1",
            "y_min": "0",
            "y_max": "1",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == 2


def test_stokes_theorem():
    """Verify Stokes' theorem on F = (y, -x, 0) over plane z = 0 on [0, 1] x [0, 1] yields -2."""
    solver = StokesTheoremSolver()
    req = ProblemRequest(
        raw_input="y, -x, 0",
        problem_type=ProblemType.STOKES_THEOREM,
        parameters={
            "surface_expr": "0",
            "x_min": "0",
            "x_max": "1",
            "y_min": "0",
            "y_max": "1",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == -2


def test_divergence_theorem():
    """Verify Divergence theorem on F = (x, y, z) over unit cube yields 3."""
    solver = DivergenceTheoremSolver()
    req = ProblemRequest(
        raw_input="x, y, z",
        problem_type=ProblemType.DIVERGENCE_THEOREM,
        parameters={
            "x_min": "0",
            "x_max": "1",
            "y_min": "0",
            "y_max": "1",
            "z_min": "0",
            "z_max": "1",
        },
    )
    resp = solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(resp.final_result) == 3

"""Unit tests for Arc Length solver reliability, singularity analysis, and convergence detection."""

from __future__ import annotations

import math
import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.geometry.arc_length_solver import ArcLengthSolver
from math_app.verification.calculus.arc_length_verifier import ArcLengthVerifier


@pytest.fixture
def arc_length_solver() -> ArcLengthSolver:
    return ArcLengthSolver()


@pytest.fixture
def arc_length_verifier() -> ArcLengthVerifier:
    return ArcLengthVerifier()


def test_arc_length_linear_segment(arc_length_solver: ArcLengthSolver) -> None:
    """Case A: Regular linear curve y = x on [0, 1]. Arc length is sqrt(2)."""
    req = ProblemRequest(
        raw_input="x",
        problem_type=ProblemType.ARC_LENGTH,
        target_variable="x",
        parameters={"lower_bound": "0", "upper_bound": "1"},
    )
    resp = arc_length_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    val = float(sp.sympify(resp.final_result).evalf())
    assert math.isclose(val, math.sqrt(2), rel_tol=1e-5)
    assert resp.verification.status == VerificationStatus.VERIFIED


def test_arc_length_parabola(arc_length_solver: ArcLengthSolver) -> None:
    """Case B: Nonlinear curve y = x^2 on [0, 1]. Expected ~ 1.47894."""
    req = ProblemRequest(
        raw_input="x^2",
        problem_type=ProblemType.ARC_LENGTH,
        target_variable="x",
        parameters={"lower_bound": "0", "upper_bound": "1"},
    )
    resp = arc_length_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    val = float(sp.sympify(resp.final_result).evalf())
    expected = math.sqrt(5) / 2 + math.asinh(2) / 4
    assert math.isclose(val, expected, rel_tol=1e-4)
    assert resp.verification.status == VerificationStatus.VERIFIED


def test_arc_length_divergent_singularity_cos_minus_tan(
    arc_length_solver: ArcLengthSolver,
) -> None:
    """Case C: y = cos(x) - tan(x) on [0, 3]. Pole at pi/2 in (0, 3) with order p=2 >= 1.
    Must detect divergence to +oo quickly (< 2.0s) and not time out.
    """
    req = ProblemRequest(
        raw_input="cos(x) - tan(x)",
        problem_type=ProblemType.ARC_LENGTH,
        target_variable="x",
        parameters={"lower_bound": "0", "upper_bound": "3"},
    )
    resp = arc_length_solver.solve(req)

    assert resp.status == SolutionStatus.DIVERGENT
    assert resp.final_result == "oo"
    assert r"+\infty" in resp.final_latex

    # Steps must clearly document the singularity at pi/2
    step_texts = " ".join(s.description + " " + (s.equation_latex or "") for s in resp.steps)
    assert r"\pi" in step_texts or "pi" in step_texts or "1.57" in step_texts

    # Verification must acknowledge divergence
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert "phân kỳ" in resp.verification.details.lower() or "kỳ dị" in resp.verification.details.lower()


def test_arc_length_singularity_outside_interval(
    arc_length_solver: ArcLengthSolver,
) -> None:
    """Case D: y = cos(x) - tan(x) on [0, 1]. Pole at pi/2 ~ 1.5708 is outside [0, 1].
    Must compute accurate finite numerical value (~ 2.28048411076) without timing out.
    """
    req = ProblemRequest(
        raw_input="cos(x) - tan(x)",
        problem_type=ProblemType.ARC_LENGTH,
        target_variable="x",
        parameters={"lower_bound": "0", "upper_bound": "1"},
    )
    resp = arc_length_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    val = float(sp.sympify(resp.final_result).evalf())
    expected = 2.280484110764684
    assert math.isclose(val, expected, rel_tol=1e-5)
    assert math.isfinite(val)
    assert resp.verification.status == VerificationStatus.VERIFIED


def test_arc_length_linear_scaled_2x(arc_length_solver: ArcLengthSolver) -> None:
    """Case G: Regular linear curve y = 2x on [0, 3]. Arc length is 3*sqrt(5)."""
    req = ProblemRequest(
        raw_input="2*x",
        problem_type=ProblemType.ARC_LENGTH,
        target_variable="x",
        parameters={"lower_bound": "0", "upper_bound": "3"},
    )
    resp = arc_length_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    val = float(sp.sympify(resp.final_result).evalf())
    expected = 3 * math.sqrt(5)
    assert math.isclose(val, expected, rel_tol=1e-5)
    assert resp.verification.status == VerificationStatus.VERIFIED


def test_arc_length_convergent_endpoint_singularity_sqrt(
    arc_length_solver: ArcLengthSolver,
) -> None:
    """Case E: y = sqrt(x) on [0, 1]. Derivative has pole at x=0, but order p=1/2 < 1.
    The arc length is convergent and finite (~ 1.4789).
    Must NOT be classified as divergent.
    """
    req = ProblemRequest(
        raw_input="sqrt(x)",
        problem_type=ProblemType.ARC_LENGTH,
        target_variable="x",
        parameters={"lower_bound": "0", "upper_bound": "1"},
    )
    resp = arc_length_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    val = float(sp.sympify(resp.final_result).evalf())
    expected = math.sqrt(5) / 2 + math.asinh(2) / 4  # Same arc length as y = x^2 on [0, 1] by symmetry
    assert math.isclose(val, expected, rel_tol=1e-3)
    assert resp.verification.status == VerificationStatus.VERIFIED


def test_arc_length_parametric_quarter_circle(
    arc_length_solver: ArcLengthSolver,
) -> None:
    """Case F: Parametric curve x(t) = cos(t), y(t) = sin(t) on [0, pi/2]. Expected L = pi/2."""
    req = ProblemRequest(
        raw_input="cos(t), sin(t)",
        problem_type=ProblemType.ARC_LENGTH,
        target_variable="t",
        parameters={"lower_bound": "0", "upper_bound": "pi/2"},
    )
    resp = arc_length_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    val = float(sp.sympify(resp.final_result).evalf())
    assert math.isclose(val, math.pi / 2, rel_tol=1e-5)
    assert resp.verification.status == VerificationStatus.VERIFIED

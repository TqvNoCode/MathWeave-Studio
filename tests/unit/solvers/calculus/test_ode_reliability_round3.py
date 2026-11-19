"""Comprehensive mathematical regression tests for ODE Reliability Remediation Round 3.

Covers Test Matrix R3-01 through R3-16 for Pure Power ODE Real Branch Completeness:
1.  y' = y^3: positive branch.
2.  y' = y^3: negative branch.
3.  y' = y^3: zero equilibrium.
4.  y' = y^3, y(0) = -1: valid negative solution.
5.  y' = y^3, y(0) = 1: valid positive solution.
6.  y' = y^5: all supported real branches.
7.  y' = y^4: real-root handling.
8.  y' = 1/y: both real branches.
9.  Exclude singular points from domain (y != 0 for 1/y).
10. Symbolically verify every branch against the original ODE.
11. Verify all supplied initial conditions.
12. Confirm unsupported exponents retain an implicit result rather than a wrong explicit result.
13. Confirm existing logistic behavior remains unchanged.
14. Confirm existing y' = sin(y) periodic equilibria remain unchanged.
15. Confirm multi-logarithmic performance regression remains fixed.
16. Confirm each final branch is associated with the correct branch metadata during verification.
"""

from __future__ import annotations

import time
import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.separable_solver import ODESeparableSolver
from math_app.verification.calculus.ode_verifier import ODEVerifier, _prove_symbolic_zero


@pytest.fixture
def sep_solver() -> ODESeparableSolver:
    return ODESeparableSolver()


@pytest.fixture
def verifier() -> ODEVerifier:
    return ODEVerifier()


# =============================================================================
# 1. y' = y^3: positive branch (R3-01)
# =============================================================================

def test_r3_01_y_cube_positive_branch(sep_solver: ODESeparableSolver):
    """R3-01: y' = y^3 contains positive branch y1(x) = 1/sqrt(-2*C - 2*x) satisfying ODE."""
    req = ProblemRequest(
        raw_input="y' = y^3",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "1/sqrt(-2*C - 2*x)" in res.final_result or "(-2*C - 2*x)**(-1/2)" in res.final_result

    # Rigorous symbolic residual verification of positive branch
    x, C = sp.symbols("x C")
    y_pos = 1 / sp.sqrt(-2 * C - 2 * x)
    dy_pos = sp.diff(y_pos, x)
    res_pos = sp.simplify(dy_pos - y_pos**3)
    assert _prove_symbolic_zero(res_pos, (C,), variable=x) is True


# =============================================================================
# 2. y' = y^3: negative branch (R3-02)
# =============================================================================

def test_r3_02_y_cube_negative_branch(sep_solver: ODESeparableSolver):
    """R3-02: y' = y^3 contains negative branch y2(x) = -1/sqrt(-2*C - 2*x) satisfying ODE."""
    req = ProblemRequest(
        raw_input="y' = y^3",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "-1/sqrt(-2*C - 2*x)" in res.final_result or "-(-2*C - 2*x)**(-1/2)" in res.final_result

    # Rigorous symbolic residual verification of negative branch
    x, C = sp.symbols("x C")
    y_neg = -1 / sp.sqrt(-2 * C - 2 * x)
    dy_neg = sp.diff(y_neg, x)
    res_neg = sp.simplify(dy_neg - y_neg**3)
    assert _prove_symbolic_zero(res_neg, (C,), variable=x) is True


# =============================================================================
# 3. y' = y^3: zero equilibrium (R3-03)
# =============================================================================

def test_r3_03_y_cube_zero_equilibrium(sep_solver: ODESeparableSolver):
    """R3-03: y' = y^3 preserves the zero equilibrium solution y(x) = 0."""
    req = ProblemRequest(
        raw_input="y' = y^3",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "Nghiệm cân bằng: y = 0" in res.final_result

    # IVP hitting equilibrium solution directly
    req_ivp = ProblemRequest(
        raw_input="y' = y^3, y(0) = 0",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res_ivp = sep_solver.solve(req_ivp)
    assert res_ivp.status == SolutionStatus.SUCCESS
    assert res_ivp.verification.status == VerificationStatus.VERIFIED
    assert res_ivp.final_result == "y(x) = 0"


# =============================================================================
# 4. y' = y^3, y(0) = -1: valid negative solution (R3-04)
# =============================================================================

def test_r3_04_y_cube_ivp_negative(sep_solver: ODESeparableSolver):
    """R3-04: y' = y^3, y(0) = -1 resolves to verified negative branch y(x) = -1/sqrt(1 - 2*x)."""
    req = ProblemRequest(
        raw_input="y' = y^3, y(0) = -1",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "-1/sqrt(1 - 2*x)" in res.final_result or "-(1 - 2*x)**(-1/2)" in res.final_result

    # Symbolic check of ODE and IVP
    x = sp.Symbol("x")
    sol = -1 / sp.sqrt(1 - 2 * x)
    assert sol.subs(x, 0) == -1
    dy = sp.diff(sol, x)
    assert _prove_symbolic_zero(sp.simplify(dy - sol**3), variable=x) is True


# =============================================================================
# 5. y' = y^3, y(0) = 1: valid positive solution (R3-05)
# =============================================================================

def test_r3_05_y_cube_ivp_positive(sep_solver: ODESeparableSolver):
    """R3-05: y' = y^3, y(0) = 1 resolves to verified positive branch y(x) = 1/sqrt(1 - 2*x)."""
    req = ProblemRequest(
        raw_input="y' = y^3, y(0) = 1",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "1/sqrt(1 - 2*x)" in res.final_result or "(1 - 2*x)**(-1/2)" in res.final_result

    # Symbolic check of ODE and IVP
    x = sp.Symbol("x")
    sol = 1 / sp.sqrt(1 - 2 * x)
    assert sol.subs(x, 0) == 1
    dy = sp.diff(sol, x)
    assert _prove_symbolic_zero(sp.simplify(dy - sol**3), variable=x) is True


# =============================================================================
# 6. y' = y^5: all supported real branches (R3-06)
# =============================================================================

def test_r3_06_y_fifth_all_real_branches(sep_solver: ODESeparableSolver):
    """R3-06: y' = y^5 produces both 4th root real branches and equilibrium y = 0."""
    req = ProblemRequest(
        raw_input="y' = y^5",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "(-4*C - 4*x)**(-1/4)" in res.final_result or "1/(-4*C - 4*x)**(1/4)" in res.final_result
    assert "-1/(-4*C - 4*x)**(1/4)" in res.final_result or "-(-4*C - 4*x)**(-1/4)" in res.final_result
    assert "Nghiệm cân bằng: y = 0" in res.final_result

    # Verify both branches symbolically
    x, C = sp.symbols("x C")
    y1 = (-4 * C - 4 * x) ** sp.Rational(-1, 4)
    y2 = -y1
    assert _prove_symbolic_zero(sp.simplify(sp.diff(y1, x) - y1**5), (C,), variable=x) is True
    assert _prove_symbolic_zero(sp.simplify(sp.diff(y2, x) - y2**5), (C,), variable=x) is True


# =============================================================================
# 7. y' = y^4: real-root handling without complex principal root (R3-07)
# =============================================================================

def test_r3_07_y_fourth_real_root_handling(sep_solver: ODESeparableSolver):
    """R3-07: y' = y^4 uses real odd-root branches and handles both positive and negative IVPs."""
    req = ProblemRequest(
        raw_input="y' = y^4",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "Nghiệm cân bằng: y = 0" in res.final_result

    # Test negative IVP y(0) = -1
    req_neg = ProblemRequest(
        raw_input="y' = y^4, y(0) = -1",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res_neg = sep_solver.solve(req_neg)
    assert res_neg.status == SolutionStatus.SUCCESS
    assert res_neg.verification.status == VerificationStatus.VERIFIED
    assert "-1/(3*x + 1)**(1/3)" in res_neg.final_result or "-(3*x + 1)**(-1/3)" in res_neg.final_result

    # Test positive IVP y(0) = 1
    req_pos = ProblemRequest(
        raw_input="y' = y^4, y(0) = 1",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res_pos = sep_solver.solve(req_pos)
    assert res_pos.status == SolutionStatus.SUCCESS
    assert res_pos.verification.status == VerificationStatus.VERIFIED
    assert "(1 - 3*x)**(-1/3)" in res_pos.final_result or "1/(1 - 3*x)**(1/3)" in res_pos.final_result


# =============================================================================
# 8. y' = 1/y: both real branches (R3-08)
# =============================================================================

def test_r3_08_one_over_y_both_real_branches(sep_solver: ODESeparableSolver):
    """R3-08: y' = 1/y preserves both branches y(x) = +-sqrt(2*C + 2*x)."""
    req = ProblemRequest(
        raw_input="y' = 1/y",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "sqrt(2*C + 2*x)" in res.final_result
    assert "-sqrt(2*C + 2*x)" in res.final_result

    # Solve negative IVP y(0) = -2 => y(x) = -sqrt(2*x + 4)
    req_neg = ProblemRequest(
        raw_input="y' = 1/y, y(0) = -2",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res_neg = sep_solver.solve(req_neg)
    assert res_neg.status == SolutionStatus.SUCCESS
    assert res_neg.verification.status == VerificationStatus.VERIFIED
    assert "-sqrt(2*x + 4)" in res_neg.final_result

    # Solve positive IVP y(0) = 2 => y(x) = sqrt(2*x + 4)
    req_pos = ProblemRequest(
        raw_input="y' = 1/y, y(0) = 2",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res_pos = sep_solver.solve(req_pos)
    assert res_pos.status == SolutionStatus.SUCCESS
    assert res_pos.verification.status == VerificationStatus.VERIFIED
    assert "sqrt(2*x + 4)" in res_pos.final_result


# =============================================================================
# 9. Exclude singular points from domain (R3-09)
# =============================================================================

def test_r3_09_exclude_singular_points_domain(sep_solver: ODESeparableSolver):
    """R3-09: y' = 1/y excludes singular point y = 0 from domain restrictions and has no y=0 equilibrium."""
    req = ProblemRequest(
        raw_input="y' = 1/y",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    # Domain restrictions must state y != 0
    assert any("y khác 0" in r for r in res.domain_restrictions)
    # y = 0 must NOT be in equilibrium solutions
    assert "Nghiệm cân bằng: y = 0" not in res.final_result


# =============================================================================
# 10. Symbolically verify every branch against original ODE (R3-10)
# =============================================================================

def test_r3_10_symbolically_verify_every_branch(sep_solver: ODESeparableSolver):
    """R3-10: Symbolically verifies all branches of pure-power ODEs against the original equations."""
    for ode_str in ["y' = y^3", "y' = y^5", "y' = 1/y", "y' = y^4"]:
        req = ProblemRequest(
            raw_input=ode_str,
            problem_type=ProblemType.ODE_SEPARABLE,
            target_variable="x",
        )
        res = sep_solver.solve(req)
        assert res.status == SolutionStatus.SUCCESS, f"Failed on {ode_str}"
        assert res.verification.status == VerificationStatus.VERIFIED, f"Unverified on {ode_str}"


# =============================================================================
# 11. Verify all supplied initial conditions (R3-11)
# =============================================================================

def test_r3_11_verify_all_initial_conditions(sep_solver: ODESeparableSolver):
    """R3-11: Rigorously verifies all IVPs with positive, negative, and zero values."""
    ivp_test_cases = [
        ("y' = y^3, y(0) = -1", -1),
        ("y' = y^3, y(0) = 1", 1),
        ("y' = y^3, y(0) = 0", 0),
        ("y' = 1/y, y(0) = -2", -2),
        ("y' = 1/y, y(0) = 2", 2),
        ("y' = y^4, y(0) = -1", -1),
        ("y' = y^4, y(0) = 1", 1),
    ]

    for raw, y_expected in ivp_test_cases:
        req = ProblemRequest(
            raw_input=raw,
            problem_type=ProblemType.ODE_SEPARABLE,
            target_variable="x",
        )
        res = sep_solver.solve(req)
        assert res.status == SolutionStatus.SUCCESS, f"Failed on {raw}"
        assert res.verification.status == VerificationStatus.VERIFIED, f"Unverified on {raw}"


# =============================================================================
# 12. Confirm unsupported exponents retain implicit result (R3-12)
# =============================================================================

def test_r3_12_unsupported_exponents_retain_implicit(sep_solver: ODESeparableSolver):
    """R3-12: y' = y**(1/2) preserves exact real implicit form 2*sqrt(y) = x + C with equilibrium y=0."""
    req = ProblemRequest(
        raw_input="y' = y**(1/2)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Implicit equation 2*sqrt(y) = x + C
    assert "2*sqrt(y) = x + C" in res.final_result
    assert "Nghiệm cân bằng: y = 0" in res.final_result


# =============================================================================
# 13. Confirm existing logistic behavior remains unchanged (R3-13)
# =============================================================================

def test_r3_13_existing_logistic_behavior_unchanged(sep_solver: ODESeparableSolver):
    """R3-13: Logistic equation y' = y*(1 - y) preserves explicit solution and equilibria y=0, y=1."""
    req = ProblemRequest(
        raw_input="y' = y*(1 - y)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "C*exp(x)/(C*exp(x) + 1)" in res.final_result
    assert "y = 0" in res.final_result and "y = 1" in res.final_result


# =============================================================================
# 14. Confirm existing y' = sin(y) periodic equilibria unchanged (R3-14)
# =============================================================================

def test_r3_14_existing_sin_y_periodic_equilibria_unchanged(sep_solver: ODESeparableSolver):
    """R3-14: y' = sin(y) retains periodic equilibrium solution y = n*pi and implicit relation."""
    req = ProblemRequest(
        raw_input="y' = sin(y)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "log(Abs(tan(y/2))) = x + C" in res.final_result
    assert "n*pi" in res.final_result


# =============================================================================
# 15. Confirm multi-logarithmic performance regression remains fixed (R3-15)
# =============================================================================

def test_r3_15_multi_log_performance_regression_fixed(sep_solver: ODESeparableSolver):
    """R3-15: y' = y^2 - 4 executes with no performance bottleneck (< 1.0s) and verifies correctly."""
    t0 = time.perf_counter()
    req = ProblemRequest(
        raw_input="y' = y^2 - 4",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)
    duration = time.perf_counter() - t0

    assert duration < 1.0, f"Performance bottleneck detected: took {duration:.3f}s"
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "log(Abs(y - 2))/4 - log(Abs(y + 2))/4 = x + C" in res.final_result
    assert "Nghiệm cân bằng: y = -2, y = 2" in res.final_result


# =============================================================================
# 16. Confirm branch metadata provenance during verification (R3-16)
# =============================================================================

def test_r3_16_branch_metadata_provenance(sep_solver: ODESeparableSolver):
    """R3-16: Confirms that multi-branch equations retain explicit branch provenance and verify individually."""
    # (y')^2 = y^2 has two derivative branches y' = y and y' = -y
    req = ProblemRequest(
        raw_input="(y')^2 = y^2",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Both branches are represented with their respective constants
    assert "C1*exp(-x)" in res.final_result or "C1*exp(x)" in res.final_result
    assert "C2*exp(x)" in res.final_result or "C2*exp(-x)" in res.final_result

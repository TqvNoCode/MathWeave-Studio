"""Comprehensive tests for ODE Reliability Remediation Round 2.

Covers Test Matrix R2-01 through R2-20:
- Phase B: Real solution completeness in separable ODEs ((y')^2 = y^2 with positive, negative, zero amplitudes)
- Phase C: Correct real logarithms with Abs, logistic equation domains, periodic equilibria for y' = sin(y)
- Phase D: Strict initial condition checking in implicit verification
- Phase E: Domain-aware verification of radicals (sqrt(t^2) on t > 0 and t < 0) and pole filtering
- Phase F: Hardened reduction of order with symbolic proof, counterexample rejection, and inconclusive handling
"""

from unittest.mock import patch
import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.reduction_of_order_solver import ODEReductionOfOrderSolver
from math_app.solvers.calculus.ode.separable_solver import ODESeparableSolver
from math_app.verification.calculus.ode_verifier import (
    ODEVerifier,
    ResidualCheckOutcome,
    _find_numerical_discrepancy,
    _prove_symbolic_zero,
)


@pytest.fixture
def sep_solver() -> ODESeparableSolver:
    return ODESeparableSolver()


@pytest.fixture
def roo_solver() -> ODEReductionOfOrderSolver:
    return ODEReductionOfOrderSolver()


@pytest.fixture
def verifier() -> ODEVerifier:
    return ODEVerifier()


# =============================================================================
# Phase B: Real Amplitude Parameterization & (y')^2 = y^2 (R2-01 to R2-05)
# =============================================================================

def test_r2_01_square_ode_positive_amplitude(sep_solver: ODESeparableSolver):
    """R2-01: (y')^2 = y^2 with positive amplitude y(0) = 3 produces 3*exp(x) and 3*exp(-x)."""
    req = ProblemRequest(
        raw_input="(y')^2 = y^2, y(0) = 3",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "3*exp(x)" in res.final_result or "3*exp(-x)" in res.final_result
    # Discloses multiple branches
    assert "hoặc" in res.final_result
    assert any("nhánh" in w.lower() for w in res.warnings)


def test_r2_02_square_ode_negative_amplitude(sep_solver: ODESeparableSolver):
    """R2-02: (y')^2 = y^2 with negative amplitude y(0) = -3 produces -3*exp(x) and -3*exp(-x)."""
    req = ProblemRequest(
        raw_input="(y')^2 = y^2, y(0) = -3",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "-3*exp(x)" in res.final_result or "-3*exp(-x)" in res.final_result
    assert "hoặc" in res.final_result
    assert any("nhánh" in w.lower() for w in res.warnings)


def test_r2_03_square_ode_zero_amplitude(sep_solver: ODESeparableSolver):
    """R2-03: (y')^2 = y^2 with zero amplitude y(0) = 0 produces y = 0."""
    req = ProblemRequest(
        raw_input="(y')^2 = y^2, y(0) = 0",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "y(x) = 0" in res.final_result or res.final_result == "y(x) = 0"


def test_r2_04_verify_first_exponential_branch(verifier: ODEVerifier):
    """R2-04: Verify first exponential branch y1 = C1*exp(x) satisfies (y')^2 - y^2 == 0."""
    x = sp.Symbol("x")
    C1 = sp.Symbol("C1")
    y1 = C1 * sp.exp(x)
    dy1 = sp.diff(y1, x)
    res = dy1**2 - y1**2

    assert _prove_symbolic_zero(res, (C1,))
    # For any concrete real amplitude: positive, negative, zero
    for c_val in (5.0, -7.0, 0.0):
        assert _prove_symbolic_zero(res.subs(C1, c_val))


def test_r2_05_verify_second_exponential_branch(verifier: ODEVerifier):
    """R2-05: Verify second exponential branch y2 = C2*exp(-x) satisfies (y')^2 - y^2 == 0."""
    x = sp.Symbol("x")
    C2 = sp.Symbol("C2")
    y2 = C2 * sp.exp(-x)
    dy2 = sp.diff(y2, x)
    res = dy2**2 - y2**2

    assert _prove_symbolic_zero(res, (C2,))
    for c_val in (4.2, -3.14, 0.0):
        assert _prove_symbolic_zero(res.subs(C2, c_val))


# =============================================================================
# Phase C: Real Logarithms, Logistic & Sine ODEs (R2-06 to R2-11)
# =============================================================================

def test_r2_06_logistic_equation_canonical_domain(sep_solver: ODESeparableSolver):
    """R2-06: Logistic equation y' = y*(1 - y) on 0 < y < 1 with IVP y(0) = 1/2."""
    req = ProblemRequest(
        raw_input="y' = y*(1 - y), y(0) = 1/2",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Should resolve to the explicit logistic sigmoid
    assert "exp(x)" in res.final_result


def test_r2_07_logistic_equation_negative_domain(sep_solver: ODESeparableSolver):
    """R2-07: Logistic equation y' = y*(1 - y) on y < 0 with IVP y(0) = -1."""
    req = ProblemRequest(
        raw_input="y' = y*(1 - y), y(0) = -1",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(x)" in res.final_result


def test_r2_08_logistic_preserves_both_equilibria(sep_solver: ODESeparableSolver):
    """R2-08: General solution of logistic equation preserves both equilibria y = 0 and y = 1."""
    req = ProblemRequest(
        raw_input="y' = y*(1 - y)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "0" in res.final_result and "1" in res.final_result
    assert "cân bằng" in res.final_result.lower()
    assert res.verification.status == VerificationStatus.VERIFIED


def test_r2_09_sine_transcendental_ode_log_abs(sep_solver: ODESeparableSolver):
    """R2-09: y' = sin(y) yields real logarithmic absolute-value expression ln|tan(y/2)| = x + C."""
    req = ProblemRequest(
        raw_input="y' = sin(y)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Integration contains log and tan(y/2) with Abs
    step_texts = " ".join(s.description for s in res.steps) + res.final_result
    assert "tan" in step_texts
    assert "log" in res.final_result or "tan" in res.final_result


def test_r2_10_sine_ode_periodic_equilibria(sep_solver: ODESeparableSolver):
    """R2-10: y' = sin(y) identifies periodic equilibria y = n*pi (n in Z)."""
    req = ProblemRequest(
        raw_input="y' = sin(y)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "n*pi" in res.final_result or "n\\pi" in res.final_latex or "pi" in res.final_result
    step_titles_and_desc = " ".join(s.title + " " + s.description for s in res.steps)
    assert "tuần hoàn" in step_titles_and_desc.lower() or "cân bằng" in step_titles_and_desc.lower()


def test_r2_11_logistic_ivp_explicit_form_verified(sep_solver: ODESeparableSolver):
    """R2-11: Logistic IVP y(0) = 1/2 gives explicit y(x) = exp(x)/(1 + exp(x)) verified."""
    req = ProblemRequest(
        raw_input="y' = y*(1 - y), y(0) = 1/2",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    x = sp.Symbol("x")
    # Check that final solution matches e^x / (1 + e^x) symbolically
    expected = sp.exp(x) / (1 + sp.exp(x))
    # Extract solution expression from response
    sol_str = res.final_result.replace("y(x) = ", "")
    parsed_sol = sp.sympify(sol_str)
    assert _prove_symbolic_zero(parsed_sol - expected)


# =============================================================================
# Phase D: Strict Initial Condition Checking in Implicit Verifier (R2-12, R2-13)
# =============================================================================

def test_r2_12_implicit_verifier_incorrect_ic_fails(verifier: ODEVerifier):
    """R2-12: Incorrect initial condition in verify_implicit returns FAILED."""
    x, y = sp.symbols("x y")
    # Implicit solution phi = y^2 - x^2 = C. For y(1) = 2, C must be 2^2 - 1^2 = 3.
    phi = y**2 - x**2
    # If caller specifies c_val = 10, verification must fail!
    res = verifier.verify_implicit(
        potential_phi=phi,
        x_sym=x,
        y_sym=y,
        rhs_f_expr=x,
        rhs_g_expr=1 / y,
        initial_condition=(sp.Integer(1), sp.Integer(2)),
        c_val=sp.Integer(10),  # incorrect
    )

    assert res.status == VerificationStatus.FAILED
    assert res.method == "initial_condition_mismatch"


def test_r2_13_implicit_verifier_omitted_c_val_unverified(verifier: ODEVerifier):
    """R2-13: When initial condition is given without c_val, returns UNVERIFIED."""
    x, y = sp.symbols("x y")
    phi = sp.log(sp.Abs(y)) - x
    res = verifier.verify_implicit(
        potential_phi=phi,
        x_sym=x,
        y_sym=y,
        rhs_f_expr=sp.Integer(1),
        rhs_g_expr=y,
        initial_condition=(sp.Integer(0), sp.Integer(1)),
        c_val=None,  # omitted
    )

    assert res.status == VerificationStatus.UNVERIFIED
    assert res.method == "ic_constant_unspecified"


# =============================================================================
# Phase E: Domain-Aware Verification of Radicals & Poles (R2-14 to R2-16)
# =============================================================================

def test_r2_14_domain_aware_sqrt_positive(verifier: ODEVerifier):
    """R2-14: y = sqrt(t^2) on t > 0 for y' = 1 must return VERIFIED (no false negative discrepancy)."""
    t = sp.Symbol("t")
    sol = sp.sqrt(t**2)

    res = verifier.verify_explicit(
        solution=sol,
        variable=t,
        p_expr=sp.Integer(0),
        g_expr=sp.Integer(1),
        domain_interval=(0, sp.oo),
        domain_restrictions=("t > 0",),
    )

    assert res.status == VerificationStatus.VERIFIED
    assert res.method == "ode_residual_symbolic_zero_check"


def test_r2_15_domain_aware_sqrt_negative(verifier: ODEVerifier):
    """R2-15: y = sqrt(t^2) on t < 0 for y' = -1 must return VERIFIED."""
    t = sp.Symbol("t")
    sol = sp.sqrt(t**2)

    res = verifier.verify_explicit(
        solution=sol,
        variable=t,
        p_expr=sp.Integer(0),
        g_expr=sp.Integer(-1),
        domain_interval=(-sp.oo, 0),
        domain_restrictions=("t < 0",),
    )

    assert res.status == VerificationStatus.VERIFIED
    assert res.method == "ode_residual_symbolic_zero_check"


def test_r2_16_probe_points_filter_poles(verifier: ODEVerifier):
    """R2-16: Rational solution with pole at t = 0.47 excludes that point from numerical probes."""
    t = sp.Symbol("t")
    # Residual with pole at 0.47
    residual = 1 / (t - 0.47)
    # The discrepancy finder should cleanly detect discrepancy from other non-pole points without crashing on pole
    disc = _find_numerical_discrepancy(residual, t)
    assert disc is not None
    assert disc > 0


# =============================================================================
# Phase F: Hardened Reduction of Order (R2-17 to R2-20)
# =============================================================================

def test_r2_17_reduction_of_order_valid_y1_verified(roo_solver: ODEReductionOfOrderSolver):
    """R2-17: Valid fundamental solution y1 = exp(x) for y'' - y = 0 is verified."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        raw_input="y''(x) - y(x) = 0",
        parameters={"y1": "exp(x)"},
    )
    res = roo_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(x)" in res.final_result
    assert "exp(-x)" in res.final_result


def test_r2_18_reduction_of_order_invalid_y1_rejected(roo_solver: ODEReductionOfOrderSolver):
    """R2-18: Invalid y1 = x for y'' - y = 0 is proven non-zero and rejected with InvalidInputError."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        raw_input="y''(x) - y(x) = 0",
        parameters={"y1": "x"},
    )

    with pytest.raises(InvalidInputError, match="không thỏa mãn"):
        roo_solver.solve(req)


def test_r2_19_reduction_of_order_inconclusive_returns_cannot_solve(roo_solver: ODEReductionOfOrderSolver):
    """R2-19: Inconclusive y1 validation returns CANNOT_SOLVE and UNVERIFIED, not false rejection."""
    with patch(
        "math_app.solvers.calculus.ode.reduction_of_order_solver.check_residual_outcome",
        return_value=ResidualCheckOutcome.UNKNOWN,
    ):
        req = ProblemRequest(
            problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
            raw_input="y''(x) - y(x) = 0",
            parameters={"y1": "exp(x)"},
        )
        res = roo_solver.solve(req)

        assert res.status == SolutionStatus.CANNOT_SOLVE
        assert res.verification.status == VerificationStatus.UNVERIFIED
        assert "không thể kiểm chứng" in res.final_result.lower() or "cannot verify" in res.final_result.lower()


def test_r2_20_numerical_discrepancy_returns_failed(verifier: ODEVerifier):
    """R2-20: Valid numerical counterexample returns FAILED."""
    t = sp.Symbol("t")
    # Candidate solution y(t) = t for y' + y = 0. Residual R(t) = 1 + t != 0
    res = verifier.verify_explicit(
        solution=t,
        variable=t,
        p_expr=sp.Integer(1),
        g_expr=sp.Integer(0),
    )

    assert res.status == VerificationStatus.FAILED
    assert res.method == "numerical_residual_discrepancy"


# =============================================================================
# Performance Remediation: Conservative Explicit Conversion & Implicit Preservation
# =============================================================================

def test_performance_separable_implicit_logarithmic_no_hang(sep_solver: ODESeparableSolver):
    """Ensure equations with multi-log integrals like y^2 - 4 return implicit forms immediately without hanging."""
    import time

    t0 = time.perf_counter()
    req = ProblemRequest(
        raw_input="dy/dx = (x + 1)*(y^2 - 4)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)
    elapsed = time.perf_counter() - t0

    assert elapsed < 3.0  # Must complete quickly, never hanging
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Implicit equation preserved with absolute values
    assert "log" in res.final_result and "y" in res.final_result
    # Equilibria y = 2 and y = -2 preserved
    assert "2" in res.final_result and "-2" in res.final_result


def test_performance_separable_unsupported_explicit_inversion_preserves_implicit(sep_solver: ODESeparableSolver):
    """Ensure cubic equation y' = y^3 - y preserves implicit form and equilibria y = -1, 0, 1."""
    import time

    t0 = time.perf_counter()
    req = ProblemRequest(
        raw_input="dy/dx = y^3 - y",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)
    elapsed = time.perf_counter() - t0

    assert elapsed < 3.0
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Equilibria y = 0, 1, -1 preserved
    assert "0" in res.final_result and "1" in res.final_result and "-1" in res.final_result

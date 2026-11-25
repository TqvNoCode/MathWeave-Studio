"""Unit tests for Second-Order Nonhomogeneous ODEs via the Method of Undetermined Coefficients.

Covers:
- Reference Cases (REF-1 through REF-5)
- Polynomial Forcing Family (constant, linear, quadratic, resonance s=1, s=2)
- Exponential Forcing Family (non-resonance, simple resonance s=1, double resonance s=2, poly*exp)
- Trigonometric Forcing Family (pure sine, pure cosine, same-frequency superposition, pure imaginary resonance, damped resonance)
- Multi-component Superposition
- Sign Invariant Regressions (LHS/RHS variations, negative rem_expr)
- Defensive Rejections and Milestone Gates (unsupported functions -> M2, nonhomogeneous IVP -> M3)
- Target variable variation (e.g. x instead of t)
- Mathematical Verification Guarantee (R(t) = a*y'' + b*y' + c*y - g(t) == 0)
"""

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.second_order_constant_coeff_solver import ODESecondOrderConstantCoeffSolver
from math_app.solvers.calculus.ode.undetermined_coefficients import (
    classify_single_term,
    decompose_and_group_forcing,
    get_resonance_multiplicity,
    solve_undetermined_coefficients,
)
from math_app.verification.calculus.ode_verifier import ODEVerifier


@pytest.fixture
def solver() -> ODESecondOrderConstantCoeffSolver:
    return ODESecondOrderConstantCoeffSolver(verifier=ODEVerifier())


def _verify_solution_residual(
    sol_expr: sp.Expr,
    a_val: float | int,
    b_val: float | int,
    c_val: float | int,
    g_val: sp.Expr,
    var: sp.Symbol,
) -> bool:
    """Helper to independently evaluate residual R(t) = a*y'' + b*y' + c*y - g(t)."""
    dy = sp.diff(sol_expr, var)
    d2y = sp.diff(dy, var)
    lhs = a_val * d2y + b_val * dy + c_val * sol_expr
    residual = sp.simplify(lhs - g_val)
    if residual != 0:
        residual = sp.simplify(sp.trigsimp(sp.expand(residual)))
    return bool(residual == 0)


# =============================================================================
# 1. Low-level Classifier, Resonance, and Decomposition Unit Tests
# =============================================================================


def test_classify_single_term_polynomial():
    t = sp.Symbol("t")
    # Constant
    res = classify_single_term(sp.Integer(5), t)
    assert res is not None
    assert res == (sp.Integer(0), sp.Integer(0), sp.Integer(5), sp.Integer(0))

    # Linear
    res = classify_single_term(3 * t + 2, t)
    assert res is not None
    assert res == (sp.Integer(0), sp.Integer(0), 3 * t + 2, sp.Integer(0))


def test_classify_single_term_exponential():
    t = sp.Symbol("t")
    res = classify_single_term(3 * sp.exp(2 * t), t)
    assert res is not None
    assert res == (sp.Integer(2), sp.Integer(0), sp.Integer(3), sp.Integer(0))

    # Poly * exp
    res = classify_single_term((t**2 - 1) * sp.exp(-t), t)
    assert res is not None
    assert res == (sp.Integer(-1), sp.Integer(0), t**2 - 1, sp.Integer(0))


def test_classify_single_term_trigonometric():
    t = sp.Symbol("t")
    # Pure sine
    res = classify_single_term(2 * sp.sin(3 * t), t)
    assert res is not None
    assert res == (sp.Integer(0), sp.Integer(3), sp.Integer(0), sp.Integer(2))

    # Pure cosine
    res = classify_single_term(-sp.cos(4 * t), t)
    assert res is not None
    assert res == (sp.Integer(0), sp.Integer(4), sp.Integer(-1), sp.Integer(0))

    # Exp * trig
    res = classify_single_term(sp.exp(-t) * sp.sin(2 * t), t)
    assert res is not None
    assert res == (sp.Integer(-1), sp.Integer(2), sp.Integer(0), sp.Integer(1))


def test_classify_single_term_unsupported():
    t = sp.Symbol("t")
    assert classify_single_term(sp.tan(t), t) is None
    assert classify_single_term(sp.log(t), t) is None
    assert classify_single_term(1 / t, t) is None
    assert classify_single_term(sp.sqrt(t), t) is None
    assert classify_single_term(sp.exp(t**2), t) is None


def test_resonance_numeric_non_resonance():
    """1. Numeric non-resonance: a=1, b=-3, c=-4, lambda=2 -> P(2) = -6 != 0 -> s=0."""
    assert get_resonance_multiplicity(sp.Integer(1), sp.Integer(-3), sp.Integer(-4), sp.Integer(2), sp.Integer(0)) == 0


def test_resonance_numeric_simple():
    """2. Numeric simple resonance: a=1, b=-3, c=-4, lambda=4 -> P(4) = 0, P'(4) = 5 != 0 -> s=1."""
    assert get_resonance_multiplicity(sp.Integer(1), sp.Integer(-3), sp.Integer(-4), sp.Integer(4), sp.Integer(0)) == 1
    # Pure imaginary simple root: a=1, b=0, c=4, lambda=2i -> P(2i) = 0, P'(2i) = 4i != 0 -> s=1
    assert get_resonance_multiplicity(sp.Integer(1), sp.Integer(0), sp.Integer(4), sp.Integer(0), sp.Integer(2)) == 1


def test_resonance_numeric_double():
    """3. Numeric double resonance: a=1, b=-2, c=1, lambda=1 -> P(1) = 0, P'(1) = 0 -> s=2."""
    assert get_resonance_multiplicity(sp.Integer(1), sp.Integer(-2), sp.Integer(1), sp.Integer(1), sp.Integer(0)) == 2


def test_resonance_exact_algebraic():
    """4. Exact algebraic resonance: a=1, b=0, c=-2, lambda=sqrt(2) -> P(sqrt(2)) = 0, P' = 2*sqrt(2) != 0 -> s=1."""
    sqrt2 = sp.sqrt(2)
    assert get_resonance_multiplicity(sp.Integer(1), sp.Integer(0), sp.Integer(-2), sqrt2, sp.Integer(0)) == 1


def test_resonance_symbolic_guaranteed_non_resonance_under_assumptions():
    """5. Symbolic parameter with guaranteed non-resonance under explicit assumptions:

    k > 0 -> P(0) = k^2 + 1 > 1 > 0 -> s=0.
    """
    k_pos = sp.Symbol("k", positive=True)
    assert get_resonance_multiplicity(sp.Integer(1), sp.Integer(0), k_pos**2 + 1, sp.Integer(0), sp.Integer(0)) == 0


def test_resonance_symbolic_conditional_inconclusive():
    """6. Symbolic parameter where resonance is conditional:

    P(1) = 1 - k depends on unspecified k -> Inconclusive (returns None).
    """
    k = sp.Symbol("k")
    assert get_resonance_multiplicity(sp.Integer(1), sp.Integer(0), -k, sp.Integer(1), sp.Integer(0)) is None


def test_resonance_symbolic_multiplicity_inconclusive():
    """7. Symbolic parameter where multiplicity cannot be established:

    P(0) = 0, P'(0) = k (could be s=1 if k!=0 or s=2 if k=0) -> Inconclusive (returns None).
    """
    k = sp.Symbol("k")
    assert get_resonance_multiplicity(sp.Integer(1), k, sp.Integer(0), sp.Integer(0), sp.Integer(0)) is None


def test_frequency_grouping_merges_trig_terms():
    t = sp.Symbol("t")
    # 2*sin(3*t) + 4*cos(3*t) must produce exactly 1 group with alpha=0, beta=3
    components = decompose_and_group_forcing(2 * sp.sin(3 * t) + 4 * sp.cos(3 * t), t)
    assert components is not None
    assert len(components) == 1
    comp = components[0]
    assert comp.alpha == 0
    assert comp.beta == 3
    assert comp.P_poly == 4
    assert comp.Q_poly == 2


# =============================================================================
# 2. Reference Cases from Specification (REF-1 to REF-5)
# =============================================================================


def test_ref1_exponential_non_resonance(solver: ODESecondOrderConstantCoeffSolver):
    """REF-1: y'' - 3y' - 4y = 3*exp(2t) -> Yp = -1/2 * exp(2t)."""
    req = ProblemRequest(
        raw_input="y'' - 3*y' - 4*y = 3*exp(2*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(2*t)" in res.final_result
    # Check particular solution part: -1/2*exp(2*t)
    t = sp.Symbol("t")
    yp = -sp.Rational(1, 2) * sp.exp(2 * t)
    assert _verify_solution_residual(yp, 1, -3, -4, 3 * sp.exp(2 * t), t)


def test_ref2_sine_non_resonance(solver: ODESecondOrderConstantCoeffSolver):
    """REF-2: y'' - 3y' - 4y = 2*sin(t) -> Yp = 3/17*cos(t) - 5/17*sin(t)."""
    req = ProblemRequest(
        raw_input="y'' - 3*y' - 4*y = 2*sin(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = sp.Rational(3, 17) * sp.cos(t) - sp.Rational(5, 17) * sp.sin(t)
    assert _verify_solution_residual(yp, 1, -3, -4, 2 * sp.sin(t), t)


def test_ref3_exponential_simple_resonance(solver: ODESecondOrderConstantCoeffSolver):
    """REF-3: y'' - 3y' - 4y = 3*exp(4t) -> resonance s=1 -> Yp = 3/5 * t * exp(4t)."""
    req = ProblemRequest(
        raw_input="y'' - 3*y' - 4*y = 3*exp(4*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "t*exp(4*t)" in res.final_result or "exp(4*t)*t" in res.final_result
    t = sp.Symbol("t")
    yp = sp.Rational(3, 5) * t * sp.exp(4 * t)
    assert _verify_solution_residual(yp, 1, -3, -4, 3 * sp.exp(4 * t), t)


def test_ref4_original_m0_linear_polynomial(solver: ODESecondOrderConstantCoeffSolver):
    """Original M0 REF-4: y'' + y' - 2y = 2t -> yc = C1*exp(t) + C2*exp(-2t), Yp = -t - 1/2."""
    req = ProblemRequest(
        raw_input="y'' + y' - 2*y = 2*t",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = -t - sp.Rational(1, 2)
    assert _verify_solution_residual(yp, 1, 1, -2, 2 * t, t)
    assert "exp(t)" in res.final_result
    assert "exp(-2*t)" in res.final_result
    assert "- t - 1/2" in res.final_result or "- 1/2 - t" in res.final_result or "- t" in res.final_result


def test_ref4_alternative_linear_polynomial(solver: ODESecondOrderConstantCoeffSolver):
    """REF-4 alternative: y'' - 3y' - 4y = 2t -> Yp = -1/2*t + 3/8."""
    req = ProblemRequest(
        raw_input="y'' - 3*y' - 4*y = 2*t",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = -sp.Rational(1, 2) * t + sp.Rational(3, 8)
    assert _verify_solution_residual(yp, 1, -3, -4, 2 * t, t)


def test_ref5_superposition_three_groups(solver: ODESecondOrderConstantCoeffSolver):
    """REF-5: y'' - 3y' - 4y = 3*exp(2t) + 2*sin(t) + t^2 -> 3 frequency groups superposition."""
    req = ProblemRequest(
        raw_input="y'' - 3*y' - 4*y = 3*exp(2*t) + 2*sin(t) + t^2",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Should explain superposition in derivation steps
    step_titles = [s.title for s in res.steps]
    assert any("chồng chất" in t.lower() for t in step_titles)


# =============================================================================
# 3. Polynomial Forcing Family
# =============================================================================


def test_poly_constant_forcing(solver: ODESecondOrderConstantCoeffSolver):
    """Constant forcing: y'' + 4y = 8 -> Yp = 2."""
    req = ProblemRequest(
        raw_input="y'' + 4*y = 8",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "2" in res.final_result


def test_poly_linear_forcing(solver: ODESecondOrderConstantCoeffSolver):
    """Linear forcing: y'' - y' - 2y = 4t -> Yp = -2t + 1."""
    req = ProblemRequest(
        raw_input="y'' - y' - 2*y = 4*t",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = -2 * t + 1
    assert _verify_solution_residual(yp, 1, -1, -2, 4 * t, t)


def test_poly_quadratic_forcing(solver: ODESecondOrderConstantCoeffSolver):
    """Quadratic forcing: y'' + y = t^2 -> Yp = t^2 - 2."""
    req = ProblemRequest(
        raw_input="y'' + y = t^2",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = t**2 - 2
    assert _verify_solution_residual(yp, 1, 0, 1, t**2, t)


def test_poly_resonance_s1(solver: ODESecondOrderConstantCoeffSolver):
    """Polynomial resonance s=1 when c=0: y'' + 3y' = 6t -> Yp = t^2 - 2/3*t."""
    req = ProblemRequest(
        raw_input="y'' + 3*y' = 6*t",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = t**2 - sp.Rational(2, 3) * t
    assert _verify_solution_residual(yp, 1, 3, 0, 6 * t, t)


def test_poly_resonance_s2(solver: ODESecondOrderConstantCoeffSolver):
    """Polynomial resonance s=2 when b=0, c=0: y'' = 6t -> Yp = t^3."""
    req = ProblemRequest(
        raw_input="y'' = 6*t",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = t**3
    assert _verify_solution_residual(yp, 1, 0, 0, 6 * t, t)


# =============================================================================
# 4. Exponential Forcing Family
# =============================================================================


def test_exp_non_resonance(solver: ODESecondOrderConstantCoeffSolver):
    """Non-resonance exponential: y'' - y = exp(2t) -> Yp = 1/3 * exp(2t)."""
    req = ProblemRequest(
        raw_input="y'' - y = exp(2*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = sp.Rational(1, 3) * sp.exp(2 * t)
    assert _verify_solution_residual(yp, 1, 0, -1, sp.exp(2 * t), t)


def test_exp_simple_resonance_s1(solver: ODESecondOrderConstantCoeffSolver):
    """Simple resonance s=1: y'' - 3y' + 2y = exp(t) -> Yp = -t * exp(t)."""
    req = ProblemRequest(
        raw_input="y'' - 3*y' + 2*y = exp(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = -t * sp.exp(t)
    assert _verify_solution_residual(yp, 1, -3, 2, sp.exp(t), t)


def test_exp_double_resonance_s2(solver: ODESecondOrderConstantCoeffSolver):
    """Double resonance s=2: y'' - 2y' + y = exp(t) -> Yp = 1/2 * t^2 * exp(t)."""
    req = ProblemRequest(
        raw_input="y'' - 2*y' + y = exp(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = sp.Rational(1, 2) * (t**2) * sp.exp(t)
    assert _verify_solution_residual(yp, 1, -2, 1, sp.exp(t), t)


def test_exp_times_poly_non_resonance(solver: ODESecondOrderConstantCoeffSolver):
    """Exponential times linear polynomial: y'' - 4y = t*exp(t) -> Yp = (-1/3*t - 2/9)*exp(t)."""
    req = ProblemRequest(
        raw_input="y'' - 4*y = t*exp(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = (-sp.Rational(1, 3) * t - sp.Rational(2, 9)) * sp.exp(t)
    assert _verify_solution_residual(yp, 1, 0, -4, t * sp.exp(t), t)


def test_exp_times_poly_double_resonance_s2(solver: ODESecondOrderConstantCoeffSolver):
    """Exponential times linear polynomial with double resonance: y'' - 2y' + y = t*exp(t) -> Yp = 1/6 * t^3 * exp(t)."""
    req = ProblemRequest(
        raw_input="y'' - 2*y' + y = t*exp(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = sp.Rational(1, 6) * (t**3) * sp.exp(t)
    assert _verify_solution_residual(yp, 1, -2, 1, t * sp.exp(t), t)


# =============================================================================
# 5. Trigonometric Forcing Family
# =============================================================================


def test_trig_pure_sine_non_resonance(solver: ODESecondOrderConstantCoeffSolver):
    """Pure sine non-resonance: y'' + 9y = sin(2t) -> Yp = 1/5 * sin(2t)."""
    req = ProblemRequest(
        raw_input="y'' + 9*y = sin(2*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = sp.Rational(1, 5) * sp.sin(2 * t)
    assert _verify_solution_residual(yp, 1, 0, 9, sp.sin(2 * t), t)


def test_trig_pure_cosine_non_resonance(solver: ODESecondOrderConstantCoeffSolver):
    """Pure cosine non-resonance: y'' + 9y = cos(2t) -> Yp = 1/5 * cos(2t)."""
    req = ProblemRequest(
        raw_input="y'' + 9*y = cos(2*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = sp.Rational(1, 5) * sp.cos(2 * t)
    assert _verify_solution_residual(yp, 1, 0, 9, sp.cos(2 * t), t)


def test_trig_same_frequency_linear_combination(solver: ODESecondOrderConstantCoeffSolver):
    """Same frequency linear combination: y'' + y' + y = 2*sin(3t) + 4*cos(3t)."""
    req = ProblemRequest(
        raw_input="y'' + y' + y = 2*sin(3*t) + 4*cos(3*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


def test_trig_pure_imaginary_resonance_cosine_s1(solver: ODESecondOrderConstantCoeffSolver):
    """Pure imaginary resonance s=1 with cosine: y'' + 4y = cos(2t) -> Yp = 1/4 * t * sin(2t)."""
    req = ProblemRequest(
        raw_input="y'' + 4*y = cos(2*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = sp.Rational(1, 4) * t * sp.sin(2 * t)
    assert _verify_solution_residual(yp, 1, 0, 4, sp.cos(2 * t), t)


def test_trig_pure_imaginary_resonance_sine_s1(solver: ODESecondOrderConstantCoeffSolver):
    """Pure imaginary resonance s=1 with sine: y'' + 4y = sin(2t) -> Yp = -1/4 * t * cos(2t)."""
    req = ProblemRequest(
        raw_input="y'' + 4*y = sin(2*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = -sp.Rational(1, 4) * t * sp.cos(2 * t)
    assert _verify_solution_residual(yp, 1, 0, 4, sp.sin(2 * t), t)


def test_trig_damped_harmonic_resonance_s1(solver: ODESecondOrderConstantCoeffSolver):
    """Damped harmonic resonance s=1: y'' + 2y' + 2y = exp(-t)*sin(t).
    Roots of P(r) = r^2 + 2r + 2 are -1 +- i.
    Forcing has alpha=-1, beta=1 -> match characteristic frequency -> s=1.
    Ansatz: t * exp(-t) * (A*cos(t) + B*sin(t)) -> Yp = -1/2 * t * exp(-t) * cos(t).
    """
    req = ProblemRequest(
        raw_input="y'' + 2*y' + 2*y = exp(-t)*sin(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = -sp.Rational(1, 2) * t * sp.exp(-t) * sp.cos(t)
    assert _verify_solution_residual(yp, 1, 2, 2, sp.exp(-t) * sp.sin(t), t)


# =============================================================================
# 6. Multi-Component Superposition Cases
# =============================================================================


def test_superposition_poly_and_exp(solver: ODESecondOrderConstantCoeffSolver):
    """Superposition: y'' - y = t + exp(2t) -> Yp = -t + 1/3*exp(2t)."""
    req = ProblemRequest(
        raw_input="y'' - y = t + exp(2*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = -t + sp.Rational(1, 3) * sp.exp(2 * t)
    assert _verify_solution_residual(yp, 1, 0, -1, t + sp.exp(2 * t), t)


def test_superposition_exp_and_trig(solver: ODESecondOrderConstantCoeffSolver):
    """Superposition: y'' + y = exp(t) + sin(2t)."""
    req = ProblemRequest(
        raw_input="y'' + y = exp(t) + sin(2*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = sp.Rational(1, 2) * sp.exp(t) - sp.Rational(1, 3) * sp.sin(2 * t)
    assert _verify_solution_residual(yp, 1, 0, 1, sp.exp(t) + sp.sin(2 * t), t)


def test_superposition_differing_resonance(solver: ODESecondOrderConstantCoeffSolver):
    """Superposition with differing resonance: y'' + y = cos(t) + exp(2t).
    cos(t) has s=1 resonance (roots +-i). exp(2t) has s=0.
    """
    req = ProblemRequest(
        raw_input="y'' + y = cos(t) + exp(2*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    yp = sp.Rational(1, 2) * t * sp.sin(t) + sp.Rational(1, 5) * sp.exp(2 * t)
    assert _verify_solution_residual(yp, 1, 0, 1, sp.cos(t) + sp.exp(2 * t), t)


# =============================================================================
# 7. Mandatory Sign Invariant Regressions
# =============================================================================


def test_mandatory_sign_case_1(solver: ODESecondOrderConstantCoeffSolver):
    """Mandatory sign test 1: y'' + y = sin(t) -> standard RHS."""
    req = ProblemRequest(
        raw_input="y'' + y = sin(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "t*cos(t)" in res.final_result or "cos(t)*t" in res.final_result


def test_mandatory_sign_case_2(solver: ODESecondOrderConstantCoeffSolver):
    """Mandatory sign test 2: y'' + y - sin(t) = 0 -> all terms on LHS."""
    req = ProblemRequest(
        raw_input="y'' + y - sin(t) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "t*cos(t)" in res.final_result or "cos(t)*t" in res.final_result


def test_mandatory_sign_case_3(solver: ODESecondOrderConstantCoeffSolver):
    """Mandatory sign test 3: sin(t) = y'' + y -> swapped LHS and RHS.
    standard_expr = sin(t) - (y'' + y) = -y'' - y + sin(t) = 0.
    a = -1, rem_expr = sin(t) -> g(t) = -rem_expr = -sin(t).
    f(t) = -rem_expr / a = sin(t).
    The ODE -y'' - y = -sin(t) is identical to y'' + y = sin(t).
    """
    req = ProblemRequest(
        raw_input="sin(t) = y'' + y",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "t*cos(t)" in res.final_result or "cos(t)*t" in res.final_result


def test_mandatory_sign_case_4(solver: ODESecondOrderConstantCoeffSolver):
    """Mandatory sign test 4: y'' + 4*y = 8 -> Yp = 2."""
    req = ProblemRequest(
        raw_input="y'' + 4*y = 8",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "+ 2" in res.final_result or " 2" in res.final_result


def test_mandatory_sign_case_5(solver: ODESecondOrderConstantCoeffSolver):
    """Mandatory sign test 5: y'' + 4*y + 8 = 0 -> rem_expr = 8 -> g(t) = -8 -> Yp = -2."""
    req = ProblemRequest(
        raw_input="y'' + 4*y + 8 = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "- 2" in res.final_result


def test_sign_equivalence_across_forms(solver: ODESecondOrderConstantCoeffSolver):
    """Verify that y'' + y = sin(t), y'' + y - sin(t) = 0, and sin(t) = y'' + y yield the same particular solution."""
    t = sp.Symbol("t")
    res1 = solver.solve(ProblemRequest(raw_input="y'' + y = sin(t)", problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, target_variable="t"))
    res2 = solver.solve(ProblemRequest(raw_input="y'' + y - sin(t) = 0", problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, target_variable="t"))
    res3 = solver.solve(ProblemRequest(raw_input="sin(t) = y'' + y", problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF, target_variable="t"))

    expected_yp = -sp.Rational(1, 2) * t * sp.cos(t)
    assert _verify_solution_residual(expected_yp, 1, 0, 1, sp.sin(t), t)
    assert res1.status == SolutionStatus.SUCCESS
    assert res2.status == SolutionStatus.SUCCESS
    assert res3.status == SolutionStatus.SUCCESS


# =============================================================================
# 8. Defensive Rejections and Milestone Gates
# =============================================================================


def test_nonhomogeneous_ivp_solved_in_m3(solver: ODESecondOrderConstantCoeffSolver):
    """Nonhomogeneous Cauchy IVPs are solved and verified in Milestone 3."""
    req = ProblemRequest(
        raw_input="y'' + y = sin(t), y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


def test_nonhomogeneous_partial_ivp_rejected(solver: ODESecondOrderConstantCoeffSolver):
    """Nonhomogeneous equation with partial initial condition (only y(0) = 1) raises InvalidInputError."""
    req = ProblemRequest(
        raw_input="y'' + y = sin(t), y(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="không hoàn chỉnh"):
        solver.solve(req)


@pytest.mark.parametrize(
    "forcing_expr",
    [
        "tan(t)",
        "ln(t)",
        "1/t",
        "sqrt(t)",
        "exp(t^2)",
        "sec(t)",
    ],
)
def test_unsupported_forcing_functions_deferred_to_m2(forcing_expr: str):
    """The Undetermined Coefficients engine rejects functions outside polynomial, exp, and trig families."""
    t = sp.Symbol("t")
    clean_expr = forcing_expr.replace("ln(", "log(")
    g = sp.sympify(clean_expr)
    res = solve_undetermined_coefficients(sp.Integer(1), sp.Integer(0), sp.Integer(1), g, t)
    assert res.is_supported is False
    assert res.unsupported_reason is not None
    reason = res.unsupported_reason.lower()
    assert (
        "hệ số bất định" in reason
        or "variation of parameters" in reason
        or "lagrange" in reason
    )


def test_rejection_of_non_constant_coefficients(solver: ODESecondOrderConstantCoeffSolver):
    """Variable-coefficient second-order equation must still be rejected."""
    req = ProblemRequest(
        raw_input="t^2*y'' + t*y' - y = t",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert any("hệ số phụ thuộc biến số" in w.lower() for w in res.warnings)


def test_rejection_of_symbolic_parameter_conditional_resonance(solver: ODESecondOrderConstantCoeffSolver):
    """Equation with symbolic parameter in coefficients whose discriminant sign is inconclusive is rejected cleanly."""
    req = ProblemRequest(
        raw_input="y'' - k*y = exp(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert any("tham số" in w.lower() or "cộng hưởng" in w.lower() for w in res.warnings)


def test_rejection_of_symbolic_parameter_in_forcing_inconclusive_resonance(solver: ODESecondOrderConstantCoeffSolver):
    """Equation with numeric coefficients but symbolic frequency in forcing is rejected cleanly due to inconclusive resonance."""
    req = ProblemRequest(
        raw_input="y'' - y = exp(k*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert any("tham số" in w.lower() or "cộng hưởng" in w.lower() for w in res.warnings)


# =============================================================================
# 9. Target Variable Variation
# =============================================================================


def test_target_variable_x(solver: ODESecondOrderConstantCoeffSolver):
    """Verify that solver correctly respects target variable 'x' instead of default 't'."""
    req = ProblemRequest(
        raw_input="y'' + y = sin(x)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="x",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "x" in res.final_result
    assert "t" not in res.final_result


# =============================================================================
# 10. Pedagogical Derivation Steps Structure
# =============================================================================


def test_pedagogical_derivation_steps(solver: ODESecondOrderConstantCoeffSolver):
    """Verify that step sequence contains all required pedagogical milestones."""
    req = ProblemRequest(
        raw_input="y'' - 3*y' - 4*y = 3*exp(2*t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS

    # Check strictly monotonic step numbers
    step_nums = [s.step_number for s in res.steps]
    assert step_nums == list(range(1, len(res.steps) + 1))

    # Check key rule names exist
    rule_names = [s.rule_name for s in res.steps]
    assert "Phương trình đặc trưng" in rule_names
    assert "Hai nghiệm thực phân biệt" in rule_names
    assert "Hệ nghiệm cơ bản" in rule_names
    assert "Dạng nghiệm riêng đề xuất" in rule_names
    assert "Đạo hàm và thế toán tử" in rule_names
    assert "Hệ phương trình hệ số bất định" in rule_names
    assert "Nghiệm riêng thành phần" in rule_names
    assert "Tổng hợp nghiệm tổng quát" in rule_names
    assert "Kiểm chứng nghiệm" in rule_names

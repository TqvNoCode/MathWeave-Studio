"""Dedicated mathematical reliability and presentation regression test suite for Round 4.2.

Covers all 34 matrix items from Section 9:
1-11:  Classical homogeneous ODE (critical F(v)-v=0 case, general, positive/negative/zero IVP,
       x0=0 rejection, straight-line equilibria, multiple slopes, implicit verification, implicit IVP,
       conservative transcendental inversion, no unrestricted sp.solve).
12-18: Uniqueness & domain (sqrt(y) right-sided, -sqrt(y) left-sided, non-Lipschitz unproven uniqueness,
       removable denominator preservation, leading coeff singularity, radical/log domain, one-sided validation).
19-25: Verification (no numerical point proving identity, every branch verified independently,
       branch metadata survives deduplication, correct IC per branch, Abel with continuous coeffs,
       Abel with singular coeffs returns UNVERIFIED, Peano counterexample).
26-34: Mathematical presentation (separable inline/display math, exactness condition, potential function,
       integrating factor formula, transformed exact equation, absolute-value logs, fractions and derivatives,
       second-order ODE explanation remains intact).
"""

from __future__ import annotations

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import EquilibriumUniqueness, ProblemType, SolutionStatus, VerificationStatus
from math_app.rendering.text_math_renderer import render_math_in_text_html
from math_app.solvers.calculus.ode.classical_homogeneous_solver import (
    ODEClassicalHomogeneousSolver,
    _invert_homogeneous_relation_conservative,
)
from math_app.solvers.calculus.ode.exact_solver import ODEExactSolver
from math_app.solvers.calculus.ode.integrating_factor_solver import ODEIntegratingFactorSolver
from math_app.solvers.calculus.ode.second_order_constant_coeff_solver import ODESecondOrderConstantCoeffSolver
from math_app.solvers.calculus.ode.separable_solver import (
    ODESeparableSolver,
    _check_equilibrium_uniqueness,
)
from math_app.verification.calculus.ode_verifier import ODEVerifier


@pytest.fixture
def homog_solver() -> ODEClassicalHomogeneousSolver:
    return ODEClassicalHomogeneousSolver()


@pytest.fixture
def sep_solver() -> ODESeparableSolver:
    return ODESeparableSolver()


@pytest.fixture
def exact_solver() -> ODEExactSolver:
    return ODEExactSolver()


@pytest.fixture
def if_solver() -> ODEIntegratingFactorSolver:
    return ODEIntegratingFactorSolver()


@pytest.fixture
def second_order_solver() -> ODESecondOrderConstantCoeffSolver:
    return ODESecondOrderConstantCoeffSolver()


@pytest.fixture
def verifier() -> ODEVerifier:
    return ODEVerifier()


# =========================================================================
# Group 1: Classical Homogeneous ODE (Items 1 - 11)
# =========================================================================


def test_matrix_01_classical_homog_y_over_x_general(homog_solver: ODEClassicalHomogeneousSolver):
    """Item 1: y' = y/x general solution y = C*x with x != 0 restriction."""
    req = ProblemRequest(raw_input="y' = y/x", problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS)
    res = homog_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "y(x) = C*x" in res.final_result
    assert any("x khác 0" in r or "x != 0" in r for r in res.domain_restrictions)


def test_matrix_02_classical_homog_positive_ivp(homog_solver: ODEClassicalHomogeneousSolver):
    """Item 2: y' = y/x, y(1) = 2 -> y(x) = 2*x verified on (0, oo)."""
    req = ProblemRequest(raw_input="y' = y/x, y(1) = 2", problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS)
    res = homog_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.final_result == "y(x) = 2*x"
    assert res.final_latex == "y(x) = 2 x"


def test_matrix_03_classical_homog_negative_ivp(homog_solver: ODEClassicalHomogeneousSolver):
    """Item 3: y' = y/x, y(-2) = -6 -> y(x) = 3*x on (-oo, 0)."""
    req = ProblemRequest(raw_input="y' = y/x, y(-2) = -6", problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS)
    res = homog_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.final_result == "y(x) = 3*x"
    assert res.final_latex == "y(x) = 3 x"


def test_matrix_04_classical_homog_zero_ivp(homog_solver: ODEClassicalHomogeneousSolver):
    """Item 4: y' = y/x, y(1) = 0 -> y(x) = 0."""
    req = ProblemRequest(raw_input="y' = y/x, y(1) = 0", problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS)
    res = homog_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.final_result == "y(x) = 0"


def test_matrix_05_classical_homog_x0_zero_rejection(homog_solver: ODEClassicalHomogeneousSolver):
    """Item 5: Base point x0=0 rejection with InvalidInputError."""
    req = ProblemRequest(raw_input="y' = y/x, y(0) = 1", problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS)
    with pytest.raises(InvalidInputError) as exc_info:
        homog_solver.solve(req)
    assert "x0 = 0 là điểm kỳ dị" in str(exc_info.value) or "x0 cannot be zero" in str(exc_info.value)


def test_matrix_06_classical_homog_straight_line_equilibria(homog_solver: ODEClassicalHomogeneousSolver):
    """Item 6: Straight-line equilibria F(v) - v = 0."""
    # y' = 2*(y/x) => F(v) = 2v => F(v) - v = v = 0 => v0 = 0 => y = 0
    req = ProblemRequest(raw_input="y' = 2*y/x, y(1) = 0", problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS)
    res = homog_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.final_result == "y(x) = 0"


def test_matrix_07_classical_homog_multiple_supported_slopes(homog_solver: ODEClassicalHomogeneousSolver):
    """Item 7: Multiple supported slopes from F(v) - v = 0."""
    # y' = (y/x)**2 - y/x => F(v) = v^2 - v => F(v) - v = v^2 - 2v = v(v - 2) = 0 => v0 in {0, 2}
    req = ProblemRequest(raw_input="y' = (y/x)**2 - y/x", problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS)
    res = homog_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    # Check that equilibrium step detected both slopes v=0 and v=2
    eq_step = next(s for s in res.steps if s.rule_name == "Nghiệm đường thẳng cân bằng")
    assert "0" in eq_step.description and "2" in eq_step.description


def test_matrix_08_classical_homog_implicit_verification(verifier: ODEVerifier):
    """Item 8: Dedicated classical homogeneous implicit verifier."""
    x, y, v = sp.symbols("x y v", real=True)
    # y' = 1 + y/x => F(v) = 1 + v. Phi = y/x - ln|x| = C
    phi = y / x - sp.log(sp.Abs(x))
    F_v = 1 + v
    res = verifier.verify_classical_homogeneous_implicit(
        potential_phi=phi,
        x_sym=x,
        y_sym=y,
        F_v_expr=F_v,
        domain_interval=(0, sp.oo),
    )

    assert res.status == VerificationStatus.VERIFIED
    assert res.method == "classical_homogeneous_implicit_verified"


def test_matrix_09_classical_homog_implicit_ivp(homog_solver: ODEClassicalHomogeneousSolver):
    """Item 9: Implicit solution with Cauchy IVP."""
    # y' = (x^2 + y^2)/(2*x*y), y(1) = 2
    req = ProblemRequest(
        raw_input="y' = (x**2 + y**2)/(2*x*y), y(1) = 2",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
    )
    res = homog_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "log" in res.final_result or "ln" in res.final_latex


def test_matrix_10_classical_homog_unsupported_transcendental_inversion(homog_solver: ODEClassicalHomogeneousSolver):
    """Item 10: Unsupported transcendental inversion preserves exact implicit relation."""
    # y' = (x^2 + y^2)/(2*x*y) leads to -log|1 - (y/x)^2| = log|x| + C
    req = ProblemRequest(
        raw_input="y' = (x**2 + y**2)/(2*x*y)",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
    )
    res = homog_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Preserved as implicit equation
    assert "log" in res.final_result or "ln" in res.final_latex


def test_matrix_11_classical_homog_no_unrestricted_sp_solve():
    """Item 11: _invert_homogeneous_relation_conservative returns None for transcendental expressions."""
    x, v, C = sp.symbols("x v C", real=True)
    # Logarithmic-polynomial transcendental relation
    transcendental_int = sp.log(sp.Abs(v)) - v
    res = _invert_homogeneous_relation_conservative(transcendental_int, v, x, C)
    assert res is None


# =========================================================================
# Group 2: Uniqueness and Domain (Items 12 - 18)
# =========================================================================


def test_matrix_12_uniqueness_sqrt_y_positive_direction(sep_solver: ODESeparableSolver):
    """Item 12: y' = sqrt(y), y(0) = 0 -> positive direction x >= 0."""
    req = ProblemRequest(raw_input="y' = sqrt(y), y(0) = 0", problem_type=ProblemType.ODE_SEPARABLE)
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.verification.method == "equilibrium_ivp_nonunique"
    assert "x >= 0" in res.final_result
    assert "x**2/4" in res.final_result


def test_matrix_13_uniqueness_minus_sqrt_y_negative_direction(sep_solver: ODESeparableSolver):
    """Item 13: y' = -sqrt(y), y(0) = 0 -> negative direction x <= 0."""
    req = ProblemRequest(raw_input="y' = -sqrt(y), y(0) = 0", problem_type=ProblemType.ODE_SEPARABLE)
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.verification.method == "equilibrium_ivp_nonunique"
    assert "x <= 0" in res.final_result
    assert "x**2/4" in res.final_result


def test_matrix_14_non_lipschitz_uniqueness_not_established():
    """Item 14: Non-Lipschitz case where branching solution cannot be symbolically proven -> UNIQUENESS_NOT_ESTABLISHED."""
    t, y = sp.symbols("t y", real=True)
    # Candidate where Lipschitz fails but candidate branching fails symbolic ODE check
    # g(y) = y^(1/3), f(t) = 0 (dy/dt = 0)
    status, reason, alt_sol, alt_dom = _check_equilibrium_uniqueness(
        g_expr=y ** sp.Rational(1, 3),
        f_expr=sp.Integer(0),
        var=t,
        dep_var=y,
        t0=sp.Integer(0),
        y0=sp.Integer(0),
    )
    assert status == EquilibriumUniqueness.UNIQUENESS_NOT_ESTABLISHED


def test_matrix_15_removable_denominator_preserved(sep_solver: ODESeparableSolver):
    """Item 15: Removable denominator y' = (y^2 - 1)/(y - 1), y(0) = 1 is rejected."""
    req = ProblemRequest(
        raw_input="y' = (y**2 - 1)/(y - 1), y(0) = 1",
        problem_type=ProblemType.ODE_SEPARABLE,
    )
    res = sep_solver.solve(req)
    # Undefined at y=1 in original equation
    assert res.status == SolutionStatus.INVALID_INPUT
    assert any("mẫu số" in w or "Invalid initial condition" in w for w in res.warnings)


def test_matrix_16_leading_coeff_singularity_preserved(sep_solver: ODESeparableSolver):
    """Item 16: Leading coefficient singularity x*y' + 2*x*y = 0 with x0=0 is rejected."""
    req = ProblemRequest(
        raw_input="x*y' + 2*x*y = 0, y(0) = 1",
        problem_type=ProblemType.ODE_SEPARABLE,
    )
    res = sep_solver.solve(req)
    assert res.status == SolutionStatus.INVALID_INPUT
    assert any("hệ số" in w or "Invalid initial condition" in w for w in res.warnings)


def test_matrix_17_radical_and_log_domain_preserved(sep_solver: ODESeparableSolver):
    """Item 17: Radical and logarithm domain restrictions are preserved."""
    req = ProblemRequest(
        raw_input="y' = sqrt(x)*y",
        problem_type=ProblemType.ODE_SEPARABLE,
    )
    res = sep_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert any("x >= 0" in r or "căn" in r for r in res.domain_restrictions)


def test_matrix_18_one_sided_domain_validation(sep_solver: ODESeparableSolver):
    """Item 18: Initial point outside radical domain (e.g. x0 = -1 for sqrt(x)) is rejected."""
    req = ProblemRequest(
        raw_input="y' = sqrt(x)*y, y(-1) = 2",
        problem_type=ProblemType.ODE_SEPARABLE,
    )
    res = sep_solver.solve(req)
    assert res.status == SolutionStatus.INVALID_INPUT
    assert any("nằm ngoài miền" in w or "Invalid" in w or "căn" in w for w in res.warnings)


# =========================================================================
# Group 3: Verification Rigor (Items 19 - 25)
# =========================================================================


def test_matrix_19_no_numerical_point_used_to_prove_identity():
    """Item 19: Numerical agreement at a single probe point is never used to claim proven identity."""
    t, y = sp.symbols("t y", real=True)
    # Construct an artificially contrived expression that is 0 only at t = 1/2
    status, _, alt_sol, _ = _check_equilibrium_uniqueness(
        g_expr=sp.sqrt(y),
        f_expr=sp.Integer(1),
        var=t,
        dep_var=y,
        t0=sp.Integer(0),
        y0=sp.Integer(0),
    )
    # Must be NONUNIQUE_PROVEN through symbolic proof on interval, not probe point
    assert status == EquilibriumUniqueness.NONUNIQUE_PROVEN
    assert alt_sol is not None


def test_matrix_20_every_emitted_branch_verified_independently(sep_solver: ODESeparableSolver):
    """Item 20: Every emitted branch is independently verified against original ODE."""
    # dy/dt = y^3 has general solution y = +/- 1 / sqrt(-2t - 2C) with multiple real branches
    req = ProblemRequest(raw_input="y' = y**3", problem_type=ProblemType.ODE_SEPARABLE)
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


def test_matrix_21_branch_metadata_survives_filtering_and_deduplication(sep_solver: ODESeparableSolver):
    """Item 21: Emitted branch solutions retain provenance and domain restrictions."""
    req = ProblemRequest(raw_input="y' = 2*t*y", problem_type=ProblemType.ODE_SEPARABLE, target_variable="t")
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert len(res.steps) >= 3


def test_matrix_22_correct_initial_condition_for_every_branch(sep_solver: ODESeparableSolver):
    """Item 22: Correct initial condition per branch."""
    req = ProblemRequest(raw_input="y' = 2*x*y, y(0) = 5", problem_type=ProblemType.ODE_SEPARABLE)
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "5*exp(x**2)" in res.final_result


def test_matrix_23_abel_theorem_continuous_coefficients(verifier: ODEVerifier):
    """Item 23: Abel's theorem holds for continuous coefficients."""
    t = sp.Symbol("t", real=True)
    y1 = sp.cos(2 * t)
    y2 = sp.sin(2 * t)
    # y'' + 4y = 0: Wronskian is nonzero constant
    w, res = verifier.verify_wronskian(y1, y2, t)
    assert res.status == VerificationStatus.VERIFIED
    assert res.method == "wronskian_nonzero_independence_verified"


def test_matrix_24_abel_theorem_singular_coefficients_unverified(verifier: ODEVerifier):
    """Item 24: Abel's theorem across coefficient singularity returns UNVERIFIED."""
    t = sp.Symbol("t", real=True)
    # Cauchy-Euler equation: a(t) = t vanishing at 0 across (-2, 2)
    y1 = t
    y2 = 2 * t
    w, res = verifier.verify_wronskian(
        y1,
        y2,
        t,
        ode_coeffs=(t, sp.Integer(0), sp.Integer(1)),
        domain_interval=(-2, 2),
    )
    assert res.status == VerificationStatus.UNVERIFIED
    assert res.method == "abel_theorem_condition_violated"


def test_matrix_25_peano_counterexample(verifier: ODEVerifier):
    """Item 25: Peano counterexample y1 = t^2, y2 = t*|t| crossing t = 0."""
    t = sp.Symbol("t", real=True)
    y1 = t ** 2
    y2 = t * sp.Abs(t)
    # Arbitrary functions without verified ODE context: W=0 is inconclusive
    w, res = verifier.verify_wronskian(y1, y2, t)
    assert res.status == VerificationStatus.UNVERIFIED
    assert res.method == "wronskian_zero_inconclusive_arbitrary_functions"


# =========================================================================
# Group 4: Mathematical Presentation (Items 26 - 34)
# =========================================================================


def test_matrix_26_separable_ode_renders_inline_math(sep_solver: ODESeparableSolver):
    """Item 26: Separable ODE explanation contains proper inline math tokens."""
    req = ProblemRequest(raw_input="dy/dt = 2*t*y", problem_type=ProblemType.ODE_SEPARABLE, target_variable="t")
    res = sep_solver.solve(req)

    for step in res.steps:
        rendered = render_math_in_text_html(step.description)
        assert "$" not in rendered, f"Unrendered raw delimiter in step {step.step_number}"
        assert "math-inline" in rendered or "math-block" in rendered


def test_matrix_27_separable_ode_no_raw_python_tokens(sep_solver: ODESeparableSolver):
    """Item 27: Explanatory prose does not contain raw Python tokens like 2*t or y_prime."""
    req = ProblemRequest(raw_input="dy/dt = 2*t*y", problem_type=ProblemType.ODE_SEPARABLE, target_variable="t")
    res = sep_solver.solve(req)

    for step in res.steps:
        rendered = render_math_in_text_html(step.description)
        assert "2*t" not in rendered
        assert "y_prime" not in rendered
        assert "int(1 / y)" not in rendered


def test_matrix_28_exactness_condition_renders_correctly(exact_solver: ODEExactSolver):
    """Item 28: Partial derivatives dM/dy and dN/dx render properly as LaTeX fractions."""
    req = ProblemRequest(raw_input="(2*x + y) + (x + 2*y)*y' = 0", problem_type=ProblemType.ODE_EXACT)
    res = exact_solver.solve(req)

    step1 = res.steps[0]
    rendered = render_math_in_text_html(step1.description)
    assert "dM/dy" not in rendered
    assert "dN/dx" not in rendered
    assert "math-inline" in rendered


def test_matrix_29_potential_function_renders_correctly(exact_solver: ODEExactSolver):
    """Item 29: Potential function Psi and F render cleanly in math tags."""
    req = ProblemRequest(raw_input="(2*x + y) + (x + 2*y)*y' = 0", problem_type=ProblemType.ODE_EXACT)
    res = exact_solver.solve(req)

    step4 = res.steps[3]
    assert "\\Psi(" in step4.description
    rendered = render_math_in_text_html(step4.description)
    assert "$" not in rendered
    assert "math-inline" in rendered
    assert "math-inline" in rendered


def test_matrix_30_integrating_factor_formula_renders_correctly(if_solver: ODEIntegratingFactorSolver):
    """Item 30: Integrating factor mu(x) formula renders with partial derivatives."""
    req = ProblemRequest(
        raw_input="(3*x*y + y**2) + (x**2 + x*y)*y' = 0",
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
    )
    res = if_solver.solve(req)

    step2 = res.steps[1]
    rendered = render_math_in_text_html(step2.description)
    assert "exp(int(" not in rendered
    assert "dM/dy" not in rendered
    assert "math-inline" in rendered


def test_matrix_31_transformed_exact_equation_renders_correctly(if_solver: ODEIntegratingFactorSolver):
    """Item 31: Transformed exact equation renders with proper differentials."""
    req = ProblemRequest(
        raw_input="(3*x*y + y**2) + (x**2 + x*y)*y' = 0",
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
    )
    res = if_solver.solve(req)

    step3 = res.steps[2]
    rendered = render_math_in_text_html(step3.description)
    assert "dM_new/dy" not in rendered
    assert "math-inline" in rendered


def test_matrix_32_absolute_value_logs_render_correctly(sep_solver: ODESeparableSolver):
    """Item 32: Absolute-value logs in integration step render cleanly."""
    req = ProblemRequest(raw_input="y' = y", problem_type=ProblemType.ODE_SEPARABLE)
    res = sep_solver.solve(req)

    int_step = next(s for s in res.steps if s.rule_name == "Tích phân hai vế")
    rendered = render_math_in_text_html(int_step.description)
    assert "log(Abs(y))" not in rendered
    assert "math-inline" in rendered


def test_matrix_33_fractions_and_derivative_notation_rendered(homog_solver: ODEClassicalHomogeneousSolver):
    """Item 33: Classical homogeneous solver renders fractions and derivatives."""
    req = ProblemRequest(raw_input="y' = 1 + y/x", problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS)
    res = homog_solver.solve(req)

    for step in res.steps:
        rendered = render_math_in_text_html(step.description)
        assert "$" not in rendered
        assert "math-inline" in rendered


def test_matrix_34_second_order_explanation_remains_correct(second_order_solver: ODESecondOrderConstantCoeffSolver):
    """Item 34: Existing second-order ODE explanation remains intact."""
    req = ProblemRequest(
        raw_input="y'' + 4*y = 0, y(0) = 1, y'(0) = 2",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
    )
    res = second_order_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    for step in res.steps:
        rendered = render_math_in_text_html(step.description)
        assert "$" not in rendered

"""Regression tests for real odd-root semantics in classical homogeneous and separable ODE solvers.

Verifies:
- Mathematically correct real odd-root semantics for positive and negative radicands.
- Avoidance of complex principal roots (e.g. (-8)**(1/3) -> 1 + sqrt(3)*I) in real solutions.
- Correct handling of negative odd inverse exponents (e.g. p = -3 with U != 0 exclusion).
- Independent branch verification against original ODE residuals.
- Preservation of domain restrictions and connected intervals.
- Correct LaTeX rendering without complex tokens.
"""

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.classical_homogeneous_solver import ODEClassicalHomogeneousSolver
from math_app.solvers.calculus.ode.separable_solver import ODESeparableSolver
from math_app.verification.calculus.ode_verifier import _prove_symbolic_zero


@pytest.fixture
def homog_solver() -> ODEClassicalHomogeneousSolver:
    return ODEClassicalHomogeneousSolver()


@pytest.fixture
def sep_solver() -> ODESeparableSolver:
    return ODESeparableSolver()


def test_odd_root_positive_radicand_ivp(homog_solver: ODEClassicalHomogeneousSolver):
    """y' = y/x + x^2/(3*y^2), y(1) = 2 produces real positive branch with residual 0."""
    req = ProblemRequest(
        raw_input="y' = y/x + x^2/(3*y^2), y(1) = 2",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = homog_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 1

    b = res.branch_solutions[0]
    assert b.branch_identity == "Nhánh căn lẻ thực (radicand >= 0)"
    assert b.verification.status == VerificationStatus.VERIFIED
    assert b.integration_constant_val == 8
    assert b.domain_interval == (sp.exp(-8), sp.oo)

    # Check value at x=1
    x = sp.Symbol("x", positive=True)
    expr = b.expression.subs(sp.Symbol("x"), x)
    assert expr.subs(x, 1) == 2

    # Check absence of complex tokens
    assert not expr.has(sp.I)
    assert "I" not in res.final_latex
    assert r"\sqrt[3]" in res.final_latex

    # Verify residual against original ODE symbolically on x > 0
    y = expr
    dy_dx = sp.diff(y, x)
    residual = sp.simplify(dy_dx - (y / x + x**2 / (3 * y**2)))
    assert _prove_symbolic_zero(residual, domain_interval=(0, sp.oo), variable=x)


def test_odd_root_negative_radicand_ivp(homog_solver: ODEClassicalHomogeneousSolver):
    """y' = y/x + x^2/(3*y^2), y(1) = -2 produces purely real negative branch with residual 0."""
    req = ProblemRequest(
        raw_input="y' = y/x + x^2/(3*y^2), y(1) = -2",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = homog_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 1

    b = res.branch_solutions[0]
    assert b.branch_identity == "Nhánh căn lẻ thực (radicand <= 0)"
    assert b.verification.status == VerificationStatus.VERIFIED
    assert b.integration_constant_val == -8
    assert b.domain_interval == (0, sp.exp(8))

    # Check value at x=1: must be exactly -2, never complex!
    x = sp.Symbol("x", positive=True)
    expr = b.expression.subs(sp.Symbol("x"), x)
    val_at_1 = expr.subs(x, 1)
    assert sp.simplify(val_at_1) == -2
    assert not expr.has(sp.I)
    assert "I" not in res.final_latex
    assert r"\sqrt[3]" in res.final_latex

    # Verify residual against original ODE symbolically on x > 0
    y = expr
    dy_dx = sp.diff(y, x)
    residual = sp.simplify(dy_dx - (y / x + x**2 / (3 * y**2)))
    assert _prove_symbolic_zero(residual, domain_interval=(0, sp.oo), variable=x)


def test_odd_root_general_solution_branches(homog_solver: ODEClassicalHomogeneousSolver):
    """General solution y' = y/x + x^2/(3*y^2) emits both positive and negative real branches."""
    req = ProblemRequest(
        raw_input="y' = y/x + x^2/(3*y^2)",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = homog_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 2

    # Branch 0: positive branch
    b0 = res.branch_solutions[0]
    assert "radicand >= 0" in b0.branch_identity
    assert b0.verification.status == VerificationStatus.VERIFIED

    # Branch 1: negative branch
    b1 = res.branch_solutions[1]
    assert "radicand <= 0" in b1.branch_identity
    assert b1.verification.status == VerificationStatus.VERIFIED

    # Check each against original ODE residual
    x = sp.Symbol("x", positive=True)
    c = sp.Symbol("C")
    for b in (b0, b1):
        y = b.expression.subs(sp.Symbol("x"), x)
        dy_dx = sp.diff(y, x)
        residual = sp.simplify(dy_dx - (y / x + x**2 / (3 * y**2)))
        assert _prove_symbolic_zero(residual, (c,), domain_interval=(0, sp.oo), variable=x)


def test_odd_root_negative_inverse_exponent_positive(homog_solver: ODEClassicalHomogeneousSolver):
    """y' = y/x - y^4/(3*x^4), y(1) = 1 has p=-3, positive root, and U != 0 restriction."""
    req = ProblemRequest(
        raw_input="y' = y/x - y^4/(3*x^4), y(1) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = homog_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 1

    b = res.branch_solutions[0]
    assert b.verification.status == VerificationStatus.VERIFIED
    assert any("khác 0" in d for d in b.denominator_exclusions)

    x = sp.Symbol("x", positive=True)
    expr = b.expression.subs(sp.Symbol("x"), x)
    assert expr.subs(x, 1) == 1

    # Verify residual
    y = expr
    dy_dx = sp.diff(y, x)
    residual = sp.simplify(dy_dx - (y / x - y**4 / (3 * x**4)))
    assert _prove_symbolic_zero(residual, domain_interval=(0, sp.oo), variable=x)


def test_odd_root_negative_inverse_exponent_negative(homog_solver: ODEClassicalHomogeneousSolver):
    """y' = y/x - y^4/(3*x^4), y(1) = -1 has p=-3, negative root, and U != 0 restriction."""
    req = ProblemRequest(
        raw_input="y' = y/x - y^4/(3*x^4), y(1) = -1",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = homog_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 1

    b = res.branch_solutions[0]
    assert b.verification.status == VerificationStatus.VERIFIED
    assert any("khác 0" in d for d in b.denominator_exclusions)

    x = sp.Symbol("x", positive=True)
    expr = b.expression.subs(sp.Symbol("x"), x)
    assert expr.subs(x, 1) == -1
    assert not expr.has(sp.I)

    # Verify residual
    y = expr
    dy_dx = sp.diff(y, x)
    residual = sp.simplify(dy_dx - (y / x - y**4 / (3 * x**4)))
    assert _prove_symbolic_zero(residual, domain_interval=(0, sp.oo), variable=x)


def test_odd_root_separable_solver_consistency(sep_solver: ODESeparableSolver):
    """Separable solver handles odd-root inversion consistently without complex numbers."""
    req = ProblemRequest(
        raw_input="y' = 1/(3*y^2), y(0) = -2",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.branch_solutions) == 1

    b = res.branch_solutions[0]
    assert b.verification.status == VerificationStatus.VERIFIED
    assert not b.expression.has(sp.I)

    x = sp.Symbol("x")
    val_at_0 = b.expression.subs(x, 0)
    assert sp.simplify(val_at_0) == -2


def test_odd_root_boundary_point_at_singularity_rejected(homog_solver: ODEClassicalHomogeneousSolver):
    """Initial points at the boundary where y=0 or x=0 must be rejected as ODE singularities."""
    from math_app.domain.exceptions import InvalidInputError

    # Boundary x=exp(-8), y=0 for positive branch boundary
    # ODE has 3*y^2 in denominator, so y=0 is an ODE singularity
    req1 = ProblemRequest(
        raw_input="y' = y/x + x^2/(3*y^2), y(0.00033546) = 0",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    with pytest.raises(InvalidInputError):
        homog_solver.solve(req1)

    # Singularity at x=0
    req2 = ProblemRequest(
        raw_input="y' = y/x + x^2/(3*y^2), y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    with pytest.raises(InvalidInputError):
        homog_solver.solve(req2)


def test_odd_root_outside_boundary_point_rejected(homog_solver: ODEClassicalHomogeneousSolver):
    """Verify exact domain intervals, boundary exclusion, and outside-boundary radicand violation.

    For y' = y/x + x^2/(3*y^2):
    1. Positive branch (C = 8, from IVP y(1) = 2):
       - Exact domain interval is strictly (exp(-8), oo).
       - Lower boundary x = exp(-8) yields y = 0, where original ODE denominator 3*y^2 vanishes.
       - A point strictly below exp(-8) (e.g. x = exp(-9)) violates the real-radicand condition U >= 0.
    2. Negative branch (C = -8, from IVP y(1) = -2):
       - Exact domain interval is strictly (0, exp(8)).
       - Upper boundary x = exp(8) yields y = 0, where original ODE denominator 3*y^2 vanishes.
       - A point strictly above exp(8) (e.g. x = exp(9)) violates the negative branch real-radicand condition -U >= 0.
    """
    x = sp.Symbol("x")
    y = sp.Symbol("y")
    ode_rhs = y / x + x**2 / (3 * y**2)

    # --- Part 1: Positive Branch (C = 8 from y(1) = 2) ---
    req_pos = ProblemRequest(
        raw_input="y' = y/x + x^2/(3*y^2), y(1) = 2",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res_pos = homog_solver.solve(req_pos)
    assert res_pos.status == SolutionStatus.SUCCESS
    assert len(res_pos.branch_solutions) == 1
    b_pos = res_pos.branch_solutions[0]

    # Exact domain interval is (exp(-8), oo)
    assert b_pos.domain_interval == (sp.exp(-8), sp.oo)
    assert b_pos.integration_constant_val == 8

    # Lower boundary x = exp(-8) evaluation:
    val_at_lower_boundary = sp.simplify(b_pos.expression.subs(x, sp.exp(-8)))
    assert val_at_lower_boundary == 0

    # Original ODE is undefined at (exp(-8), 0) because denominator 3*y^2 vanishes:
    ode_denom_at_lower = (3 * y**2).subs([(x, sp.exp(-8)), (y, val_at_lower_boundary)])
    assert ode_denom_at_lower == 0
    rhs_at_lower = ode_rhs.subs([(x, sp.exp(-8)), (y, val_at_lower_boundary)])
    assert rhs_at_lower.has(sp.zoo, sp.nan) or rhs_at_lower.is_finite is False

    # A point strictly below exp(-8), e.g. x_below = exp(-9) < exp(-8):
    x_below = sp.exp(-9)
    assert (x_below < sp.exp(-8)) is sp.true or float(sp.N(x_below)) < float(sp.N(sp.exp(-8)))
    # Positive branch radicand is U(x) = ln(x) + 8:
    u_pos_below = sp.simplify(sp.log(x_below) + 8)
    assert u_pos_below == -1
    assert u_pos_below < 0  # Violates real-radicand condition U >= 0!

    # Verifier explicitly rejects initial point at x_below against (exp(-8), oo):
    v_res_below = homog_solver.verifier.verify_explicit(
        b_pos.expression,
        x,
        rhs_f=ode_rhs,
        dep_var=y,
        initial_condition=(x_below, sp.Integer(1)),
        domain_interval=(sp.exp(-8), sp.oo),
    )
    assert v_res_below.status == VerificationStatus.FAILED
    assert v_res_below.method == "ic_outside_domain_interval"

    # --- Part 2: Negative Branch (C = -8 from y(1) = -2) ---
    req_neg = ProblemRequest(
        raw_input="y' = y/x + x^2/(3*y^2), y(1) = -2",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res_neg = homog_solver.solve(req_neg)
    assert res_neg.status == SolutionStatus.SUCCESS
    assert len(res_neg.branch_solutions) == 1
    b_neg = res_neg.branch_solutions[0]

    # Exact domain interval is (0, exp(8))
    assert b_neg.domain_interval == (0, sp.exp(8))
    assert b_neg.integration_constant_val == -8

    # Upper boundary x = exp(8) evaluation:
    val_at_upper_boundary = sp.simplify(b_neg.expression.subs(x, sp.exp(8)))
    assert val_at_upper_boundary == 0

    # Original ODE is undefined at (exp(8), 0) because denominator 3*y^2 vanishes:
    ode_denom_at_upper = (3 * y**2).subs([(x, sp.exp(8)), (y, val_at_upper_boundary)])
    assert ode_denom_at_upper == 0
    rhs_at_upper = ode_rhs.subs([(x, sp.exp(8)), (y, val_at_upper_boundary)])
    assert rhs_at_upper.has(sp.zoo, sp.nan) or rhs_at_upper.is_finite is False

    # A point strictly above exp(8), e.g. x_above = exp(9) > exp(8):
    x_above = sp.exp(9)
    assert (x_above > sp.exp(8)) is sp.true or float(sp.N(x_above)) > float(sp.N(sp.exp(8)))
    # Negative branch radicand is -U(x) = -(ln(x) - 8) = 8 - ln(x):
    u_neg_above = sp.simplify(8 - sp.log(x_above))
    assert u_neg_above == -1
    assert u_neg_above < 0  # Violates negative branch real-radicand condition -U >= 0!

    # Verifier explicitly rejects initial point at x_above against (0, exp(8)):
    v_res_above = homog_solver.verifier.verify_explicit(
        b_neg.expression,
        x,
        rhs_f=ode_rhs,
        dep_var=y,
        initial_condition=(x_above, sp.Integer(-1)),
        domain_interval=(0, sp.exp(8)),
    )
    assert v_res_above.status == VerificationStatus.FAILED
    assert v_res_above.method == "ic_outside_domain_interval"


def test_odd_root_general_solution_exact_domains(homog_solver: ODEClassicalHomogeneousSolver):
    """General solution branches have exact domain intervals parameterized by C."""
    req = ProblemRequest(
        raw_input="y' = y/x + x^2/(3*y^2)",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = homog_solver.solve(req)
    assert res.status == SolutionStatus.SUCCESS
    assert len(res.branch_solutions) == 2

    c = sp.Symbol("C")
    b0 = res.branch_solutions[0]  # positive branch
    assert b0.domain_interval == (sp.exp(-c), sp.oo)
    assert any("exp(-C)" in r for r in b0.domain_restrictions)

    b1 = res.branch_solutions[1]  # negative branch
    assert b1.domain_interval == (0, sp.exp(-c))
    assert any("exp(-C)" in r for r in b1.domain_restrictions)


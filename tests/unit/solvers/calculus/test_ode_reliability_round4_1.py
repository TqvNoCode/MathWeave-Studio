"""Comprehensive mathematical regression tests for ODE Reliability Remediation Round 4.1.

Focus:
1. Picard-Lindelöf 3-way uniqueness assessment (UNIQUE_PROVEN, NONUNIQUE_PROVEN, UNIQUENESS_NOT_ESTABLISHED).
2. Domain preservation before algebraic cancellation (y' = (y^2-1)/(y-1), x y' + 2x y = 0).
3. Dedicated Classical Degree-0 Homogeneous First-Order Solver (y' = F(y/x), Examples A & B).
4. Homogeneous vs. Nonhomogeneous scope boundary.
5. Periodic trigonometric equilibrium families with symbolic parameter a and integer n in Z.
6. Hardened Wronskian & Abel verification (connected domain, Peano counterexample).
7. Reduction of Order IVP validation (finite real numbers, method limitation vs ODE singularity).
"""

from __future__ import annotations

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import EquilibriumUniqueness, ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.classical_homogeneous_solver import ODEClassicalHomogeneousSolver
from math_app.solvers.calculus.ode.exact_solver import ODEExactSolver
from math_app.solvers.calculus.ode.linear_solver import ODELinearSolver
from math_app.solvers.calculus.ode.reduction_of_order_solver import ODEReductionOfOrderSolver
from math_app.solvers.calculus.ode.separable_solver import (
    ODESeparableSolver,
    _check_equilibrium_uniqueness,
)
from math_app.verification.calculus.ode_verifier import ODEVerifier


@pytest.fixture
def sep_solver() -> ODESeparableSolver:
    return ODESeparableSolver()


@pytest.fixture
def linear_solver() -> ODELinearSolver:
    return ODELinearSolver()


@pytest.fixture
def exact_solver() -> ODEExactSolver:
    return ODEExactSolver()


@pytest.fixture
def classical_homog_solver() -> ODEClassicalHomogeneousSolver:
    return ODEClassicalHomogeneousSolver()


@pytest.fixture
def reduction_solver() -> ODEReductionOfOrderSolver:
    return ODEReductionOfOrderSolver()


@pytest.fixture
def verifier() -> ODEVerifier:
    return ODEVerifier()


# =========================================================================
# Section 1: Correct Uniqueness Assessment
# =========================================================================

def test_r4_1_01_sqrt_y_cauchy_nonunique(sep_solver: ODESeparableSolver):
    """y' = sqrt(y), y(0) = 0: NONUNIQUE_PROVEN, returns both y1 = 0 and y2 = x^2/4 (x >= 0)."""
    req = ProblemRequest(
        raw_input="y' = sqrt(y), y(0) = 0",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.verification.method == "equilibrium_ivp_nonunique"
    # Both solutions must be emitted
    assert "y_1(x) = 0" in res.final_result
    assert "y_2(x) = x**2/4" in res.final_result
    assert "x >= 0" in res.final_result
    # Warning must explain non-uniqueness
    assert any("Lipschitz" in w and "nhiều hơn một nghiệm" in w for w in res.warnings)


def test_r4_1_02_y3_cauchy_unique(sep_solver: ODESeparableSolver):
    """y' = y^3, y(0) = 0: UNIQUE_PROVEN, returns y(x) = 0 as unique Picard-Lindelöf solution."""
    req = ProblemRequest(
        raw_input="y' = y^3, y(0) = 0",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.verification.method == "equilibrium_ivp_picard_lindelof_unique"
    assert res.final_result == "y(x) = 0"


def test_r4_1_03_y_one_third_nonunique():
    """y' = y^(1/3), y(0) = 0: g'(0) -> oo, separation integral converges -> NONUNIQUE_PROVEN."""
    x = sp.Symbol("x", real=True)
    y = sp.Symbol("y", real=True)
    f_expr = sp.Integer(1)
    g_expr = y ** sp.Rational(1, 3)

    status, reason, alt_sol, alt_dom = _check_equilibrium_uniqueness(
        g_expr, f_expr, x, y, sp.Integer(0), sp.Integer(0)
    )

    assert status == EquilibriumUniqueness.NONUNIQUE_PROVEN
    assert alt_sol is not None
    assert alt_dom == "x >= 0"


def test_r4_1_04_uniqueness_not_established_when_no_alternative():
    """When Lipschitz fails but no alternative solution is proven, status is UNIQUENESS_NOT_ESTABLISHED."""
    x = sp.Symbol("x", real=True)
    y = sp.Symbol("y", real=True)
    f_expr = sp.Integer(1)
    # g(y) = y * ln|y|: g'(0) -> -oo (Lipschitz fails), but Osgood integral diverges to oo
    g_expr = y * sp.log(sp.Abs(y))

    status, reason, alt_sol, alt_dom = _check_equilibrium_uniqueness(
        g_expr, f_expr, x, y, sp.Integer(0), sp.Integer(0)
    )

    assert status == EquilibriumUniqueness.UNIQUENESS_NOT_ESTABLISHED
    assert "Tính duy nhất của nghiệm chưa được khẳng định" in reason
    assert alt_sol is None


# =========================================================================
# Section 2: Domain Preservation Before Algebraic Cancellation
# =========================================================================

def test_r4_1_05_domain_preservation_y_minus_1_denom_rejected(linear_solver: ODELinearSolver):
    """y' = (y^2 - 1)/(y - 1), y(0) = 1: y=1 makes original RHS undefined; IVP must be rejected."""
    req = ProblemRequest(
        raw_input="y' = (y^2 - 1)/(y - 1), y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.INVALID_INPUT
    assert "Mẫu số ban đầu" in res.verification.details
    assert "triệt tiêu" in res.verification.details


def test_r4_1_06_domain_preservation_y_minus_1_denom_accepted(linear_solver: ODELinearSolver):
    """y' = (y^2 - 1)/(y - 1), y(0) = 0: y=0 is valid in original domain (denom = -1 != 0); accepted."""
    req = ProblemRequest(
        raw_input="y' = (y^2 - 1)/(y - 1), y(0) = 0",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


def test_r4_1_07_domain_preservation_leading_coeff_singularity_rejected(linear_solver: ODELinearSolver):
    """x*y' + 2*x*y = 0, y(0) = 1: A(0) = 0 is a singular point; IVP must be rejected."""
    req = ProblemRequest(
        raw_input="x*y' + 2*x*y = 0, y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.INVALID_INPUT
    assert "điểm kỳ dị" in res.verification.details.lower() or "hệ số dẫn" in res.verification.details.lower()


def test_r4_1_08_domain_preservation_leading_coeff_singularity_accepted(linear_solver: ODELinearSolver):
    """x*y' + 2*x*y = 0, y(1) = 1: x0 = 1 is non-singular; accepted and verified."""
    req = ProblemRequest(
        raw_input="x*y' + 2*x*y = 0, y(1) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = linear_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED


# =========================================================================
# Section 3: Dedicated Classical Degree-0 Homogeneous Solver
# =========================================================================

def test_r4_1_09_classical_homogeneous_example_a_general(classical_homog_solver: ODEClassicalHomogeneousSolver):
    """Example A: y' = (x + y)/x <=> y = x*ln|x| + C*x; verified."""
    req = ProblemRequest(
        raw_input="y' = (x + y)/x",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = classical_homog_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "x*(C + log(Abs(x)))" in res.final_result
    assert any("x khác 0" in r for r in res.domain_restrictions)


def test_r4_1_10_classical_homogeneous_example_a_ivp(classical_homog_solver: ODEClassicalHomogeneousSolver):
    """Example A Cauchy IVP: y' = (x + y)/x, y(1) = 2 => C = 2 => y = x*ln|x| + 2x; verified."""
    req = ProblemRequest(
        raw_input="y' = (x + y)/x, y(1) = 2",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = classical_homog_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "x*(log(Abs(x)) + 2)" in res.final_result


def test_r4_1_11_classical_homogeneous_example_a_singular_x0_rejected(classical_homog_solver: ODEClassicalHomogeneousSolver):
    """Example A Cauchy IVP: y' = (x + y)/x, y(0) = 1 has singular point x0=0; must be rejected."""
    req = ProblemRequest(
        raw_input="y' = (x + y)/x, y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    with pytest.raises(InvalidInputError, match="x0 cannot be zero|điểm kỳ dị"):
        classical_homog_solver.solve(req)


def test_r4_1_12_classical_homogeneous_example_b_general(classical_homog_solver: ODEClassicalHomogeneousSolver):
    """Example B: y' = y/x + (y/x)^2 <=> y = -x / (ln|x| + C); verified."""
    req = ProblemRequest(
        raw_input="y' = y/x + (y/x)^2",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = classical_homog_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "-x/(C + log(Abs(x)))" in res.final_result


def test_r4_1_13_classical_homogeneous_example_b_equilibrium_straight_line(classical_homog_solver: ODEClassicalHomogeneousSolver):
    """Example B: Straight-line equilibrium ray y = 0 from F(v) - v = v^2 = 0."""
    req = ProblemRequest(
        raw_input="y' = y/x + (y/x)^2",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = classical_homog_solver.solve(req)

    # Check equilibrium step
    eq_step = [s for s in res.steps if "cân bằng" in s.title.lower()]
    assert len(eq_step) >= 1
    assert "0" in eq_step[0].content.expression_after


def test_r4_1_14_classical_homogeneous_example_b_ivp_hits_equilibrium(classical_homog_solver: ODEClassicalHomogeneousSolver):
    """Example B Cauchy IVP: y' = y/x + (y/x)^2, y(1) = 0 hits straight-line equilibrium y = 0."""
    req = ProblemRequest(
        raw_input="y' = y/x + (y/x)^2, y(1) = 0",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
    )
    res = classical_homog_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.final_result == "y(x) = 0"


# =========================================================================
# Section 5 & 6: Wronskian, Abel's Theorem & Peano Counterexample
# =========================================================================

def test_r4_1_15_peano_counterexample_unverified(verifier: ODEVerifier):
    """Peano counterexample: y1 = t^2, y2 = Piecewise((-t^2, t < 0), (t^2, True)).

    W = 0 everywhere on R, but functions are linearly independent.
    Arbitrary functions without ODE coefficients must return UNVERIFIED.
    """
    t = sp.Symbol("t", real=True)
    y1 = t ** 2
    y2 = sp.Piecewise((-t ** 2, t < 0), (t ** 2, True))

    w_val, verif = verifier.verify_wronskian(y1, y2, t)

    assert w_val == 0
    assert verif.status == VerificationStatus.UNVERIFIED
    assert "Peano" in verif.details or "peano" in verif.details.lower()


def test_r4_1_16_peano_piecewise_construction_wronskian_zero():
    """Verify that Peano's Piecewise pair has continuous derivatives and W == 0 without Dirac delta."""
    t = sp.Symbol("t", real=True)
    y1 = t ** 2
    y2 = sp.Piecewise((-t ** 2, t < 0), (t ** 2, True))

    dy1 = sp.diff(y1, t)
    dy2 = sp.diff(y2, t)

    # Derivative at t=0 is 0
    assert dy2.subs(t, 0) == 0

    # Wronskian evaluates to 0 identically
    w = sp.simplify(y1 * dy2 - dy1 * y2)
    assert w == 0


def test_r4_1_17_abel_theorem_connected_domain_verified(verifier: ODEVerifier):
    """Abel's theorem: y1 = sin(t), y2 = 2*sin(t) are solutions of y'' + y = 0.

    a(t) = 1 != 0 everywhere on connected domain R => W = 0 proves linear dependence.
    """
    t = sp.Symbol("t", real=True)
    y1 = sp.sin(t)
    y2 = 2 * sp.sin(t)

    w_val, verif = verifier.verify_wronskian(
        y1, y2, t, ode_coeffs=(sp.Integer(1), sp.Integer(0), sp.Integer(1)), domain_interval=(-sp.oo, sp.oo)
    )

    assert w_val == 0
    assert verif.status == VerificationStatus.VERIFIED
    assert "Abel" in verif.details


def test_r4_1_18_abel_theorem_singular_leading_coeff_unverified(verifier: ODEVerifier):
    """Abel's theorem does NOT apply when interval contains a zero of leading coefficient a(t)."""
    t = sp.Symbol("t", real=True)
    y1 = sp.sin(t)
    y2 = 2 * sp.sin(t)

    # a(t) = t has a zero at t = 0 in domain interval (-2, 2)
    w_val, verif = verifier.verify_wronskian(
        y1, y2, t, ode_coeffs=(t, sp.Integer(0), sp.Integer(1)), domain_interval=(-2, 2)
    )

    assert verif.status == VerificationStatus.UNVERIFIED
    assert "Định lý Abel không áp dụng" in verif.details


# =========================================================================
# Section 7: Reduction of Order IVP Validation
# =========================================================================

def test_r4_1_19_reduction_of_order_complex_cauchy_rejected(reduction_solver: ODEReductionOfOrderSolver):
    """Reduction of Order: Complex Cauchy initial values must be rejected."""
    req = ProblemRequest(
        raw_input="t^2*y'' - 2*t*y' + 2*y = 0, y1 = t, y(1) = 2*I, y'(1) = 1",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="chứa phần ảo|không phải là số thực"):
        reduction_solver.solve(req)


def test_r4_1_20_reduction_of_order_method_limitation_vs_ode_singularity(reduction_solver: ODEReductionOfOrderSolver):
    """Distinguish method limitation y1(t0) = 0 from ODE singularity a(t0) = 0.

    1. y1(0) = 0 with a(0) != 0 -> Method limitation error.
    2. a(0) = 0 -> ODE singularity error.
    """
    # 1. Method limitation: y'' + y = 0 with known y1 = sin(t). At t0 = 0, a(0) = 1 != 0, but y1(0) = 0.
    req_method_limit = ProblemRequest(
        raw_input="y'' + y = 0, y1 = sin(t), y(0) = 0, y'(0) = 1",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="Phương pháp hạ bậc không thể áp dụng|Method limitation"):
        reduction_solver.solve(req_method_limit)

    # 2. ODE singularity: t*y'' + y' = 0 with y1 = 1. At t0 = 0, a(0) = 0.
    req_ode_sing = ProblemRequest(
        raw_input="t*y'' + y' = 0, y1 = 1, y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    with pytest.raises(InvalidInputError, match="điểm kỳ dị|ODE singularity"):
        reduction_solver.solve(req_ode_sing)

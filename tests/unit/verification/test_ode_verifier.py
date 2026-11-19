"""Unit tests for independent ODE verifier."""

import sympy as sp

from math_app.domain.models import VerificationStatus
from math_app.verification.calculus.ode_verifier import ODEVerifier


def test_ode_verifier_explicit_symbolic_residual():
    verifier = ODEVerifier()
    t, C = sp.symbols("t C")
    # ODE: y' + 2y = 4 => p = 2, g = 4, sol = C*exp(-2t) + 2
    sol = C * sp.exp(-2 * t) + 2
    res = verifier.verify_explicit(solution=sol, variable=t, p_expr=sp.Integer(2), g_expr=sp.Integer(4))

    assert res.status == VerificationStatus.VERIFIED
    assert "symbolic_zero_check" in res.method


def test_ode_verifier_with_initial_condition_satisfied():
    verifier = ODEVerifier()
    t = sp.symbols("t")
    # ODE: y' = 2y + 3, y(0) = 1 => sol = (5/2)*exp(2t) - 3/2
    sol = sp.Rational(5, 2) * sp.exp(2 * t) - sp.Rational(3, 2)
    res = verifier.verify_explicit(
        solution=sol,
        variable=t,
        p_expr=sp.Integer(-2),
        g_expr=sp.Integer(3),
        initial_condition=(sp.Integer(0), sp.Integer(1)),
    )

    assert res.status == VerificationStatus.VERIFIED
    assert "initial condition identically zero" in res.details or "nghiệm đúng" in res.details


def test_ode_verifier_initial_condition_mismatch():
    verifier = ODEVerifier()
    t = sp.symbols("t")
    # Satisfies ODE y' = 2y + 3, but y(0) is 1, test with wrong IC y(0) = 9
    sol = sp.Rational(5, 2) * sp.exp(2 * t) - sp.Rational(3, 2)
    res = verifier.verify_explicit(
        solution=sol,
        variable=t,
        p_expr=sp.Integer(-2),
        g_expr=sp.Integer(3),
        initial_condition=(sp.Integer(0), sp.Integer(9)),
    )

    assert res.status == VerificationStatus.FAILED
    assert "initial_condition_mismatch" in res.method


def test_ode_verifier_wrong_solution():
    verifier = ODEVerifier()
    t = sp.symbols("t")
    # Wrong solution for y' + y = 0
    wrong_sol = sp.exp(5 * t)
    res = verifier.verify_explicit(solution=wrong_sol, variable=t, p_expr=sp.Integer(1), g_expr=sp.Integer(0))

    assert res.status == VerificationStatus.FAILED


def test_ode_verifier_exact_potential_gradient_match():
    verifier = ODEVerifier()
    x, y = sp.symbols("x y")
    # M = 2xy + 3, N = x^2 + 4y => F(x, y) = x^2*y + 3x + 2y^2
    F = x**2 * y + 3 * x + 2 * y**2
    M = 2 * x * y + 3
    N = x**2 + 4 * y
    res = verifier.verify_exact(potential_F=F, M_expr=M, N_expr=N, x_sym=x, y_sym=y)

    assert res.status == VerificationStatus.VERIFIED
    assert "exact_potential_gradient_check" in res.method


def test_ode_verifier_exact_potential_gradient_mismatch():
    verifier = ODEVerifier()
    x, y = sp.symbols("x y")
    wrong_F = x**3 + y**3
    M = 2 * x * y + 3
    N = x**2 + 4 * y
    res = verifier.verify_exact(potential_F=wrong_F, M_expr=M, N_expr=N, x_sym=x, y_sym=y)

    assert res.status == VerificationStatus.FAILED
    assert "mismatch" in res.method


def test_ode_verifier_exact_with_ivp():
    verifier = ODEVerifier()
    x, y = sp.symbols("x y")
    F = x**2 * y + 3 * x + 2 * y**2
    M = 2 * x * y + 3
    N = x**2 + 4 * y
    res = verifier.verify_exact(
        potential_F=F,
        M_expr=M,
        N_expr=N,
        x_sym=x,
        y_sym=y,
        initial_condition=(sp.Integer(0), sp.Integer(1)),
    )

    assert res.status == VerificationStatus.VERIFIED
    assert "exact_potential_gradient_and_ic_check" in res.method


def test_ode_verifier_implicit_separable():
    verifier = ODEVerifier()
    x, y = sp.symbols("x y")
    # dy/dx = x^2 / (1 - y^2) => phi = y - y^3/3 - x^3/3
    phi = y - y**3 / 3 - x**3 / 3
    f_expr = x**2
    g_expr = 1 / (1 - y**2)
    res = verifier.verify_implicit(
        potential_phi=phi,
        x_sym=x,
        y_sym=y,
        rhs_f_expr=f_expr,
        rhs_g_expr=g_expr,
        initial_condition=(sp.Integer(0), sp.Integer(0)),
        c_val=sp.Integer(0),
    )

    assert res.status == VerificationStatus.VERIFIED
    assert "separable_implicit_derivation_verified" in res.method


def test_ode_verifier_implicit_separable_mismatch():
    verifier = ODEVerifier()
    x, y = sp.symbols("x y")
    wrong_phi = y**2 - x**2
    f_expr = x**2
    g_expr = 1 / (1 - y**2)
    res = verifier.verify_implicit(
        potential_phi=wrong_phi,
        x_sym=x,
        y_sym=y,
        rhs_f_expr=f_expr,
        rhs_g_expr=g_expr,
    )

    assert res.status == VerificationStatus.FAILED
    assert "implicit_differential_mismatch" in res.method


def test_ode_verifier_integrating_factor_success():
    verifier = ODEVerifier()
    x, y = sp.symbols("x y")
    # (3xy + y^2)dx + (x^2 + xy)dy = 0 with mu = x => F = x^3*y + x^2*y^2 / 2
    F = x**3 * y + sp.Rational(1, 2) * x**2 * y**2
    mu = x
    M = 3 * x * y + y**2
    N = x**2 + x * y
    res = verifier.verify_integrating_factor(
        potential_F=F,
        mu_expr=mu,
        M_expr=M,
        N_expr=N,
        x_sym=x,
        y_sym=y,
        initial_condition=(sp.Integer(1), sp.Integer(1)),
    )

    assert res.status == VerificationStatus.VERIFIED
    assert "integrating_factor" in res.method


def test_ode_verifier_integrating_factor_mismatch():
    verifier = ODEVerifier()
    x, y = sp.symbols("x y")
    wrong_F = x**2 + y**2
    mu = x
    M = 3 * x * y + y**2
    N = x**2 + x * y
    res = verifier.verify_integrating_factor(
        potential_F=wrong_F,
        mu_expr=mu,
        M_expr=M,
        N_expr=N,
        x_sym=x,
        y_sym=y,
    )

    assert res.status == VerificationStatus.FAILED
    assert "integrating_factor_gradient_mismatch" in res.method


def test_ode_verifier_second_order_residual_and_dual_ic():
    verifier = ODEVerifier()
    t = sp.Symbol("t")
    # y'' + 5y' + 6y = 0, y(0) = 2, y'(0) = 3 => sol = 9*exp(-2t) - 7*exp(-3t)
    sol = 9 * sp.exp(-2 * t) - 7 * sp.exp(-3 * t)
    res = verifier.verify_second_order(
        solution=sol,
        variable=t,
        a_coeff=sp.Integer(1),
        b_coeff=sp.Integer(5),
        c_coeff=sp.Integer(6),
        initial_condition=(sp.Integer(0), sp.Integer(2)),
        initial_derivative=(sp.Integer(0), sp.Integer(3)),
    )
    assert res.status == VerificationStatus.VERIFIED
    assert "second_order_ode_residual_and_dual_ic_zero_check" in res.method


def test_ode_verifier_second_order_ic_mismatch():
    verifier = ODEVerifier()
    t = sp.Symbol("t")
    sol = 9 * sp.exp(-2 * t) - 7 * sp.exp(-3 * t)
    # Wrong y(0)
    res = verifier.verify_second_order(
        solution=sol,
        variable=t,
        a_coeff=sp.Integer(1),
        b_coeff=sp.Integer(5),
        c_coeff=sp.Integer(6),
        initial_condition=(sp.Integer(0), sp.Integer(5)),
        initial_derivative=(sp.Integer(0), sp.Integer(3)),
    )
    assert res.status == VerificationStatus.FAILED
    assert "initial_condition_mismatch" in res.method

    # Wrong y'(0)
    res_deriv = verifier.verify_second_order(
        solution=sol,
        variable=t,
        a_coeff=sp.Integer(1),
        b_coeff=sp.Integer(5),
        c_coeff=sp.Integer(6),
        initial_condition=(sp.Integer(0), sp.Integer(2)),
        initial_derivative=(sp.Integer(0), sp.Integer(99)),
    )
    assert res_deriv.status == VerificationStatus.FAILED
    assert "initial_derivative_mismatch" in res_deriv.method


def test_ode_verifier_wronskian_independence():
    verifier = ODEVerifier()
    t = sp.Symbol("t")
    # Independent: cos(t), sin(t)
    w_expr, res = verifier.verify_wronskian(sp.cos(t), sp.sin(t), t)
    assert w_expr == 1
    assert res.status == VerificationStatus.VERIFIED
    assert "wronskian_nonzero_independence_verified" in res.method

    # Arbitrary functions without common ODE context: W == 0 is inconclusive
    w_zero, res_dep = verifier.verify_wronskian(2 * t, 5 * t, t)
    assert w_zero == 0
    assert res_dep.status == VerificationStatus.UNVERIFIED
    assert "wronskian_zero_inconclusive" in res_dep.method

    # Verified solutions to common ODE (y'' = 0): W == 0 implies linear dependence by Abel
    w_ode, res_ode = verifier.verify_wronskian(
        2 * t, 5 * t, t, ode_coeffs=(sp.Integer(1), sp.Integer(0), sp.Integer(0))
    )
    assert w_ode == 0
    assert res_ode.status == VerificationStatus.VERIFIED
    assert "wronskian_zero_ode_solutions_dependent_verified" in res_ode.method


def test_ode_verifier_reduction_of_order():
    verifier = ODEVerifier()
    t = sp.Symbol("t")
    # 2*t^2*y'' + 3*t*y' - y = 0
    # y1 = 1/t, y2 = sqrt(t)
    y1 = 1 / t
    y2 = sp.sqrt(t)
    res = verifier.verify_reduction_of_order(
        y1=y1,
        y2=y2,
        variable=t,
        a_coeff=2 * t**2,
        b_coeff=3 * t,
        c_coeff=sp.Integer(-1),
    )
    assert res.status == VerificationStatus.VERIFIED
    assert "reduction_of_order_full_verification" in res.method


def test_adversarial_sample_point_vanishing_residual_not_verified():
    """An expression whose residual vanishes at previous sample points (0.23, 0.71, 1.45, 2.87)
    must NEVER be promoted to VERIFIED."""
    verifier = ODEVerifier()
    t = sp.Symbol("t")
    # Equation: y' = 0.
    # Candidate whose derivative is R(t) = (t - 0.23)*(t - 0.71)*(t - 1.45)*(t - 2.87)
    s = sp.Symbol("s")
    poly_integrand = (s - sp.Float("0.23")) * (s - sp.Float("0.71")) * (s - sp.Float("1.45")) * (s - sp.Float("2.87"))
    fake_sol = sp.integrate(poly_integrand, (s, 0, t))

    res = verifier.verify_explicit(
        solution=fake_sol,
        variable=t,
        p_expr=sp.Integer(0),
        g_expr=sp.Integer(0),
    )
    # Must NOT be VERIFIED!
    assert res.status != VerificationStatus.VERIFIED
    assert res.status in (VerificationStatus.FAILED, VerificationStatus.UNVERIFIED)


def test_adversarial_wrong_second_order_candidate_not_verified():
    """A wrong candidate for second-order ODE must return FAILED and not receive a green badge."""
    verifier = ODEVerifier()
    t = sp.Symbol("t")
    # ODE: y'' + y = 0
    # Candidate: y = cosh(t) (solves y'' - y = 0, NOT y'' + y = 0)
    res = verifier.verify_second_order(
        solution=sp.cosh(t),
        variable=t,
        a_coeff=sp.Integer(1),
        b_coeff=sp.Integer(0),
        c_coeff=sp.Integer(1),
    )
    assert res.status == VerificationStatus.FAILED


def test_adversarial_ivp_satisfied_ode_wrong_initial_conditions():
    """A candidate satisfying the differential equation but violating initial conditions must FAIL."""
    verifier = ODEVerifier()
    t = sp.Symbol("t")
    # ODE: y'' + 5y' + 6y = 0. Candidate: y = 9*exp(-2t) - 7*exp(-3t) (y(0) = 2, y'(0) = 3)
    sol = 9 * sp.exp(-2 * t) - 7 * sp.exp(-3 * t)

    # Test with wrong y(0) = 10
    res_y = verifier.verify_second_order(
        solution=sol,
        variable=t,
        a_coeff=sp.Integer(1),
        b_coeff=sp.Integer(5),
        c_coeff=sp.Integer(6),
        initial_condition=(sp.Integer(0), sp.Integer(10)),
        initial_derivative=(sp.Integer(0), sp.Integer(3)),
    )
    assert res_y.status == VerificationStatus.FAILED
    assert "initial_condition_mismatch" in res_y.method

    # Test with wrong y'(0) = -5
    res_yp = verifier.verify_second_order(
        solution=sol,
        variable=t,
        a_coeff=sp.Integer(1),
        b_coeff=sp.Integer(5),
        c_coeff=sp.Integer(6),
        initial_condition=(sp.Integer(0), sp.Integer(2)),
        initial_derivative=(sp.Integer(0), sp.Integer(-5)),
    )
    assert res_yp.status == VerificationStatus.FAILED
    assert "initial_derivative_mismatch" in res_yp.method


def test_general_solution_arbitrary_constants_verified():
    """General solutions with arbitrary symbolic constants must be proven identically zero."""
    verifier = ODEVerifier()
    t, C1, C2 = sp.symbols("t C1 C2")
    # y'' + 5y' + 6y = 0 with arbitrary C1, C2
    gen_sol = C1 * sp.exp(-2 * t) + C2 * sp.exp(-3 * t)
    res = verifier.verify_second_order(
        solution=gen_sol,
        variable=t,
        a_coeff=sp.Integer(1),
        b_coeff=sp.Integer(5),
        c_coeff=sp.Integer(6),
        c1_sym=C1,
        c2_sym=C2,
    )
    assert res.status == VerificationStatus.VERIFIED
    assert "second_order_ode_residual_zero_check" in res.method


def test_reduction_of_order_nonhomogeneous_rejected():
    """verify_reduction_of_order must reject a nonhomogeneous equation."""
    verifier = ODEVerifier()
    t = sp.Symbol("t")
    # y'' + y = 1 (forcing_expr = 1)
    res = verifier.verify_reduction_of_order(
        y1=sp.cos(t),
        y2=sp.sin(t),
        variable=t,
        a_coeff=sp.Integer(1),
        b_coeff=sp.Integer(0),
        c_coeff=sp.Integer(1),
        forcing_expr=sp.Integer(1),
    )
    assert res.status == VerificationStatus.FAILED
    assert "nonhomogeneous" in res.method


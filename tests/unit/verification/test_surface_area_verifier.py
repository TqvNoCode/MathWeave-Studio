"""Unit tests for independent surface area verification."""

import sympy as sp
from math_app.domain.models import VerificationStatus
from math_app.verification.calculus.surface_area_verifier import SurfaceAreaVerifier


def test_surface_area_symbolic_verified():
    verifier = SurfaceAreaVerifier()
    u, v = sp.symbols("u v")

    # Flat plane z = 0 over [0, 2] x [0, 3], area = 6
    integrand = sp.Integer(1)
    computed_area = sp.Integer(6)

    result = verifier.verify_surface_area(
        computed_area=computed_area,
        integrand=integrand,
        u_var=u,
        u_min=sp.Integer(0),
        u_max=sp.Integer(2),
        v_var=v,
        v_min=sp.Integer(0),
        v_max=sp.Integer(3),
    )

    assert result.status == VerificationStatus.VERIFIED
    assert result.method == "symbolic_surface_area_integral"


def test_surface_area_detects_wrong_computed_area():
    verifier = SurfaceAreaVerifier()
    u, v = sp.symbols("u v")

    # Deliberately wrong computed area (expected 6, provided 100)
    integrand = sp.Integer(1)
    wrong_area = sp.Integer(100)

    result = verifier.verify_surface_area(
        computed_area=wrong_area,
        integrand=integrand,
        u_var=u,
        u_min=sp.Integer(0),
        u_max=sp.Integer(2),
        v_var=v,
        v_min=sp.Integer(0),
        v_max=sp.Integer(3),
    )

    assert result.status == VerificationStatus.FAILED
    assert "discrepancy" in result.method.lower()


def test_surface_area_gauss_quadrature_verified():
    verifier = SurfaceAreaVerifier()
    u, v = sp.symbols("u v")

    # Non-trivial surface integrand sqrt(1 + 4*u^2 + 4*v^2) for paraboloid
    # For a small region [0, 0.5] x [0, 0.5]
    integrand = sp.sqrt(1 + 4 * u**2 + 4 * v**2)
    # Compute exact analytical integral via sympy
    inner = sp.integrate(integrand, (u, 0, sp.Rational(1, 2)))
    exact_area = sp.integrate(inner, (v, 0, sp.Rational(1, 2)))

    result = verifier.verify_surface_area(
        computed_area=exact_area,
        integrand=integrand,
        u_var=u,
        u_min=sp.Integer(0),
        u_max=sp.Rational(1, 2),
        v_var=v,
        v_min=sp.Integer(0),
        v_max=sp.Rational(1, 2),
    )

    assert result.status == VerificationStatus.VERIFIED

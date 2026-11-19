"""Unit tests for ArcLengthVerifier independent mathematical verification."""

from __future__ import annotations

import sympy as sp

from math_app.domain.models import VerificationStatus
from math_app.verification.calculus.arc_length_verifier import ArcLengthVerifier


def test_verifier_exact_symbolic_curve():
    """Verify exact symbolic verification on y = x on [0, 1] -> sqrt(2)."""
    verifier = ArcLengthVerifier()
    x = sp.Symbol("x")
    integrand = sp.sqrt(1 + 1**2)  # sqrt(2)

    res = verifier.verify_arc_length(
        computed_length=sp.sqrt(2),
        integrand=integrand,
        var=x,
        a=sp.Integer(0),
        b=sp.Integer(1),
    )
    assert res.status == VerificationStatus.VERIFIED
    assert res.method == "symbolic_arc_length_integral"
    assert "dạng đóng" in res.details


def test_verifier_numerical_quadrature_agreement():
    """Verify numerical adaptive quadrature agreement on cos(x) - tan(x) on [0, 1]."""
    verifier = ArcLengthVerifier()
    x = sp.Symbol("x")
    df = sp.diff(sp.cos(x) - sp.tan(x), x)
    integrand = sp.sqrt(1 + df**2)

    res = verifier.verify_arc_length(
        computed_length=sp.Float(2.280484110764684, 15),
        integrand=integrand,
        var=x,
        a=sp.Integer(0),
        b=sp.Integer(1),
    )
    assert res.status == VerificationStatus.VERIFIED
    assert res.method == "numerical_quadrature_arc_length"


def test_verifier_rejects_incorrect_value_1_8354():
    """Verify that an incorrect arc length value (e.g. 1.8354) is rejected as FAILED."""
    verifier = ArcLengthVerifier()
    x = sp.Symbol("x")
    df = sp.diff(sp.cos(x) - sp.tan(x), x)
    integrand = sp.sqrt(1 + df**2)

    res = verifier.verify_arc_length(
        computed_length=sp.Float(1.8354, 10),
        integrand=integrand,
        var=x,
        a=sp.Integer(0),
        b=sp.Integer(1),
    )
    assert res.status == VerificationStatus.FAILED
    assert res.method == "numerical_quadrature_discrepancy"
    assert "sai lệch số học" in res.details


def test_verifier_confirms_divergent_singularity():
    """Verify that divergence at pi/2 in cos(x) - tan(x) on [0, 3] is verified."""
    verifier = ArcLengthVerifier()
    x = sp.Symbol("x")
    df = sp.diff(sp.cos(x) - sp.tan(x), x)
    integrand = sp.sqrt(1 + df**2)

    res = verifier.verify_arc_length(
        computed_length=sp.oo,
        integrand=integrand,
        var=x,
        a=sp.Integer(0),
        b=sp.Integer(3),
        is_divergent=True,
    )
    assert res.status == VerificationStatus.VERIFIED
    assert res.method == "divergence_singularity_analysis"


def test_verifier_rejects_false_divergence_claim():
    """Verify that claiming divergence for a regular curve (y = x on [0, 1]) is rejected as FAILED."""
    verifier = ArcLengthVerifier()
    x = sp.Symbol("x")
    integrand = sp.sqrt(2)

    res = verifier.verify_arc_length(
        computed_length=sp.oo,
        integrand=integrand,
        var=x,
        a=sp.Integer(0),
        b=sp.Integer(1),
        is_divergent=True,
    )
    assert res.status == VerificationStatus.FAILED
    assert res.method == "divergence_refuted"

"""Unit tests for independent DerivativeVerifier."""

import sympy as sp

from math_app.domain.models import VerificationStatus
from math_app.verification.calculus.derivative_verifier import DerivativeVerifier


def test_verifier_confirms_correct_derivative():
    verifier = DerivativeVerifier()
    x = sp.Symbol("x")
    orig = x ** 3
    correct_derived = 3 * (x ** 2)

    result = verifier.verify(orig, correct_derived, x)
    assert result.status == VerificationStatus.VERIFIED
    assert "algebraically equivalent" in result.details


def test_verifier_flags_incorrect_derivative():
    verifier = DerivativeVerifier()
    x = sp.Symbol("x")
    orig = x ** 3
    wrong_derived = 2 * (x ** 2)  # Wrong derivative

    result = verifier.verify(orig, wrong_derived, x)
    assert result.status == VerificationStatus.FAILED
    assert "Discrepancy detected" in result.details


def test_verifier_complex_trig_product():
    verifier = DerivativeVerifier()
    x = sp.Symbol("x")
    orig = (x ** 2) * sp.sin(x)
    derived = 2 * x * sp.sin(x) + (x ** 2) * sp.cos(x)

    result = verifier.verify(orig, derived, x)
    assert result.status == VerificationStatus.VERIFIED

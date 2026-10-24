"""Unit tests for independent integral verification."""

import sympy as sp
from math_app.domain.models import VerificationStatus
from math_app.verification.calculus.integral_verifier import IntegralVerifier


def test_indefinite_ftc_symbolic_verified():
    verifier = IntegralVerifier()
    x = sp.Symbol("x")

    # Correct antiderivative of x^2 is x^3 / 3
    integrand = x ** 2
    antiderivative = (x ** 3) / 3
    result = verifier.verify_indefinite(integrand, antiderivative, x)

    assert result.status == VerificationStatus.VERIFIED
    assert result.method == "fundamental_theorem_of_calculus"


def test_indefinite_ftc_detects_wrong_antiderivative():
    verifier = IntegralVerifier()
    x = sp.Symbol("x")

    # Deliberately incorrect antiderivative
    integrand = x ** 2
    wrong_antiderivative = x ** 2
    result = verifier.verify_indefinite(integrand, wrong_antiderivative, x)

    assert result.status == VerificationStatus.FAILED
    assert result.method == "numerical_ftc_spot_check"


def test_indefinite_ftc_numerical_spot_check_verified():
    verifier = IntegralVerifier()
    x = sp.Symbol("x")

    # Integrand whose difference with derived might not immediately simplify to 0 without expansion
    integrand = sp.sin(x) * sp.cos(x)
    antiderivative = (sp.sin(x) ** 2) / 2
    result = verifier.verify_indefinite(integrand, antiderivative, x)

    assert result.status == VerificationStatus.VERIFIED


def test_definite_symbolic_verified():
    verifier = IntegralVerifier()
    x = sp.Symbol("x")

    # Definite integral of x from 0 to 2 is 2
    integrand = x
    computed = sp.Integer(2)
    result = verifier.verify_definite(integrand, computed, x, sp.Integer(0), sp.Integer(2))

    assert result.status == VerificationStatus.VERIFIED
    assert result.method == "symbolic_definite_integration_check"


def test_definite_detects_wrong_computed_result():
    verifier = IntegralVerifier()
    x = sp.Symbol("x")

    # Deliberately incorrect definite value (expected 2, provided 99)
    integrand = x
    wrong_computed = sp.Integer(99)
    result = verifier.verify_definite(integrand, wrong_computed, x, sp.Integer(0), sp.Integer(2))

    assert result.status == VerificationStatus.FAILED
    assert "discrepancy" in result.method.lower()


def test_definite_numerical_quadrature_verified():
    verifier = IntegralVerifier()
    x = sp.Symbol("x")

    # Known analytical value: integral of exp(-x) from 0 to 1 = 1 - exp(-1)
    integrand = sp.exp(-x)
    computed = 1 - sp.exp(-1)
    result = verifier.verify_definite(integrand, computed, x, sp.Integer(0), sp.Integer(1))

    assert result.status == VerificationStatus.VERIFIED

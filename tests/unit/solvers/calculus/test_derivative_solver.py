"""Unit tests for DerivativeSolver end-to-end derivation and boundary cases."""

import sympy as sp

from math_app.application.dtos import ProblemRequest, VerificationResult
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.differentiation.solver import DerivativeSolver


def test_derivative_solver_can_solve():
    solver = DerivativeSolver()
    req_valid = ProblemRequest("x^2", ProblemType.DERIVATIVE)
    req_invalid = ProblemRequest("x^2", ProblemType.INTEGRAL)

    assert solver.can_solve(req_valid) is True
    assert solver.can_solve(req_invalid) is False


def test_derivative_solver_polynomial_end_to_end():
    solver = DerivativeSolver()
    request = ProblemRequest("x^3 - 4*x + 7", ProblemType.DERIVATIVE, target_variable="x")
    response = solver.solve(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED
    # Compare mathematically with independent SymPy
    res_sym = sp.sympify(response.final_result)
    expected_sym = sp.sympify("3*x**2 - 4")
    assert sp.simplify(res_sym - expected_sym) == 0

    assert len(response.steps) >= 1
    assert response.final_latex != ""


def test_derivative_solver_product_with_trig():
    solver = DerivativeSolver()
    request = ProblemRequest("x^2 * sin(x)", ProblemType.DERIVATIVE, target_variable="x")
    response = solver.solve(request)

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED

    res_sym = sp.sympify(response.final_result)
    x = sp.Symbol("x")
    expected_sym = 2 * x * sp.sin(x) + (x ** 2) * sp.cos(x)
    assert sp.simplify(res_sym - expected_sym) == 0

    # Ensure steps recorded product rule
    step_names = [s.rule_name for s in response.steps]
    assert "Product Rule" in step_names


def test_derivative_solver_detects_domain_restrictions():
    solver = DerivativeSolver()
    request = ProblemRequest("1 / x", ProblemType.DERIVATIVE, target_variable="x")
    response = solver.solve(request)

    assert len(response.domain_restrictions) >= 1
    assert any("x" in r for r in response.domain_restrictions)


def test_derivative_solver_handles_verification_discrepancy():
    class BuggyVerifier:
        def verify(self, orig, derived, var):
            return VerificationResult(
                status=VerificationStatus.FAILED,
                method="mock_failed_audit",
                details="Artificial discrepancy injected.",
            )

    solver = DerivativeSolver(verifier=BuggyVerifier())
    request = ProblemRequest("x^2", ProblemType.DERIVATIVE)
    response = solver.solve(request)

    assert response.status == SolutionStatus.DISCREPANCY_DETECTED
    assert response.verification.status == VerificationStatus.FAILED
    assert "Artificial discrepancy" in response.warnings[0]

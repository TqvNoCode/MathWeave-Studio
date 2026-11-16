"""Comprehensive integration tests for Second-Order ODE pipeline via SolveProblemUseCase."""

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.main import build_application


@pytest.fixture
def use_case():
    return build_application()


def test_pipeline_constant_coeff_real_roots(use_case):
    """Pipeline: y'' + 5*y' + 6*y = 0."""
    req = ProblemRequest(
        raw_input="y'' + 5*y' + 6*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = use_case.execute(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.steps) >= 4
    assert res.final_latex.startswith("y(t) = ")


def test_pipeline_mandatory_ivp(use_case):
    """Pipeline: y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = 3 => y(t) = 9e^(-2t) - 7e^(-3t)."""
    req = ProblemRequest(
        raw_input="y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = 3",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = use_case.execute(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    expected = 9 * sp.exp(-2 * t) - 7 * sp.exp(-3 * t)
    sol_str = res.final_result.split("=", 1)[1].strip()
    assert sp.simplify(sp.sympify(sol_str) - expected) == 0


def test_pipeline_reduction_of_order_all_reference_examples(use_case):
    """Pipeline: Test all 4 reference examples for Reduction of Order."""
    # Example 1: Euler-Cauchy
    req1 = ProblemRequest(
        raw_input="2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    res1 = use_case.execute(req1)
    assert res1.status == SolutionStatus.SUCCESS
    assert res1.verification.status == VerificationStatus.VERIFIED
    assert "1/t" in res1.final_result
    assert "sqrt(t)" in res1.final_result or "t**(1/2)" in res1.final_result

    # Example 2: Repeated root
    req2 = ProblemRequest(
        raw_input="y'' - 2*y' + y = 0, y1 = exp(t)",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    res2 = use_case.execute(req2)
    assert res2.status == SolutionStatus.SUCCESS
    assert res2.verification.status == VerificationStatus.VERIFIED
    assert "exp(t)" in res2.final_result

    # Example 3: Trigonometric
    req3 = ProblemRequest(
        raw_input="y'' + y = 0, y1 = cos(t)",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    res3 = use_case.execute(req3)
    assert res3.status == SolutionStatus.SUCCESS
    assert res3.verification.status == VerificationStatus.VERIFIED
    assert "cos(t)" in res3.final_result
    assert "sin(t)" in res3.final_result

    # Example 4: Variable coeff
    req4 = ProblemRequest(
        raw_input="y'' - (2/t^2)*y = 0, y1 = t^2",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
    )
    res4 = use_case.execute(req4)
    assert res4.status == SolutionStatus.SUCCESS
    assert res4.verification.status == VerificationStatus.VERIFIED
    assert "t**2" in res4.final_result
    assert "1/t" in res4.final_result or "3*t" in res4.final_result


def test_pipeline_wronskian(use_case):
    """Pipeline: Wronskian computation."""
    req = ProblemRequest(
        raw_input="cos(t), sin(t)",
        problem_type=ProblemType.WRONSKIAN,
        target_variable="t",
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "= 1" in res.final_result


def test_pipeline_security_rejection(use_case):
    """Pipeline: Hostile or malicious inputs rejected safely."""
    hostile_inputs = [
        "__import__('os').system('ls')",
        "eval('1+1')",
        "exec('x = 1')",
        "open('/etc/passwd').read()",
    ]
    for inp in hostile_inputs:
        req = ProblemRequest(
            raw_input=inp,
            problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
            target_variable="t",
        )
        res = use_case.execute(req)
        assert res.status in (SolutionStatus.INVALID_INPUT, SolutionStatus.CANNOT_SOLVE)
        assert res.verification.status in (VerificationStatus.NOT_APPLICABLE, VerificationStatus.FAILED)

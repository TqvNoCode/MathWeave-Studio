"""Unit tests for domain models and serializable DTOs."""

from dataclasses import is_dataclass
import pytest

from math_app.application.dtos import (
    SolutionResponse,
    SolutionStep,
    VerificationResult,
)
from math_app.domain.models import SolutionStatus, VerificationStatus
from math_app.domain.step_content import ExpressionStepContent


def test_step_content_serialization_purity():
    """ExpressionStepContent must only hold serializable strings, not SymPy objects."""
    content = ExpressionStepContent(
        expression_before="x**2",
        expression_after="2*x",
        latex_before="x^{2}",
        latex_after="2 x",
    )
    assert isinstance(content.expression_before, str)
    assert isinstance(content.expression_after, str)
    assert isinstance(content.latex_before, str)
    assert isinstance(content.latex_after, str)

    # Must be frozen
    with pytest.raises(Exception):
        content.expression_before = "modified"  # type: ignore


def test_solution_step_immutability_and_substeps():
    content = ExpressionStepContent(
        expression_before="x",
        expression_after="1",
        latex_before="x",
        latex_after="1",
    )
    step = SolutionStep(
        step_number=1,
        rule_name="Power Rule",
        description="d/dx(x) = 1",
        content=content,
        substeps=(),
    )
    assert step.step_number == 1
    assert step.rule_name == "Power Rule"
    assert step.substeps == ()


def test_solution_response_contains_no_sympy_objects():
    verification = VerificationResult(
        status=VerificationStatus.VERIFIED,
        method="symbolic_difference",
        details="Verified successfully.",
    )
    content = ExpressionStepContent("x", "1", "x", "1")
    step = SolutionStep(1, "Identity", "Identity rule", content)

    response = SolutionResponse(
        status=SolutionStatus.SUCCESS,
        verification=verification,
        raw_input="x",
        canonical_input="x",
        final_result="1",
        final_latex="1",
        steps=(step,),
        domain_restrictions=(),
        warnings=(),
        execution_time_ms=1.5,
    )

    assert response.status == SolutionStatus.SUCCESS
    assert response.verification.status == VerificationStatus.VERIFIED
    assert isinstance(response.final_result, str)
    assert isinstance(response.final_latex, str)
    assert is_dataclass(response)

"""Structured, serializable models for mathematical step content."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpressionStepContent:
    """Serializable payload for expression-based mathematical steps.

    Contains both the canonical string representation and pre-rendered LaTeX
    for UI display, preventing SymPy objects from leaking across boundaries.
    """

    expression_before: str
    expression_after: str
    latex_before: str
    latex_after: str

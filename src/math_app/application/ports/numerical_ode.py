"""Application ports for numerical ODE solvers, verifiers, error analyzers, and comparisons."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from math_app.domain.numerical_ode import (
    AnalyticalComparisonResult,
    NumericalErrorAnalysis,
    NumericalODEMethod,
    NumericalODERequest,
    NumericalODEResponse,
    NumericalVerificationReport,
)


@runtime_checkable
class NumericalODESolver(Protocol):
    """Protocol satisfied by numerical ODE initial-value problem solvers."""

    method: NumericalODEMethod

    def solve(self, request: NumericalODERequest) -> NumericalODEResponse:
        """Compute numerical approximation for the requested initial-value problem."""
        ...


@runtime_checkable
class NumericalODEVerifier(Protocol):
    """Protocol satisfied by independent numerical ODE verifiers."""

    def verify(
        self,
        request: NumericalODERequest,
        response: NumericalODEResponse,
    ) -> NumericalVerificationReport:
        """Independently verify grid, step sizes, recurrence, error analysis, and invariants."""
        ...


@runtime_checkable
class AnalyticalComparisonProvider(Protocol):
    """Protocol providing optional exact analytical comparison for numerical solutions."""

    def compare(
        self,
        request: NumericalODERequest,
        response: NumericalODEResponse,
    ) -> AnalyticalComparisonResult:
        """Attempt exact analytical IVP comparison without altering analytical solvers."""
        ...


@runtime_checkable
class NumericalErrorAnalyzer(Protocol):
    """Protocol providing local one-step defect, global error, and step-halving analysis."""

    def analyze(
        self,
        request: NumericalODERequest,
        response: NumericalODEResponse,
    ) -> NumericalErrorAnalysis:
        """Compute rigorous local/global error metrics and optional step-halving estimates."""
        ...

"""Port defining the mathematical solver protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from math_app.application.dtos import ProblemRequest, SolutionResponse


@runtime_checkable
class Solver(Protocol):
    """Protocol satisfied by all mathematical domain solvers."""

    def can_solve(self, request: ProblemRequest) -> bool:
        """Return True if this solver can process the given problem request."""
        ...

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        """Derive the step-by-step solution and return the response DTO."""
        ...

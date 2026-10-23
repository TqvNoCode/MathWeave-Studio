"""Port defining the solver registry protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from math_app.application.ports.solver import Solver
from math_app.domain.models import ProblemType


@runtime_checkable
class SolverRegistry(Protocol):
    """Protocol for managing and dispatching solvers by problem category."""

    def register(self, problem_type: ProblemType, solver: Solver) -> None:
        """Register a solver for a specific problem type."""
        ...

    def get(self, problem_type: ProblemType) -> Solver | None:
        """Retrieve the registered solver for the problem type, if available."""
        ...

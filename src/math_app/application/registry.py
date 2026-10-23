"""Concrete implementation of the SolverRegistry."""

from __future__ import annotations

from math_app.application.ports.solver import Solver
from math_app.application.ports.solver_registry import SolverRegistry
from math_app.domain.models import ProblemType


class DefaultSolverRegistry(SolverRegistry):
    """In-memory dictionary-backed solver registry."""

    def __init__(self) -> None:
        self._solvers: dict[ProblemType, Solver] = {}

    def register(self, problem_type: ProblemType, solver: Solver) -> None:
        self._solvers[problem_type] = solver

    def get(self, problem_type: ProblemType) -> Solver | None:
        return self._solvers.get(problem_type)

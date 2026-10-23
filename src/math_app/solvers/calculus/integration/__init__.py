"""Calculus integration package."""

from math_app.solvers.calculus.integration.solver import IntegralSolver
from math_app.solvers.calculus.integration.line_integral_solver import LineIntegralSolver
from math_app.solvers.calculus.integration.surface_integral_solver import SurfaceIntegralSolver
from math_app.solvers.calculus.integration.triple_integral_solver import TripleIntegralSolver

__all__ = [
    "IntegralSolver",
    "LineIntegralSolver",
    "SurfaceIntegralSolver",
    "TripleIntegralSolver",
]

"""Numerical ODE solvers package."""

from math_app.solvers.numerical.error_analysis import ExplicitEulerErrorAnalyzer
from math_app.solvers.numerical.euler_engine import (
    EulerStepRecord,
    FirstOrderEulerAdapter,
    SecondOrderEulerAdapter,
    integrate_explicit_euler,
)
from math_app.solvers.numerical.explicit_euler_solver import ExplicitEulerSolver
from math_app.solvers.numerical.time_grid import TimeGrid, build_time_grid, subdivide_time_grid_half

__all__ = [
    "EulerStepRecord",
    "ExplicitEulerErrorAnalyzer",
    "ExplicitEulerSolver",
    "FirstOrderEulerAdapter",
    "SecondOrderEulerAdapter",
    "TimeGrid",
    "build_time_grid",
    "integrate_explicit_euler",
    "subdivide_time_grid_half",
]

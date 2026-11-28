"""Domain models for numerical Ordinary Differential Equation (ODE) solvers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NumericalODEMethod(str, Enum):
    """Supported numerical integration methods for ODE initial-value problems."""

    EXPLICIT_EULER = "explicit_euler"

    @property
    def display_label(self) -> str:
        """Return user-facing Vietnamese/English method label."""
        labels = {
            NumericalODEMethod.EXPLICIT_EULER: "Phương pháp Euler tiến (Explicit Euler)",
        }
        return labels[self]


class NumericalODEOrder(int, Enum):
    """Supported ODE orders for numerical integration."""

    FIRST_ORDER = 1
    SECOND_ORDER = 2


class NumericalODEStatus(str, Enum):
    """Outcome status for a numerical ODE computation."""

    SUCCESS = "success"
    INVALID_INPUT = "invalid_input"
    SINGULARITY_ERROR = "singularity_error"
    NUMERICAL_ERROR = "numerical_error"
    ITERATION_LIMIT_EXCEEDED = "iteration_limit_exceeded"
    ERROR = "error"


@dataclass(frozen=True)
class NumericalIterationRow:
    """Single row in the numerical ODE iteration table."""

    step_index: int
    t: float
    y: float
    slope_y: float
    step_used: float | None = None
    v: float | None = None
    slope_v: float | None = None


@dataclass(frozen=True)
class AnalyticalComparisonPoint:
    """Pointwise comparison between numerical approximation and exact analytical solution."""

    step_index: int
    t: float
    y_numerical: float
    y_exact: float
    abs_error: float


@dataclass(frozen=True)
class AnalyticalComparisonResult:
    """Result of comparing numerical approximation against an analytical IVP solution."""

    available: bool
    exact_expression_str: str = ""
    exact_latex: str = ""
    points: tuple[AnalyticalComparisonPoint, ...] = ()
    max_abs_error: float | None = None
    final_abs_error: float | None = None
    notes: str = ""


@dataclass(frozen=True)
class NumericalVerificationCheck:
    """Individual invariant check executed by the numerical verifier."""

    name: str
    passed: bool
    details: str


@dataclass(frozen=True)
class NumericalVerificationReport:
    """Independent verification report for a numerical ODE approximation."""

    is_verified: bool
    method: str
    summary: str
    checks: tuple[NumericalVerificationCheck, ...] = ()
    checked_indices: tuple[int, ...] = ()
    max_recurrence_residual: float = 0.0


@dataclass(frozen=True)
class NumericalODERequest:
    """Immutable input request for numerical ODE integration."""

    raw_equation: str
    order: NumericalODEOrder
    independent_var: str = "t"
    dependent_var: str = "y"
    t0: str = "0"
    y0: str = "1"
    t_end: str = "1"
    step_size: str = "0.1"
    v0: str | None = None
    method: NumericalODEMethod = NumericalODEMethod.EXPLICIT_EULER
    max_steps: int = 10_000
    compute_analytical_comparison: bool = True


@dataclass(frozen=True)
class NumericalODEResponse:
    """Immutable structured result returned by numerical ODE use cases."""

    status: NumericalODEStatus
    method: NumericalODEMethod
    order: NumericalODEOrder
    raw_equation: str
    independent_var: str = "t"
    dependent_var: str = "y"
    canonical_rhs_str: str = ""
    canonical_rhs_latex: str = ""
    equation_latex: str = ""
    is_euler_cauchy_transformed: bool = False
    euler_cauchy_original_latex: str = ""
    t0: float = 0.0
    y0: float = 0.0
    v0: float | None = None
    t_end: float = 0.0
    step_size: float = 0.0
    direction: int = 1
    total_steps: int = 0
    has_shortened_final_step: bool = False
    final_step_size: float = 0.0
    rows: tuple[NumericalIterationRow, ...] = ()
    final_t: float | None = None
    final_y: float | None = None
    final_v: float | None = None
    error_message: str = ""
    failing_step: int | None = None
    warnings: tuple[str, ...] = ()
    domain_restrictions: tuple[str, ...] = ()
    verification: NumericalVerificationReport | None = None
    analytical_comparison: AnalyticalComparisonResult | None = None
    execution_time_ms: float = 0.0

"""Core domain models for MathWeave Studio."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProblemType(str, Enum):
    """Supported mathematical problem categories."""

    # Calculus
    DERIVATIVE = "derivative"
    HIGHER_ORDER_DERIVATIVE = "higher_order_derivative"
    PARTIAL_DERIVATIVE = "partial_derivative"
    INTEGRAL = "integral"
    INDEFINITE_INTEGRAL = "indefinite_integral"
    DEFINITE_INTEGRAL = "definite_integral"
    LIMIT = "limit"
    SOLVE_EQUATION = "solve_equation"

    # Multivariable & Advanced Definite Integration (Phase 3)
    LINE_INTEGRAL = "line_integral"
    SURFACE_INTEGRAL = "surface_integral"
    TRIPLE_INTEGRAL = "triple_integral"

    # Parametric Geometry & Surfaces (Phase 4)
    PARAMETRIC_CURVE = "parametric_curve"
    ARC_LENGTH = "arc_length"
    SURFACE_AREA = "surface_area"
    SURFACE_OF_REVOLUTION = "surface_of_revolution"

    # Vector Calculus Theorems (Phase 5)
    GREENS_THEOREM = "greens_theorem"
    STOKES_THEOREM = "stokes_theorem"
    DIVERGENCE_THEOREM = "divergence_theorem"

    # Linear Algebra
    MATRIX_ADD_SUB = "matrix_add_sub"
    MATRIX_MULTIPLY = "matrix_multiply"
    MATRIX_TRANSPOSE = "matrix_transpose"
    MATRIX_DETERMINANT = "matrix_determinant"
    MATRIX_INVERSE = "matrix_inverse"
    MATRIX_RANK = "matrix_rank"
    MATRIX_REF = "matrix_ref"
    MATRIX_RREF = "matrix_rref"
    MATRIX_SOLVE_SYSTEM = "matrix_solve_system"

    @property
    def is_matrix(self) -> bool:
        """Return True if this problem type belongs to linear algebra / matrix operations."""
        return self in _MATRIX_PROBLEM_TYPES

    @property
    def is_calculus(self) -> bool:
        """Return True if this problem type belongs to calculus operations."""
        return not self.is_matrix


_MATRIX_PROBLEM_TYPES: frozenset[ProblemType] = frozenset({
    ProblemType.MATRIX_ADD_SUB,
    ProblemType.MATRIX_MULTIPLY,
    ProblemType.MATRIX_TRANSPOSE,
    ProblemType.MATRIX_DETERMINANT,
    ProblemType.MATRIX_INVERSE,
    ProblemType.MATRIX_RANK,
    ProblemType.MATRIX_REF,
    ProblemType.MATRIX_RREF,
    ProblemType.MATRIX_SOLVE_SYSTEM,
})


class SolutionStatus(str, Enum):
    """Overall outcome for a problem resolution attempt."""

    SUCCESS = "success"
    PARTIAL = "partial"
    CANNOT_SOLVE = "cannot_solve"
    INVALID_INPUT = "invalid_input"
    TIMEOUT = "timeout"
    DISCREPANCY_DETECTED = "discrepancy"
    ERROR = "error"
    UNVERIFIED = "unverified"


class VerificationStatus(str, Enum):
    """Confidence status produced by the mathematical verification procedure."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class DomainAssumption:
    """Explicit domain condition or restriction (e.g. variable assumption)."""

    variable: str
    condition: str


@dataclass(frozen=True)
class DomainRestriction:
    """Potential restriction identified during mathematical derivation."""

    expression: str
    restriction_type: str  # e.g., "non_zero_denominator", "positive_log_argument"
    description: str

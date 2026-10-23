"""Domain exceptions for MathWeave Studio."""


class MathWeaveStudioError(Exception):
    """Base exception for all MathWeave Studio domain errors."""


# Backward compatibility alias
MathStudioError = MathWeaveStudioError


class InvalidInputError(MathWeaveStudioError):
    """Raised when mathematical input is malformed, ambiguous, or violates grammar."""


class UnsupportedProblemError(MathWeaveStudioError):
    """Raised when a mathematical problem type or operation cannot be solved."""


class ComputationTimeoutError(MathWeaveStudioError):
    """Raised when symbolic computation exceeds allowable time budget."""

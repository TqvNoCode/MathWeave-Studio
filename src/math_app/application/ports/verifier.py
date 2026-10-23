"""Port defining mathematical verification protocols."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from math_app.application.dtos import VerificationResult


@runtime_checkable
class Verifier(Protocol):
    """Protocol satisfied by mathematical verification engines."""

    def verify(self, original: Any, derived: Any, variable: Any) -> VerificationResult:
        """Verify mathematical equivalence or preservation of invariants."""
        ...

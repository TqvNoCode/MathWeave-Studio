"""Base protocol for differentiation transformation rules."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
import sympy as sp


@runtime_checkable
class DifferentiationRule(Protocol):
    """Protocol satisfied by individual differentiation transformation rules."""

    def can_apply(self, expr: sp.Expr, var: sp.Symbol) -> bool:
        """Return True if this rule applies to the given expression."""
        ...

    def apply(
        self,
        expr: sp.Expr,
        var: sp.Symbol,
        engine: Any,
        builder: Any,
    ) -> sp.Expr:
        """Apply the differentiation rule, record steps in builder, and return derived expr."""
        ...

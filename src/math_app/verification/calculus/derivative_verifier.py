"""Independent mathematical verification for differentiation solutions."""

from __future__ import annotations

import math
import sympy as sp

from math_app.application.dtos import VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class DerivativeVerifier(Verifier):
    """Verifies a derived derivative against an independent SymPy reference."""

    # Default probe points avoiding 0, integers, and negative numbers where logs/roots might fail
    SAMPLE_PROBE_POINTS = (0.37, 1.13, 2.71, 3.49)

    def verify(self, original: sp.Expr, derived: sp.Expr, variable: sp.Symbol, order: int = 1) -> VerificationResult:
        try:
            reference = sp.diff(original, variable, order)
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="reference_differentiation_failed",
                details=f"Could not compute reference derivative: {exc}",
            )

        # 1. Primary test: Symbolic difference simplification
        try:
            difference = sp.simplify(derived - reference)
            if difference == 0:
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="symbolic_difference_zero_check",
                    details="Derived expression is algebraically equivalent to independent reference derivative.",
                )
        except Exception:
            pass  # Fall through to numerical spot-checks if simplification times out or raises

        # 2. Secondary test: Numerical spot-checks across domain probe points
        discrepancies: list[float] = []
        matches: int = 0

        for pt in self.SAMPLE_PROBE_POINTS:
            try:
                val_derived = complex(derived.subs(variable, pt).evalf())
                val_ref = complex(reference.subs(variable, pt).evalf())

                if math.isnan(val_derived.real) or math.isnan(val_ref.real):
                    continue

                diff = abs(val_derived - val_ref)
                if diff > 1e-6:
                    discrepancies.append(diff)
                else:
                    matches += 1
            except Exception:
                continue

        if discrepancies:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                method="numerical_spot_check",
                details=(
                    f"Discrepancy detected at probe points (max error: {max(discrepancies):.6e}). "
                    "Derived solution does not match reference."
                ),
            )

        if matches >= 2:
            # Numerically matches at multiple points even if symbolic simplification was inconclusive
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="multi_point_numerical_confirmation",
                details="Numerical evaluation at multiple test points matched reference derivative within tolerance.",
            )

        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="inconclusive",
            details="Mathematical verification was inconclusive. Universal equivalence could not be established.",
        )

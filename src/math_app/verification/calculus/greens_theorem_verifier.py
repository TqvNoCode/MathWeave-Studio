"""Independent mathematical verification for Green's Theorem."""

from __future__ import annotations

import sympy as sp

from math_app.application.dtos import VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class GreensTheoremVerifier(Verifier):
    """Verifies Green's Theorem by independently checking line integral == double integral."""

    def verify_greens_theorem(
        self,
        line_integral_val: sp.Expr,
        double_integral_val: sp.Expr,
    ) -> VerificationResult:
        """Verify that line integral along closed boundary matches double integral over region."""
        try:
            diff = sp.simplify(line_integral_val - double_integral_val)
            if diff == 0:
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="greens_theorem_lhs_rhs_identity",
                    details="Định lý Green được kiểm chứng: Tích phân đường trên biên đóng bằng chính xác tích phân bội hai trên miền.",
                )
        except Exception:
            pass

        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="greens_theorem_check",
            details="Không thể xác nhận sự đồng nhất giữa hai vế của định lý Green.",
        )

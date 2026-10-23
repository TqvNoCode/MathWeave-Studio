"""Independent mathematical verification for Stokes' Theorem."""

from __future__ import annotations

import sympy as sp

from math_app.application.dtos import VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class StokesTheoremVerifier(Verifier):
    """Verifies Stokes' Theorem by checking boundary line integral == surface curl integral."""

    def verify_stokes_theorem(
        self,
        line_integral_val: sp.Expr,
        surface_integral_val: sp.Expr,
    ) -> VerificationResult:
        """Verify boundary circulation matches surface flux of curl."""
        try:
            diff = sp.simplify(line_integral_val - surface_integral_val)
            if diff == 0:
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="stokes_theorem_lhs_rhs_identity",
                    details="Định lý Stokes được kiểm chứng: Tích phân lưu thông dọc biên ∂S bằng chính xác thông lượng của curl qua mặt S.",
                )
        except Exception:
            pass

        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="stokes_theorem_check",
            details="Không thể xác nhận sự đồng nhất giữa hai vế của định lý Stokes.",
        )

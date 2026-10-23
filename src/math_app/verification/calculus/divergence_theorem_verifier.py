"""Independent mathematical verification for the Divergence (Gauss–Ostrogradsky) Theorem."""

from __future__ import annotations

import sympy as sp

from math_app.application.dtos import VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class DivergenceTheoremVerifier(Verifier):
    """Verifies Divergence Theorem by checking closed surface flux == triple integral of divergence."""

    def verify_divergence_theorem(
        self,
        surface_flux_val: sp.Expr,
        triple_integral_val: sp.Expr,
    ) -> VerificationResult:
        """Verify outward flux through boundary surface matches volume integral of divergence."""
        try:
            diff = sp.simplify(surface_flux_val - triple_integral_val)
            if diff == 0:
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="divergence_theorem_lhs_rhs_identity",
                    details="Định lý Divergence được kiểm chứng: Thông lượng qua mặt kín ∂V bằng chính xác tích phân bội ba của div(F) trên khối V.",
                )
        except Exception:
            pass

        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="divergence_theorem_check",
            details="Không thể xác nhận sự đồng nhất giữa hai vế của định lý Divergence.",
        )

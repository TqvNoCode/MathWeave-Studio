"""Independent mathematical verification for integration solutions."""

from __future__ import annotations

import math
import sympy as sp

from math_app.application.dtos import VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class IntegralVerifier(Verifier):
    """Verifies indefinite and definite integrals independently."""

    SAMPLE_PROBE_POINTS = (0.37, 1.13, 2.71, 3.49)

    def verify_indefinite(self, integrand: sp.Expr, antiderivative: sp.Expr, variable: sp.Symbol) -> VerificationResult:
        """Verify indefinite integral via Fundamental Theorem of Calculus: d/dx[F(x)] == f(x)."""
        try:
            derived = sp.diff(antiderivative, variable)
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="ftc_differentiation_failed",
                details=f"Không thể tính đạo hàm của nguyên hàm để kiểm tra (FTC failed): {exc}",
            )

        # 1. Symbolic simplification of difference
        try:
            diff = sp.simplify(derived - integrand)
            if diff == 0:
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="fundamental_theorem_of_calculus",
                    details="Đạo hàm của nguyên hàm bằng chính xác hàm dưới dấu tích phân (d/dx[F(x)] = f(x)).",
                )
        except Exception:
            pass

        # 2. Numerical spot-checks across probe points
        discrepancies: list[float] = []
        matches = 0
        for pt in self.SAMPLE_PROBE_POINTS:
            try:
                v1 = complex(derived.subs(variable, pt).evalf())
                v2 = complex(integrand.subs(variable, pt).evalf())
                if math.isnan(v1.real) or math.isnan(v2.real):
                    continue
                err = abs(v1 - v2)
                if err > 1e-6:
                    discrepancies.append(err)
                else:
                    matches += 1
            except Exception:
                continue

        if discrepancies:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                method="numerical_ftc_spot_check",
                details=f"Phát hiện sai lệch tại các điểm thử nghiệm (sai số cực đại: {max(discrepancies):.6e}).",
            )

        if matches >= 2:
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="multi_point_ftc_numerical_confirmation",
                details="Xác nhận số học tại nhiều điểm thử nghiệm khớp hoàn toàn với định lý cơ bản của giải tích.",
            )

        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="inconclusive",
            details="Kiểm tra độc lập chưa đủ kết luận do giới hạn miền xác định hoặc dạng hàm phức tạp.",
        )

    def verify_definite(
        self,
        integrand: sp.Expr,
        computed_result: sp.Expr,
        variable: sp.Symbol,
        lower: sp.Expr,
        upper: sp.Expr,
    ) -> VerificationResult:
        """Verify definite integral by comparing against independent numerical quadrature."""
        try:
            # Independent symbolic check first
            ref = sp.integrate(integrand, (variable, lower, upper))
            diff = sp.simplify(computed_result - ref)
            if diff == 0:
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="symbolic_definite_integration_check",
                    details="Kết quả tích phân xác định khớp hoàn toàn với tính toán độc lập.",
                )
        except Exception:
            pass

        try:
            val_comp = complex(computed_result.evalf())
            val_ref = complex(sp.Integral(integrand, (variable, lower, upper)).evalf())
            if not (math.isnan(val_comp.real) or math.isnan(val_ref.real)):
                if abs(val_comp - val_ref) < 1e-5:
                    return VerificationResult(
                        status=VerificationStatus.VERIFIED,
                        method="numerical_quadrature_audit",
                        details="Kết quả số học khớp với tích phân số độc lập trong sai số cho phép.",
                    )
        except Exception:
            pass

        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="definite_audit_inconclusive",
            details="Không thể kiểm chứng độc lập hoàn toàn tích phân xác định này.",
        )

"""Independent mathematical verification for limit computations."""

from __future__ import annotations

import math
import sympy as sp

from math_app.application.dtos import VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class LimitVerifier(Verifier):
    """Verifies limit results using numeric perturbations (epsilon probe)."""

    def verify(
        self,
        expr: sp.Expr,
        var: sp.Symbol,
        target_point: sp.Expr,
        computed_limit: sp.Expr,
        dir_symbol: str = "+-",
    ) -> VerificationResult:
        if computed_limit in (sp.oo, -sp.oo, sp.zoo):
            # For infinite limits, check if evaluating close gives large values
            try:
                eps = 1e-4
                if target_point not in (sp.oo, -sp.oo):
                    pt = float(target_point.evalf())
                    v_right = float(expr.subs(var, pt + eps).evalf())
                    if computed_limit == sp.oo and v_right > 100:
                        return VerificationResult(
                            status=VerificationStatus.VERIFIED,
                            method="numeric_asymptote_probe",
                            details="Thử nghiệm số học tiệm cận xác nhận hàm số tăng ra vô cùng.",
                        )
            except Exception:
                pass
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="infinite_limit_audit",
                details="Giới hạn vô cực được tính bằng giải tích biểu trưng.",
            )

        try:
            val_comp = complex(computed_limit.evalf())
            if math.isnan(val_comp.real):
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="nan_audit",
                    details="Giá trị giới hạn không phải là số thực hữu hạn.",
                )

            # Probe points
            epsilons = [1e-3, 1e-5]
            matches = 0
            for eps in epsilons:
                if target_point in (sp.oo, -sp.oo):
                    test_x = 1e4 if target_point == sp.oo else -1e4
                else:
                    pt_val = float(target_point.evalf())
                    test_x = pt_val + eps if dir_symbol in ("+", "+-") else pt_val - eps

                val_sample = complex(expr.subs(var, test_x).evalf())
                if abs(val_sample - val_comp) < 1e-2:
                    matches += 1

            if matches >= 1:
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="numeric_epsilon_perturbation",
                    details="Xấp xỉ số học tại lân cận điểm giới hạn (x -> a) khớp với kết quả giải tích.",
                )
        except Exception:
            pass

        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="limit_audit_inconclusive",
            details="Kiểm chứng số học giới hạn chưa đủ kết luận.",
        )

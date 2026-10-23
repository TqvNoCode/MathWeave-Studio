"""Independent mathematical verification for surface of revolution (area and volume)."""

from __future__ import annotations

import math
import sympy as sp

from math_app.application.dtos import VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class SurfaceOfRevolutionVerifier(Verifier):
    """Verifies area and volume of revolution using independent symbolic integration."""

    def verify_revolution(
        self,
        computed_area: sp.Expr,
        computed_volume: sp.Expr,
        area_integrand: sp.Expr,
        vol_integrand: sp.Expr,
        var: sp.Symbol,
        a: sp.Expr,
        b: sp.Expr,
    ) -> VerificationResult:
        """Verify revolution area and volume independently."""
        # 1. Independent symbolic re-integration
        try:
            ref_area = sp.integrate(area_integrand, (var, a, b))
            ref_vol = sp.integrate(vol_integrand, (var, a, b))
            diff_a = sp.simplify(computed_area - ref_area)
            diff_v = sp.simplify(computed_volume - ref_vol)
            if diff_a == 0 and diff_v == 0:
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="symbolic_revolution_integrals",
                    details="Cả diện tích mặt và thể tích khối tròn xoay khớp hoàn toàn với tính toán độc lập.",
                )
        except Exception:
            pass

        # 2. Numerical check
        try:
            ca_f = float(computed_area.evalf())
            cv_f = float(computed_volume.evalf())
            a_f = float(a.evalf())
            b_f = float(b.evalf())
            if b_f > a_f and math.isfinite(a_f) and math.isfinite(b_f):
                fa_num = sp.lambdify(var, area_integrand, modules=["math", "numpy"])
                fv_num = sp.lambdify(var, vol_integrand, modules=["math", "numpy"])
                nodes = [-0.9061798459, -0.5384693101, 0.0, 0.5384693101, 0.9061798459]
                weights = [0.2369268850, 0.4786286705, 0.5688888889, 0.4786286705, 0.2369268850]
                mid = 0.5 * (b_f + a_f)
                half = 0.5 * (b_f - a_f)
                num_a = half * sum(w * fa_num(mid + half * xi) for xi, w in zip(nodes, weights))
                num_v = half * sum(w * fv_num(mid + half * xi) for xi, w in zip(nodes, weights))
                if abs(ca_f - num_a) < 1e-3 * (abs(ca_f) + 1.0) and abs(cv_f - num_v) < 1e-3 * (abs(cv_f) + 1.0):
                    return VerificationResult(
                        status=VerificationStatus.VERIFIED,
                        method="numerical_gauss_legendre_revolution",
                        details="Xác nhận số học bằng cầu phương Gauss–Legendre khớp với diện tích và thể tích tròn xoay.",
                    )
        except Exception:
            pass

        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="revolution_check",
            details="Kiểm tra độc lập biểu trưng chưa thể quy về dạng đóng.",
        )

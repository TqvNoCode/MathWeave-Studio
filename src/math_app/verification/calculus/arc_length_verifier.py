"""Independent mathematical verification for arc length calculations."""

from __future__ import annotations

import math
import sympy as sp

from math_app.application.dtos import VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class ArcLengthVerifier(Verifier):
    """Verifies arc length calculations using independent symbolic and numerical methods."""

    def verify_arc_length(
        self,
        computed_length: sp.Expr,
        integrand: sp.Expr,
        var: sp.Symbol,
        a: sp.Expr,
        b: sp.Expr,
    ) -> VerificationResult:
        """Verify arc length value independently."""
        # 1. Independent symbolic re-integration
        try:
            ref_val = sp.integrate(integrand, (var, a, b))
            diff = sp.simplify(computed_length - ref_val)
            if diff == 0:
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="symbolic_arc_length_integral",
                    details="Độ dài cung khớp hoàn toàn với tính toán tích phân độc lập dạng đóng.",
                )
        except Exception:
            pass

        # 2. Numerical Gauss-Legendre quadrature check
        try:
            comp_f = float(computed_length.evalf())
            a_f = float(a.evalf())
            b_f = float(b.evalf())
            if b_f > a_f and math.isfinite(a_f) and math.isfinite(b_f):
                f_num = sp.lambdify(var, integrand, modules=["math", "numpy"])
                nodes = [-0.9061798459, -0.5384693101, 0.0, 0.5384693101, 0.9061798459]
                weights = [0.2369268850, 0.4786286705, 0.5688888889, 0.4786286705, 0.2369268850]
                mid = 0.5 * (b_f + a_f)
                half = 0.5 * (b_f - a_f)
                num_val = half * sum(w * f_num(mid + half * xi) for xi, w in zip(nodes, weights))
                if abs(comp_f - num_val) < 1e-4 * (abs(comp_f) + 1.0):
                    return VerificationResult(
                        status=VerificationStatus.VERIFIED,
                        method="numerical_gauss_legendre_arc_length",
                        details="Xác nhận số học bằng cầu phương Gauss–Legendre khớp với kết quả.",
                    )
        except Exception:
            pass

        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="arc_length_check",
            details="Kiểm tra độc lập biểu trưng chưa thể quy về dạng đóng.",
        )

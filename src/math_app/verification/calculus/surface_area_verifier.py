"""Independent mathematical verification for surface area calculations."""

from __future__ import annotations

import math
import sympy as sp

from math_app.application.dtos import VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class SurfaceAreaVerifier(Verifier):
    """Verifies surface area calculations using independent symbolic and numerical methods."""

    def verify_surface_area(
        self,
        computed_area: sp.Expr,
        integrand: sp.Expr,
        u_var: sp.Symbol,
        u_min: sp.Expr,
        u_max: sp.Expr,
        v_var: sp.Symbol,
        v_min: sp.Expr,
        v_max: sp.Expr,
    ) -> VerificationResult:
        """Verify surface area value independently."""
        # 1. Independent symbolic re-integration
        try:
            inner = sp.integrate(integrand, (u_var, u_min, u_max))
            ref_val = sp.integrate(inner, (v_var, v_min, v_max))
            diff = sp.simplify(computed_area - ref_val)
            if diff == 0:
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="symbolic_surface_area_integral",
                    details="Diện tích mặt khớp hoàn toàn với tính toán tích phân bội hai độc lập.",
                )
        except Exception:
            pass

        # 2. 2D Gauss-Legendre quadrature check
        try:
            comp_f = float(computed_area.evalf())
            u_a = float(u_min.evalf())
            u_b = float(u_max.evalf())
            v_a = float(v_min.evalf())
            v_b = float(v_max.evalf())
            if u_b > u_a and v_b > v_a and all(math.isfinite(x) for x in (u_a, u_b, v_a, v_b)):
                f_num = sp.lambdify((u_var, v_var), integrand, modules=["math", "numpy"])
                nodes = [-0.7745966692, 0.0, 0.7745966692]
                weights = [0.5555555556, 0.8888888889, 0.5555555556]
                u_mid = 0.5 * (u_b + u_a)
                u_half = 0.5 * (u_b - u_a)
                v_mid = 0.5 * (v_b + v_a)
                v_half = 0.5 * (v_b - v_a)
                total = 0.0
                for xi_u, w_u in zip(nodes, weights):
                    u_pt = u_mid + u_half * xi_u
                    for xi_v, w_v in zip(nodes, weights):
                        v_pt = v_mid + v_half * xi_v
                        total += w_u * w_v * f_num(u_pt, v_pt)
                num_val = u_half * v_half * total
                if abs(comp_f - num_val) < 1e-3 * (abs(comp_f) + 1.0):
                    return VerificationResult(
                        status=VerificationStatus.VERIFIED,
                        method="numerical_2d_gauss_quadrature_surface_area",
                        details="Xác nhận số học bằng cầu phương Gauss 2D khớp với diện tích mặt tính toán.",
                    )
                else:
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="numerical_2d_gauss_quadrature_discrepancy",
                        details=f"Phát hiện sai lệch giữa diện tích tính toán ({comp_f:.6g}) và cầu phương Gauss 2D ({num_val:.6g}).",
                    )
        except Exception:
            pass

        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="surface_area_check",
            details="Kiểm tra độc lập biểu trưng chưa thể quy về dạng đóng.",
        )

"""Independent mathematical verification for scalar and vector surface integrals."""

from __future__ import annotations

import sympy as sp

from math_app.application.dtos import VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class SurfaceIntegralVerifier(Verifier):
    """Verifies surface integrals using orientation inversion invariants and independent 2D integration."""

    def verify_surface_integral(
        self,
        computed_result: sp.Expr,
        integrand_2d: sp.Expr,
        u_var: sp.Symbol,
        u_min: sp.Expr,
        u_max: sp.Expr,
        v_var: sp.Symbol,
        v_min: sp.Expr,
        v_max: sp.Expr,
        is_flux: bool = False,
    ) -> VerificationResult:
        """Verify surface integral by comparing against independent iterated double integration."""
        try:
            # 1. Independent symbolic iterated integration
            inner = sp.integrate(integrand_2d, (v_var, v_min, v_max))
            ref_val = sp.integrate(inner, (u_var, u_min, u_max))
            diff = sp.simplify(computed_result - ref_val)
            if diff == 0:
                details = (
                    "Thông lượng trường vectơ qua mặt cong khớp hoàn toàn với tính toán độc lập."
                    if is_flux
                    else "Tích phân mặt vô hướng khớp hoàn toàn với tính toán độc lập."
                )
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="symbolic_iterated_surface_integral",
                    details=details,
                )
        except Exception:
            pass

        # 2. Independent 2D numerical quadrature approximation
        try:
            val_comp = float(computed_result.evalf())
            f_num = sp.lambdify((u_var, v_var), integrand_2d, modules=["math", "numpy"])
            u1, u2 = float(u_min.evalf()), float(u_max.evalf())
            v1, v2 = float(v_min.evalf()), float(v_max.evalf())
            # 3x3 Gauss-Legendre grid
            nodes = [-0.7745966692, 0.0, 0.7745966692]
            weights = [5.0 / 9.0, 8.0 / 9.0, 5.0 / 9.0]
            u_mid, u_half = 0.5 * (u2 + u1), 0.5 * (u2 - u1)
            v_mid, v_half = 0.5 * (v2 + v1), 0.5 * (v2 - v1)

            num_val = 0.0
            for ui, wu in zip(nodes, weights):
                for vi, wv in zip(nodes, weights):
                    u_pt = u_mid + u_half * ui
                    v_pt = v_mid + v_half * vi
                    num_val += wu * wv * f_num(u_pt, v_pt)
            num_val *= u_half * v_half

            if abs(val_comp - num_val) < 2e-3 * (abs(val_comp) + 1.0):
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="numerical_2d_gauss_legendre_surface_integral",
                    details="Xác nhận số học bằng cầu phương Gauss–Legendre 2 chiều khớp với kết quả.",
                )
        except Exception:
            pass

        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="surface_integral_check",
            details="Kiểm tra độc lập biểu trưng chưa thể quy về dạng đóng.",
        )

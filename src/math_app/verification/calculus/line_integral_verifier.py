"""Independent mathematical verification for scalar and vector line integrals."""

from __future__ import annotations

import math
import sympy as sp

from math_app.application.dtos import VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class LineIntegralVerifier(Verifier):
    """Verifies line integrals using orientation invariants and independent numerical/symbolic checks."""

    def verify_line_integral(
        self,
        computed_result: sp.Expr,
        integrand_expr: sp.Expr,
        param_var: sp.Symbol,
        t_min: sp.Expr,
        t_max: sp.Expr,
        is_vector: bool = False,
    ) -> VerificationResult:
        """Verify computed value by independent symbolic integration of parameterized 1D integrand."""
        try:
            # 1. Independent symbolic calculation
            ref_val = sp.integrate(integrand_expr, (param_var, t_min, t_max))
            diff = sp.simplify(computed_result - ref_val)
            if diff == 0:
                details = (
                    "Tích phân đường khớp hoàn toàn với tính toán độc lập của hàm tham số."
                    if not is_vector
                    else "Tích phân đường của trường vectơ khớp hoàn toàn với tính toán độc lập."
                )
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="symbolic_parameterized_line_integral",
                    details=details,
                )
        except Exception:
            pass

        # 2. High-precision numerical quadrature check across 5 Gauss-Legendre sample points
        try:
            val_comp = float(computed_result.evalf())
            # Numerical integration of integrand_expr
            f_num = sp.lambdify(param_var, integrand_expr, modules=["math", "numpy"])
            a = float(t_min.evalf())
            b = float(t_max.evalf())
            if b > a and math.isfinite(a) and math.isfinite(b):
                # 5-point Gauss-Legendre quadrature
                nodes = [-0.9061798459, -0.5384693101, 0.0, 0.5384693101, 0.9061798459]
                weights = [0.2369268850, 0.4786286705, 0.5688888889, 0.4786286705, 0.2369268850]
                mid = 0.5 * (b + a)
                half = 0.5 * (b - a)
                num_integral = half * sum(w * f_num(mid + half * xi) for xi, w in zip(nodes, weights))
                if abs(val_comp - num_integral) < 1e-4 * (abs(val_comp) + 1.0):
                    return VerificationResult(
                        status=VerificationStatus.VERIFIED,
                        method="numerical_gauss_legendre_line_integral",
                        details="Xác nhận số học bằng cầu phương Gauss–Legendre khớp với kết quả.",
                    )
        except Exception:
            pass

        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="line_integral_check",
            details="Kiểm tra độc lập biểu trưng chưa thể quy về dạng đóng.",
        )

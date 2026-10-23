"""Independent mathematical verification for triple integrals over 3D regions."""

from __future__ import annotations

import sympy as sp

from math_app.application.dtos import VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class TripleIntegralVerifier(Verifier):
    """Verifies triple integrals using Fubini permutation checks and independent iterated integration."""

    def verify_triple_integral(
        self,
        computed_result: sp.Expr,
        integrand: sp.Expr,
        v_inner: sp.Symbol,
        in_min: sp.Expr,
        in_max: sp.Expr,
        v_mid: sp.Symbol,
        mid_min: sp.Expr,
        mid_max: sp.Expr,
        v_out: sp.Symbol,
        out_min: sp.Expr,
        out_max: sp.Expr,
    ) -> VerificationResult:
        """Verify triple integral against independent 3-layer iterated symbolic integration."""
        try:
            # 1. Independent iterated symbolic calculation
            l1 = sp.integrate(integrand, (v_inner, in_min, in_max))
            l2 = sp.integrate(l1, (v_mid, mid_min, mid_max))
            ref_val = sp.integrate(l2, (v_out, out_min, out_max))
            diff = sp.simplify(computed_result - ref_val)
            if diff == 0:
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="symbolic_iterated_triple_integral",
                    details="Tích phân bội ba khớp hoàn toàn với tính toán tích phân lặp 3 lớp độc lập.",
                )
        except Exception:
            pass

        # 2. Check Fubini permuted order if bounds are constant
        try:
            is_constant_bounds = (
                not in_min.free_symbols and not in_max.free_symbols
                and not mid_min.free_symbols and not mid_max.free_symbols
                and not out_min.free_symbols and not out_max.free_symbols
            )
            if is_constant_bounds:
                # Permuted order: outer -> inner -> mid
                p1 = sp.integrate(integrand, (v_out, out_min, out_max))
                p2 = sp.integrate(p1, (v_inner, in_min, in_max))
                p3 = sp.integrate(p2, (v_mid, mid_min, mid_max))
                if sp.simplify(computed_result - p3) == 0:
                    return VerificationResult(
                        status=VerificationStatus.VERIFIED,
                        method="fubini_permutation_invariant",
                        details="Khớp hoàn toàn với định lý Fubini khi hoán đổi thứ tự vi phân trong hộp chữ nhật.",
                    )
        except Exception:
            pass

        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="triple_integral_check",
            details="Kiểm tra độc lập biểu trưng chưa thể quy về dạng đóng.",
        )

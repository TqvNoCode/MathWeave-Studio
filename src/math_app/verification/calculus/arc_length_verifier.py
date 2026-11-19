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
        is_divergent: bool = False,
    ) -> VerificationResult:
        """Verify arc length value independently."""
        # 1. Independent verification of divergent improper integral
        if is_divergent or computed_length in (sp.oo, -sp.oo):
            try:
                a_f = float(a.evalf())
                b_f = float(b.evalf())
                interval = sp.Interval(a, b)
                candidates: set[sp.Expr] = set()
                for node in sp.preorder_traversal(integrand):
                    if node.is_Pow and node.exp.is_negative:
                        try:
                            sols = sp.solveset(node.base, var, domain=interval)
                            for s in sols:
                                candidates.add(s)
                        except Exception:
                            pass
                    elif isinstance(node, (sp.tan, sp.sec)):
                        try:
                            sols = sp.solveset(sp.cos(node.args[0]), var, domain=interval)
                            for s in sols:
                                candidates.add(s)
                        except Exception:
                            pass
                    elif isinstance(node, (sp.cot, sp.csc)):
                        try:
                            sols = sp.solveset(sp.sin(node.args[0]), var, domain=interval)
                            for s in sols:
                                candidates.add(s)
                        except Exception:
                            pass

                # Check if any candidate point has a confirmed non-integrable pole
                confirmed_divergence = False
                for pt in candidates:
                    try:
                        pt_f = float(pt.evalf())
                        if (a_f - 1e-7) <= pt_f <= (b_f + 1e-7):
                            lim_val = sp.limit(integrand, var, pt)
                            if lim_val in (sp.oo, -sp.oo) or lim_val.has(sp.zoo):
                                confirmed_divergence = True
                                break
                            order_lim = sp.limit((var - pt) * integrand, var, pt)
                            if order_lim != 0:
                                confirmed_divergence = True
                                break
                    except Exception:
                        pass

                if confirmed_divergence:
                    return VerificationResult(
                        status=VerificationStatus.VERIFIED,
                        method="divergence_singularity_analysis",
                        details="Xác nhận độc lập: tích phân độ dài cung suy rộng phân kỳ tới +vô cùng do tồn tại điểm kỳ dị bậc p >= 1.",
                    )
                elif not candidates:
                    try:
                        import mpmath

                        f_num = sp.lambdify(var, integrand, modules=["mpmath"])
                        v = mpmath.quad(f_num, [a_f, b_f], method="tanh-sinh")
                        if math.isfinite(float(v)):
                            return VerificationResult(
                                status=VerificationStatus.FAILED,
                                method="divergence_refuted",
                                details="Kiểm tra độc lập phát hiện biểu thức khả tích và không phân kỳ trên đoạn đã cho.",
                            )
                    except Exception:
                        pass
            except Exception:
                pass

            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="divergence_inconclusive",
                details="Chưa thể xác nhận độc lập tính phân kỳ của tích phân độ dài cung.",
            )

        # 2. Independent symbolic re-integration (only for exact symbolic results)
        if not isinstance(computed_length, sp.Float):
            from math_app.application.process_guard import run_with_process_timeout

            try:
                res_exec = run_with_process_timeout(
                    sp.integrate,
                    args=(integrand, (var, a, b)),
                    timeout_seconds=1.0,
                )
                if res_exec.status == "ok":
                    ref_val = res_exec.value
                    if ref_val is not None and not isinstance(ref_val, sp.Integral):
                        diff = sp.simplify(computed_length - ref_val)
                        if diff == 0:
                            return VerificationResult(
                                status=VerificationStatus.VERIFIED,
                                method="symbolic_arc_length_integral",
                                details="Độ dài cung khớp hoàn toàn với tính toán tích phân độc lập dạng đóng.",
                            )
            except Exception:
                pass

        # 3. Robust numerical adaptive quadrature check (tanh-sinh / mpmath)
        try:
            import mpmath

            comp_f = float(computed_length.evalf())
            a_f = float(a.evalf())
            b_f = float(b.evalf())
            if b_f > a_f and math.isfinite(a_f) and math.isfinite(b_f):
                f_num = sp.lambdify(var, integrand, modules=["mpmath"])
                num_val, _ = mpmath.quad(f_num, [a_f, b_f], error=True, method="tanh-sinh")
                num_f = float(num_val)
                if abs(comp_f - num_f) < 1e-3 * (abs(comp_f) + 1.0):
                    return VerificationResult(
                        status=VerificationStatus.VERIFIED,
                        method="numerical_quadrature_arc_length",
                        details="Xác nhận số học bằng cầu phương thích ứng tanh-sinh khớp với kết quả.",
                    )
                else:
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="numerical_quadrature_discrepancy",
                        details=f"Phát hiện sai lệch số học giữa kết quả tính toán ({comp_f:.6g}) và kiểm tra số độc lập ({num_f:.6g}).",
                    )
        except Exception:
            pass

        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="arc_length_check",
            details="Kiểm tra độc lập biểu trưng chưa thể quy về dạng đóng.",
        )

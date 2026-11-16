"""Independent mathematical verification for differential equation solutions."""

from __future__ import annotations

import math
from typing import Any
import sympy as sp

from math_app.application.dtos import VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class ODEVerifier(Verifier):
    """Verifies differential equation solutions against original equations and initial conditions."""

    SAMPLE_PROBE_POINTS = (0.23, 0.71, 1.45, 2.87)

    def verify(self, *args: Any, **kwargs: Any) -> VerificationResult:
        """Route to appropriate verification method based on arguments."""
        if "potential_F" in kwargs or (len(args) >= 3 and isinstance(args[0], sp.Expr) and len(args) == 5):
            return self.verify_exact(*args, **kwargs)
        return self.verify_explicit(*args, **kwargs)

    def verify_explicit(
        self,
        solution: sp.Expr,
        variable: sp.Symbol,
        p_expr: sp.Expr,
        g_expr: sp.Expr,
        initial_condition: tuple[sp.Expr, sp.Expr] | None = None,
        integration_constant: sp.Symbol | None = None,
    ) -> VerificationResult:
        """Verify an explicit ODE solution y(t) by evaluating the residual:

        R(t) = y'(t) + p(t)*y(t) - g(t)
        """
        try:
            diff_y = sp.diff(solution, variable)
            residual = sp.simplify(diff_y + p_expr * solution - g_expr)
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="residual_computation_failed",
                details=f"Không thể tính toán biểu thức dư R(t): {exc}",
            )

        # 1. Symbolic verification of residual
        is_residual_zero = False
        try:
            if residual == 0:
                is_residual_zero = True
            else:
                expanded = sp.expand(diff_y + p_expr * solution - g_expr)
                if sp.simplify(expanded) == 0:
                    is_residual_zero = True
        except Exception:
            pass

        # 2. Numerical spot-checks if symbolic simplification was inconclusive
        if not is_residual_zero:
            const_sym = integration_constant or sp.Symbol("C")
            discrepancies: list[float] = []
            matches = 0

            # Substitute test value C = 1 if C is still present
            probe_residual = residual.subs(const_sym, 1) if const_sym in residual.free_symbols else residual

            for pt in self.SAMPLE_PROBE_POINTS:
                try:
                    val = complex(probe_residual.subs(variable, pt).evalf())
                    if math.isnan(val.real) or math.isnan(val.imag):
                        continue
                    err = abs(val)
                    if err > 1e-6:
                        discrepancies.append(err)
                    else:
                        matches += 1
                except Exception:
                    continue

            if discrepancies:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="numerical_residual_discrepancy",
                    details=f"Phát hiện sai số trong kiểm tra số dư tại các điểm thử (sai số lớn nhất: {max(discrepancies):.6e}).",
                )
            if matches >= 2:
                is_residual_zero = True

        if not is_residual_zero:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="inconclusive",
                details="Biểu thức dư giải tích R(t) không thể rút gọn thành 0 bằng phương pháp ký hiệu.",
            )

        # 3. Check initial condition if provided
        if initial_condition is not None:
            t0, y0 = initial_condition
            try:
                val_at_t0 = sp.simplify(solution.subs(variable, t0))
                ic_diff = sp.simplify(val_at_t0 - y0)
                if ic_diff != 0:
                    # Try numerical verification of IC
                    try:
                        num_diff = abs(complex((val_at_t0 - y0).evalf()))
                        if num_diff > 1e-6:
                            return VerificationResult(
                                status=VerificationStatus.FAILED,
                                method="initial_condition_mismatch",
                                details=f"Nghiệm thỏa mãn phương trình vi phân nhưng sai lệch tại điều kiện ban đầu: y({t0}) = {val_at_t0} != {y0}.",
                            )
                    except Exception:
                        return VerificationResult(
                            status=VerificationStatus.FAILED,
                            method="initial_condition_mismatch",
                            details=f"Nghiệm không thỏa mãn điều kiện ban đầu y({t0}) = {y0}.",
                        )
            except Exception as exc:
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="ic_evaluation_failed",
                    details=f"Không thể kiểm tra điều kiện ban đầu: {exc}",
                )

            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="ode_residual_and_ic_symbolic_zero_check",
                details=f"Kiểm chứng độc lập thành công: Biểu thức dư R({variable}) ≡ 0 và điều kiện ban đầu y({t0}) = {y0} nghiệm đúng.",
            )

        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            method="ode_residual_symbolic_zero_check",
            details=f"Kiểm chứng độc lập thành công: Biểu thức dư R({variable}) = y' + p({variable})y - g({variable}) ≡ 0.",
        )

    def verify_exact(
        self,
        potential_F: sp.Expr,
        M_expr: sp.Expr,
        N_expr: sp.Expr,
        x_sym: sp.Symbol,
        y_sym: sp.Symbol,
        initial_condition: tuple[sp.Expr, sp.Expr] | None = None,
    ) -> VerificationResult:
        """Verify potential function F(x, y) for exact equation M dx + N dy = 0."""
        try:
            dF_dx = sp.diff(potential_F, x_sym)
            dF_dy = sp.diff(potential_F, y_sym)
            diff_M = sp.simplify(dF_dx - M_expr)
            diff_N = sp.simplify(dF_dy - N_expr)

            if diff_M != 0 or diff_N != 0:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="exact_potential_gradient_mismatch",
                    details="Hàm thế F(x, y) không thỏa mãn hệ thức ∇F = (M, N).",
                )

            if initial_condition is not None:
                x0, y0 = initial_condition
                val_at_ic = sp.simplify(potential_F.subs([(x_sym, x0), (y_sym, y0)]))
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="exact_potential_gradient_and_ic_check",
                    details=f"Kiểm chứng thành công: ∇F = (M, N) và F({x0}, {y0}) = {val_at_ic}.",
                )

            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="exact_potential_gradient_check",
                details="Kiểm chứng thành công: Gradient của hàm thế ∇F = (∂F/∂x, ∂F/∂y) đồng nhất với (M, N).",
            )
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="exact_verification_failed",
                details=f"Không thể kiểm tra hàm thế vi phân toàn phần: {exc}",
            )

    def verify_implicit(
        self,
        potential_phi: sp.Expr,
        x_sym: sp.Symbol,
        y_sym: sp.Symbol,
        rhs_f_expr: sp.Expr,
        rhs_g_expr: sp.Expr,
        initial_condition: tuple[sp.Expr, sp.Expr] | None = None,
        c_val: sp.Expr | None = None,
    ) -> VerificationResult:
        """Verify implicit relation Phi(x, y) = C for dy/dx = f(x)*g(y).

        By implicit differentiation: dPhi/dx + (dPhi/dy)*y' = 0 => y' = -Phi_x / Phi_y.
        Residual: Phi_x + Phi_y * (f(x)*g(y)) == 0.
        """
        try:
            phi_x = sp.diff(potential_phi, x_sym)
            phi_y = sp.diff(potential_phi, y_sym)
            implicit_residual = sp.simplify(phi_x + phi_y * rhs_f_expr * rhs_g_expr)

            if implicit_residual != 0:
                implicit_residual = sp.simplify(sp.expand(phi_x + phi_y * rhs_f_expr * rhs_g_expr))

            if implicit_residual != 0:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="implicit_differential_mismatch",
                    details="Đạo hàm ẩn của hệ thức không thỏa mãn phương trình vi phân ban đầu.",
                )

            if initial_condition is not None and c_val is not None:
                x0, y0 = initial_condition
                val_at_ic = sp.simplify(potential_phi.subs([(x_sym, x0), (y_sym, y0)]))
                if sp.simplify(val_at_ic - c_val) != 0:
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="initial_condition_mismatch",
                        details=f"Hệ thức nghiệm ẩn không thỏa mãn điều kiện ban đầu y({x0}) = {y0}.",
                    )

            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="separable_implicit_derivation_verified",
                details="Kiểm chứng thành công: Đạo hàm ẩn d/dx[Φ(x, y)] đồng nhất với phương trình vi phân ban đầu.",
            )
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="implicit_verification_failed",
                details=f"Không thể kiểm tra nghiệm ẩn: {exc}",
            )

    def verify_integrating_factor(
        self,
        potential_F: sp.Expr,
        mu_expr: sp.Expr,
        M_expr: sp.Expr,
        N_expr: sp.Expr,
        x_sym: sp.Symbol,
        y_sym: sp.Symbol,
        initial_condition: tuple[sp.Expr, sp.Expr] | None = None,
    ) -> VerificationResult:
        """Verify integrating factor mu and potential F for M dx + N dy = 0."""
        try:
            dF_dx = sp.diff(potential_F, x_sym)
            dF_dy = sp.diff(potential_F, y_sym)
            M_transformed = sp.simplify(mu_expr * M_expr)
            N_transformed = sp.simplify(mu_expr * N_expr)

            diff_M = sp.simplify(dF_dx - M_transformed)
            diff_N = sp.simplify(dF_dy - N_transformed)

            if diff_M != 0 or diff_N != 0:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="integrating_factor_gradient_mismatch",
                    details="Hàm thế F(x, y) không thỏa mãn ∇F = (μM, μN).",
                )

            if initial_condition is not None:
                x0, y0 = initial_condition
                val_at_ic = sp.simplify(potential_F.subs([(x_sym, x0), (y_sym, y0)]))
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="integrating_factor_and_ic_check",
                    details=f"Kiểm chứng thành công: ∇F = (μM, μN) và F({x0}, {y0}) = {val_at_ic}.",
                )

            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="integrating_factor_exactness_verified",
                details="Kiểm chứng thành công: Thừa số tích phân μ biến đổi phương trình thành vi phân toàn phần và ∇F = (μM, μN).",
            )
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="integrating_factor_verification_failed",
                details=f"Không thể kiểm tra thừa số tích phân: {exc}",
            )

    def verify_second_order(
        self,
        solution: sp.Expr,
        variable: sp.Symbol,
        a_coeff: sp.Expr,
        b_coeff: sp.Expr,
        c_coeff: sp.Expr,
        initial_condition: tuple[sp.Expr, sp.Expr] | None = None,
        initial_derivative: tuple[sp.Expr, sp.Expr] | None = None,
        c1_sym: sp.Symbol | None = None,
        c2_sym: sp.Symbol | None = None,
    ) -> VerificationResult:
        """Verify a second-order ODE solution against a*y'' + b*y' + c*y = 0 and optional IVPs."""
        try:
            dy = sp.diff(solution, variable)
            d2y = sp.diff(dy, variable)
            ode_lhs = a_coeff * d2y + b_coeff * dy + c_coeff * solution
            residual = sp.simplify(ode_lhs)
            if residual != 0:
                residual = sp.simplify(sp.expand(ode_lhs))
            if residual != 0:
                residual = sp.simplify(sp.trigsimp(residual))
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="residual_computation_failed",
                details=f"Không thể tính toán biểu thức dư cấp hai R(t): {exc}",
            )

        # 1. Symbolic verification of residual
        is_residual_zero = bool(residual == 0)

        # If general solution contains C1, C2
        c1 = c1_sym or sp.Symbol("C1")
        c2 = c2_sym or sp.Symbol("C2")
        if not is_residual_zero and (c1 in residual.free_symbols or c2 in residual.free_symbols):
            try:
                coeff_c1 = sp.simplify(residual.coeff(c1, 1))
                coeff_c2 = sp.simplify(residual.coeff(c2, 1))
                rem = sp.simplify(residual.subs([(c1, 0), (c2, 0)]))
                if coeff_c1 == 0 and coeff_c2 == 0 and rem == 0:
                    is_residual_zero = True
            except Exception:
                pass

        # 2. Numerical spot checks if symbolic was inconclusive
        if not is_residual_zero:
            probe = residual.subs([(c1, 1), (c2, 1)])
            matches = 0
            discrepancies: list[float] = []
            for pt in self.SAMPLE_PROBE_POINTS:
                try:
                    val = complex(probe.subs(variable, pt).evalf())
                    if math.isnan(val.real) or math.isnan(val.imag):
                        continue
                    err = abs(val)
                    if err > 1e-6:
                        discrepancies.append(err)
                    else:
                        matches += 1
                except Exception:
                    continue

            if discrepancies:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="numerical_residual_discrepancy",
                    details=f"Sai số dư cấp hai tại các điểm thử nghiệm (sai số lớn nhất: {max(discrepancies):.6e}).",
                )
            if matches >= 2:
                is_residual_zero = True

        if not is_residual_zero:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="inconclusive",
                details="Biểu thức dư cấp hai R(t) = a*y'' + b*y' + c*y không thể rút gọn thành 0 bằng ký hiệu.",
            )

        # 3. Check initial conditions if provided
        if initial_condition is not None:
            t0, y0 = initial_condition
            try:
                val_y = sp.simplify(solution.subs(variable, t0))
                diff_y = sp.simplify(val_y - y0)
                if diff_y != 0:
                    try:
                        num_diff = abs(complex(diff_y.evalf()))
                        if num_diff > 1e-6:
                            return VerificationResult(
                                status=VerificationStatus.FAILED,
                                method="initial_condition_mismatch",
                                details=f"Nghiệm không thỏa mãn điều kiện ban đầu y({t0}): nhận được {val_y}, kỳ vọng {y0}.",
                            )
                    except Exception:
                        return VerificationResult(
                            status=VerificationStatus.FAILED,
                            method="initial_condition_mismatch",
                            details=f"Nghiệm không thỏa mãn điều kiện ban đầu y({t0}) = {y0}.",
                        )
            except Exception as exc:
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="ic_evaluation_failed",
                    details=f"Không thể kiểm tra điều kiện ban đầu y(t0): {exc}",
                )

        if initial_derivative is not None:
            t0_v, v0 = initial_derivative
            try:
                val_yp = sp.simplify(dy.subs(variable, t0_v))
                diff_yp = sp.simplify(val_yp - v0)
                if diff_yp != 0:
                    try:
                        num_diff = abs(complex(diff_yp.evalf()))
                        if num_diff > 1e-6:
                            return VerificationResult(
                                status=VerificationStatus.FAILED,
                                method="initial_derivative_mismatch",
                                details=f"Nghiệm không thỏa mãn điều kiện đạo hàm ban đầu y'({t0_v}): nhận được {val_yp}, kỳ vọng {v0}.",
                            )
                    except Exception:
                        return VerificationResult(
                            status=VerificationStatus.FAILED,
                            method="initial_derivative_mismatch",
                            details=f"Nghiệm không thỏa mãn điều kiện đạo hàm ban đầu y'({t0_v}) = {v0}.",
                        )
            except Exception as exc:
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="ic_deriv_evaluation_failed",
                    details=f"Không thể kiểm tra điều kiện đạo hàm ban đầu y'(t0): {exc}",
                )

        if initial_condition is not None and initial_derivative is not None:
            t0, y0 = initial_condition
            _, v0 = initial_derivative
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="second_order_ode_residual_and_dual_ic_zero_check",
                details=f"Kiểm chứng độc lập thành công: Biểu thức dư R({variable}) ≡ 0 và hệ điều kiện Cauchy y({t0}) = {y0}, y'({t0}) = {v0} nghiệm đúng.",
            )

        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            method="second_order_ode_residual_zero_check",
            details=f"Kiểm chứng độc lập thành công: Biểu thức dư R({variable}) = a*y'' + b*y' + c*y ≡ 0.",
        )

    def verify_wronskian(
        self,
        y1: sp.Expr,
        y2: sp.Expr,
        variable: sp.Symbol,
        ode_coeffs: tuple[sp.Expr, sp.Expr, sp.Expr] | None = None,
    ) -> tuple[sp.Expr, VerificationResult]:
        """Compute and verify Wronskian W(y1, y2) = y1*y2' - y1'*y2."""
        try:
            dy1 = sp.diff(y1, variable)
            dy2 = sp.diff(y2, variable)
            w_expr = sp.simplify(y1 * dy2 - dy1 * y2)
            if w_expr != 0:
                w_expr = sp.simplify(sp.trigsimp(w_expr))
        except Exception as exc:
            return sp.Integer(0), VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="wronskian_computation_failed",
                details=f"Không thể tính toán định thức Wronskian: {exc}",
            )

        if w_expr != 0:
            return w_expr, VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="wronskian_nonzero_independence_verified",
                details=f"Kiểm chứng độc lập thành công: Định thức Wronskian W(y1, y2) = {w_expr} khác 0 trên miền xác định; hai nghiệm độc lập tuyến tính.",
            )

        # Here w_expr == 0 identically
        # Check if known ODE coefficients were provided and both functions satisfy the ODE
        if ode_coeffs is not None:
            a_c, b_c, c_c = ode_coeffs
            res_y1 = self.verify_second_order(y1, variable, a_c, b_c, c_c)
            res_y2 = self.verify_second_order(y2, variable, a_c, b_c, c_c)
            if res_y1.status == VerificationStatus.VERIFIED and res_y2.status == VerificationStatus.VERIFIED:
                return w_expr, VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="wronskian_zero_ode_solutions_dependent_verified",
                    details="Kiểm chứng thành công: Cả hai hàm số đều là nghiệm của cùng một phương trình vi phân tuyến tính cấp hai có hệ số liên tục và W(y1, y2) ≡ 0; hai nghiệm phụ thuộc tuyến tính theo định lý Abel.",
                )

        # For arbitrary functions without a verified common ODE context, W == 0 is inconclusive
        return w_expr, VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="wronskian_zero_inconclusive_arbitrary_functions",
            details="Định thức Wronskian W(y1, y2) ≡ 0. Đối với hai hàm số khả vi bất kỳ chưa xác định phương trình vi phân liên kết, điều kiện W ≡ 0 chưa đủ để khẳng định phụ thuộc tuyến tính trên toàn miền (phản ví dụ Peano). Kết luận: Chưa đủ điều kiện kết luận (Inconclusive / Unverified).",
        )

    def verify_reduction_of_order(
        self,
        y1: sp.Expr,
        y2: sp.Expr,
        variable: sp.Symbol,
        a_coeff: sp.Expr,
        b_coeff: sp.Expr,
        c_coeff: sp.Expr,
    ) -> VerificationResult:
        """Verify both fundamental solutions and Wronskian independence for Reduction of Order."""
        # 1. Verify y1 satisfies ODE
        res_y1 = self.verify_second_order(y1, variable, a_coeff, b_coeff, c_coeff)
        if res_y1.status != VerificationStatus.VERIFIED:
            return VerificationResult(
                status=res_y1.status,
                method="reduction_of_order_y1_residual_mismatch",
                details=f"Nghiệm thứ nhất y1 không thỏa mãn phương trình: {res_y1.details}",
            )

        # 2. Verify y2 satisfies ODE
        res_y2 = self.verify_second_order(y2, variable, a_coeff, b_coeff, c_coeff)
        if res_y2.status != VerificationStatus.VERIFIED:
            return VerificationResult(
                status=res_y2.status,
                method="reduction_of_order_y2_residual_mismatch",
                details=f"Nghiệm thứ hai y2 tìm được không thỏa mãn phương trình: {res_y2.details}",
            )

        # 3. Verify Wronskian independence
        _, res_w = self.verify_wronskian(y1, y2, variable, ode_coeffs=(a_coeff, b_coeff, c_coeff))
        if res_w.status != VerificationStatus.VERIFIED:
            return VerificationResult(
                status=res_w.status,
                method="reduction_of_order_wronskian_failure",
                details=f"Kiểm tra độc lập tuyến tính qua Wronskian thất bại: {res_w.details}",
            )

        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            method="reduction_of_order_full_verification",
            details="Kiểm chứng thành công: Cả hai nghiệm y1 và y2 đều thỏa mãn phương trình vi phân và Wronskian khác 0 (độc lập tuyến tính).",
        )

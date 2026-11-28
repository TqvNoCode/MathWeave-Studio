"""Independent numerical verifier for Explicit Euler ODE approximations."""

from __future__ import annotations

from decimal import Decimal
import math

from math_app.domain.numerical_ode import (
    NumericalODEMethod,
    NumericalODEOrder,
    NumericalODERequest,
    NumericalODEResponse,
    NumericalODEStatus,
    NumericalVerificationCheck,
    NumericalVerificationReport,
)
from math_app.solvers.numerical.expression_adapter import (
    check_interval_singularities,
    compile_safe_real_evaluator,
    parse_numeric_scalar,
    parse_numerical_ode_equation,
)

_TOL_STEP = 1e-11
_TOL_REC = 1e-10


def _sample_indices(total_steps: int) -> tuple[int, ...]:
    """Select deterministic step indices for independent recurrence verification."""
    if total_steps <= 0:
        return ()
    if total_steps <= 50:
        return tuple(range(total_steps))
    indices: set[int] = set(range(10))
    indices.update(range(max(0, total_steps - 10), total_steps))
    stride = max(1, total_steps // 10)
    for k in range(0, total_steps, stride):
        indices.add(k)
    return tuple(sorted(indices))


class ExplicitEulerVerifier:
    """Independent verifier auditing all 10 Explicit Euler mathematical & grid invariants."""

    def verify(
        self,
        request: NumericalODERequest,
        response: NumericalODEResponse,
    ) -> NumericalVerificationReport:
        if response.status != NumericalODEStatus.SUCCESS:
            return NumericalVerificationReport(
                is_verified=False,
                method="explicit_euler_independent_audit",
                summary="Không thể kiểm chứng vì quá trình giải số không thành công.",
                checks=(
                    NumericalVerificationCheck(
                        name="Trạng thái thực thi",
                        passed=False,
                        details=response.error_message or f"Status: {response.status.value}",
                    ),
                ),
            )

        if request.method != NumericalODEMethod.EXPLICIT_EULER or response.method != NumericalODEMethod.EXPLICIT_EULER:
            return NumericalVerificationReport(
                is_verified=False,
                method="explicit_euler_independent_audit",
                summary="Phương pháp không khớp Explicit Euler.",
            )

        checks: list[NumericalVerificationCheck] = []
        rows = response.rows

        # Re-parse scalar parameters & ODE independently
        try:
            t0_dec, t0_flt = parse_numeric_scalar(request.t0, "t₀")
            _, y0_flt = parse_numeric_scalar(request.y0, "y₀")
            t_end_dec, t_end_flt = parse_numeric_scalar(request.t_end, "T")
            h_dec, h_flt = parse_numeric_scalar(request.step_size, "h")
            v0_flt: float | None = None
            if request.order == NumericalODEOrder.SECOND_ORDER:
                _, v0_flt = parse_numeric_scalar(request.v0, "v₀")
            parsed = parse_numerical_ode_equation(
                request.raw_equation,
                order=request.order,
                indep_var=request.independent_var,
                dep_var=request.dependent_var,
            )
        except Exception as exc:
            return NumericalVerificationReport(
                is_verified=False,
                method="explicit_euler_independent_audit",
                summary=f"Kiểm chứng thất bại khi phân tích độc lập đầu vào: {exc}",
                checks=(NumericalVerificationCheck("Phân tích độc lập", False, str(exc)),),
            )

        # 1. Iteration count
        expected_dir = 1 if t_end_dec > t0_dec else -1
        span = abs(t_end_dec - t0_dec)
        full_steps = int(span // h_dec)
        rem = span - Decimal(full_steps) * h_dec
        tol_dec = h_dec * Decimal("1e-12")
        if rem <= tol_dec:
            rem = Decimal(0)
        elif abs(h_dec - rem) <= tol_dec:
            full_steps += 1
            rem = Decimal(0)
        expected_total_steps = full_steps + (1 if rem > 0 else 0)

        iter_count_ok = (
            response.total_steps == expected_total_steps
            and len(rows) == expected_total_steps + 1
            and response.total_steps <= request.max_steps
            and all(rows[i].step_index == i for i in range(len(rows)))
        )
        checks.append(
            NumericalVerificationCheck(
                name="1. Số bước lặp & chỉ số",
                passed=iter_count_ok,
                details=f"N = {response.total_steps} (kỳ vọng {expected_total_steps}, số hàng = {len(rows)}).",
            )
        )

        # 2. Time-grid construction & drift check
        grid_ok = bool(rows) and abs(rows[0].t - t0_flt) <= _TOL_STEP
        if grid_ok:
            for i in range(len(rows) - 1):
                if expected_dir > 0 and not (rows[i + 1].t > rows[i].t):
                    grid_ok = False
                    break
                if expected_dir < 0 and not (rows[i + 1].t < rows[i].t):
                    grid_ok = False
                    break
        checks.append(
            NumericalVerificationCheck(
                name="2. Lưới thời gian đơn điệu & khởi đầu",
                passed=grid_ok,
                details=f"t₀ = {rows[0].t if rows else 'N/A'} → t_N = {rows[-1].t if rows else 'N/A'} (hướng {'+1' if expected_dir > 0 else '-1'}).",
            )
        )

        # 3. Step-size handling (interior exact h, optional shortened final step <= h)
        step_ok = len(rows) >= 2
        if step_ok:
            for i in range(len(rows) - 1):
                dt = rows[i + 1].t - rows[i].t
                if dt * expected_dir <= 0:
                    step_ok = False
                    break
                if i < len(rows) - 2:
                    if abs(abs(dt) - h_flt) > max(_TOL_STEP, 1e-11 * max(1.0, abs(rows[i].t), h_flt)):
                        step_ok = False
                        break
                else:
                    if abs(dt) > h_flt + max(_TOL_STEP, 1e-11 * max(1.0, h_flt)):
                        step_ok = False
                        break
                    if rows[i].step_used is not None and abs(rows[i].step_used - dt) > _TOL_STEP:
                        step_ok = False
                        break
        checks.append(
            NumericalVerificationCheck(
                name="3. Xử lý bước nhảy h & bước cuối",
                passed=step_ok,
                details=f"h = {h_flt:g}, bước cuối |h_{{N-1}}| = {abs(rows[-1].t - rows[-2].t) if len(rows) >= 2 else 0.0:.6g}.",
            )
        )

        # 4 & 5. Independent recurrence recomputation (1st-order / 2nd-order simultaneous)
        sampled = _sample_indices(len(rows) - 1)
        max_residual = 0.0
        rec_ok = len(sampled) > 0
        try:
            if request.order == NumericalODEOrder.FIRST_ORDER:
                eval_fn = compile_safe_real_evaluator(parsed.rhs_expr, (parsed.indep_var, parsed.dep_var))
                if abs(rows[0].y - y0_flt) > _TOL_REC:
                    rec_ok = False
                for idx in sampled:
                    r0 = rows[idx]
                    r1 = rows[idx + 1]
                    dt = r1.t - r0.t
                    f_ind = eval_fn(r0.t, r0.y)
                    y_pred = r0.y + dt * f_ind
                    res = abs(r1.y - y_pred)
                    slope_res = abs(r0.slope_y - f_ind)
                    max_residual = max(max_residual, res, slope_res)
                    tol = max(_TOL_REC, 1e-10 * max(1.0, abs(r1.y), abs(y_pred)))
                    if res > tol or slope_res > max(_TOL_REC, 1e-10 * max(1.0, abs(f_ind))):
                        rec_ok = False
                        break
                checks.append(
                    NumericalVerificationCheck(
                        name="4. Công thức truy hồi Euler cấp 1",
                        passed=rec_ok,
                        details=f"Kiểm tra {len(sampled)} bước; sai lệch truy hồi lớn nhất = {max_residual:.3e}.",
                    )
                )
            else:
                eval_fn = compile_safe_real_evaluator(
                    parsed.rhs_expr, (parsed.indep_var, parsed.dep_var, parsed.yp_sym)
                )
                if abs(rows[0].y - y0_flt) > _TOL_REC or rows[0].v is None or v0_flt is None or abs(rows[0].v - v0_flt) > _TOL_REC:
                    rec_ok = False
                for idx in sampled:
                    r0 = rows[idx]
                    r1 = rows[idx + 1]
                    if r0.v is None or r1.v is None or r0.slope_v is None:
                        rec_ok = False
                        break
                    dt = r1.t - r0.t
                    F_ind = eval_fn(r0.t, r0.y, r0.v)
                    # Simultaneous update using OLD (r0.y, r0.v)
                    y_pred = r0.y + dt * r0.v
                    v_pred = r0.v + dt * F_ind
                    res_y = abs(r1.y - y_pred)
                    res_v = abs(r1.v - v_pred)
                    res_f = abs(r0.slope_v - F_ind)
                    max_residual = max(max_residual, res_y, res_v, res_f)
                    tol_y = max(_TOL_REC, 1e-10 * max(1.0, abs(r1.y), abs(y_pred)))
                    tol_v = max(_TOL_REC, 1e-10 * max(1.0, abs(r1.v), abs(v_pred)))
                    tol_f = max(_TOL_REC, 1e-10 * max(1.0, abs(F_ind)))
                    if res_y > tol_y or res_v > tol_v or res_f > tol_f:
                        rec_ok = False
                        break
                checks.append(
                    NumericalVerificationCheck(
                        name="5. Cập nhật đồng thời Euler cấp 2",
                        passed=rec_ok,
                        details=f"Kiểm tra {len(sampled)} bước (y và v dùng giá trị cũ); sai lệch lớn nhất = {max_residual:.3e}.",
                    )
                )
        except Exception as exc:
            rec_ok = False
            checks.append(
                NumericalVerificationCheck(
                    name="4/5. Kiểm tra công thức truy hồi",
                    passed=False,
                    details=f"Lỗi khi tính lại công thức truy hồi: {exc}",
                )
            )

        # 6. Final endpoint accuracy & zero overshoot
        endpoint_ok = bool(rows) and abs(rows[-1].t - t_end_flt) <= max(_TOL_STEP, 1e-11 * max(1.0, abs(t_end_flt)))
        checks.append(
            NumericalVerificationCheck(
                name="6. Độ chính xác điểm kết thúc T",
                passed=endpoint_ok,
                details=f"t_N = {rows[-1].t if rows else 'N/A'} vs T = {t_end_flt:g} (không vượt cận).",
            )
        )

        # 7. Floating-point finiteness
        finite_ok = all(
            math.isfinite(r.t)
            and math.isfinite(r.y)
            and math.isfinite(r.slope_y)
            and (r.v is None or math.isfinite(r.v))
            and (r.slope_v is None or math.isfinite(r.slope_v))
            for r in rows
        )
        checks.append(
            NumericalVerificationCheck(
                name="7. Tính hữu hạn dấu phẩy động",
                passed=finite_ok,
                details="Mọi phần tử trong bảng lặp đều hữu hạn (không chứa NaN/Infinity).",
            )
        )

        # 8. Domain & singularity compliance
        sing_err = check_interval_singularities(parsed, t0_flt, t_end_flt)
        domain_ok = sing_err is None
        checks.append(
            NumericalVerificationCheck(
                name="8. Miền xác định & điểm kỳ dị",
                passed=domain_ok,
                details="Khoảng tích phân nằm hoàn toàn trong miền chính quy." if domain_ok else str(sing_err),
            )
        )

        # 9. Analytical comparison consistency (when available)
        ana = response.analytical_comparison
        if ana is not None and ana.available:
            ana_ok = len(ana.points) == len(rows) and all(
                abs(p.abs_error - abs(p.y_exact - p.y_numerical)) <= 1e-11
                and abs(p.t - rows[p.step_index].t) <= 1e-11
                for p in ana.points
            )
            checks.append(
                NumericalVerificationCheck(
                    name="9. Nhất quán đối chiếu giải tích",
                    passed=ana_ok,
                    details=f"Đối chiếu {len(ana.points)} điểm; sai số cuối |y(T) - y_N| = {ana.final_abs_error:.6g}.",
                )
            )
        else:
            checks.append(
                NumericalVerificationCheck(
                    name="9. Đối chiếu giải tích (tùy chọn)",
                    passed=True,
                    details="Không có nghiệm giải tích đóng tương ứng hoặc không bật đối chiếu.",
                )
            )

        # 10. Output data consistency
        out_ok = (
            bool(rows)
            and response.final_t == rows[-1].t
            and response.final_y == rows[-1].y
            and (
                request.order == NumericalODEOrder.FIRST_ORDER
                or response.final_v == rows[-1].v
            )
        )
        checks.append(
            NumericalVerificationCheck(
                name="10. Nhất quán dữ liệu đầu ra",
                passed=out_ok,
                details="final_t, final_y, final_v khớp chính xác với hàng cuối cùng của bảng lặp.",
            )
        )

        all_passed = all(c.passed for c in checks)
        summary = (
            f"Đã kiểm chứng độc lập {len(checks)}/{len(checks)} tiêu chí Explicit Euler (sai lệch truy hồi ≤ {max_residual:.2e})."
            if all_passed
            else "Phát hiện sai lệch trong kiểm chứng độc lập phép tính số."
        )
        return NumericalVerificationReport(
            is_verified=all_passed,
            method="explicit_euler_independent_audit",
            summary=summary,
            checks=tuple(checks),
            checked_indices=sampled,
            max_recurrence_residual=max_residual,
        )

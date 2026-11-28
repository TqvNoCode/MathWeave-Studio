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
    """Independent verifier auditing Explicit Euler mathematical, grid, and error-analysis invariants."""

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
        eval_fn = None
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

        # 9. Analytical comparison & local one-step defect consistency
        ana = response.analytical_comparison
        if ana is not None and ana.available:
            ana_ok = len(ana.points) == len(rows) and all(
                abs(p.abs_error - abs(p.y_exact - p.y_numerical)) <= 1e-11
                and abs(p.t - rows[p.step_index].t) <= 1e-11
                for p in ana.points
            )
            if ana_ok and ana.points:
                max_y_exp = max(p.abs_error for p in ana.points)
                if (
                    ana.max_abs_error is None
                    or abs(ana.max_abs_error - max_y_exp) > 1e-11
                    or ana.final_abs_error is None
                    or abs(ana.final_abs_error - ana.points[-1].abs_error) > 1e-11
                ):
                    ana_ok = False

            if ana_ok and request.order == NumericalODEOrder.SECOND_ORDER:
                for p in ana.points:
                    r = rows[p.step_index]
                    if (
                        p.v_exact is None
                        or p.v_abs_error is None
                        or r.v is None
                        or abs(p.v_abs_error - abs(p.v_exact - r.v)) > 1e-11
                    ):
                        ana_ok = False
                        break
                if ana_ok and ana.points:
                    max_v_exp = max(p.v_abs_error for p in ana.points if p.v_abs_error is not None)
                    if (
                        ana.max_v_abs_error is None
                        or abs(ana.max_v_abs_error - max_v_exp) > 1e-11
                        or ana.final_v_abs_error is None
                        or ana.points[-1].v_abs_error is None
                        or abs(ana.final_v_abs_error - ana.points[-1].v_abs_error) > 1e-11
                    ):
                        ana_ok = False

            # Independently verify local one-step defect δ_{n+1} when eval_fn is available
            if ana_ok and eval_fn is not None and len(ana.points) >= 2:
                if ana.points[0].local_defect_y is not None or ana.points[0].local_defect_v is not None:
                    ana_ok = False
                for idx in sampled:
                    p0 = ana.points[idx]
                    p1 = ana.points[idx + 1]
                    dt = p1.t - p0.t
                    if request.order == NumericalODEOrder.FIRST_ORDER:
                        if p1.local_defect_y is None:
                            ana_ok = False
                            break
                        exp_def = p1.y_exact - p0.y_exact - dt * eval_fn(p0.t, p0.y_exact)
                        tol_d = max(1e-10, 1e-10 * max(1.0, abs(p1.y_exact), abs(exp_def)))
                        if abs(p1.local_defect_y - exp_def) > tol_d:
                            ana_ok = False
                            break
                    else:
                        if (
                            p0.v_exact is None
                            or p1.v_exact is None
                            or p1.local_defect_y is None
                            or p1.local_defect_v is None
                        ):
                            ana_ok = False
                            break
                        exp_def_y = p1.y_exact - p0.y_exact - dt * p0.v_exact
                        exp_def_v = p1.v_exact - p0.v_exact - dt * eval_fn(p0.t, p0.y_exact, p0.v_exact)
                        tol_dy = max(1e-10, 1e-10 * max(1.0, abs(p1.y_exact), abs(exp_def_y)))
                        tol_dv = max(1e-10, 1e-10 * max(1.0, abs(p1.v_exact), abs(exp_def_v)))
                        if abs(p1.local_defect_y - exp_def_y) > tol_dy or abs(p1.local_defect_v - exp_def_v) > tol_dv:
                            ana_ok = False
                            break

            checks.append(
                NumericalVerificationCheck(
                    name="9. Nhất quán đối chiếu giải tích & sai số cục bộ/toàn cục",
                    passed=ana_ok,
                    details=(
                        f"Đối chiếu {len(ana.points)} điểm; sai số cuối |y(T) - y_N| = {ana.final_abs_error:.6g}"
                        + (f", |y'(T) - v_N| = {ana.final_v_abs_error:.6g}." if ana.final_v_abs_error is not None else ".")
                    ),
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

        # 11. Error analysis & step-halving Richardson estimate consistency
        ea = response.error_analysis
        if ea is None:
            checks.append(
                NumericalVerificationCheck(
                    name="11. Phân tích sai số & ước lượng h/2",
                    passed=True,
                    details="Chưa gắn bộ phân tích sai số tùy chọn.",
                )
            )
        else:
            ea_ok = True
            ea_detail = "Phân tích sai số cục bộ O(h²), toàn cục O(h) nhất quán."
            if not ea.has_exact_reference:
                if any(
                    v is not None
                    for v in (
                        ea.final_global_error_y,
                        ea.max_global_error_y,
                        ea.final_global_error_v,
                        ea.max_global_error_v,
                        ea.final_local_defect_y,
                        ea.max_abs_local_defect_y,
                        ea.final_local_defect_v,
                        ea.max_abs_local_defect_v,
                    )
                ):
                    ea_ok = False
                    ea_detail = "Phát hiện giá trị sai số thực bị gán khi không có nghiệm giải tích."
            elif ana is None or not ana.available:
                ea_ok = False
                ea_detail = "has_exact_reference=True nhưng không có analytical_comparison."
            else:
                if (
                    ea.final_global_error_y != ana.final_abs_error
                    or ea.max_global_error_y != ana.max_abs_error
                    or ea.final_global_error_v != ana.final_v_abs_error
                    or ea.max_global_error_v != ana.max_v_abs_error
                    or ea.final_local_defect_y != ana.final_local_defect_y
                    or ea.max_abs_local_defect_y != ana.max_local_defect_y
                    or ea.final_local_defect_v != ana.final_local_defect_v
                    or ea.max_abs_local_defect_v != ana.max_local_defect_v
                ):
                    ea_ok = False
                    ea_detail = "Tổng hợp sai số trong error_analysis không khớp với bảng đối chiếu."

            sh = ea.step_halving
            if ea_ok and sh is not None and sh.available:
                if len(sh.points) != len(rows) or abs(sh.richardson_factor - 2.0) > 1e-12:
                    ea_ok = False
                    ea_detail = "Lưới ước lượng h/2 hoặc hệ số Richardson p=1 không hợp lệ."
                else:
                    for pt in sh.points:
                        r = rows[pt.step_index]
                        if abs(pt.t - r.t) > 1e-11 or abs(pt.y_coarse - r.y) > 1e-11:
                            ea_ok = False
                            ea_detail = "Điểm lưới ước lượng h/2 không thẳng hàng với lưới h."
                            break
                        exp_est_y = 2.0 * abs(pt.y_fine - pt.y_coarse)
                        if abs(pt.estimated_error_y - exp_est_y) > max(1e-11, 1e-10 * exp_est_y):
                            ea_ok = False
                            ea_detail = "Công thức Richardson E_h ≈ 2·|y_(h/2) - y_h| không nhất quán."
                            break
                        if request.order == NumericalODEOrder.SECOND_ORDER:
                            if (
                                pt.v_coarse is None
                                or pt.v_fine is None
                                or pt.estimated_error_v is None
                                or abs(pt.estimated_error_v - 2.0 * abs(pt.v_fine - pt.v_coarse))
                                > max(1e-11, 1e-10 * abs(pt.estimated_error_v))
                            ):
                                ea_ok = False
                                ea_detail = "Công thức Richardson cho đạo hàm v không nhất quán."
                                break
                    if ea_ok and sh.points:
                        max_ey = max(pt.estimated_error_y for pt in sh.points)
                        if (
                            sh.max_estimated_error_y is None
                            or abs(sh.max_estimated_error_y - max_ey) > 1e-11
                            or sh.final_estimated_error_y != sh.points[-1].estimated_error_y
                        ):
                            ea_ok = False
                            ea_detail = "Tổng hợp ước lượng Richardson không khớp các điểm."

            checks.append(
                NumericalVerificationCheck(
                    name="11. Phân tích sai số & ước lượng h/2",
                    passed=ea_ok,
                    details=ea_detail,
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

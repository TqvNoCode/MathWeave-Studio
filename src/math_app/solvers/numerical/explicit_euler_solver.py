"""Independent Explicit Euler (Forward Euler) numerical ODE solver."""

from __future__ import annotations

from decimal import Decimal
import math
import time

from math_app.domain.exceptions import InvalidInputError
from math_app.domain.numerical_ode import (
    NumericalIterationRow,
    NumericalODEMethod,
    NumericalODEOrder,
    NumericalODERequest,
    NumericalODEResponse,
    NumericalODEStatus,
)
from math_app.solvers.numerical.expression_adapter import (
    MAX_NUMERIC_MAGNITUDE,
    NumericalDomainError,
    NumericalOverflowError,
    NumericalSingularityError,
    check_interval_singularities,
    compile_safe_real_evaluator,
    parse_numeric_scalar,
    parse_numerical_ode_equation,
)

DEFAULT_MAX_STEPS = 10_000


def _error_response(
    request: NumericalODERequest,
    status: NumericalODEStatus,
    message: str,
    *,
    failing_step: int | None = None,
    t0: float = 0.0,
    y0: float = 0.0,
    v0: float | None = None,
    t_end: float = 0.0,
    step_size: float = 0.0,
    direction: int = 1,
    canonical_rhs_str: str = "",
    canonical_rhs_latex: str = "",
    equation_latex: str = "",
    is_euler_cauchy: bool = False,
    ec_orig_latex: str = "",
    domain_restrictions: tuple[str, ...] = (),
    rows: tuple[NumericalIterationRow, ...] = (),
    elapsed_ms: float = 0.0,
) -> NumericalODEResponse:
    return NumericalODEResponse(
        status=status,
        method=request.method,
        order=request.order,
        raw_equation=request.raw_equation,
        independent_var=request.independent_var,
        dependent_var=request.dependent_var,
        canonical_rhs_str=canonical_rhs_str,
        canonical_rhs_latex=canonical_rhs_latex,
        equation_latex=equation_latex,
        is_euler_cauchy_transformed=is_euler_cauchy,
        euler_cauchy_original_latex=ec_orig_latex,
        t0=t0,
        y0=y0,
        v0=v0,
        t_end=t_end,
        step_size=step_size,
        direction=direction,
        total_steps=max(0, len(rows) - 1),
        rows=rows,
        error_message=message,
        failing_step=failing_step,
        warnings=(message,),
        domain_restrictions=domain_restrictions,
        execution_time_ms=elapsed_ms,
    )


class ExplicitEulerSolver:
    """Explicit Euler (Forward Euler) numerical solver for 1st- and 2nd-order ODE IVPs."""

    method: NumericalODEMethod = NumericalODEMethod.EXPLICIT_EULER

    def solve(self, request: NumericalODERequest) -> NumericalODEResponse:
        """Integrate the requested 1st- or 2nd-order IVP using Explicit Euler."""
        t_start = time.perf_counter()

        if request.method != NumericalODEMethod.EXPLICIT_EULER:
            return _error_response(
                request,
                NumericalODEStatus.INVALID_INPUT,
                f"Phương pháp '{request.method.value}' chưa được bộ giải ExplicitEulerSolver hỗ trợ.",
                elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
            )

        # 1. Validate numeric IVP parameters before parsing/solving
        try:
            t0_dec, t0_flt = parse_numeric_scalar(request.t0, "t₀")
            y0_dec, y0_flt = parse_numeric_scalar(request.y0, "y₀")
            t_end_dec, t_end_flt = parse_numeric_scalar(request.t_end, "T")
            h_dec, h_flt = parse_numeric_scalar(request.step_size, "h")
            v0_flt: float | None = None
            if request.order == NumericalODEOrder.SECOND_ORDER:
                if request.v0 is None or not str(request.v0).strip():
                    raise InvalidInputError(
                        "PTVP cấp 2 yêu cầu giá trị đạo hàm ban đầu v₀ = y'(t₀)."
                    )
                _, v0_flt = parse_numeric_scalar(request.v0, "v₀ = y'(t₀)")
        except InvalidInputError as exc:
            return _error_response(
                request,
                NumericalODEStatus.INVALID_INPUT,
                str(exc),
                elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
            )

        if h_dec <= 0 or h_flt <= 0.0:
            return _error_response(
                request,
                NumericalODEStatus.INVALID_INPUT,
                "Bước nhảy h phải là số dương (h > 0).",
                t0=t0_flt,
                y0=y0_flt,
                v0=v0_flt,
                t_end=t_end_flt,
                step_size=h_flt,
                elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
            )

        if t0_dec == t_end_dec or abs(t_end_flt - t0_flt) == 0.0:
            return _error_response(
                request,
                NumericalODEStatus.INVALID_INPUT,
                "Điểm bắt đầu t₀ và điểm kết thúc T phải khác nhau (t₀ ≠ T).",
                t0=t0_flt,
                y0=y0_flt,
                v0=v0_flt,
                t_end=t_end_flt,
                step_size=h_flt,
                elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
            )

        if request.max_steps <= 0:
            return _error_response(
                request,
                NumericalODEStatus.INVALID_INPUT,
                "Giới hạn số bước lặp tối đa phải dương.",
                elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
            )

        direction = 1 if t_end_dec > t0_dec else -1

        # 2. Parse & validate the differential equation
        try:
            parsed = parse_numerical_ode_equation(
                request.raw_equation,
                order=request.order,
                indep_var=request.independent_var,
                dep_var=request.dependent_var,
            )
        except InvalidInputError as exc:
            return _error_response(
                request,
                NumericalODEStatus.INVALID_INPUT,
                str(exc),
                t0=t0_flt,
                y0=y0_flt,
                v0=v0_flt,
                t_end=t_end_flt,
                step_size=h_flt,
                direction=direction,
                elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
            )

        # 3. Check interval singularities (including Euler-Cauchy t = 0 guard)
        singularity_msg = check_interval_singularities(parsed, t0_flt, t_end_flt)
        if singularity_msg is not None:
            return _error_response(
                request,
                NumericalODEStatus.SINGULARITY_ERROR,
                singularity_msg,
                failing_step=0,
                t0=t0_flt,
                y0=y0_flt,
                v0=v0_flt,
                t_end=t_end_flt,
                step_size=h_flt,
                direction=direction,
                canonical_rhs_str=parsed.rhs_str,
                canonical_rhs_latex=parsed.rhs_latex,
                equation_latex=parsed.equation_latex,
                is_euler_cauchy=parsed.is_euler_cauchy,
                ec_orig_latex=parsed.euler_cauchy_original_latex,
                domain_restrictions=parsed.domain_restrictions,
                elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
            )

        # 4. Construct drift-free time grid and enforce iteration bound (never truncate)
        span = abs(t_end_dec - t0_dec)
        full_steps = int(span // h_dec)
        rem = span - (Decimal(full_steps) * h_dec)
        tol_dec = h_dec * Decimal("1e-12")
        if rem <= tol_dec:
            rem = Decimal(0)
        elif abs(h_dec - rem) <= tol_dec:
            full_steps += 1
            rem = Decimal(0)

        has_shortened_final_step = rem > 0
        total_steps = full_steps + (1 if has_shortened_final_step else 0)
        if total_steps <= 0:
            total_steps = 1
            has_shortened_final_step = True

        if total_steps > request.max_steps:
            min_h = float(span / Decimal(request.max_steps))
            return _error_response(
                request,
                NumericalODEStatus.ITERATION_LIMIT_EXCEEDED,
                (
                    f"Số bước lặp yêu cầu ({total_steps:,}) vượt quá giới hạn an toàn tối đa "
                    f"({request.max_steps:,} bước). Hệ thống không tự ý cắt bớt phép tính; "
                    f"vui lòng tăng bước nhảy lên tối thiểu h ≥ {min_h:.6g} hoặc thu hẹp khoảng [t₀, T]."
                ),
                t0=t0_flt,
                y0=y0_flt,
                v0=v0_flt,
                t_end=t_end_flt,
                step_size=h_flt,
                direction=direction,
                canonical_rhs_str=parsed.rhs_str,
                canonical_rhs_latex=parsed.rhs_latex,
                equation_latex=parsed.equation_latex,
                is_euler_cauchy=parsed.is_euler_cauchy,
                ec_orig_latex=parsed.euler_cauchy_original_latex,
                domain_restrictions=parsed.domain_restrictions,
                elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
            )

        # Pre-build exact Decimal grid nodes so t_n never accumulates floating-point drift
        signed_h_dec = h_dec if direction > 0 else -h_dec
        t_dec_nodes: list[Decimal] = [
            t0_dec + (Decimal(i) * signed_h_dec) for i in range(full_steps + 1)
        ]
        if has_shortened_final_step:
            t_dec_nodes.append(t_end_dec)
        else:
            t_dec_nodes[-1] = t_end_dec

        t_nodes = [float(d) for d in t_dec_nodes]
        step_deltas = [float(t_dec_nodes[i + 1] - t_dec_nodes[i]) for i in range(total_steps)]
        final_step_mag = abs(step_deltas[-1])

        # 5. Compile AST-safe RHS evaluator once (O(1) symbolic prep)
        try:
            if request.order == NumericalODEOrder.FIRST_ORDER:
                rhs_eval = compile_safe_real_evaluator(parsed.rhs_expr, (parsed.indep_var, parsed.dep_var))
            else:
                rhs_eval = compile_safe_real_evaluator(
                    parsed.rhs_expr,
                    (parsed.indep_var, parsed.dep_var, parsed.yp_sym),
                )
        except InvalidInputError as exc:
            return _error_response(
                request,
                NumericalODEStatus.INVALID_INPUT,
                str(exc),
                t0=t0_flt,
                y0=y0_flt,
                v0=v0_flt,
                t_end=t_end_flt,
                step_size=h_flt,
                direction=direction,
                canonical_rhs_str=parsed.rhs_str,
                canonical_rhs_latex=parsed.rhs_latex,
                equation_latex=parsed.equation_latex,
                is_euler_cauchy=parsed.is_euler_cauchy,
                ec_orig_latex=parsed.euler_cauchy_original_latex,
                domain_restrictions=parsed.domain_restrictions,
                elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
            )

        # 6. Execute Explicit Euler iteration loop
        rows: list[NumericalIterationRow] = []
        y_curr = y0_flt
        v_curr = v0_flt if v0_flt is not None else 0.0

        try:
            for n in range(total_steps):
                t_curr = t_nodes[n]
                h_n = step_deltas[n]

                if request.order == NumericalODEOrder.FIRST_ORDER:
                    try:
                        slope_y = rhs_eval(t_curr, y_curr)
                    except (NumericalSingularityError, NumericalDomainError, NumericalOverflowError) as exc:
                        exc.failing_step = n
                        raise

                    rows.append(
                        NumericalIterationRow(
                            step_index=n,
                            t=t_curr,
                            y=y_curr,
                            slope_y=slope_y,
                            step_used=h_n,
                        )
                    )
                    y_next = y_curr + h_n * slope_y
                    if not math.isfinite(y_next) or abs(y_next) > MAX_NUMERIC_MAGNITUDE:
                        raise NumericalOverflowError(
                            f"Tràn số học hoặc giá trị không hữu hạn tại bước n = {n} (t = {t_curr:.6g}).",
                            failing_step=n,
                        )
                    y_curr = y_next
                else:
                    try:
                        slope_v = rhs_eval(t_curr, y_curr, v_curr)
                    except (NumericalSingularityError, NumericalDomainError, NumericalOverflowError) as exc:
                        exc.failing_step = n
                        raise

                    # Simultaneous Explicit Euler update using OLD y_curr and OLD v_curr
                    y_old = y_curr
                    v_old = v_curr
                    rows.append(
                        NumericalIterationRow(
                            step_index=n,
                            t=t_curr,
                            y=y_old,
                            slope_y=v_old,
                            step_used=h_n,
                            v=v_old,
                            slope_v=slope_v,
                        )
                    )
                    y_next = y_old + h_n * v_old
                    v_next = v_old + h_n * slope_v
                    if (
                        not math.isfinite(y_next)
                        or not math.isfinite(v_next)
                        or abs(y_next) > MAX_NUMERIC_MAGNITUDE
                        or abs(v_next) > MAX_NUMERIC_MAGNITUDE
                    ):
                        raise NumericalOverflowError(
                            f"Tràn số học hoặc giá trị không hữu hạn tại bước n = {n} (t = {t_curr:.6g}).",
                            failing_step=n,
                        )
                    y_curr = y_next
                    v_curr = v_next

            # Evaluate slope at final endpoint t_N (without stepping past T)
            t_final = t_nodes[-1]
            if request.order == NumericalODEOrder.FIRST_ORDER:
                try:
                    final_slope_y = rhs_eval(t_final, y_curr)
                except (NumericalSingularityError, NumericalDomainError, NumericalOverflowError) as exc:
                    exc.failing_step = total_steps
                    raise
                rows.append(
                    NumericalIterationRow(
                        step_index=total_steps,
                        t=t_final,
                        y=y_curr,
                        slope_y=final_slope_y,
                        step_used=None,
                    )
                )
            else:
                try:
                    final_slope_v = rhs_eval(t_final, y_curr, v_curr)
                except (NumericalSingularityError, NumericalDomainError, NumericalOverflowError) as exc:
                    exc.failing_step = total_steps
                    raise
                rows.append(
                    NumericalIterationRow(
                        step_index=total_steps,
                        t=t_final,
                        y=y_curr,
                        slope_y=v_curr,
                        step_used=None,
                        v=v_curr,
                        slope_v=final_slope_v,
                    )
                )

        except NumericalSingularityError as exc:
            step_idx = exc.failing_step if exc.failing_step is not None else len(rows)
            t_at = t_nodes[min(step_idx, len(t_nodes) - 1)]
            return _error_response(
                request,
                NumericalODEStatus.SINGULARITY_ERROR,
                f"Lỗi kỳ dị tại bước lặp n = {step_idx} ({parsed.indep_var} = {t_at:.6g}): {exc}",
                failing_step=step_idx,
                t0=t0_flt,
                y0=y0_flt,
                v0=v0_flt,
                t_end=t_end_flt,
                step_size=h_flt,
                direction=direction,
                canonical_rhs_str=parsed.rhs_str,
                canonical_rhs_latex=parsed.rhs_latex,
                equation_latex=parsed.equation_latex,
                is_euler_cauchy=parsed.is_euler_cauchy,
                ec_orig_latex=parsed.euler_cauchy_original_latex,
                domain_restrictions=parsed.domain_restrictions,
                rows=tuple(rows),
                elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
            )
        except (NumericalDomainError, NumericalOverflowError) as exc:
            step_idx = exc.failing_step if exc.failing_step is not None else len(rows)
            t_at = t_nodes[min(step_idx, len(t_nodes) - 1)]
            return _error_response(
                request,
                NumericalODEStatus.NUMERICAL_ERROR,
                f"Lỗi tính toán số tại bước lặp n = {step_idx} ({parsed.indep_var} = {t_at:.6g}): {exc}",
                failing_step=step_idx,
                t0=t0_flt,
                y0=y0_flt,
                v0=v0_flt,
                t_end=t_end_flt,
                step_size=h_flt,
                direction=direction,
                canonical_rhs_str=parsed.rhs_str,
                canonical_rhs_latex=parsed.rhs_latex,
                equation_latex=parsed.equation_latex,
                is_euler_cauchy=parsed.is_euler_cauchy,
                ec_orig_latex=parsed.euler_cauchy_original_latex,
                domain_restrictions=parsed.domain_restrictions,
                rows=tuple(rows),
                elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
            )

        warnings_list: list[str] = []
        if has_shortened_final_step:
            warnings_list.append(
                f"Khoảng [{t0_flt:g}, {t_end_flt:g}] không chia hết cho h = {h_flt:g}; "
                f"bước cuối được rút ngắn thành h_{total_steps - 1} = {final_step_mag:.6g} để dừng đúng tại T = {t_end_flt:g}."
            )

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        return NumericalODEResponse(
            status=NumericalODEStatus.SUCCESS,
            method=request.method,
            order=request.order,
            raw_equation=request.raw_equation,
            independent_var=parsed.indep_var.name,
            dependent_var=parsed.dep_var.name,
            canonical_rhs_str=parsed.rhs_str,
            canonical_rhs_latex=parsed.rhs_latex,
            equation_latex=parsed.equation_latex,
            is_euler_cauchy_transformed=parsed.is_euler_cauchy,
            euler_cauchy_original_latex=parsed.euler_cauchy_original_latex,
            t0=t0_flt,
            y0=y0_flt,
            v0=v0_flt,
            t_end=t_end_flt,
            step_size=h_flt,
            direction=direction,
            total_steps=total_steps,
            has_shortened_final_step=has_shortened_final_step,
            final_step_size=final_step_mag,
            rows=tuple(rows),
            final_t=t_nodes[-1],
            final_y=y_curr,
            final_v=v_curr if request.order == NumericalODEOrder.SECOND_ORDER else None,
            warnings=tuple(warnings_list),
            domain_restrictions=parsed.domain_restrictions,
            execution_time_ms=elapsed_ms,
        )

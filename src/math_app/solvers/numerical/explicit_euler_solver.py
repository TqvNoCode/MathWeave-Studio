"""Independent Explicit Euler (Forward Euler) numerical ODE solver."""

from __future__ import annotations

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
from math_app.solvers.numerical.euler_engine import (
    FirstOrderEulerAdapter,
    SecondOrderEulerAdapter,
    integrate_explicit_euler,
)
from math_app.solvers.numerical.expression_adapter import (
    NumericalDomainError,
    NumericalOverflowError,
    NumericalSingularityError,
    check_interval_singularities,
    compile_safe_real_evaluator,
    parse_numeric_scalar,
    parse_numerical_ode_equation,
)
from math_app.solvers.numerical.time_grid import GridLimitExceededError, build_time_grid

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
        """Integrate the requested 1st- or 2nd-order IVP using the shared Explicit Euler core."""
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
            _, y0_flt = parse_numeric_scalar(request.y0, "y₀")
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

        # 4. Construct shared drift-free Decimal time grid
        try:
            grid = build_time_grid(t0_dec, t_end_dec, h_dec, request.max_steps)
        except GridLimitExceededError as exc:
            return _error_response(
                request,
                NumericalODEStatus.ITERATION_LIMIT_EXCEEDED,
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

        # 5. Compile AST-safe RHS evaluator and select order-specific adapter
        try:
            if request.order == NumericalODEOrder.FIRST_ORDER:
                rhs_eval = compile_safe_real_evaluator(parsed.rhs_expr, (parsed.indep_var, parsed.dep_var))
                adapter: FirstOrderEulerAdapter | SecondOrderEulerAdapter = FirstOrderEulerAdapter(rhs_eval, y0_flt)
            else:
                rhs_eval = compile_safe_real_evaluator(
                    parsed.rhs_expr,
                    (parsed.indep_var, parsed.dep_var, parsed.yp_sym),
                )
                adapter = SecondOrderEulerAdapter(rhs_eval, y0_flt, v0_flt if v0_flt is not None else 0.0)
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

        # 6. Execute shared Explicit Euler integration engine via adapter
        try:
            records = integrate_explicit_euler(grid, adapter.initial_state, adapter.rhs_system)
            rows = adapter.to_rows(records)
        except NumericalSingularityError as exc:
            step_idx = exc.failing_step if exc.failing_step is not None else 0
            t_at = grid.t_nodes[min(step_idx, len(grid.t_nodes) - 1)]
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
                elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
            )
        except (NumericalDomainError, NumericalOverflowError) as exc:
            step_idx = exc.failing_step if exc.failing_step is not None else 0
            t_at = grid.t_nodes[min(step_idx, len(grid.t_nodes) - 1)]
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
                elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
            )

        warnings_list: list[str] = []
        if grid.has_shortened_final_step:
            warnings_list.append(
                f"Khoảng [{t0_flt:g}, {t_end_flt:g}] không chia hết cho h = {h_flt:g}; "
                f"bước cuối được rút ngắn thành h_{grid.total_steps - 1} = {grid.final_step_size:.6g} "
                f"để dừng đúng tại T = {t_end_flt:g}."
            )

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        final_row = rows[-1]
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
            direction=grid.direction,
            total_steps=grid.total_steps,
            has_shortened_final_step=grid.has_shortened_final_step,
            final_step_size=grid.final_step_size,
            rows=rows,
            final_t=final_row.t,
            final_y=final_row.y,
            final_v=final_row.v if request.order == NumericalODEOrder.SECOND_ORDER else None,
            warnings=tuple(warnings_list),
            domain_restrictions=parsed.domain_restrictions,
            execution_time_ms=elapsed_ms,
        )

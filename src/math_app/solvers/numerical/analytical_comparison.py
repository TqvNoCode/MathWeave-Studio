"""Optional analytical IVP comparison adapter reusing existing analytical ODE solvers read-only."""

from __future__ import annotations

import math
import re
from typing import Callable

import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionResponse
from math_app.application.use_cases.solve_problem import SolveProblemUseCase
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.domain.numerical_ode import (
    AnalyticalComparisonPoint,
    AnalyticalComparisonResult,
    NumericalODEOrder,
    NumericalODERequest,
    NumericalODEResponse,
    NumericalODEStatus,
)
from math_app.input.ode_parser import (
    extract_initial_condition_from_string,
    extract_interval_from_string,
    extract_second_order_ics_from_string,
)
from math_app.input.parser import normalize_variable_name, parse_safe_expression
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.solvers.numerical.expression_adapter import (
    compile_safe_real_evaluator,
    parse_numerical_ode_equation,
)

_TRUSTED_VERIFICATION_STATUSES = frozenset({
    VerificationStatus.VERIFIED,
    VerificationStatus.VERIFIED_ON_BRANCH,
    VerificationStatus.VERIFIED_GLOBALLY,
})


def _extract_explicit_expr(
    final_result: str,
    indep_var: str,
    dep_var: str,
) -> sp.Expr | None:
    """Parse an analytical final_result string into an explicit y(t) SymPy expression if possible."""
    cleaned = (final_result or "").strip()
    if not cleaned:
        return None
    if "Integral" in cleaned or "Piecewise" in cleaned or "RootOf" in cleaned:
        return None

    # Strip leading 'y(t) = ' or 'y = '
    pattern = re.compile(
        rf"^{re.escape(dep_var)}\s*(?:\(\s*{re.escape(indep_var)}\s*\))?\s*=\s*(.+)$"
    )
    m = pattern.match(cleaned)
    rhs = m.group(1).strip() if m else cleaned

    # Reject implicit solutions like 'x^2*y + 2*y^2 = 5'
    if "=" in rhs:
        return None

    t_sym = sp.Symbol(indep_var)
    try:
        expr = parse_safe_expression(
            rhs,
            target_variable=indep_var,
            allowed_variables={indep_var},
            evaluate=True,
        )
    except Exception:
        return None

    # Reject remaining integration constants or unrelated symbols
    if expr.free_symbols - {t_sym}:
        return None
    if expr.has(sp.Integral, sp.I, sp.zoo, sp.nan, sp.oo, -sp.oo, sp.AccumBounds):
        return None
    return expr


class AnalyticalComparisonService:
    """Provides optional exact analytical comparison via existing SolveProblemUseCase."""

    def __init__(self, analytical_use_case: SolveProblemUseCase) -> None:
        self._analytical_use_case = analytical_use_case

    def compare(
        self,
        request: NumericalODERequest,
        response: NumericalODEResponse,
    ) -> AnalyticalComparisonResult:
        if response.status != NumericalODEStatus.SUCCESS or not response.rows:
            return AnalyticalComparisonResult(
                available=False,
                notes="Không thể so sánh giải tích khi phép tính số chưa thành công.",
            )

        indep = normalize_variable_name(response.independent_var)
        dep = normalize_variable_name(response.dependent_var)
        eq_clean, _ = extract_interval_from_string(request.raw_equation.strip())
        if request.order == NumericalODEOrder.SECOND_ORDER:
            eq_clean, _, _, _ = extract_second_order_ics_from_string(eq_clean)
        else:
            eq_clean, _ = extract_initial_condition_from_string(eq_clean)
        eq_clean = eq_clean.strip()

        candidate_requests: list[ProblemRequest] = []
        if request.order == NumericalODEOrder.FIRST_ORDER:
            ic_str = f"{dep}({request.t0.strip()}) = {request.y0.strip()}"
            for pt in (
                ProblemType.ODE_FIRST_ORDER_LINEAR,
                ProblemType.ODE_SEPARABLE,
                ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
            ):
                candidate_requests.append(
                    ProblemRequest(
                        raw_input=eq_clean,
                        problem_type=pt,
                        target_variable=indep,
                        parameters={"initial_condition": ic_str},
                    )
                )
        else:
            v0_str = (request.v0 or "").strip()
            ic_str = f"{dep}({request.t0.strip()}) = {request.y0.strip()}, {dep}'({request.t0.strip()}) = {v0_str}"
            if response.is_euler_cauchy_transformed:
                branch_hint = f"{indep} > 0" if response.t0 > 0 else f"{indep} < 0"
                raw_ec = f"{eq_clean}, {branch_hint}"
                candidate_requests.append(
                    ProblemRequest(
                        raw_input=raw_ec,
                        problem_type=ProblemType.ODE_EULER_CAUCHY,
                        target_variable=indep,
                        parameters={
                            "expected_classification": "EULER_CAUCHY",
                            "problem_mode": "CAUCHY_IVP",
                            "initial_condition": ic_str,
                        },
                    )
                )
            else:
                candidate_requests.append(
                    ProblemRequest(
                        raw_input=eq_clean,
                        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
                        target_variable=indep,
                        parameters={
                            "problem_mode": "CAUCHY_IVP",
                            "initial_condition": ic_str,
                        },
                    )
                )

        matched_resp: SolutionResponse | None = None
        matched_expr: sp.Expr | None = None
        matched_deriv_expr: sp.Expr | None = None
        t_sym = sp.Symbol(indep)

        for cand_req in candidate_requests:
            try:
                ana_resp = self._analytical_use_case.execute(cand_req, timeout_seconds=3.0)
            except Exception:
                continue

            if ana_resp.status != SolutionStatus.SUCCESS:
                continue
            if ana_resp.verification.status not in _TRUSTED_VERIFICATION_STATUSES:
                continue

            expr = _extract_explicit_expr(ana_resp.final_result, indep, dep)
            if expr is None:
                continue

            # Sanity-check initial condition consistency before accepting comparison
            try:
                exact_fn = compile_safe_real_evaluator(expr, (t_sym,))
                y0_exact = exact_fn(response.t0)
                if abs(y0_exact - response.y0) > 1e-6:
                    continue
                d_expr_cand: sp.Expr | None = None
                if request.order == NumericalODEOrder.SECOND_ORDER and response.v0 is not None:
                    d_expr_cand = sp.simplify(sp.diff(expr, t_sym))
                    d_fn = compile_safe_real_evaluator(d_expr_cand, (t_sym,))
                    if abs(d_fn(response.t0) - response.v0) > 1e-5:
                        continue
            except Exception:
                continue

            matched_resp = ana_resp
            matched_expr = expr
            matched_deriv_expr = d_expr_cand
            break

        if matched_resp is None or matched_expr is None:
            return AnalyticalComparisonResult(
                available=False,
                notes=(
                    "Bộ giải giải tích hiện không có nghiệm hiển đóng đã kiểm chứng cho bài toán này; "
                    "hiển thị kết quả xấp xỉ số độc lập."
                ),
            )

        exact_fn = compile_safe_real_evaluator(matched_expr, (t_sym,))
        exact_v_fn: Callable[..., float] | None = None
        if request.order == NumericalODEOrder.SECOND_ORDER and matched_deriv_expr is not None:
            try:
                exact_v_fn = compile_safe_real_evaluator(matched_deriv_expr, (t_sym,))
            except Exception:
                return AnalyticalComparisonResult(
                    available=False,
                    notes="Không thể định giá đạo hàm nghiệm giải tích trên khoảng tính toán.",
                )

        # Compile RHS evaluator for unnormalized one-step local defect δ_{n+1}
        rhs_eval: Callable[..., float] | None = None
        try:
            parsed_ode = parse_numerical_ode_equation(
                request.raw_equation,
                order=request.order,
                indep_var=indep,
                dep_var=dep,
            )
            if request.order == NumericalODEOrder.FIRST_ORDER:
                rhs_eval = compile_safe_real_evaluator(
                    parsed_ode.rhs_expr, (parsed_ode.indep_var, parsed_ode.dep_var)
                )
            else:
                rhs_eval = compile_safe_real_evaluator(
                    parsed_ode.rhs_expr, (parsed_ode.indep_var, parsed_ode.dep_var, parsed_ode.yp_sym)
                )
        except Exception:
            rhs_eval = None

        points: list[AnalyticalComparisonPoint] = []
        max_err_y = 0.0
        max_err_v: float | None = 0.0 if exact_v_fn is not None else None
        max_def_y: float | None = None
        max_def_v: float | None = None
        prev_t: float | None = None
        prev_y_ex: float | None = None
        prev_v_ex: float | None = None

        for row in response.rows:
            try:
                y_ex = exact_fn(row.t)
            except Exception:
                return AnalyticalComparisonResult(
                    available=False,
                    notes="Không thể định giá nghiệm giải tích tại một số điểm lưới.",
                )
            if not math.isfinite(y_ex):
                return AnalyticalComparisonResult(
                    available=False,
                    notes="Nghiệm giải tích không hữu hạn trên khoảng tính toán.",
                )

            v_num: float | None = row.v
            v_ex: float | None = None
            err_v: float | None = None
            if exact_v_fn is not None and v_num is not None:
                try:
                    v_ex = exact_v_fn(row.t)
                except Exception:
                    return AnalyticalComparisonResult(
                        available=False,
                        notes="Không thể định giá đạo hàm nghiệm giải tích tại một số điểm lưới.",
                    )
                if not math.isfinite(v_ex):
                    return AnalyticalComparisonResult(
                        available=False,
                        notes="Đạo hàm nghiệm giải tích không hữu hạn trên khoảng tính toán.",
                    )
                err_v = abs(v_ex - v_num)
                if max_err_v is not None:
                    max_err_v = max(max_err_v, err_v)

            err_y = abs(y_ex - row.y)
            max_err_y = max(max_err_y, err_y)

            local_def_y: float | None = None
            local_def_v: float | None = None
            if prev_t is not None and prev_y_ex is not None:
                h_prev = row.t - prev_t
                if request.order == NumericalODEOrder.FIRST_ORDER and rhs_eval is not None:
                    try:
                        f_exact_prev = rhs_eval(prev_t, prev_y_ex)
                        cand_def = y_ex - prev_y_ex - h_prev * f_exact_prev
                        if math.isfinite(cand_def):
                            local_def_y = cand_def
                            max_def_y = abs(cand_def) if max_def_y is None else max(max_def_y, abs(cand_def))
                    except Exception:
                        local_def_y = None
                elif (
                    request.order == NumericalODEOrder.SECOND_ORDER
                    and v_ex is not None
                    and prev_v_ex is not None
                ):
                    try:
                        cand_def_y = y_ex - prev_y_ex - h_prev * prev_v_ex
                        if math.isfinite(cand_def_y):
                            local_def_y = cand_def_y
                            max_def_y = abs(cand_def_y) if max_def_y is None else max(max_def_y, abs(cand_def_y))
                    except Exception:
                        local_def_y = None
                    if rhs_eval is not None:
                        try:
                            f_exact_prev = rhs_eval(prev_t, prev_y_ex, prev_v_ex)
                            cand_def_v = v_ex - prev_v_ex - h_prev * f_exact_prev
                            if math.isfinite(cand_def_v):
                                local_def_v = cand_def_v
                                max_def_v = abs(cand_def_v) if max_def_v is None else max(max_def_v, abs(cand_def_v))
                        except Exception:
                            local_def_v = None

            points.append(
                AnalyticalComparisonPoint(
                    step_index=row.step_index,
                    t=row.t,
                    y_numerical=row.y,
                    y_exact=y_ex,
                    abs_error=err_y,
                    v_numerical=v_num,
                    v_exact=v_ex,
                    v_abs_error=err_v,
                    local_defect_y=local_def_y,
                    local_defect_v=local_def_v,
                )
            )
            prev_t = row.t
            prev_y_ex = y_ex
            prev_v_ex = v_ex

        exact_latex = f"{dep}({indep}) = {expr_to_latex(matched_expr)}"
        exact_deriv_str = (
            f"{dep}'({indep}) = {matched_deriv_expr}"
            if matched_deriv_expr is not None
            else ""
        )
        exact_deriv_latex = (
            f"{dep}'({indep}) = {expr_to_latex(matched_deriv_expr)}"
            if matched_deriv_expr is not None
            else ""
        )

        return AnalyticalComparisonResult(
            available=True,
            exact_expression_str=f"{dep}({indep}) = {matched_expr}",
            exact_latex=exact_latex,
            exact_derivative_str=exact_deriv_str,
            exact_derivative_latex=exact_deriv_latex,
            points=tuple(points),
            max_abs_error=max_err_y,
            final_abs_error=points[-1].abs_error if points else None,
            max_v_abs_error=max_err_v,
            final_v_abs_error=points[-1].v_abs_error if points else None,
            max_local_defect_y=max_def_y,
            final_local_defect_y=points[-1].local_defect_y if points else None,
            max_local_defect_v=max_def_v,
            final_local_defect_v=points[-1].local_defect_v if points else None,
            notes="Đã đối chiếu trực tiếp với nghiệm giải tích chính xác của hệ thống.",
        )

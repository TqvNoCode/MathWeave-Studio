"""First-order linear differential equation solver (Constant & Variable Coefficients)."""

from __future__ import annotations

import math
import time
import sympy as sp
from sympy.core.function import AppliedUndef

from math_app.application.dtos import (
    BranchSolution,
    ProblemRequest,
    SolutionResponse,
    SolutionStep,
    VerificationResult,
)
from math_app.application.ports.solver import Solver
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import DomainCompleteness, ProblemType, SolutionStatus, VerificationStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.input.ode_parser import ParsedODE, parse_ode_input
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.solvers.calculus.ode._real_calculus import (
    has_non_elementary_or_complex_branch,
    real_integrate_on_interval,
    unwrap_abs_on_interval,
)
from math_app.solvers.calculus.ode.domain_analyzer import (
    DomainAnalysisResult,
    ODEDomainAnalyzer,
    format_interval_latex,
)
from math_app.verification.calculus.ode_verifier import (
    ODEVerifier,
    _prove_symbolic_zero,
    derive_unique_branch_constant,
    evaluate_initial_point_domain,
    is_point_in_interval_interior,
)


def _is_finite_real_limit(val: sp.Expr | None) -> bool:
    """Check if a limit expression is a determinate, finite, real value."""
    if val is None:
        return False
    if isinstance(val, bool):
        return False
    if isinstance(val, (int, float)):
        return math.isfinite(val)
    if isinstance(val, complex):
        return False
    has_fn = getattr(val, "has", None)
    if callable(has_fn) and has_fn(
        sp.AccumBounds,
        sp.Limit,
        sp.zoo,
        sp.nan,
        sp.oo,
        -sp.oo,
        sp.I,
        sp.Order,
        sp.Integral,
        sp.Derivative,
        sp.Sum,
        sp.Product,
        sp.Subs,
        AppliedUndef,
    ):
        return False
    is_finite = getattr(val, "is_finite", None)
    if is_finite is False:
        return False
    is_real = getattr(val, "is_real", None)
    if is_real is not True:
        return False
    return True


class ODELinearSolver(Solver):
    """Solver for first-order linear ODEs: y' = ay + b and y' + p(t)y = g(t)."""

    def __init__(self, verifier: ODEVerifier | None = None) -> None:
        self.verifier = verifier or ODEVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type in (
            ProblemType.ODE_FIRST_ORDER_LINEAR,
            ProblemType.SOLVE_EQUATION,
        )

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        t0_start = time.perf_counter()
        raw = request.raw_input.strip()
        if not raw:
            raise InvalidInputError("Phương trình vi phân không được để trống (Equation cannot be empty).")

        # Parse and validate equation
        parsed: ParsedODE = parse_ode_input(
            raw,
            target_variable=request.target_variable,
            parameters=dict(request.parameters),
        )

        if not parsed.is_linear:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="linearity_check",
                    details="Phương trình không phải là phương trình vi phân tuyến tính cấp 1.",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=(
                    "Phương trình này phi tuyến tính theo y hoặc y' và không thể giải bằng thuật toán tuyến tính cấp 1 "
                    "(Nonlinear ODE is unsupported by ODELinearSolver).",
                ),
                execution_time_ms=elapsed,
            )

        var = parsed.independent_var
        dep_var = parsed.dependent_var
        p_expr = parsed.p_expr if parsed.p_expr is not None else sp.Integer(0)
        g_expr = parsed.g_expr if parsed.g_expr is not None else sp.Integer(0)
        c_sym = sp.Symbol("C")
        user_warnings: list[str] = []
        final_result_str: str | None = None
        is_singular_cauchy_compatible = False
        singular_required_y: sp.Expr | None = None
        singular_required_yp: sp.Expr | None = None

        # Validate initial point in domain of linear equation
        if parsed.initial_condition is not None:
            t0, y0 = parsed.initial_condition

            # Check if t0 is a singular point where leading coefficient vanishes
            is_singular_point = False
            if parsed.leading_coeffs:
                for lcoeff in parsed.leading_coeffs:
                    try:
                        lc_val = sp.simplify(lcoeff.subs([(var, t0)]))
                        if _prove_symbolic_zero(lc_val) or lc_val == 0:
                            is_singular_point = True
                            break
                    except Exception:
                        pass

            if is_singular_point:
                # In original equation a1(t)*y' + b0(t)*y = r(t):
                # At t = t0, a1(t0) = 0 => b0(t0)*y0 = r(t0)
                try:
                    lead_c = parsed.leading_coeffs[0]
                    b0_expr = sp.simplify(p_expr * lead_c)
                    r_expr = sp.simplify(g_expr * lead_c)
                    b0_t0 = sp.simplify(b0_expr.subs([(var, t0)]))
                    r_t0 = sp.simplify(r_expr.subs([(var, t0)]))

                    if b0_t0.has(sp.nan, sp.zoo):
                        try:
                            lim_b0_l = sp.limit(b0_expr, var, t0, dir="-")
                            lim_b0_r = sp.limit(b0_expr, var, t0, dir="+")
                            if lim_b0_l == lim_b0_r and _is_finite_real_limit(lim_b0_l):
                                b0_t0 = lim_b0_l
                        except Exception:
                            pass
                    if r_t0.has(sp.nan, sp.zoo):
                        try:
                            lim_r_l = sp.limit(r_expr, var, t0, dir="-")
                            lim_r_r = sp.limit(r_expr, var, t0, dir="+")
                            if lim_r_l == lim_r_r and _is_finite_real_limit(lim_r_l):
                                r_t0 = lim_r_l
                        except Exception:
                            pass

                    if not _is_finite_real_limit(b0_t0) or not _is_finite_real_limit(r_t0):
                        elapsed = (time.perf_counter() - t0_start) * 1000.0
                        return SolutionResponse(
                            status=SolutionStatus.UNVERIFIED,
                            verification=VerificationResult(
                                status=VerificationStatus.UNVERIFIED,
                                method="singular_cauchy_limit_classification",
                                details=(
                                    f"Hệ số phương trình vi phân gốc dao động hoặc không xác định tại điểm kỳ dị {var} = {t0} "
                                    f"(b0({t0}) = {b0_t0}, r({t0}) = {r_t0}). Không thể xác lập sự tồn tại nghiệm nối trơn C¹."
                                ),
                            ),
                            raw_input=request.raw_input,
                            canonical_input=parsed.canonical_eq,
                            final_result="",
                            final_latex="",
                            warnings=(
                                f"Hệ số phương trình vi phân dao động không hội tụ tại điểm kỳ dị {var} = {t0}; không thể kết luận nghiệm C1.",
                            ),
                            execution_time_ms=elapsed,
                        )
                    d_lead_c = sp.diff(lead_c, var).subs([(var, t0)])
                    d_b0 = sp.diff(b0_expr, var).subs([(var, t0)])
                    d_r = sp.diff(r_expr, var).subs([(var, t0)])

                    if not _prove_symbolic_zero(b0_t0):
                        # Subcase A: b0(t0) != 0 -> algebraic condition y(t0) = r(t0)/b0(t0)
                        singular_required_y = sp.simplify(r_t0 / b0_t0)
                        denom_yp = sp.simplify(d_lead_c + b0_t0)
                        if denom_yp != 0:
                            singular_required_yp = sp.simplify((d_r - d_b0 * singular_required_y) / denom_yp)
                    else:
                        # b0(t0) == 0.
                        # Original equation at t0 is a1(t0)*y'(t0) + b0(t0)*y(t0) = r(t0) => 0 = r(t0).
                        if not _prove_symbolic_zero(r_t0):
                            # Algebraic contradiction: 0 = r(t0) != 0 (e.g. t*y' = 1, y(0) = 5)
                            elapsed = (time.perf_counter() - t0_start) * 1000.0
                            return SolutionResponse(
                                status=SolutionStatus.INVALID_INPUT,
                                verification=VerificationResult(
                                    status=VerificationStatus.NOT_APPLICABLE,
                                    method="initial_point_domain_validation",
                                    details=(
                                        f"Tại điểm kỳ dị {var} = {t0}, hệ số dẫn {lead_c} triệt tiêu và b0({t0}) = 0 "
                                        f"nhưng vế phải r({t0}) = {r_t0} khác 0. Phương trình dẫn đến mâu thuẫn đại số 0 = {r_t0}; "
                                        f"không tồn tại nghiệm cổ điển thỏa mãn bài toán Cauchy."
                                    ),
                                ),
                                raw_input=request.raw_input,
                                canonical_input=parsed.canonical_eq,
                                final_result="",
                                final_latex="",
                                warnings=(
                                    f"Điều kiện ban đầu ({t0}, {y0}) không hợp lệ: Phương trình suy biến thành 0 = {r_t0} tại {var} = {t0}.",
                                ),
                                execution_time_ms=elapsed,
                            )
                        else:
                            # 0 = 0 (underdetermined identity at t0).
                            # Check whether normalized coefficients have finite limits (removable singularity)
                            try:
                                lim_p_left = sp.limit(p_expr, var, t0, dir="-")
                                lim_p_right = sp.limit(p_expr, var, t0, dir="+")
                                lim_g_left = sp.limit(g_expr, var, t0, dir="-")
                                lim_g_right = sp.limit(g_expr, var, t0, dir="+")
                            except Exception as e:
                                elapsed = (time.perf_counter() - t0_start) * 1000.0
                                return SolutionResponse(
                                    status=SolutionStatus.UNVERIFIED,
                                    verification=VerificationResult(
                                        status=VerificationStatus.UNVERIFIED,
                                        method="singular_cauchy_limit_classification",
                                        details=f"Không thể tính giới hạn hệ số chuẩn hóa tại điểm kỳ dị {var} = {t0}: {e}.",
                                    ),
                                    raw_input=request.raw_input,
                                    canonical_input=parsed.canonical_eq,
                                    final_result="",
                                    final_latex="",
                                    warnings=(
                                        f"Không thể tính giới hạn hệ số chuẩn hóa tại điểm kỳ dị {var} = {t0}.",
                                    ),
                                    execution_time_ms=elapsed,
                                )

                            # Check for oscillatory, indeterminate, or uncomputable limits
                            has_oscillatory = any(
                                lim.has(sp.AccumBounds, sp.Limit)
                                for lim in (lim_p_left, lim_p_right, lim_g_left, lim_g_right)
                            )
                            if has_oscillatory:
                                elapsed = (time.perf_counter() - t0_start) * 1000.0
                                return SolutionResponse(
                                    status=SolutionStatus.UNVERIFIED,
                                    verification=VerificationResult(
                                        status=VerificationStatus.UNVERIFIED,
                                        method="singular_cauchy_limit_classification",
                                        details=(
                                            f"Hệ số chuẩn hóa của phương trình vi phân có giới hạn dao động hoặc không xác định "
                                            f"tại điểm kỳ dị {var} = {t0} (lim p = [{lim_p_left}, {lim_p_right}], "
                                            f"lim g = [{lim_g_left}, {lim_g_right}]). Không thể xác lập sự tồn tại nghiệm nối trơn C¹."
                                        ),
                                    ),
                                    raw_input=request.raw_input,
                                    canonical_input=parsed.canonical_eq,
                                    final_result="",
                                    final_latex="",
                                    warnings=(
                                        f"Hệ số chuẩn hóa dao động không hội tụ tại điểm kỳ dị {var} = {t0}; không thể kết luận nghiệm C1.",
                                    ),
                                    execution_time_ms=elapsed,
                                )

                            # Check for infinite limits / poles
                            has_pole = any(
                                lim.has(sp.zoo, sp.nan, sp.oo, -sp.oo)
                                for lim in (lim_p_left, lim_p_right, lim_g_left, lim_g_right)
                            )
                            if has_pole:
                                elapsed = (time.perf_counter() - t0_start) * 1000.0
                                return SolutionResponse(
                                    status=SolutionStatus.INVALID_INPUT,
                                    verification=VerificationResult(
                                        status=VerificationStatus.NOT_APPLICABLE,
                                        method="initial_point_domain_validation",
                                        details=(
                                            f"Điểm ban đầu {var} = {t0} là điểm kỳ dị không khử được của phương trình vi phân: "
                                            f"hệ số dẫn {lead_c} triệt tiêu và hệ số chuẩn hóa tiến tới vô cực."
                                        ),
                                    ),
                                    raw_input=request.raw_input,
                                    canonical_input=parsed.canonical_eq,
                                    final_result="",
                                    final_latex="",
                                    warnings=(
                                        f"Điều kiện ban đầu ({t0}, {y0}) không hợp lệ: Điểm ban đầu {var} = {t0} là điểm kỳ dị cực điểm của hệ số chuẩn hóa.",
                                    ),
                                    execution_time_ms=elapsed,
                                )

                            # Check if all one-sided limits are finite real numbers
                            if (
                                _is_finite_real_limit(lim_p_left)
                                and _is_finite_real_limit(lim_p_right)
                                and _is_finite_real_limit(lim_g_left)
                                and _is_finite_real_limit(lim_g_right)
                            ):
                                p_match = _prove_symbolic_zero(sp.simplify(lim_p_left - lim_p_right))
                                g_match = _prove_symbolic_zero(sp.simplify(lim_g_left - lim_g_right))
                                if p_match and g_match:
                                    # Removable singularity with matching two-sided limits: any y0 is compatible!
                                    singular_required_y = y0
                                    # lim y'(t) = lim (g(t) - p(t)*y(t)) = lim_g - lim_p * y0
                                    singular_required_yp = sp.simplify(lim_g_left - lim_p_left * y0)
                                else:
                                    # Unequal one-sided limits: cannot infer unique derivative or C1 extension
                                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                                    return SolutionResponse(
                                        status=SolutionStatus.UNVERIFIED,
                                        verification=VerificationResult(
                                            status=VerificationStatus.UNVERIFIED,
                                            method="singular_cauchy_limit_classification",
                                            details=(
                                                f"Giới hạn một phía của hệ số chuẩn hóa tại điểm kỳ dị {var} = {t0} không trùng khớp: "
                                                f"lim p- = {lim_p_left} != lim p+ = {lim_p_right} hoặc "
                                                f"lim g- = {lim_g_left} != lim g+ = {lim_g_right}. "
                                                f"Đạo hàm một phía không tương thích; không thể mở rộng trơn C¹."
                                            ),
                                        ),
                                        raw_input=request.raw_input,
                                        canonical_input=parsed.canonical_eq,
                                        final_result="",
                                        final_latex="",
                                        warnings=(
                                            "Giới hạn hai phía của hệ số chuẩn hóa tại điểm kỳ dị không khớp nhau; không thể xác lập nghiệm trơn C1.",
                                        ),
                                        execution_time_ms=elapsed,
                                    )
                            else:
                                elapsed = (time.perf_counter() - t0_start) * 1000.0
                                return SolutionResponse(
                                    status=SolutionStatus.UNVERIFIED,
                                    verification=VerificationResult(
                                        status=VerificationStatus.UNVERIFIED,
                                        method="singular_cauchy_limit_classification",
                                        details=(
                                            f"Giới hạn hệ số chuẩn hóa tại điểm kỳ dị {var} = {t0} không phải là số thực hữu hạn: "
                                            f"p: [{lim_p_left}, {lim_p_right}], g: [{lim_g_left}, {lim_g_right}]."
                                        ),
                                    ),
                                    raw_input=request.raw_input,
                                    canonical_input=parsed.canonical_eq,
                                    final_result="",
                                    final_latex="",
                                    warnings=(
                                        "Giới hạn hệ số chuẩn hóa tại điểm kỳ dị không xác định hoặc không thực.",
                                    ),
                                    execution_time_ms=elapsed,
                                )
                except Exception as exc:
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    return SolutionResponse(
                        status=SolutionStatus.UNVERIFIED,
                        verification=VerificationResult(
                            status=VerificationStatus.UNVERIFIED,
                            method="singular_cauchy_limit_classification",
                            details=(
                                f"Không thể hoàn tất phân loại giới hạn tại điểm kỳ dị {var} = {t0}: {exc}."
                            ),
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        warnings=(
                            f"Không thể xác minh điều kiện kỳ dị tại {var} = {t0}; giữ trạng thái chưa kiểm chứng.",
                        ),
                        execution_time_ms=elapsed,
                    )

                if singular_required_y is not None and not _prove_symbolic_zero(y0 - singular_required_y):
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    return SolutionResponse(
                        status=SolutionStatus.INVALID_INPUT,
                        verification=VerificationResult(
                            status=VerificationStatus.NOT_APPLICABLE,
                            method="initial_point_domain_validation",
                            details=(
                                f"Tại điểm kỳ dị {var} = {t0}, hệ số dẫn triệt tiêu. "
                                f"Phương trình vi phân gốc rút gọn thành điều kiện đại số {dep_var}({t0}) = {singular_required_y}. "
                                f"Giá trị ban đầu {dep_var}({t0}) = {y0} mâu thuẫn với phương trình; "
                                f"không tồn tại nghiệm cổ điển (classical solution) thỏa mãn bài toán Cauchy."
                            ),
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        warnings=(
                            f"Điều kiện ban đầu ({t0}, {y0}) không hợp lệ: Điểm ban đầu {var} = {t0} là điểm kỳ dị của hệ số dẫn. "
                            f"Phương trình vi phân gốc rút gọn thành điều kiện đại số {dep_var}({t0}) = {singular_required_y}. "
                            f"Do {dep_var}({t0}) = {y0} khác {singular_required_y}, không tồn tại nghiệm cổ điển (classical solution).",
                        ),
                        execution_time_ms=elapsed,
                    )
                elif singular_required_y is not None and _prove_symbolic_zero(y0 - singular_required_y):
                    is_singular_cauchy_compatible = True
                    user_warnings.append(
                        f"Điểm ban đầu {var} = {t0} là điểm kỳ dị của hệ số dẫn. "
                        f"Giá trị ban đầu {dep_var}({t0}) = {y0} thỏa mãn điều kiện đại số suy biến tại điểm kỳ dị, "
                        f"nhưng định lý Cauchy cổ điển (Picard-Lindelöf) không áp dụng tại điểm kỳ dị."
                    )

            src_constraints = getattr(parsed, "original_domain_constraints", ())
            if not is_singular_cauchy_compatible:
                linear_ic_checks = (
                    (
                        None,
                        src_constraints,
                        f"Điểm ban đầu ({t0}, {y0}) vi phạm điều kiện xác định ban đầu: {{err}}",
                        f"Điều kiện ban đầu ({t0}, {y0}) không hợp lệ: {{err}}",
                    ),
                    (
                        p_expr,
                        (),
                        f"Điểm ban đầu t0 = {t0} là điểm kỳ dị của hệ số p({var}) = {p_expr}: {{err}}",
                        f"Điều kiện ban đầu ({t0}, {y0}) không hợp lệ: Hệ số p({var}) = {p_expr} "
                        f"có điểm kỳ dị hoặc không xác định tại {var} = {t0} ({{err}}).",
                    ),
                    (
                        g_expr,
                        (),
                        f"Điểm ban đầu t0 = {t0} là điểm kỳ dị của hàm tự do g({var}) = {g_expr}: {{err}}",
                        f"Điều kiện ban đầu ({t0}, {y0}) không hợp lệ: Hàm tự do g({var}) = {g_expr} "
                        f"có điểm kỳ dị hoặc không xác định tại {var} = {t0} ({{err}}).",
                    ),
                )
                unknown_ic: tuple[str, str] | None = None
                for check_expr, check_constraints, det_tpl, warn_tpl in linear_ic_checks:
                    dom_stat, dom_err = evaluate_initial_point_domain(
                        check_expr,
                        var,
                        dep_var,
                        t0,
                        y0,
                        original_denominators=parsed.original_denominators,
                        leading_coeffs=parsed.leading_coeffs,
                        source_constraints=check_constraints,
                    )
                    if dom_stat == "invalid":
                        elapsed = (time.perf_counter() - t0_start) * 1000.0
                        return SolutionResponse(
                            status=SolutionStatus.INVALID_INPUT,
                            verification=VerificationResult(
                                status=VerificationStatus.NOT_APPLICABLE,
                                method="initial_point_domain_validation",
                                details=det_tpl.format(err=dom_err),
                            ),
                            raw_input=request.raw_input,
                            canonical_input=parsed.canonical_eq,
                            final_result="",
                            final_latex="",
                            warnings=(warn_tpl.format(err=dom_err),),
                            execution_time_ms=elapsed,
                        )
                    if dom_stat == "unknown" and unknown_ic is None:
                        unknown_ic = (det_tpl.format(err=dom_err), warn_tpl.format(err=dom_err))

                if unknown_ic is not None:
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    return SolutionResponse(
                        status=SolutionStatus.UNVERIFIED,
                        verification=VerificationResult(
                            status=VerificationStatus.UNVERIFIED,
                            method="initial_condition_domain_unverified",
                            details=unknown_ic[0],
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        warnings=(unknown_ic[1],),
                        execution_time_ms=elapsed,
                    )
            else:
                orig_stat, orig_err = evaluate_initial_point_domain(
                    None,
                    var,
                    dep_var,
                    t0,
                    y0,
                    original_denominators=parsed.original_denominators,
                    leading_coeffs=(),
                    source_constraints=src_constraints,
                )
                if orig_stat == "invalid":
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    return SolutionResponse(
                        status=SolutionStatus.INVALID_INPUT,
                        verification=VerificationResult(
                            status=VerificationStatus.NOT_APPLICABLE,
                            method="initial_point_domain_validation",
                            details=f"Điểm ban đầu ({t0}, {y0}) vi phạm điều kiện xác định ban đầu: {orig_err}",
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        warnings=(f"Điều kiện ban đầu ({t0}, {y0}) không hợp lệ: {orig_err}",),
                        execution_time_ms=elapsed,
                    )
                if orig_stat == "unknown":
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    return SolutionResponse(
                        status=SolutionStatus.UNVERIFIED,
                        verification=VerificationResult(
                            status=VerificationStatus.UNVERIFIED,
                            method="initial_condition_domain_unverified",
                            details=f"Không thể xác nhận điều kiện ban đầu ({t0}, {y0}) thuộc miền xác định: {orig_err}",
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        warnings=(f"Không thể xác nhận điều kiện ban đầu ({t0}, {y0}): {orig_err}",),
                        execution_time_ms=elapsed,
                    )

        steps: list[SolutionStep] = []
        step_num = 1
        domain_restrictions: list[str] = []
        domain_analysis: DomainAnalysisResult | None = None
        branch_solutions_list: list[BranchSolution] = []
        final_result_str: str | None = None

        # =========================================================================
        # Case 1: First-order Linear ODE with Constant Coefficients (Phase A)
        # Equation: y' = a*y + b
        # =========================================================================
        if parsed.is_constant_coeff and parsed.a_coeff is not None and parsed.b_coeff is not None:
            a_val = parsed.a_coeff
            b_val = parsed.b_coeff

            # Step 1: Standard form identification
            eq_latex = f"\\frac{{d{dep_var}}}{{d{var}}} = {expr_to_latex(a_val * sp.Symbol(str(dep_var)) + b_val)}"
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Nhận dạng dạng phương trình",
                    title="Nhận dạng phương trình vi phân tuyến tính hệ số hằng",
                    description=(
                        f"Phương trình đưa về dạng chuẩn $y' = a\\,y + b$ với hệ số hằng "
                        f"$a = {expr_to_latex(a_val)}$ và $b = {expr_to_latex(b_val)}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=parsed.canonical_eq,
                        expression_after=f"y' = {a_val}*y + {b_val}",
                        latex_before=expr_to_latex(parsed.lhs_expr) + " = " + expr_to_latex(parsed.rhs_expr),
                        latex_after=eq_latex,
                    ),
                )
            )
            step_num += 1

            # Subcase A1: a == 0 -> y' = b -> y(t) = b*t + C
            if a_val == 0:
                gen_sol = b_val * var + c_sym
                gen_sol_latex = (
                    f"{dep_var}({var}) = {expr_to_latex(b_val * var)} + C" if b_val != 0 else f"{dep_var}({var}) = C"
                )

                steps.append(
                    SolutionStep(
                        step_number=step_num,
                        rule_name="Tích phân hai vế",
                        title="Tích phân trực tiếp khi hệ số a = 0",
                        description=(
                            f"Vì $a = 0$, phương trình trở thành $y' = {expr_to_latex(b_val)}$. "
                            f"Tích phân hai vế theo biến ${var}$ thu được nghiệm tổng quát $y = {expr_to_latex(b_val)}\\,{var} + C$."
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"y' = {b_val}",
                            expression_after=f"y({var}) = {gen_sol}",
                            latex_before=f"\\frac{{d{dep_var}}}{{d{var}}} = {expr_to_latex(b_val)}",
                            latex_after=gen_sol_latex,
                        ),
                    )
                )
                step_num += 1

                final_sol = gen_sol
                final_latex_sol = gen_sol_latex

                # Initial condition handling
                if parsed.initial_condition is not None:
                    t0, y0 = parsed.initial_condition
                    c_val = sp.simplify(y0 - b_val * t0)
                    part_sol = sp.simplify(b_val * var + c_val)
                    part_sol_latex = f"{dep_var}({var}) = {expr_to_latex(part_sol)}"

                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name="Áp dụng điều kiện ban đầu",
                            title="Xác định hằng số C từ điều kiện ban đầu",
                            description=(
                                f"Thay {var} = {t0} và {dep_var} = {y0} vào nghiệm tổng quát: "
                                f"{y0} = {b_val}*({t0}) + C => C = {c_val}."
                            ),
                            content=ExpressionStepContent(
                                expression_before=f"{y0} = {b_val}*{t0} + C",
                                expression_after=f"C = {c_val}",
                                latex_before=f"{expr_to_latex(y0)} = {expr_to_latex(b_val)}\\cdot {expr_to_latex(t0)} + C",
                                latex_after=f"C = {expr_to_latex(c_val)}",
                            ),
                        )
                    )
                    step_num += 1

                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name="Nghiệm riêng",
                            title="Nghiệm riêng của bài toán Cauchy (IVP)",
                            description="Thế giá trị hằng số C vừa tìm được vào nghiệm tổng quát để kết luận nghiệm riêng.",
                            content=ExpressionStepContent(
                                expression_before=f"y({var}) = {gen_sol}",
                                expression_after=f"y({var}) = {part_sol}",
                                latex_before=gen_sol_latex,
                                latex_after=part_sol_latex,
                            ),
                        )
                    )
                    final_sol = part_sol
                    final_latex_sol = part_sol_latex

            # Subcase A2: a != 0 -> y(t) = C*exp(a*t) - b/a
            else:
                # Equilibrium solution: y' = 0 => y_eq = -b/a
                y_eq = sp.simplify(-b_val / a_val)
                y_eq_latex = f"{dep_var}_{{eq}} = {expr_to_latex(y_eq)}"

                steps.append(
                    SolutionStep(
                        step_number=step_num,
                        rule_name="Nghiệm cân bằng",
                        title="Xác định nghiệm cân bằng (Equilibrium Solution)",
                        description=(
                            f"Cho y' = 0 ta có {a_val}*y + {b_val} = 0 => nghiệm cân bằng duy nhất y = {y_eq}."
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"{a_val}*y + {b_val} = 0",
                            expression_after=f"y_eq = {y_eq}",
                            latex_before=f"{expr_to_latex(a_val)}{dep_var} + {expr_to_latex(b_val)} = 0",
                            latex_after=y_eq_latex,
                        ),
                    )
                )
                step_num += 1

                if a_val.is_symbol:
                    domain_restrictions.append(f"Giả định tham số {a_val} khác 0 để tránh phép chia cho 0.")

                # Integrating factor for y' - a*y = b: mu(t) = exp(-a*t)
                mu_expr = sp.exp(-a_val * var)
                gen_sol = sp.simplify(c_sym * sp.exp(a_val * var) - b_val / a_val)
                gen_sol_latex = f"{dep_var}({var}) = {expr_to_latex(gen_sol)}"

                steps.append(
                    SolutionStep(
                        step_number=step_num,
                        rule_name="Thừa số tích phân",
                        title="Tìm thừa số tích phân và dẫn xuất nghiệm tổng quát",
                        description=(
                            f"Đưa phương trình về dạng $y' - {expr_to_latex(a_val)}y = {expr_to_latex(b_val)}$. "
                            f"Thừa số tích phân là $\\mu({var}) = e^{{\\int (-{expr_to_latex(a_val)})\\,d{var}}} = {expr_to_latex(mu_expr)}$. "
                            f"Nhân hai vế và tích phân suy ra nghiệm tổng quát: $y({var}) = {expr_to_latex(gen_sol)}$."
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"y' - {a_val}*y = {b_val}",
                            expression_after=f"y({var}) = {gen_sol}",
                            latex_before=f"\\frac{{d{dep_var}}}{{d{var}}} - {expr_to_latex(a_val)}{dep_var} = {expr_to_latex(b_val)}",
                            latex_after=gen_sol_latex,
                        ),
                    )
                )
                step_num += 1

                final_sol = gen_sol
                final_latex_sol = gen_sol_latex

                # Initial condition handling
                if parsed.initial_condition is not None:
                    t0, y0 = parsed.initial_condition
                    # y0 = C*exp(a*t0) - b/a => C = (y0 + b/a)*exp(-a*t0)
                    c_val = sp.simplify((y0 + b_val / a_val) * sp.exp(-a_val * t0))
                    part_sol = sp.simplify((y0 + b_val / a_val) * sp.exp(a_val * (var - t0)) - b_val / a_val)
                    part_sol_latex = f"{dep_var}({var}) = {expr_to_latex(part_sol)}"

                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name="Áp dụng điều kiện ban đầu",
                            title="Xác định hằng số C từ điều kiện ban đầu",
                            description=(
                                f"Thay {var} = {t0} và {dep_var} = {y0} vào nghiệm tổng quát: "
                                f"{y0} = C*exp({a_val}*{t0}) - {b_val}/{a_val} => C = {c_val}."
                            ),
                            content=ExpressionStepContent(
                                expression_before=f"{y0} = C*exp({a_val}*{t0}) - {b_val}/{a_val}",
                                expression_after=f"C = {c_val}",
                                latex_before=f"{expr_to_latex(y0)} = {expr_to_latex(sp.simplify(c_sym * sp.exp(a_val * t0) - b_val / a_val))}",
                                latex_after=f"C = {expr_to_latex(c_val)}",
                            ),
                        )
                    )
                    step_num += 1

                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name="Nghiệm riêng",
                            title="Nghiệm riêng của bài toán Cauchy (IVP)",
                            description="Thế giá trị hằng số C cụ thể vào nghiệm tổng quát để thu được nghiệm riêng duy nhất.",
                            content=ExpressionStepContent(
                                expression_before=f"y({var}) = {gen_sol}",
                                expression_after=f"y({var}) = {part_sol}",
                                latex_before=gen_sol_latex,
                                latex_after=part_sol_latex,
                            ),
                        )
                    )
                    final_sol = part_sol
                    final_latex_sol = part_sol_latex

        # =========================================================================
        # Case 2: First-order Linear ODE with Variable Coefficients (Phase B)
        # Equation: y' + p(t)*y = g(t)
        # =========================================================================
        else:
            # Check leading coefficient
            lead_coeff_expr = None
            if parsed.leading_coeffs:
                for lc in parsed.leading_coeffs:
                    if lc != 1 and lc != -1:
                        lead_coeff_expr = lc
                        break

            # Run generic ODE domain and singular point analysis
            domain_analysis = ODEDomainAnalyzer.analyze_first_order_ode(
                original_lhs=parsed.lhs_expr,
                original_rhs=parsed.rhs_expr,
                leading_coeff=lead_coeff_expr,
                p_expr=p_expr,
                g_expr=g_expr,
                var=var,
                dep_var=dep_var if isinstance(dep_var, sp.Symbol) else sp.Symbol(str(dep_var)),
            )
            for restr in domain_analysis.domain_restrictions:
                if restr not in domain_restrictions:
                    domain_restrictions.append(restr)

            lead_coeff_desc = ""
            if lead_coeff_expr is not None:
                lead_latex = expr_to_latex(lead_coeff_expr)
                domain_transition = ""
                if domain_analysis.original_domain != domain_analysis.normalized_domain:
                    domain_transition = (
                        f" Phương trình gốc xác định trên ${domain_analysis.original_domain_latex}$. "
                        f"Sau khi chia cho $({lead_latex})$, phương trình dạng chuẩn tắc được xét trên ${domain_analysis.normalized_domain_latex}$."
                    )
                lead_coeff_desc = f"Chia cả hai vế cho $({lead_latex})$, với điều kiện ${lead_latex} \\ne 0$, để đưa phương trình về dạng tuyến tính chuẩn.{domain_transition} "

            # Step 1: Identify p(t) and g(t)
            eq_std_latex = f"\\frac{{d{dep_var}}}{{d{var}}} + \\left( {expr_to_latex(p_expr)} \\right) {dep_var} = {expr_to_latex(g_expr)}"
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Xác định hệ số",
                    title="Nhận dạng dạng chuẩn y' + p(t)y = g(t)",
                    description=(
                        f"{lead_coeff_desc}"
                        f"Phương trình vi phân tuyến tính cấp 1 có hệ số $p({var}) = {expr_to_latex(p_expr)}$ "
                        f"và hàm tự do (forcing term) $g({var}) = {expr_to_latex(g_expr)}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=parsed.canonical_eq,
                        expression_after=f"y' + ({p_expr})*y = {g_expr}",
                        latex_before=expr_to_latex(parsed.lhs_expr) + " = " + expr_to_latex(parsed.rhs_expr),
                        latex_after=eq_std_latex,
                    ),
                )
            )
            step_num += 1

            # Step 2: Compute integrating factor mu(t) = exp(int(p(t) dt))
            is_mu_unevaluated = False
            int_p: sp.Expr | None = None
            if not p_expr.has(sp.log, sp.polylog, sp.meijerg):
                try:
                    int_cand = sp.integrate(p_expr, var)
                    if not int_cand.has(sp.polylog, sp.meijerg, sp.Piecewise, sp.Integral):
                        int_p = int_cand
                except Exception:
                    int_p = None

            if int_p is None:
                is_mu_unevaluated = True
                int_p = sp.Integral(p_expr, var)
                mu_expr = sp.exp(int_p)
                mu_latex = f"\\mu({var}) = e^{{\\int \\left( {expr_to_latex(p_expr)} \\right) d{var}}}"
                user_warnings.append(
                    f"Tích phân của hệ số p({var}) không có nguyên hàm biểu diễn dưới dạng hàm sơ cấp đóng. "
                    "Thừa số tích phân được bảo toàn dưới dạng tích phân giải tích chuẩn tắc."
                )
                step_2_desc = (
                    f"Tính thừa số tích phân theo công thức $\\mu({var}) = e^{{\\int p({var})\\,d{var}}}$: "
                    f"Do $\\int p({var})\\,d{var}$ không có nguyên hàm sơ cấp, thừa số tích phân được xác định dưới dạng: "
                    f"${mu_latex}$."
                )
            else:
                mu_expr = sp.simplify(sp.exp(int_p))
                mu_latex = f"\\mu({var}) = e^{{\\int \\left( {expr_to_latex(p_expr)} \\right) d{var}}} = {expr_to_latex(mu_expr)}"
                step_2_desc = (
                    f"Tính thừa số tích phân theo công thức $\\mu({var}) = e^{{\\int p({var})\\,d{var}}}$: "
                    f"$\\int ({expr_to_latex(p_expr)})\\,d{var} = {expr_to_latex(int_p)} \\implies \\mu({var}) = {expr_to_latex(mu_expr)}$."
                )

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Thừa số tích phân",
                    title="Tính thừa số tích phân \\mu(t)",
                    description=step_2_desc,
                    content=ExpressionStepContent(
                        expression_before=f"int({p_expr}) d{var} = {int_p}",
                        expression_after=f"mu({var}) = {mu_expr}",
                        latex_before=f"\\int \\left( {expr_to_latex(p_expr)} \\right) d{var} = {expr_to_latex(int_p)}",
                        latex_after=mu_latex,
                    ),
                )
            )
            step_num += 1

            # Step 3: Multiply both sides by mu(t)
            if is_mu_unevaluated:
                lhs_mult = f"\\mu({var}) \\frac{{d{dep_var}}}{{d{var}}} + \\mu({var}) p({var}) {dep_var}"
                rhs_mult = f"\\mu({var}) \\left( {expr_to_latex(g_expr)} \\right)"
                expr_after_step3 = f"mu({var})*y' + mu({var})*({p_expr})*y = mu({var})*({g_expr})"
            else:
                lhs_mult = f"\\left( {expr_to_latex(mu_expr)} \\right) \\frac{{d{dep_var}}}{{d{var}}} + \\left( {expr_to_latex(sp.simplify(mu_expr * p_expr))} \\right) {dep_var}"
                rhs_mult = expr_to_latex(sp.simplify(mu_expr * g_expr))
                expr_after_step3 = (
                    f"({mu_expr})*y' + ({sp.simplify(mu_expr * p_expr)})*y = {sp.simplify(mu_expr * g_expr)}"
                )

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Nhân thừa số tích phân",
                    title="Nhân hai vế của phương trình với thừa số tích phân",
                    description=(f"Nhân hai vế của phương trình vi phân với $\\mu({var}) = {expr_to_latex(mu_expr)}$."),
                    content=ExpressionStepContent(
                        expression_before=f"y' + ({p_expr})*y = {g_expr}",
                        expression_after=expr_after_step3,
                        latex_before=eq_std_latex,
                        latex_after=f"{lhs_mult} = {rhs_mult}",
                    ),
                )
            )
            step_num += 1

            # Step 4: Product rule transformation
            prod_lhs_latex = (
                f"\\frac{{d}}{{d{var}}} \\left[ \\mu({var}) \\,{dep_var} \\right]"
                if is_mu_unevaluated
                else f"\\frac{{d}}{{d{var}}} \\left[ \\left( {expr_to_latex(mu_expr)} \\right) {dep_var} \\right]"
            )
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Quy tắc đạo hàm của tích (ODE)",
                    title="Biến đổi vế trái theo quy tắc đạo hàm của tích",
                    description=(
                        f"Theo quy tắc đạo hàm của tích, $\\frac{{d}}{{d{var}}}[\\mu({var})\\,y] = \\mu\\,y' + \\mu'\\,y$. "
                        f"Vì $\\mu' = \\mu\\,p({var})$, vế trái chính là đạo hàm $\\frac{{d}}{{d{var}}}\\left[\\mu({var})\\,{dep_var}\\right]$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=expr_after_step3,
                        expression_after=f"d/d{var}[mu({var})*y] = mu({var})*({g_expr})"
                        if is_mu_unevaluated
                        else f"d/d{var}[({mu_expr})*y] = {sp.simplify(mu_expr * g_expr)}",
                        latex_before=f"{lhs_mult} = {rhs_mult}",
                        latex_after=f"{prod_lhs_latex} = {rhs_mult}",
                    ),
                )
            )
            step_num += 1

            # Step 5: Integrate both sides
            if is_mu_unevaluated:
                rhs_integrand = mu_expr * g_expr
                is_rhs_unevaluated = True
                rhs_integral = sp.Integral(rhs_integrand, var)
                user_warnings.append(
                    f"Tích phân vế phải int(\\mu({var}) * g({var}) d{var}) không có nguyên hàm sơ cấp đóng. "
                    "Nghiệm tổng quát được bảo toàn dưới dạng tích phân giải tích chuẩn tắc."
                )
                integrated_latex = (
                    f"\\mu({var}) {dep_var} = C + \\int \\mu({var}) \\left( {expr_to_latex(g_expr)} \\right) d{var}"
                )
                step_5_desc = f"Tích phân hai vế: $\\mu({var})\\,{dep_var} = C + \\int \\mu({var}) \\left({expr_to_latex(g_expr)}\\right)\\,d{var}$."
            else:
                rhs_integrand = sp.simplify(mu_expr * g_expr)
                is_rhs_unevaluated = False
                rhs_integral = sp.integrate(rhs_integrand, var)
                if has_non_elementary_or_complex_branch(rhs_integral, rhs_integrand):
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    return SolutionResponse(
                        status=SolutionStatus.CANNOT_SOLVE,
                        verification=VerificationResult(
                            status=VerificationStatus.NOT_APPLICABLE,
                            method="integrating_factor",
                            details=f"Tích phân int(\u03bc({var}) * g({var}) d{var}) không thể biểu diễn dưới dạng hàm sơ cấp.",
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        warnings=(
                            f"Tích phân int(\u03bc({var}) * g({var}) d{var}) = int({rhs_integrand} d{var}) không có nguyên hàm sơ cấp "
                            "(Non-elementary integral on RHS).",
                        ),
                        execution_time_ms=elapsed,
                    )
                if not domain_analysis.is_disconnected and domain_analysis.connected_intervals:
                    single_iv = domain_analysis.connected_intervals[0]
                    real_rhs = real_integrate_on_interval(
                        rhs_integrand,
                        var,
                        (single_iv.start, single_iv.end),
                        source_expr=rhs_integrand,
                        sample_point=parsed.initial_condition[0] if parsed.initial_condition else None,
                    )
                    if real_rhs is not None:
                        rhs_integral = real_rhs
                integrated_latex = (
                    f"\\left( {expr_to_latex(mu_expr)} \\right) {dep_var} = {expr_to_latex(rhs_integral)} + C"
                )
                step_5_desc = f"Tích phân vế phải: $\\int ({expr_to_latex(rhs_integrand)})\\,d{var} = {expr_to_latex(rhs_integral)} + C$."

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Tích phân hai vế",
                    title="Lấy tích phân hai vế và bổ sung hằng số C",
                    description=step_5_desc,
                    content=ExpressionStepContent(
                        expression_before=f"d/d{var}[({mu_expr})*y] = {rhs_integrand}",
                        expression_after=f"({mu_expr})*y = {rhs_integral} + C",
                        latex_before=f"{prod_lhs_latex} = {rhs_mult}",
                        latex_after=integrated_latex,
                    ),
                )
            )
            step_num += 1

            # Step 6: Derive general solution
            branch_solutions_list = []
            branch_integrals: list[tuple[sp.Expr, sp.Expr] | None] = []

            if domain_analysis.is_disconnected:
                cases_latex_lines = []
                for idx, iv in enumerate(domain_analysis.connected_intervals, start=1):
                    low, high = iv.start, iv.end
                    c_k = sp.Symbol(f"C_{idx}")
                    int_latex = format_interval_latex(low, high)

                    # Check for singular points on boundaries of this interval
                    sing_notes = []
                    for spa in domain_analysis.singular_point_analyses:
                        if spa.point == low or spa.point == high:
                            y_s_ltx = (
                                expr_to_latex(spa.y_singular)
                                if spa.y_singular is not None
                                else "\\text{không xác định}"
                            )
                            yp_s_ltx = (
                                expr_to_latex(spa.yp_singular)
                                if spa.yp_singular is not None
                                else "\\text{không xác định}"
                            )
                            sing_notes.append(
                                f"Tại điểm kỳ dị {var} = {expr_to_latex(spa.point)}: y({expr_to_latex(spa.point)}) = {y_s_ltx}, "
                                f"y'({expr_to_latex(spa.point)}) = {yp_s_ltx}."
                            )
                    ext_details = " ".join(sing_notes) if sing_notes else None
                    ext_status = VerificationStatus.PARTIALLY_VERIFIED.value if sing_notes else None

                    if is_mu_unevaluated or is_rhs_unevaluated:
                        b_expr = (c_k + rhs_integral) / mu_expr
                        b_str = f"1/mu({var}) * [{c_k} + int(mu({var}) * ({g_expr}) d{var})]"
                        b_latex = rf"\frac{{1}}{{\mu({var})}} \left[ {c_k} + \int \mu({var}) \left( {expr_to_latex(g_expr)} \right) d{var} \right]"
                        branch_integrals.append(None)
                    else:
                        # Derive strictly real-domain branch antiderivatives on (low, high)
                        mu_iv = mu_expr
                        rhs_int_iv = rhs_integral
                        int_p_iv = real_integrate_on_interval(p_expr, var, (low, high), source_expr=p_expr)
                        if int_p_iv is not None:
                            mu_cand = unwrap_abs_on_interval(sp.simplify(sp.exp(int_p_iv)), var, (low, high))
                            if not has_non_elementary_or_complex_branch(mu_cand, p_expr):
                                rhs_cand_integrand = sp.simplify(mu_cand * g_expr)
                                rhs_cand = real_integrate_on_interval(
                                    rhs_cand_integrand, var, (low, high), source_expr=rhs_cand_integrand
                                )
                                if rhs_cand is not None:
                                    mu_iv = mu_cand
                                    rhs_int_iv = rhs_cand
                        b_expr = sp.simplify((rhs_int_iv + c_k) / mu_iv)
                        b_str = str(b_expr)
                        b_latex = expr_to_latex(b_expr)
                        branch_integrals.append((mu_iv, rhs_int_iv))

                    cases_latex_lines.append(rf"{b_latex}, & {var} \in I_{idx} = {int_latex}")

                    branch_solutions_list.append(
                        BranchSolution(
                            expression=b_expr,
                            solution_str=b_str,
                            solution_latex=b_latex,
                            branch_identity=f"Nhánh I_{idx} ({int_latex})",
                            integration_constant=c_k,
                            integration_constant_val=None,
                            domain_interval=(low, high),
                            domain_restrictions=(f"{var} \\in {int_latex}",),
                            extension_status=ext_status,
                            extension_details=ext_details,
                            left_open=iv.left_open,
                            right_open=iv.right_open,
                            domain_set=iv,
                            singular_exclusions=tuple(domain_analysis.singular_points),
                            initial_condition_status=None,
                        )
                    )

                cases_body = " \\\\\n".join(cases_latex_lines)
                if is_mu_unevaluated or is_rhs_unevaluated:
                    gen_sol_latex = (
                        rf"{dep_var}({var}) = \begin{{cases}} "
                        rf"{cases_body} "
                        rf"\end{{cases}}, \quad \mu({var}) = \exp\left(\int {expr_to_latex(p_expr)} \, d{var}\right)"
                    )
                    cases_str = ", ".join(
                        f"1/mu({var}) * [{b.integration_constant} + int(mu({var}) * ({g_expr}) d{var})] for {var} in {format_interval_latex(b.domain_interval[0], b.domain_interval[1])}"
                        for b in branch_solutions_list
                    )
                    final_result_str = f"{dep_var}({var}) = {{{cases_str}}}, mu({var}) = exp(int({p_expr} d{var}))"
                else:
                    gen_sol_latex = (
                        rf"{dep_var}({var}) = \begin{{cases}} "
                        rf"{cases_body} "
                        rf"\end{{cases}}"
                    )
                    cases_str = ", ".join(
                        f"{b.expression} for {var} in {format_interval_latex(b.domain_interval[0], b.domain_interval[1])}"
                        for b in branch_solutions_list
                    )
                    final_result_str = f"{dep_var}({var}) = {{{cases_str}}}"

                # Pedagogical description for disconnected domain
                const_symbols_str = ", ".join(f"C_{i}" for i in range(1, len(branch_solutions_list) + 1))
                sing_explanations = []
                for spa in domain_analysis.singular_point_analyses:
                    y_s_ltx = expr_to_latex(spa.y_singular) if spa.y_singular is not None else "\\text{không xác định}"
                    yp_s_ltx = (
                        expr_to_latex(spa.yp_singular) if spa.yp_singular is not None else "\\text{không xác định}"
                    )
                    sing_explanations.append(
                        f"Tại điểm kỳ dị ${var} = {expr_to_latex(spa.point)}$, phương trình ban đầu đòi hỏi giá trị nghiệm "
                        f"$y({expr_to_latex(spa.point)}) = {y_s_ltx}$ và đạo hàm $y'({expr_to_latex(spa.point)}) = {yp_s_ltx}$. "
                        f"Việc nối trơn các nhánh nghiệm đòi hỏi giới hạn từ hai phía khớp với giá trị này."
                    )
                sing_desc = (" " + " ".join(sing_explanations)) if sing_explanations else ""

                mu_factor_desc = (
                    f"$\\mu({var}) = \\exp\\left(\\int {expr_to_latex(p_expr)}\\,d{var}\\right)$"
                    if is_mu_unevaluated
                    else f"$\\mu({var}) = {expr_to_latex(mu_expr)}$"
                )
                step_6_desc = (
                    f"Chia hai vế cho thừa số tích phân {mu_factor_desc}. "
                    f"Do miền xác định của phương trình gồm {len(branch_solutions_list)} khoảng liên thông rời rạc "
                    f"$\\mathcal{{D}}_{{\\text{{norm}}}} = {domain_analysis.normalized_domain_latex}$, "
                    f"hằng số tích phân được chọn hoàn toàn độc lập ${const_symbols_str}$ trên từng khoảng.{sing_desc} "
                    f"Nghiệm tổng quát dưới dạng từng khúc (piecewise solution): $${gen_sol_latex}$$"
                )
                gen_sol = branch_solutions_list[0].expression
            else:
                if is_mu_unevaluated or is_rhs_unevaluated:
                    gen_sol = (c_sym + rhs_integral) / mu_expr
                    gen_sol_latex = (
                        f"{dep_var}({var}) = \\frac{{1}}{{\\mu({var})}} \\left[ C + \\int \\mu({var}) \\left( {expr_to_latex(g_expr)} \\right) d{var} \\right], "
                        f"\\quad \\mu({var}) = e^{{\\int \\left( {expr_to_latex(p_expr)} \\right) d{var}}}"
                    )
                    step_6_desc = (
                        f"Chia hai vế cho $\\mu({var})$ để thu được nghiệm tổng quát dạng tích phân giải tích: "
                        f"${gen_sol_latex}$."
                    )
                    final_result_str = (
                        f"{dep_var}({var}) = 1/mu({var}) * [C + int(mu({var}) * ({g_expr}) d{var})], "
                        f"mu({var}) = exp(int({p_expr} d{var}))"
                    )
                else:
                    gen_sol = sp.simplify((rhs_integral + c_sym) / mu_expr)
                    gen_sol_latex = f"{dep_var}({var}) = {expr_to_latex(gen_sol)}"
                    step_6_desc = (
                        f"Chia hai vế cho $\\mu({var}) = {expr_to_latex(mu_expr)}$ để thu được nghiệm tổng quát "
                        f"$y({var}) = {expr_to_latex(gen_sol)}$."
                    )
                    final_result_str = f"{dep_var}({var}) = {gen_sol}"

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Rút ra nghiệm tổng quát",
                    title="Rút ra nghiệm tổng quát y(t)",
                    description=step_6_desc,
                    content=ExpressionStepContent(
                        expression_before=f"({mu_expr})*y = {rhs_integral} + C",
                        expression_after=f"y({var}) = {gen_sol}",
                        latex_before=integrated_latex,
                        latex_after=gen_sol_latex,
                    ),
                )
            )
            step_num += 1

            final_sol = gen_sol
            final_latex_sol = gen_sol_latex

            # Step 7: Initial condition if given
            if parsed.initial_condition is not None:
                t0, y0 = parsed.initial_condition
                target_branch_idx = None

                if is_singular_cauchy_compatible:
                    # Case C: Singular Cauchy IVP with compatible initial value
                    # Do not anchor across singularity t = t0.
                    # Retain independent branches and analyze continuation conditions.
                    y_s_val = singular_required_y if singular_required_y is not None else y0
                    y_s_ltx = expr_to_latex(y_s_val)
                    yp_s_ltx = (
                        expr_to_latex(singular_required_yp)
                        if singular_required_yp is not None
                        else "\\text{không xác định}"
                    )

                    cond_step_desc = (
                        f"Tại điểm kỳ dị ${var} = {expr_to_latex(t0)}$ (hệ số dẫn triệt tiêu), phương trình vi phân gốc rút gọn "
                        f"thành điều kiện đại số: ${dep_var}({expr_to_latex(t0)}) = {y_s_ltx}$. "
                        f"Điều kiện ban đầu đã cho thỏa mãn điều kiện đại số này. "
                        f"Tuy nhiên, do ${var} = {expr_to_latex(t0)}$ là điểm kỳ dị, định lý Picard–Lindelöf không áp dụng; "
                        f"thừa số tích phân không thể neo tích phân xác định tại điểm kỳ dị (tích phân suy rộng tại cận dưới). "
                        f"Nghiệm tổng quát trên các nhánh độc lập được bảo toàn. "
                        f"Để tồn tại nghiệm nối trơn $C^1$ qua ${var} = {expr_to_latex(t0)}$, các giới hạn một phía phải thỏa mãn: "
                        f"$$\\lim_{{{var} \\to {expr_to_latex(t0)}^-}} y_1({var}; C_1) = {y_s_ltx}, \\quad "
                        f"\\lim_{{{var} \\to {expr_to_latex(t0)}^+}} y_2({var}; C_2) = {y_s_ltx}$$ "
                        f"$$\\lim_{{{var} \\to {expr_to_latex(t0)}^-}} y'_1({var}; C_1) = "
                        f"\\lim_{{{var} \\to {expr_to_latex(t0)}^+}} y'_2({var}; C_2) = {yp_s_ltx}$$."
                    )
                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name="Phân tích bài toán Cauchy tại điểm kỳ dị",
                            title="Phân tích điều kiện nối nghiệm tại điểm kỳ dị",
                            description=cond_step_desc,
                            content=ExpressionStepContent(
                                expression_before=f"{dep_var}({t0}) = {y0}",
                                expression_after=f"lim {dep_var}({var}) = {y_s_val}, lim {dep_var}'({var}) = {singular_required_yp}",
                                latex_before=f"{dep_var}({expr_to_latex(t0)}) = {expr_to_latex(y0)}",
                                latex_after=rf"\lim_{{{var} \to {expr_to_latex(t0)}}} {dep_var}({var}) = {y_s_ltx}, \quad \lim_{{{var} \to {expr_to_latex(t0)}}} {dep_var}'({var}) = {yp_s_ltx}",
                            ),
                        )
                    )
                    step_num += 1

                    # Determine integration constants from initial value condition at singular point if solvable
                    can_determine_all_branches = True
                    candidate_expressions: list[sp.Expr] = []

                    for b_idx, b in enumerate(branch_solutions_list):
                        c_sym = b.integration_constant if isinstance(b.integration_constant, sp.Symbol) else None
                        if c_sym is not None and not b.expression.has(sp.Integral):
                            direction = "+"
                            if b.domain_interval is not None:
                                low, high = b.domain_interval
                                if high is not None and sp.simplify(high - t0) == 0:
                                    direction = "-"
                                elif low is not None and sp.simplify(low - t0) == 0:
                                    direction = "+"
                            try:
                                b_lim = sp.limit(b.expression, var, t0, dir=direction)
                                if c_sym in b_lim.free_symbols or c_sym in b.expression.free_symbols:
                                    sols_c = (
                                        sp.solve(sp.Eq(b_lim, y_s_val), c_sym)
                                        if not b_lim.has(sp.oo, -sp.oo, sp.zoo)
                                        else []
                                    )
                                    real_sols_c = [s for s in sols_c if s.is_real is not False and not s.has(sp.I)]
                                    c_fixed: sp.Expr | None = real_sols_c[0] if len(real_sols_c) == 1 else None
                                    if c_fixed is None:
                                        c_fixed = derive_unique_branch_constant(
                                            b.expression, var, t0, direction, c_sym, y_s_val
                                        )
                                    if c_fixed is not None:
                                        b_expr_fixed = sp.simplify(b.expression.subs(c_sym, c_fixed))
                                        candidate_expressions.append(b_expr_fixed)
                                        branch_solutions_list[b_idx] = BranchSolution(
                                            expression=b_expr_fixed,
                                            solution_str=str(b_expr_fixed),
                                            solution_latex=f"{dep_var}({var}) = {expr_to_latex(b_expr_fixed)}",
                                            branch_identity=b.branch_identity,
                                            integration_constant=c_sym,
                                            integration_constant_val=c_fixed,
                                            real_root_restrictions=b.real_root_restrictions,
                                            denominator_exclusions=b.denominator_exclusions,
                                            domain_interval=b.domain_interval,
                                            domain_restrictions=b.domain_restrictions,
                                            extension_status=b.extension_status,
                                            extension_details=b.extension_details,
                                            left_open=b.left_open,
                                            right_open=b.right_open,
                                            domain_set=b.domain_set,
                                            singular_exclusions=b.singular_exclusions,
                                            initial_condition_status=f"Xác định hằng số {c_sym} = {c_fixed} từ điều kiện nối nghiệm tại điểm kỳ dị",
                                        )
                                    else:
                                        can_determine_all_branches = False
                                else:
                                    diff_lim_y = sp.simplify(b_lim - y_s_val)
                                    if _prove_symbolic_zero(diff_lim_y):
                                        candidate_expressions.append(b.expression)
                                    else:
                                        can_determine_all_branches = False
                            except Exception:
                                can_determine_all_branches = False
                        else:
                            can_determine_all_branches = False

                    if can_determine_all_branches and candidate_expressions:
                        first_expr = candidate_expressions[0]
                        all_coincide = all(_prove_symbolic_zero(sp.simplify(e - first_expr)) for e in candidate_expressions)
                        if all_coincide:
                            final_sol = first_expr
                            final_latex_sol = f"{dep_var}({var}) = {expr_to_latex(final_sol)}"
                            final_result_str = f"{dep_var}({var}) = {final_sol}"
                            steps.append(
                                SolutionStep(
                                    step_number=step_num,
                                    rule_name="Nghiệm riêng bài toán Cauchy tại điểm kỳ dị",
                                    title="Xác định nghiệm riêng thỏa mãn bài toán Cauchy",
                                    description=(
                                        f"Giới hạn của nghiệm trên từng nhánh xác định đều tiến tới ${dep_var}({expr_to_latex(t0)}) = {y_s_ltx}$. "
                                        f"Điều kiện này xác định duy nhất các hằng số tích phân trên các nhánh lân cận, "
                                        f"dẫn đến nghiệm toàn cục duy nhất: ${dep_var}({var}) = {expr_to_latex(final_sol)}$."
                                    ),
                                    content=ExpressionStepContent(
                                        expression_before=f"{dep_var}({t0}) = {y0}",
                                        expression_after=f"{dep_var}({var}) = {final_sol}",
                                        latex_before=f"{dep_var}({expr_to_latex(t0)}) = {expr_to_latex(y0)}",
                                        latex_after=f"{dep_var}({var}) = {expr_to_latex(final_sol)}",
                                    ),
                                )
                            )
                            step_num += 1
                        else:
                            cases_cauchy_lines = []
                            for b in branch_solutions_list:
                                raw_ltx = (
                                    b.solution_latex.split("=", 1)[-1].strip()
                                    if "=" in b.solution_latex
                                    else b.solution_latex
                                )
                                cases_cauchy_lines.append(rf"{raw_ltx}, & {var} \in {b.interval_notation_latex}")
                            cauchy_body = " \\\\\n".join(cases_cauchy_lines)
                            final_latex_sol = rf"{dep_var}({var}) = \begin{{cases}} {cauchy_body} \end{{cases}}"
                            final_result_str = f"{dep_var}({var}) = {cases_cauchy_lines}"
                            final_sol = branch_solutions_list[0].expression
                    else:
                        for b_idx, b in enumerate(branch_solutions_list):
                            branch_solutions_list[b_idx] = BranchSolution(
                                expression=b.expression,
                                solution_str=b.solution_str,
                                solution_latex=b.solution_latex,
                                branch_identity=b.branch_identity,
                                integration_constant=b.integration_constant,
                                integration_constant_val=None,
                                real_root_restrictions=b.real_root_restrictions,
                                denominator_exclusions=b.denominator_exclusions,
                                domain_interval=b.domain_interval,
                                domain_restrictions=b.domain_restrictions,
                                extension_status=b.extension_status,
                                extension_details=b.extension_details,
                                left_open=b.left_open,
                                right_open=b.right_open,
                                domain_set=b.domain_set,
                                singular_exclusions=b.singular_exclusions,
                                initial_condition_status=f"Đòi hỏi điều kiện nối nghiệm tại điểm kỳ dị {var} = {expr_to_latex(t0)}",
                            )

                        cases_cauchy_lines = []
                        for b in branch_solutions_list:
                            raw_ltx = (
                                b.solution_latex.split("=", 1)[-1].strip()
                                if "=" in b.solution_latex
                                else b.solution_latex
                            )
                            cases_cauchy_lines.append(rf"{raw_ltx}, & {var} \in {b.interval_notation_latex}")
                        cauchy_body = " \\\\\n".join(cases_cauchy_lines)
                        final_latex_sol = rf"{dep_var}({var}) = \begin{{cases}} {cauchy_body} \end{{cases}}"
                        final_result_str = (
                            f"{dep_var}({var}) = {{{gen_sol_latex}}}; tại {var} = {t0}, {dep_var}({t0}) = {y0} "
                            f"(điểm kỳ dị, điều kiện nối nghiệm C1 chưa được chứng minh giải tích)"
                        )
                        final_sol = branch_solutions_list[0].expression if branch_solutions_list else gen_sol

                else:
                    # Case A: Regular Cauchy IVP
                    if domain_analysis.is_disconnected and branch_solutions_list:
                        for b_idx, b in enumerate(branch_solutions_list):
                            if b.domain_interval is not None:
                                low, high = b.domain_interval
                                if is_point_in_interval_interior(t0, low, high):
                                    target_branch_idx = b_idx
                                    break

                    try:
                        if is_mu_unevaluated or is_rhs_unevaluated:
                            c_val = None  # Crucial: do not set c_val = y0!
                            u_name = "u" if var.name != "u" and dep_var.name != "u" else "xi"
                            s_name = "s" if var.name != "s" and dep_var.name != "s" else "tau"
                            u_sym = sp.Symbol(u_name, real=True)
                            s_sym = sp.Symbol(s_name, real=True)

                            p_u = p_expr.subs(var, u_sym)
                            g_s = g_expr.subs(var, s_sym)

                            # Integrating factor anchored at t0: mu_{t0}(t) = exp(int_{t0}^t p(u) du)
                            mu_anchored = sp.exp(sp.Integral(p_u, (u_sym, t0, var)))

                            # mu_{t0}(s) = exp(int_{t0}^s p(u) du)
                            mu_s = sp.exp(sp.Integral(p_u, (u_sym, t0, s_sym)))

                            # Anchored RHS integral: int_{t0}^t mu_{t0}(s) * g(s) ds
                            rhs_integral_anchored = sp.Integral(mu_s * g_s, (s_sym, t0, var))

                            # Particular solution anchored at t0: y(t) = (y0 + int_{t0}^t mu_{t0}(s)*g(s) ds) / mu_{t0}(t)
                            part_sol = (y0 + rhs_integral_anchored) / mu_anchored

                            t0_ltx = expr_to_latex(t0)
                            y0_ltx = expr_to_latex(y0)
                            mu_t0_ltx = rf"\mu_{{{t0_ltx}}}({var})"
                            part_sol_latex = (
                                rf"{dep_var}({var}) = \frac{{1}}{{{mu_t0_ltx}}} \left[ {y0_ltx} + "
                                rf"\int_{{{t0_ltx}}}^{{{var}}} \mu_{{{t0_ltx}}}({s_name}) \left( {expr_to_latex(g_s)} \right) d{s_name} \right], "
                                rf"\quad {mu_t0_ltx} = \exp\left(\int_{{{t0_ltx}}}^{{{var}}} {expr_to_latex(p_u)} \, d{u_name}\right)"
                            )
                            part_sol_str = f"1/mu_{t0}({var}) * [{y0} + int_{t0}^{var}(mu_{t0}({s_name}) * ({g_s}) d{s_name})]"
                            step_before_desc = (
                                f"Thừa số tích phân chuẩn hóa tại điểm ban đầu {var} = {t0}: mu_{t0}({var}) = exp(int_{t0}^{var} p(u) du). "
                                f"Nghiệm riêng Cauchy được neo giải tích tại ({t0}, {y0}): y({t0}) = {y0}."
                            )
                            latex_before_step = (
                                rf"\mu_{{{t0_ltx}}}({var}) = \exp\left( \int_{{{t0_ltx}}}^{{{var}}} {expr_to_latex(p_u)} \, d{u_name} \right)"
                            )
                        else:
                            active_mu = mu_expr
                            active_rhs_int = rhs_integral
                            if (
                                target_branch_idx is not None
                                and target_branch_idx < len(branch_integrals)
                                and branch_integrals[target_branch_idx] is not None
                            ):
                                active_mu, active_rhs_int = branch_integrals[target_branch_idx]  # type: ignore[misc]
                            mu_t0 = sp.simplify(active_mu.subs(var, t0))
                            int_t0 = sp.simplify(active_rhs_int.subs(var, t0))
                            c_val = sp.simplify(y0 * mu_t0 - int_t0)
                            part_sol = sp.simplify((active_rhs_int + c_val) / active_mu)
                            part_sol_latex = f"{dep_var}({var}) = {expr_to_latex(part_sol)}"
                            part_sol_str = f"{dep_var}({var}) = {part_sol}"
                            step_before_desc = (
                                f"Thay {var} = {t0} và {dep_var} = {y0} vào hệ thức: "
                                f"{y0} = ({int_t0} + C) / {mu_t0} => C = {c_val}."
                            )
                            latex_before_step = f"{expr_to_latex(y0)} = \\frac{{{expr_to_latex(int_t0)} + C}}{{{expr_to_latex(mu_t0)}}}"

                        if target_branch_idx is not None:
                            for b_idx, b in enumerate(branch_solutions_list):
                                if b_idx == target_branch_idx:
                                    branch_solutions_list[b_idx] = BranchSolution(
                                        expression=part_sol,
                                        solution_str=part_sol_str,
                                        solution_latex=part_sol_latex,
                                        branch_identity=b.branch_identity,
                                        integration_constant=b.integration_constant,
                                        integration_constant_val=c_val,
                                        real_root_restrictions=b.real_root_restrictions,
                                        denominator_exclusions=b.denominator_exclusions,
                                        domain_interval=b.domain_interval,
                                        domain_restrictions=b.domain_restrictions,
                                        extension_status=b.extension_status,
                                        extension_details=b.extension_details,
                                        left_open=b.left_open,
                                        right_open=b.right_open,
                                        domain_set=b.domain_set,
                                        singular_exclusions=b.singular_exclusions,
                                        initial_condition_status=f"Định bởi Cauchy IVP ({var}0 = {expr_to_latex(t0)})",
                                    )
                                else:
                                    branch_solutions_list[b_idx] = BranchSolution(
                                        expression=b.expression,
                                        solution_str=b.solution_str,
                                        solution_latex=b.solution_latex,
                                        branch_identity=b.branch_identity,
                                        integration_constant=b.integration_constant,
                                        integration_constant_val=None,
                                        real_root_restrictions=b.real_root_restrictions,
                                        denominator_exclusions=b.denominator_exclusions,
                                        domain_interval=b.domain_interval,
                                        domain_restrictions=b.domain_restrictions,
                                        extension_status=b.extension_status,
                                        extension_details=b.extension_details,
                                        left_open=b.left_open,
                                        right_open=b.right_open,
                                        domain_set=b.domain_set,
                                        singular_exclusions=b.singular_exclusions,
                                        initial_condition_status=f"Chưa xác định (Nghiệm tổng quát {b.integration_constant})",
                                    )

                            target_b = branch_solutions_list[target_branch_idx]
                            target_int_latex = target_b.interval_notation_latex
                            cases_cauchy_lines = []
                            for b in branch_solutions_list:
                                raw_ltx = (
                                    b.solution_latex.split("=", 1)[-1].strip()
                                    if "=" in b.solution_latex
                                    else b.solution_latex
                                )
                                cases_cauchy_lines.append(rf"{raw_ltx}, & {var} \in {b.interval_notation_latex}")
                            cauchy_body = " \\\\\n".join(cases_cauchy_lines)
                            final_latex_sol = rf"{dep_var}({var}) = \begin{{cases}} {cauchy_body} \end{{cases}}"
                            final_result_str = (
                                f"{dep_var}({var}) = {part_sol} (duy nhất trên {target_int_latex} chứa {var}0 = {t0}; "
                                f"các khoảng khác phụ thuộc hằng số tự do)"
                            )
                            step_cauchy_desc = (
                                f"Điều kiện ban đầu ${dep_var}({expr_to_latex(t0)}) = {expr_to_latex(y0)}$ nằm trong khoảng "
                                f"${target_int_latex}$. Do phương trình gián đoạn miền tại các điểm kỳ dị, bài toán Cauchy "
                                f"xác định nghiệm riêng duy nhất trên nhánh $I_{{{target_branch_idx + 1}}} = {target_int_latex}$. "
                                f"Trên các nhánh rời rạc khác, nghiệm vẫn phụ thuộc vào hằng số tích phân tự do."
                            )
                        else:
                            step_cauchy_desc = "Thế giá trị hằng số C cụ thể vào biểu thức nghiệm để kết luận nghiệm riêng duy nhất."
                            final_latex_sol = part_sol_latex
                            final_result_str = f"{dep_var}({var}) = {part_sol}"

                        c_display_val = (
                            expr_to_latex(c_val)
                            if c_val is not None
                            else rf"\text{{xác định theo neo }} {expr_to_latex(t0)}"
                        )
                        steps.append(
                            SolutionStep(
                                step_number=step_num,
                                rule_name="Áp dụng điều kiện ban đầu",
                                title="Xác định hằng số C từ điều kiện ban đầu",
                                description=step_before_desc,
                                content=ExpressionStepContent(
                                    expression_before=f"{y0} = f({t0}, C)",
                                    expression_after=f"C = {c_val}" if c_val is not None else f"y({t0}) = {y0}",
                                    latex_before=latex_before_step,
                                    latex_after=rf"C = {c_display_val}" if c_val is not None else rf"{dep_var}({expr_to_latex(t0)}) = {expr_to_latex(y0)}",
                                ),
                            )
                        )
                        step_num += 1

                        steps.append(
                            SolutionStep(
                                step_number=step_num,
                                rule_name="Nghiệm riêng",
                                title="Nghiệm riêng của bài toán giá trị ban đầu",
                                description=step_cauchy_desc,
                                content=ExpressionStepContent(
                                    expression_before=f"y({var}) = {gen_sol}",
                                    expression_after=f"y({var}) = {part_sol}",
                                    latex_before=gen_sol_latex,
                                    latex_after=final_latex_sol,
                                ),
                            )
                        )
                        final_sol = part_sol
                    except Exception as exc:
                        domain_restrictions.append(f"Không thể áp dụng điều kiện ban đầu: {exc}")

        # Verification
        if branch_solutions_list:
            branch_solutions_tuple, verif_res = self.verifier.verify_branch_solutions(
                branches=tuple(branch_solutions_list),
                variable=var,
                p_expr=p_expr,
                g_expr=g_expr,
                initial_condition=parsed.initial_condition,
                singular_points=domain_analysis.singular_points if domain_analysis else (),
                singular_point_analyses=domain_analysis.singular_point_analyses if domain_analysis else (),
            )
        else:
            verif_res = self.verifier.verify_explicit(
                solution=final_sol,
                variable=var,
                p_expr=p_expr,
                g_expr=g_expr,
                initial_condition=parsed.initial_condition,
                integration_constant=c_sym,
            )
            branch_solutions_tuple = ()

        # Determine overall solution status
        warnings_list: list[str] = list(user_warnings)
        if verif_res.status == VerificationStatus.FAILED:
            sol_status = SolutionStatus.DISCREPANCY_DETECTED
            warnings_list.append(f"Cảnh báo kiểm định toán học: {verif_res.details}")
        elif verif_res.status == VerificationStatus.UNVERIFIED:
            sol_status = SolutionStatus.UNVERIFIED
            warnings_list.append(f"Không thể kiểm chứng độc lập hoàn toàn: {verif_res.details}")
        elif is_singular_cauchy_compatible:
            # Check original unnormalized differential equation residual (fail-closed)
            orig_residual_verified = False
            residual_failure_status = None
            residual_details = ""

            if final_sol is None:
                orig_residual_verified = False
                residual_failure_status = VerificationStatus.UNVERIFIED
                residual_details = "Không có nghiệm giải tích cụ thể để kiểm chứng phần dư phương trình vi phân gốc."
            else:
                try:
                    dep_var_sym = sp.Symbol(str(dep_var))
                    y_prime_sym = sp.Symbol(f"{dep_var}_prime")
                    dy_sol = sp.diff(final_sol, var)
                    sub_dict = {dep_var_sym: final_sol, y_prime_sym: dy_sol}
                    orig_residual = sp.simplify(parsed.standard_expr.subs(sub_dict))
                    if _prove_symbolic_zero(orig_residual):
                        orig_residual_verified = True
                    else:
                        orig_residual_verified = False
                        residual_failure_status = VerificationStatus.FAILED
                        residual_details = f"Biểu thức dư của phương trình vi phân gốc R({var}) = {orig_residual} khác 0."
                except Exception as exc:
                    orig_residual_verified = False
                    residual_failure_status = VerificationStatus.UNVERIFIED
                    residual_details = f"Lỗi trong quá trình tính toán phần dư phương trình vi phân gốc: {exc}."

            if not orig_residual_verified:
                verif_res = VerificationResult(
                    status=residual_failure_status or VerificationStatus.UNVERIFIED,
                    method="original_equation_residual_check",
                    details=residual_details or "Không thể xác minh phần dư của phương trình vi phân gốc.",
                )

            if orig_residual_verified and verif_res.status in (
                VerificationStatus.VERIFIED,
                VerificationStatus.VERIFIED_GLOBALLY,
                VerificationStatus.C1_EXTENSION_VERIFIED,
            ):
                verif_res = VerificationResult(
                    status=VerificationStatus.C1_EXTENSION_VERIFIED,
                    method=verif_res.method,
                    details=f"Đã kiểm chứng nghiệm trơn C¹ thỏa mãn phương trình và điều kiện ban đầu tại điểm kỳ dị: {verif_res.details}",
                )
                if final_result_str is not None and "điều kiện nối nghiệm C1 chưa được chứng minh giải tích" in final_result_str:
                    final_result_str = final_result_str.replace(
                        "điều kiện nối nghiệm C1 chưa được chứng minh giải tích",
                        "đã kiểm chứng tồn tại nghiệm nối trơn C1",
                    )
                sol_status = SolutionStatus.SUCCESS
                warnings_list.append(
                    f"Bài toán Cauchy tại điểm kỳ dị được chứng minh tồn tại nghiệm nối trơn C1: {verif_res.details}"
                )
            else:
                # Singular Cauchy IVP: cannot claim SUCCESS without analytic continuation proof!
                sol_status = (
                    SolutionStatus.UNVERIFIED
                    if verif_res.status != VerificationStatus.FAILED
                    else SolutionStatus.DISCREPANCY_DETECTED
                )
                warnings_list.append(
                    f"Thỏa mãn điều kiện đại số ban đầu nhưng sự tồn tại nghiệm nối trơn toàn cục chưa được chứng minh: {verif_res.details}"
                )
        elif verif_res.status == VerificationStatus.PARTIALLY_VERIFIED:
            sol_status = SolutionStatus.SUCCESS
            warnings_list.append(
                f"Kiểm chứng từng nhánh thành công; lưu ý điều kiện mở rộng tại điểm kỳ dị: {verif_res.details}"
            )
        else:
            sol_status = SolutionStatus.SUCCESS

        # Constrain status by domain completeness
        if domain_analysis is not None:
            if domain_analysis.completeness == DomainCompleteness.PARTIAL:
                if verif_res.status in (VerificationStatus.VERIFIED, VerificationStatus.VERIFIED_GLOBALLY):
                    verif_res = VerificationResult(
                        status=VerificationStatus.PARTIALLY_VERIFIED,
                        method=verif_res.method,
                        details=f"{verif_res.details} (Miền xác định chỉ được xác định một phần: {domain_analysis.completeness.value}).",
                    )
            elif domain_analysis.completeness == DomainCompleteness.UNKNOWN:
                if verif_res.status in (VerificationStatus.VERIFIED, VerificationStatus.VERIFIED_GLOBALLY):
                    verif_res = VerificationResult(
                        status=VerificationStatus.PARTIALLY_VERIFIED,
                        method=verif_res.method,
                        details=f"{verif_res.details} (Miền xác định chưa thể xác định đầy đủ: {domain_analysis.completeness.value}).",
                    )

        elapsed = (time.perf_counter() - t0_start) * 1000.0
        return SolutionResponse(
            status=sol_status,
            verification=verif_res,
            raw_input=request.raw_input,
            canonical_input=parsed.canonical_eq,
            final_result=final_result_str
            if final_result_str is not None
            else f"{dep_var}({var}) = {final_sol}",
            final_latex=final_latex_sol,
            steps=tuple(steps),
            domain_restrictions=tuple(domain_restrictions),
            warnings=tuple(warnings_list),
            execution_time_ms=elapsed,
            branch_solutions=branch_solutions_tuple,
            original_domain_latex=domain_analysis.original_domain_latex if domain_analysis else "\\mathbb{R}",
            normalized_domain_latex=domain_analysis.normalized_domain_latex if domain_analysis else "\\mathbb{R}",
        )

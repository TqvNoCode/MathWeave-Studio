"""Dedicated Euler–Cauchy ODE Solver for Second-Order Homogeneous and Nonhomogeneous Equations."""

from __future__ import annotations

import time
import sympy as sp

from math_app.application.dtos import (
    BranchSolution,
    ProblemRequest,
    SolutionResponse,
    SolutionStep,
    VerificationResult,
)
from math_app.application.ports.solver import Solver
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import (
    DomainCompleteness,
    ProblemType,
    SolutionStatus,
    VerificationStatus,
)
from math_app.domain.step_content import ExpressionStepContent
from math_app.input.ode_parser import (
    ParsedIntervalConstraint,
    ParsedSecondOrderODE,
    parse_interval_constraint,
    parse_second_order_ode_input,
)
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.solvers.calculus.ode._real_calculus import (
    _combine_completeness,
    _format_domain_with_completeness,
    _univariate_constraint_real_set,
)
from math_app.solvers.calculus.ode.domain_analyzer import (
    _decompose_set_components,
    format_interval_latex,
)
from math_app.solvers.calculus.ode.nonhomogeneous_ivp import (
    validate_initial_point_against_domain,
)
from math_app.solvers.calculus.ode.variation_of_parameters import (
    VariationOfParametersResult,
    extract_domain_restrictions_from_expr,
)
from math_app.verification.calculus.ode_verifier import (
    ODEVerifier,
    _prove_symbolic_zero,
    classify_scalar_real_finite,
    evaluate_initial_point_domain,
)

_NON_ELEMENTARY_ATOMS: tuple[type[sp.Basic], ...] = tuple(
    cls
    for cls in (
        getattr(sp, name, None)
        for name in (
            "Integral",
            "meijerg",
            "hyper",
            "Piecewise",
            "RootSum",
            "Ei",
            "Si",
            "Ci",
            "Shi",
            "Chi",
            "li",
            "erf",
            "erfi",
            "erfc",
            "fresnels",
            "fresnelc",
            "uppergamma",
            "lowergamma",
            "polylog",
            "LambertW",
        )
    )
    if cls is not None
)


def _exclude_expr_zeros(
    base_set: sp.Set | None,
    expr: sp.Expr | None,
    var: sp.Symbol,
    comp: DomainCompleteness,
) -> tuple[sp.Set | None, DomainCompleteness]:
    """Exclude real zeros of expr over var from base_set while preserving completeness."""
    if expr is None:
        return base_set, comp
    if expr.free_symbols - {var}:
        return base_set, _combine_completeness(comp, DomainCompleteness.PARTIAL)
    if var not in expr.free_symbols:
        if _prove_symbolic_zero(expr):
            return sp.S.EmptySet, comp
        if expr.is_zero is not False:
            return base_set, _combine_completeness(comp, DomainCompleteness.UNKNOWN)
        return base_set, comp
    try:
        zeros = sp.solveset(sp.Eq(expr, 0), var, sp.S.Reals)
        if isinstance(zeros, sp.ConditionSet):
            return base_set, _combine_completeness(comp, DomainCompleteness.UNKNOWN)
        if zeros != sp.S.EmptySet and base_set is not None:
            return sp.Intersection(base_set, sp.Complement(sp.S.Reals, zeros)), comp
        return base_set, comp
    except Exception:
        return base_set, _combine_completeness(comp, DomainCompleteness.UNKNOWN)


def _interval_sort_key(iv: sp.Interval) -> tuple[int, float]:
    """Order positive intervals first (ascending), then negative intervals (descending)."""
    is_pos = iv.start.is_nonnegative is True
    try:
        ref = float(sp.N(iv.start)) if iv.start != -sp.oo else -1e12
    except Exception:
        ref = 0.0
    if is_pos:
        return (0, ref)
    try:
        end_ref = float(sp.N(iv.end)) if iv.end != sp.oo else 1e12
    except Exception:
        end_ref = 0.0
    return (1, -end_ref)


def _build_domain_metadata(
    parsed: ParsedSecondOrderODE,
    var: sp.Symbol,
    dep_var: sp.Symbol,
) -> tuple[
    sp.Set | None,
    DomainCompleteness,
    sp.Set | None,
    DomainCompleteness,
    tuple[sp.Interval, ...],
    tuple[sp.Set, ...],
    str,
    str,
    DomainCompleteness,
    list[str],
]:
    """Derive original & normalized domains from ParsedSecondOrderODE metadata."""
    restrictions: list[str] = [
        f"Điểm kỳ dị của hệ số dẫn a({var}): {var} = 0. "
        f"Nghiệm không xác định tại {var} = 0 và không liên tục qua điểm này (Natural domain: R \\ {{0}})."
    ]
    for restr in getattr(parsed, "original_domain_restrictions", ()):
        if restr not in restrictions:
            restrictions.append(restr)

    orig_domain: sp.Set | None = sp.S.Reals
    orig_comp = DomainCompleteness.EXACT

    for constraint in getattr(parsed, "original_domain_constraints", ()):
        c_set, c_comp, c_note = _univariate_constraint_real_set(constraint, var, dep_var)
        orig_comp = _combine_completeness(orig_comp, c_comp)
        if c_note and c_note not in restrictions:
            restrictions.append(c_note)
        if c_set is not None:
            if orig_domain is not None:
                try:
                    orig_domain = sp.Intersection(orig_domain, c_set)
                except Exception as exc:
                    orig_comp = _combine_completeness(orig_comp, DomainCompleteness.PARTIAL)
                    restrictions.append(f"Không thể giao miền ràng buộc {constraint.expr}: {exc}")
            elif c_set != sp.S.Reals:
                orig_domain = c_set

    for denom in getattr(parsed, "original_denominators", ()):
        orig_domain, orig_comp = _exclude_expr_zeros(orig_domain, denom, var, orig_comp)

    if orig_comp != DomainCompleteness.EXACT and orig_domain == sp.S.Reals:
        orig_domain = None

    norm_domain: sp.Set | None = orig_domain
    norm_comp = orig_comp
    if norm_domain is not None:
        norm_domain = sp.Intersection(
            norm_domain,
            sp.Complement(sp.S.Reals, sp.FiniteSet(sp.Integer(0))),
        )

    for lc in (*getattr(parsed, "leading_coeffs", ()), parsed.a_coeff):
        norm_domain, norm_comp = _exclude_expr_zeros(norm_domain, lc, var, norm_comp)

    if norm_comp != DomainCompleteness.EXACT and norm_domain == sp.S.Reals:
        norm_domain = None

    raw_intervals, isolated_pts, other_comps = (
        _decompose_set_components(norm_domain) if norm_domain is not None else ([], [], [])
    )
    if isolated_pts:
        norm_comp = _combine_completeness(norm_comp, DomainCompleteness.PARTIAL)
    if other_comps:
        norm_comp = _combine_completeness(norm_comp, DomainCompleteness.PARTIAL)

    sorted_intervals = tuple(sorted(raw_intervals, key=_interval_sort_key))

    orig_latex, orig_fmt_err = _format_domain_with_completeness(orig_domain, orig_comp, var.name)
    if orig_fmt_err:
        orig_comp = _combine_completeness(orig_comp, DomainCompleteness.UNKNOWN)
        restrictions.append(orig_fmt_err)
    norm_latex, norm_fmt_err = _format_domain_with_completeness(norm_domain, norm_comp, var.name)
    if norm_fmt_err:
        norm_comp = _combine_completeness(norm_comp, DomainCompleteness.UNKNOWN)
        restrictions.append(norm_fmt_err)

    overall_comp = _combine_completeness(orig_comp, norm_comp)
    return (
        orig_domain,
        orig_comp,
        norm_domain,
        norm_comp,
        sorted_intervals,
        tuple(other_comps),
        orig_latex,
        norm_latex,
        overall_comp,
        list(dict.fromkeys(restrictions)),
    )


def _is_elementary_real_closed_form(expr: sp.Expr, var: sp.Symbol, is_neg: bool) -> bool:
    """Return True only when expr is a real elementary closed form without unverified special funcs."""
    if not isinstance(expr, sp.Basic):
        return False
    if expr.has(sp.I, sp.zoo, sp.nan, sp.oo, -sp.oo, sp.AccumBounds):
        return False
    if _NON_ELEMENTARY_ATOMS and expr.has(*_NON_ELEMENTARY_ATOMS):
        return False
    if is_neg:
        # Reject negative logarithms log(t) or fractional powers t^p on t < 0
        for lg in expr.atoms(sp.log):
            if lg.args[0] == var or (
                isinstance(lg.args[0], sp.Expr)
                and lg.args[0].has(var)
                and not lg.args[0].has(-var)
            ):
                # Substitute a negative sample if numeric check shows log argument <= 0
                try:
                    sample_val = sp.N(lg.args[0].subs(var, -sp.Integer(2)))
                    if sample_val.is_real and float(sample_val) <= 0:
                        return False
                except Exception:
                    pass
    return True


def _integrate_on_real_branch(
    integrand: sp.Expr,
    var: sp.Symbol,
    is_neg: bool,
) -> tuple[bool, sp.Expr]:
    """Integrate integrand on either t > 0 or t < 0 using positive substitution tau = |t| > 0."""
    from sympy.integrals.risch import NonElementaryIntegral

    tau = sp.Symbol("_ec_tau", positive=True)
    sub_expr = -var if is_neg else var
    try:
        transformed = sp.simplify(integrand.subs(var, -tau if is_neg else tau))
        if is_neg:
            # dt = -d(tau) under t = -tau
            transformed = -transformed
        risch_try = sp.integrate(transformed, tau, risch=True)
        if isinstance(risch_try, NonElementaryIntegral):
            # Risch decision procedure proved no elementary antiderivative exists.
            return False, sp.Integer(0)
        antideriv_tau = (
            sp.integrate(transformed, tau)
            if risch_try.has(sp.Integral)
            else risch_try
        )
        if not _is_elementary_real_closed_form(antideriv_tau, tau, is_neg=False):
            return False, sp.Integer(0)
        antideriv_tau = sp.simplify(sp.trigsimp(antideriv_tau))
        antideriv = antideriv_tau.subs(tau, sub_expr)
        if not _is_elementary_real_closed_form(antideriv, var, is_neg=is_neg):
            return False, sp.Integer(0)
        return True, antideriv
    except Exception:
        return False, sp.Integer(0)


def _compute_euler_cauchy_vop(
    A: sp.Expr,
    B: sp.Expr,
    C: sp.Expr,
    g_expr: sp.Expr,
    y1_fund: sp.Expr,
    y2_fund: sp.Expr,
    W_fund: sp.Expr,
    var: sp.Symbol,
    is_neg: bool,
    initial_point: sp.Expr | None = None,
) -> VariationOfParametersResult:
    """Compute particular solution y_p(t) for A*t^2*y'' + B*t*y' + C*y = g(t) via Variation of Parameters."""
    a_t = A * (var**2)
    b_t = B * var
    R_expr = sp.simplify(g_expr / a_t)

    u1_prime = sp.simplify(sp.trigsimp(-y2_fund * R_expr / W_fund))
    u2_prime = sp.simplify(sp.trigsimp(y1_fund * R_expr / W_fund))

    is_integral_form = False
    u1_sol: sp.Expr
    u2_sol: sp.Expr

    if initial_point is not None:
        s_sym = sp.Symbol("s") if var.name != "s" else sp.Symbol("tau")
        u1_sol = -sp.Integral(sp.simplify(y2_fund * R_expr / W_fund).subs(var, s_sym), (s_sym, initial_point, var))
        u2_sol = sp.Integral(sp.simplify(y1_fund * R_expr / W_fund).subs(var, s_sym), (s_sym, initial_point, var))
        is_integral_form = True
        yp_sol = u1_sol * y1_fund + u2_sol * y2_fund
    else:
        ok1, u1_cand = _integrate_on_real_branch(u1_prime, var, is_neg=is_neg)
        ok2, u2_cand = _integrate_on_real_branch(u2_prime, var, is_neg=is_neg)
        if ok1 and ok2:
            tau = sp.Symbol("_ec_tau", positive=True)
            sub_expr = -var if is_neg else var
            yp_raw = u1_cand * y1_fund + u2_cand * y2_fund
            yp_tau = sp.simplify(
                sp.trigsimp(
                    sp.radsimp(sp.expand(yp_raw.subs(var, -tau if is_neg else tau)))
                )
            )
            yp_cand = yp_tau.subs(tau, sub_expr)
            # Validate residual symbolically in positive tau coordinates
            dyp_cand = sp.diff(yp_cand, var)
            d2yp_cand = sp.diff(dyp_cand, var)
            res_tau = sp.simplify(
                sp.trigsimp(
                    (a_t * d2yp_cand + b_t * dyp_cand + C * yp_cand - g_expr).subs(
                        var, -tau if is_neg else tau
                    )
                )
            )
            if _prove_symbolic_zero(res_tau, variable=tau, domain_interval=(0, sp.oo)) and _is_elementary_real_closed_form(
                yp_cand, var, is_neg=is_neg
            ):
                u1_sol = u1_cand
                u2_sol = u2_cand
                yp_sol = yp_cand
            else:
                is_integral_form = True
                u1_sol = -sp.Integral(sp.simplify(y2_fund * R_expr / W_fund), var)
                u2_sol = sp.Integral(sp.simplify(y1_fund * R_expr / W_fund), var)
                yp_sol = u1_sol * y1_fund + u2_sol * y2_fund
        else:
            is_integral_form = True
            u1_sol = -sp.Integral(sp.simplify(y2_fund * R_expr / W_fund), var)
            u2_sol = sp.Integral(sp.simplify(y1_fund * R_expr / W_fund), var)
            yp_sol = u1_sol * y1_fund + u2_sol * y2_fund

    return VariationOfParametersResult(
        is_supported=True,
        particular_solution=yp_sol,
        u1_expr=u1_sol,
        u2_expr=u2_sol,
        u1_prime=u1_prime,
        u2_prime=u2_prime,
        wronskian=W_fund,
        is_integral_form=is_integral_form,
        initial_point=initial_point,
    )


class ODEEulerCauchySolver(Solver):
    """Solver for second-order homogeneous and nonhomogeneous Euler–Cauchy ODEs:

    a*t^2*y''(t) + b*t*y'(t) + c*y(t) = g(t),  (a != 0, t != 0),

    supporting general solutions and complete second-order Cauchy IVPs across
    both positive and negative connected domain intervals.
    """

    def __init__(self, verifier: ODEVerifier | None = None) -> None:
        self.verifier = verifier or ODEVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type in (
            ProblemType.ODE_EULER_CAUCHY,
            ProblemType.SOLVE_EQUATION,
        )

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        t0_start = time.perf_counter()
        raw = request.raw_input.strip()
        if not raw and not request.parameters:
            raise InvalidInputError("Phương trình vi phân không được để trống (Equation cannot be empty).")

        parsed: ParsedSecondOrderODE = parse_second_order_ode_input(
            raw,
            target_variable=request.target_variable,
            parameters=dict(request.parameters),
        )

        elapsed = (time.perf_counter() - t0_start) * 1000.0

        # Validate second order
        if sp.simplify(parsed.a_coeff) == 0:
            raise InvalidInputError("Hệ số của y'' bằng 0; không phải phương trình vi phân cấp 2 (a != 0).")

        var = parsed.independent_var
        dep_var = parsed.dependent_var
        a_expr = parsed.a_coeff
        b_expr = parsed.b_coeff
        c_expr = parsed.c_coeff

        # Detect homogeneity and validate forcing term g(t)
        rem_simp = sp.simplify(parsed.rem_expr)
        g_expr_cand = sp.simplify(-rem_simp)
        is_nonhomogeneous = not (parsed.is_homogeneous or _prove_symbolic_zero(g_expr_cand))
        g_expr: sp.Expr | None = g_expr_cand if is_nonhomogeneous else None

        if g_expr is not None:
            extra_g_syms = g_expr.free_symbols - {var}
            if extra_g_syms:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = (
                    f"Vế phải g({var}) = {g_expr} chứa tham số chưa xác định "
                    f"{tuple(sorted(s.name for s in extra_g_syms))}."
                )
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="euler_cauchy_unresolved_forcing_parameter",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )
            if g_expr.has(sp.oo, -sp.oo, sp.zoo, sp.nan, sp.AccumBounds):
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = f"Vế phải g({var}) = {g_expr} chứa giá trị vô cực hoặc bất định."
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="euler_cauchy_infinite_forcing",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )
            if g_expr.has(sp.I):
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = f"Vế phải g({var}) = {g_expr} chứa đơn vị ảo phức; hệ thống chỉ giải phương trình thực."
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="euler_cauchy_complex_forcing",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )

        # 1. Structural Euler-Cauchy verification
        # a(t) = A*t^2, b(t) = B*t, c(t) = C
        A_cand = sp.simplify(a_expr / (var**2))
        B_cand = sp.simplify(b_expr / var)
        C_cand = sp.simplify(c_expr)

        # Check if coefficients depend on var
        if A_cand.has(var) or B_cand.has(var) or C_cand.has(var):
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            msg = (
                f"Phương trình không có cấu trúc Euler–Cauchy chuẩn tắc a·{var}²·y'' + b·{var}·y' + c·y = 0. "
                f"Các hệ số thu được: a({var})/({var}²) = {expr_to_latex(A_cand)}, "
                f"b({var})/{var} = {expr_to_latex(B_cand)}, c({var}) = {expr_to_latex(C_cand)} phụ thuộc vào {var}."
            )
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="euler_cauchy_structure_mismatch",
                    details=msg,
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=(msg,),
                execution_time_ms=elapsed,
            )

        # Ensure A != 0
        if A_cand.is_zero is True or _prove_symbolic_zero(A_cand):
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            msg = (
                f"Hệ số dẫn của phương trình Euler–Cauchy A = a({var})/({var}²) bằng 0 "
                "(Leading Euler–Cauchy coefficient A cannot be zero)."
            )
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="euler_cauchy_zero_leading_coeff",
                    details=msg,
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=(msg,),
                execution_time_ms=elapsed,
            )

        # Ensure A, B, C are proven finite real constants without unresolved parameters
        for c_name, c_val in (("A", A_cand), ("B", B_cand), ("C", C_cand)):
            if c_val.free_symbols:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = f"Hệ số {c_name} = {c_val} chứa tham số chưa xác định {tuple(c_val.free_symbols)}."
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="euler_cauchy_unresolved_parameter",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )
            if c_val.has(sp.oo, -sp.oo, sp.zoo, sp.nan, sp.AccumBounds) or c_val.is_finite is False:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = f"Hệ số {c_name} = {c_val} không phải là số thực hữu hạn."
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="euler_cauchy_infinite_coefficient",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )
            if c_val.has(sp.I) or c_val.is_real is False:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = f"Hệ số {c_name} = {c_val} chứa đơn vị ảo phức hoặc không thuần thực."
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="euler_cauchy_complex_coefficient",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )
            if c_val.is_real is not True or c_val.is_finite is not True:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = (
                    f"Không thể xác minh hệ số {c_name} = {c_val} là số thực hữu hạn "
                    "theo giả thiết ký hiệu (is_real/is_finite chưa được xác lập)."
                )
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="euler_cauchy_unverified_coefficient",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )

        if A_cand.is_zero is not False:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            msg = f"Không thể chứng minh hệ số dẫn A = {A_cand} khác 0 bằng phương pháp ký hiệu."
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="euler_cauchy_leading_coeff_unresolved",
                    details=msg,
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=(msg,),
                execution_time_ms=elapsed,
            )

        A = A_cand
        B = B_cand
        C = C_cand

        # Preserve and validate original source-domain metadata
        (
            _orig_domain,
            _orig_comp,
            norm_domain,
            norm_comp,
            connected_intervals,
            other_comps,
            orig_domain_latex,
            norm_domain_latex,
            overall_comp,
            domain_restrictions,
        ) = _build_domain_metadata(parsed, var, dep_var)

        if g_expr is not None:
            for g_restr in extract_domain_restrictions_from_expr(g_expr, var):
                if g_restr not in domain_restrictions:
                    domain_restrictions.append(g_restr)

        # 2. Validate Cauchy IVP conditions based on problem mode
        has_y_ic = parsed.initial_condition is not None
        has_yp_ic = parsed.initial_derivative is not None

        prob_mode = str(request.parameters.get("problem_mode", "")).strip().upper()
        if prob_mode == "GENERAL" and (has_y_ic or has_yp_ic):
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            msg = (
                "Phát hiện không khớp yêu cầu bài toán: Bạn đang ở chế độ 'Tìm nghiệm tổng quát' "
                "nhưng dữ liệu bài toán lại chứa điều kiện ban đầu Cauchy (y(t0) hoặc y'(t0)). "
                "Vui lòng chuyển sang chế độ 'Bài toán Cauchy (IVP)' để tìm nghiệm xác định duy nhất, "
                "hoặc xóa các điều kiện ban đầu để tìm nghiệm tổng quát."
            )
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="problem_mode_mismatch",
                    details=msg,
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=(msg,),
                execution_time_ms=elapsed,
            )

        is_cauchy_request = (
            prob_mode == "CAUCHY_IVP"
            or request.problem_type == ProblemType.ODE_SECOND_ORDER_IVP
            or (has_y_ic and has_yp_ic)
        )

        if prob_mode == "CAUCHY_IVP" or request.problem_type == ProblemType.ODE_SECOND_ORDER_IVP:
            if not has_y_ic and not has_yp_ic:
                raise InvalidInputError(
                    "Bài toán Cauchy (IVP) cấp hai yêu cầu cung cấp đầy đủ hai điều kiện ban đầu: "
                    f"{dep_var}({var}0) = y0 và {dep_var}'({var}0) = v0."
                )
            if not has_y_ic or not has_yp_ic:
                raise InvalidInputError(
                    "Bài toán Cauchy (IVP) cấp hai thiếu điều kiện ban đầu. "
                    f"Cần cung cấp đầy đủ cả hai điều kiện: {dep_var}({var}0) = y0 và {dep_var}'({var}0) = v0 để xác định nghiệm duy nhất."
                )
        else:
            if (has_y_ic and not has_yp_ic) or (not has_y_ic and has_yp_ic):
                raise InvalidInputError(
                    "Phương trình vi phân cấp hai nhận được điều kiện ban đầu không hoàn chỉnh. "
                    f"Vui lòng cung cấp đầy đủ cả hai điều kiện: {dep_var}({var}0) = y0 và {dep_var}'({var}0) = v0 để giải bài toán Cauchy, "
                    "hoặc không cung cấp điều kiện nào để tìm nghiệm tổng quát."
                )

        t0_val: sp.Expr | None = None
        y0_val: sp.Expr | None = None
        v0_val: sp.Expr | None = None

        if has_y_ic and has_yp_ic:
            t0_cand, y0_cand = parsed.initial_condition  # type: ignore[misc]
            t1_cand, v0_cand = parsed.initial_derivative  # type: ignore[misc]
            try:
                base_diff = sp.simplify(t0_cand - t1_cand)
            except Exception:
                base_diff = t0_cand - t1_cand
            if not _prove_symbolic_zero(base_diff) and base_diff != 0:
                raise InvalidInputError(
                    f"Bài toán Cauchy (IVP) cấp hai yêu cầu hai điều kiện tại cùng một điểm ban đầu {var}0: "
                    f"{dep_var}({t0_cand}) và {dep_var}'({t1_cand}) không cùng điểm khởi đầu (Base point mismatch)."
                )

            for val_name, val_expr in (("t0", t0_cand), ("y0", y0_cand), ("v0", v0_cand)):
                v_stat, v_msg = classify_scalar_real_finite(val_expr, allow_complex=False)
                if v_stat == "invalid":
                    raise InvalidInputError(
                        f"Giá trị điều kiện ban đầu {val_name} = {val_expr} không phải là số thực hữu hạn: {v_msg} "
                        "(Finite real numbers required for Cauchy initial conditions)."
                    )
                if (
                    v_stat == "unknown"
                    or val_expr.free_symbols
                    or val_expr.is_real is not True
                    or val_expr.is_finite is not True
                ):
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    msg = (
                        f"Không thể xác nhận giá trị điều kiện ban đầu {val_name} = {val_expr} "
                        f"là số thực hữu hạn: {v_msg}"
                    )
                    return SolutionResponse(
                        status=SolutionStatus.UNVERIFIED,
                        verification=VerificationResult(
                            status=VerificationStatus.UNVERIFIED,
                            method="initial_condition_domain_unverified",
                            details=msg,
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        domain_restrictions=tuple(domain_restrictions),
                        original_domain_latex=orig_domain_latex,
                        normalized_domain_latex=norm_domain_latex,
                        domain_completeness=overall_comp,
                        warnings=(msg,),
                        execution_time_ms=elapsed,
                    )

            # Origin is a singular point
            if t0_cand.is_zero is True or _prove_symbolic_zero(t0_cand):
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = (
                    f"Điểm ban đầu {var}0 = 0 là điểm kỳ dị (singular point) của phương trình vi phân Euler–Cauchy "
                    f"(hệ số dẫn a({var}) = {expr_to_latex(a_expr)} triệt tiêu tại {var} = 0). "
                    f"Bài toán Cauchy tại điểm kỳ dị {var}0 = 0 là bài toán suy biến, không thể giải bằng phương pháp chuẩn tắc trong phạm vi EC1."
                )
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="singular_point_initial_condition",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )

            # Validate initial condition against preserved original denominators, constraints, and leading coeffs
            orig_stat, orig_err = evaluate_initial_point_domain(
                None,
                var,
                dep_var,
                t0_cand,
                y0_cand,
                original_denominators=parsed.original_denominators,
                leading_coeffs=parsed.leading_coeffs,
                source_constraints=getattr(parsed, "original_domain_constraints", ()),
                allow_complex=False,
            )
            if orig_stat == "invalid":
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.INVALID_INPUT,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="initial_point_domain_validation",
                        details=f"Điều kiện ban đầu {var}0 = {t0_cand} vi phạm miền xác định ban đầu: {orig_err}",
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(f"Điều kiện ban đầu không hợp lệ: {orig_err}",),
                    execution_time_ms=elapsed,
                )
            if orig_stat == "unknown":
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = f"Không thể xác nhận điều kiện ban đầu ({t0_cand}, {y0_cand}, {v0_cand}): {orig_err}"
                return SolutionResponse(
                    status=SolutionStatus.UNVERIFIED,
                    verification=VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="initial_condition_domain_unverified",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )

            if g_expr is not None:
                g_dom_ok, g_dom_err = validate_initial_point_against_domain(
                    t0_cand, g_expr, var, tuple(domain_restrictions)
                )
                if not g_dom_ok:
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    msg = g_dom_err or f"Điểm ban đầu {var}0 = {t0_cand} không hợp lệ với vế phải g({var})."
                    return SolutionResponse(
                        status=SolutionStatus.INVALID_INPUT,
                        verification=VerificationResult(
                            status=VerificationStatus.NOT_APPLICABLE,
                            method="initial_point_domain_validation",
                            details=msg,
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        domain_restrictions=tuple(domain_restrictions),
                        original_domain_latex=orig_domain_latex,
                        normalized_domain_latex=norm_domain_latex,
                        domain_completeness=overall_comp,
                        warnings=(msg,),
                        execution_time_ms=elapsed,
                    )

            t0_val = t0_cand
            y0_val = y0_cand
            v0_val = v0_cand

        # 3. Domain and Interval Analysis using structured parser interval metadata
        interval_raw = parsed.interval
        interval_spec: ParsedIntervalConstraint | None = getattr(parsed, "interval_spec", None)
        if not interval_raw and "interval" in request.parameters and request.parameters["interval"]:
            interval_raw = str(request.parameters["interval"]).strip()
            interval_spec = parse_interval_constraint(interval_raw, variable=var.name)
        elif interval_raw and interval_spec is None:
            interval_spec = parse_interval_constraint(interval_raw, variable=var.name)

        requested_interval: sp.Interval | None = None
        is_negative_domain = False

        if interval_spec is not None:
            if not interval_spec.is_supported or interval_spec.interval is None:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = (
                    interval_spec.error
                    or f"Khoảng xác định '{interval_raw}' không được hỗ trợ hoặc không hợp lệ."
                )
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="unsupported_interval_syntax",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )

            requested_interval = interval_spec.interval
            contains_zero = requested_interval.contains(sp.Integer(0))
            if contains_zero is sp.S.true or contains_zero is True:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = (
                    f"Khoảng xác định yêu cầu '{interval_raw}' chứa điểm kỳ dị {var} = 0 "
                    "của phương trình vi phân Euler–Cauchy. Nghiệm không tồn tại qua điểm kỳ dị này."
                )
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="singular_point_interval",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )
            if contains_zero is not sp.S.false and contains_zero is not False:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = f"Không thể xác định khoảng '{interval_raw}' có chứa điểm kỳ dị {var} = 0 hay không."
                return SolutionResponse(
                    status=SolutionStatus.UNVERIFIED,
                    verification=VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="singular_point_interval_unresolved",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )

            if norm_comp != DomainCompleteness.EXACT or norm_domain is None:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = (
                    f"Không thể xác minh khoảng '{interval_raw}' nằm trọn trong miền xác định ban đầu "
                    "do miền xác định phương trình chưa được phân tích đầy đủ."
                )
                return SolutionResponse(
                    status=SolutionStatus.UNVERIFIED,
                    verification=VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="source_domain_unverified",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )

            is_sub = requested_interval.is_subset(norm_domain)
            if is_sub is None:
                try:
                    diff_set = sp.Complement(requested_interval, norm_domain)
                    if diff_set == sp.S.EmptySet:
                        is_sub = True
                    elif (
                        isinstance(diff_set, (sp.FiniteSet, sp.Interval, sp.Union))
                        and not diff_set.has(sp.ConditionSet)
                    ):
                        is_sub = False
                except Exception:
                    is_sub = None
            if is_sub is False:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = (
                    f"Khoảng xác định yêu cầu '{interval_raw}' vượt ra ngoài miền xác định hợp lệ của phương trình "
                    f"({norm_domain_latex or 'miền chuẩn hóa'})."
                )
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="source_domain_interval_violation",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )
            if is_sub is not True:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = f"Không thể xác nhận khoảng '{interval_raw}' là tập con của miền xác định phương trình."
                return SolutionResponse(
                    status=SolutionStatus.UNVERIFIED,
                    verification=VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="source_domain_interval_unverified",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )

            if requested_interval.start.is_nonnegative is True:
                is_negative_domain = False
            elif requested_interval.end.is_nonpositive is True:
                is_negative_domain = True
            else:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = f"Không thể xác định dấu của khoảng xác định '{interval_raw}'."
                return SolutionResponse(
                    status=SolutionStatus.UNVERIFIED,
                    verification=VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="interval_sign_unresolved",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )

        active_ivp_interval: sp.Interval | None = None
        if t0_val is not None:
            if t0_val.is_negative is True:
                t0_is_neg = True
            elif t0_val.is_positive is True:
                t0_is_neg = False
            else:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = f"Không thể xác định dấu của điểm ban đầu {var}0 = {t0_val} bằng phương pháp ký hiệu."
                return SolutionResponse(
                    status=SolutionStatus.UNVERIFIED,
                    verification=VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="initial_condition_sign_unresolved",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )

            if requested_interval is not None:
                in_req = requested_interval.contains(t0_val)
                if in_req is sp.S.false or in_req is False:
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    msg = (
                        f"Điểm ban đầu {var}0 = {t0_val} nằm ngoài khoảng xác định yêu cầu "
                        f"'{interval_raw}' ({format_interval_latex(requested_interval)})."
                    )
                    return SolutionResponse(
                        status=SolutionStatus.CANNOT_SOLVE,
                        verification=VerificationResult(
                            status=VerificationStatus.NOT_APPLICABLE,
                            method="initial_condition_domain_mismatch",
                            details=msg,
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        domain_restrictions=tuple(domain_restrictions),
                        original_domain_latex=orig_domain_latex,
                        normalized_domain_latex=norm_domain_latex,
                        domain_completeness=overall_comp,
                        warnings=(msg,),
                        execution_time_ms=elapsed,
                    )
                if in_req is not sp.S.true and in_req is not True:
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    msg = f"Không thể kiểm chứng {var}0 = {t0_val} có thuộc khoảng '{interval_raw}' hay không."
                    return SolutionResponse(
                        status=SolutionStatus.UNVERIFIED,
                        verification=VerificationResult(
                            status=VerificationStatus.UNVERIFIED,
                            method="initial_condition_domain_unverified",
                            details=msg,
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        domain_restrictions=tuple(domain_restrictions),
                        original_domain_latex=orig_domain_latex,
                        normalized_domain_latex=norm_domain_latex,
                        domain_completeness=overall_comp,
                        warnings=(msg,),
                        execution_time_ms=elapsed,
                    )
                active_ivp_interval = requested_interval
            else:
                if norm_comp != DomainCompleteness.EXACT or norm_domain is None:
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    msg = f"Không thể xác định khoảng liên thông chứa {var}0 = {t0_val} từ miền xác định ban đầu."
                    return SolutionResponse(
                        status=SolutionStatus.UNVERIFIED,
                        verification=VerificationResult(
                            status=VerificationStatus.UNVERIFIED,
                            method="source_domain_unverified",
                            details=msg,
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        domain_restrictions=tuple(domain_restrictions),
                        original_domain_latex=orig_domain_latex,
                        normalized_domain_latex=norm_domain_latex,
                        domain_completeness=overall_comp,
                        warnings=(msg,),
                        execution_time_ms=elapsed,
                    )
                for iv in connected_intervals:
                    if iv.contains(t0_val) is sp.S.true:
                        active_ivp_interval = iv
                        break
                if active_ivp_interval is None:
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    msg = f"Điểm ban đầu {var}0 = {t0_val} không thuộc khoảng liên thông hợp lệ nào của phương trình."
                    return SolutionResponse(
                        status=SolutionStatus.INVALID_INPUT,
                        verification=VerificationResult(
                            status=VerificationStatus.NOT_APPLICABLE,
                            method="initial_point_domain_validation",
                            details=msg,
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        domain_restrictions=tuple(domain_restrictions),
                        original_domain_latex=orig_domain_latex,
                        normalized_domain_latex=norm_domain_latex,
                        domain_completeness=overall_comp,
                        warnings=(msg,),
                        execution_time_ms=elapsed,
                    )

            is_negative_domain = t0_is_neg

        # 4. Indicial Equation & Discriminant
        # A*m*(m-1) + B*m + C = 0  =>  A*m^2 + (B - A)*m + C = 0
        m_sym = sp.Symbol("m")
        a_ind = A
        b_ind = sp.simplify(B - A)
        c_ind = C

        indicial_poly = sp.simplify(a_ind * m_sym**2 + b_ind * m_sym + c_ind)
        delta = sp.simplify(b_ind**2 - 4 * a_ind * c_ind)

        # Conservative classification strictly via SymPy mathematical assumptions
        root_case: str  # "DISTINCT", "REPEATED", "COMPLEX"
        m1_val: sp.Expr
        m2_val: sp.Expr
        alpha_val: sp.Expr | None = None
        beta_val: sp.Expr | None = None

        if delta.is_positive is True:
            root_case = "DISTINCT"
            m1_val = sp.simplify((-b_ind + sp.sqrt(delta)) / (2 * a_ind))
            m2_val = sp.simplify((-b_ind - sp.sqrt(delta)) / (2 * a_ind))
        elif delta.is_zero is True:
            root_case = "REPEATED"
            m1_val = sp.simplify(-b_ind / (2 * a_ind))
            m2_val = m1_val
        elif delta.is_negative is True:
            root_case = "COMPLEX"
            alpha_val = sp.simplify(-b_ind / (2 * a_ind))
            beta_val = sp.simplify(sp.sqrt(-delta) / (2 * sp.Abs(a_ind)))
            m1_val = alpha_val + sp.I * beta_val
            m2_val = alpha_val - sp.I * beta_val
        else:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            msg = f"Biệt thức Delta = {delta} không thể xác định dấu bằng phương pháp ký hiệu."
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="indicial_discriminant_unresolved",
                    details=msg,
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                domain_restrictions=tuple(domain_restrictions),
                original_domain_latex=orig_domain_latex,
                normalized_domain_latex=norm_domain_latex,
                domain_completeness=overall_comp,
                warnings=(msg,),
                execution_time_ms=elapsed,
            )

        # 5. Build fundamental solutions helper
        def get_fundamentals(is_neg: bool) -> tuple[sp.Expr, sp.Expr, sp.Expr]:
            """Return (y1, y2, W) on either positive (t > 0) or negative (t < 0) domain."""
            base_expr = -var if is_neg else var
            if root_case == "DISTINCT":
                y1 = base_expr**m1_val
                y2 = base_expr**m2_val
            elif root_case == "REPEATED":
                y1 = base_expr**m1_val
                y2 = (base_expr**m1_val) * sp.log(base_expr)
            else:  # COMPLEX
                assert alpha_val is not None and beta_val is not None
                exp_factor = base_expr**alpha_val
                y1 = exp_factor * sp.cos(beta_val * sp.log(base_expr))
                y2 = exp_factor * sp.sin(beta_val * sp.log(base_expr))

            # Simplify fundamental solutions
            y1 = sp.simplify(y1)
            y2 = sp.simplify(y2)
            W = sp.simplify(y1 * sp.diff(y2, var) - sp.diff(y1, var) * y2)
            return y1, y2, W

        # 6. Branch Solutions Construction
        c1_sym = sp.Symbol("C1")
        c2_sym = sp.Symbol("C2")

        steps: list[SolutionStep] = []
        response_warnings: list[str] = []

        if is_cauchy_request and t0_val is not None and y0_val is not None and v0_val is not None:
            # Cauchy IVP Mode
            assert active_ivp_interval is not None
            y1_active, y2_active, W_active = get_fundamentals(is_negative_domain)
            dom_int = (active_ivp_interval.start, active_ivp_interval.end)
            if active_ivp_interval == sp.Interval.open(-sp.oo, 0):
                dom_desc = f"{var} < 0"
            elif active_ivp_interval == sp.Interval.open(0, sp.oo):
                dom_desc = f"{var} > 0"
            else:
                dom_desc = f"{var} \\in {format_interval_latex(active_ivp_interval)}"
            domain_restrictions.append(f"Khoảng liên thông chứa điểm ban đầu {var}0 = {t0_val}: {dom_desc}.")

            vop_active: VariationOfParametersResult | None = None
            yp_part = sp.Integer(0)
            yp_at_t0 = sp.Integer(0)
            dyp_at_t0 = sp.Integer(0)
            if g_expr is not None:
                vop_active = _compute_euler_cauchy_vop(
                    A=A,
                    B=B,
                    C=C,
                    g_expr=g_expr,
                    y1_fund=y1_active,
                    y2_fund=y2_active,
                    W_fund=W_active,
                    var=var,
                    is_neg=is_negative_domain,
                    initial_point=None,
                )
                if vop_active.is_integral_form:
                    vop_active = _compute_euler_cauchy_vop(
                        A=A,
                        B=B,
                        C=C,
                        g_expr=g_expr,
                        y1_fund=y1_active,
                        y2_fund=y2_active,
                        W_fund=W_active,
                        var=var,
                        is_neg=is_negative_domain,
                        initial_point=t0_val,
                    )
                    yp_part = vop_active.particular_solution
                    yp_at_t0 = sp.Integer(0)
                    dyp_at_t0 = sp.Integer(0)
                    response_warnings.append(
                        f"Nghiệm riêng cho vế phải g({var}) = {expr_to_latex(g_expr)} không có nguyên hàm sơ cấp tường minh; "
                        f"được biểu diễn chính xác bằng tích phân xác định neo tại {var}0 = {t0_val}."
                    )
                else:
                    yp_part = vop_active.particular_solution
                    d_yp_part = sp.diff(yp_part, var)
                    yp_at_t0 = sp.simplify(yp_part.subs(var, t0_val))
                    dyp_at_t0 = sp.simplify(d_yp_part.subs(var, t0_val))

            # Solve linear system for C1, C2:
            # C1*y1(t0) + C2*y2(t0) = y0 - yp(t0)
            # C1*y1'(t0) + C2*y2'(t0) = v0 - yp'(t0)
            dy1_active = sp.diff(y1_active, var)
            dy2_active = sp.diff(y2_active, var)

            y1_0 = sp.simplify(y1_active.subs(var, t0_val))
            y2_0 = sp.simplify(y2_active.subs(var, t0_val))
            dy1_0 = sp.simplify(dy1_active.subs(var, t0_val))
            dy2_0 = sp.simplify(dy2_active.subs(var, t0_val))

            rhs_y0 = sp.simplify(y0_val - yp_at_t0)
            rhs_v0 = sp.simplify(v0_val - dyp_at_t0)

            det_M = sp.simplify(y1_0 * dy2_0 - y2_0 * dy1_0)
            if det_M.is_zero is True or _prove_symbolic_zero(det_M):
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = f"Định thức hệ phương trình Cauchy triệt tiêu tại {var}0 = {t0_val} (Degenerate Cauchy system)."
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="degenerate_cauchy_system",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )
            if det_M.is_nonzero is not True:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = f"Không thể xác nhận định thức hệ phương trình Cauchy tại {var}0 = {t0_val} khác 0 ({det_M})."
                return SolutionResponse(
                    status=SolutionStatus.UNVERIFIED,
                    verification=VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="cauchy_determinant_unresolved",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )

            val_c1 = sp.simplify((rhs_y0 * dy2_0 - rhs_v0 * y2_0) / det_M)
            val_c2 = sp.simplify((y1_0 * rhs_v0 - dy1_0 * rhs_y0) / det_M)
            if vop_active is None:
                particular_sol = val_c1 * y1_active + val_c2 * y2_active
            elif vop_active.is_integral_form:
                particular_sol = (val_c1 * y1_active + val_c2 * y2_active) + yp_part
            else:
                particular_sol = sp.simplify(val_c1 * y1_active + val_c2 * y2_active + yp_part)

            # Independent Verification including fundamental-system Wronskian gate
            v_res = self.verifier.verify_second_order(
                solution=particular_sol,
                variable=var,
                a_coeff=parsed.a_coeff,
                b_coeff=parsed.b_coeff,
                c_coeff=parsed.c_coeff,
                forcing_expr=g_expr,
                initial_condition=(t0_val, y0_val),
                initial_derivative=(t0_val, v0_val),
                domain_interval=dom_int,
                domain_restrictions=tuple(domain_restrictions),
                fundamental_solutions=(y1_active, y2_active),
                left_open=active_ivp_interval.left_open,
                right_open=active_ivp_interval.right_open,
            )

            branch_identity = f"Nhánh {dom_desc} (Cauchy IVP)"
            branch_sol = BranchSolution(
                expression=particular_sol,
                solution_str=f"{dep_var}({var}) = {particular_sol}",
                solution_latex=f"{dep_var}({var}) = {expr_to_latex(particular_sol)}",
                branch_identity=branch_identity,
                integration_constant=None,
                integration_constant_val=None,
                domain_interval=dom_int,
                domain_restrictions=tuple(domain_restrictions),
                verification=v_res,
                left_open=bool(active_ivp_interval.left_open),
                right_open=bool(active_ivp_interval.right_open),
                domain_set=active_ivp_interval,
                initial_condition_status=f"y({t0_val}) = {y0_val}, y'({t0_val}) = {v0_val}",
            )
            branch_solutions = (branch_sol,)

            final_res_str = f"{dep_var}({var}) = {particular_sol}"
            final_latex_str = f"{dep_var}({var}) = {expr_to_latex(particular_sol)}"

            # Pedagogical steps
            steps = self._build_solution_steps(
                var=var,
                dep_var=dep_var,
                A=A,
                B=B,
                C=C,
                g_expr=g_expr,
                indicial_poly=indicial_poly,
                delta=delta,
                root_case=root_case,
                m1=m1_val,
                m2=m2_val,
                alpha=alpha_val,
                beta=beta_val,
                y1_fund=y1_active,
                y2_fund=y2_active,
                W_fund=W_active,
                is_neg=is_negative_domain,
                dom_desc=dom_desc,
                c1_sym=c1_sym,
                c2_sym=c2_sym,
                vop_res=vop_active,
                t0=t0_val,
                y0=y0_val,
                v0=v0_val,
                val_c1=val_c1,
                val_c2=val_c2,
                particular_sol=particular_sol,
                yp_at_t0=yp_at_t0,
                dyp_at_t0=dyp_at_t0,
                v_res=v_res,
            )

        elif requested_interval is not None:
            # Explicit single-interval general solution preserving exact requested interval
            dom_int = (requested_interval.start, requested_interval.end)
            if requested_interval == sp.Interval.open(-sp.oo, 0):
                dom_desc = f"{var} < 0"
            elif requested_interval == sp.Interval.open(0, sp.oo):
                dom_desc = f"{var} > 0"
            else:
                dom_desc = f"{var} \\in {format_interval_latex(requested_interval)}"
            domain_restrictions.append(f"Khoảng xác định được chọn: {dom_desc}.")

            y1_active, y2_active, W_active = get_fundamentals(is_negative_domain)
            vop_active = None
            gen_sol = c1_sym * y1_active + c2_sym * y2_active
            if g_expr is not None:
                vop_active = _compute_euler_cauchy_vop(
                    A=A,
                    B=B,
                    C=C,
                    g_expr=g_expr,
                    y1_fund=y1_active,
                    y2_fund=y2_active,
                    W_fund=W_active,
                    var=var,
                    is_neg=is_negative_domain,
                    initial_point=None,
                )
                gen_sol = gen_sol + vop_active.particular_solution
                if vop_active.is_integral_form:
                    response_warnings.append(
                        f"Nghiệm riêng cho vế phải g({var}) = {expr_to_latex(g_expr)} không có nguyên hàm sơ cấp tường minh; "
                        "hệ thống bảo toàn chính xác biểu diễn tích phân ký hiệu."
                    )

            v_res = self.verifier.verify_second_order(
                solution=gen_sol,
                variable=var,
                a_coeff=parsed.a_coeff,
                b_coeff=parsed.b_coeff,
                c_coeff=parsed.c_coeff,
                forcing_expr=g_expr,
                c1_sym=c1_sym,
                c2_sym=c2_sym,
                domain_interval=dom_int,
                domain_restrictions=tuple(domain_restrictions),
                fundamental_solutions=(y1_active, y2_active),
                left_open=requested_interval.left_open,
                right_open=requested_interval.right_open,
            )

            branch_identity = f"Nhánh {dom_desc}"
            branch_sol = BranchSolution(
                expression=gen_sol,
                solution_str=f"{dep_var}({var}) = {gen_sol}",
                solution_latex=f"{dep_var}({var}) = {expr_to_latex(gen_sol)}",
                branch_identity=branch_identity,
                integration_constant=sp.Symbol("C1, C2"),
                domain_interval=dom_int,
                domain_restrictions=tuple(domain_restrictions),
                verification=v_res,
                left_open=bool(requested_interval.left_open),
                right_open=bool(requested_interval.right_open),
                domain_set=requested_interval,
            )
            branch_solutions = (branch_sol,)

            final_res_str = f"{dep_var}({var}) = {gen_sol}"
            final_latex_str = f"{dep_var}({var}) = {expr_to_latex(gen_sol)}"

            steps = self._build_solution_steps(
                var=var,
                dep_var=dep_var,
                A=A,
                B=B,
                C=C,
                g_expr=g_expr,
                indicial_poly=indicial_poly,
                delta=delta,
                root_case=root_case,
                m1=m1_val,
                m2=m2_val,
                alpha=alpha_val,
                beta=beta_val,
                y1_fund=y1_active,
                y2_fund=y2_active,
                W_fund=W_active,
                is_neg=is_negative_domain,
                dom_desc=dom_desc,
                c1_sym=c1_sym,
                c2_sym=c2_sym,
                vop_res=vop_active,
                v_res=v_res,
            )

        else:
            # Natural domain derived from preserved source domain minus singularities
            if norm_comp != DomainCompleteness.EXACT or norm_domain is None or other_comps:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = (
                    "Không thể phân giải đầy đủ các khoảng liên thông của miền xác định "
                    "từ điều kiện ban đầu của phương trình."
                )
                return SolutionResponse(
                    status=SolutionStatus.UNVERIFIED,
                    verification=VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="source_domain_unverified",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )

            if not connected_intervals:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                msg = "Miền xác định hợp lệ của phương trình rỗng; không tồn tại khoảng liên thông để xây dựng nghiệm."
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="empty_solution_domain",
                        details=msg,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    original_domain_latex=orig_domain_latex,
                    normalized_domain_latex=norm_domain_latex,
                    domain_completeness=overall_comp,
                    warnings=(msg,),
                    execution_time_ms=elapsed,
                )

            branch_list: list[BranchSolution] = []
            branch_step_entries: list[tuple[sp.Interval, sp.Expr, sp.Expr, sp.Expr, sp.Symbol, sp.Symbol]] = []
            branch_vops: list[VariationOfParametersResult] = []
            branch_verifs: list[VerificationResult] = []
            res_parts: list[str] = []
            ltx_cases: list[str] = []

            for idx, iv in enumerate(connected_intervals):
                if iv.start.is_nonnegative is True:
                    is_neg_iv = False
                elif iv.end.is_nonpositive is True:
                    is_neg_iv = True
                else:
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    msg = f"Khoảng liên thông {iv} chứa hoặc không tách biệt hoàn toàn với điểm kỳ dị {var} = 0."
                    return SolutionResponse(
                        status=SolutionStatus.UNVERIFIED,
                        verification=VerificationResult(
                            status=VerificationStatus.UNVERIFIED,
                            method="singular_point_interval_unresolved",
                            details=msg,
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        domain_restrictions=tuple(domain_restrictions),
                        original_domain_latex=orig_domain_latex,
                        normalized_domain_latex=norm_domain_latex,
                        domain_completeness=overall_comp,
                        warnings=(msg,),
                        execution_time_ms=elapsed,
                    )

                c_a = sp.Symbol(f"C{2 * idx + 1}")
                c_b = sp.Symbol(f"C{2 * idx + 2}")
                y1_b, y2_b, W_b = get_fundamentals(is_neg=is_neg_iv)
                gen_sol_b = c_a * y1_b + c_b * y2_b
                if g_expr is not None:
                    vop_b = _compute_euler_cauchy_vop(
                        A=A,
                        B=B,
                        C=C,
                        g_expr=g_expr,
                        y1_fund=y1_b,
                        y2_fund=y2_b,
                        W_fund=W_b,
                        var=var,
                        is_neg=is_neg_iv,
                        initial_point=None,
                    )
                    gen_sol_b = gen_sol_b + vop_b.particular_solution
                    branch_vops.append(vop_b)
                    if vop_b.is_integral_form:
                        response_warnings.append(
                            f"Nghiệm riêng cho vế phải g({var}) = {expr_to_latex(g_expr)} không có nguyên hàm sơ cấp tường minh; "
                            "hệ thống bảo toàn chính xác biểu diễn tích phân ký hiệu."
                        )

                v_res_b = self.verifier.verify_second_order(
                    solution=gen_sol_b,
                    variable=var,
                    a_coeff=parsed.a_coeff,
                    b_coeff=parsed.b_coeff,
                    c_coeff=parsed.c_coeff,
                    forcing_expr=g_expr,
                    c1_sym=c_a,
                    c2_sym=c_b,
                    domain_interval=(iv.start, iv.end),
                    domain_restrictions=tuple(domain_restrictions),
                    fundamental_solutions=(y1_b, y2_b),
                    left_open=iv.left_open,
                    right_open=iv.right_open,
                )
                branch_verifs.append(v_res_b)

                if iv == sp.Interval.open(0, sp.oo):
                    iv_label = f"{var} > 0"
                    iv_ltx_cond = f"{var} > 0"
                elif iv == sp.Interval.open(-sp.oo, 0):
                    iv_label = f"{var} < 0"
                    iv_ltx_cond = f"{var} < 0"
                else:
                    iv_ltx = format_interval_latex(iv)
                    iv_label = f"{var} in {iv_ltx}"
                    iv_ltx_cond = rf"{var} \in {iv_ltx}"

                branch_list.append(
                    BranchSolution(
                        expression=gen_sol_b,
                        solution_str=f"{dep_var}({var}) = {gen_sol_b}",
                        solution_latex=f"{dep_var}({var}) = {expr_to_latex(gen_sol_b)}",
                        branch_identity=f"Nhánh {iv_label}",
                        integration_constant=sp.Symbol(f"{c_a.name}, {c_b.name}"),
                        domain_interval=(iv.start, iv.end),
                        domain_restrictions=tuple(domain_restrictions) + (f"Khoảng liên thông {iv_label}",),
                        verification=v_res_b,
                        left_open=bool(iv.left_open),
                        right_open=bool(iv.right_open),
                        domain_set=iv,
                    )
                )
                branch_step_entries.append((iv, gen_sol_b, y1_b, y2_b, c_a, c_b))
                res_parts.append(f"{dep_var}({var}) = {gen_sol_b} (với {iv_label})")
                ltx_cases.append(rf"{expr_to_latex(gen_sol_b)} & \text{{khi }} {iv_ltx_cond}")

            branch_solutions = tuple(branch_list)

            # Overall verification
            if all(v.status == VerificationStatus.VERIFIED for v in branch_verifs):
                v_res = VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="euler_cauchy_all_branches_verified",
                    details="Tất cả các nhánh nghiệm trên từng khoảng liên thông đều thỏa mãn phương trình vi phân Euler–Cauchy và hệ nghiệm cơ bản độc lập tuyến tính.",
                )
            elif any(v.status == VerificationStatus.FAILED for v in branch_verifs):
                v_res = next(v for v in branch_verifs if v.status == VerificationStatus.FAILED)
            else:
                v_res = VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="euler_cauchy_branch_inconclusive",
                    details="Không thể kiểm chứng hoàn toàn tất cả các nhánh nghiệm bằng phương pháp ký hiệu.",
                )

            if len(branch_list) == 1:
                final_res_str = branch_list[0].solution_str
                final_latex_str = branch_list[0].solution_latex
                rep_iv = connected_intervals[0]
                rep_is_neg = rep_iv.end.is_nonpositive is True
                rep_y1, rep_y2, rep_W = get_fundamentals(is_neg=rep_is_neg)
                rep_vop = branch_vops[0] if branch_vops else None
                steps = self._build_solution_steps(
                    var=var,
                    dep_var=dep_var,
                    A=A,
                    B=B,
                    C=C,
                    g_expr=g_expr,
                    indicial_poly=indicial_poly,
                    delta=delta,
                    root_case=root_case,
                    m1=m1_val,
                    m2=m2_val,
                    alpha=alpha_val,
                    beta=beta_val,
                    y1_fund=rep_y1,
                    y2_fund=rep_y2,
                    W_fund=rep_W,
                    is_neg=rep_is_neg,
                    dom_desc=norm_domain_latex or f"{var} \\in {format_interval_latex(rep_iv)}",
                    c1_sym=c1_sym,
                    c2_sym=c2_sym,
                    vop_res=rep_vop,
                    v_res=v_res,
                )
            else:
                final_res_str = "; ".join(res_parts)
                final_latex_str = (
                    rf"{dep_var}({var}) = \begin{{cases}} "
                    + r" \\ ".join(ltx_cases)
                    + r" \end{cases}"
                )
                rep_iv = connected_intervals[0]
                rep_is_neg = rep_iv.end.is_nonpositive is True
                rep_y1, rep_y2, rep_W = get_fundamentals(is_neg=rep_is_neg)
                rep_vop = branch_vops[0] if branch_vops else None
                steps = self._build_solution_steps(
                    var=var,
                    dep_var=dep_var,
                    A=A,
                    B=B,
                    C=C,
                    g_expr=g_expr,
                    indicial_poly=indicial_poly,
                    delta=delta,
                    root_case=root_case,
                    m1=m1_val,
                    m2=m2_val,
                    alpha=alpha_val,
                    beta=beta_val,
                    y1_fund=rep_y1,
                    y2_fund=rep_y2,
                    W_fund=rep_W,
                    is_neg=rep_is_neg,
                    dom_desc=norm_domain_latex or f"{var} \\in (-\\infty, 0) \\cup (0, \\infty)",
                    c1_sym=c1_sym,
                    c2_sym=c2_sym,
                    vop_res=rep_vop,
                    branch_vops=tuple(branch_vops) if branch_vops else None,
                    v_res=v_res,
                    multi_branch=tuple(branch_step_entries),
                )

        # Status resolution
        if v_res.status == VerificationStatus.VERIFIED:
            sol_status = SolutionStatus.SUCCESS
        elif v_res.status == VerificationStatus.FAILED:
            sol_status = SolutionStatus.DISCREPANCY_DETECTED
        else:
            sol_status = SolutionStatus.UNVERIFIED

        elapsed = (time.perf_counter() - t0_start) * 1000.0

        return SolutionResponse(
            status=sol_status,
            verification=v_res,
            raw_input=request.raw_input,
            canonical_input=parsed.canonical_eq,
            final_result=final_res_str,
            final_latex=final_latex_str,
            steps=tuple(steps),
            domain_restrictions=tuple(dict.fromkeys(domain_restrictions)),
            warnings=tuple(dict.fromkeys(response_warnings)),
            execution_time_ms=elapsed,
            branch_solutions=branch_solutions,
            original_domain_latex=orig_domain_latex,
            normalized_domain_latex=norm_domain_latex,
            domain_completeness=overall_comp,
        )

    def _build_vop_pedagogical_steps(
        self,
        *,
        step_idx: int,
        var: sp.Symbol,
        dep_var: sp.Symbol,
        A: sp.Expr,
        B: sp.Expr,
        C: sp.Expr,
        g_expr: sp.Expr,
        y1_fund: sp.Expr,
        y2_fund: sp.Expr,
        W_fund: sp.Expr,
        vop_res: VariationOfParametersResult,
    ) -> tuple[list[SolutionStep], int]:
        """Build Variation of Parameters steps for normalized Euler–Cauchy equation."""
        steps: list[SolutionStep] = []
        p_norm = sp.simplify(B / (A * var))
        q_norm = sp.simplify(C / (A * var**2))
        r_norm = sp.simplify(g_expr / (A * var**2))

        p_ltx = expr_to_latex(p_norm)
        q_ltx = expr_to_latex(q_norm)
        r_ltx = expr_to_latex(r_norm)
        g_ltx = expr_to_latex(g_expr)

        # Normalize: y'' + P(t)y' + Q(t)y = R(t)
        norm_eq_ltx = rf"{dep_var}'' + \left({p_ltx}\right){dep_var}' + \left({q_ltx}\right){dep_var} = {r_ltx}"
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Chuẩn hóa và phương pháp Biến thiên hằng số",
                title="Chuẩn hóa phương trình và thiết lập Biến thiên hằng số",
                description=(
                    f"Chia cả hai vế của phương trình cho hệ số dẫn $A{var}^2 = {expr_to_latex(A * var**2)}$ (${var} \\ne 0$) "
                    f"để đưa về dạng chuẩn tắc $y'' + P({var})y' + Q({var})y = R({var})$:\n"
                    f"$$P({var}) = \\frac{{B}}{{A{var}}} = {p_ltx}, \\quad "
                    f"Q({var}) = \\frac{{C}}{{A{var}^2}} = {q_ltx}, \\quad "
                    f"R({var}) = \\frac{{g({var})}}{{A{var}^2}} = {r_ltx}$$\n"
                    f"Áp dụng phương pháp Biến thiên hằng số (Lagrange) với nghiệm riêng có dạng "
                    f"$y_p({var}) = u_1({var})y_1({var}) + u_2({var})y_2({var})$."
                ),
                content=ExpressionStepContent(
                    expression_before=f"{A}*{var}^2*y'' + {B}*{var}*y' + {C}*y = {g_expr}",
                    expression_after=f"y'' + ({p_norm})*y' + ({q_norm})*y = {r_norm}",
                    latex_before=rf"{expr_to_latex(A)}\,{var}^2\,y'' + {expr_to_latex(B)}\,{var}\,y' + {expr_to_latex(C)}\,y = {g_ltx}",
                    latex_after=norm_eq_ltx,
                ),
                equation_latex=norm_eq_ltx,
            )
        )
        step_idx += 1

        # Derivatives u1', u2' from Cramer's rule
        u1p_ltx = expr_to_latex(vop_res.u1_prime)
        u2p_ltx = expr_to_latex(vop_res.u2_prime)
        w_ltx = expr_to_latex(W_fund)
        y1_ltx = expr_to_latex(y1_fund)
        y2_ltx = expr_to_latex(y2_fund)
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Đạo hàm hàm biến thiên",
                title="Giải hệ Lagrange tìm đạo hàm u1' và u2'",
                description=(
                    f"Với điều kiện phụ trợ Lagrange $u_1'({var})y_1({var}) + u_2'({var})y_2({var}) = 0$ "
                    f"và $u_1'({var})y_1'({var}) + u_2'({var})y_2'({var}) = R({var})$, quy tắc Cramer cho:\n"
                    f"$$u_1'({var}) = -\\frac{{y_2({var})R({var})}}{{W({var})}} = -\\frac{{({y2_ltx})({r_ltx})}}{{{w_ltx}}} = {u1p_ltx}$$\n"
                    f"$$u_2'({var}) = \\frac{{y_1({var})R({var})}}{{W({var})}} = \\frac{{({y1_ltx})({r_ltx})}}{{{w_ltx}}} = {u2p_ltx}$$"
                ),
                content=ExpressionStepContent(
                    expression_before="u1' = -y2*R/W, u2' = y1*R/W",
                    expression_after=f"u1' = {vop_res.u1_prime}, u2' = {vop_res.u2_prime}",
                    latex_before=r"u_1' = -\frac{y_2 R}{W}, \quad u_2' = \frac{y_1 R}{W}",
                    latex_after=rf"u_1'({var}) = {u1p_ltx}, \quad u_2'({var}) = {u2p_ltx}",
                ),
                equation_latex=rf"u_1'({var}) = {u1p_ltx}, \quad u_2'({var}) = {u2p_ltx}",
            )
        )
        step_idx += 1

        # Integration to obtain u1, u2
        u1_ltx = expr_to_latex(vop_res.u1_expr)
        u2_ltx = expr_to_latex(vop_res.u2_expr)
        if vop_res.initial_point is not None:
            t0_ltx = expr_to_latex(vop_res.initial_point)
            int_note = (
                f"Tích phân $u_1'({var})$ và $u_2'({var})$ không biểu diễn được qua hàm sơ cấp hữu hạn; "
                f"bảo toàn chính xác dưới dạng tích phân xác định neo tại ${var}_0 = {t0_ltx}$ ($u_1({t0_ltx}) = u_2({t0_ltx}) = 0$):"
            )
        elif vop_res.is_integral_form:
            int_note = (
                "Một hoặc cả hai tích phân không có nguyên hàm sơ cấp tường minh; "
                "bảo toàn chính xác dạng tích phân ký hiệu:"
            )
        else:
            int_note = (
                f"Lấy nguyên hàm theo biến ${var}$ trên khoảng liên thông đang xét "
                "(các hằng số tích phân tùy ý đã được gộp vào nghiệm thuần nhất $y_c$):"
            )

        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Tích phân hàm biến thiên",
                title="Tính tích phân xác định các hàm u1 và u2",
                description=(
                    f"{int_note}\n"
                    f"$$u_1({var}) = {u1_ltx}$$\n"
                    f"$$u_2({var}) = {u2_ltx}$$"
                ),
                content=ExpressionStepContent(
                    expression_before=f"u1 = Integral({vop_res.u1_prime}, {var}), u2 = Integral({vop_res.u2_prime}, {var})",
                    expression_after=f"u1 = {vop_res.u1_expr}, u2 = {vop_res.u2_expr}",
                    latex_before=rf"u_1 = \int \left({u1p_ltx}\right)d{var}, \quad u_2 = \int \left({u2p_ltx}\right)d{var}",
                    latex_after=rf"u_1({var}) = {u1_ltx}, \quad u_2({var}) = {u2_ltx}",
                ),
                equation_latex=rf"u_1({var}) = {u1_ltx}, \quad u_2({var}) = {u2_ltx}",
            )
        )
        step_idx += 1

        # Particular solution yp(t) = u1*y1 + u2*y2
        yp_ltx = expr_to_latex(vop_res.particular_solution)
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Nghiệm riêng biến thiên hằng số",
                title="Xác định nghiệm riêng y_p(t)",
                description=(
                    f"Thay $u_1({var})$ và $u_2({var})$ vào công thức nghiệm riêng:\n"
                    f"$$y_p({var}) = u_1({var})y_1({var}) + u_2({var})y_2({var}) = {yp_ltx}$$"
                ),
                content=ExpressionStepContent(
                    expression_before="y_p = u1*y1 + u2*y2",
                    expression_after=f"y_p({var}) = {vop_res.particular_solution}",
                    latex_before=rf"y_p({var}) = u_1({var})y_1({var}) + u_2({var})y_2({var})",
                    latex_after=rf"y_p({var}) = {yp_ltx}",
                ),
                equation_latex=rf"y_p({var}) = {yp_ltx}",
            )
        )
        step_idx += 1
        return steps, step_idx

    def _build_solution_steps(
        self,
        var: sp.Symbol,
        dep_var: sp.Symbol,
        A: sp.Expr,
        B: sp.Expr,
        C: sp.Expr,
        indicial_poly: sp.Expr,
        delta: sp.Expr,
        root_case: str,
        m1: sp.Expr,
        m2: sp.Expr,
        alpha: sp.Expr | None,
        beta: sp.Expr | None,
        y1_fund: sp.Expr,
        y2_fund: sp.Expr,
        W_fund: sp.Expr,
        is_neg: bool,
        dom_desc: str,
        c1_sym: sp.Symbol,
        c2_sym: sp.Symbol,
        g_expr: sp.Expr | None = None,
        vop_res: VariationOfParametersResult | None = None,
        branch_vops: tuple[VariationOfParametersResult, ...] | None = None,
        t0: sp.Expr | None = None,
        y0: sp.Expr | None = None,
        v0: sp.Expr | None = None,
        val_c1: sp.Expr | None = None,
        val_c2: sp.Expr | None = None,
        particular_sol: sp.Expr | None = None,
        yp_at_t0: sp.Expr | None = None,
        dyp_at_t0: sp.Expr | None = None,
        v_res: VerificationResult | None = None,
        multi_branch: tuple[tuple[sp.Interval, sp.Expr, sp.Expr, sp.Expr, sp.Symbol, sp.Symbol], ...] | None = None,
    ) -> list[SolutionStep]:
        """Construct coherent, academically correct derivation steps for Euler-Cauchy ODE."""
        steps: list[SolutionStep] = []
        step_idx = 1
        basis_var_str = f"(-{var})" if is_neg else str(var)
        basis_var_ltx = rf"(-{var})" if is_neg else str(var)
        is_nonhomo = g_expr is not None

        # -------------------------------------------------------------
        # Step 1: Identify Euler-Cauchy form
        # -------------------------------------------------------------
        if is_nonhomo:
            g_ltx = expr_to_latex(g_expr)
            s1_desc = (
                f"Phương trình đã cho có dạng phương trình vi phân tuyến tính Euler–Cauchy không thuần nhất cấp 2:\n"
                f"$$A {var}^2 {dep_var}'' + B {var} {dep_var}' + C {dep_var} = g({var})$$\n"
                f"với các hệ số thực hằng số:\n"
                f"$$A = \\frac{{a({var})}}{{{var}^2}} = {expr_to_latex(A)}, \\quad "
                f"B = \\frac{{b({var})}}{{{var}}} = {expr_to_latex(B)}, \\quad "
                f"C = c({var}) = {expr_to_latex(C)}, \\quad "
                f"g({var}) = {g_ltx}$$\n"
                f"Phương trình thuần nhất liên kết là ${expr_to_latex(A)}\\,{var}^2 {dep_var}'' + {expr_to_latex(B)}\\,{var} {dep_var}' + {expr_to_latex(C)} {dep_var} = 0$."
            )
            s1_content = ExpressionStepContent(
                expression_before=f"a({var})*y'' + b({var})*y' + c({var})*y = g({var})",
                expression_after=f"{A}*{var}^2*y'' + {B}*{var}*y' + {C}*y = {g_expr}",
                latex_before=rf"a({var})\,y'' + b({var})\,y' + c({var})\,y = g({var})",
                latex_after=rf"{expr_to_latex(A)}\,{var}^2\,y'' + {expr_to_latex(B)}\,{var}\,y' + {expr_to_latex(C)}\,y = {g_ltx}",
            )
        else:
            s1_desc = (
                f"Phương trình đã cho có dạng phương trình vi phân tuyến tính Euler–Cauchy thuần nhất cấp 2:\n"
                f"$$A {var}^2 {dep_var}'' + B {var} {dep_var}' + C {dep_var} = 0$$\n"
                f"với các hệ số thực hằng số:\n"
                f"$$A = \\frac{{a({var})}}{{{var}^2}} = {expr_to_latex(A)}, \\quad "
                f"B = \\frac{{b({var})}}{{{var}}} = {expr_to_latex(B)}, \\quad "
                f"C = c({var}) = {expr_to_latex(C)}$$\n"
                f"Phương trình có bậc của biến độc lập {var} tương ứng chính xác với cấp của đạo hàm "
                f"(${var}^2 y''$, ${var} y'$, $y$), khác biệt hoàn toàn với phương trình hệ số hằng."
            )
            s1_content = ExpressionStepContent(
                expression_before=f"a({var})*y'' + b({var})*y' + c({var})*y = 0",
                expression_after=f"{A}*{var}^2*y'' + {B}*{var}*y' + {C}*y = 0",
                latex_before=rf"a({var})\,y'' + b({var})\,y' + c({var})\,y = 0",
                latex_after=rf"{expr_to_latex(A)}\,{var}^2\,y'' + {expr_to_latex(B)}\,{var}\,y' + {expr_to_latex(C)}\,y = 0",
            )

        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Nhận dạng dạng phương trình Euler–Cauchy",
                title="Nhận dạng dạng phương trình Euler–Cauchy",
                description=s1_desc,
                content=s1_content,
            )
        )
        step_idx += 1

        # -------------------------------------------------------------
        # Step 2: Introduce the trial solution
        # -------------------------------------------------------------
        if not is_neg:
            d1_ltx = rf"m\,{var}^{{m-1}}"
            d2_ltx = rf"m(m-1)\,{var}^{{m-2}}"
        else:
            d1_ltx = rf"-m\,(-{var})^{{m-1}}"
            d2_ltx = rf"m(m-1)\,(-{var})^{{m-2}}"

        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Nghiệm thử hàm lũy thừa",
                title="Thiết lập nghiệm thử dạng lũy thừa",
                description=(
                    f"Đối với phương trình Euler–Cauchy, ta xét nghiệm thử dưới dạng hàm lũy thừa:\n"
                    f"$${dep_var}({var}) = {basis_var_ltx}^m$$\n"
                    f"Tính các đạo hàm cấp 1 và cấp 2 theo biến ${var}$:\n"
                    f"$$\\begin{{aligned}} "
                    f"{dep_var}'({var}) &= {d1_ltx} \\\\ "
                    f"{dep_var}''({var}) &= {d2_ltx} "
                    f"\\end{{aligned}}$$"
                ),
                content=ExpressionStepContent(
                    expression_before=f"y = {basis_var_str}^m",
                    expression_after=f"y' = {d1_ltx}, y'' = {d2_ltx}",
                    latex_before=rf"y = {basis_var_ltx}^m",
                    latex_after=rf"y' = {d1_ltx}, \quad y'' = {d2_ltx}",
                ),
            )
        )
        step_idx += 1

        # -------------------------------------------------------------
        # Step 3: Derive the indicial equation
        # -------------------------------------------------------------
        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Phương trình chỉ số",
                title="Thay nghiệm thử và thiết lập phương trình chỉ số",
                description=(
                    f"Thay nghiệm thử và các đạo hàm vào phương trình vi phân ban đầu:\n"
                    f"$${expr_to_latex(A)} {var}^2 \\left({d2_ltx}\\right) + "
                    f"{expr_to_latex(B)} {var} \\left({d1_ltx}\\right) + "
                    f"{expr_to_latex(C)} \\left({basis_var_ltx}^m\\right) = 0$$\n"
                    f"Đặt nhân tử chung ${basis_var_ltx}^m$:\n"
                    f"$$\\left[{expr_to_latex(A)}\\,m(m-1) + {expr_to_latex(B)}\\,m + {expr_to_latex(C)}\\right] {basis_var_ltx}^m = 0$$\n"
                    f"Vì trên miền khảo sát ${basis_var_ltx} \\ne 0 \\implies {basis_var_ltx}^m \\ne 0$, ta thu được phương trình chỉ số (indicial equation):\n"
                    f"$${expr_to_latex(A)}\\,m(m-1) + {expr_to_latex(B)}\\,m + {expr_to_latex(C)} = 0$$"
                ),
                content=ExpressionStepContent(
                    expression_before=f"{A}*m*(m-1) + {B}*m + {C} = 0",
                    expression_after=f"{indicial_poly} = 0",
                    latex_before=rf"{expr_to_latex(A)}\,m(m-1) + {expr_to_latex(B)}\,m + {expr_to_latex(C)} = 0",
                    latex_after=rf"{expr_to_latex(indicial_poly)} = 0",
                ),
            )
        )
        step_idx += 1

        # -------------------------------------------------------------
        # Step 4: Calculate the discriminant and roots
        # -------------------------------------------------------------
        b_ind = sp.simplify(B - A)
        if root_case == "DISTINCT":
            root_desc = (
                f"Vì $\\Delta = {expr_to_latex(delta)} > 0$, phương trình chỉ số có hai nghiệm thực phân biệt:\n"
                f"$$m_1 = \\frac{{-(B-A) + \\sqrt{{\\Delta}}}}{{2A}} = {expr_to_latex(m1)}, \\quad "
                f"m_2 = \\frac{{-(B-A) - \\sqrt{{\\Delta}}}}{{2A}} = {expr_to_latex(m2)}$$"
            )
            root_exp_after = f"m1 = {m1}, m2 = {m2}"
            root_ltx_after = rf"m_1 = {expr_to_latex(m1)}, \quad m_2 = {expr_to_latex(m2)}"
        elif root_case == "REPEATED":
            root_desc = (
                f"Vì $\\Delta = 0$, phương trình chỉ số có nghiệm kép thực:\n"
                f"$$m_1 = m_2 = m = -\\frac{{B-A}}{{2A}} = {expr_to_latex(m1)}$$"
            )
            root_exp_after = f"m = {m1}"
            root_ltx_after = rf"m_1 = m_2 = {expr_to_latex(m1)}"
        else:  # COMPLEX
            assert alpha is not None and beta is not None
            root_desc = (
                f"Vì $\\Delta = {expr_to_latex(delta)} < 0$, phương trình chỉ số có cặp nghiệm phức liên hợp:\n"
                f"$$m_{{1,2}} = \\alpha \\pm i\\beta = {expr_to_latex(alpha)} \\pm i \\left({expr_to_latex(beta)}\\right)$$"
            )
            root_exp_after = f"alpha = {alpha}, beta = {beta}"
            root_ltx_after = rf"\alpha = {expr_to_latex(alpha)}, \quad \beta = {expr_to_latex(beta)}"

        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Biệt thức Delta và nghiệm chỉ số",
                title="Tính biệt thức Delta và xác định các nghiệm chỉ số",
                description=(
                    f"Rút gọn đa thức chỉ số về dạng chuẩn tắc bậc hai:\n"
                    f"$$P(m) = {expr_to_latex(indicial_poly)} = 0$$\n"
                    f"với hệ số bậc hai $a = {expr_to_latex(A)}$, hệ số bậc nhất $b = B - A = {expr_to_latex(b_ind)}$, hệ số tự do $c = {expr_to_latex(C)}$.\n"
                    f"Tính biệt thức $\\Delta$:\n"
                    f"$$\\Delta = (B - A)^2 - 4AC = ({expr_to_latex(b_ind)})^2 - 4({expr_to_latex(A)})({expr_to_latex(C)}) = {expr_to_latex(delta)}$$\n"
                    f"{root_desc}"
                ),
                content=ExpressionStepContent(
                    expression_before=f"Delta = {delta}",
                    expression_after=root_exp_after,
                    latex_before=rf"\Delta = {expr_to_latex(delta)}",
                    latex_after=root_ltx_after,
                ),
            )
        )
        step_idx += 1

        # -------------------------------------------------------------
        # Step 5: Construct the fundamental solutions
        # -------------------------------------------------------------
        if root_case == "DISTINCT":
            case_fund_desc = (
                f"Tương ứng với hai nghiệm thực phân biệt $m_1 = {expr_to_latex(m1)}$ và $m_2 = {expr_to_latex(m2)}$, "
                f"hệ hai nghiệm cơ bản là:\n"
                f"$$y_1({var}) = {expr_to_latex(y1_fund)}, \\quad y_2({var}) = {expr_to_latex(y2_fund)}$$"
            )
        elif root_case == "REPEATED":
            case_fund_desc = (
                f"Tương ứng với nghiệm kép $m = {expr_to_latex(m1)}$, nghiệm cơ bản thứ hai thu được thông qua thừa số $\\ln |{var}|$:\n"
                f"$$y_1({var}) = {expr_to_latex(y1_fund)}, \\quad y_2({var}) = {expr_to_latex(y2_fund)}$$"
            )
        else:  # COMPLEX
            assert alpha is not None and beta is not None
            case_fund_desc = (
                f"Áp dụng công thức Euler vào nghiệm phức $m = \\alpha \\pm i\\beta$:\n"
                f"$${basis_var_ltx}^{{\\alpha \\pm i\\beta}} = {basis_var_ltx}^\\alpha e^{{\\pm i \\beta \\ln {basis_var_ltx}}} = "
                f"{basis_var_ltx}^\\alpha \\left[\\cos(\\beta \\ln {basis_var_ltx}) \\pm i\\sin(\\beta \\ln {basis_var_ltx})\\right]$$\n"
                f"Tách phần thực và phần ảo ta thu được hệ hai nghiệm thực cơ bản:\n"
                f"$$y_1({var}) = {expr_to_latex(y1_fund)}, \\quad y_2({var}) = {expr_to_latex(y2_fund)}$$"
            )

        v_status = v_res.status if v_res else VerificationStatus.UNVERIFIED
        v_details = v_res.details if v_res and v_res.details else ""
        is_verified = v_status == VerificationStatus.VERIFIED
        is_failed = v_status == VerificationStatus.FAILED

        if is_verified:
            wronskian_step_desc = (
                f"{case_fund_desc}\n\n"
                f"Kiểm tra tính độc lập tuyến tính qua định thức Wronskian:\n"
                f"$$W(y_1, y_2) = y_1 y_2' - y_1' y_2 = {expr_to_latex(W_fund)} \\ne 0$$\n"
                f"Định thức Wronskian đã được kiểm chứng độc lập khác 0 trên toàn bộ khoảng xác định; $y_1({var})$ và $y_2({var})$ tạo thành hệ nghiệm cơ bản đầy đủ."
            )
            wronskian_ltx_after = rf"W(y_1, y_2) = {expr_to_latex(W_fund)} \ne 0"
        elif is_failed:
            wronskian_step_desc = (
                f"{case_fund_desc}\n\n"
                f"Định thức Wronskian tính được:\n"
                f"$$W(y_1, y_2) = y_1 y_2' - y_1' y_2 = {expr_to_latex(W_fund)}$$\n"
                f"Lưu ý: Kiểm chứng độc lập phát hiện sai lệch hoặc hệ nghiệm không thỏa mãn đầy đủ điều kiện kiểm chứng."
            )
            wronskian_ltx_after = rf"W(y_1, y_2) = {expr_to_latex(W_fund)}"
        else:
            wronskian_step_desc = (
                f"{case_fund_desc}\n\n"
                f"Định thức Wronskian tính được:\n"
                f"$$W(y_1, y_2) = y_1 y_2' - y_1' y_2 = {expr_to_latex(W_fund)}$$\n"
                f"Lưu ý: Tính độc lập tuyến tính và nghiệm chưa được xác nhận hoàn toàn bằng kiểm chứng ký hiệu."
            )
            wronskian_ltx_after = rf"W(y_1, y_2) = {expr_to_latex(W_fund)}"

        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Hệ nghiệm cơ bản",
                title="Xây dựng hệ nghiệm cơ bản độc lập tuyến tính",
                description=wronskian_step_desc,
                content=ExpressionStepContent(
                    expression_before=f"y1 = {y1_fund}, y2 = {y2_fund}",
                    expression_after=f"W(y1, y2) = {W_fund}",
                    latex_before=rf"y_1 = {expr_to_latex(y1_fund)}, \quad y_2 = {expr_to_latex(y2_fund)}",
                    latex_after=wronskian_ltx_after,
                ),
            )
        )
        step_idx += 1

        # -------------------------------------------------------------
        # Optional Step 5b & VoP steps for Nonhomogeneous Euler-Cauchy
        # -------------------------------------------------------------
        if is_nonhomo and vop_res is not None:
            yc_expr = c1_sym * y1_fund + c2_sym * y2_fund
            yc_ltx = expr_to_latex(yc_expr)
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Nghiệm thuần nhất liên kết",
                    title="Xác định nghiệm thuần nhất liên kết y_c(t)",
                    description=(
                        f"Từ hệ nghiệm cơ bản $\\{{y_1, y_2\\}}$, nghiệm của phương trình thuần nhất liên kết là:\n"
                        f"$$y_c({var}) = C_1 y_1({var}) + C_2 y_2({var}) = {yc_ltx}$$"
                    ),
                    content=ExpressionStepContent(
                        expression_before="y_c = C1*y1 + C2*y2",
                        expression_after=f"y_c({var}) = {yc_expr}",
                        latex_before=rf"y_c({var}) = C_1 y_1({var}) + C_2 y_2({var})",
                        latex_after=rf"y_c({var}) = {yc_ltx}",
                    ),
                    equation_latex=rf"y_c({var}) = {yc_ltx}",
                )
            )
            step_idx += 1

            vop_steps, step_idx = self._build_vop_pedagogical_steps(
                step_idx=step_idx,
                var=var,
                dep_var=dep_var,
                A=A,
                B=B,
                C=C,
                g_expr=g_expr,  # type: ignore[arg-type]
                y1_fund=y1_fund,
                y2_fund=y2_fund,
                W_fund=W_fund,
                vop_res=vop_res,
            )
            steps.extend(vop_steps)

        # -------------------------------------------------------------
        # Step 6: Assemble the general solution
        # -------------------------------------------------------------
        if multi_branch is not None:
            aligned_lines: list[str] = []
            case_lines: list[str] = []
            exp_after_parts: list[str] = []
            const_syms_list: list[str] = []
            for idx_b, (iv_b, sol_b, y1_b, y2_b, ca_b, cb_b) in enumerate(multi_branch):
                if iv_b == sp.Interval.open(0, sp.oo):
                    cond_ltx = rf"\text{{khi }} {var} > 0"
                    lbl = "pos"
                elif iv_b == sp.Interval.open(-sp.oo, 0):
                    cond_ltx = rf"\text{{khi }} {var} < 0"
                    lbl = "neg"
                else:
                    cond_ltx = rf"\text{{khi }} {var} \in {format_interval_latex(iv_b)}"
                    lbl = format_interval_latex(iv_b)
                yp_b_ltx = ""
                if is_nonhomo and branch_vops and idx_b < len(branch_vops):
                    yp_b_ltx = f" + {expr_to_latex(branch_vops[idx_b].particular_solution)}"
                aligned_lines.append(
                    rf"y({var}) &= {ca_b.name[0]}_{{{ca_b.name[1:]}}} {expr_to_latex(y1_b)} + {cb_b.name[0]}_{{{cb_b.name[1:]}}} {expr_to_latex(y2_b)}{yp_b_ltx} = {expr_to_latex(sol_b)} \quad ({cond_ltx})"
                )
                case_lines.append(rf"{expr_to_latex(sol_b)} & {cond_ltx}")
                exp_after_parts.append(f"y_{lbl} = {sol_b}")
                const_syms_list.extend(
                    [f"{ca_b.name[0]}_{{{ca_b.name[1:]}}}", f"{cb_b.name[0]}_{{{cb_b.name[1:]}}}"]
                )

            gen_desc = (
                f"Do điểm kỳ dị tại ${var} = 0$ và các điều kiện xác định của phương trình, miền xác định tự nhiên tách rời thành {len(multi_branch)} khoảng liên thông độc lập.\n"
                f"Nghiệm tổng quát sử dụng các hằng số tích phân độc lập cho từng nhánh liên thông:\n"
                f"$$\\begin{{aligned}} "
                + r" \\ ".join(aligned_lines)
                + f" \\end{{aligned}}$$\n"
                f"với ${', '.join(const_syms_list)} \\in \\mathbb{{R}}$ là các hằng số tích phân độc lập."
            )
            gen_exp_after = ", ".join(exp_after_parts)
            gen_ltx_after = (
                rf"y({var}) = \begin{{cases}} " + r" \\ ".join(case_lines) + r" \end{cases}"
            )
            gen_before_str = "y = y_c + y_p" if is_nonhomo else "y = C1*y1 + C2*y2"
            gen_before_ltx = rf"y({var}) = y_c({var}) + y_p({var})" if is_nonhomo else rf"y({var}) = C_1 y_1({var}) + C_2 y_2({var})"
        elif is_nonhomo and vop_res is not None:
            yc_expr = c1_sym * y1_fund + c2_sym * y2_fund
            yp_expr = vop_res.particular_solution
            gen_sol_combined = (
                (sp.simplify(yc_expr) + yp_expr)
                if vop_res.is_integral_form
                else sp.simplify(yc_expr + yp_expr)
            )
            gen_desc = (
                f"Tổng hợp nghiệm tổng quát theo nguyên lý chồng chất $y({var}) = y_c({var}) + y_p({var})$:\n"
                f"$$y({var}) = {expr_to_latex(gen_sol_combined)}$$\n"
                f"với $C_1, C_2 \\in \\mathbb{{R}}$ là các hằng số tích phân tùy ý; miền xác định: ${dom_desc}$."
            )
            gen_exp_after = f"y({var}) = {gen_sol_combined}"
            gen_ltx_after = rf"y({var}) = {expr_to_latex(gen_sol_combined)}"
            gen_before_str = "y = y_c + y_p"
            gen_before_ltx = rf"y({var}) = y_c({var}) + y_p({var})"
        else:
            gen_sol_combined = sp.simplify(c1_sym * y1_fund + c2_sym * y2_fund)
            gen_desc = (
                f"Nghiệm tổng quát là tổ hợp tuyến tính của hệ nghiệm cơ bản trên miền khảo sát:\n"
                f"$$y({var}) = C_1 y_1({var}) + C_2 y_2({var}) = {expr_to_latex(gen_sol_combined)}$$\n"
                f"với $C_1, C_2 \\in \\mathbb{{R}}$ là các hằng số tích phân tùy ý; miền xác định: ${dom_desc}$."
            )
            gen_exp_after = f"y({var}) = {gen_sol_combined}"
            gen_ltx_after = rf"y({var}) = {expr_to_latex(gen_sol_combined)}"
            gen_before_str = "y = C1*y1 + C2*y2"
            gen_before_ltx = r"y(t) = C_1 y_1(t) + C_2 y_2(t)"

        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Nghiệm tổng quát",
                title="Thiết lập nghiệm tổng quát trên miền xác định",
                description=gen_desc,
                content=ExpressionStepContent(
                    expression_before=gen_before_str,
                    expression_after=gen_exp_after,
                    latex_before=gen_before_ltx,
                    latex_after=gen_ltx_after,
                ),
            )
        )
        step_idx += 1

        # -------------------------------------------------------------
        # Optional Step 7: Cauchy IVP integration constants evaluation
        # -------------------------------------------------------------
        if t0 is not None and y0 is not None and v0 is not None and val_c1 is not None and val_c2 is not None and particular_sol is not None:
            dy1_fund = sp.diff(y1_fund, var)
            dy2_fund = sp.diff(y2_fund, var)
            y1_0 = sp.simplify(y1_fund.subs(var, t0))
            y2_0 = sp.simplify(y2_fund.subs(var, t0))
            dy1_0 = sp.simplify(dy1_fund.subs(var, t0))
            dy2_0 = sp.simplify(dy2_fund.subs(var, t0))
            rhs1 = sp.simplify(y0 - (yp_at_t0 if yp_at_t0 is not None else sp.Integer(0)))
            rhs2 = sp.simplify(v0 - (dyp_at_t0 if dyp_at_t0 is not None else sp.Integer(0)))
            rhs_note = (
                (
                    f"\n(Trong đó $y_p({expr_to_latex(t0)}) = {expr_to_latex(yp_at_t0 or 0)}$ và "
                    f"$y_p'({expr_to_latex(t0)}) = {expr_to_latex(dyp_at_t0 or 0)}$.)"
                )
                if is_nonhomo
                else ""
            )

            ivp_substeps = (
                SolutionStep(
                    step_number=1,
                    rule_name="Thiết lập hệ Cauchy",
                    title="Thay điều kiện ban đầu vào nghiệm tổng quát",
                    description=(
                        f"Thay điểm ban đầu ${var}_0 = {expr_to_latex(t0)}$ vào $y({var})$ và $y'({var})$:{rhs_note}\n"
                        f"$$\\begin{{cases}} "
                        f"C_1 \\cdot ({expr_to_latex(y1_0)}) + C_2 \\cdot ({expr_to_latex(y2_0)}) = {expr_to_latex(rhs1)} \\\\ "
                        f"C_1 \\cdot ({expr_to_latex(dy1_0)}) + C_2 \\cdot ({expr_to_latex(dy2_0)}) = {expr_to_latex(rhs2)} "
                        f"\\end{{cases}}$$"
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"y({t0}) = {y0}, y'({t0}) = {v0}",
                        expression_after=f"C1*{y1_0} + C2*{y2_0} = {rhs1}",
                        latex_before=rf"y({expr_to_latex(t0)}) = {expr_to_latex(y0)}, \quad y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}",
                        latex_after=rf"C_1({expr_to_latex(y1_0)}) + C_2({expr_to_latex(y2_0)}) = {expr_to_latex(rhs1)}",
                    ),
                ),
                SolutionStep(
                    step_number=2,
                    rule_name="Giải hệ đại số tuyến tính",
                    title="Xác định giá trị chính xác của C1 và C2",
                    description=(
                        f"Giải hệ phương trình tuyến tính 2 ẩn:\n"
                        f"$$C_1 = {expr_to_latex(val_c1)}, \\quad C_2 = {expr_to_latex(val_c2)}$$"
                    ),
                    content=ExpressionStepContent(
                        expression_before="System for C1, C2",
                        expression_after=f"C1 = {val_c1}, C2 = {val_c2}",
                        latex_before=r"\text{Hệ phương trình ẩn } C_1, C_2",
                        latex_after=rf"C_1 = {expr_to_latex(val_c1)}, \quad C_2 = {expr_to_latex(val_c2)}",
                    ),
                ),
                SolutionStep(
                    step_number=3,
                    rule_name="Nghiệm riêng",
                    title="Thay các hằng số vào nghiệm tổng quát",
                    description=(
                        f"Thay các giá trị hằng số $C_1, C_2$ vào nghiệm tổng quát thu được nghiệm riêng duy nhất:\n"
                        f"$$y({var}) = {expr_to_latex(particular_sol)}$$"
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"C1 = {val_c1}, C2 = {val_c2}",
                        expression_after=f"y({var}) = {particular_sol}",
                        latex_before=rf"C_1 = {expr_to_latex(val_c1)}, \quad C_2 = {expr_to_latex(val_c2)}",
                        latex_after=rf"y({var}) = {expr_to_latex(particular_sol)}",
                    ),
                ),
            )

            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Điều kiện ban đầu Cauchy",
                    title="Xác định nghiệm riêng từ điều kiện ban đầu Cauchy",
                    description=(
                        f"Áp dụng hai điều kiện ban đầu Cauchy tại điểm ${var}_0 = {expr_to_latex(t0)}$:\n"
                        f"$$y({expr_to_latex(t0)}) = {expr_to_latex(y0)}, \\quad y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}$$\n"
                        f"để xác định nghiệm riêng duy nhất: $y({var}) = {expr_to_latex(particular_sol)}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"y({t0}) = {y0}, y'({t0}) = {v0}",
                        expression_after=f"y({var}) = {particular_sol}",
                        latex_before=rf"y({expr_to_latex(t0)}) = {expr_to_latex(y0)}, \quad y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}",
                        latex_after=rf"y({var}) = {expr_to_latex(particular_sol)}",
                    ),
                    substeps=ivp_substeps,
                )
            )
            step_idx += 1

        # -------------------------------------------------------------
        # Final Step: Independent verification (status derived strictly from v_res)
        # -------------------------------------------------------------
        res_rhs_raw = f" - ({g_expr})" if is_nonhomo else ""
        res_rhs_ltx = f" - \\left({expr_to_latex(g_expr)}\\right)" if is_nonhomo else ""
        if is_verified:
            res_substep = SolutionStep(
                step_number=1,
                rule_name="Kiểm chứng phương trình vi phân",
                title="Kiểm chứng phương trình Euler–Cauchy",
                description=(
                    f"Thay nghiệm vào phương trình vi phân ban đầu:\n"
                    f"$$R({var}) = {expr_to_latex(A)}\\,{var}^2\\,y'' + {expr_to_latex(B)}\\,{var}\\,y' + {expr_to_latex(C)}\\,y{res_rhs_ltx} "
                    f"\\equiv 0$$\n"
                    f"Biểu thức dư được kiểm chứng triệt tiêu hoàn toàn bằng phương pháp ký hiệu exact."
                ),
                content=ExpressionStepContent(
                    expression_before=f"R({var}) = a*{var}^2*y'' + b*{var}*y' + c*y{res_rhs_raw}",
                    expression_after=f"R({var}) = 0",
                    latex_before=rf"R({var}) = {expr_to_latex(A)}\,{var}^2\,y'' + {expr_to_latex(B)}\,{var}\,y' + {expr_to_latex(C)}\,y{res_rhs_ltx}",
                    latex_after=rf"R({var}) \equiv 0",
                ),
            )
            w_substep = SolutionStep(
                step_number=2,
                rule_name="Kiểm chứng hệ nghiệm cơ bản",
                title="Kiểm chứng độc lập tuyến tính qua Wronskian",
                description=(
                    f"Kiểm chứng định thức Wronskian trên khoảng xác định:\n"
                    f"$$W(y_1, y_2) = {expr_to_latex(W_fund)} \\ne 0$$\n"
                    f"Hai nghiệm cơ bản được xác nhận độc lập tuyến tính hoàn toàn."
                ),
                content=ExpressionStepContent(
                    expression_before="W(y1, y2)",
                    expression_after=f"W(y1, y2) = {W_fund} != 0 (Verified)",
                    latex_before=r"W(y_1, y_2) = y_1 y_2' - y_1' y_2",
                    latex_after=rf"W(y_1, y_2) = {expr_to_latex(W_fund)} \ne 0",
                ),
            )
        elif is_failed:
            res_substep = SolutionStep(
                step_number=1,
                rule_name="Kiểm chứng phương trình vi phân",
                title="Kiểm chứng phương trình Euler–Cauchy (Thất bại)",
                description=(
                    f"Kiểm chứng độc lập phát hiện sai lệch (FAILED):\n"
                    f"{v_details or f'Biểu thức dư R({var}) không thỏa mãn phương trình.'}"
                ),
                content=ExpressionStepContent(
                    expression_before=f"R({var}) = a*{var}^2*y'' + b*{var}*y' + c*y{res_rhs_raw}",
                    expression_after=f"R({var}) FAILED",
                    latex_before=rf"R({var}) = {expr_to_latex(A)}\,{var}^2\,y'' + {expr_to_latex(B)}\,{var}\,y' + {expr_to_latex(C)}\,y{res_rhs_ltx}",
                    latex_after=rf"R({var}) \quad (\text{{FAILED}})",
                ),
            )
            w_substep = SolutionStep(
                step_number=2,
                rule_name="Kiểm chứng hệ nghiệm cơ bản",
                title="Kiểm chứng độc lập tuyến tính qua Wronskian (Thất bại)",
                description=(
                    f"Định thức Wronskian ứng viên: $W(y_1, y_2) = {expr_to_latex(W_fund)}$.\n"
                    f"Trạng thái kiểm chứng tổng thể: FAILED ({v_details or 'Phát hiện sai lệch nghiệm.'})."
                ),
                content=ExpressionStepContent(
                    expression_before="W(y1, y2)",
                    expression_after=f"W(y1, y2) = {W_fund} (FAILED)",
                    latex_before=r"W(y_1, y_2) = y_1 y_2' - y_1' y_2",
                    latex_after=rf"W(y_1, y_2) = {expr_to_latex(W_fund)} \quad (\text{{FAILED}})",
                ),
            )
        else:
            res_substep = SolutionStep(
                step_number=1,
                rule_name="Kiểm chứng phương trình vi phân",
                title="Kiểm chứng phương trình Euler–Cauchy (Chưa kết luận)",
                description=(
                    f"Chưa thể kiểm chứng hoàn toàn biểu thức dư $R({var})$ bằng phương pháp ký hiệu (UNVERIFIED):\n"
                    f"{v_details or 'Kết quả kiểm chứng chưa thể xác nhận hoàn toàn.'}"
                ),
                content=ExpressionStepContent(
                    expression_before=f"R({var}) = a*{var}^2*y'' + b*{var}*y' + c*y{res_rhs_raw}",
                    expression_after=f"R({var}) UNVERIFIED",
                    latex_before=rf"R({var}) = {expr_to_latex(A)}\,{var}^2\,y'' + {expr_to_latex(B)}\,{var}\,y' + {expr_to_latex(C)}\,y{res_rhs_ltx}",
                    latex_after=rf"R({var}) \quad (\text{{UNVERIFIED}})",
                ),
            )
            w_substep = SolutionStep(
                step_number=2,
                rule_name="Kiểm chứng hệ nghiệm cơ bản",
                title="Kiểm chứng độc lập tuyến tính qua Wronskian (Chưa kết luận)",
                description=(
                    f"Định thức Wronskian ứng viên: $W(y_1, y_2) = {expr_to_latex(W_fund)}$.\n"
                    f"Trạng thái kiểm chứng tổng thể: UNVERIFIED ({v_details or 'Không thể xác nhận bằng phương pháp ký hiệu.'})."
                ),
                content=ExpressionStepContent(
                    expression_before="W(y1, y2)",
                    expression_after=f"W(y1, y2) = {W_fund} (UNVERIFIED)",
                    latex_before=r"W(y_1, y_2) = y_1 y_2' - y_1' y_2",
                    latex_after=rf"W(y_1, y_2) = {expr_to_latex(W_fund)} \quad (\text{{UNVERIFIED}})",
                ),
            )

        verif_substeps: list[SolutionStep] = [res_substep, w_substep]

        if t0 is not None and y0 is not None and v0 is not None:
            if is_verified:
                ic_title = "Kiểm chứng các giá trị ban đầu tại t0"
                ic_desc = (
                    f"Thay trực tiếp ${var}_0 = {expr_to_latex(t0)}$:\n"
                    f"$$y({expr_to_latex(t0)}) = {expr_to_latex(y0)}, \\quad y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}$$\n"
                    f"Cả hai điều kiện ban đầu đều được thỏa mãn chính xác tuyệt đối."
                )
                ic_exp_after = f"y({t0}) = {y0}, y'({t0}) = {v0}"
                ic_ltx_after = rf"y({expr_to_latex(t0)}) = {expr_to_latex(y0)}, \quad y'({expr_to_latex(t0)}) = {expr_to_latex(v0)}"
            elif is_failed:
                ic_title = "Kiểm chứng các giá trị ban đầu tại t0 (Thất bại)"
                ic_desc = (
                    f"Kiểm chứng điều kiện Cauchy tại ${var}_0 = {expr_to_latex(t0)}$ thất bại hoặc không hoàn tất (FAILED): "
                    f"{v_details}"
                )
                ic_exp_after = f"Cauchy IC check FAILED at {var}0 = {t0}"
                ic_ltx_after = rf"\text{{Cauchy IC at }} {expr_to_latex(t0)} \quad (\text{{FAILED}})"
            else:
                ic_title = "Kiểm chứng các giá trị ban đầu tại t0 (Chưa kết luận)"
                ic_desc = (
                    f"Chưa thể xác nhận hoàn toàn điều kiện Cauchy tại ${var}_0 = {expr_to_latex(t0)}$ (UNVERIFIED): "
                    f"{v_details}"
                )
                ic_exp_after = f"Cauchy IC check UNVERIFIED at {var}0 = {t0}"
                ic_ltx_after = rf"\text{{Cauchy IC at }} {expr_to_latex(t0)} \quad (\text{{UNVERIFIED}})"

            verif_substeps.append(
                SolutionStep(
                    step_number=3,
                    rule_name="Kiểm chứng điều kiện Cauchy",
                    title=ic_title,
                    description=ic_desc,
                    content=ExpressionStepContent(
                        expression_before=f"y({t0}), y'({t0})",
                        expression_after=ic_exp_after,
                        latex_before=rf"y({expr_to_latex(t0)}), \quad y'({expr_to_latex(t0)})",
                        latex_after=ic_ltx_after,
                    ),
                )
            )

        if is_verified:
            parent_desc = (
                "Kiểm chứng độc lập bằng SymPy: Nghiệm thỏa mãn hoàn toàn phương trình vi phân ban đầu, "
                "hệ nghiệm cơ bản độc lập tuyến tính (W ≠ 0)"
                + (" và cả hai điều kiện ban đầu Cauchy." if t0 is not None else " trên miền xác định.")
            )
            parent_exp_after = f"R({var}) = 0 (Verified)"
            parent_ltx_after = rf"R({var}) \equiv 0 \quad (\text{{VERIFIED}})"
        elif is_failed:
            parent_desc = (
                f"Kiểm chứng độc lập thất bại (FAILED): {v_details or 'Phát hiện sai lệch trong kiểm chứng nghiệm.'}"
            )
            parent_exp_after = f"Verification FAILED ({v_status.value})"
            parent_ltx_after = rf"R({var}) \quad (\text{{FAILED}})"
        else:
            parent_desc = (
                f"Kiểm chứng độc lập chưa thể kết luận (UNVERIFIED): {v_details or 'Không thể xác nhận hoàn toàn bằng phương pháp ký hiệu.'}"
            )
            parent_exp_after = f"Verification UNVERIFIED ({v_status.value})"
            parent_ltx_after = rf"R({var}) \quad (\text{{UNVERIFIED}})"

        steps.append(
            SolutionStep(
                step_number=step_idx,
                rule_name="Kiểm chứng độc lập",
                title="Kiểm chứng tính đúng đắn toán học của nghiệm",
                description=parent_desc,
                content=ExpressionStepContent(
                    expression_before=f"Residual check R({var})",
                    expression_after=parent_exp_after,
                    latex_before=rf"R({var}) = a\,{var}^2 y'' + b\,{var} y' + c\,y{res_rhs_ltx}",
                    latex_after=parent_ltx_after,
                ),
                substeps=tuple(verif_substeps),
            )
        )

        return steps

"""Shared real-calculus integration and differential-form domain validation helpers for ODE solvers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Iterable

import sympy as sp

from math_app.application.dtos import (
    SolutionResponse,
    VerificationResult,
)
from math_app.domain.models import DomainCompleteness, SolutionStatus, VerificationStatus
from math_app.input.ode_parser import ParsedODE
from math_app.solvers.calculus.ode.domain_analyzer import (
    extract_expression_domain_with_completeness,
    format_set_latex,
)
from math_app.verification.calculus.ode_verifier import (
    classify_scalar_real_finite,
    evaluate_initial_point_domain,
)


def has_non_elementary_or_complex_branch(expr: sp.Expr, source_expr: sp.Expr) -> bool:
    """Return True when an antiderivative contains unevaluated/polar/spurious complex branches."""
    if expr.has(sp.Integral, sp.exp_polar, sp.meijerg, sp.hyper):
        return True
    if expr.has(sp.I) and not source_expr.has(sp.I):
        return True
    return False


def strip_log_abs(expr: sp.Expr) -> sp.Expr:
    """Replace log(Abs(u)) with log(u) solely for smooth algebraic differentiation away from u = 0."""
    return expr.replace(
        lambda node: isinstance(node, sp.log) and bool(node.args) and isinstance(node.args[0], sp.Abs),
        lambda node: sp.log(node.args[0].args[0]),
    )


def realify_integrated_logs(
    expr: sp.Expr,
    source_expr: sp.Expr,
    eval_subs: dict[sp.Symbol, sp.Expr] | list[tuple[sp.Symbol, sp.Expr]] | None = None,
    *,
    wrap_all: bool = False,
) -> sp.Expr:
    """Convert newly integrated log(u) terms into log(Abs(u)) on real domains when valid.

    Preserves any log(u) already present in source_expr so explicit log domain
    restrictions (e.g. u > 0 from ln(x) in the input ODE) are never silently widened.
    When wrap_all is False and eval_subs is provided, only wraps newly introduced
    log(u) terms whose argument evaluates strictly negative at the initial point.
    """
    existing_log_args = {node.args[0] for node in source_expr.atoms(sp.log) if node.args}

    def _should_wrap(node: sp.Expr) -> bool:
        if not isinstance(node, sp.log) or not node.args:
            return False
        arg = node.args[0]
        if isinstance(arg, sp.Abs):
            return False
        if arg in existing_log_args:
            return False
        if getattr(arg, "is_positive", False) is True:
            return False
        if wrap_all:
            return True
        if eval_subs is not None:
            try:
                arg_val = sp.simplify(arg.subs(eval_subs))
                if arg_val.is_number and arg_val.is_real is True and bool(arg_val < 0):
                    return True
            except Exception:
                pass
        return False

    return expr.replace(_should_wrap, lambda node: sp.log(sp.Abs(node.args[0])))


def real_integrate_expression(
    expr: sp.Expr,
    var: sp.Symbol,
    source_expr: sp.Expr | None = None,
    eval_subs: dict[sp.Symbol, sp.Expr] | list[tuple[sp.Symbol, sp.Expr]] | None = None,
    *,
    wrap_all_logs: bool = False,
) -> sp.Expr | None:
    """Compute a real-domain antiderivative, returning None for non-elementary or polar results."""
    ref_expr = expr if source_expr is None else source_expr
    raw = sp.integrate(expr, var)
    if raw.has(sp.Integral, sp.exp_polar, sp.meijerg, sp.hyper):
        return None
    realified = realify_integrated_logs(raw, ref_expr, eval_subs=eval_subs, wrap_all=wrap_all_logs)
    simplified = sp.simplify(realified)
    if has_non_elementary_or_complex_branch(simplified, ref_expr):
        return None
    return simplified


def _interior_sample_point(low: Any, high: Any, var: sp.Symbol, sample_point: sp.Expr | None = None) -> sp.Expr:
    """Return a finite interior test point inside the open interval (low, high)."""
    if sample_point is not None:
        try:
            low_ok = low is None or low == -sp.oo or bool(sp.N(sample_point - low) > 0)
            high_ok = high is None or high == sp.oo or bool(sp.N(high - sample_point) > 0)
            if low_ok and high_ok:
                return sample_point
        except Exception:
            pass
    if (low is None or low == -sp.oo) and (high is None or high == sp.oo):
        return sp.Integer(0)
    if low is None or low == -sp.oo:
        return high - 1
    if high is None or high == sp.oo:
        return low + 1
    return sp.simplify((low + high) / 2)


def unwrap_abs_on_interval(
    expr: sp.Expr,
    var: sp.Symbol,
    interval: tuple[Any, Any] | None,
    sample_point: sp.Expr | None = None,
) -> sp.Expr:
    """On an open interval (low, high), replace Abs(u) by +u or -u when u keeps constant sign."""
    if interval is None or not expr.has(sp.Abs):
        return expr
    low, high = interval
    low_b = -sp.oo if low is None else low
    high_b = sp.oo if high is None else high
    open_iv = sp.Interval.open(low_b, high_b)
    mid = _interior_sample_point(low_b, high_b, var, sample_point)

    def _unwrap(node: sp.Abs) -> sp.Expr:
        arg = node.args[0]
        if var not in arg.free_symbols:
            return node
        try:
            roots = sp.solveset(arg, var, open_iv)
            if roots is not sp.S.EmptySet:
                return node
            arg_mid = sp.simplify(arg.subs(var, mid))
            if arg_mid.is_number and arg_mid.is_real is True:
                if bool(arg_mid > 0):
                    return arg
                if bool(arg_mid < 0):
                    return -arg
        except Exception:
            pass
        return node

    res = expr.replace(lambda n: isinstance(n, sp.Abs) and bool(n.args), _unwrap)
    try:
        if high_b != sp.oo and high_b.is_number and bool(sp.N(high_b) <= 0):
            v_neg = sp.Symbol(var.name, negative=True)
            res = sp.simplify(res.subs(var, v_neg)).subs(v_neg, var)
        elif low_b != -sp.oo and low_b.is_number and bool(sp.N(low_b) >= 0):
            v_pos = sp.Symbol(var.name, positive=True)
            res = sp.simplify(res.subs(var, v_pos)).subs(v_pos, var)
        else:
            v_real = sp.Symbol(var.name, real=True)
            res = sp.simplify(res.subs(var, v_real)).subs(v_real, var)
    except Exception:
        pass
    return sp.simplify(res)


def real_integrate_on_interval(
    expr: sp.Expr,
    var: sp.Symbol,
    interval: tuple[Any, Any] | None,
    *,
    source_expr: sp.Expr | None = None,
    sample_point: sp.Expr | None = None,
) -> sp.Expr | None:
    """Compute a smooth real antiderivative on an open interval (low, high)."""
    antideriv = real_integrate_expression(expr, var, source_expr=source_expr or expr, wrap_all_logs=True)
    if antideriv is None:
        return None
    unwrapped = unwrap_abs_on_interval(antideriv, var, interval, sample_point=sample_point)
    ref = source_expr or expr
    if has_non_elementary_or_complex_branch(unwrapped, ref):
        return None
    return unwrapped


@dataclass(frozen=True)
class DifferentialFormDomainMetadata:
    """Preserved original and normalized domain metadata for differential-form ODEs."""

    domain_restrictions: tuple[str, ...]
    original_domain_latex: str
    normalized_domain_latex: str
    completeness: DomainCompleteness = DomainCompleteness.EXACT
    original_completeness: DomainCompleteness = DomainCompleteness.EXACT
    normalized_completeness: DomainCompleteness = DomainCompleteness.EXACT


def _combine_completeness(a: DomainCompleteness, b: DomainCompleteness) -> DomainCompleteness:
    """Combine two completeness flags using the conservative lattice UNKNOWN > PARTIAL > EXACT."""
    if a == DomainCompleteness.UNKNOWN or b == DomainCompleteness.UNKNOWN:
        return DomainCompleteness.UNKNOWN
    if a == DomainCompleteness.PARTIAL or b == DomainCompleteness.PARTIAL:
        return DomainCompleteness.PARTIAL
    return DomainCompleteness.EXACT


def _univariate_constraint_real_set(
    constraint: Any,
    x_var: sp.Symbol,
    y_var: sp.Symbol,
) -> tuple[sp.Set | None, DomainCompleteness, str | None]:
    """Resolve a SourceDomainConstraint into a subset of R over x_var, preserving completeness."""
    c_expr = getattr(constraint, "expr", None)
    rel = getattr(constraint, "relation", None)
    if c_expr is None or rel is None:
        return None, DomainCompleteness.UNKNOWN, "Ràng buộc miền xác định không đầy đủ."

    extra_syms = c_expr.free_symbols - {x_var}
    if extra_syms:
        kind = "đa biến" if y_var in extra_syms else "tham số ký hiệu"
        return (
            None,
            DomainCompleteness.PARTIAL,
            f"Ràng buộc {kind} ({c_expr}) không được ép thành khoảng một chiều theo {x_var}.",
        )

    if x_var not in c_expr.free_symbols:
        return sp.S.Reals, DomainCompleteness.EXACT, None

    try:
        if rel == "ge":
            sol = sp.solveset(c_expr >= 0, x_var, sp.S.Reals)
        elif rel == "gt":
            sol = sp.solveset(c_expr > 0, x_var, sp.S.Reals)
        elif rel == "ne":
            zeros = sp.solveset(sp.Eq(c_expr, 0), x_var, sp.S.Reals)
            if isinstance(zeros, sp.ConditionSet):
                return (
                    None,
                    DomainCompleteness.UNKNOWN,
                    f"Không thể giải đầy đủ điều kiện {c_expr} != 0 trên tập số thực.",
                )
            return sp.Complement(sp.S.Reals, zeros), DomainCompleteness.EXACT, None
        else:
            return None, DomainCompleteness.UNKNOWN, f"Không hỗ trợ loại ràng buộc '{rel}'."

        if isinstance(sol, sp.ConditionSet):
            return (
                None,
                DomainCompleteness.UNKNOWN,
                f"Không thể giải đầy đủ ràng buộc {c_expr} ({rel}) thành khoảng thực tường minh.",
            )
        return sol, DomainCompleteness.EXACT, None
    except Exception as exc:
        return None, DomainCompleteness.UNKNOWN, f"Không thể phân tích ràng buộc {c_expr}: {exc}"


def _extract_univariate_subexpr_constraints(
    expr: sp.Expr,
    x_var: sp.Symbol,
    y_var: sp.Symbol,
    *,
    require_nonzero: bool = False,
) -> tuple[sp.Set | None, DomainCompleteness, str | None]:
    """Analyze an expression with symbols outside {x_var}, separating multivariate/parametric rules."""
    dom_set: sp.Set | None = sp.S.Reals
    comp = DomainCompleteness.EXACT
    has_non_univar_restriction = False
    has_unsolved_restriction = False

    for node in sp.preorder_traversal(expr):
        target_part: sp.Expr | None = None
        if isinstance(node, sp.Pow):
            b, e = node.as_base_exp()
            e_simp = sp.simplify(e)
            if e_simp.is_negative or (e_simp.is_Rational and e_simp.q % 2 == 0):
                target_part = b
        elif isinstance(node, (sp.log, sp.tan, sp.cot, sp.sec, sp.csc, sp.asin, sp.acos, sp.acosh, sp.atanh)):
            target_part = node.args[0]

        if target_part is None or not target_part.free_symbols:
            continue

        if target_part.free_symbols - {x_var}:
            has_non_univar_restriction = True
            comp = _combine_completeness(comp, DomainCompleteness.PARTIAL)
            continue

        if x_var in target_part.free_symbols:
            try:
                part_set, part_comp = extract_expression_domain_with_completeness(node, x_var)
                comp = _combine_completeness(comp, part_comp)
                if isinstance(part_set, sp.ConditionSet) or part_comp == DomainCompleteness.UNKNOWN:
                    has_unsolved_restriction = True
                elif dom_set is not None and part_set is not None:
                    dom_set = sp.Intersection(dom_set, part_set)
            except Exception:
                has_unsolved_restriction = True
                comp = DomainCompleteness.UNKNOWN

    if require_nonzero and (expr.free_symbols - {x_var}):
        has_non_univar_restriction = True
        comp = _combine_completeness(comp, DomainCompleteness.PARTIAL)

    if has_unsolved_restriction and dom_set == sp.S.Reals:
        return (
            None,
            DomainCompleteness.UNKNOWN,
            f"Không thể xác định đầy đủ miền một biến trong biểu thức {expr}.",
        )

    if has_non_univar_restriction:
        if dom_set == sp.S.Reals:
            dom_set = None
        kind = "đa biến" if y_var in expr.free_symbols else "tham số ký hiệu"
        return (
            dom_set,
            comp,
            f"Biểu thức {expr} chứa ràng buộc miền {kind}; không ép thành khoảng thực một chiều đầy đủ.",
        )

    return dom_set, comp, None


def _univariate_expr_domain_set(
    expr: sp.Expr | None,
    x_var: sp.Symbol,
    y_var: sp.Symbol,
    *,
    require_nonzero: bool = False,
) -> tuple[sp.Set | None, DomainCompleteness, str | None]:
    """Extract univariate x_var domain set for an expression while preserving completeness."""
    if expr is None:
        return sp.S.Reals, DomainCompleteness.EXACT, None

    if expr.free_symbols - {x_var}:
        return _extract_univariate_subexpr_constraints(
            expr, x_var, y_var, require_nonzero=require_nonzero
        )

    if x_var not in expr.free_symbols:
        if require_nonzero and expr == 0:
            return sp.S.EmptySet, DomainCompleteness.EXACT, None
        return sp.S.Reals, DomainCompleteness.EXACT, None

    try:
        dom_set, comp = extract_expression_domain_with_completeness(expr, x_var)
    except Exception as exc:
        return (
            None,
            DomainCompleteness.UNKNOWN,
            f"Không thể phân tích miền xác định của biểu thức {expr}: {exc}",
        )

    if isinstance(dom_set, sp.ConditionSet) or comp == DomainCompleteness.UNKNOWN:
        return (
            None,
            DomainCompleteness.UNKNOWN,
            f"Miền xác định của biểu thức {expr} chưa thể giải hoàn chỉnh.",
        )

    note: str | None = None
    if require_nonzero:
        try:
            zeros = sp.solveset(sp.Eq(expr, 0), x_var, sp.S.Reals)
            if isinstance(zeros, sp.ConditionSet):
                comp = _combine_completeness(
                    comp,
                    DomainCompleteness.PARTIAL if dom_set != sp.S.Reals else DomainCompleteness.UNKNOWN,
                )
                note = f"Không thể xác định đầy đủ tập nghiệm triệt tiêu {expr} = 0."
                if dom_set == sp.S.Reals:
                    dom_set = None
            else:
                dom_set = sp.Intersection(dom_set, sp.Complement(sp.S.Reals, zeros))
        except Exception as exc:
            comp = _combine_completeness(
                comp,
                DomainCompleteness.PARTIAL if dom_set != sp.S.Reals else DomainCompleteness.UNKNOWN,
            )
            note = f"Không thể giải điều kiện {expr} != 0: {exc}"
            if dom_set == sp.S.Reals:
                dom_set = None

    return dom_set, comp, note


def _format_domain_with_completeness(
    dom_set: sp.Set | None,
    completeness: DomainCompleteness,
    var_name: str,
) -> tuple[str, str | None]:
    """Format domain set into LaTeX without ever claiming an incomplete S.Reals as complete."""
    if dom_set is None:
        return "", None
    if completeness != DomainCompleteness.EXACT and dom_set == sp.S.Reals:
        return "", None
    try:
        base_latex = format_set_latex(dom_set, var_name)
    except Exception as exc:
        return "", f"Không thể định dạng LaTeX cho miền xác định: {exc}"
    if completeness != DomainCompleteness.EXACT:
        return rf"{base_latex} \text{{ (một phần)}}", None
    return base_latex, None


def compute_differential_form_domain_metadata(
    *,
    parsed: ParsedODE,
    x_var: sp.Symbol,
    y_var: sp.Symbol,
    M_expr: sp.Expr,
    N_expr: sp.Expr,
    mu_expr: sp.Expr | None = None,
    extra_restrictions: tuple[str, ...] = (),
) -> DifferentialFormDomainMetadata:
    """Compute human-readable restrictions and LaTeX domain intervals preserving completeness."""
    restrictions: list[str] = list(parsed.original_domain_restrictions)
    restrictions.extend(extra_restrictions)

    if mu_expr is not None:
        restrictions.append(f"Điều kiện thừa số tích phân: \u03bc = {mu_expr} khác 0.")
        try:
            _, mu_denom = sp.fraction(mu_expr)
            if mu_denom != 1 and (x_var in mu_denom.free_symbols or y_var in mu_denom.free_symbols):
                restrictions.append(f"Điều kiện xác định của thừa số tích phân \u03bc: {mu_denom} khác 0.")
        except Exception as exc:
            restrictions.append(f"Không thể tách mẫu số của thừa số tích phân \u03bc: {exc}")

    for label, expr_val in ((f"M({x_var}, {y_var})", M_expr), (f"N({x_var}, {y_var})", N_expr)):
        try:
            _, denom = sp.fraction(expr_val)
            if denom != 1 and (x_var in denom.free_symbols or y_var in denom.free_symbols):
                restrictions.append(f"Điều kiện xác định của {label}: {denom} khác 0.")
        except Exception as exc:
            restrictions.append(f"Không thể tách mẫu số của {label}: {exc}")

    orig_set: sp.Set | None = sp.S.Reals
    orig_comp = DomainCompleteness.EXACT
    for constraint in getattr(parsed, "original_domain_constraints", ()):
        c_set, c_comp, c_note = _univariate_constraint_real_set(constraint, x_var, y_var)
        orig_comp = _combine_completeness(orig_comp, c_comp)
        if c_note:
            restrictions.append(c_note)
        if c_set is not None:
            if orig_set is not None:
                try:
                    orig_set = sp.Intersection(orig_set, c_set)
                except Exception as exc:
                    orig_comp = _combine_completeness(orig_comp, DomainCompleteness.PARTIAL)
                    restrictions.append(f"Không thể giao miền ràng buộc {constraint.expr}: {exc}")
            elif c_set != sp.S.Reals:
                orig_set = c_set
    if orig_comp != DomainCompleteness.EXACT and orig_set == sp.S.Reals:
        orig_set = None

    norm_set: sp.Set | None = orig_set
    norm_comp = orig_comp
    for expr_val, nonzero in ((M_expr, False), (N_expr, False), (mu_expr, True)):
        if expr_val is not None:
            e_set, e_comp, e_note = _univariate_expr_domain_set(
                expr_val, x_var, y_var, require_nonzero=nonzero
            )
            norm_comp = _combine_completeness(norm_comp, e_comp)
            if e_note:
                restrictions.append(e_note)
            if e_set is not None:
                if norm_set is not None:
                    try:
                        norm_set = sp.Intersection(norm_set, e_set)
                    except Exception as exc:
                        norm_comp = _combine_completeness(norm_comp, DomainCompleteness.PARTIAL)
                        restrictions.append(f"Không thể giao miền biểu thức {expr_val}: {exc}")
                elif e_set != sp.S.Reals:
                    norm_set = e_set
    if norm_comp != DomainCompleteness.EXACT and norm_set == sp.S.Reals:
        norm_set = None

    orig_latex, orig_fmt_err = _format_domain_with_completeness(orig_set, orig_comp, x_var.name)
    if orig_fmt_err:
        orig_comp = _combine_completeness(orig_comp, DomainCompleteness.UNKNOWN)
        restrictions.append(orig_fmt_err)
    norm_latex, norm_fmt_err = _format_domain_with_completeness(norm_set, norm_comp, x_var.name)
    if norm_fmt_err:
        norm_comp = _combine_completeness(norm_comp, DomainCompleteness.UNKNOWN)
        restrictions.append(norm_fmt_err)

    overall_comp = _combine_completeness(orig_comp, norm_comp)
    return DifferentialFormDomainMetadata(
        domain_restrictions=tuple(dict.fromkeys(restrictions)),
        original_domain_latex=orig_latex,
        normalized_domain_latex=norm_latex,
        completeness=overall_comp,
        original_completeness=orig_comp,
        normalized_completeness=norm_comp,
    )


def classify_finite_real_scalar(val: sp.Expr, source_exprs: Iterable[sp.Expr] = ()) -> tuple[str, str]:
    """Classify an evaluated scalar as 'valid', 'invalid', or 'unknown' for real finiteness."""
    allow_complex = any(src.has(sp.I) for src in source_exprs)
    return classify_scalar_real_finite(val, allow_complex=allow_complex)


def is_finite_real_scalar(val: sp.Expr, source_exprs: Iterable[sp.Expr] = ()) -> tuple[bool, str]:
    """Fail-closed check returning True only when scalar is proven finite and real (unless complex inputs)."""
    status, reason = classify_finite_real_scalar(val, source_exprs)
    return status == "valid", reason


def validate_differential_form_ic(
    *,
    raw_input: str,
    parsed: ParsedODE,
    x_var: sp.Symbol,
    y_var: sp.Symbol,
    M_expr: sp.Expr,
    N_expr: sp.Expr,
    elapsed_ms_fn: Callable[[], float],
) -> SolutionResponse | None:
    """Validate the initial condition (x0, y0) for M(x, y) dx + N(x, y) dy = 0."""
    if parsed.initial_condition is None:
        return None

    x0, y0 = parsed.initial_condition
    domain_meta = compute_differential_form_domain_metadata(
        parsed=parsed,
        x_var=x_var,
        y_var=y_var,
        M_expr=M_expr,
        N_expr=N_expr,
    )
    allow_complex = M_expr.has(sp.I) or N_expr.has(sp.I)
    checks: tuple[tuple[str, sp.Expr | None, tuple[Any, ...], str, str], ...] = (
        (
            "initial_point_domain_validation",
            None,
            getattr(parsed, "original_domain_constraints", ()),
            f"Điểm ban đầu ({x0}, {y0}) vi phạm điều kiện xác định ban đầu: {{err}}",
            f"Điều kiện ban đầu ({x0}, {y0}) không hợp lệ: {{err}}.",
        ),
        (
            "initial_point_domain_validation",
            M_expr,
            (),
            f"Điểm ban đầu ({x0}, {y0}) không thuộc miền xác định của M({x_var}, {y_var}): {{err}}",
            f"Điều kiện ban đầu ({x0}, {y0}) không hợp lệ đối với M({x_var}, {y_var}): {{err}}.",
        ),
        (
            "initial_point_domain_validation",
            N_expr,
            (),
            f"Điểm ban đầu ({x0}, {y0}) không thuộc miền xác định của N({x_var}, {y_var}): {{err}}",
            f"Điều kiện ban đầu ({x0}, {y0}) không hợp lệ đối với N({x_var}, {y_var}): {{err}}.",
        ),
    )

    unknown_failure: tuple[str, str, str, str] | None = None
    for method, expr, src_constraints, detail_tpl, warn_tpl in checks:
        dom_status, err = evaluate_initial_point_domain(
            expr,
            x_var,
            y_var,
            x0,
            y0,
            original_denominators=parsed.original_denominators,
            leading_coeffs=parsed.leading_coeffs,
            source_constraints=src_constraints,
            allow_complex=allow_complex,
        )
        if dom_status == "invalid":
            return SolutionResponse(
                status=SolutionStatus.INVALID_INPUT,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method=method,
                    details=detail_tpl.format(err=err),
                ),
                raw_input=raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                domain_restrictions=domain_meta.domain_restrictions,
                original_domain_latex=domain_meta.original_domain_latex,
                normalized_domain_latex=domain_meta.normalized_domain_latex,
                domain_completeness=domain_meta.completeness,
                warnings=(warn_tpl.format(err=err),),
                execution_time_ms=elapsed_ms_fn(),
            )
        if dom_status == "unknown" and unknown_failure is None:
            unknown_failure = (method, detail_tpl.format(err=err), warn_tpl.format(err=err), err)

    if unknown_failure is not None:
        method, details_msg, warn_msg, _ = unknown_failure
        return SolutionResponse(
            status=SolutionStatus.UNVERIFIED,
            verification=VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="initial_condition_domain_unverified",
                details=details_msg,
            ),
            raw_input=raw_input,
            canonical_input=parsed.canonical_eq,
            final_result="",
            final_latex="",
            domain_restrictions=domain_meta.domain_restrictions,
            original_domain_latex=domain_meta.original_domain_latex,
            normalized_domain_latex=domain_meta.normalized_domain_latex,
            domain_completeness=domain_meta.completeness,
            warnings=(warn_msg,),
            execution_time_ms=elapsed_ms_fn(),
        )

    return None

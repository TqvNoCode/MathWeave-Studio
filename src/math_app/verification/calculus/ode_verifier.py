"""Independent mathematical verification for differential equation solutions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import combinations
import math
import re
from typing import Any
import sympy as sp
from sympy.core.function import AppliedUndef

from math_app.application.dtos import BranchSolution, VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class ResidualCheckOutcome(str, Enum):
    PROVED_ZERO = "proved_zero"
    PROVED_NONZERO = "proved_nonzero"
    UNKNOWN = "unknown"
    INVALID_DOMAIN = "invalid_domain"


def _prove_symbolic_zero(
    expr: sp.Expr,
    constants: tuple[sp.Symbol, ...] = (),
    domain_interval: tuple[sp.Expr | float, sp.Expr | float] | str | None = None,
    variable: sp.Symbol | None = None,
) -> bool:
    """Rigorously attempt to establish that an expression is identically zero using symbolic methods.

    Never uses numerical probes to declare an expression identically zero.
    Supports domain assumptions when domain_interval is provided.
    """
    try:
        if expr == 0:
            return True
        s = sp.simplify(expr)
        if s == 0:
            return True
        s_exp = sp.simplify(sp.expand(expr))
        if s_exp == 0:
            return True
        s_trig = sp.simplify(sp.trigsimp(s))
        if s_trig == 0:
            return True
        try:
            s_fu = sp.simplify(sp.fu(s))
            if s_fu == 0:
                return True
        except Exception:
            pass
        try:
            s_exp_rewrite = sp.simplify(s.rewrite(sp.exp))
            if s_exp_rewrite == 0:
                return True
        except Exception:
            pass
        s_rad = sp.simplify(sp.radsimp(s))
        if s_rad == 0:
            return True
        s_can = sp.simplify(sp.cancel(s))
        if s_can == 0:
            return True

        # Handle Piecewise expressions resulting from absolute value derivatives
        if isinstance(s, sp.Piecewise):
            # Check if generic condition (True) has zero value
            generic_zero = False
            for val, cond in s.args:
                if cond is True and sp.simplify(val) == 0:
                    generic_zero = True
                    break
            if generic_zero:
                return True

        # Check domain restrictions/assumptions on variable
        if variable is not None and expr.has(variable):
            is_positive = False
            is_negative = False
            if variable.is_positive:
                is_positive = True
            elif variable.is_negative:
                is_negative = True

            if domain_interval is not None:
                if isinstance(domain_interval, str):
                    d_str = domain_interval.replace(" ", "")
                    if ">0" in d_str or ">=0" in d_str or "(0,oo)" in d_str or "(0,inf)" in d_str:
                        is_positive = True
                    elif "<0" in d_str or "<=0" in d_str or "(-oo,0)" in d_str or "(-inf,0)" in d_str:
                        is_negative = True
                elif isinstance(domain_interval, (tuple, list)) and len(domain_interval) == 2:
                    low, high = domain_interval
                    try:
                        if low is not None and float(sp.N(low)) >= 0:
                            is_positive = True
                        if high is not None and float(sp.N(high)) <= 0:
                            is_negative = True
                    except Exception:
                        if low is not None:
                            low_s = sp.sympify(low)
                            if low_s.is_nonnegative or low_s.is_positive or getattr(low_s, "func", None) == sp.exp:
                                is_positive = True
                        if high is not None:
                            high_s = sp.sympify(high)
                            if high_s.is_nonpositive or high_s.is_negative:
                                is_negative = True

            if is_positive:
                var_pos = sp.Symbol(variable.name, positive=True)
                s_pos = sp.simplify(expr.subs(variable, var_pos).doit())
                if s_pos == 0 or sp.simplify(sp.cancel(s_pos)) == 0:
                    return True
                if s_pos.has(sp.Add) and sp.simplify(sp.radsimp(s_pos)) == 0:
                    return True
            elif is_negative:
                var_neg = sp.Symbol(variable.name, negative=True)
                s_neg = sp.simplify(expr.subs(variable, var_neg).doit())
                if s_neg == 0 or sp.simplify(sp.cancel(s_neg)) == 0:
                    return True
                if s_neg.has(sp.Add) and sp.simplify(sp.radsimp(s_neg)) == 0:
                    return True

        # Check for free integration constants (e.g. C, C1, C2)
        active_consts = [c for c in constants if expr.has(c)]
        if not active_consts:
            active_consts = [sym for sym in expr.free_symbols if re.match(r"^C\d*$", sym.name)]

        if active_consts:
            # 1. Check partial derivatives with respect to each constant
            all_derivs_zero = True
            for c in active_consts:
                d_c = sp.diff(expr, c)
                other_consts = tuple(ac for ac in active_consts if ac != c)
                if not _prove_symbolic_zero(d_c, other_consts, domain_interval=domain_interval, variable=variable):
                    all_derivs_zero = False
                    break
            if all_derivs_zero:
                # Expression is constant with respect to all active constants.
                rem_zero = expr.subs([(c, 0) for c in active_consts])
                if _prove_symbolic_zero(rem_zero, (), domain_interval=domain_interval, variable=variable):
                    return True

            # 2. Check polynomial coefficients in constants
            try:
                poly = expr.as_poly(*active_consts)
                if poly is not None:
                    if all(_prove_symbolic_zero(c_val, (), domain_interval=domain_interval, variable=variable) for c_val in poly.coeffs()):
                        return True
            except Exception:
                pass
    except Exception:
        return False
    return False


def _simplify_limit_expr(expr: sp.Expr) -> sp.Expr:
    """Cancel rational terms before SymPy limits/series to prevent 0/0 nseries hangs."""
    if not isinstance(expr, sp.Expr) or expr.has(sp.Integral, sp.Piecewise, sp.AccumBounds, AppliedUndef):
        return expr
    try:
        return sp.cancel(sp.together(expr))
    except Exception:
        try:
            return sp.simplify(expr)
        except Exception:
            return expr


def _diff_real_expr(
    expr: sp.Expr,
    var: sp.Symbol,
    domain_interval: Any = None,
    *,
    side: str | None = None,
    point: Any = None,
) -> sp.Expr:
    """Differentiate with domain-appropriate real assumptions (preventing re(t)/Derivative artifacts)."""
    work_var = sp.Symbol(var.name, real=True)
    # Infer strict sign when domain interval or one-sided zero limit determines it
    try:
        if side == "-" and point == 0:
            work_var = sp.Symbol(var.name, negative=True)
        elif side == "+" and point == 0:
            work_var = sp.Symbol(var.name, positive=True)
        elif isinstance(domain_interval, (tuple, list)) and len(domain_interval) == 2:
            low, high = domain_interval
            if high is not None and high != sp.oo and float(sp.N(high)) <= 0:
                work_var = sp.Symbol(var.name, negative=True)
            elif low is not None and low != -sp.oo and float(sp.N(low)) >= 0:
                work_var = sp.Symbol(var.name, positive=True)
        elif isinstance(domain_interval, str):
            d_str = domain_interval.replace(" ", "")
            if "<0" in d_str or "<=0" in d_str or "(-oo,0)" in d_str:
                work_var = sp.Symbol(var.name, negative=True)
            elif ">0" in d_str or ">=0" in d_str or "(0,oo)" in d_str:
                work_var = sp.Symbol(var.name, positive=True)
    except Exception:
        pass

    if not expr.has(sp.Abs, sp.sign) and getattr(var, "is_real", None) is True and work_var == sp.Symbol(var.name, real=True):
        return sp.diff(expr, var)

    sub_expr = expr.subs(var, work_var) if work_var != var else expr
    diff_res = sp.diff(sub_expr, work_var)
    return diff_res.subs(work_var, var) if work_var != var else diff_res


def _filter_probe_points_by_domain(
    probe_points: tuple[float, ...],
    variable: sp.Symbol,
    domain_interval: tuple[sp.Expr | float, sp.Expr | float] | str | None = None,
    domain_restrictions: tuple[str, ...] = (),
) -> list[float]:
    """Filter or generate probe points conforming to the specified domain."""
    filtered: list[float] = list(probe_points)
    is_positive_domain = False
    is_negative_domain = False
    lower_bound: float | None = None
    upper_bound: float | None = None

    if variable.is_positive:
        is_positive_domain = True
    elif variable.is_negative:
        is_negative_domain = True

    if domain_interval is not None:
        if isinstance(domain_interval, str):
            d_str = domain_interval.replace(" ", "")
            if ">0" in d_str or ">=0" in d_str or "(0,oo)" in d_str or "(0,inf)" in d_str:
                is_positive_domain = True
            elif "<0" in d_str or "<=0" in d_str or "(-oo,0)" in d_str or "(-inf,0)" in d_str:
                is_negative_domain = True
        elif isinstance(domain_interval, (tuple, list)) and len(domain_interval) == 2:
            a_val, b_val = domain_interval
            try:
                if a_val != -sp.oo and a_val is not None:
                    lower_bound = float(sp.N(a_val))
                if b_val != sp.oo and b_val is not None:
                    upper_bound = float(sp.N(b_val))
            except Exception:
                pass

    for restr in domain_restrictions:
        r_str = restr.replace(" ", "")
        if ">0" in r_str or ">=0" in r_str:
            is_positive_domain = True
        elif "<0" in r_str or "<=0" in r_str:
            is_negative_domain = True

    if is_positive_domain:
        filtered = [pt for pt in filtered if pt > 0]
        if not filtered:
            filtered = [0.19, 0.47, 0.83, 1.27, 2.13, 3.71]
    elif is_negative_domain:
        filtered = [pt for pt in filtered if pt < 0]
        if not filtered:
            filtered = [-0.19, -0.47, -0.83, -1.27, -2.13, -3.71]

    if lower_bound is not None:
        filtered = [pt for pt in filtered if pt > lower_bound]
        if not filtered:
            filtered = [lower_bound + 0.2, lower_bound + 0.5, lower_bound + 1.2, lower_bound + 2.5]
    if upper_bound is not None:
        filtered = [pt for pt in filtered if pt < upper_bound]
        if not filtered:
            filtered = [upper_bound - 0.2, upper_bound - 0.5, upper_bound - 1.2, upper_bound - 2.5]

    return filtered


def _simplify_zero_bound_integrals(expr: sp.Expr) -> sp.Expr:
    """Safely collapse only definite integrals whose lower and upper bounds are identical."""
    changed = True
    cur = expr
    while changed:
        changed = False
        for node in cur.atoms(sp.Integral):
            if all(len(lim) == 3 and _prove_symbolic_zero(lim[1] - lim[2]) for lim in node.limits):
                cur = cur.subs(node, 0)
                changed = True
                break
    return cur


def is_point_in_interval_interior(t0: sp.Expr, low: sp.Expr, high: sp.Expr) -> bool:
    """Determine strictly if t0 lies within the open interior (low, high) symbolically."""
    if low is not None and low != -sp.oo:
        diff_low = sp.simplify(t0 - low)
        if _prove_symbolic_zero(diff_low) or diff_low == 0:
            return False
        if diff_low.is_positive is False or diff_low.is_negative is True:
            return False
        try:
            if float(sp.N(diff_low)) <= 0:
                return False
        except Exception:
            pass

    if high is not None and high != sp.oo:
        diff_high = sp.simplify(high - t0)
        if _prove_symbolic_zero(diff_high) or diff_high == 0:
            return False
        if diff_high.is_positive is False or diff_high.is_negative is True:
            return False
        try:
            if float(sp.N(diff_high)) <= 0:
                return False
        except Exception:
            pass

    return True


def _extract_integration_constants(expr: sp.Expr, var: sp.Symbol) -> set[sp.Symbol]:
    """Extract all integration constant symbols appearing in an expression."""
    consts = set()
    for s in expr.free_symbols:
        if s.name != var.name and (s.name.startswith("C") or "const" in s.name.lower()):
            consts.add(s)
    return consts


@dataclass(frozen=True)
class _ConstraintBranch:
    """Exhaustive symbolic branch assigning integration constants over real/integer parameters."""

    assignments: dict[sp.Symbol, sp.Expr]
    param_domains: dict[sp.Symbol, sp.Set]


def _apply_real_assumptions(
    expr: sp.Expr,
    param_domains: dict[sp.Symbol, sp.Set],
    free_consts: set[sp.Symbol] = (),
) -> sp.Expr:
    """Bind integration constants and parameters to temporary symbols with exact real/integer assumptions."""
    sub_map: dict[sp.Symbol, sp.Symbol] = {}
    for sym, dom in param_domains.items():
        if dom.is_subset(sp.S.Integers) is True:
            if sym.is_integer is not True:
                sub_map[sym] = sp.Dummy(sym.name, integer=True)
        elif dom.is_subset(sp.S.Reals) is True:
            if sym.is_real is not True:
                sub_map[sym] = sp.Dummy(sym.name, real=True)
    for sym in free_consts:
        if sym not in param_domains and sym not in sub_map and sym.is_real is not True:
            sub_map[sym] = sp.Dummy(sym.name, real=True)
    return expr.subs(sub_map) if sub_map else expr


def _is_valid_real_limit_expr(
    expr: sp.Expr | None,
    param_domains: dict[sp.Symbol, sp.Set],
    free_consts: set[sp.Symbol] = (),
) -> bool:
    """Verify symbolically that a limit expression is determinate, finite, and real over all parameters."""
    if expr is None:
        return False
    if expr.has(
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
    if getattr(expr, "is_finite", None) is False:
        return False
    assumed = _apply_real_assumptions(expr, param_domains, free_consts)
    if getattr(assumed, "is_finite", None) is False:
        return False
    if getattr(assumed, "is_real", None) is not True:
        return False
    return True


def _is_proven_nonzero_expr(
    expr: sp.Expr | None,
    param_domains: dict[sp.Symbol, sp.Set] | None = None,
    free_consts: set[sp.Symbol] = (),
) -> bool:
    """Return True only when expr is mathematically proven nonzero over the full parameter domain."""
    if expr is None:
        return False
    if expr.has(sp.zoo, sp.nan, sp.oo, -sp.oo, sp.Limit, sp.AccumBounds, AppliedUndef):
        return False
    try:
        simplified = sp.simplify(expr)
    except Exception:
        simplified = expr
    assumed = _apply_real_assumptions(simplified, param_domains or {}, free_consts)
    if getattr(assumed, "is_nonzero", None) is True and getattr(assumed, "is_finite", None) is not False and getattr(assumed, "is_real", None) is True:
        return True
    if not assumed.free_symbols and not assumed.has(sp.I):
        if _prove_symbolic_zero(assumed):
            return False
        if assumed.is_number:
            try:
                return abs(complex(sp.N(assumed))) > 1e-12
            except Exception:
                return False
    return False


def _has_proven_nonzero_full_row_minor(
    mat: sp.Matrix,
    param_domains: dict[sp.Symbol, sp.Set] | None = None,
) -> bool:
    """Check whether a full-row-rank minor of coefficient matrix mat is proven nonzero everywhere."""
    if mat.rows == 0 or mat.cols < mat.rows:
        return False
    if mat.rows == mat.cols:
        try:
            return _is_proven_nonzero_expr(mat.det(), param_domains)
        except Exception:
            return False
    if math.comb(mat.cols, mat.rows) > 30:
        return False
    for cols in combinations(range(mat.cols), mat.rows):
        try:
            minor = mat[:, list(cols)].det()
            if _is_proven_nonzero_expr(minor, param_domains):
                return True
        except Exception:
            continue
    return False


def _factor_denominator_terms(expr: sp.Expr) -> list[sp.Expr]:
    """Collect symbolic denominator factors from an expression without dropping unsimplified singularities."""
    dens: list[sp.Expr] = []
    try:
        _, den_t = sp.together(expr).as_numer_denom()
        if den_t != 1:
            dens.append(den_t)
    except Exception:
        pass
    for node in sp.preorder_traversal(expr):
        if isinstance(node, sp.Pow):
            base, exp = node.as_base_exp()
            if exp.is_negative is True or (exp.is_number and sp.N(exp) < 0):
                dens.append(base)
    return dens


def _check_branch_denominators(
    exprs: list[sp.Expr],
    branch: _ConstraintBranch,
    var: sp.Symbol | None = None,
    free_consts: set[sp.Symbol] = (),
) -> tuple[str, _ConstraintBranch, str]:
    """Ensure no parameter-dependent denominator in exprs vanishes on branch.param_domains."""
    param_domains = dict(branch.param_domains)
    for expr in exprs:
        sub_candidates = [expr]
        try:
            sub_candidates.append(sp.simplify(expr))
        except Exception:
            pass
        for cand in sub_candidates:
            for den in _factor_denominator_terms(cand):
                try:
                    _, factors = sp.factor_list(den)
                    factor_exprs = [f for f, _ in factors]
                except Exception:
                    factor_exprs = [den]
                for fac in factor_exprs:
                    if var is not None and var in fac.free_symbols:
                        continue
                    param_syms = fac.free_symbols & set(param_domains.keys())
                    if not param_syms:
                        if not fac.free_symbols and _prove_symbolic_zero(fac):
                            return ("empty", branch, f"Mẫu số {fac} triệt tiêu trên nhánh nghiệm.")
                        if fac.free_symbols and not _is_proven_nonzero_expr(fac, param_domains, free_consts):
                            return (
                                "unresolved",
                                branch,
                                f"Không thể chứng minh mẫu số {fac} khác 0 trên toàn miền thực.",
                            )
                        continue
                    fac_assumed = _apply_real_assumptions(fac, param_domains)
                    if fac_assumed.is_nonzero is True:
                        continue
                    if len(param_syms) == 1 and fac.free_symbols <= set(param_domains.keys()):
                        p = next(iter(param_syms))
                        dom = param_domains[p]
                        try:
                            zset = sp.solveset(fac, p, domain=dom)
                        except Exception as exc:
                            return ("unresolved", branch, f"Không thể kiểm tra điều kiện khác 0 của mẫu số {fac}: {exc}")
                        if zset == sp.S.EmptySet:
                            continue
                        if zset.has(sp.ConditionSet) or not isinstance(zset, sp.FiniteSet):
                            return (
                                "unresolved",
                                branch,
                                f"Không thể xác định đầy đủ nghiệm triệt tiêu mẫu số {fac} trên miền tham số.",
                            )
                        new_dom = sp.Complement(dom, zset)
                        if new_dom == sp.S.EmptySet:
                            return ("empty", branch, f"Mẫu số {fac} triệt tiêu trên toàn miền tham số.")
                        param_domains[p] = new_dom
                    else:
                        return (
                            "unresolved",
                            branch,
                            f"Không thể chứng minh mẫu số {fac} khác 0 trên toàn miền tham số.",
                        )
    return ("ok", _ConstraintBranch(assignments=branch.assignments, param_domains=param_domains), "")


def _is_finite_real_scalar(val: sp.Expr) -> tuple[str, sp.Expr | None]:
    """Validate whether a scalar candidate root from solveset is genuinely real and finite."""
    if val.has(sp.zoo, sp.nan, sp.oo, -sp.oo, sp.Limit, sp.AccumBounds):
        return ("invalid", None)
    if val.is_real is False:
        return ("nonreal", None)
    if val.has(sp.I):
        try:
            im_part = sp.simplify(sp.im(val))
            if im_part == 0:
                re_val = sp.simplify(sp.re(val))
                if re_val.is_real is True and re_val.is_finite is not False:
                    return ("real", re_val)
            elif im_part.is_nonzero is True or im_part != 0:
                return ("nonreal", None)
        except Exception:
            return ("unresolved", None)
        return ("unresolved", None)
    if val.is_real is True and val.is_finite is not False:
        return ("real", val)
    return ("unresolved", None)


def _decompose_univariate_set(
    var: sp.Symbol,
    solset: sp.Set,
) -> tuple[str, list[tuple[sp.Expr, dict[sp.Symbol, sp.Set]]], str]:
    """Decompose a SymPy Set into exhaustive (expression, parameter_domains) items without sampling."""
    if solset == sp.S.EmptySet:
        return ("empty", [], f"Phương trình vô nghiệm đối với {var}.")

    if solset.has(sp.ConditionSet):
        return (
            "unresolved",
            [],
            f"Không thể xác định tập nghiệm giải tích đầy đủ cho {var}: {solset}.",
        )

    if isinstance(solset, sp.FiniteSet):
        items: list[tuple[sp.Expr, dict[sp.Symbol, sp.Set]]] = []
        for r in solset:
            kind, cleaned = _is_finite_real_scalar(r)
            if kind == "unresolved":
                return ("unresolved", [], f"Không thể xác minh tính thực hữu hạn của nghiệm {r}.")
            if kind == "real" and cleaned is not None:
                items.append((cleaned, {}))
        if not items:
            return ("empty", [], f"Không tồn tại nghiệm thực cho {var}.")
        return ("resolved", items, "")

    if isinstance(solset, sp.Union):
        all_items: list[tuple[sp.Expr, dict[sp.Symbol, sp.Set]]] = []
        for part in solset.args:
            if not isinstance(part, sp.Set):
                return ("unresolved", [], f"Thành phần hợp nghiệm không xác định: {part}.")
            out, part_items, msg = _decompose_univariate_set(var, part)
            if out == "unresolved":
                return ("unresolved", [], msg)
            if out == "resolved":
                all_items.extend(part_items)
        if not all_items:
            return ("empty", [], f"Tập hợp nghiệm của {var} rỗng trên miền xác định.")
        return ("resolved", all_items, "")

    if isinstance(solset, sp.ImageSet):
        lam = solset.lamda
        base_sets = solset.base_sets
        if len(lam.variables) != 1 or len(base_sets) != 1:
            return ("unresolved", [], f"Không thể phân giải đầy đủ ImageSet đa chiều: {solset}.")
        base = base_sets[0]
        if base.has(sp.ConditionSet):
            return ("unresolved", [], f"Miền cơ sở của ImageSet chưa được giải: {solset}.")
        if base.is_subset(sp.S.Integers) is True:
            param = sp.Dummy("k", integer=True)
            expr_k = lam(param)
            if not _is_valid_real_limit_expr(expr_k, {param: base}):
                return ("unresolved", [], f"Biểu thức họ nghiệm {expr_k} không xác định thực hữu hạn trên {base}.")
            return ("resolved", [(expr_k, {param: base})], "")
        if base.is_subset(sp.S.Reals) is True:
            param = sp.Dummy("tau", real=True)
            expr_t = lam(param)
            if not _is_valid_real_limit_expr(expr_t, {param: base}):
                return ("unresolved", [], f"Biểu thức họ nghiệm {expr_t} không xác định thực hữu hạn trên {base}.")
            return ("resolved", [(expr_t, {param: base})], "")
        return ("unresolved", [], f"Miền tham số không thuộc tập số thực: {solset}.")

    if solset == sp.S.Reals or solset == sp.S.Integers:
        is_int = solset == sp.S.Integers
        param = sp.Dummy("k" if is_int else "tau", integer=is_int, real=True)
        return ("resolved", [(param, {param: solset})], "")

    if isinstance(solset, sp.Interval):
        if solset.left.has(sp.I, sp.zoo, sp.nan) or solset.right.has(sp.I, sp.zoo, sp.nan):
            return ("unresolved", [], f"Khoảng nghiệm không hợp lệ trên miền thực: {solset}.")
        param = sp.Dummy("tau", real=True)
        return ("resolved", [(param, {param: solset})], "")

    if isinstance(solset, sp.Complement):
        base_set, excl_set = solset.args[0], solset.args[1]
        if isinstance(base_set, sp.Union):
            pieces = [sp.Complement(arg, excl_set) for arg in base_set.args]
            return _decompose_univariate_set(var, sp.Union(*pieces))
        if isinstance(base_set, sp.ImageSet) and isinstance(excl_set, sp.FiniteSet):
            lam = base_set.lamda
            base = base_set.base_sets[0]
            if len(lam.variables) == 1 and base.is_subset(sp.S.Integers) is True:
                param = sp.Dummy("k", integer=True)
                expr_k = lam(param)
                bad_params = []
                for ex in excl_set:
                    try:
                        ex_set = sp.solveset(expr_k - ex, param, domain=base)
                        if ex_set.has(sp.ConditionSet):
                            return ("unresolved", [], f"Không thể quy đổi phần bù tập nghiệm {solset}.")
                        if isinstance(ex_set, sp.FiniteSet):
                            bad_params.extend(list(ex_set))
                        elif ex_set != sp.S.EmptySet:
                            return ("unresolved", [], f"Không thể quy đổi phần bù tập nghiệm {solset}.")
                    except Exception:
                        return ("unresolved", [], f"Không thể quy đổi phần bù tập nghiệm {solset}.")
                new_base = sp.Complement(base, sp.FiniteSet(*bad_params)) if bad_params else base
                if new_base == sp.S.EmptySet:
                    return ("empty", [], f"Tập nghiệm {solset} rỗng.")
                if not _is_valid_real_limit_expr(expr_k, {param: new_base}):
                    return ("unresolved", [], f"Biểu thức họ nghiệm {expr_k} không thực hữu hạn trên {new_base}.")
                return ("resolved", [(expr_k, {param: new_base})], "")
        if (base_set == sp.S.Reals or base_set == sp.S.Integers or isinstance(base_set, sp.Interval)) and isinstance(
            excl_set, sp.FiniteSet
        ):
            is_int = base_set.is_subset(sp.S.Integers) is True
            param = sp.Dummy("k" if is_int else "tau", integer=is_int, real=True)
            return ("resolved", [(param, {param: solset})], "")
        return ("unresolved", [], f"Không thể phân giải đầy đủ tập bù {solset}.")

    return ("unresolved", [], f"Dạng tập nghiệm không thể chứng minh đầy đủ: {solset}.")


def _compose_branches(
    outer: _ConstraintBranch,
    inner: _ConstraintBranch,
    rem_consts: set[sp.Symbol],
) -> _ConstraintBranch:
    """Compose outer branch with inner branch solving active parameters and remaining constants."""
    new_assignments: dict[sp.Symbol, sp.Expr] = {}
    for c, expr_c in outer.assignments.items():
        new_assignments[c] = sp.simplify(expr_c.subs(inner.assignments)) if inner.assignments else expr_c
    for c in rem_consts:
        if c in inner.assignments:
            new_assignments[c] = inner.assignments[c]

    used_params = set()
    for val in new_assignments.values():
        used_params |= val.free_symbols

    new_param_domains: dict[sp.Symbol, sp.Set] = {}
    for p, dom in outer.param_domains.items():
        if p not in inner.assignments and p in used_params:
            new_param_domains[p] = dom
    for p, dom in inner.param_domains.items():
        if p in used_params:
            new_param_domains[p] = dom

    return _ConstraintBranch(assignments=new_assignments, param_domains=new_param_domains)


def _merge_branch_pair_lists(
    outer: _ConstraintBranch,
    inner_branches: list[_ConstraintBranch],
    rem_consts: set[sp.Symbol],
) -> list[_ConstraintBranch]:
    return [_compose_branches(outer, ib, rem_consts) for ib in inner_branches]


def _verify_branch_satisfies_equations(
    br: _ConstraintBranch,
    equations: list[sp.Expr],
) -> tuple[bool, bool]:
    """Check whether a branch satisfies all equations. Returns (all_zero, uncertain)."""
    for eq in equations:
        try:
            sub_eq = eq.subs(br.assignments)
            assumed = _apply_real_assumptions(sub_eq, br.param_domains)
            if not _prove_symbolic_zero(assumed):
                return (False, False)
        except Exception:
            return (False, True)
    return (True, False)


def _solve_real_constraint_system(
    equations: list[sp.Expr | sp.Equality],
    variables: list[sp.Symbol],
    var_domains: dict[sp.Symbol, sp.Set] | None = None,
    _depth: int = 0,
    _allow_groebner: bool = True,
) -> tuple[str, list[_ConstraintBranch], str]:
    """Solve constraint system over real/integer domains using completeness-preserving methods only.

    Returns:
        (outcome, branches, message)
        outcome:
            - 'resolved': exhaustive proven real solution set as union of _ConstraintBranch items
            - 'empty': mathematically proven EmptySet over specified domains
            - 'unresolved': completeness or emptiness cannot be proven
    """
    if _depth > 12:
        return ("unresolved", [], "Hệ phương trình ràng buộc vượt quá độ sâu phân giải quy nạp.")

    doms = {v: (var_domains or {}).get(v, sp.S.Reals) for v in variables}
    var_set = set(variables)

    norm_eqs: list[sp.Expr] = []
    for eq in equations:
        if eq is sp.S.true or eq is True:
            continue
        if eq is sp.S.false or eq is False:
            return ("empty", [], "Phương trình ràng buộc mâu thuẫn (False).")
        eq_expr = (eq.lhs - eq.rhs) if isinstance(eq, sp.Equality) else eq
        if eq_expr.has(sp.zoo, sp.nan, sp.oo, -sp.oo, sp.Limit, sp.AccumBounds):
            return ("unresolved", [], f"Biểu thức ràng buộc chứa giá trị chưa xác định: {eq_expr}.")
        eq_vars = eq_expr.free_symbols & var_set
        if not eq_vars:
            if _prove_symbolic_zero(eq_expr):
                continue
            assumed_const = _apply_real_assumptions(eq_expr, doms)
            if assumed_const.is_nonzero is True:
                return ("empty", [], f"Điều kiện đại số mâu thuẫn {eq_expr} = 0.")
            if assumed_const.is_number and not assumed_const.has(sp.I, AppliedUndef):
                try:
                    if abs(complex(sp.N(assumed_const))) > 1e-12:
                        return ("empty", [], f"Điều kiện đại số mâu thuẫn {eq_expr} = 0.")
                except Exception:
                    pass
            return ("unresolved", [], f"Không thể xác minh phương trình hằng số {eq_expr} = 0.")
        norm_eqs.append(eq_expr)

    if not norm_eqs:
        free_assigns = {}
        free_doms = {}
        for v in variables:
            is_int = doms[v].is_subset(sp.S.Integers) is True
            param = v if v in (var_domains or {}) else sp.Dummy(v.name, integer=is_int, real=True)
            free_assigns[v] = param
            free_doms[param] = doms[v]
        return ("resolved", [_ConstraintBranch(assignments=free_assigns, param_domains=free_doms)], "")

    active_vars = [v for v in variables if any(v in eq.free_symbols for eq in norm_eqs)]
    untouched_vars = [v for v in variables if v not in active_vars]

    def _with_untouched(branches: list[_ConstraintBranch]) -> list[_ConstraintBranch]:
        if not untouched_vars:
            return branches
        res_branches: list[_ConstraintBranch] = []
        for br in branches:
            new_assigns = dict(br.assignments)
            new_doms = dict(br.param_domains)
            for uv in untouched_vars:
                if uv in (var_domains or {}):
                    new_assigns[uv] = uv
                    new_doms[uv] = doms[uv]
                else:
                    # Leave original untouched integration constant unbound if never mentioned in norm_eqs
                    pass
            res_branches.append(_ConstraintBranch(assignments=new_assigns, param_domains=new_doms))
        return res_branches

    # Check definite sign impossibility of any equation under real/integer assumptions
    for eq in norm_eqs:
        assumed_eq = _apply_real_assumptions(eq, doms, set(active_vars))
        if assumed_eq.is_positive is True or assumed_eq.is_negative is True:
            return (
                "empty",
                [],
                f"Phương trình {eq} = 0 không đổi dấu và vô nghiệm thực trên miền đã cho.",
            )

    # Strategy 1: Univariate reduction (group all univariate equations by variable and intersect)
    univariate_groups: dict[sp.Symbol, list[sp.Expr]] = {}
    for eq in norm_eqs:
        ev = eq.free_symbols & set(active_vars)
        if len(ev) == 1:
            uvar = next(iter(ev))
            univariate_groups.setdefault(uvar, []).append(eq)

    if univariate_groups:
        # Prefer variables whose equations yield finite or explicit periodic sets
        chosen_var = next(iter(univariate_groups))
        chosen_eqs = univariate_groups[chosen_var]
        u_dom = doms[chosen_var]
        for ueq in chosen_eqs:
            ext_in_ueq = ueq.free_symbols - var_set - set(doms.keys())
            if ext_in_ueq:
                # Guard against parameter-dependent leading coeff or content being divided away by solveset
                try:
                    upoly = sp.Poly(ueq, chosen_var)
                    lc_u = upoly.LC()
                    if (lc_u.free_symbols & ext_in_ueq) and not _is_proven_nonzero_expr(lc_u, doms):
                        return (
                            "unresolved",
                            [],
                            f"Hệ số bậc cao nhất {lc_u} của {ueq} = 0 phụ thuộc tham số chưa loại trừ khả năng triệt tiêu.",
                        )
                except Exception:
                    pass
                try:
                    cont_u, _ = sp.factor_list(ueq, chosen_var)
                    if (cont_u.free_symbols & ext_in_ueq) and not _is_proven_nonzero_expr(cont_u, doms):
                        return (
                            "unresolved",
                            [],
                            f"Nhân tử tham số {cont_u} của {ueq} = 0 có thể triệt tiêu trên miền thực.",
                        )
                except Exception:
                    pass

        solsets: list[sp.Set] = []
        for ueq in chosen_eqs:
            try:
                solsets.append(sp.solveset(ueq, chosen_var, domain=u_dom))
            except Exception as exc:
                return ("unresolved", [], f"Không thể giải điều kiện một ẩn cho {chosen_var}: {exc}")

        full_set = solsets[0] if len(solsets) == 1 else sp.Intersection(*solsets)
        dec_out, dec_items, dec_msg = _decompose_univariate_set(chosen_var, full_set)
        if dec_out == "empty":
            return ("empty", [], dec_msg)
        if dec_out == "unresolved":
            return ("unresolved", [], dec_msg)

        rem_eqs = [eq for eq in norm_eqs if eq not in chosen_eqs]
        rem_vars = [v for v in active_vars if v != chosen_var]
        all_branches: list[_ConstraintBranch] = []

        for val_expr, extra_doms in dec_items:
            ext_in_val = val_expr.free_symbols - set(extra_doms.keys())
            if ext_in_val and not _is_valid_real_limit_expr(val_expr, extra_doms, ext_in_val):
                return (
                    "unresolved",
                    [],
                    f"Nghiệm {chosen_var} = {val_expr} không chứng minh được tính xác định thực hữu hạn trên toàn miền tham số.",
                )
            sub_rem_eqs = []
            den_failed = False
            for req in rem_eqs:
                try:
                    sub_req = req.subs(chosen_var, val_expr)
                    sub_rem_eqs.append(sub_req)
                except Exception:
                    return ("unresolved", [], f"Lỗi khi thay giá trị {chosen_var} = {val_expr} vào hệ phương trình.")
            den_out, checked_extra, den_msg = _check_branch_denominators(
                [val_expr] + sub_rem_eqs,
                _ConstraintBranch(assignments={chosen_var: val_expr}, param_domains=extra_doms),
            )
            if den_out == "unresolved":
                return ("unresolved", [], den_msg)
            if den_out == "empty":
                den_failed = True
            if den_failed:
                continue

            sub_extra_doms = checked_extra.param_domains
            extra_vars_in_rem = [p for p in sub_extra_doms if any(p in eq.free_symbols for eq in sub_rem_eqs)]
            next_vars = rem_vars + extra_vars_in_rem
            next_doms = {v: doms[v] for v in rem_vars}
            next_doms.update(sub_extra_doms)

            sub_out, sub_branches, sub_msg = _solve_real_constraint_system(
                sub_rem_eqs,
                next_vars,
                var_domains=next_doms,
                _depth=_depth + 1,
                _allow_groebner=_allow_groebner,
            )
            if sub_out == "unresolved":
                return ("unresolved", [], sub_msg)
            if sub_out == "empty":
                continue
            for sb in sub_branches:
                final_val = sp.simplify(val_expr.subs(sb.assignments)) if sb.assignments else val_expr
                merged_assigns = {chosen_var: final_val}
                for rv in rem_vars:
                    if rv in sb.assignments:
                        merged_assigns[rv] = sb.assignments[rv]
                merged_doms = {}
                used_p = set()
                for val in merged_assigns.values():
                    used_p |= val.free_symbols
                for p, pd in sub_extra_doms.items():
                    if p not in sb.assignments and p in used_p:
                        merged_doms[p] = pd
                for p, pd in sb.param_domains.items():
                    if p in used_p:
                        merged_doms[p] = pd
                all_branches.append(_ConstraintBranch(assignments=merged_assigns, param_domains=merged_doms))

        if not all_branches:
            return ("empty", [], f"Không tồn tại nghiệm thực thỏa mãn hệ phương trình {norm_eqs}.")
        return ("resolved", _with_untouched(all_branches), "")

    # Strategy 2: Purely linear system over Reals via sp.linsolve
    all_reals = all(doms[v] == sp.S.Reals for v in active_vars)
    if all_reals:
        is_pure_linear = True
        for eq in norm_eqs:
            if eq.has(AppliedUndef, sp.Integral, sp.Limit):
                is_pure_linear = False
                break
            non_vars = eq.free_symbols - set(active_vars)
            if any(sym.is_real is not True for sym in non_vars):
                is_pure_linear = False
                break
            try:
                poly = sp.Poly(eq, *active_vars)
                if poly.total_degree() != 1:
                    is_pure_linear = False
                    break
            except Exception:
                is_pure_linear = False
                break

        if is_pure_linear:
            # Deduplicate identical equations up to sign before matrix rank inspection
            unique_eqs: list[sp.Expr] = []
            seen_keys: set[str] = set()
            for eq in norm_eqs:
                exp_eq = sp.expand(eq)
                k_pos = str(exp_eq)
                k_neg = str(sp.expand(-exp_eq))
                if k_pos not in seen_keys and k_neg not in seen_keys:
                    seen_keys.add(k_pos)
                    unique_eqs.append(eq)

            try:
                mat_a, vec_b = sp.linear_eq_to_matrix(unique_eqs, active_vars)
                ext_syms = (mat_a.free_symbols | vec_b.free_symbols) - set(active_vars)
                lin_sol = sp.linsolve(unique_eqs, active_vars)
            except Exception as exc:
                return (
                    "unresolved",
                    [],
                    f"Không thể phân giải hệ phương trình tuyến tính {unique_eqs}: {exc}",
                )

            if lin_sol == sp.S.EmptySet:
                if not ext_syms:
                    return ("empty", [], f"Hệ phương trình tuyến tính {unique_eqs} vô nghiệm thực.")
                const_rows = [eq for eq in unique_eqs if not (eq.free_symbols & ext_syms)]
                if const_rows:
                    try:
                        if sp.linsolve(const_rows, active_vars) == sp.S.EmptySet:
                            return ("empty", [], f"Hệ phương trình tuyến tính {unique_eqs} vô nghiệm thực.")
                    except Exception:
                        pass
                return (
                    "unresolved",
                    [],
                    f"Tính tương thích của hệ tuyến tính phụ thuộc tham số ngoài {sorted(ext_syms, key=lambda s: s.name)}; "
                    f"không thể khẳng định vô nghiệm trên toàn miền thực.",
                )

            if isinstance(lin_sol, sp.FiniteSet) and len(lin_sol) == 1:
                tup = next(iter(lin_sol))
                if any(item.has(sp.I, sp.zoo, sp.nan, sp.oo, -sp.oo) for item in tup):
                    return ("unresolved", [], f"Nghiệm hệ tuyến tính chứa thành phần không thực hoặc không hữu hạn: {tup}.")

                if ext_syms:
                    # Guard against parameter-dependent rank drops, minor degeneracies, and division by parameters
                    if mat_a.rank() < mat_a.rows:
                        return (
                            "unresolved",
                            [],
                            f"Hạng ma trận hệ số của hệ tuyến tính phụ thuộc tham số {sorted(ext_syms, key=lambda s: s.name)} "
                            f"(không thể bảo đảm tính đầy đủ trên toàn miền thực).",
                        )
                    if (mat_a.free_symbols & ext_syms) and not _has_proven_nonzero_full_row_minor(mat_a, doms):
                        return (
                            "unresolved",
                            [],
                            f"Định thức/định thức con của ma trận hệ số phụ thuộc tham số {sorted(mat_a.free_symbols & ext_syms, key=lambda s: s.name)} "
                            f"không chứng minh được khác 0 trên toàn miền thực; tồn tại giá trị tham số suy biến hạng.",
                        )
                    for item in tup:
                        for den in _factor_denominator_terms(item):
                            try:
                                _, d_factors = sp.factor_list(den)
                                fac_list = [f for f, _ in d_factors]
                            except Exception:
                                fac_list = [den]
                            for fac in fac_list:
                                if (fac.free_symbols & ext_syms) and not _is_proven_nonzero_expr(fac, doms):
                                    return (
                                        "unresolved",
                                        [],
                                        f"Biểu thức nghiệm tuyến tính chứa mẫu số phụ thuộc tham số ({fac}) chưa chứng minh được khác 0.",
                                    )
                        if not _is_valid_real_limit_expr(item, doms, ext_syms):
                            return (
                                "unresolved",
                                [],
                                f"Thành phần nghiệm {item} chưa chứng minh được tính thực hữu hạn trên toàn miền tham số.",
                            )

                # Bind free variables in tup to explicit real Dummy parameters
                param_rebind: dict[sp.Symbol, sp.Symbol] = {}
                param_doms: dict[sp.Symbol, sp.Set] = {}
                for idx, v in enumerate(active_vars):
                    if tup[idx] == v:
                        tau = sp.Dummy(v.name, real=True)
                        param_rebind[v] = tau
                        param_doms[tau] = sp.S.Reals
                # Check all remaining free variables among active_vars
                for item in tup:
                    for sym in item.free_symbols & set(active_vars):
                        if sym not in param_rebind:
                            tau = sp.Dummy(sym.name, real=True)
                            param_rebind[sym] = tau
                            param_doms[tau] = sp.S.Reals
                assigns = {
                    v: (tup[idx].subs(param_rebind) if param_rebind else tup[idx])
                    for idx, v in enumerate(active_vars)
                }
                br = _ConstraintBranch(assignments=assigns, param_domains=param_doms)
                ok_eq, unc_eq = _verify_branch_satisfies_equations(br, unique_eqs)
                if ok_eq and not unc_eq:
                    return ("resolved", _with_untouched([br]), "")

            return (
                "unresolved",
                [],
                f"Không thể xác lập tập nghiệm thực đầy đủ cho hệ tuyến tính {unique_eqs}.",
            )

    # Strategy 3: Exact polynomial factor splitting (A * B = 0)
    for idx, eq in enumerate(norm_eqs):
        try:
            poly_chk = sp.Poly(eq, *active_vars)
        except Exception:
            poly_chk = None
        if poly_chk is not None:
            try:
                cont, factors = sp.factor_list(eq)
                ext_in_cont = cont.free_symbols - var_set - set(doms.keys())
                if ext_in_cont and not _is_proven_nonzero_expr(cont, doms):
                    return (
                        "unresolved",
                        [],
                        f"Nhân tử tham số {cont} của {eq} = 0 chưa chứng minh được khác 0 trên toàn miền thực.",
                    )
                var_factors = [fac for fac, _ in factors if fac.free_symbols & set(active_vars)]
                if len(var_factors) >= 2:
                    rest_eqs = norm_eqs[:idx] + norm_eqs[idx + 1 :]
                    fact_branches: list[_ConstraintBranch] = []
                    for fac in var_factors:
                        sub_out, sub_branches, sub_msg = _solve_real_constraint_system(
                            [fac] + rest_eqs,
                            active_vars,
                            var_domains={v: doms[v] for v in active_vars},
                            _depth=_depth + 1,
                            _allow_groebner=_allow_groebner,
                        )
                        if sub_out == "unresolved":
                            return ("unresolved", [], sub_msg)
                        if sub_out == "resolved":
                            fact_branches.extend(sub_branches)
                    if not fact_branches:
                        return ("empty", [], f"Mọi nhân tử của {eq} = 0 đều vô nghiệm thực.")
                    return ("resolved", _with_untouched(fact_branches), "")
            except Exception:
                pass

    # Strategy 4: Linear isolation of a variable with constant nonzero coefficient
    for idx, eq in enumerate(norm_eqs):
        for v in active_vars:
            if doms[v] != sp.S.Reals or v not in eq.free_symbols:
                continue
            try:
                coeff = sp.simplify(sp.diff(eq, v))
            except Exception:
                continue
            if coeff.free_symbols & set(active_vars):
                continue
            coeff_assumed = _apply_real_assumptions(coeff, doms)
            if not (coeff_assumed.is_real is True and coeff_assumed.is_finite is True and coeff_assumed.is_nonzero is True):
                continue
            try:
                rem = sp.simplify(eq - coeff * v)
            except Exception:
                continue
            if v in rem.free_symbols:
                continue
            rem_assumed = _apply_real_assumptions(rem, doms, set(active_vars))
            if not _is_valid_real_limit_expr(rem_assumed, doms, set(active_vars)):
                continue
            isolated = sp.simplify(-rem / coeff)
            rest_eqs = [r.subs(v, isolated) for r in (norm_eqs[:idx] + norm_eqs[idx + 1 :])]
            rem_vars = [rv for rv in active_vars if rv != v]
            sub_out, sub_branches, sub_msg = _solve_real_constraint_system(
                rest_eqs,
                rem_vars,
                var_domains={rv: doms[rv] for rv in rem_vars},
                _depth=_depth + 1,
                _allow_groebner=_allow_groebner,
            )
            if sub_out == "unresolved":
                return ("unresolved", [], sub_msg)
            if sub_out == "empty":
                return ("empty", [], sub_msg)
            iso_branches: list[_ConstraintBranch] = []
            for sb in sub_branches:
                new_assigns = dict(sb.assignments)
                new_doms = dict(sb.param_domains)
                val_v = sp.simplify(isolated.subs(new_assigns))
                for rv in list(val_v.free_symbols & set(rem_vars)):
                    if rv not in new_assigns:
                        tau = sp.Dummy(rv.name, real=True)
                        new_assigns[rv] = tau
                        new_doms[tau] = doms[rv]
                val_v = sp.simplify(isolated.subs(new_assigns))
                new_assigns[v] = val_v
                iso_branches.append(_ConstraintBranch(assignments=new_assigns, param_domains=new_doms))
            return ("resolved", _with_untouched(iso_branches), "")

    # Strategy 5: Coupled multivariate polynomial elimination via Gröbner basis
    if _allow_groebner and all_reals and 2 <= len(active_vars) <= 4:
        is_pure_poly = True
        has_inexact_float = False
        for eq in norm_eqs:
            if eq.has(sp.Float):
                has_inexact_float = True
            non_vars = eq.free_symbols - set(active_vars)
            if non_vars:
                is_pure_poly = False
                break
            try:
                sp.Poly(eq, *active_vars)
            except Exception:
                is_pure_poly = False
                break

        if is_pure_poly and not has_inexact_float:
            try:
                groeb = sp.groebner(norm_eqs, *active_vars, order="lex")
                g_polys = list(groeb)
                if g_polys == [1]:
                    return ("empty", [], f"Hệ đa thức {norm_eqs} vô nghiệm theo cơ sở Gröbner.")
                has_univar = any(len(gp.free_symbols & set(active_vars)) == 1 for gp in g_polys)
                if has_univar:
                    sub_out, sub_branches, sub_msg = _solve_real_constraint_system(
                        g_polys,
                        active_vars,
                        var_domains={v: doms[v] for v in active_vars},
                        _depth=_depth + 1,
                        _allow_groebner=False,
                    )
                    if sub_out == "empty":
                        return ("empty", [], sub_msg)
                    if sub_out == "unresolved":
                        return ("unresolved", [], sub_msg)
                    verified_branches = []
                    for sb in sub_branches:
                        ok_eq, unc_eq = _verify_branch_satisfies_equations(sb, norm_eqs)
                        if unc_eq:
                            return ("unresolved", [], "Không thể kiểm chứng hoàn toàn nghiệm đa thức.")
                        if ok_eq:
                            verified_branches.append(sb)
                    if not verified_branches:
                        return ("empty", [], f"Không có nghiệm thực nào thỏa mãn hệ đa thức {norm_eqs}.")
                    return ("resolved", _with_untouched(verified_branches), "")
            except Exception:
                pass

    return (
        "unresolved",
        [],
        f"Không thể xác lập tập nghiệm thực đầy đủ và khép kín cho hệ phương trình {norm_eqs} đối với {active_vars}.",
    )


def _format_single_branch_constraint(br: _ConstraintBranch) -> str:
    """Format a single constraint branch with human-readable parameter names."""
    rename_map: dict[sp.Symbol, sp.Symbol] = {}
    used_names: set[str] = set()
    dom_notes: list[str] = []

    # Check if a parameter represents one of the constants identically (e.g. C2 = _tau)
    for c in sorted(br.assignments.keys(), key=lambda s: s.name):
        if br.assignments[c] in br.param_domains and br.assignments[c] not in rename_map:
            p = br.assignments[c]
            if c.name not in used_names:
                clean_sym = sp.Symbol(c.name, real=True)
                rename_map[p] = clean_sym
                used_names.add(c.name)
                dom_notes.append(f"{clean_sym} in {br.param_domains[p]}")

    int_idx = 0
    real_idx = 0
    for p in sorted(br.param_domains.keys(), key=lambda s: s.name):
        if p in rename_map:
            continue
        dom = br.param_domains[p]
        if dom.is_subset(sp.S.Integers) is True:
            int_idx += 1
            base_name = "k" if int_idx == 1 else f"k{int_idx}"
            while base_name in used_names:
                int_idx += 1
                base_name = f"k{int_idx}"
            clean_sym = sp.Symbol(base_name, integer=True)
        else:
            real_idx += 1
            base_name = "t_param" if real_idx == 1 else f"t_param{real_idx}"
            while base_name in used_names:
                real_idx += 1
                base_name = f"t_param{real_idx}"
            clean_sym = sp.Symbol(base_name, real=True)
        rename_map[p] = clean_sym
        used_names.add(base_name)
        dom_notes.append(f"{clean_sym} in {dom}")

    assign_parts = []
    for c in sorted(br.assignments.keys(), key=lambda s: s.name):
        val = br.assignments[c].subs(rename_map) if rename_map else br.assignments[c]
        if isinstance(val, sp.Symbol) and val.name == c.name and br.assignments[c] in br.param_domains:
            continue
        assign_parts.append(f"{c} = {val}")

    base_str = ", ".join(assign_parts)
    if base_str and dom_notes:
        return f"{base_str} ({', '.join(dom_notes)})"
    if dom_notes:
        return ", ".join(dom_notes)
    return base_str


def _format_branches_summary(branches: list[_ConstraintBranch]) -> str:
    """Format a list of complete constraint branches, coalescing single-constant sets cleanly."""
    if not branches:
        return ""

    # If all branches constrain only a single common constant, inspect combined set structure
    first_keys = set(branches[0].assignments.keys())
    if len(first_keys) == 1 and all(set(br.assignments.keys()) == first_keys for br in branches):
        c = next(iter(first_keys))
        has_infinite = any(br.param_domains for br in branches)
        if not has_infinite:
            discrete_vals: list[sp.Expr] = []
            for br in branches:
                val = br.assignments[c]
                if not any(_prove_symbolic_zero(sp.simplify(val - prev)) for prev in discrete_vals):
                    discrete_vals.append(val)

            def _sort_key(v: sp.Expr) -> tuple[int, float, str]:
                try:
                    return (0, float(sp.N(v)), str(v))
                except Exception:
                    return (1, 0.0, str(v))

            discrete_vals.sort(key=_sort_key)
            return " hoặc ".join(f"{c} = {val}" for val in discrete_vals)

        # Infinite / parameterized single-constant family: reconstruct Set Union
        set_parts: list[sp.Set] = []
        all_convert_ok = True
        for br in branches:
            if not br.param_domains:
                set_parts.append(sp.FiniteSet(br.assignments[c]))
            elif len(br.param_domains) == 1:
                p, dom = next(iter(br.param_domains.items()))
                is_int = dom.is_subset(sp.S.Integers) is True
                k_sym = sp.Symbol("k" if is_int else "tau", integer=is_int, real=True)
                set_parts.append(sp.ImageSet(sp.Lambda(k_sym, br.assignments[c].subs(p, k_sym)), dom))
            else:
                all_convert_ok = False
                break

        if all_convert_ok and set_parts:
            full_set = set_parts[0] if len(set_parts) == 1 else sp.Union(*set_parts)
            s_full = str(full_set)
            if isinstance(full_set, (sp.ImageSet, sp.Union)) and "pi" in s_full:
                if ("2*pi*k + pi" in s_full and "2*pi*k)" in s_full) or ("2*k*pi + pi" in s_full and "2*k*pi)" in s_full):
                    return f"{c} = k*pi, k in Integers ({full_set})"
            return f"{c} in {full_set}"

    # General multi-constant or mixed branches: deduplicate cleanly
    formatted_parts: list[str] = []
    for br in branches:
        s_str = _format_single_branch_constraint(br)
        if s_str and s_str not in formatted_parts:
            formatted_parts.append(s_str)
    return " hoặc ".join(formatted_parts)


def _derive_pole_cancellation_equations(
    expr: sp.Expr,
    var: sp.Symbol,
    point: sp.Expr,
    direction: str,
    consts: set[sp.Symbol],
) -> tuple[str, list[sp.Expr], sp.Expr | None, str]:
    """Check one-sided finiteness and extract pole-cancellation equations if divergent.

    Returns:
        (outcome, equations, lim_or_none, message)
        outcome:
            - 'finite': expression already has a finite real limit without pole constraints
            - 'equations': pole-cancellation equations extracted for constants
            - 'failed': pole proved uncancellable (no constants or proven constant-free pole)
            - 'unresolved': limit or pole condition could not be resolved reliably
    """
    try:
        lim = sp.limit(expr, var, point, dir=direction)
    except Exception as exc:
        return ("unresolved", [], None, f"Không thể tính giới hạn một phía ({direction}) tại {point}: {exc}")

    if lim.has(sp.Limit, sp.AccumBounds, AppliedUndef):
        return ("unresolved", [], lim, f"Giới hạn một phía chưa thể tính được biểu thức giải tích hội tụ: {lim}")

    if not lim.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        if not _is_valid_real_limit_expr(lim, {}, consts):
            return (
                "unresolved",
                [],
                lim,
                f"Giới hạn một phía {lim} chưa chứng minh được tính thực hữu hạn trên toàn miền.",
            )
        return ("finite", [], lim, "")

    if not consts:
        if lim.has(sp.nan):
            return ("unresolved", [], lim, f"Giới hạn một phía bất định {lim}.")
        return ("failed", [], lim, f"Giới hạn một phía không hữu hạn và không có hằng số tích phân để triệt tiêu: {lim}")

    equations: list[sp.Expr] = []
    has_const_free_div = False

    # 1. Series expansion Laurent terms
    try:
        h = sp.Symbol("_h", positive=True)
        t_sub = point - h if direction == "-" else point + h
        expr_h = expr.subs(var, t_sub)
        s = expr_h.series(h, 0, n=1).removeO()
        const_free_terms = []
        const_dep_orders = set()
        for term in s.as_ordered_terms():
            lim_term = sp.limit(term, h, 0, dir="+")
            if lim_term.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
                c_h, exp_h = term.as_coeff_exponent(h)
                if h in c_h.free_symbols:
                    c_indep, h_part = c_h.as_independent(h, as_Add=False)
                    if h not in c_indep.free_symbols:
                        c_h = c_indep
                        exp_h = (exp_h, h_part)
                    else:
                        continue
                if any(c in c_h.free_symbols for c in consts):
                    equations.append(c_h)
                    const_dep_orders.add(exp_h)
                else:
                    const_free_terms.append((c_h, exp_h))
        # A constant-free divergent term of order not shared with any constant-dependent term is uncancellable
        if const_free_terms and not equations and all(ord_h not in const_dep_orders for _, ord_h in const_free_terms):
            has_const_free_div = True
    except Exception:
        pass

    # 2. Extract arguments of sign() in limit
    if lim.has(sp.sign):
        for s_node in lim.atoms(sp.sign):
            if any(c in s_node.args[0].free_symbols for c in consts) and _h_free(s_node.args[0], var):
                equations.append(s_node.args[0])

    # 3. Denominator vanishing in rational form
    try:
        num, den = sp.together(expr).as_numer_denom()
        if _prove_symbolic_zero(den.subs(var, point)) or den.subs(var, point) == 0:
            num_at_pt = num.subs(var, point)
            if any(c in num_at_pt.free_symbols for c in consts):
                equations.append(num_at_pt)
            elif not equations and num_at_pt != 0 and _apply_real_assumptions(num_at_pt, {}, consts).is_nonzero is True:
                has_const_free_div = True
    except Exception:
        pass

    if not equations:
        if has_const_free_div and not lim.has(sp.nan):
            return (
                "failed",
                [],
                lim,
                f"Giới hạn một phía chứa cực điểm không phụ thuộc hằng số tích phân nên không thể triệt tiêu: {lim}.",
            )
        return (
            "unresolved",
            [],
            lim,
            f"Giới hạn một phía không hữu hạn ({lim}) và chưa thể trích xuất đầy đủ điều kiện khử cực điểm.",
        )

    return ("equations", equations, lim, "")


def _h_free(expr: sp.Expr, var: sp.Symbol) -> bool:
    return var not in expr.free_symbols and all(s.name != "_h" for s in expr.free_symbols)


def _derive_pole_cancellation_constraints(
    expr: sp.Expr,
    var: sp.Symbol,
    point: sp.Expr,
    direction: str,
    consts: set[sp.Symbol],
) -> tuple[str, list[tuple[dict[sp.Symbol, Any], sp.Expr]], str]:
    """Derive complete real constraints on integration constants to cancel poles at a singular point."""
    out, equations, lim, msg = _derive_pole_cancellation_equations(expr, var, point, direction, consts)
    if out == "unresolved":
        return ("unresolved", [], msg)
    if out == "failed":
        return ("failed", [], msg)
    if out == "finite":
        return ("finite", [({}, lim)], "")

    sys_out, branches, sys_msg = _solve_real_constraint_system(equations, sorted(consts, key=lambda s: s.name))
    if sys_out == "empty":
        return ("failed", [], sys_msg)
    if sys_out == "unresolved" or not branches:
        return ("unresolved", [], sys_msg or "Không thể thiết lập tập nghiệm thực đầy đủ khử cực điểm.")

    valid_sols: list[tuple[dict[sp.Symbol, Any], sp.Expr]] = []
    has_unresolved_lim = False
    unresolved_lim_msg = ""

    for br in branches:
        sub_expr = expr.subs(br.assignments)
        rem_c_p = consts - set(br.assignments.keys())
        den_out, checked_br, den_msg = _check_branch_denominators([sub_expr], br, var=var, free_consts=rem_c_p)
        if den_out == "unresolved":
            has_unresolved_lim = True
            unresolved_lim_msg = den_msg
            continue
        if den_out == "empty":
            continue
        try:
            sub_lim = sp.limit(sub_expr, var, point, dir=direction)
        except Exception as exc:
            has_unresolved_lim = True
            unresolved_lim_msg = f"Không thể tính giới hạn trên nhánh nghiệm {checked_br.assignments}: {exc}"
            continue
        if sub_lim.has(sp.Limit, sp.AccumBounds, AppliedUndef):
            has_unresolved_lim = True
            unresolved_lim_msg = f"Giới hạn trên nhánh nghiệm {checked_br.assignments} chưa giải được: {sub_lim}"
            continue
        if sub_lim.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
            if checked_br.param_domains or (sub_lim.free_symbols & consts):
                has_unresolved_lim = True
                unresolved_lim_msg = f"Chưa chứng minh được khử cực điểm trên toàn bộ họ tham số: {sub_lim}"
            continue
        rem_c = consts - set(checked_br.assignments.keys())
        if not _is_valid_real_limit_expr(sub_lim, checked_br.param_domains, rem_c):
            has_unresolved_lim = True
            unresolved_lim_msg = f"Giới hạn {sub_lim} không xác định thực hữu hạn."
            continue
        valid_sols.append((dict(checked_br.assignments), sub_lim))

    if has_unresolved_lim:
        return ("unresolved", [], unresolved_lim_msg)
    if not valid_sols:
        return ("failed", [], "Không có nghiệm thực nào của phương trình khử cực điểm dẫn đến giới hạn hữu hạn.")
    return ("resolved", valid_sols, "")


def verify_singular_extension(
    branch_left: Any | None,
    branch_right: Any | None,
    singular_point: sp.Expr,
    value_at_point: sp.Expr | None = None,
    deriv_at_point: sp.Expr | None = None,
    variable: sp.Symbol = sp.Symbol("t"),
) -> tuple[VerificationStatus, str]:
    """Verify continuity and C1 differentiability across a singular point separating two branches.

    Checks:
    - lim_{t -> ts^-} y1(t) and lim_{t -> ts^+} y2(t) against value_at_point (or against each other if value_at_point is None)
    - lim_{t -> ts^-} y1'(t) and lim_{t -> ts^+} y2'(t) against deriv_at_point (or against each other if deriv_at_point is None)
    - Supports free integration constants: solves compatibility equations when possible without arbitrary zero assignments.
    - Detects explicit limit conflicts (jump discontinuity) and returns FAILED.
    - Returns UNVERIFIED if unevaluated integrals or limits prevent conclusive resolution.
    - Distinguishes unrestricted C1, conditional C1 (CONDITIONAL_EXTENSION), and continuous but not C1 (CONTINUITY_VERIFIED).
    """
    if branch_left is None or branch_right is None:
        return (
            VerificationStatus.UNVERIFIED,
            f"Điểm kỳ dị {singular_point} không nằm giữa hai nhánh nghiệm liên tiếp.",
        )

    # Re-bind variable to matching symbol in expressions if names match to prevent real=True vs None symbol mismatch
    for s in (branch_left.expression.free_symbols | branch_right.expression.free_symbols):
        if s.name == variable.name:
            variable = s
            break

    # If expressions contain unevaluated integrals, limits cannot be evaluated by SymPy
    if branch_left.expression.has(sp.Integral) or branch_right.expression.has(sp.Integral):
        return (
            VerificationStatus.UNVERIFIED,
            f"Nghiệm tại các nhánh lân cận chứa tích phân chưa tính được nguyên hàm sơ cấp; "
            f"giới hạn một phía tại điểm kỳ dị {singular_point} chưa thể kiểm chứng ký hiệu.",
        )

    # Identify all free integration constants in both branches
    consts_left = _extract_integration_constants(branch_left.expression, variable)
    if isinstance(branch_left.integration_constant, sp.Symbol):
        consts_left.add(branch_left.integration_constant)
    consts_right = _extract_integration_constants(branch_right.expression, variable)
    if isinstance(branch_right.integration_constant, sp.Symbol):
        consts_right.add(branch_right.integration_constant)
    all_consts = consts_left | consts_right

    # Stage 0: Pole cancellation without representative sampling
    outcome_l, eqs_l, _, msg_l = _derive_pole_cancellation_equations(
        branch_left.expression, variable, singular_point, "-", consts_left
    )
    if outcome_l == "unresolved":
        return (VerificationStatus.UNVERIFIED, msg_l)
    if outcome_l == "failed":
        return (VerificationStatus.FAILED, msg_l)

    outcome_r, eqs_r, _, msg_r = _derive_pole_cancellation_equations(
        branch_right.expression, variable, singular_point, "+", consts_right
    )
    if outcome_r == "unresolved":
        return (VerificationStatus.UNVERIFIED, msg_r)
    if outcome_r == "failed":
        return (VerificationStatus.FAILED, msg_r)

    pole_eqs = eqs_l + eqs_r
    if pole_eqs:
        sys_out, raw_pole_branches, sys_msg = _solve_real_constraint_system(
            pole_eqs, sorted(all_consts, key=lambda s: s.name)
        )
        if sys_out == "empty":
            return (VerificationStatus.FAILED, sys_msg)
        if sys_out == "unresolved" or not raw_pole_branches:
            return (
                VerificationStatus.UNVERIFIED,
                sys_msg or f"Không thể xác lập tập nghiệm thực đầy đủ khử cực điểm tại {singular_point}.",
            )
    else:
        raw_pole_branches = [_ConstraintBranch(assignments={}, param_domains={})]

    # Universally verify left & right limits across EVERY member of every pole branch (never via samples)
    pole_branches: list[_ConstraintBranch] = []
    has_unresolved_pole = False
    unresolved_pole_msg = ""

    for br in raw_pole_branches:
        sub_l = _simplify_limit_expr(branch_left.expression.subs(br.assignments))
        sub_r = _simplify_limit_expr(branch_right.expression.subs(br.assignments))
        rem_consts_p = all_consts - set(br.assignments.keys())
        den_out, checked_br, den_msg = _check_branch_denominators([sub_l, sub_r], br, var=variable, free_consts=rem_consts_p)
        if den_out == "unresolved":
            has_unresolved_pole = True
            unresolved_pole_msg = den_msg
            continue
        if den_out == "empty":
            continue
        try:
            lim_l = sp.limit(sub_l, variable, singular_point, dir="-")
            lim_r = sp.limit(sub_r, variable, singular_point, dir="+")
        except Exception as exc:
            has_unresolved_pole = True
            unresolved_pole_msg = f"Không thể tính giới hạn một phía trên nhánh nghiệm tại {singular_point}: {exc}"
            continue
        if lim_l.has(sp.Limit, sp.AccumBounds, AppliedUndef) or lim_r.has(sp.Limit, sp.AccumBounds, AppliedUndef):
            has_unresolved_pole = True
            unresolved_pole_msg = (
                f"Giới hạn một phía trên nhánh nghiệm tại điểm kỳ dị {singular_point} chưa giải được: "
                f"lim- = {lim_l}, lim+ = {lim_r}."
            )
            continue
        if lim_l.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or lim_r.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
            if checked_br.param_domains or (
                (lim_l.free_symbols | lim_r.free_symbols) & all_consts
            ) or lim_l.has(sp.nan) or lim_r.has(sp.nan):
                has_unresolved_pole = True
                unresolved_pole_msg = (
                    f"Chưa chứng minh được khử cực điểm trên toàn bộ họ tham số tại {singular_point}: "
                    f"lim- = {lim_l}, lim+ = {lim_r}."
                )
            continue
        if not _is_valid_real_limit_expr(lim_l, checked_br.param_domains, rem_consts_p) or not _is_valid_real_limit_expr(
            lim_r, checked_br.param_domains, rem_consts_p
        ):
            has_unresolved_pole = True
            unresolved_pole_msg = f"Giới hạn một phía không chứng minh được tính thực hữu hạn: lim- = {lim_l}, lim+ = {lim_r}."
            continue
        pole_branches.append(checked_br)

    if has_unresolved_pole:
        return (VerificationStatus.UNVERIFIED, unresolved_pole_msg)

    if not pole_branches:
        return (
            VerificationStatus.FAILED,
            f"Các điều kiện khử cực điểm ở hai nhánh mâu thuẫn nhau tại điểm kỳ dị {singular_point}.",
        )

    # Stage 1: Value compatibility / continuity over the complete parameter set
    val_branches: list[_ConstraintBranch] = []
    has_unresolved_val = False
    unresolved_val_msg = ""

    for br in pole_branches:
        rem_consts = all_consts - set(br.assignments.keys())
        sub_l = _simplify_limit_expr(branch_left.expression.subs(br.assignments))
        sub_r = _simplify_limit_expr(branch_right.expression.subs(br.assignments))
        try:
            curr_lim_l = sp.limit(sub_l, variable, singular_point, dir="-")
            curr_lim_r = sp.limit(sub_r, variable, singular_point, dir="+")
        except Exception as exc:
            has_unresolved_val = True
            unresolved_val_msg = f"Không thể tính giới hạn một phía tại điểm kỳ dị {singular_point}: {exc}"
            continue

        if curr_lim_l.has(sp.Limit, sp.AccumBounds, AppliedUndef) or curr_lim_r.has(sp.Limit, sp.AccumBounds, AppliedUndef):
            has_unresolved_val = True
            unresolved_val_msg = (
                f"Giới hạn một phía tại điểm kỳ dị {singular_point} chưa thể tính được biểu thức giải tích: "
                f"lim- = {curr_lim_l}, lim+ = {curr_lim_r}."
            )
            continue

        if curr_lim_l.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or curr_lim_r.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
            if br.param_domains or rem_consts or curr_lim_l.has(sp.nan) or curr_lim_r.has(sp.nan):
                has_unresolved_val = True
                unresolved_val_msg = f"Giới hạn một phía tại điểm kỳ dị {singular_point} không xác định: lim- = {curr_lim_l}, lim+ = {curr_lim_r}."
            continue

        if not _is_valid_real_limit_expr(curr_lim_l, br.param_domains, rem_consts) or not _is_valid_real_limit_expr(
            curr_lim_r, br.param_domains, rem_consts
        ):
            has_unresolved_val = True
            unresolved_val_msg = f"Giới hạn một phía tại điểm kỳ dị {singular_point} chưa xác định thực hữu hạn."
            continue

        if value_at_point is not None:
            raw_val_eqs = [sp.Eq(curr_lim_l, value_at_point, evaluate=False), sp.Eq(curr_lim_r, value_at_point, evaluate=False)]
        else:
            raw_val_eqs = [sp.Eq(curr_lim_l, curr_lim_r, evaluate=False)]

        active_doms = {p: dom for p, dom in br.param_domains.items()}
        for c in rem_consts:
            active_doms[c] = sp.S.Reals

        active_v_vars = [p for p in br.param_domains if any(p in eq.free_symbols for eq in raw_val_eqs)] + [
            c for c in sorted(rem_consts, key=lambda s: s.name) if any(c in eq.free_symbols for eq in raw_val_eqs)
        ]

        # Check constant-only value mismatches quickly for crisp user-facing diagnostics
        if not active_v_vars:
            if value_at_point is not None:
                diff_l = sp.simplify(_apply_real_assumptions(curr_lim_l - value_at_point, br.param_domains, rem_consts))
                diff_r = sp.simplify(_apply_real_assumptions(curr_lim_r - value_at_point, br.param_domains, rem_consts))
                l_ok = _prove_symbolic_zero(diff_l)
                r_ok = _prove_symbolic_zero(diff_r)
                if not l_ok:
                    if diff_l.is_nonzero is True or diff_l.is_number:
                        if len(pole_branches) == 1 and not br.param_domains and not rem_consts:
                            return (
                                VerificationStatus.FAILED,
                                f"Giới hạn bên trái lim- = {curr_lim_l} không trùng khớp với giá trị tại điểm kỳ dị y({singular_point}) = {value_at_point}.",
                            )
                        continue
                    has_unresolved_val = True
                    unresolved_val_msg = f"Chưa thể kiểm chứng đẳng thức giới hạn trái {curr_lim_l} = {value_at_point}."
                    continue
                if not r_ok:
                    if diff_r.is_nonzero is True or diff_r.is_number:
                        if len(pole_branches) == 1 and not br.param_domains and not rem_consts:
                            return (
                                VerificationStatus.FAILED,
                                f"Giới hạn bên phải lim+ = {curr_lim_r} không trùng khớp với giá trị tại điểm kỳ dị y({singular_point}) = {value_at_point}.",
                            )
                        continue
                    has_unresolved_val = True
                    unresolved_val_msg = f"Chưa thể kiểm chứng đẳng thức giới hạn phải {curr_lim_r} = {value_at_point}."
                    continue
                val_branches.append(br)
            else:
                diff_lims = sp.simplify(_apply_real_assumptions(curr_lim_l - curr_lim_r, br.param_domains, rem_consts))
                if not _prove_symbolic_zero(diff_lims):
                    if diff_lims.is_nonzero is True or diff_lims.is_number:
                        if len(pole_branches) == 1 and not br.param_domains and not rem_consts:
                            return (
                                VerificationStatus.FAILED,
                                f"Mâu thuẫn giới hạn hai phía tại điểm kỳ dị {singular_point} (bước nhảy không phụ thuộc hằng số): "
                                f"lim- = {curr_lim_l} != lim+ = {curr_lim_r}.",
                            )
                        continue
                    has_unresolved_val = True
                    unresolved_val_msg = f"Chưa thể kiểm chứng tương thích giới hạn hai phía {curr_lim_l} = {curr_lim_r}."
                    continue
                val_branches.append(br)
        else:
            sys_out, v_sub_branches, sys_msg = _solve_real_constraint_system(
                raw_val_eqs,
                active_v_vars,
                var_domains={v: active_doms[v] for v in active_v_vars},
            )
            if sys_out == "empty":
                continue
            if sys_out == "unresolved" or not v_sub_branches:
                has_unresolved_val = True
                unresolved_val_msg = sys_msg or f"Không thể giải đầy đủ phương trình tương thích giá trị tại {singular_point}."
                continue
            for sb in v_sub_branches:
                composed = _compose_branches(br, sb, rem_consts)
                sub_l_c = branch_left.expression.subs(composed.assignments)
                sub_r_c = branch_right.expression.subs(composed.assignments)
                rem_c2 = all_consts - set(composed.assignments.keys())
                den_out, checked_c, den_msg = _check_branch_denominators([sub_l_c, sub_r_c], composed, var=variable, free_consts=rem_c2)
                if den_out == "unresolved":
                    has_unresolved_val = True
                    unresolved_val_msg = den_msg
                    continue
                if den_out == "empty":
                    continue
                try:
                    c_lim_l = sp.limit(sub_l_c, variable, singular_point, dir="-")
                    c_lim_r = sp.limit(sub_r_c, variable, singular_point, dir="+")
                except Exception as exc:
                    has_unresolved_val = True
                    unresolved_val_msg = f"Không thể xác minh lại giới hạn sau ràng buộc giá trị: {exc}"
                    continue
                if not _is_valid_real_limit_expr(c_lim_l, checked_c.param_domains, rem_c2) or not _is_valid_real_limit_expr(
                    c_lim_r, checked_c.param_domains, rem_c2
                ):
                    has_unresolved_val = True
                    unresolved_val_msg = f"Giới hạn sau ràng buộc giá trị không hợp lệ: lim-={c_lim_l}, lim+={c_lim_r}"
                    continue
                val_branches.append(checked_c)

    if not val_branches:
        if has_unresolved_val:
            return (VerificationStatus.UNVERIFIED, unresolved_val_msg)
        if value_at_point is not None:
            return (
                VerificationStatus.FAILED,
                f"Không tồn tại giá trị thực của các hằng số {all_consts} để thỏa mãn giá trị tại điểm kỳ dị y({singular_point}) = {value_at_point}.",
            )
        else:
            return (
                VerificationStatus.FAILED,
                f"Mâu thuẫn giới hạn hai phía tại điểm kỳ dị {singular_point}; "
                f"không tồn tại bất kỳ phép gán hằng số thực nào để nối nghiệm liên tục.",
            )

    # Stage 2: Differentiability analysis universally across every value branch
    c1_verified_cases: list[tuple[_ConstraintBranch, str]] = []
    conditional_c1_cases: list[tuple[_ConstraintBranch, str]] = []
    continuity_verified_cases: list[tuple[_ConstraintBranch, str]] = []
    unverified_cases: list[tuple[_ConstraintBranch, str]] = []

    for val_br in val_branches:
        expr_l_sub = _simplify_limit_expr(branch_left.expression.subs(val_br.assignments))
        expr_r_sub = _simplify_limit_expr(branch_right.expression.subs(val_br.assignments))
        rem_consts = all_consts - set(val_br.assignments.keys())

        den_out_d, checked_val_br, den_msg_d = _check_branch_denominators([expr_l_sub, expr_r_sub], val_br, var=variable, free_consts=rem_consts)
        if den_out_d == "unresolved":
            unverified_cases.append((val_br, den_msg_d))
            continue
        if den_out_d == "empty":
            continue

        try:
            dy_left = _simplify_limit_expr(
                _diff_real_expr(expr_l_sub, variable, domain_interval=branch_left.domain_interval, side="-", point=singular_point)
            )
            dy_right = _simplify_limit_expr(
                _diff_real_expr(expr_r_sub, variable, domain_interval=branch_right.domain_interval, side="+", point=singular_point)
            )
            lim_dy_left = sp.limit(dy_left, variable, singular_point, dir="-")
            lim_dy_right = sp.limit(dy_right, variable, singular_point, dir="+")
        except Exception as exc:
            unverified_cases.append((
                checked_val_br,
                f"Đã kiểm chứng tính liên tục tại điểm kỳ dị {singular_point}, nhưng gặp lỗi khi kiểm chứng giới hạn đạo hàm: {exc}."
            ))
            continue

        if lim_dy_left.has(sp.Limit, sp.AccumBounds, AppliedUndef) or lim_dy_right.has(
            sp.Limit, sp.AccumBounds, AppliedUndef
        ):
            unverified_cases.append((
                checked_val_br,
                f"Đã kiểm chứng tính liên tục tại điểm kỳ dị {singular_point}, nhưng chưa thể tính biểu thức giải tích của giới hạn đạo hàm."
            ))
            continue

        if lim_dy_left.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or lim_dy_right.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
            if (
                checked_val_br.param_domains
                or rem_consts
                or lim_dy_left.has(sp.nan)
                or lim_dy_right.has(sp.nan)
            ):
                unverified_cases.append((
                    checked_val_br,
                    f"Đã kiểm chứng tính liên tục tại điểm kỳ dị {singular_point}, nhưng giới hạn đạo hàm chưa xác định trên toàn bộ miền tham số: "
                    f"lim dy/dt- = {lim_dy_left}, lim dy/dt+ = {lim_dy_right}."
                ))
            else:
                continuity_verified_cases.append((
                    checked_val_br,
                    f"Đã kiểm chứng tính liên tục tại điểm kỳ dị {singular_point}, nhưng giới hạn đạo hàm không xác định hoặc không hữu hạn: "
                    f"lim dy/dt- = {lim_dy_left}, lim dy/dt+ = {lim_dy_right}."
                ))
            continue

        if not _is_valid_real_limit_expr(lim_dy_left, checked_val_br.param_domains, rem_consts) or not _is_valid_real_limit_expr(
            lim_dy_right, checked_val_br.param_domains, rem_consts
        ):
            unverified_cases.append((
                checked_val_br,
                f"Giới hạn đạo hàm tại {singular_point} không chứng minh được tính thực hữu hạn: "
                f"lim dy/dt- = {lim_dy_left}, lim dy/dt+ = {lim_dy_right}."
            ))
            continue

        if deriv_at_point is not None:
            deriv_eqs = [sp.Eq(lim_dy_left, deriv_at_point, evaluate=False), sp.Eq(lim_dy_right, deriv_at_point, evaluate=False)]
        else:
            deriv_eqs = [sp.Eq(lim_dy_left, lim_dy_right, evaluate=False)]

        matches_identically = all(
            _prove_symbolic_zero(sp.simplify(_apply_real_assumptions(eq.lhs - eq.rhs, checked_val_br.param_domains, rem_consts)))
            for eq in deriv_eqs
        )

        if matches_identically:
            if deriv_at_point is not None:
                c1_verified_cases.append((checked_val_br, f"lim y'({variable}) = {deriv_at_point}"))
            elif not checked_val_br.assignments:
                c1_verified_cases.append((checked_val_br, f"lim y'({variable}) = {lim_dy_left}"))
            else:
                conditional_c1_cases.append((checked_val_br, f"lim y'({variable}) = {lim_dy_left}"))
        else:
            active_d_vars = [
                p for p in checked_val_br.param_domains if any(p in eq.free_symbols for eq in deriv_eqs)
            ] + [
                c for c in sorted(rem_consts, key=lambda s: s.name) if any(c in eq.free_symbols for eq in deriv_eqs)
            ]
            if not active_d_vars:
                incompat_proven = any(
                    (
                        sp.simplify(_apply_real_assumptions(eq.lhs - eq.rhs, checked_val_br.param_domains, rem_consts)).is_nonzero is True
                        or (
                            sp.simplify(_apply_real_assumptions(eq.lhs - eq.rhs, checked_val_br.param_domains, rem_consts)).is_number
                            and not _prove_symbolic_zero(sp.simplify(eq.lhs - eq.rhs))
                        )
                    )
                    for eq in deriv_eqs
                )
                if not incompat_proven:
                    unverified_cases.append((
                        checked_val_br,
                        f"Không thể chứng minh hay bác bỏ tương thích đạo hàm một phía ({deriv_eqs})."
                    ))
                elif deriv_at_point is not None:
                    continuity_verified_cases.append((
                        checked_val_br,
                        f"Đã kiểm chứng tính liên tục tại điểm kỳ dị {singular_point}. "
                        f"Tuy nhiên, đạo hàm một phía không khớp với giá trị vi phân yêu cầu ({deriv_at_point}): "
                        f"lim dy/dt- = {lim_dy_left}, lim dy/dt+ = {lim_dy_right}. Không thể mở rộng khả vi C¹."
                    ))
                else:
                    continuity_verified_cases.append((
                        checked_val_br,
                        f"Đã kiểm chứng tính liên tục tại điểm kỳ dị {singular_point}. "
                        f"Tuy nhiên, đạo hàm một phía không khớp nhau: "
                        f"lim dy/dt- = {lim_dy_left} != lim dy/dt+ = {lim_dy_right}. Không thể mở rộng khả vi C¹."
                    ))
            else:
                active_d_doms = {p: dom for p, dom in checked_val_br.param_domains.items()}
                for c in rem_consts:
                    active_d_doms[c] = sp.S.Reals

                d_out, d_sub_branches, d_msg = _solve_real_constraint_system(
                    deriv_eqs,
                    active_d_vars,
                    var_domains={v: active_d_doms[v] for v in active_d_vars},
                )
                if d_out == "unresolved" or (d_out == "resolved" and not d_sub_branches):
                    unverified_cases.append((
                        checked_val_br,
                        d_msg or f"Không thể giải đầy đủ phương trình tương thích đạo hàm {deriv_eqs}."
                    ))
                    continue
                if d_out == "empty":
                    continuity_verified_cases.append((
                        checked_val_br,
                        f"Đã kiểm chứng tính liên tục tại điểm kỳ dị {singular_point}. "
                        f"Phương trình tương thích đạo hàm một phía ({deriv_eqs}) vô nghiệm thực đối với các tham số/hằng số; "
                        f"không thể tồn tại bất kỳ phép gán hằng số nào để mở rộng khả vi C¹."
                    ))
                    continue

                for sb in d_sub_branches:
                    refined_br = _compose_branches(checked_val_br, sb, rem_consts)
                    ref_l = _simplify_limit_expr(branch_left.expression.subs(refined_br.assignments))
                    ref_r = _simplify_limit_expr(branch_right.expression.subs(refined_br.assignments))
                    rem_after_d = all_consts - set(refined_br.assignments.keys())
                    den_out_r, checked_ref_br, den_msg_r = _check_branch_denominators(
                        [ref_l, ref_r], refined_br, var=variable, free_consts=rem_after_d
                    )
                    if den_out_r == "unresolved":
                        unverified_cases.append((refined_br, den_msg_r))
                        continue
                    if den_out_r == "empty":
                        continue
                    try:
                        ref_dy_l = _simplify_limit_expr(
                            _diff_real_expr(ref_l, variable, domain_interval=branch_left.domain_interval, side="-", point=singular_point)
                        )
                        ref_dy_r = _simplify_limit_expr(
                            _diff_real_expr(ref_r, variable, domain_interval=branch_right.domain_interval, side="+", point=singular_point)
                        )
                        ref_lim_l = sp.limit(ref_dy_l, variable, singular_point, dir="-")
                        ref_lim_r = sp.limit(ref_dy_r, variable, singular_point, dir="+")
                    except Exception as exc:
                        unverified_cases.append((checked_ref_br, f"Không thể xác minh đạo hàm sau ràng buộc: {exc}"))
                        continue
                    if not _is_valid_real_limit_expr(ref_lim_l, checked_ref_br.param_domains, rem_after_d) or not _is_valid_real_limit_expr(
                        ref_lim_r, checked_ref_br.param_domains, rem_after_d
                    ):
                        unverified_cases.append((checked_ref_br, f"Giới hạn đạo hàm sau ràng buộc không hợp lệ: {ref_lim_l}, {ref_lim_r}"))
                        continue
                    if deriv_at_point is not None:
                        c1_verified_cases.append((checked_ref_br, f"lim y'({variable}) = {deriv_at_point}"))
                    else:
                        conditional_c1_cases.append((checked_ref_br, f"lim y'({variable}) = {ref_lim_l}"))

    # Conservative completeness gate: never claim complete conditional/unconditional extension if any branch remained unresolved
    if has_unresolved_val or unverified_cases:
        reason = unresolved_val_msg if has_unresolved_val else unverified_cases[0][1]
        return (VerificationStatus.UNVERIFIED, reason)

    if c1_verified_cases:
        br0, info = c1_verified_cases[0]
        assigned_branches = [br for br, _ in c1_verified_cases if br.assignments]
        c_str = _format_branches_summary(assigned_branches) if assigned_branches else ""
        c_info = f" ({c_str})" if c_str else ""
        y_info = f"y({singular_point}) = {value_at_point}" if value_at_point is not None else f"lim y({variable}) liên tục"
        return (
            VerificationStatus.C1_EXTENSION_VERIFIED,
            f"Đã kiểm chứng khả năng nối trơn C¹ tại điểm kỳ dị {singular_point}: {y_info}, {info}{c_info}."
        )

    if conditional_c1_cases:
        constraints_repr = _format_branches_summary([br for br, _ in conditional_c1_cases]) or "điều kiện tương thích"
        return (
            VerificationStatus.CONDITIONAL_EXTENSION,
            f"Họ nghiệm phụ thuộc các hằng số tích phân tự do. "
            f"Nghiệm có thể mở rộng trơn C¹ qua điểm kỳ dị {singular_point} khi và chỉ khi thỏa mãn điều kiện ràng buộc: {constraints_repr}. "
            f"Họ nghiệm tổng quát không thể xem là nối trơn C¹ vô điều kiện."
        )

    if continuity_verified_cases:
        _, msg = continuity_verified_cases[0]
        return (VerificationStatus.CONTINUITY_VERIFIED, msg)

    return (
        VerificationStatus.FAILED,
        f"Không thể kiểm chứng khả năng mở rộng nghiệm qua điểm kỳ dị {singular_point}."
    )

def derive_unique_branch_constant(
    expr: sp.Expr,
    variable: sp.Symbol,
    singular_point: sp.Expr,
    direction: str,
    c_sym: sp.Symbol,
    target_value: sp.Expr,
) -> sp.Expr | None:
    """Resolve a unique real integration constant fixing both pole cancellation and limit value."""
    try:
        outcome, pole_sols, _ = _derive_pole_cancellation_constraints(
            expr, variable, singular_point, direction, {c_sym}
        )
        if outcome != "resolved" or len(pole_sols) != 1:
            return None
        assigns, lim_val = pole_sols[0]
        candidate_val: sp.Expr | None = sp.simplify(assigns[c_sym]) if c_sym in assigns else None
        if candidate_val is None and c_sym in lim_val.free_symbols:
            sys_out, branches, _ = _solve_real_constraint_system(
                [sp.Eq(lim_val, target_value, evaluate=False)], [c_sym]
            )
            if sys_out != "resolved" or len(branches) != 1 or c_sym not in branches[0].assignments or branches[0].param_domains:
                return None
            candidate_val = sp.simplify(branches[0].assignments[c_sym])
            lim_val = sp.simplify(lim_val.subs(c_sym, candidate_val))
        if candidate_val is None or candidate_val.is_real is False or candidate_val.has(sp.I):
            return None
        if _prove_symbolic_zero(sp.simplify(lim_val - target_value)):
            return candidate_val
    except Exception:
        return None
    return None


def classify_scalar_real_finite(
    val: sp.Expr | None,
    *,
    allow_complex: bool = False,
) -> tuple[str, str]:
    """Classify a scalar SymPy expression as 'valid', 'invalid', or 'unknown' for real finiteness.

    Fail closed on unassumed or indeterminate symbolic quantities ('unknown') while
    still permitting ground numeric expressions (e.g., Ci(exp(1)), Si(1)) whose
    realness and finiteness can be established numerically.
    """
    if val is None:
        return "unknown", "Không có giá trị để kiểm tra tính thực hữu hạn."
    if val.has(sp.Integral):
        return "unknown", "Biểu thức chứa tích phân chưa đánh giá."
    if val.has(sp.zoo, sp.nan, sp.oo, -sp.oo, sp.AccumBounds) or val.is_finite is False:
        return "invalid", f"Giá trị {val} không phải là số hữu hạn."

    candidate = val
    if not allow_complex:
        if candidate.is_real is False:
            return "invalid", f"Giá trị {val} chứa phần ảo hoặc không phải là số thực."
        if candidate.has(sp.I):
            candidate = sp.simplify(candidate)
            if candidate.is_real is False:
                return "invalid", f"Giá trị {val} chứa phần ảo hoặc không phải là số thực."

    if not candidate.free_symbols:
        try:
            num = complex(candidate.evalf())
        except (TypeError, ValueError):
            if candidate.is_finite is True and (allow_complex or candidate.is_real is True):
                return "valid", ""
            return "unknown", f"Không thể đánh giá số cho giá trị {val}."
        if not (math.isfinite(num.real) and math.isfinite(num.imag)):
            return "invalid", f"Giá trị {val} không hữu hạn khi tính số."
        if not allow_complex and abs(num.imag) > 1e-12:
            return "invalid", f"Giá trị {val} nhận giá trị phức ({val})."
        return "valid", ""

    if candidate.is_finite is True and (allow_complex or candidate.is_real is True):
        return "valid", ""

    return (
        "unknown",
        f"Không thể xác nhận giá trị {val} là số thực hữu hạn với các giả thiết hiện tại.",
    )


def _evaluate_single_domain_constraint(
    relation: str,
    expr_target: sp.Expr,
    eval_val: sp.Expr,
    x0: sp.Expr,
    y0: sp.Expr,
    label_prefix: str = "Điều kiện xác định ban đầu",
) -> tuple[str, str]:
    """Evaluate a single ('ne', 'ge', 'gt') domain constraint at an initial point."""
    scalar_status, scalar_msg = classify_scalar_real_finite(eval_val, allow_complex=False)
    if scalar_status == "invalid":
        return (
            "invalid",
            f"{label_prefix} đối với {expr_target} không xác định thực hữu hạn tại ({x0}, {y0}): {scalar_msg}",
        )

    if relation == "ne":
        if _prove_symbolic_zero(eval_val) or eval_val == 0:
            return (
                "invalid",
                f"{label_prefix}: {expr_target} khác 0 bị vi phạm tại ({x0}, {y0}) ({expr_target} = {eval_val}).",
            )
        if scalar_status == "unknown":
            return (
                "unknown",
                f"Không thể xác nhận điều kiện {expr_target} != 0 tại ({x0}, {y0}) do thiếu giả thiết thực/khác 0.",
            )
        if eval_val.is_zero is False:
            return "valid", ""
        if not eval_val.free_symbols:
            try:
                num = complex(eval_val.evalf())
                if abs(num) > 1e-12:
                    return "valid", ""
            except (TypeError, ValueError) as exc:
                return (
                    "unknown",
                    f"Không thể đánh giá số để xác nhận {expr_target} != 0 tại ({x0}, {y0}): {exc}",
                )
        return (
            "unknown",
            f"Không thể loại trừ khả năng {expr_target} = 0 tại ({x0}, {y0}).",
        )

    if relation == "ge":
        if scalar_status == "unknown":
            return (
                "unknown",
                f"Không thể xác nhận điều kiện {expr_target} >= 0 tại ({x0}, {y0}): {scalar_msg}",
            )
        if eval_val.is_negative is True:
            return (
                "invalid",
                f"{label_prefix}: biểu thức dưới căn bậc chẵn {expr_target} có giá trị âm ({eval_val}) tại ({x0}, {y0}).",
            )
        if eval_val.is_nonnegative is True or _prove_symbolic_zero(eval_val):
            return "valid", ""
        if not eval_val.free_symbols:
            try:
                num = complex(eval_val.evalf())
                if abs(num.imag) <= 1e-12:
                    if num.real < -1e-12:
                        return (
                            "invalid",
                            f"{label_prefix}: biểu thức dưới căn bậc chẵn {expr_target} có giá trị âm ({eval_val}) tại ({x0}, {y0}).",
                        )
                    if num.real > 1e-12:
                        return "valid", ""
            except (TypeError, ValueError) as exc:
                return (
                    "unknown",
                    f"Không thể đánh giá số để xác nhận {expr_target} >= 0 tại ({x0}, {y0}): {exc}",
                )
        return (
            "unknown",
            f"Không thể xác nhận điều kiện {expr_target} >= 0 tại ({x0}, {y0}).",
        )

    if relation == "gt":
        if scalar_status == "unknown":
            return (
                "unknown",
                f"Không thể xác nhận điều kiện {expr_target} > 0 tại ({x0}, {y0}): {scalar_msg}",
            )
        if _prove_symbolic_zero(eval_val) or eval_val.is_nonpositive is True:
            return (
                "invalid",
                f"{label_prefix}: biểu thức trong logarit {expr_target} không dương ({eval_val}) tại ({x0}, {y0}).",
            )
        if eval_val.is_positive is True:
            return "valid", ""
        if not eval_val.free_symbols:
            try:
                num = complex(eval_val.evalf())
                if abs(num.imag) <= 1e-12:
                    if num.real <= 1e-12 and (num.real < -1e-12 or _prove_symbolic_zero(eval_val)):
                        return (
                            "invalid",
                            f"{label_prefix}: biểu thức trong logarit {expr_target} không dương ({eval_val}) tại ({x0}, {y0}).",
                        )
                    if num.real > 1e-12:
                        return "valid", ""
            except (TypeError, ValueError) as exc:
                return (
                    "unknown",
                    f"Không thể đánh giá số để xác nhận {expr_target} > 0 tại ({x0}, {y0}): {exc}",
                )
        return (
            "unknown",
            f"Không thể xác nhận điều kiện {expr_target} > 0 tại ({x0}, {y0}).",
        )

    return "unknown", f"Không hỗ trợ loại ràng buộc miền '{relation}'."


def evaluate_initial_point_domain(
    expr: sp.Expr | None,
    x_sym: sp.Symbol,
    y_sym: sp.Symbol,
    x0: sp.Expr,
    y0: sp.Expr,
    original_denominators: tuple[sp.Expr, ...] = (),
    leading_coeffs: tuple[sp.Expr, ...] = (),
    source_constraints: tuple[Any, ...] = (),
    *,
    allow_complex: bool = False,
) -> tuple[str, str]:
    """Evaluate initial point (x0, y0) against ODE domain constraints returning ('valid'|'invalid'|'unknown', msg)."""
    unknown_reasons: list[str] = []

    # 0. Check finiteness and reality of initial point coordinates
    for coord_name, coord_val in (("x0", x0), ("y0", y0)):
        if coord_val is not None:
            coord_stat, coord_msg = classify_scalar_real_finite(coord_val, allow_complex=allow_complex)
            if coord_stat == "invalid":
                return "invalid", f"Giá trị điều kiện ban đầu {coord_name} = {coord_val}: {coord_msg}"
            if coord_stat == "unknown":
                unknown_reasons.append(f"Giá trị điều kiện ban đầu {coord_name} = {coord_val}: {coord_msg}")

    sub_map = [(sym, val) for sym, val in ((x_sym, x0), (y_sym, y0)) if val is not None]

    # 1. Check unsimplified original denominators
    for denom in original_denominators:
        try:
            d_val = sp.simplify(denom.subs(sub_map))
        except ZeroDivisionError as exc:
            return "invalid", f"Chia cho 0 khi đánh giá mẫu số ban đầu {denom} tại ({x0}, {y0}): {exc}"
        except Exception as exc:
            unknown_reasons.append(f"Không thể đánh giá mẫu số ban đầu {denom}: {exc}")
            continue
        d_stat, d_msg = _evaluate_single_domain_constraint(
            "ne", denom, d_val, x0, y0, label_prefix="Mẫu số ban đầu"
        )
        if d_stat == "invalid":
            return (
                "invalid",
                f"Mẫu số ban đầu {denom} triệt tiêu tại điều kiện ban đầu ({x0}, {y0}) (Original denominator vanishes at initial point).",
            )
        if d_stat == "unknown":
            unknown_reasons.append(d_msg)

    # 2. Check preserved unsimplified source constraints (!= 0, >= 0, > 0)
    for constraint in source_constraints:
        rel = getattr(constraint, "relation", None)
        c_expr = getattr(constraint, "expr", None)
        if rel is None or c_expr is None:
            continue
        try:
            c_val = sp.simplify(c_expr.subs(sub_map))
        except ZeroDivisionError as exc:
            return "invalid", f"Chia cho 0 khi đánh giá ràng buộc {c_expr} tại ({x0}, {y0}): {exc}"
        except Exception as exc:
            unknown_reasons.append(f"Không thể đánh giá ràng buộc {c_expr} tại ({x0}, {y0}): {exc}")
            continue
        c_prefix = "Mẫu số ban đầu" if rel == "ne" else "Điều kiện xác định ban đầu"
        c_stat, c_msg = _evaluate_single_domain_constraint(
            rel, c_expr, c_val, x0, y0, label_prefix=c_prefix
        )
        if c_stat == "invalid":
            return "invalid", c_msg
        if c_stat == "unknown":
            unknown_reasons.append(c_msg)

    # 3. Check leading coefficients
    for lcoeff in leading_coeffs:
        try:
            if y_sym in lcoeff.free_symbols:
                # Differential forms M dx + N dy = 0 can have a regular vertical tangent N(x0, y0) = 0
                # (only reject if the coefficient vanishes identically at x0 or is non-real/non-finite).
                lc_at_x0 = sp.simplify(lcoeff.subs([(x_sym, x0)]))
                if _prove_symbolic_zero(lc_at_x0) or lc_at_x0 == 0:
                    return (
                        "invalid",
                        f"Điểm ban đầu {x0} là điểm kỳ dị của phương trình vi phân: hệ số dẫn {lcoeff} triệt tiêu (Initial point is a singular point where leading coefficient vanishes).",
                    )
                lc_at_ic = sp.simplify(lcoeff.subs(sub_map))
                lc_stat, lc_msg = classify_scalar_real_finite(lc_at_ic, allow_complex=allow_complex)
                if lc_stat == "invalid":
                    return "invalid", f"Hệ số dẫn {lcoeff} không xác định thực hữu hạn tại ({x0}, {y0}): {lc_msg}"
                if lc_stat == "unknown":
                    unknown_reasons.append(lc_msg)
                continue
            lc_val = sp.simplify(lcoeff.subs(sub_map))
        except ZeroDivisionError as exc:
            return "invalid", f"Chia cho 0 khi đánh giá hệ số dẫn {lcoeff} tại ({x0}, {y0}): {exc}"
        except Exception as exc:
            unknown_reasons.append(f"Không thể đánh giá hệ số dẫn {lcoeff}: {exc}")
            continue
        lc_stat, lc_msg = _evaluate_single_domain_constraint(
            "ne", lcoeff, lc_val, x0, y0, label_prefix="Hệ số dẫn"
        )
        if lc_stat == "invalid":
            return (
                "invalid",
                f"Điểm ban đầu {x0} là điểm kỳ dị của phương trình vi phân: hệ số dẫn {lcoeff} triệt tiêu (Initial point is a singular point where leading coefficient vanishes).",
            )
        if lc_stat == "unknown":
            unknown_reasons.append(lc_msg)

    # 4. Check expression AST nodes and evaluation
    if expr is not None:
        expr_allow_complex = allow_complex or expr.has(sp.I)
        for node in sp.preorder_traversal(expr):
            if isinstance(node, sp.Pow):
                b, e = node.as_base_exp()
                e_simp = sp.simplify(e)
                if e_simp.is_negative:
                    try:
                        b_val = sp.simplify(b.subs(sub_map))
                        b_stat, b_msg = _evaluate_single_domain_constraint(
                            "ne", b, b_val, x0, y0, label_prefix="Mẫu số"
                        )
                        if b_stat == "invalid":
                            return (
                                "invalid",
                                f"Mẫu số ban đầu {b} triệt tiêu tại điều kiện ban đầu ({x0}, {y0}) (Original denominator vanishes at initial point).",
                            )
                        if b_stat == "unknown":
                            unknown_reasons.append(b_msg)
                    except ZeroDivisionError as exc:
                        return "invalid", f"Chia cho 0 khi đánh giá mẫu số {b} tại ({x0}, {y0}): {exc}"
                    except Exception as exc:
                        unknown_reasons.append(f"Không thể đánh giá mẫu số {b} tại ({x0}, {y0}): {exc}")
                if e_simp.is_Rational and e_simp.q % 2 == 0 and not expr_allow_complex:
                    try:
                        b_val = sp.simplify(b.subs(sub_map))
                        b_stat, b_msg = _evaluate_single_domain_constraint(
                            "ge", b, b_val, x0, y0, label_prefix="Điều kiện căn bậc chẵn"
                        )
                        if b_stat == "invalid":
                            return "invalid", b_msg
                        if b_stat == "unknown":
                            unknown_reasons.append(b_msg)
                    except ZeroDivisionError as exc:
                        return (
                            "invalid",
                            f"Chia cho 0 khi đánh giá biểu thức dưới căn bậc chẵn {b} tại ({x0}, {y0}): {exc}",
                        )
                    except Exception as exc:
                        unknown_reasons.append(
                            f"Không thể đánh giá biểu thức dưới căn bậc chẵn {b} tại ({x0}, {y0}): {exc}"
                        )
            elif isinstance(node, sp.log) and not expr_allow_complex:
                try:
                    arg_val = sp.simplify(node.args[0].subs(sub_map))
                    a_stat, a_msg = _evaluate_single_domain_constraint(
                        "gt", node.args[0], arg_val, x0, y0, label_prefix="Điều kiện logarit"
                    )
                    if a_stat == "invalid":
                        return "invalid", a_msg
                    if a_stat == "unknown":
                        unknown_reasons.append(a_msg)
                except ZeroDivisionError as exc:
                    return (
                        "invalid",
                        f"Chia cho 0 khi đánh giá biểu thức trong logarit {node.args[0]} tại ({x0}, {y0}): {exc}",
                    )
                except Exception as exc:
                    unknown_reasons.append(
                        f"Không thể đánh giá biểu thức trong logarit {node.args[0]} tại ({x0}, {y0}): {exc}"
                    )

        try:
            val = sp.simplify(expr.subs(sub_map))
            val_stat, val_msg = classify_scalar_real_finite(val, allow_complex=expr_allow_complex)
            if val_stat == "invalid":
                if val.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or val.is_finite is False:
                    return (
                        "invalid",
                        f"Phương trình vi phân không xác định (chia cho 0 hoặc tiến tới vô cực: {val}) tại điểm ban đầu ({x0}, {y0}).",
                    )
                return (
                    "invalid",
                    f"Phương trình vi phân nhận giá trị phức ({val}) tại điểm ban đầu ({x0}, {y0}).",
                )
            if val_stat == "unknown":
                unknown_reasons.append(val_msg)
        except ZeroDivisionError as exc:
            return "invalid", f"Phương trình vi phân chia cho 0 tại điểm ban đầu ({x0}, {y0}): {exc}"
        except Exception as exc:
            unknown_reasons.append(
                f"Không thể đánh giá phương trình vi phân tại điểm ban đầu ({x0}, {y0}): {exc}"
            )

    if unknown_reasons:
        return "unknown", unknown_reasons[0]

    return "valid", ""


def validate_initial_point_in_domain(
    expr: sp.Expr | None,
    x_sym: sp.Symbol,
    y_sym: sp.Symbol,
    x0: sp.Expr,
    y0: sp.Expr,
    original_denominators: tuple[sp.Expr, ...] = (),
    leading_coeffs: tuple[sp.Expr, ...] = (),
    source_constraints: tuple[Any, ...] = (),
) -> tuple[bool, str]:
    """Legacy fail-closed Boolean wrapper returning True only when domain status is proven 'valid'.

    Note: Both 'invalid' and 'unknown' statuses return False so unresolved conditions never
    silently become valid. Internal ODE solvers must use evaluate_initial_point_domain() directly
    to distinguish invalid inputs (INVALID_INPUT) from unresolved symbolic cases (UNVERIFIED).
    """
    status, msg = evaluate_initial_point_domain(
        expr,
        x_sym,
        y_sym,
        x0,
        y0,
        original_denominators=original_denominators,
        leading_coeffs=leading_coeffs,
        source_constraints=source_constraints,
    )
    if status != "valid":
        return False, msg
    return True, ""


def _find_numerical_discrepancy(
    expr: sp.Expr,
    variable: sp.Symbol,
    constants: tuple[sp.Symbol, ...] = (),
    domain_interval: tuple[sp.Expr | float, sp.Expr | float] | str | None = None,
    domain_restrictions: tuple[str, ...] = (),
    probe_points: tuple[float, ...] = (0.19, 0.47, 0.83, 1.27, 2.13, 3.71, -0.65, -1.82),
    const_subsets: tuple[tuple[float, ...], ...] = ((1.0, 1.0), (0.5, -2.0), (-1.5, 0.8)),
    tol: float = 1e-5,
) -> float | None:
    """Probe an expression numerically in an attempt to find a non-zero residual counterexample.

    A detected discrepancy proves the expression is NOT identically zero.
    Domain-aware: Excludes sample points outside the valid domain, near poles, or causing invalid evaluations.
    """
    try:
        if expr.is_number:
            c_val = complex(expr.evalf())
            if not math.isnan(c_val.real) and not math.isinf(c_val.real):
                err = abs(c_val)
                if err > tol:
                    return err
                return None

        active_consts = [c for c in constants if expr.has(c)]
        if not active_consts:
            active_consts = [sym for sym in expr.free_symbols if re.match(r"^C\d*$", sym.name)]

        other_syms = [s for s in expr.free_symbols if s not in active_consts and s != variable]
        active_points = _filter_probe_points_by_domain(probe_points, variable, domain_interval, domain_restrictions)
        if not active_points:
            return None

        def _probe_expr(cur_expr: sp.Expr) -> float | None:
            for pt_idx, pt in enumerate(active_points):
                sub_list = []
                if cur_expr.has(variable):
                    sub_list.append((variable, pt))
                for idx, osym in enumerate(other_syms):
                    sub_list.append((osym, active_points[(pt_idx + idx + 1) % len(active_points)]))

                # Check for poles/singularities or non-real evaluations
                has_singularity = False
                for node in sp.preorder_traversal(cur_expr):
                    if isinstance(node, sp.Pow):
                        b, e = node.as_base_exp()
                        if e.is_negative:
                            try:
                                b_val = float(b.subs(sub_list).evalf())
                                if abs(b_val) < 1e-4:
                                    has_singularity = True
                                    break
                            except Exception:
                                has_singularity = True
                                break
                        elif e.is_Rational and e.q % 2 == 0:
                            try:
                                b_val = float(b.subs(sub_list).evalf())
                                if b_val < -1e-5:
                                    has_singularity = True
                                    break
                            except Exception:
                                has_singularity = True
                                break
                    elif isinstance(node, sp.log):
                        try:
                            arg_val = float(node.args[0].subs(sub_list).evalf())
                            if arg_val <= 1e-5:
                                has_singularity = True
                                break
                        except Exception:
                            has_singularity = True
                            break

                if has_singularity:
                    continue

                try:
                    val = complex(cur_expr.subs(sub_list).evalf())
                    if math.isnan(val.real) or math.isinf(val.real):
                        continue
                    if abs(val.imag) > 1e-4 and not cur_expr.has(sp.I):
                        continue
                    err = abs(val)
                    if err > tol:
                        return err
                except Exception:
                    continue
            return None

        if not active_consts:
            return _probe_expr(expr)

        for c_vals in const_subsets:
            sub_map = [(c, c_vals[i % len(c_vals)]) for i, c in enumerate(active_consts)]
            try:
                c_expr = expr.subs(sub_map)
            except Exception:
                continue
            err = _probe_expr(c_expr)
            if err is not None:
                return err
    except Exception:
        return None
    return None


def check_residual_outcome(
    expr: sp.Expr,
    variable: sp.Symbol,
    constants: tuple[sp.Symbol, ...] = (),
    domain_interval: tuple[sp.Expr | float, sp.Expr | float] | str | None = None,
    domain_restrictions: tuple[str, ...] = (),
    probe_points: tuple[float, ...] = (0.19, 0.47, 0.83, 1.27, 2.13, 3.71, -0.65, -1.82),
) -> ResidualCheckOutcome:
    """Classify the residual into PROVED_ZERO, PROVED_NONZERO, UNKNOWN, or INVALID_DOMAIN."""
    if _prove_symbolic_zero(expr, constants, domain_interval=domain_interval, variable=variable):
        return ResidualCheckOutcome.PROVED_ZERO

    active_points = _filter_probe_points_by_domain(probe_points, variable, domain_interval, domain_restrictions)
    if not active_points:
        return ResidualCheckOutcome.INVALID_DOMAIN

    disc = _find_numerical_discrepancy(
        expr,
        variable,
        constants,
        domain_interval=domain_interval,
        domain_restrictions=domain_restrictions,
        probe_points=probe_points,
    )
    if disc is not None or (expr.is_number and expr != 0):
        return ResidualCheckOutcome.PROVED_NONZERO

    return ResidualCheckOutcome.UNKNOWN


class ODEVerifier(Verifier):
    """Verifies differential equation solutions against original equations and initial conditions.

    Strict verification policy:
    - VERIFIED: Established symbolically under declared mathematical assumptions.
    - FAILED: Genuine counterexample or contradiction (symbolic non-zero or numerical discrepancy).
    - UNVERIFIED: Inconclusive symbolic result; numerical probes NEVER promote to VERIFIED.
    """

    SAMPLE_PROBE_POINTS = (0.19, 0.47, 0.83, 1.27, 2.13, 3.71, -0.65, -1.82)

    def verify(self, *args: Any, **kwargs: Any) -> VerificationResult:
        """Route to appropriate verification method based on arguments."""
        if "potential_F" in kwargs or (len(args) >= 3 and isinstance(args[0], sp.Expr) and len(args) == 5):
            return self.verify_exact(*args, **kwargs)
        return self.verify_explicit(*args, **kwargs)

    def verify_explicit(
        self,
        solution: sp.Expr,
        variable: sp.Symbol,
        p_expr: sp.Expr = sp.Integer(0),
        g_expr: sp.Expr = sp.Integer(0),
        initial_condition: tuple[sp.Expr, sp.Expr] | None = None,
        integration_constant: sp.Symbol | None = None,
        rhs_f: sp.Expr | None = None,
        dep_var: sp.Symbol | None = None,
        domain_interval: tuple[sp.Expr | float, sp.Expr | float] | str | None = None,
        domain_restrictions: tuple[str, ...] = (),
    ) -> VerificationResult:
        """Verify an explicit ODE solution y(t) by evaluating the residual:

        For linear form: R(t) = y'(t) + p(t)*y(t) - g(t)
        For general explicit form: R(t) = y'(t) - F(t, y(t))
        Supports domain-aware verification via domain_interval and domain_restrictions.
        """
        try:
            diff_y = _diff_real_expr(solution, variable, domain_interval=domain_interval)
            if rhs_f is not None and dep_var is not None:
                residual = sp.simplify(diff_y - rhs_f.subs(dep_var, solution))
            else:
                residual = sp.simplify(diff_y + p_expr * solution - g_expr)
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="residual_computation_failed",
                details=f"Không thể tính toán biểu thức dư R(t): {exc}",
            )

        # Identify integration constants
        consts: list[sp.Symbol] = []
        if integration_constant is not None:
            consts.append(integration_constant)
        for sym in solution.free_symbols:
            if sym != variable and re.match(r"^C\d*$", sym.name) and sym not in consts:
                consts.append(sym)

        # 1. Rigorous symbolic verification of residual (domain-aware)
        is_residual_zero = _prove_symbolic_zero(
            residual,
            tuple(consts),
            domain_interval=domain_interval,
            variable=variable,
        )

        # 2. If symbolic simplification was inconclusive, look for numerical discrepancies (counterexamples)
        if not is_residual_zero:
            discrepancy = _find_numerical_discrepancy(
                residual,
                variable,
                tuple(consts),
                domain_interval=domain_interval,
                domain_restrictions=domain_restrictions,
                probe_points=self.SAMPLE_PROBE_POINTS,
            )
            if discrepancy is not None:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="numerical_residual_discrepancy",
                    details=f"Phát hiện sai số trong kiểm tra số dư tại điểm thử nghiệm (sai số: {discrepancy:.6e}). Nghiệm không thỏa mãn phương trình.",
                )
            # Never promote inconclusive numerical result to VERIFIED
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="inconclusive",
                details="Biểu thức dư giải tích R(t) không thể rút gọn thành 0 bằng phương pháp ký hiệu (Inconclusive).",
            )

        # 3. Check initial condition if provided
        if initial_condition is not None:
            t0, y0 = initial_condition

            # Validate that t0 lies strictly within the domain interval
            if domain_interval is not None and isinstance(domain_interval, (tuple, list)) and len(domain_interval) == 2:
                low, high = domain_interval
                try:
                    t0_n = float(sp.N(t0))
                    if low is not None and low != -sp.oo:
                        low_n = float(sp.N(low))
                        if t0_n <= low_n:
                            return VerificationResult(
                                status=VerificationStatus.FAILED,
                                method="ic_outside_domain_interval",
                                details=f"Điểm ban đầu {t0} nằm tại hoặc ngoài cận dưới của miền xác định ({low}, {high}).",
                            )
                    if high is not None and high != sp.oo:
                        high_n = float(sp.N(high))
                        if t0_n >= high_n:
                            return VerificationResult(
                                status=VerificationStatus.FAILED,
                                method="ic_outside_domain_interval",
                                details=f"Điểm ban đầu {t0} nằm tại hoặc ngoài cận trên của miền xác định ({low}, {high}).",
                            )
                except Exception:
                    pass

            # Validate that original ODE RHS is non-singular at (t0, y0)
            if rhs_f is not None and dep_var is not None:
                try:
                    f_val = rhs_f.subs([(variable, t0), (dep_var, y0)])
                    if f_val.has(sp.zoo, sp.nan) or f_val.is_finite is False:
                        return VerificationResult(
                            status=VerificationStatus.FAILED,
                            method="ic_ode_singularity",
                            details=f"Vế phải phương trình vi phân không xác định tại điều kiện ban đầu ({t0}, {y0}).",
                        )
                except Exception:
                    pass

            try:
                subbed_sol = solution.subs(variable, t0)
                collapsed_sol = _simplify_zero_bound_integrals(subbed_sol)

                # If solution still has un-collapsed integrals, it is not properly anchored at t0
                if collapsed_sol.has(sp.Integral):
                    return VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="ic_unanchored_integral",
                        details=f"Biểu thức nghiệm tại {variable} = {t0} chứa tích phân chưa xác định hoặc không triệt tiêu tại cận; chưa thể kiểm chứng điều kiện ban đầu.",
                    )

                val_at_t0 = sp.simplify(collapsed_sol)
                ic_diff = sp.simplify(val_at_t0 - y0)
                if not _prove_symbolic_zero(ic_diff, tuple(consts), domain_interval=domain_interval, variable=variable):
                    # Check for contradiction / discrepancy
                    disc_ic = _find_numerical_discrepancy(
                        ic_diff,
                        variable,
                        tuple(consts),
                        domain_interval=domain_interval,
                        domain_restrictions=domain_restrictions,
                    )
                    if disc_ic is not None or ic_diff.is_number:
                        return VerificationResult(
                            status=VerificationStatus.FAILED,
                            method="initial_condition_mismatch",
                            details=f"Nghiệm thỏa mãn phương trình vi phân nhưng sai lệch tại điều kiện ban đầu: y({t0}) = {val_at_t0} != {y0}.",
                        )
                    return VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="ic_evaluation_failed",
                        details=f"Không thể xác nhận điều kiện ban đầu y({t0}) = {y0} bằng phương pháp ký hiệu.",
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
            details=f"Kiểm chứng độc lập thành công: Biểu thức dư R({variable}) ≡ 0 bằng phương pháp ký hiệu.",
        )

    def verify_branch_solutions(
        self,
        branches: tuple[BranchSolution, ...],
        variable: sp.Symbol,
        p_expr: sp.Expr = sp.Integer(0),
        g_expr: sp.Expr = sp.Integer(0),
        initial_condition: tuple[sp.Expr, sp.Expr] | None = None,
        singular_points: tuple[sp.Expr, ...] = (),
        singular_point_analyses: tuple[Any, ...] = (),
    ) -> tuple[tuple[BranchSolution, ...], VerificationResult]:
        """Verify each branch solution on its valid domain interval independently,
        and evaluate singular-point continuation properties across adjacent branches."""
        verified_branches: list[BranchSolution] = []
        all_verified = True
        has_failed = False
        failed_details: list[str] = []

        for b in branches:
            # Determine if initial condition applies to this branch interior
            branch_ic = None
            if initial_condition is not None and b.domain_interval is not None:
                t0, y0 = initial_condition
                low, high = b.domain_interval
                if is_point_in_interval_interior(t0, low, high):
                    branch_ic = initial_condition

            const_sym = b.integration_constant if isinstance(b.integration_constant, sp.Symbol) else None
            b_verif = self.verify_explicit(
                solution=b.expression,
                variable=variable,
                p_expr=p_expr,
                g_expr=g_expr,
                initial_condition=branch_ic,
                integration_constant=const_sym,
                domain_interval=b.domain_interval,
                domain_restrictions=b.domain_restrictions,
            )

            new_b = BranchSolution(
                expression=b.expression,
                solution_str=b.solution_str,
                solution_latex=b.solution_latex,
                branch_identity=b.branch_identity,
                integration_constant=b.integration_constant,
                integration_constant_val=b.integration_constant_val,
                real_root_restrictions=b.real_root_restrictions,
                denominator_exclusions=b.denominator_exclusions,
                domain_interval=b.domain_interval,
                domain_restrictions=b.domain_restrictions,
                verification=b_verif,
                extension_status=b.extension_status,
                extension_details=b.extension_details,
                left_open=b.left_open,
                right_open=b.right_open,
                domain_set=b.domain_set,
                singular_exclusions=b.singular_exclusions,
                initial_condition_status=b.initial_condition_status,
            )
            verified_branches.append(new_b)

            if b_verif.status == VerificationStatus.FAILED:
                has_failed = True
                failed_details.append(f"{b.branch_identity}: {b_verif.details}")
            elif b_verif.status != VerificationStatus.VERIFIED:
                all_verified = False

        # Evaluate singular-point continuation across adjacent branches
        singular_ext_statuses: list[VerificationStatus] = []
        singular_ext_details_list: list[str] = []

        if singular_points and len(verified_branches) > 1:
            for sp_pt in singular_points:
                val_at_pt = None
                deriv_at_pt = None
                if singular_point_analyses:
                    for spa in singular_point_analyses:
                        if hasattr(spa, "point") and sp.simplify(spa.point - sp_pt) == 0:
                            val_at_pt = spa.value_at_point
                            deriv_at_pt = spa.derivative_at_point
                            break

                b_left_idx = None
                b_right_idx = None
                for idx, b in enumerate(verified_branches):
                    if b.domain_interval is not None:
                        low, high = b.domain_interval
                        try:
                            if high is not None and sp.simplify(high - sp_pt) == 0:
                                b_left_idx = idx
                            elif low is not None and sp.simplify(low - sp_pt) == 0:
                                b_right_idx = idx
                        except Exception:
                            pass

                b_left = verified_branches[b_left_idx] if b_left_idx is not None else None
                b_right = verified_branches[b_right_idx] if b_right_idx is not None else None

                ext_status, ext_details = verify_singular_extension(
                    branch_left=b_left,
                    branch_right=b_right,
                    singular_point=sp_pt,
                    value_at_point=val_at_pt,
                    deriv_at_point=deriv_at_pt,
                    variable=variable,
                )
                singular_ext_statuses.append(ext_status)
                singular_ext_details_list.append(f"{sp_pt}: {ext_details}")

                for b_idx in (b_left_idx, b_right_idx):
                    if b_idx is not None:
                        curr_b = verified_branches[b_idx]
                        comb_details = (
                            f"{curr_b.extension_details} (Kiểm định nối nghiệm: {ext_details})"
                            if curr_b.extension_details
                            else ext_details
                        )
                        verified_branches[b_idx] = BranchSolution(
                            expression=curr_b.expression,
                            solution_str=curr_b.solution_str,
                            solution_latex=curr_b.solution_latex,
                            branch_identity=curr_b.branch_identity,
                            integration_constant=curr_b.integration_constant,
                            integration_constant_val=curr_b.integration_constant_val,
                            real_root_restrictions=curr_b.real_root_restrictions,
                            denominator_exclusions=curr_b.denominator_exclusions,
                            domain_interval=curr_b.domain_interval,
                            domain_restrictions=curr_b.domain_restrictions,
                            verification=curr_b.verification,
                            extension_status=ext_status.value,
                            extension_details=comb_details,
                            left_open=curr_b.left_open,
                            right_open=curr_b.right_open,
                            domain_set=curr_b.domain_set,
                            singular_exclusions=curr_b.singular_exclusions,
                            initial_condition_status=curr_b.initial_condition_status,
                        )

        # Check if initial condition was at a singular point
        is_ic_at_singular_point = False
        if initial_condition is not None and singular_points:
            t0, _ = initial_condition
            for sp_pt in singular_points:
                try:
                    if _prove_symbolic_zero(sp.simplify(t0 - sp_pt)) or sp.simplify(t0 - sp_pt) == 0:
                        is_ic_at_singular_point = True
                        break
                except Exception:
                    pass

        # Authoritative Status Aggregation (Section 3.2)
        if has_failed:
            overall_status = VerificationStatus.FAILED
            overall_details = "Phát hiện sai số trong một số nhánh nghiệm: " + "; ".join(failed_details)
        elif initial_condition is not None and not is_ic_at_singular_point and len(branches) > 1:
            # Regular Cauchy problem on disconnected domain: target branch determined and verified;
            # failure to extend continuously across a singular boundary point != t0 is normal maximal-interval behavior.
            overall_status = VerificationStatus.PARTIALLY_VERIFIED
            t0, y0 = initial_condition
            ext_note = f" ({'; '.join(singular_ext_details_list)})" if singular_ext_details_list else ""
            overall_details = (
                f"Bài toán Cauchy tại {variable} = {t0} được kiểm chứng triệt tiêu phần dư và thỏa mãn điều kiện ban đầu trên nhánh xác định. "
                f"Các nhánh nghiệm khác độc lập và giữ hằng số tích phân tự do.{ext_note}"
            )
        elif any(st == VerificationStatus.FAILED for st in singular_ext_statuses):
            overall_status = VerificationStatus.FAILED
            overall_details = "Mâu thuẫn trong điều kiện nối nghiệm tại điểm kỳ dị: " + "; ".join(singular_ext_details_list)
        elif any(st == VerificationStatus.CONDITIONAL_EXTENSION for st in singular_ext_statuses):
            overall_status = VerificationStatus.PARTIALLY_VERIFIED
            overall_details = (
                "Các nhánh nghiệm thỏa mãn phần dư trên từng khoảng xác định. "
                "Khả năng mở rộng qua điểm kỳ dị đòi hỏi điều kiện ràng buộc giữa các hằng số tích phân (CONDITIONAL_EXTENSION): "
                + "; ".join(singular_ext_details_list)
            )
        elif is_ic_at_singular_point:
            # Cauchy initial condition was set at a singular point
            if singular_ext_statuses and all(st == VerificationStatus.C1_EXTENSION_VERIFIED for st in singular_ext_statuses) and all_verified:
                overall_status = VerificationStatus.C1_EXTENSION_VERIFIED
                overall_details = "Bài toán Cauchy tại điểm kỳ dị thỏa mãn nối trơn C1: " + "; ".join(singular_ext_details_list)
            elif singular_ext_statuses and all(st in (VerificationStatus.CONTINUITY_VERIFIED, VerificationStatus.C1_EXTENSION_VERIFIED) for st in singular_ext_statuses) and all_verified:
                overall_status = VerificationStatus.CONTINUITY_VERIFIED
                overall_details = "Bài toán Cauchy tại điểm kỳ dị thỏa mãn liên tục C0, chưa xác lập C1: " + "; ".join(singular_ext_details_list)
            else:
                overall_status = VerificationStatus.UNVERIFIED
                overall_details = (
                    "Bài toán Cauchy tại điểm kỳ dị thỏa mãn điều kiện đại số ban đầu nhưng điều kiện nối nghiệm giải tích chưa được chứng minh: "
                    + "; ".join(singular_ext_details_list)
                )
        elif singular_ext_statuses:
            if all(st == VerificationStatus.C1_EXTENSION_VERIFIED for st in singular_ext_statuses) and all_verified:
                overall_status = VerificationStatus.C1_EXTENSION_VERIFIED
                overall_details = "Tất cả các nhánh nghiệm và điểm kỳ dị đều được kiểm chứng nối trơn C1: " + "; ".join(singular_ext_details_list)
            elif all(st in (VerificationStatus.CONTINUITY_VERIFIED, VerificationStatus.C1_EXTENSION_VERIFIED) for st in singular_ext_statuses) and all_verified:
                overall_status = VerificationStatus.CONTINUITY_VERIFIED
                overall_details = "Kiểm chứng tính liên tục thành công trên toàn miền; đạo hàm cấp 1 chưa hoàn tất: " + "; ".join(singular_ext_details_list)
            else:
                overall_status = VerificationStatus.PARTIALLY_VERIFIED
                overall_details = (
                    f"Các nhánh nghiệm được kiểm chứng triệt tiêu phần dư độc lập ({VerificationStatus.VERIFIED_ON_BRANCH.value}), "
                    f"nhưng điều kiện mở rộng qua điểm kỳ dị chưa hoàn tất ({VerificationStatus.UNVERIFIED.value}): "
                    + "; ".join(singular_ext_details_list)
                )
        elif all_verified:
            overall_status = VerificationStatus.VERIFIED
            overall_details = (
                f"Tất cả {len(branches)} nhánh nghiệm đều được kiểm chứng độc lập triệt tiêu phần dư R({variable}) ≡ 0 "
                f"trên từng khoảng xác định."
            )
        else:
            overall_status = VerificationStatus.PARTIALLY_VERIFIED
            overall_details = (
                f"Các nhánh nghiệm đã được kiểm tra trên từng khoảng; một số nhánh ở trạng thái {VerificationStatus.UNVERIFIED.value}."
            )

        return (
            tuple(verified_branches),
            VerificationResult(
                status=overall_status,
                method="branch_aware_verification",
                details=overall_details,
            ),
        )

    @staticmethod
    def _strip_log_abs(expr: sp.Expr) -> sp.Expr:
        """Strip Abs inside log(Abs(u)) solely for smooth algebraic differentiation away from u = 0."""
        return expr.replace(
            lambda node: isinstance(node, sp.log) and bool(node.args) and isinstance(node.args[0], sp.Abs),
            lambda node: sp.log(node.args[0].args[0]),
        )

    @staticmethod
    def _validate_scalar_at_ic(
        val: sp.Expr,
        label: str,
        x0: sp.Expr,
        y0: sp.Expr,
        *,
        allow_complex: bool,
        integral_method: str,
    ) -> VerificationResult | None:
        """Fail closed if evaluating an expression at (x0, y0) yields an integral, singularity, non-real value, or unverified symbolic value."""
        if val.has(sp.Integral):
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method=integral_method,
                details=f"Không thể xác nhận giá trị {label} tại ({x0}, {y0}) do còn tích phân chưa tính.",
            )
        stat, reason = classify_scalar_real_finite(val, allow_complex=allow_complex)
        if stat == "invalid":
            if val.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or val.is_finite is False:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="initial_condition_out_of_domain",
                    details=f"Biểu thức {label} không xác định hữu hạn tại ({x0}, {y0}): {label} = {val}.",
                )
            return VerificationResult(
                status=VerificationStatus.FAILED,
                method="initial_condition_nonreal",
                details=f"Biểu thức {label} nhận giá trị phức trên tập thực tại ({x0}, {y0}): {label} = {val}.",
            )
        if stat == "unknown":
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="initial_condition_symbolic_unverified",
                details=f"Không thể xác nhận giá trị {label} tại ({x0}, {y0}) là số thực hữu hạn: {reason}",
            )
        return None

    def _check_differential_form_ic_domain(
        self,
        *,
        x_sym: sp.Symbol,
        y_sym: sp.Symbol,
        x0: sp.Expr,
        y0: sp.Expr,
        M_expr: sp.Expr,
        N_expr: sp.Expr,
        mu_expr: sp.Expr | None = None,
        source_constraints: tuple[Any, ...] = (),
        allow_complex: bool = False,
    ) -> VerificationResult | None:
        """Validate source constraints and differential coefficients at an initial point."""
        expr_checks: list[sp.Expr | None] = [None, M_expr, N_expr]
        if mu_expr is not None:
            expr_checks.append(mu_expr)
        unknown_result: VerificationResult | None = None
        for expr_target in expr_checks:
            dom_stat, dom_msg = evaluate_initial_point_domain(
                expr_target,
                x_sym,
                y_sym,
                x0,
                y0,
                source_constraints=source_constraints if expr_target is None else (),
                allow_complex=allow_complex,
            )
            if dom_stat == "invalid":
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="initial_condition_out_of_domain",
                    details=dom_msg,
                )
            if dom_stat == "unknown" and unknown_result is None:
                unknown_result = VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="initial_condition_domain_unverified",
                    details=dom_msg,
                )
        return unknown_result

    def verify_exact(
        self,
        potential_F: sp.Expr,
        M_expr: sp.Expr,
        N_expr: sp.Expr,
        x_sym: sp.Symbol,
        y_sym: sp.Symbol,
        initial_condition: tuple[sp.Expr, sp.Expr] | None = None,
        source_constraints: tuple[Any, ...] = (),
    ) -> VerificationResult:
        """Verify potential function F(x, y) for exact equation M dx + N dy = 0."""
        try:
            allow_complex = M_expr.has(sp.I) or N_expr.has(sp.I)
            if potential_F.has(sp.Integral, sp.exp_polar, sp.meijerg, sp.hyper) or (
                potential_F.has(sp.I) and not allow_complex
            ):
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="exact_potential_non_elementary_or_complex",
                    details="Hàm thế F(x, y) chứa tích phân chưa đánh giá hoặc nhánh phức không sơ cấp; chưa thể kiểm chứng giải tích.",
                )

            smooth_F = self._strip_log_abs(potential_F)
            dF_dx = sp.diff(smooth_F, x_sym)
            dF_dy = sp.diff(smooth_F, y_sym)
            diff_M = sp.simplify(dF_dx - M_expr)
            diff_N = sp.simplify(dF_dy - N_expr)

            zero_M = _prove_symbolic_zero(diff_M)
            zero_N = _prove_symbolic_zero(diff_N)

            if not zero_M or not zero_N:
                disc_m = _find_numerical_discrepancy(diff_M, x_sym, (y_sym,))
                disc_n = _find_numerical_discrepancy(diff_N, x_sym, (y_sym,))
                if disc_m is not None or disc_n is not None or diff_M.is_number or diff_N.is_number:
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="exact_potential_gradient_mismatch",
                        details="Hàm thế F(x, y) không thỏa mãn hệ thức ∇F = (M, N).",
                    )
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="exact_verification_inconclusive",
                    details="Không thể chứng minh ∇F = (M, N) bằng phương pháp ký hiệu.",
                )

            if initial_condition is not None:
                x0, y0 = initial_condition
                dom_err = self._check_differential_form_ic_domain(
                    x_sym=x_sym,
                    y_sym=y_sym,
                    x0=x0,
                    y0=y0,
                    M_expr=M_expr,
                    N_expr=N_expr,
                    source_constraints=source_constraints,
                    allow_complex=allow_complex,
                )
                if dom_err is not None:
                    return dom_err
                val_at_ic = sp.simplify(potential_F.subs([(x_sym, x0), (y_sym, y0)]))
                ic_err = self._validate_scalar_at_ic(
                    val_at_ic,
                    f"F({x_sym}, {y_sym})",
                    x0,
                    y0,
                    allow_complex=allow_complex,
                    integral_method="exact_ic_unanchored_integral",
                )
                if ic_err is not None:
                    return ic_err
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="exact_potential_gradient_and_ic_check",
                    details=f"Kiểm chứng thành công: ∇F = (M, N) và F({x0}, {y0}) = {val_at_ic}.",
                )

            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="exact_potential_gradient_check",
                details=f"Kiểm chứng thành công: Gradient của hàm thế ∇F = (∂F/∂{x_sym}, ∂F/∂{y_sym}) đồng nhất với (M, N).",
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
        domain_interval: tuple[sp.Expr | float, sp.Expr | float] | str | None = None,
        domain_restrictions: tuple[str, ...] = (),
    ) -> VerificationResult:
        """Verify implicit relation Phi(x, y) = C for dy/dx = f(x)*g(y).

        By implicit differentiation: dPhi/dx + (dPhi/dy)*y' = 0 => y' = -Phi_x / Phi_y.
        Residual: Phi_x + Phi_y * (f(x)*g(y)) == 0.
        Supports domain-aware verification and rigorous Cauchy IVP verification.
        """
        try:
            # Smooth differentiation: strip Abs inside logarithms to differentiate purely algebraically
            phi_smooth = potential_phi.replace(sp.Abs, lambda arg: arg)
            phi_x = sp.diff(phi_smooth, x_sym)
            phi_y = sp.diff(phi_smooth, y_sym)
            implicit_residual = sp.simplify(phi_x + phi_y * rhs_f_expr * rhs_g_expr)

            is_res_zero = _prove_symbolic_zero(
                implicit_residual,
                domain_interval=domain_interval,
                variable=x_sym,
            )
            if not is_res_zero:
                disc = _find_numerical_discrepancy(
                    implicit_residual,
                    x_sym,
                    (y_sym,),
                    domain_interval=domain_interval,
                    domain_restrictions=domain_restrictions,
                )
                if disc is not None or implicit_residual.is_number:
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="implicit_differential_mismatch",
                        details="Đạo hàm ẩn của hệ thức không thỏa mãn phương trình vi phân ban đầu.",
                    )
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="implicit_verification_inconclusive",
                    details="Không thể chứng minh hệ thức nghiệm ẩn bằng phương pháp ký hiệu.",
                )

            # Rigorous Initial-Condition Verification
            if initial_condition is not None:
                if c_val is None:
                    return VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="ic_constant_unspecified",
                        details="Không thể xác nhận bài toán giá trị ban đầu (IVP) vì hằng số tích phân C chưa được cung cấp để đối chiếu với điều kiện ban đầu.",
                    )

                x0, y0 = initial_condition
                val_at_ic = sp.simplify(potential_phi.subs([(x_sym, x0), (y_sym, y0)]))
                if val_at_ic.has(sp.nan) or val_at_ic.has(sp.zoo) or (sp.I in val_at_ic.atoms() and not c_val.has(sp.I)):
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="initial_condition_out_of_domain",
                        details=f"Hệ thức nghiệm ẩn không xác định trên tập số thực tại điều kiện ban đầu ({x0}, {y0}): nhận được {val_at_ic}.",
                    )

                ic_diff = sp.simplify(val_at_ic - c_val)
                if not _prove_symbolic_zero(ic_diff, domain_interval=domain_interval, variable=x_sym):
                    disc_ic = _find_numerical_discrepancy(
                        ic_diff,
                        x_sym,
                        domain_interval=domain_interval,
                        domain_restrictions=domain_restrictions,
                    )
                    if disc_ic is not None or ic_diff.is_number:
                        return VerificationResult(
                            status=VerificationStatus.FAILED,
                            method="initial_condition_mismatch",
                            details=f"Hệ thức nghiệm ẩn không thỏa mãn điều kiện ban đầu y({x0}) = {y0}: Φ({x0}, {y0}) = {val_at_ic} != C = {c_val}.",
                        )
                    return VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="ic_evaluation_failed",
                        details=f"Không thể xác nhận điều kiện ban đầu y({x0}) = {y0} cho nghiệm ẩn.",
                    )

                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="separable_implicit_derivation_verified_with_ic",
                    details=f"Kiểm chứng thành công: Đạo hàm ẩn d/dx[Φ(x, y)] thỏa mãn phương trình và điều kiện ban đầu y({x0}) = {y0} nghiệm đúng.",
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

    def verify_classical_homogeneous_implicit(
        self,
        potential_phi: sp.Expr,
        x_sym: sp.Symbol,
        y_sym: sp.Symbol,
        F_v_expr: sp.Expr,
        initial_condition: tuple[sp.Expr, sp.Expr] | None = None,
        c_val: sp.Expr | None = None,
        domain_interval: tuple[sp.Expr | float, sp.Expr | float] | str | None = None,
        domain_restrictions: tuple[str, ...] = (),
    ) -> VerificationResult:
        """Verify implicit relation Phi(x, y) = C for classical homogeneous ODE: y' = F(y/x).

        By implicit differentiation:
            dPhi/dx + (dPhi/dy) * y' = 0  =>  y' = -Phi_x / Phi_y.
        Residual against original ODE y' = F(y/x):
            Phi_x + Phi_y * F(y/x) == 0 (where Phi_y != 0 and x != 0).
        Verifies both residual identity on the stated domain and Cauchy IVP if provided.
        """
        try:
            # Smooth differentiation: strip Abs inside logarithms to differentiate algebraically
            phi_smooth = potential_phi.replace(sp.Abs, lambda arg: arg)
            phi_x = sp.diff(phi_smooth, x_sym)
            phi_y = sp.diff(phi_smooth, y_sym)

            # Check for degenerate implicit derivative (Phi_y identically zero)
            if _prove_symbolic_zero(phi_y, domain_interval=domain_interval, variable=x_sym):
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="implicit_derivative_degenerate",
                    details="Hệ thức ẩn suy biến: Đạo hàm riêng theo y triệt tiêu đồng nhất (Phi_y ≡ 0), không xác định được y là hàm của x.",
                )

            # Substitute v -> y / x in F(v)
            v_real = sp.Symbol("v", real=True)
            v_plain = sp.Symbol("v")
            v_ratio = sp.Symbol("_v_ratio", real=True)
            F_yx = F_v_expr.subs([(v_real, y_sym / x_sym), (v_plain, y_sym / x_sym), (v_ratio, y_sym / x_sym)])

            # Differentiate residual: d/dx[Phi(x, y(x))] = Phi_x + Phi_y * F(y/x)
            implicit_residual = sp.simplify(phi_x + phi_y * F_yx)

            is_res_zero = _prove_symbolic_zero(
                implicit_residual,
                domain_interval=domain_interval,
                variable=x_sym,
            )
            if not is_res_zero:
                disc = _find_numerical_discrepancy(
                    implicit_residual,
                    x_sym,
                    (y_sym,),
                    domain_interval=domain_interval,
                    domain_restrictions=domain_restrictions,
                )
                if disc is not None or implicit_residual.is_number:
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="classical_homogeneous_implicit_differential_mismatch",
                        details="Đạo hàm ẩn d/dx[Φ(x, y)] không thỏa mãn phương trình vi phân thuần nhất bậc 0: y' = F(y/x).",
                    )
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="classical_homogeneous_implicit_verification_inconclusive",
                    details="Không thể chứng minh hệ thức nghiệm ẩn bằng phương pháp ký hiệu.",
                )

            # Rigorous Initial-Condition Verification
            if initial_condition is not None:
                if c_val is None:
                    return VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="ic_constant_unspecified",
                        details="Không thể xác nhận bài toán Cauchy vì hằng số tích phân C chưa được cung cấp để đối chiếu với điều kiện ban đầu.",
                    )

                x0, y0 = initial_condition
                if _prove_symbolic_zero(x0):
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="initial_condition_singular_point",
                        details=f"Điểm ban đầu x0 = {x0} là điểm kỳ dị của phương trình thuần nhất cấp một.",
                    )

                # Check if Phi_y(x0, y0) == 0 (implicit function theorem fails at initial point)
                phi_y_at_ic = sp.simplify(phi_y.subs([(x_sym, x0), (y_sym, y0)]))
                if _prove_symbolic_zero(phi_y_at_ic):
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="implicit_singular_initial_point",
                        details=f"Tại điểm ban đầu ({x0}, {y0}), đạo hàm riêng Phi_y triệt tiêu, vi phạm điều kiện tồn tại hàm ẩn địa phương.",
                    )

                val_at_ic = sp.simplify(potential_phi.subs([(x_sym, x0), (y_sym, y0)]))
                if val_at_ic.has(sp.nan) or val_at_ic.has(sp.zoo) or (sp.I in val_at_ic.atoms() and not c_val.has(sp.I)):
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="initial_condition_out_of_domain",
                        details=f"Hệ thức nghiệm ẩn không xác định trên tập số thực tại điều kiện ban đầu ({x0}, {y0}): nhận được {val_at_ic}.",
                    )

                ic_diff = sp.simplify(val_at_ic - c_val)
                if not _prove_symbolic_zero(ic_diff, domain_interval=domain_interval, variable=x_sym):
                    disc_ic = _find_numerical_discrepancy(
                        ic_diff,
                        x_sym,
                        domain_interval=domain_interval,
                        domain_restrictions=domain_restrictions,
                    )
                    if disc_ic is not None or ic_diff.is_number:
                        return VerificationResult(
                            status=VerificationStatus.FAILED,
                            method="initial_condition_mismatch",
                            details=f"Hệ thức nghiệm ẩn không thỏa mãn điều kiện ban đầu y({x0}) = {y0}: Φ({x0}, {y0}) = {val_at_ic} != C = {c_val}.",
                        )
                    return VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="ic_evaluation_failed",
                        details=f"Không thể xác nhận điều kiện ban đầu y({x0}) = {y0} cho nghiệm ẩn.",
                    )

                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="classical_homogeneous_implicit_verified_with_ic",
                    details=f"Kiểm chứng thành công: Đạo hàm ẩn d/dx[Φ(x, y)] thỏa mãn phương trình y' = F(y/x) và điều kiện ban đầu y({x0}) = {y0} nghiệm đúng.",
                )

            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="classical_homogeneous_implicit_verified",
                details="Kiểm chứng thành công: Đạo hàm ẩn d/dx[Φ(x, y)] đồng nhất với phương trình vi phân thuần nhất bậc 0: y' = F(y/x).",
            )
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="classical_homogeneous_implicit_verification_failed",
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
        source_constraints: tuple[Any, ...] = (),
    ) -> VerificationResult:
        """Verify integrating factor mu and potential F for M dx + N dy = 0."""
        try:
            allow_complex = M_expr.has(sp.I) or N_expr.has(sp.I)
            if potential_F.has(sp.Integral, sp.exp_polar, sp.meijerg, sp.hyper) or (
                potential_F.has(sp.I) and not allow_complex
            ):
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="integrating_factor_non_elementary_or_complex",
                    details="Hàm thế F(x, y) chứa tích phân chưa đánh giá hoặc nhánh phức không sơ cấp; chưa thể kiểm chứng giải tích.",
                )

            smooth_mu = self._strip_log_abs(mu_expr)
            smooth_F = self._strip_log_abs(potential_F)

            M_transformed = sp.simplify(smooth_mu * M_expr)
            N_transformed = sp.simplify(smooth_mu * N_expr)

            # 1. Exactness check: d(mu*M)/dy == d(mu*N)/dx
            dM_dy = sp.diff(M_transformed, y_sym)
            dN_dx = sp.diff(N_transformed, x_sym)
            exact_diff = sp.simplify(dM_dy - dN_dx)
            if not _prove_symbolic_zero(exact_diff):
                disc_ex = _find_numerical_discrepancy(exact_diff, x_sym, (y_sym,))
                if disc_ex is not None or exact_diff.is_number:
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="integrating_factor_not_exact",
                        details="Thừa số tích phân μ không biến đổi phương trình thành vi phân toàn phần: ∂(μM)/∂y != ∂(μN)/∂x.",
                    )
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="integrating_factor_exactness_inconclusive",
                    details="Không thể chứng minh phương trình biến đổi là vi phân toàn phần bằng phương pháp ký hiệu.",
                )

            # 2. Gradient check: grad(F) == (mu*M, mu*N)
            dF_dx = sp.diff(smooth_F, x_sym)
            dF_dy = sp.diff(smooth_F, y_sym)
            diff_M = sp.simplify(dF_dx - M_transformed)
            diff_N = sp.simplify(dF_dy - N_transformed)

            if not _prove_symbolic_zero(diff_M) or not _prove_symbolic_zero(diff_N):
                disc_m = _find_numerical_discrepancy(diff_M, x_sym, (y_sym,))
                disc_n = _find_numerical_discrepancy(diff_N, x_sym, (y_sym,))
                if disc_m is not None or disc_n is not None or diff_M.is_number or diff_N.is_number:
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="integrating_factor_gradient_mismatch",
                        details="Hàm thế F(x, y) không thỏa mãn ∇F = (μM, μN).",
                    )
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="integrating_factor_gradient_inconclusive",
                    details="Không thể chứng minh ∇F = (μM, μN) bằng phương pháp ký hiệu.",
                )

            if initial_condition is not None:
                x0, y0 = initial_condition
                dom_err = self._check_differential_form_ic_domain(
                    x_sym=x_sym,
                    y_sym=y_sym,
                    x0=x0,
                    y0=y0,
                    M_expr=M_expr,
                    N_expr=N_expr,
                    mu_expr=mu_expr,
                    source_constraints=source_constraints,
                    allow_complex=allow_complex,
                )
                if dom_err is not None:
                    return dom_err
                mu_at_ic = sp.simplify(mu_expr.subs([(x_sym, x0), (y_sym, y0)]))
                if _prove_symbolic_zero(mu_at_ic):
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="integrating_factor_singular_at_ic",
                        details=f"Thừa số tích phân μ triệt tiêu tại điều kiện ban đầu ({x0}, {y0}): μ = 0.",
                    )
                mu_err = self._validate_scalar_at_ic(
                    mu_at_ic,
                    "μ",
                    x0,
                    y0,
                    allow_complex=allow_complex,
                    integral_method="integrating_factor_unanchored_integral",
                )
                if mu_err is not None:
                    return VerificationResult(
                        status=mu_err.status,
                        method="integrating_factor_singular_at_ic",
                        details=mu_err.details,
                    )

                val_at_ic = sp.simplify(potential_F.subs([(x_sym, x0), (y_sym, y0)]))
                ic_err = self._validate_scalar_at_ic(
                    val_at_ic,
                    f"F({x_sym}, {y_sym})",
                    x0,
                    y0,
                    allow_complex=allow_complex,
                    integral_method="integrating_factor_ic_unanchored_integral",
                )
                if ic_err is not None:
                    return ic_err
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

    def verify_fundamental_system(
        self,
        y1: sp.Expr,
        y2: sp.Expr,
        variable: sp.Symbol,
        domain_interval: tuple[sp.Expr | float, sp.Expr | float] | sp.Interval | str | None = None,
        *,
        left_open: bool = True,
        right_open: bool = True,
    ) -> tuple[sp.Expr, VerificationResult]:
        """Symbolically verify linear independence of fundamental solutions (W != 0) on the interval."""
        iv_set: sp.Interval | None = None
        if isinstance(domain_interval, sp.Interval):
            iv_set = domain_interval
        elif isinstance(domain_interval, (tuple, list)) and len(domain_interval) == 2:
            low, high = domain_interval
            if low is not None and high is not None:
                try:
                    low_e = sp.sympify(low)
                    high_e = sp.sympify(high)
                    iv_set = sp.Interval(
                        low_e,
                        high_e,
                        left_open=bool(left_open or low_e == -sp.oo),
                        right_open=bool(right_open or high_e == sp.oo),
                    )
                except Exception:
                    iv_set = None
        elif isinstance(domain_interval, str) and domain_interval.strip():
            try:
                from math_app.input.ode_parser import parse_interval_constraint

                parsed_iv = parse_interval_constraint(domain_interval, variable=variable.name)
                if parsed_iv.is_supported and parsed_iv.interval is not None:
                    iv_set = parsed_iv.interval
            except Exception:
                iv_set = None

        if iv_set is not None:
            if iv_set.start.is_nonnegative is True and iv_set.contains(sp.Integer(0)) is sp.S.false:
                v_dom = sp.Symbol(variable.name, positive=True)
            elif iv_set.end.is_nonpositive is True and iv_set.contains(sp.Integer(0)) is sp.S.false:
                v_dom = sp.Symbol(variable.name, negative=True)
            else:
                v_dom = sp.Symbol(variable.name, real=True)
        else:
            v_dom = variable if variable.is_real is True else sp.Symbol(variable.name, real=True)

        try:
            y1_d = y1.subs(variable, v_dom) if v_dom != variable else y1
            y2_d = y2.subs(variable, v_dom) if v_dom != variable else y2
            dy1_d = sp.diff(y1_d, v_dom)
            dy2_d = sp.diff(y2_d, v_dom)
            w_raw_d = y1_d * dy2_d - dy1_d * y2_d
            w_dom = sp.simplify(sp.trigsimp(sp.simplify(w_raw_d)))
            w_expr = w_dom.subs(v_dom, variable) if v_dom != variable else w_dom
        except Exception as exc:
            return sp.Integer(0), VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="fundamental_system_wronskian_unverified",
                details=f"Không thể tính toán và kiểm chứng định thức Wronskian W(y1, y2): {exc}",
            )

        if _prove_symbolic_zero(w_dom, domain_interval=domain_interval, variable=v_dom):
            return sp.Integer(0), VerificationResult(
                status=VerificationStatus.FAILED,
                method="fundamental_system_wronskian_zero",
                details=f"Hai nghiệm cơ bản không độc lập tuyến tính: định thức Wronskian W(y1, y2) ≡ 0 trên {variable}.",
            )

        if w_dom.has(sp.zoo, sp.nan, sp.oo, -sp.oo, sp.AccumBounds) or w_dom.is_finite is False:
            return w_expr, VerificationResult(
                status=VerificationStatus.FAILED,
                method="fundamental_system_wronskian_nonfinite",
                details=f"Định thức Wronskian W(y1, y2) = {w_expr} không hữu hạn trên miền xác định.",
            )

        if w_dom.has(sp.I) or w_dom.is_real is False:
            return w_expr, VerificationResult(
                status=VerificationStatus.FAILED,
                method="fundamental_system_wronskian_nonreal",
                details=f"Định thức Wronskian W(y1, y2) = {w_expr} chứa thành phần không thực trên miền xác định.",
            )

        extra_syms = w_dom.free_symbols - {v_dom}
        if extra_syms:
            return w_expr, VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="fundamental_system_wronskian_unverified",
                details=f"Không thể xác nhận W(y1, y2) = {w_expr} khác 0 do chứa tham số chưa xác định {tuple(extra_syms)}.",
            )

        if w_dom.is_real is not True or w_dom.is_finite is not True:
            return w_expr, VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="fundamental_system_wronskian_unverified",
                details=f"Không thể chứng minh tính thực hữu hạn của W(y1, y2) = {w_expr} bằng phương pháp ký hiệu.",
            )

        if iv_set is not None:
            try:
                _, w_den = sp.together(w_dom).as_numer_denom()
                if w_den != 1 and v_dom in w_den.free_symbols:
                    den_zeros = sp.solveset(w_den, v_dom, domain=iv_set)
                    if den_zeros.has(sp.ConditionSet):
                        return w_expr, VerificationResult(
                            status=VerificationStatus.UNVERIFIED,
                            method="fundamental_system_wronskian_unverified",
                            details=f"Không thể kiểm tra đầy đủ mẫu số của W(y1, y2) = {w_expr} trên khoảng {iv_set}.",
                        )
                    if den_zeros != sp.S.EmptySet:
                        return w_expr, VerificationResult(
                            status=VerificationStatus.FAILED,
                            method="fundamental_system_wronskian_undefined_on_interval",
                            details=f"Định thức Wronskian W(y1, y2) = {w_expr} không xác định tại {den_zeros} thuộc khoảng {iv_set}.",
                        )
            except Exception as exc:
                return w_expr, VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="fundamental_system_wronskian_unverified",
                    details=f"Không thể kiểm tra cực điểm của Wronskian W(y1, y2) = {w_expr}: {exc}",
                )

        if w_dom.is_nonzero is True or w_dom.is_positive is True or w_dom.is_negative is True:
            return w_expr, VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="fundamental_system_wronskian_verified",
                details=f"Định thức Wronskian W(y1, y2) = {w_expr} được chứng minh khác 0 trên toàn khoảng liên thông.",
            )

        if iv_set is not None:
            try:
                w_zeros = sp.solveset(w_dom, v_dom, domain=iv_set)
                if w_zeros.has(sp.ConditionSet):
                    return w_expr, VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="fundamental_system_wronskian_unverified",
                        details=f"Không thể loại trừ nghiệm triệt tiêu của W(y1, y2) = {w_expr} trên {iv_set}.",
                    )
                if w_zeros != sp.S.EmptySet:
                    return w_expr, VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="fundamental_system_wronskian_vanishes_on_interval",
                        details=f"Định thức Wronskian W(y1, y2) = {w_expr} triệt tiêu tại {w_zeros} trên khoảng {iv_set}.",
                    )
                return w_expr, VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="fundamental_system_wronskian_verified",
                    details=f"Định thức Wronskian W(y1, y2) = {w_expr} được chứng minh khác 0 trên khoảng {iv_set}.",
                )
            except Exception as exc:
                return w_expr, VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="fundamental_system_wronskian_unverified",
                    details=f"Không thể kiểm chứng tính khác 0 của Wronskian W(y1, y2) = {w_expr}: {exc}",
                )

        return w_expr, VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="fundamental_system_wronskian_unverified",
            details=f"Không thể chứng minh W(y1, y2) = {w_expr} khác 0 trên khoảng xác định.",
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
        forcing_expr: sp.Expr | None = None,
        domain_interval: tuple[sp.Expr | float, sp.Expr | float] | str | None = None,
        domain_restrictions: tuple[str, ...] = (),
        fundamental_solutions: tuple[sp.Expr, sp.Expr] | None = None,
        left_open: bool = True,
        right_open: bool = True,
    ) -> VerificationResult:
        """Verify a second-order ODE solution against a*y'' + b*y' + c*y - g(t) = 0 and optional IVPs."""
        allow_complex = any(
            expr is not None and expr.has(sp.I)
            for expr in (
                a_coeff,
                b_coeff,
                c_coeff,
                forcing_expr,
                *(initial_condition or ()),
                *(initial_derivative or ()),
            )
        )
        if solution.has(sp.I) and not allow_complex:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                method="second_order_nonreal_solution",
                details=f"Nghiệm y({variable}) = {solution} chứa đơn vị ảo i dù phương trình và điều kiện ban đầu thuần thực.",
            )
        try:
            dy = sp.diff(solution, variable)
            d2y = sp.diff(dy, variable)
            ode_lhs = a_coeff * d2y + b_coeff * dy + c_coeff * solution
            if forcing_expr is not None:
                ode_lhs = ode_lhs - forcing_expr
            residual = sp.simplify(ode_lhs)
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="residual_computation_failed",
                details=f"Không thể tính toán biểu thức dư cấp hai R(t): {exc}",
            )

        # Identify integration constants
        consts: list[sp.Symbol] = []
        if c1_sym is not None:
            consts.append(c1_sym)
        if c2_sym is not None:
            consts.append(c2_sym)
        for sym in solution.free_symbols:
            if sym != variable and re.match(r"^C\d*$", sym.name) and sym not in consts:
                consts.append(sym)

        # 1. Rigorous symbolic verification of residual (domain-aware)
        is_residual_zero = _prove_symbolic_zero(
            residual,
            tuple(consts),
            domain_interval=domain_interval,
            variable=variable,
        )

        # 2. If symbolic is inconclusive, search for counterexamples via numerical probes
        if not is_residual_zero:
            discrepancy = _find_numerical_discrepancy(
                residual,
                variable,
                tuple(consts),
                domain_interval=domain_interval,
                domain_restrictions=domain_restrictions,
                probe_points=self.SAMPLE_PROBE_POINTS,
            )
            if discrepancy is not None:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="numerical_residual_discrepancy",
                    details=f"Sai số dư cấp hai tại điểm thử nghiệm (sai số: {discrepancy:.6e}). Nghiệm không thỏa mãn phương trình.",
                )
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="inconclusive",
                details="Biểu thức dư cấp hai R(t) = a*y'' + b*y' + c*y - g(t) không thể rút gọn thành 0 bằng phương pháp ký hiệu (Inconclusive).",
            )

        # 3. Check initial conditions if provided
        if initial_condition is not None:
            t0, y0 = initial_condition
            try:
                val_y = sp.simplify(solution.subs(variable, t0))
                diff_y = sp.simplify(val_y - y0)
                if not _prove_symbolic_zero(
                    diff_y, tuple(consts), domain_interval=domain_interval, variable=variable
                ):
                    disc_y = _find_numerical_discrepancy(
                        diff_y,
                        variable,
                        tuple(consts),
                        domain_interval=domain_interval,
                        domain_restrictions=domain_restrictions,
                    )
                    if disc_y is not None or diff_y.is_number:
                        return VerificationResult(
                            status=VerificationStatus.FAILED,
                            method="initial_condition_mismatch",
                            details=f"Nghiệm không thỏa mãn điều kiện ban đầu y({t0}): nhận được {val_y}, kỳ vọng {y0}.",
                        )
                    return VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="ic_evaluation_failed",
                        details=f"Không thể xác nhận điều kiện ban đầu y({t0}) = {y0} bằng phương pháp ký hiệu.",
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
                if not _prove_symbolic_zero(
                    diff_yp, tuple(consts), domain_interval=domain_interval, variable=variable
                ):
                    disc_yp = _find_numerical_discrepancy(
                        diff_yp,
                        variable,
                        tuple(consts),
                        domain_interval=domain_interval,
                        domain_restrictions=domain_restrictions,
                    )
                    if disc_yp is not None or diff_yp.is_number:
                        return VerificationResult(
                            status=VerificationStatus.FAILED,
                            method="initial_derivative_mismatch",
                            details=f"Nghiệm không thỏa mãn điều kiện đạo hàm ban đầu y'({t0_v}): nhận được {val_yp}, kỳ vọng {v0}.",
                        )
                    return VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="ic_deriv_evaluation_failed",
                        details=f"Không thể xác nhận điều kiện đạo hàm ban đầu y'({t0_v}) = {v0} bằng phương pháp ký hiệu.",
                    )
            except Exception as exc:
                return VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="ic_deriv_evaluation_failed",
                    details=f"Không thể kiểm tra điều kiện đạo hàm ban đầu y'(t0): {exc}",
                )

        wronskian_suffix = ""
        if fundamental_solutions is not None:
            w_val, w_res = self.verify_fundamental_system(
                fundamental_solutions[0],
                fundamental_solutions[1],
                variable,
                domain_interval=domain_interval,
                left_open=left_open,
                right_open=right_open,
            )
            if w_res.status != VerificationStatus.VERIFIED:
                return w_res
            wronskian_suffix = f" Hệ nghiệm cơ bản độc lập tuyến tính với W(y1, y2) = {w_val} ≠ 0."

        if initial_condition is not None and initial_derivative is not None:
            t0, y0 = initial_condition
            _, v0 = initial_derivative
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="second_order_ode_residual_and_dual_ic_zero_check",
                details=f"Kiểm chứng độc lập thành công: Biểu thức dư R({variable}) ≡ 0 và hệ điều kiện Cauchy y({t0}) = {y0}, y'({t0}) = {v0} nghiệm đúng.{wronskian_suffix}",
            )

        if initial_condition is not None:
            t0, y0 = initial_condition
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="second_order_ode_residual_and_ic_zero_check",
                details=f"Kiểm chứng độc lập thành công: Biểu thức dư R({variable}) ≡ 0 và điều kiện ban đầu y({t0}) = {y0} nghiệm đúng.{wronskian_suffix}",
            )

        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            method="second_order_ode_residual_zero_check",
            details=f"Kiểm chứng độc lập thành công: Biểu thức dư R({variable}) = a*y'' + b*y' + c*y ≡ 0.{wronskian_suffix}",
        )

    def verify_wronskian(
        self,
        y1: sp.Expr,
        y2: sp.Expr,
        variable: sp.Symbol,
        ode_coeffs: tuple[sp.Expr, sp.Expr, sp.Expr] | None = None,
        domain_interval: tuple[sp.Expr | float, sp.Expr | float] | str | None = None,
    ) -> tuple[sp.Expr, VerificationResult]:
        """Compute and verify Wronskian W(y1, y2) = y1*y2' - y1'*y2."""
        try:
            real_var = variable if variable.is_real else sp.Symbol(variable.name, real=True)
            y1_r = y1.subs(variable, real_var) if real_var != variable else y1
            y2_r = y2.subs(variable, real_var) if real_var != variable else y2
            dy1 = sp.diff(y1_r, real_var)
            dy2 = sp.diff(y2_r, real_var)
            w_raw_r = y1_r * dy2 - dy1 * y2_r
            if _prove_symbolic_zero(w_raw_r, domain_interval=domain_interval, variable=real_var):
                w_expr = sp.Integer(0)
            else:
                w_simp_r = sp.simplify(sp.trigsimp(sp.simplify(w_raw_r)))
                if w_simp_r != 0 and w_simp_r.has(sp.Abs, sp.sign):
                    w_pw = sp.simplify(w_simp_r.rewrite(sp.Piecewise))
                    if _prove_symbolic_zero(w_pw, domain_interval=domain_interval, variable=real_var):
                        w_simp_r = sp.Integer(0)
                w_expr = w_simp_r.subs(real_var, variable) if real_var != variable else w_simp_r
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

            # Check if domain_interval is disconnected
            is_disconnected = False
            if isinstance(domain_interval, str):
                d_str = domain_interval.lower()
                if "u" in d_str or "union" in d_str or "!=" in d_str or "/=" in d_str or "khac" in d_str:
                    is_disconnected = True

            # Check whether a(t) vanishes on the domain interval
            a_has_zeros = False
            if a_c.has(variable):
                try:
                    zeros = sp.solve(a_c, variable)
                    real_zeros = [z for z in zeros if z.is_real]
                    if real_zeros:
                        if domain_interval is None or is_disconnected:
                            a_has_zeros = True
                        elif isinstance(domain_interval, (tuple, list)) and len(domain_interval) == 2:
                            low, high = domain_interval
                            low_f = float(sp.N(low)) if low != -sp.oo and low is not None else -math.inf
                            high_f = float(sp.N(high)) if high != sp.oo and high is not None else math.inf
                            for z in real_zeros:
                                try:
                                    zf = float(sp.N(z))
                                    if low_f <= zf <= high_f:
                                        a_has_zeros = True
                                        break
                                except Exception:
                                    a_has_zeros = True
                                    break
                        elif isinstance(domain_interval, str):
                            a_has_zeros = True
                except Exception:
                    pass

            if is_disconnected or a_has_zeros:
                return w_expr, VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="abel_theorem_condition_violated",
                    details="Định lý Abel không áp dụng trên miền chứa điểm kỳ dị của hệ số dẫn a(t) = 0 hoặc miền không liên thông (Abel's theorem requires continuous coefficients on a connected interval).",
                )

            res_y1 = self.verify_second_order(y1, variable, a_c, b_c, c_c, domain_interval=domain_interval)
            res_y2 = self.verify_second_order(y2, variable, a_c, b_c, c_c, domain_interval=domain_interval)
            if res_y1.status == VerificationStatus.VERIFIED and res_y2.status == VerificationStatus.VERIFIED:
                return w_expr, VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="wronskian_zero_ode_solutions_dependent_verified",
                    details="Kiểm chứng thành công: Cả hai hàm số đều là nghiệm của cùng một phương trình vi phân tuyến tính cấp hai có hệ số liên tục và W(y1, y2) ≡ 0; hai nghiệm phụ thuộc tuyến tính theo định lý Abel.",
                )

        # For arbitrary functions without a verified common ODE context, W == 0 is inconclusive (Peano counterexample)
        return w_expr, VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            method="wronskian_zero_inconclusive_arbitrary_functions",
            details="Wronskian triệt tiêu nhưng hai hàm số khả vi bất kỳ chưa chắc phụ thuộc tuyến tính trên toàn miền (phản ví dụ Peano: t^2 và t|t| trên R có W ≡ 0 nhưng độc lập tuyến tính).",
        )

    def verify_reduction_of_order(
        self,
        y1: sp.Expr,
        y2: sp.Expr,
        variable: sp.Symbol,
        a_coeff: sp.Expr,
        b_coeff: sp.Expr,
        c_coeff: sp.Expr,
        forcing_expr: sp.Expr | None = None,
        domain_interval: tuple[sp.Expr | float, sp.Expr | float] | str | None = None,
        domain_restrictions: tuple[str, ...] = (),
    ) -> VerificationResult:
        """Verify both fundamental solutions and Wronskian independence for Reduction of Order."""
        # Check homogeneity
        if forcing_expr is not None and not _prove_symbolic_zero(forcing_expr):
            return VerificationResult(
                status=VerificationStatus.FAILED,
                method="reduction_of_order_nonhomogeneous_rejected",
                details="Phương pháp hạ bậc chỉ áp dụng cho phương trình vi phân tuyến tính thuần nhất (Nonhomogeneous equation rejected).",
            )

        # 1. Verify y1 satisfies ODE
        res_y1 = self.verify_second_order(
            y1,
            variable,
            a_coeff,
            b_coeff,
            c_coeff,
            domain_interval=domain_interval,
            domain_restrictions=domain_restrictions,
        )
        if res_y1.status == VerificationStatus.FAILED:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                method="reduction_of_order_y1_residual_mismatch",
                details=f"Nghiệm thứ nhất y1 không thỏa mãn phương trình: {res_y1.details}",
            )
        if res_y1.status == VerificationStatus.UNVERIFIED:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="reduction_of_order_y1_unverified",
                details=f"Không thể chứng minh nghiệm thứ nhất y1 thỏa mãn phương trình: {res_y1.details}",
            )

        # 2. Verify y2 satisfies ODE
        res_y2 = self.verify_second_order(
            y2,
            variable,
            a_coeff,
            b_coeff,
            c_coeff,
            domain_interval=domain_interval,
            domain_restrictions=domain_restrictions,
        )
        if res_y2.status == VerificationStatus.FAILED:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                method="reduction_of_order_y2_residual_mismatch",
                details=f"Nghiệm thứ hai y2 tìm được không thỏa mãn phương trình: {res_y2.details}",
            )
        if res_y2.status == VerificationStatus.UNVERIFIED:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="reduction_of_order_y2_unverified",
                details=f"Không thể chứng minh nghiệm thứ hai y2 thỏa mãn phương trình: {res_y2.details}",
            )

        # 3. Verify Wronskian independence
        w_val, res_w = self.verify_wronskian(
            y1,
            y2,
            variable,
            ode_coeffs=(a_coeff, b_coeff, c_coeff),
            domain_interval=domain_interval,
        )
        if res_w.status != VerificationStatus.VERIFIED or w_val == 0:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                method="reduction_of_order_wronskian_failure",
                details=f"Kiểm tra độc lập tuyến tính qua Wronskian thất bại: W(y1, y2) = {w_val}.",
            )

        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            method="reduction_of_order_full_verification",
            details="Kiểm chứng thành công: Cả hai nghiệm y1 và y2 đều thỏa mãn phương trình vi phân và Wronskian khác 0 (độc lập tuyến tính).",
        )

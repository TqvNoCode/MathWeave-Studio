"""Generic mathematical domain and singular-point analysis engine for Ordinary Differential Equations.

Derives exact domains and connected solution intervals directly from symbolic ASTs:
1. Denominator exclusions and poles (rational roots).
2. Natural logarithm and general log arguments (u(t) > 0).
3. Even roots and fractional powers with even denominators (u(t) >= 0).
4. Negative power poles (u(t) != 0).
5. Leading coefficient singular points (a_n(t) = 0).
6. Separates Original Equation Domain (D_orig) from Normalized Equation Domain (D_norm).
7. Derives maximal connected solution intervals (I_1, I_2, ...).
8. Analyzes singular-point value and derivative extension conditions at points where a_n(t) = 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import sympy as sp

from math_app.domain.models import DomainCompleteness, VerificationStatus
from math_app.rendering.latex.formatter import expr_to_latex


@dataclass(frozen=True)
class SingularPointAnalysis:
    """Mathematical analysis of a singular point introduced by ODE normalization."""

    point: sp.Expr
    point_str: str
    original_eq_valid: bool
    value_at_point: sp.Expr | None = None
    derivative_at_point: sp.Expr | None = None
    extension_status: VerificationStatus = VerificationStatus.UNVERIFIED
    details: str = ""
    latex_summary: str = ""

    @property
    def y_singular(self) -> sp.Expr | None:
        return self.value_at_point

    @property
    def yp_singular(self) -> sp.Expr | None:
        return self.derivative_at_point


@dataclass(frozen=True)
class DomainAnalysisResult:
    """Authoritative structured outcome of generic ODE domain and singular-point analysis."""

    original_domain: sp.Set
    normalized_domain: sp.Set
    connected_intervals: tuple[sp.Interval, ...]
    singular_points: tuple[sp.Expr, ...]
    denominator_zeros: tuple[sp.Expr, ...]
    original_domain_latex: str
    normalized_domain_latex: str
    domain_restrictions: tuple[str, ...]
    singular_point_analyses: tuple[SingularPointAnalysis, ...] = field(default_factory=tuple)
    is_disconnected: bool = False
    completeness: DomainCompleteness = DomainCompleteness.EXACT
    isolated_points: tuple[sp.Expr, ...] = field(default_factory=tuple)
    other_components: tuple[sp.Set, ...] = field(default_factory=tuple)


def _decompose_set_components(s: sp.Set) -> tuple[list[sp.Interval], list[sp.Expr], list[sp.Set]]:
    """Extract (intervals, isolated_points, other_components) from a SymPy set."""
    if s == sp.S.Reals:
        return [sp.Interval.open(-sp.oo, sp.oo)], [], []
    if s == sp.S.EmptySet:
        return [], [], []
    if isinstance(s, sp.Interval):
        if s.start == s.end:
            return [], [s.start], []
        return [s], [], []
    if isinstance(s, sp.FiniteSet):
        return [], list(s.args), []
    if isinstance(s, sp.Union):
        intervals: list[sp.Interval] = []
        isolated: list[sp.Expr] = []
        other: list[sp.Set] = []
        for arg in s.args:
            sub_ivs, sub_pts, sub_oth = _decompose_set_components(arg)
            intervals.extend(sub_ivs)
            isolated.extend(sub_pts)
            other.extend(sub_oth)

        def _sort_key(iv: sp.Interval) -> float:
            if iv.start == -sp.oo:
                return -1e12
            try:
                return float(sp.N(iv.start))
            except Exception:
                return 0.0

        intervals.sort(key=_sort_key)
        return intervals, isolated, other
    return [], [], [s]


def _set_to_intervals(s: sp.Set) -> list[sp.Interval]:
    """Extract ordered list of disjoint maximal connected intervals from a SymPy set."""
    intervals, _, _ = _decompose_set_components(s)
    return intervals


def format_interval_latex(*args: Any) -> str:
    """Format a SymPy Interval, a tuple (start, end), or (start, end) into standard academic LaTeX interval notation."""
    if len(args) == 2:
        start_val, end_val = args[0], args[1]
        left_open, right_open = True, True
    elif len(args) == 1:
        iv = args[0]
        if isinstance(iv, (tuple, list)) and len(iv) == 2:
            start_val, end_val = iv
            left_open, right_open = True, True
        else:
            start_val, end_val = iv.start, iv.end
            left_open, right_open = iv.left_open, iv.right_open
    else:
        raise ValueError("format_interval_latex expects 1 or 2 arguments")

    start_str = "-\\infty" if start_val == -sp.oo else expr_to_latex(start_val)
    end_str = "+\\infty" if end_val == sp.oo else expr_to_latex(end_val)
    left_bracket = "(" if left_open else "["
    right_bracket = ")" if right_open else "]"
    return f"{left_bracket}{start_str}, {end_str}{right_bracket}"


def format_set_latex(s: sp.Set, var_name: str = "t") -> str:
    """Format a generic SymPy real set into academic LaTeX notation."""
    if s == sp.S.Reals:
        return r"\mathbb{R}"
    if s == sp.S.EmptySet:
        return r"\emptyset"

    # FiniteSet: {a, b, c}
    if isinstance(s, sp.FiniteSet):
        def _sort_pt(p: Any) -> float:
            try:
                return float(sp.N(p))
            except Exception:
                return 0.0

        pts = sorted(s.args, key=_sort_pt)
        pts_str = ", ".join(expr_to_latex(p) for p in pts)
        return rf"\{{{pts_str}\}}"

    # Explicit Complement: A \ B
    if isinstance(s, sp.Complement):
        if s.args[0] == sp.S.Reals:
            if isinstance(s.args[1], sp.FiniteSet):
                pts = sorted(
                    s.args[1].args,
                    key=lambda p: float(sp.N(p)) if (p.is_number or getattr(p, "is_real", False)) else 0.0,
                )
                pts_str = ", ".join(expr_to_latex(p) for p in pts)
                return rf"\mathbb{{R}} \setminus \{{{pts_str}\}}"
            return rf"\mathbb{{R}} \setminus {format_set_latex(s.args[1], var_name)}"
        return rf"{format_set_latex(s.args[0], var_name)} \setminus {format_set_latex(s.args[1], var_name)}"

    # Single Interval
    if isinstance(s, sp.Interval):
        if s.start == -sp.oo and s.end == sp.oo:
            return r"\mathbb{R}"
        return format_interval_latex(s)

    # Union of sets
    if isinstance(s, sp.Union):
        # If all args are Intervals, format intervals or R \ {pts}
        all_intervals = all(isinstance(arg, sp.Interval) for arg in s.args)
        if all_intervals:
            intervals = _set_to_intervals(s)
            if (
                len(intervals) > 1
                and intervals[0].start == -sp.oo
                and intervals[-1].end == sp.oo
                and all(iv.left_open and iv.right_open for iv in intervals)
                and all(intervals[i].end == intervals[i + 1].start for i in range(len(intervals) - 1))
            ):
                excluded = [intervals[i].end for i in range(len(intervals) - 1)]
                pts_str = ", ".join(expr_to_latex(p) for p in excluded)
                return rf"\mathbb{{R}} \setminus \{{{pts_str}\}}"

            if len(intervals) == 1:
                iv = intervals[0]
                if iv.start == -sp.oo and iv.end == sp.oo:
                    return r"\mathbb{R}"
                return format_interval_latex(iv)

            return r" \cup ".join(format_interval_latex(iv) for iv in intervals)

        # Mixed sets: format each component, preserving FiniteSets, Intervals, Complements, etc.
        parts = [format_set_latex(arg, var_name) for arg in s.args]
        return r" \cup ".join(p for p in parts if p and p != r"\emptyset")

    intervals = _set_to_intervals(s)

    if intervals:
        # Check if intervals represent R \ {p1, p2, ...}
        if (
            len(intervals) > 1
            and intervals[0].start == -sp.oo
            and intervals[-1].end == sp.oo
            and all(iv.left_open and iv.right_open for iv in intervals)
            and all(intervals[i].end == intervals[i + 1].start for i in range(len(intervals) - 1))
        ):
            excluded = [intervals[i].end for i in range(len(intervals) - 1)]
            pts_str = ", ".join(expr_to_latex(p) for p in excluded)
            return rf"\mathbb{{R}} \setminus \{{{pts_str}\}}"

        if len(intervals) == 1:
            iv = intervals[0]
            if iv.start == -sp.oo and iv.end == sp.oo:
                return r"\mathbb{R}"
            return format_interval_latex(iv)

        return r" \cup ".join(format_interval_latex(iv) for iv in intervals)

    if isinstance(s, sp.Intersection):
        parts = [format_set_latex(arg, var_name) for arg in s.args]
        return r" \cap ".join(p for p in parts if p)

    # Fallback to symbolic expression rendering, NEVER defaulting to \mathbb{R}
    try:
        return expr_to_latex(s.as_expr()) if hasattr(s, "as_expr") else expr_to_latex(s)
    except Exception:
        return str(s)


def extract_expression_domain_with_completeness(
    expr: sp.Expr, var: sp.Symbol
) -> tuple[sp.Set, DomainCompleteness]:
    """Derive the maximal real domain where an expression is algebraically and analytically defined,
    along with a mathematical completeness flag."""
    domain: sp.Set = sp.S.Reals
    completeness = DomainCompleteness.EXACT

    if expr is None or not expr.has(var):
        return domain, completeness

    # Track processed denominators to prevent nested Complement hangs on infinite ImageSets
    processed_denoms: set[sp.Expr] = set()

    def _handle_denominator(
        denom_expr: sp.Expr, cur_domain: sp.Set, cur_completeness: DomainCompleteness
    ) -> tuple[sp.Set, DomainCompleteness]:
        if denom_expr == 1 or var not in denom_expr.free_symbols or denom_expr in processed_denoms:
            return cur_domain, cur_completeness
        processed_denoms.add(denom_expr)

        trig_handled = False
        if denom_expr.has(sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc):
            try:
                trig_zeros = sp.solveset(denom_expr, var, domain=sp.S.Reals)
                if isinstance(trig_zeros, sp.ConditionSet):
                    d_roots = sp.solve(sp.Eq(denom_expr, 0), var)
                    real_d_roots = [r for r in d_roots if r.is_real or (r.is_number and r.as_real_imag()[1] == 0)]
                    if real_d_roots:
                        cur_domain = sp.Complement(cur_domain, sp.FiniteSet(*real_d_roots))
                        cur_completeness = DomainCompleteness.PARTIAL
                    else:
                        cur_completeness = DomainCompleteness.UNKNOWN
                    trig_handled = True
                elif trig_zeros != sp.S.EmptySet:
                    cur_domain = sp.Complement(cur_domain, trig_zeros)
                    trig_handled = True
                elif trig_zeros == sp.S.EmptySet:
                    trig_handled = True
            except Exception:
                pass

        if not trig_handled:
            try:
                zeros_set = sp.solveset(denom_expr, var, domain=sp.S.Reals)
                if isinstance(zeros_set, sp.ConditionSet):
                    d_roots = sp.solve(sp.Eq(denom_expr, 0), var)
                    real_d_roots = [r for r in d_roots if r.is_real or (r.is_number and r.as_real_imag()[1] == 0)]
                    if real_d_roots:
                        cur_domain = sp.Complement(cur_domain, sp.FiniteSet(*real_d_roots))
                        cur_completeness = DomainCompleteness.PARTIAL
                    else:
                        cur_completeness = DomainCompleteness.UNKNOWN
                elif zeros_set != sp.S.EmptySet:
                    cur_domain = sp.Complement(cur_domain, zeros_set)
                elif zeros_set == sp.S.EmptySet:
                    pass
            except Exception:
                try:
                    d_roots = sp.solve(sp.Eq(denom_expr, 0), var)
                    real_d_roots = [r for r in d_roots if r.is_real or (r.is_number and r.as_real_imag()[1] == 0)]
                    if real_d_roots:
                        cur_domain = sp.Complement(cur_domain, sp.FiniteSet(*real_d_roots))
                        cur_completeness = DomainCompleteness.PARTIAL
                    else:
                        cur_completeness = DomainCompleteness.UNKNOWN
                except Exception:
                    cur_completeness = DomainCompleteness.UNKNOWN

        return cur_domain, cur_completeness

    # 1. Denominator of outer fraction
    try:
        _, denom = sp.fraction(expr)
        domain, completeness = _handle_denominator(denom, domain, completeness)
    except Exception:
        completeness = DomainCompleteness.PARTIAL

    # Check if expression contains imaginary unit I (requiring real-domain solutions)
    if expr.has(sp.I) and var in expr.free_symbols:
        try:
            im_roots = sp.solve(sp.Eq(sp.im(expr), 0), var)
            real_im_roots = [r for r in im_roots if r.is_real or (r.is_number and r.as_real_imag()[1] == 0)]
            if real_im_roots:
                domain = sp.Intersection(domain, sp.FiniteSet(*real_im_roots))
        except Exception:
            completeness = DomainCompleteness.PARTIAL

    # 2. Traverse AST sub-expressions
    for node in sp.preorder_traversal(expr):
        # Logarithm: argument must be strictly positive (arg > 0)
        if isinstance(node, sp.log):
            arg = node.args[0]
            if var in arg.free_symbols:
                try:
                    s_arg = sp.solve_univariate_inequality(arg > 0, var, relational=False)
                    domain = sp.Intersection(domain, s_arg)
                except Exception:
                    # Fallback for simple affine expressions
                    try:
                        r = sp.solve(sp.Eq(arg, 0), var)
                        if r and len(r) == 1 and r[0].is_real:
                            val = r[0]
                            # Test derivative or sign
                            if sp.diff(arg, var) > 0:
                                domain = sp.Intersection(domain, sp.Interval.open(val, sp.oo))
                            else:
                                domain = sp.Intersection(domain, sp.Interval.open(-sp.oo, val))
                            completeness = DomainCompleteness.PARTIAL
                        else:
                            completeness = DomainCompleteness.PARTIAL
                    except Exception:
                        completeness = DomainCompleteness.PARTIAL

        # Powers: even roots and negative exponents
        elif isinstance(node, sp.Pow):
            base, exp = node.as_base_exp()
            if var in base.free_symbols:
                # Negative powers => base != 0
                if exp.is_negative:
                    domain, completeness = _handle_denominator(base, domain, completeness)

                # Even roots => base >= 0
                if exp.is_Rational and exp.q % 2 == 0:
                    try:
                        s_base = sp.solve_univariate_inequality(base >= 0, var, relational=False)
                        domain = sp.Intersection(domain, s_base)
                    except Exception:
                        completeness = DomainCompleteness.PARTIAL

        # Inverse trigonometric functions: asin, acos => -1 <= arg <= 1
        elif isinstance(node, (sp.asin, sp.acos)):
            arg = node.args[0]
            if var in arg.free_symbols:
                try:
                    s_ge = sp.solve_univariate_inequality(arg >= -1, var, relational=False)
                    s_le = sp.solve_univariate_inequality(arg <= 1, var, relational=False)
                    domain = sp.Intersection(domain, s_ge, s_le)
                except Exception:
                    completeness = DomainCompleteness.PARTIAL

        # Trigonometric functions: tan, sec => cos(arg) != 0
        elif isinstance(node, (sp.tan, sp.sec)):
            arg = node.args[0]
            if var in arg.free_symbols:
                domain, completeness = _handle_denominator(sp.cos(arg), domain, completeness)

        # Trigonometric functions: cot, csc => sin(arg) != 0
        elif isinstance(node, (sp.cot, sp.csc)):
            arg = node.args[0]
            if var in arg.free_symbols:
                domain, completeness = _handle_denominator(sp.sin(arg), domain, completeness)

    return domain, completeness


def extract_expression_domain(expr: sp.Expr, var: sp.Symbol) -> sp.Set:
    """Derive the maximal real domain where an expression is algebraically and analytically defined."""
    dom, _ = extract_expression_domain_with_completeness(expr, var)
    return dom


class ODEDomainAnalyzer:
    """Analyzes Ordinary Differential Equations to extract original and normalized domains,
    connected intervals, and singular point extension properties."""

    @classmethod
    def analyze_first_order_ode(
        cls,
        original_lhs: sp.Expr,
        original_rhs: sp.Expr,
        leading_coeff: sp.Expr | None,
        p_expr: sp.Expr,
        g_expr: sp.Expr,
        var: sp.Symbol,
        dep_var: sp.Symbol,
    ) -> DomainAnalysisResult:
        """Perform comprehensive domain and singular point analysis on a first-order ODE."""
        # 1. Original Equation Domain: where the unnormalized equation is defined
        completenesses: list[DomainCompleteness] = []
        orig_lhs_dom, c_lhs = extract_expression_domain_with_completeness(original_lhs, var)
        orig_rhs_dom, c_rhs = extract_expression_domain_with_completeness(original_rhs, var)
        completenesses.extend([c_lhs, c_rhs])
        original_domain = sp.Intersection(orig_lhs_dom, orig_rhs_dom)

        # 2. Leading coefficient singular points (roots where a_n(t) = 0)
        singular_points: list[sp.Expr] = []
        if leading_coeff is not None and var in leading_coeff.free_symbols:
            try:
                lc_roots = sp.solve(sp.Eq(leading_coeff, 0), var)
                singular_points = [r for r in lc_roots if r.is_real or (r.is_number and r.as_real_imag()[1] == 0)]
            except Exception:
                completenesses.append(DomainCompleteness.PARTIAL)

        # 3. Normalized Equation Domain: where division by leading_coeff is valid and p(t), g(t) exist
        p_dom, c_p = extract_expression_domain_with_completeness(p_expr, var)
        g_dom, c_g = extract_expression_domain_with_completeness(g_expr, var)
        completenesses.extend([c_p, c_g])
        normalized_domain = sp.Intersection(original_domain, p_dom, g_dom)
        if singular_points:
            normalized_domain = sp.Complement(normalized_domain, sp.FiniteSet(*singular_points))

        # 4. Extract connected components of normalized domain
        intervals, isolated_pts, other_comps = _decompose_set_components(normalized_domain)
        connected_intervals = tuple(intervals)
        is_disconnected = len(connected_intervals) > 1

        restrictions: list[str] = []
        if isolated_pts:
            pts_str = ", ".join(expr_to_latex(p) for p in isolated_pts)
            restrictions.append(
                f"Tập xác định chứa điểm cô lập {{{pts_str}}}; "
                f"điểm cô lập không tạo thành khoảng mở hợp lệ cho bài toán vi phân (ODE)."
            )
            completenesses.append(DomainCompleteness.PARTIAL)

        if other_comps:
            completenesses.append(DomainCompleteness.PARTIAL)

        # 5. Collect all denominator zeros
        denominator_zeros_list: list[sp.Expr] = []
        for expr_part in (original_lhs, original_rhs, leading_coeff, p_expr, g_expr):
            if expr_part is None:
                continue
            for node in sp.preorder_traversal(expr_part):
                if isinstance(node, sp.Pow):
                    base, exp = node.as_base_exp()
                    if exp.is_negative and var in base.free_symbols:
                        try:
                            b_roots = sp.solve(sp.Eq(base, 0), var)
                            for r in b_roots:
                                if r.is_real or (r.is_number and r.as_real_imag()[1] == 0):
                                    if not any(sp.simplify(r - ex) == 0 for ex in denominator_zeros_list):
                                        denominator_zeros_list.append(r)
                        except Exception:
                            pass
            try:
                _, denom = sp.fraction(expr_part)
                if denom != 1 and var in denom.free_symbols:
                    d_roots = sp.solve(sp.Eq(denom, 0), var)
                    for r in d_roots:
                        if r.is_real or (r.is_number and r.as_real_imag()[1] == 0):
                            if not any(sp.simplify(r - ex) == 0 for ex in denominator_zeros_list):
                                denominator_zeros_list.append(r)
            except Exception:
                pass

        # 6. Build restrictions strings
        # Check logs
        for expr_part in (original_lhs, original_rhs, p_expr, g_expr):
            for node in expr_part.atoms(sp.log):
                arg = node.args[0]
                restrictions.append(f"Điều kiện xác định của hàm logarit: {arg} > 0.")
            for node in expr_part.atoms(sp.Pow):
                base, exp = node.as_base_exp()
                if exp.is_Rational and exp.q % 2 == 0:
                    restrictions.append(f"Điều kiện xác định: {base} >= 0 (căn bậc chẵn).")
            for node in expr_part.atoms(sp.asin, sp.acos):
                arg = node.args[0]
                restrictions.append(f"Điều kiện hàm lượng giác ngược asin / acos: -1 <= {arg} <= 1.")
            for node in expr_part.atoms(sp.tan, sp.sec):
                arg = node.args[0]
                restrictions.append(f"Điều kiện hàm lượng giác tan / sec: cos({arg}) != 0.")
            for node in expr_part.atoms(sp.cot, sp.csc):
                arg = node.args[0]
                restrictions.append(f"Điều kiện hàm lượng giác cot / csc: sin({arg}) != 0.")

        for dz in denominator_zeros_list:
            restrictions.append(f"Điều kiện xác định của mẫu số: {var} khác {dz}.")

        for sp_pt in singular_points:
            restrictions.append(f"Điểm kỳ dị của hệ số dẫn: {var} khác {sp_pt}.")

        # 7. Analyze singular points for value and derivative constraints
        singular_analyses: list[SingularPointAnalysis] = []
        yp_sym = sp.Symbol("__yp__")
        y_sym = sp.Symbol("__y__")
        ypp_sym = sp.Symbol("__ypp__")

        # Represent ODE as F(t, y, y') = 0
        try:
            # Replace derivative of dep_var with yp_sym and dep_var with y_sym
            ode_raw = original_lhs - original_rhs
            # Replace any derivative symbols
            for sym in ode_raw.free_symbols:
                if "prime" in sym.name or sym.name in ("y'", "dy", "dy_dt", "dy_dx"):
                    ode_raw = ode_raw.subs(sym, yp_sym)
            ode_F = ode_raw.subs(dep_var, y_sym)
            # If yp_sym not yet in ode_F, check if leading_coeff was separated
            if yp_sym not in ode_F.free_symbols and leading_coeff is not None:
                ode_F = leading_coeff * yp_sym + p_expr * leading_coeff * y_sym - g_expr * leading_coeff
        except Exception:
            ode_F = None

        for pt in singular_points:
            pt_in_orig = pt in original_domain
            val_at_pt: sp.Expr | None = None
            deriv_at_pt: sp.Expr | None = None
            ext_status = VerificationStatus.UNVERIFIED
            details_parts: list[str] = []

            if pt_in_orig and ode_F is not None:
                try:
                    # 1. Evaluate F(t_s, y, y')
                    ode_at_pt = sp.simplify(ode_F.subs(var, pt))
                    # If yp_sym vanished (or coeff is 0), solve for y_sym
                    if y_sym in ode_at_pt.free_symbols:
                        # Check if yp_sym vanishes
                        yp_coeff = sp.simplify(ode_at_pt.coeff(yp_sym))
                        if yp_coeff == 0 or yp_sym not in ode_at_pt.free_symbols:
                            y_sols = sp.solve(ode_at_pt, y_sym)
                            if y_sols:
                                val_at_pt = sp.simplify(y_sols[0])
                                details_parts.append(
                                    f"Tại {var} = {pt}: hệ số dẫn triệt tiêu, phương trình gốc suy biến thành phương trình đại số xác định giá trị nghiệm duy nhất: $y({expr_to_latex(pt)}) = {expr_to_latex(val_at_pt)}$."
                                )

                    # 2. Total derivative: dF/dt = dF/dvar + dF/dy * y' + dF/dy' * y''
                    if val_at_pt is not None:
                        dF_dt = sp.diff(ode_F, var) + sp.diff(ode_F, y_sym) * yp_sym + sp.diff(ode_F, yp_sym) * ypp_sym
                        dF_at_pt = sp.simplify(dF_dt.subs(var, pt).subs(y_sym, val_at_pt).subs(ypp_sym, 0))
                        if yp_sym in dF_at_pt.free_symbols:
                            yp_sols = sp.solve(dF_at_pt, yp_sym)
                            if yp_sols:
                                deriv_at_pt = sp.simplify(yp_sols[0])
                                details_parts.append(
                                    f"Đạo hàm cần thiết để nghiệm mở rộng khả vi: $y'({expr_to_latex(pt)}) = {expr_to_latex(deriv_at_pt)}$."
                                )
                                ext_status = VerificationStatus.PARTIALLY_VERIFIED
                except Exception as exc:
                    details_parts.append(f"Không thể giải tích mở rộng tại {var} = {pt}: {exc}")

            pt_str = str(pt)
            ltx_summary = ""
            if val_at_pt is not None:
                val_ltx = expr_to_latex(val_at_pt)
                ltx_summary = f"y({expr_to_latex(pt)}) = {val_ltx}"
                if deriv_at_pt is not None:
                    d_ltx = expr_to_latex(deriv_at_pt)
                    ltx_summary += f", \\quad y'({expr_to_latex(pt)}) = {d_ltx}"

            singular_analyses.append(
                SingularPointAnalysis(
                    point=pt,
                    point_str=pt_str,
                    original_eq_valid=pt_in_orig,
                    value_at_point=val_at_pt,
                    derivative_at_point=deriv_at_pt,
                    extension_status=ext_status,
                    details=" ".join(details_parts),
                    latex_summary=ltx_summary,
                )
            )

        # 7. Build LaTeX representations of domains
        orig_latex = format_set_latex(original_domain, var.name)
        orig_domain_latex = f"\\mathcal{{D}}_{{\\text{{orig}}}} = {orig_latex}"

        if is_disconnected:
            intervals_latex = [format_interval_latex(iv) for iv in connected_intervals]
            union_latex = " \\cup ".join(intervals_latex)
            components_latex = ", \\; ".join(f"I_{idx} = {iv_ltx}" for idx, iv_ltx in enumerate(intervals_latex, 1))
            norm_domain_latex = (
                f"\\mathcal{{D}}_{{\\text{{norm}}}} = {union_latex} = "
                + " \\cup ".join(f"I_{i}" for i in range(1, len(intervals_latex) + 1))
                + f" \\quad ({components_latex})"
            )
            comp_ve_str = " và ".join(f"I_{idx} = {iv_ltx}" for idx, iv_ltx in enumerate(intervals_latex, 1))
            restrictions.append(
                f"Miền xác định của phương trình gồm hai khoảng liên thông rời rạc: \\mathcal{{D}} = {union_latex} = "
                + " \\cup ".join(f"I_{i}" for i in range(1, len(intervals_latex) + 1))
                + f", với {comp_ve_str}."
            )
        else:
            norm_latex = format_set_latex(normalized_domain, var.name)
            norm_domain_latex = f"\\mathcal{{D}}_{{\\text{{norm}}}} = {norm_latex}"

        if any(c == DomainCompleteness.UNKNOWN for c in completenesses):
            final_completeness = DomainCompleteness.UNKNOWN
        elif any(c == DomainCompleteness.PARTIAL for c in completenesses):
            final_completeness = DomainCompleteness.PARTIAL
        else:
            final_completeness = DomainCompleteness.EXACT

        return DomainAnalysisResult(
            original_domain=original_domain,
            normalized_domain=normalized_domain,
            connected_intervals=connected_intervals,
            singular_points=tuple(singular_points),
            denominator_zeros=tuple(denominator_zeros_list),
            original_domain_latex=orig_domain_latex,
            normalized_domain_latex=norm_domain_latex,
            domain_restrictions=tuple(restrictions),
            singular_point_analyses=tuple(singular_analyses),
            is_disconnected=is_disconnected,
            completeness=final_completeness,
            isolated_points=tuple(isolated_pts),
            other_components=tuple(other_comps),
        )

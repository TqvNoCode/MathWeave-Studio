"""Independent mathematical verification for differential equation solutions."""

from __future__ import annotations

from enum import Enum
import math
import re
from typing import Any
import sympy as sp

from math_app.application.dtos import VerificationResult
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
                if s_pos == 0 or sp.simplify(sp.radsimp(s_pos)) == 0 or sp.simplify(sp.cancel(s_pos)) == 0:
                    return True
            elif is_negative:
                var_neg = sp.Symbol(variable.name, negative=True)
                s_neg = sp.simplify(expr.subs(variable, var_neg).doit())
                if s_neg == 0 or sp.simplify(sp.radsimp(s_neg)) == 0 or sp.simplify(sp.cancel(s_neg)) == 0:
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


def validate_initial_point_in_domain(
    expr: sp.Expr | None,
    x_sym: sp.Symbol,
    y_sym: sp.Symbol,
    x0: sp.Expr,
    y0: sp.Expr,
    original_denominators: tuple[sp.Expr, ...] = (),
    leading_coeffs: tuple[sp.Expr, ...] = (),
) -> tuple[bool, str]:
    """Validate whether the initial point (x0, y0) lies in the real domain of the ODE.

    Checks:
    - Finite real values for initial coordinates (rejects zoo, nan, oo, -oo, imaginary).
    - Original unsimplified denominators do not vanish at (x0, y0).
    - Leading coefficients do not vanish at x0 (singular points).
    - Even-root radicands are not strictly negative.
    - Logarithm arguments are strictly positive.
    - Expression evaluates to a finite real number without dividing by zero.

    Returns (is_valid, error_message).
    """
    # 0. Check finiteness and reality of initial point coordinates
    for coord_name, coord_val in (("x0", x0), ("y0", y0)):
        if coord_val is not None:
            if coord_val.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or coord_val.is_finite is False:
                return False, f"Giá trị điều kiện ban đầu {coord_name} = {coord_val} không phải là số thực hữu hạn."
            if coord_val.is_real is False or (coord_val.has(sp.I) and not sp.simplify(coord_val).is_real):
                return False, f"Giá trị điều kiện ban đầu {coord_name} = {coord_val} chứa phần ảo hoặc không phải là số thực."

    sub_map = [(x_sym, x0), (y_sym, y0)]

    # 1. Check unsimplified original denominators
    for denom in original_denominators:
        try:
            d_val = sp.simplify(denom.subs(sub_map))
            if _prove_symbolic_zero(d_val) or d_val == 0:
                return False, f"Mẫu số ban đầu {denom} triệt tiêu tại điều kiện ban đầu ({x0}, {y0}) (Original denominator vanishes at initial point)."
        except Exception:
            pass

    # 2. Check leading coefficients
    for lcoeff in leading_coeffs:
        try:
            lc_val = sp.simplify(lcoeff.subs([(x_sym, x0)]))
            if _prove_symbolic_zero(lc_val) or lc_val == 0:
                return False, f"Điểm ban đầu {x0} là điểm kỳ dị của phương trình vi phân: hệ số dẫn {lcoeff} triệt tiêu (Initial point is a singular point where leading coefficient vanishes)."
        except Exception:
            pass

    # 3. Check expression AST nodes and evaluation
    if expr is not None:
        for node in sp.preorder_traversal(expr):
            if isinstance(node, sp.Pow):
                b, e = node.as_base_exp()
                if e.is_negative:
                    try:
                        b_val = sp.simplify(b.subs(sub_map))
                        if _prove_symbolic_zero(b_val):
                            return False, f"Mẫu số ban đầu {b} triệt tiêu tại điều kiện ban đầu ({x0}, {y0}) (Original denominator vanishes at initial point)."
                    except Exception:
                        pass
                elif e.is_Rational and e.q % 2 == 0:
                    try:
                        b_val = sp.simplify(b.subs(sub_map))
                        if b_val.is_number and b_val < 0:
                            return False, f"Biểu thức dưới căn bậc chẵn {b} có giá trị âm ({b_val}) tại điểm ban đầu ({x0}, {y0})."
                    except Exception:
                        pass
            elif isinstance(node, sp.log):
                try:
                    arg_val = sp.simplify(node.args[0].subs(sub_map))
                    if arg_val.is_number and arg_val <= 0:
                        return False, f"Biểu thức trong logarit {node.args[0]} không dương ({arg_val}) tại điểm ban đầu ({x0}, {y0})."
                except Exception:
                    pass

        try:
            val = sp.simplify(expr.subs(sub_map))
            if val.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
                return False, f"Phương trình vi phân không xác định (chia cho 0 hoặc tiến tới vô cực: {val}) tại điểm ban đầu ({x0}, {y0})."
            if val.is_real is False or (val.has(sp.I) and not expr.has(sp.I)):
                return False, f"Phương trình vi phân nhận giá trị phức ({val}) tại điểm ban đầu ({x0}, {y0})."
        except Exception as exc:
            return False, f"Lỗi đánh giá phương trình vi phân tại điểm ban đầu ({x0}, {y0}): {exc}"

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
            diff_y = sp.diff(solution, variable)
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
                val_at_t0 = sp.simplify(solution.subs(variable, t0))
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

    def verify_exact(
        self,
        potential_F: sp.Expr,
        M_expr: sp.Expr,
        N_expr: sp.Expr,
        x_sym: sp.Symbol,
        y_sym: sp.Symbol,
        initial_condition: tuple[sp.Expr, sp.Expr] | None = None,
    ) -> VerificationResult:
        """Verify potential function F(x, y) for exact equation M dx + N dy = 0."""
        try:
            dF_dx = sp.diff(potential_F, x_sym)
            dF_dy = sp.diff(potential_F, y_sym)
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
                val_at_ic = sp.simplify(potential_F.subs([(x_sym, x0), (y_sym, y0)]))
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="exact_potential_gradient_and_ic_check",
                    details=f"Kiểm chứng thành công: ∇F = (M, N) và F({x0}, {y0}) = {val_at_ic}.",
                )

            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="exact_potential_gradient_check",
                details="Kiểm chứng thành công: Gradient của hàm thế ∇F = (∂F/∂x, ∂F/∂y) đồng nhất với (M, N).",
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
    ) -> VerificationResult:
        """Verify integrating factor mu and potential F for M dx + N dy = 0."""
        try:
            M_transformed = sp.simplify(mu_expr * M_expr)
            N_transformed = sp.simplify(mu_expr * N_expr)

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
            dF_dx = sp.diff(potential_F, x_sym)
            dF_dy = sp.diff(potential_F, y_sym)
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
                val_at_ic = sp.simplify(potential_F.subs([(x_sym, x0), (y_sym, y0)]))
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
    ) -> VerificationResult:
        """Verify a second-order ODE solution against a*y'' + b*y' + c*y - g(t) = 0 and optional IVPs."""
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

        if initial_condition is not None and initial_derivative is not None:
            t0, y0 = initial_condition
            _, v0 = initial_derivative
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="second_order_ode_residual_and_dual_ic_zero_check",
                details=f"Kiểm chứng độc lập thành công: Biểu thức dư R({variable}) ≡ 0 và hệ điều kiện Cauchy y({t0}) = {y0}, y'({t0}) = {v0} nghiệm đúng.",
            )

        if initial_condition is not None:
            t0, y0 = initial_condition
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="second_order_ode_residual_and_ic_zero_check",
                details=f"Kiểm chứng độc lập thành công: Biểu thức dư R({variable}) ≡ 0 và điều kiện ban đầu y({t0}) = {y0} nghiệm đúng.",
            )

        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            method="second_order_ode_residual_zero_check",
            details=f"Kiểm chứng độc lập thành công: Biểu thức dư R({variable}) = a*y'' + b*y' + c*y ≡ 0.",
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
            dy1 = sp.diff(y1, variable)
            dy2 = sp.diff(y2, variable)
            w_raw = y1 * dy2 - dy1 * y2
            if _prove_symbolic_zero(w_raw):
                w_expr = sp.Integer(0)
            else:
                w_expr = sp.simplify(sp.trigsimp(sp.simplify(w_raw)))
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
        w_val, res_w = self.verify_wronskian(y1, y2, variable, ode_coeffs=(a_coeff, b_coeff, c_coeff))
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

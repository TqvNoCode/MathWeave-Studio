"""Separable ordinary differential equations solver: y' = f(t)*g(y)."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any
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
from math_app.domain.models import EquilibriumUniqueness, ProblemType, SolutionStatus, VerificationStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.input.ode_parser import ParsedODE, check_classical_homogeneous_ode, parse_ode_input
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.verification.calculus.ode_verifier import (
    ODEVerifier,
    _prove_symbolic_zero,
    validate_initial_point_in_domain,
)
from sympy.calculus.util import continuous_domain


def _find_connected_domain_interval(
    expr: sp.Expr | None,
    var: sp.Symbol,
    t0: sp.Expr | float | None = None,
    given_interval: tuple[Any, Any] | None = None,
) -> tuple[sp.Expr | float, sp.Expr | float]:
    """Determine a connected real domain interval for an ODE solution branch."""
    if given_interval is not None:
        return given_interval
    if expr is not None:
        try:
            dom = continuous_domain(expr, var, sp.S.Reals)
            if isinstance(dom, sp.Interval):
                return (dom.start, dom.end)
            if isinstance(dom, sp.Union):
                if t0 is not None:
                    for arg in dom.args:
                        if isinstance(arg, sp.Interval) and (arg.contains(t0) or arg.start <= t0 <= arg.end):
                            return (arg.start, arg.end)
                for arg in dom.args:
                    if isinstance(arg, sp.Interval):
                        return (arg.start, arg.end)
        except Exception:
            pass
    if t0 is not None:
        try:
            t0_n = float(sp.N(t0))
            if t0_n > 0:
                return (0, sp.oo)
            if t0_n < 0:
                return (-sp.oo, 0)
        except Exception:
            pass
        return (-sp.oo, sp.oo)
    return (-sp.oo, sp.oo)


def _real_integrate_reciprocal(g_expr: sp.Expr, dep_var: sp.Symbol) -> sp.Expr:
    """Compute real-valued integral of 1/g(y) with respect to y, wrapping log arguments in Abs."""
    coeff, rest = g_expr.as_coeff_Mul() if g_expr.is_Mul else (sp.Integer(1), g_expr)
    if coeff.is_number and coeff != 0 and rest.func == sp.sin and len(rest.args) == 1:
        arg = rest.args[0]
        a_coeff = arg.coeff(dep_var)
        if a_coeff != 0 and arg == a_coeff * dep_var:
            return sp.log(sp.Abs(sp.tan(a_coeff * dep_var / 2))) / (coeff * a_coeff)
    elif coeff.is_number and coeff != 0 and rest.func == sp.cos and len(rest.args) == 1:
        arg = rest.args[0]
        a_coeff = arg.coeff(dep_var)
        if a_coeff != 0 and arg == a_coeff * dep_var:
            return sp.log(sp.Abs(sp.tan(a_coeff * dep_var / 2 + sp.pi / 4))) / (coeff * a_coeff)

    raw_g = sp.integrate(1 / g_expr, dep_var)
    return raw_g.replace(sp.log, lambda a: sp.log(sp.Abs(a)))


def _detect_periodic_trig_family(
    g_expr: sp.Expr,
    dep_var: sp.Symbol,
) -> tuple[bool, bool, str, str, list[sp.Expr], list[str]]:
    """Detect if g(y) has periodic roots from sin(a*y) or cos(a*y).

    Symbolically verifies the indexed identity over integer n in Z.
    Returns (is_periodic, is_complete_verified, family_str, family_latex, representative_roots, required_assumptions).
    """
    coeff, rest = g_expr.as_coeff_Mul() if g_expr.is_Mul else (sp.Integer(1), g_expr)
    if rest.func in (sp.sin, sp.cos) and len(rest.args) == 1:
        arg = rest.args[0]
        a = arg.coeff(dep_var)
        rem = sp.simplify(arg - a * dep_var)
        if a != 0 and rem == 0 and dep_var not in a.free_symbols:
            abs_a = abs(a) if a.is_number else sp.Abs(a)
            assumptions: list[str] = []
            if a.is_number:
                is_real_nonzero = bool(a.is_real and a != 0)
            else:
                is_real_nonzero = bool(getattr(a, "is_real", None) is True and getattr(a, "is_nonzero", None) is True)
                assumptions.append(f"Giả định tham số: {a} là số thực khác 0 ({a} ∈ ℝ \\ {{0}}).")

            if rest.func == sp.sin:
                fam_str = f"{dep_var} = n*pi / {abs_a} (n in Z)" if abs_a != 1 else f"{dep_var} = n*pi (n in Z)"
                fam_latex = (
                    f"{dep_var}_{{eq}} = \\frac{{n\\pi}}{{{expr_to_latex(abs_a)}}}, \\; n \\in \\mathbb{{Z}}"
                    if abs_a != 1
                    else f"{dep_var}_{{eq}} = n\\pi, \\; n \\in \\mathbb{{Z}}"
                )
                reps = [sp.simplify(k * sp.pi / abs_a) for k in (0, 1, -1)]
                return True, is_real_nonzero, fam_str, fam_latex, reps, assumptions
            elif rest.func == sp.cos:
                if abs_a == 1:
                    fam_str = f"{dep_var} = pi/2 + n*pi (n in Z)"
                    fam_latex = f"{dep_var}_{{eq}} = \\frac{{\\pi}}{{2}} + n\\pi, \\; n \\in \\mathbb{{Z}}"
                else:
                    denom = 2 * abs_a
                    fam_str = f"{dep_var} = (2*n + 1)*pi / {denom} (n in Z)"
                    fam_latex = f"{dep_var}_{{eq}} = \\frac{{(2n + 1)\\pi}}{{{expr_to_latex(denom)}}}, \\; n \\in \\mathbb{{Z}}"
                reps = [sp.simplify((2 * k + 1) * sp.pi / (2 * abs_a)) for k in (0, -1, 1)]
                return True, is_real_nonzero, fam_str, fam_latex, reps, assumptions

    return False, False, "", "", [], []


def _check_equilibrium_uniqueness(
    g_expr: sp.Expr,
    f_expr: sp.Expr,
    var: sp.Symbol,
    dep_var: sp.Symbol,
    t0: sp.Expr,
    y0: sp.Expr,
) -> tuple[EquilibriumUniqueness, str, sp.Expr | None, str | None]:
    """Assess equilibrium solution uniqueness at Cauchy initial condition (t0, y0).

    Returns:
    (status, reason, branching_solution_expr, branching_domain_str)
    """
    try:
        f_val = sp.simplify(f_expr.subs(var, t0))
        if f_val.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or (f_val.is_real is False and not f_expr.has(sp.I)):
            return (
                EquilibriumUniqueness.UNIQUENESS_NOT_ESTABLISHED,
                f"Hàm f({var}) không bị chặn hoặc không xác định tại {var} = {t0}.",
                None,
                None,
            )

        dg_dy = sp.diff(g_expr, dep_var)
        dg_val = sp.simplify(dg_dy.subs(dep_var, y0))

        # Check whether dg/dy is definitively bounded (Lipschitz) near y0
        is_lipschitz: bool | None = None

        if dg_val.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
            is_lipschitz = False
        elif dg_val.is_number and dg_val.is_real and dg_val.is_finite:
            try:
                lim_right = sp.limit(dg_dy, dep_var, y0, dir="+")
                lim_left = sp.limit(dg_dy, dep_var, y0, dir="-")
                if lim_right.has(sp.Limit) or lim_left.has(sp.Limit):
                    is_lipschitz = None
                elif lim_right.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or lim_left.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
                    is_lipschitz = False
                elif getattr(lim_right, "is_finite", False) and getattr(lim_left, "is_finite", False):
                    is_lipschitz = True
                else:
                    is_lipschitz = None
            except Exception:
                is_lipschitz = None
        else:
            try:
                lim_right = sp.limit(dg_dy, dep_var, y0, dir="+")
                lim_left = sp.limit(dg_dy, dep_var, y0, dir="-")
                if lim_right.has(sp.Limit) or lim_left.has(sp.Limit):
                    is_lipschitz = None
                elif lim_right.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or lim_left.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
                    is_lipschitz = False
                elif getattr(lim_right, "is_finite", False) and getattr(lim_left, "is_finite", False):
                    is_lipschitz = True
                else:
                    is_lipschitz = None
            except Exception:
                is_lipschitz = None

        if is_lipschitz is True:
            return (
                EquilibriumUniqueness.UNIQUE_PROVEN,
                f"Các hàm f({var}) và g({dep_var}) liên tục và g thỏa mãn điều kiện Lipschitz cục bộ theo {dep_var} trong lân cận điểm ban đầu; "
                f"theo định lý tồn tại và duy nhất nghiệm Picard–Lindelöf, nghiệm duy nhất của bài toán là hàm hằng {dep_var}({var}) = {y0}.",
                None,
                None,
            )

        if is_lipschitz is None:
            return (
                EquilibriumUniqueness.UNIQUENESS_NOT_ESTABLISHED,
                f"Giới hạn đạo hàm g'({dep_var}) tại điểm cân bằng {dep_var} = {y0} không xác định hoặc không thể tính toán kết luận ký hiệu (inconclusive symbolic limit); "
                f"chưa đủ điều kiện khẳng định tính duy nhất của nghiệm.",
                None,
                None,
            )

        # Lipschitz fails: g'(y) is unbounded near y0.
        # Now investigate whether a branching non-equilibrium solution genuinely exists.
        # 1. Check Osgood / separation integral convergence: \int_{0}^{\epsilon} du / g(y0 + u)
        u_sym = sp.Symbol("_u_osgood", positive=True)
        g_shifted = g_expr.subs(dep_var, y0 + u_sym)
        is_convergent = False
        try:
            osgood_int = sp.integrate(1 / g_shifted, (u_sym, 0, 1))
            if osgood_int.is_finite:
                is_convergent = True
        except Exception:
            pass

        # 2. Attempt to construct the branching non-equilibrium solution
        # For pure power g(y) = (y - y0)^p with 0 < p < 1
        alt_sol: sp.Expr | None = None
        alt_domain: str | None = None

        diff_y = dep_var - y0
        k_val: sp.Expr | None = None
        p_val: sp.Expr | None = None
        if g_expr.is_Pow and g_expr.base == dep_var and y0 == 0:
            k_val = sp.Integer(1)
            p_val = g_expr.exp
        elif g_expr.is_Pow and g_expr.base == diff_y:
            k_val = sp.Integer(1)
            p_val = g_expr.exp
        elif g_expr.is_Mul:
            c_part, r_part = g_expr.as_coeff_Mul()
            if r_part.is_Pow and ((r_part.base == dep_var and y0 == 0) or r_part.base == diff_y):
                k_val = c_part
                p_val = r_part.exp

        if k_val is not None and p_val is not None and 0 < p_val < 1:
            # Determine branch direction from sign of vector field near (t0, y0)
            f_at_t0 = sp.simplify(f_expr.subs(var, t0))
            if f_at_t0 == 0:
                # If f(t0) == 0, evaluate sign of first non-zero derivative or limit
                try:
                    f_diff1 = sp.diff(f_expr, var).subs(var, t0)
                    eff_sign = sp.simplify(k_val * f_diff1)
                except Exception:
                    eff_sign = sp.Integer(1)
            else:
                eff_sign = sp.simplify(k_val * f_at_t0)

            is_negative_dir = bool(eff_sign.is_negative or (eff_sign.is_number and eff_sign < 0))
            if is_negative_dir:
                branch_dom: tuple[sp.Expr | float, sp.Expr | float] = (-sp.oo, t0)
                alt_domain = f"{var} <= {t0}"
            else:
                branch_dom = (t0, sp.oo)
                alt_domain = f"{var} >= {t0}"

            int_f_cur = sp.integrate(f_expr, var)
            f_diff = int_f_cur - int_f_cur.subs(var, t0)
            m_exp = 1 - p_val
            inv_exp = 1 / m_exp

            # For negative direction, (t - t0) < 0 so f_diff and k_val have opposite signs;
            # m_exp * k_val * f_diff remains positive.
            inner_term = sp.simplify(m_exp * k_val * f_diff)
            cand_sol = y0 + (inner_term) ** inv_exp
            cand_simp = sp.simplify(cand_sol)

            dy_dt = sp.diff(cand_simp, var)
            sub_res = sp.simplify(dy_dt - f_expr * g_expr.subs(dep_var, cand_simp))

            # Strictly symbolic proof: Never prove identity with a single numerical probe point
            is_res_zero = _prove_symbolic_zero(
                sub_res,
                domain_interval=branch_dom,
                variable=var,
            )
            ic_diff = sp.simplify(cand_simp.subs(var, t0) - y0)
            is_ic_zero = _prove_symbolic_zero(ic_diff, domain_interval=branch_dom, variable=var)

            if is_res_zero and is_ic_zero and not _prove_symbolic_zero(cand_simp - y0):
                alt_sol = cand_simp
                is_convergent = True

        if not alt_sol and is_convergent:
            try:
                int_g_expr = sp.integrate(1 / g_expr, dep_var)
                int_f_expr = sp.integrate(f_expr, var)
                c_cand = sp.simplify(int_g_expr.subs(dep_var, y0) - int_f_expr.subs(var, t0))
                sols = sp.solve(int_g_expr - (int_f_expr + c_cand), dep_var)
                for s in sols:
                    if s != y0 and sp.simplify(s.subs(var, t0) - y0) == 0:
                        s_simp = sp.simplify(s)
                        # Symbolically verify candidate against ODE on domain
                        res_s = sp.simplify(sp.diff(s_simp, var) - f_expr * g_expr.subs(dep_var, s_simp))
                        if _prove_symbolic_zero(res_s, domain_interval=(t0, sp.oo), variable=var):
                            alt_sol = s_simp
                            alt_domain = f"{var} >= {t0}"
                            break
                        elif _prove_symbolic_zero(res_s, domain_interval=(-sp.oo, t0), variable=var):
                            alt_sol = s_simp
                            alt_domain = f"{var} <= {t0}"
                            break
            except Exception:
                pass

        if is_convergent and alt_sol is not None:
            return (
                EquilibriumUniqueness.NONUNIQUE_PROVEN,
                f"Đạo hàm riêng dg/dy không bị chặn tại điểm cân bằng {dep_var} = {y0}. "
                f"Tích phân tách biến hội tụ tại {dep_var} = {y0}, dẫn đến sự rẽ nhánh của nghiệm; "
                f"tồn tại ít nhất hai nghiệm thực phân biệt cùng thỏa mãn điều kiện Cauchy: "
                f"nghiệm cân bằng y_1({var}) = {y0} và nhánh nghiệm rẽ y_2({var}) = {alt_sol} ({alt_domain}). "
                f"Lưu ý: Họ nghiệm không duy nhất đầy đủ bao gồm vô số nghiệm ghép liên tục với hàm hằng tại điểm nối tùy ý c.",
                alt_sol,
                alt_domain,
            )

        return (
            EquilibriumUniqueness.UNIQUENESS_NOT_ESTABLISHED,
            f"Điều kiện Picard–Lindelöf không áp dụng (g' không bị chặn tại điểm ban đầu {dep_var} = {y0}), "
            "nhưng chưa tìm thấy hoặc chưa chứng minh được nghiệm thứ hai phân biệt thỏa mãn cùng điều kiện ban đầu; "
            "Tính duy nhất của nghiệm chưa được khẳng định (Uniqueness not established).",
            None,
            None,
        )
    except Exception as exc:
        return (
            EquilibriumUniqueness.UNIQUENESS_NOT_ESTABLISHED,
            f"Không thể khẳng định tính duy nhất nghiệm: {exc}.",
            None,
            None,
        )


@dataclass(frozen=True)
class SeparableExplicitCandidate:
    """Explicit candidate solution for y(t) with domain and radical provenance."""

    expr: sp.Expr
    branch_identity: str
    real_root_restrictions: tuple[str, ...] = ()
    denominator_exclusions: tuple[str, ...] = ()


@dataclass
class EmittedBranchSolution:
    """Dataclass preserving full provenance and verification state of an emitted ODE branch solution."""

    solution_str: str
    solution_latex: str
    explicit_expr: sp.Expr | None
    derivative_branch: sp.Expr
    f_expr: sp.Expr
    g_expr: sp.Expr
    int_f: sp.Expr
    int_g: sp.Expr
    c_sym: sp.Symbol
    c_val: sp.Expr | None = None
    real_root_restrictions: tuple[str, ...] = ()
    denominator_exclusions: tuple[str, ...] = ()
    domain_interval: tuple[Any, Any] | None = None
    domain_restrictions: tuple[str, ...] = ()
    verification: VerificationResult | None = None
    branch_index: int = 1
    branch_identity: str = ""

    def to_branch_solution(self) -> BranchSolution:
        return BranchSolution(
            expression=self.explicit_expr,
            solution_str=self.solution_str,
            solution_latex=self.solution_latex,
            branch_identity=self.branch_identity or f"Nhánh đạo hàm {self.branch_index}",
            integration_constant=self.c_sym,
            integration_constant_val=self.c_val,
            real_root_restrictions=self.real_root_restrictions,
            denominator_exclusions=self.denominator_exclusions,
            domain_interval=self.domain_interval,
            domain_restrictions=self.domain_restrictions,
            verification=self.verification,
        )


def _solve_explicit_separable_candidates(
    f_expr: sp.Expr,
    g_expr: sp.Expr,
    var: sp.Symbol,
    dep_var: sp.Symbol,
    c_sym: sp.Symbol,
) -> list[SeparableExplicitCandidate] | None:
    """Solve for explicit real solution candidates y(t) with full domain and radical provenance."""
    int_f = sp.integrate(f_expr, var)

    # 1. Constant g(y) = k
    if dep_var not in g_expr.free_symbols:
        return [
            SeparableExplicitCandidate(
                expr=g_expr * int_f + c_sym,
                branch_identity="Nhánh vế phải hằng số",
            )
        ]

    # 2. Polynomials in y: linear, logistic, or monomial
    poly_g = sp.Poly(g_expr, dep_var) if g_expr.is_polynomial(dep_var) else None
    if poly_g is not None:
        deg = poly_g.degree()
        coeffs = poly_g.all_coeffs()
        if deg == 1:
            k = coeffs[0]
            c0 = coeffs[1]
            if c0 == 0:
                # dy/dt = k * f(x) * y => y(x) = C * exp(k * F(x))
                return [
                    SeparableExplicitCandidate(
                        expr=c_sym * sp.exp(k * int_f),
                        branch_identity="Nhánh tuyến tính thuần nhất",
                    )
                ]
            else:
                # dy/dt = (k*y + c0) * f(x) => y(x) = -c0/k + C * exp(k * F(x))
                return [
                    SeparableExplicitCandidate(
                        expr=-c0 / k + c_sym * sp.exp(k * int_f),
                        branch_identity="Nhánh tuyến tính",
                    )
                ]
        elif deg == 2:
            # Logistic: g(y) = a2*y^2 + a1*y (coeffs: [a2, a1, 0]) with a1 != 0 and a2 != 0
            if coeffs[2] == 0 and coeffs[1] != 0 and coeffs[0] != 0:
                a2, a1 = coeffs[0], coeffs[1]
                # dy / [y*(a1 + a2*y)] = f(x) dx => y(x) = a1*C*exp(a1*F(x)) / (1 - a2*C*exp(a1*F(x)))
                denom_expr = 1 - a2 * c_sym * sp.exp(a1 * int_f)
                return [
                    SeparableExplicitCandidate(
                        expr=a1 * c_sym * sp.exp(a1 * int_f) / denom_expr,
                        branch_identity="Nhánh logistic",
                        denominator_exclusions=(f"{denom_expr} khác 0",),
                    )
                ]
            # Monomial quadratic: g(y) = a2*y^2 (coeffs: [a2, 0, 0])
            elif coeffs[2] == 0 and coeffs[1] == 0 and coeffs[0] != 0:
                a2 = coeffs[0]
                denom_expr = a2 * (int_f + c_sym)
                return [
                    SeparableExplicitCandidate(
                        expr=-1 / denom_expr,
                        branch_identity="Nhánh bậc hai đơn thức",
                        denominator_exclusions=(f"{denom_expr} khác 0",),
                    )
                ]

    # 3. Pure power g(y) = k * y^p with integer p != 1
    k_val: sp.Expr | None = None
    p_val: sp.Expr | None = None

    if g_expr.is_Pow and g_expr.base == dep_var:
        k_val = sp.Integer(1)
        p_val = g_expr.exp
    elif g_expr.is_Mul:
        coeff, rest = g_expr.as_coeff_Mul()
        if rest.is_Pow and rest.base == dep_var:
            k_val = coeff
            p_val = rest.exp
        elif rest == dep_var:
            k_val = coeff
            p_val = sp.Integer(1)
    elif g_expr == dep_var:
        k_val = sp.Integer(1)
        p_val = sp.Integer(1)

    if k_val is not None and p_val is not None:
        if p_val == 1:
            return [
                SeparableExplicitCandidate(
                    expr=c_sym * sp.exp(k_val * int_f),
                    branch_identity="Nhánh lũy thừa bậc 1",
                )
            ]

        if p_val.is_integer:
            p_int = int(p_val)
            m = 1 - p_int
            # int(y^(-p) dy) = y^m / m = k * (int_f + C) => y^m = m * k * (int_f + C)
            U = sp.simplify(m * k_val * (int_f + c_sym))

            if m % 2 == 0:
                # Even m (e.g. p=3 => m=-2; p=5 => m=-4; p=-1 => m=2).
                # Two symmetric real branches defined on U > 0:
                # y_1 = (U)^(1/m), y_2 = - (U)^(1/m).
                exp_val = sp.Rational(1, m)
                y_pos = U ** exp_val
                y_neg = - (U ** exp_val)
                if m > 0:
                    rad_cond = f"{U} >= 0"
                    denoms: tuple[str, ...] = ()
                else:
                    rad_cond = f"{U} > 0"
                    denoms = (f"{U} khác 0",)
                return [
                    SeparableExplicitCandidate(
                        expr=y_pos,
                        branch_identity="Nhánh căn chẵn thực dương (+)",
                        real_root_restrictions=(rad_cond,),
                        denominator_exclusions=denoms,
                    ),
                    SeparableExplicitCandidate(
                        expr=y_neg,
                        branch_identity="Nhánh căn chẵn thực âm (-)",
                        real_root_restrictions=(rad_cond,),
                        denominator_exclusions=denoms,
                    ),
                ]
            else:
                # Odd m (e.g. p=4 => m=-3; p=2 => m=-1; p=-2 => m=3).
                if m == 1:
                    return [
                        SeparableExplicitCandidate(
                            expr=U,
                            branch_identity="Nhánh lũy thừa bậc 1",
                        )
                    ]
                elif m == -1:
                    return [
                        SeparableExplicitCandidate(
                            expr=1 / U,
                            branch_identity="Nhánh lũy thừa bậc -1",
                            denominator_exclusions=(f"{U} khác 0",),
                        )
                    ]
                else:
                    # |m| >= 3 odd. Two real representations covering positive and negative ranges:
                    # On U > 0: y_1 = U^(1/m)
                    # On U < 0 (so -U > 0): y_2 = - (-U)^(1/m)
                    exp_val = sp.Rational(1, m)
                    y_pos = U ** exp_val
                    y_neg = - ((-U) ** exp_val)
                    if m > 0:
                        pos_rad = f"{U} >= 0"
                        neg_rad = f"-({U}) >= 0"
                        denoms_odd: tuple[str, ...] = ()
                    else:
                        pos_rad = f"{U} > 0"
                        neg_rad = f"-({U}) > 0"
                        denoms_odd = (f"{U} khác 0",)
                    return [
                        SeparableExplicitCandidate(
                            expr=y_pos,
                            branch_identity="Nhánh căn lẻ thực (radicand >= 0)",
                            real_root_restrictions=(pos_rad,),
                            denominator_exclusions=denoms_odd,
                        ),
                        SeparableExplicitCandidate(
                            expr=y_neg,
                            branch_identity="Nhánh căn lẻ thực (radicand <= 0)",
                            real_root_restrictions=(neg_rad,),
                            denominator_exclusions=denoms_odd,
                        ),
                    ]

    # When explicit inversion is unsupported or produces complex transcendental equations,
    # return None to preserve the exact real implicit relation.
    return None


def _solve_explicit_separable(
    f_expr: sp.Expr,
    g_expr: sp.Expr,
    var: sp.Symbol,
    dep_var: sp.Symbol,
    c_sym: sp.Symbol,
) -> list[sp.Expr] | None:
    """Solve for explicit real solutions y(t) with unrestricted real integration constant c_sym in R.

    Conservative policy: Only inverts well-defined, safe symbolic patterns (constant, linear,
    logistic quadratic, monomial quadratic, and pure powers with integer exponents).
    For multiple-valued real roots (even roots or odd roots with real branch symmetry), returns
    all valid real branches.
    Never invokes unrestricted sp.solve() on arbitrary logarithmic or transcendental relations.
    Unsupported exponents return None to preserve the exact real implicit relation.
    """
    cands = _solve_explicit_separable_candidates(f_expr, g_expr, var, dep_var, c_sym)
    if cands is None:
        return None
    return [c.expr for c in cands]


class ODESeparableSolver(Solver):
    """Solver for separable differential equations: dy/dt = f(t)*g(y)."""

    def __init__(self, verifier: ODEVerifier | None = None) -> None:
        self.verifier = verifier or ODEVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type in (
            ProblemType.ODE_SEPARABLE,
            ProblemType.SOLVE_EQUATION,
        )

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        t0_start = time.perf_counter()
        raw = request.raw_input.strip()
        if not raw:
            raise InvalidInputError("Phương trình vi phân không được để trống (Equation cannot be empty).")

        parsed: ParsedODE = parse_ode_input(
            raw,
            target_variable=request.target_variable,
            parameters=dict(request.parameters),
        )

        var = parsed.independent_var
        dep_var = parsed.dependent_var
        yp_sym = sp.Symbol("y_prime")
        c_sym = sp.Symbol("C")

        # Solve standard_expr for y_prime: standard_expr = 0 => y_prime = rhs(t, y)
        try:
            yp_sols = sp.solve(parsed.standard_expr, yp_sym)
            if not yp_sols:
                raise ValueError("Không thể biểu diễn y' theo biến độc lập và hàm số.")
        except Exception:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="separability_check",
                    details="Không thể cô lập đạo hàm y' để kiểm tra tính tách biến.",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=("Không thể biểu diễn phương trình dưới dạng y' = F(t, y).",),
                execution_time_ms=elapsed,
            )

        # Filter real branches: equations like (y')^2 + 1 = 0 have no real derivative branches
        real_branches: list[sp.Expr] = [sp.simplify(s) for s in yp_sols if not s.has(sp.I)]
        if not real_branches:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="branch_analysis",
                    details="Phương trình không có nhánh đạo hàm thực (No real derivative branches).",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="Phương trình không có nghiệm thực",
                final_latex=r"\text{Không có nghiệm thực}",
                warnings=("Phương trình vi phân không có nghiệm thực vì không tồn tại nhánh đạo hàm thực trên tập số thực.",),
                execution_time_ms=elapsed,
            )

        # Classical homogeneous ODE: y' = F(y/x) must be solved by ODEClassicalHomogeneousSolver
        if parsed.is_classical_homogeneous:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="classical_homogeneous_ode_detected",
                    details=(
                        "Phương trình có dạng vi phân thuần nhất bậc 0: y' = F(y/x). "
                        "Phương pháp tách biến trực tiếp không áp dụng được; cần sử dụng ODEClassicalHomogeneousSolver với phép thế y = vx."
                    ),
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=(
                    "Phương trình là phương trình vi phân thuần nhất bậc 0 y' = F(y/x). "
                    "Vui lòng sử dụng phương thức giải phương trình thuần nhất (ODEClassicalHomogeneousSolver).",
                ),
                execution_time_ms=elapsed,
            )

        # Validate initial point in domain before processing
        if parsed.initial_condition is not None:
            t0, y0 = parsed.initial_condition
            for br in real_branches:
                is_valid_pt, pt_err = validate_initial_point_in_domain(
                    br,
                    var,
                    dep_var,
                    t0,
                    y0,
                    original_denominators=parsed.original_denominators,
                    leading_coeffs=parsed.leading_coeffs,
                )
                if not is_valid_pt:
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    return SolutionResponse(
                        status=SolutionStatus.INVALID_INPUT,
                        verification=VerificationResult(
                            status=VerificationStatus.NOT_APPLICABLE,
                            method="initial_point_domain_validation",
                            details=f"Điểm ban đầu ({t0}, {y0}) nằm ngoài miền xác định của phương trình vi phân: {pt_err}",
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        warnings=(
                            f"Điều kiện ban đầu ({t0}, {y0}) không hợp lệ: {pt_err} "
                            "(Invalid initial condition point for differential equation).",
                        ),
                        execution_time_ms=elapsed,
                    )

        steps: list[SolutionStep] = []
        step_num = 1
        domain_restrictions: list[str] = []
        user_warnings: list[str] = []
        verified_eq_roots: set[sp.Expr] = set()
        is_periodic_trig_eq = False
        is_periodic_complete_verified = True
        periodic_family_str = ""
        periodic_family_latex = ""

        if len(real_branches) > 1:
            user_warnings.append(
                "Lưu ý: Phương trình vi phân ẩn có nhiều nhánh đạo hàm. Các họ nghiệm được xác định theo từng nhánh phân tách (branch-wise solutions). Tại các điểm chuyển nhánh (như y = 0), có thể tồn tại các nghiệm ghép nhánh cấp C¹ chưa được bao quát hoàn toàn."
            )

        # Check domain restrictions from radicals in the real branches (e.g. sqrt(x) => x >= 0)
        for br in real_branches:
            for node in br.atoms(sp.Pow):
                base, exp = node.as_base_exp()
                if exp.is_Rational and exp.q % 2 == 0:
                    domain_restrictions.append(f"Điều kiện xác định: {base} >= 0 (biểu thức dưới căn bậc chẵn).")

        # Process each real branch
        branch_solutions: list[dict[str, Any]] = []

        for b_idx, rhs_expr in enumerate(real_branches, 1):
            c_branch_sym = sp.Symbol(f"C{b_idx}") if len(real_branches) > 1 else c_sym

            # Separate RHS into f(t) * g(y)
            factored_rhs = sp.factor(rhs_expr)
            f_cand, g_cand = factored_rhs.as_independent(dep_var, as_Add=False)
            is_separable = bool(
                dep_var not in f_cand.free_symbols
                and var not in g_cand.free_symbols
                and sp.simplify(f_cand * g_cand - rhs_expr) == 0
            )
            if not is_separable:
                f_cand, g_cand = sp.factor_terms(rhs_expr).as_independent(dep_var, as_Add=False)
                is_separable = bool(
                    dep_var not in f_cand.free_symbols
                    and var not in g_cand.free_symbols
                    and sp.simplify(f_cand * g_cand - rhs_expr) == 0
                )

            if not is_separable:
                is_homog, v_expr = check_classical_homogeneous_ode(rhs_expr, var, dep_var)
                if is_homog:
                    warn_msg = (
                        f"Phương trình vi phân có dạng thuần nhất bậc 0: y' = F(y/{var}) với F(v) = {v_expr}. "
                        f"Phương pháp thế thuần nhất y = v*{var} chưa được hỗ trợ trong phạm vi giải tách biến."
                    )
                    method_detail = "Phương trình vi phân thuần nhất bậc 0 (y' = F(y/x)), chưa hỗ trợ giải tự động bằng phép thế y = vx."
                else:
                    warn_msg = (
                        f"Biểu thức vế phải {rhs_expr} không có dạng tách biến f({var})*g({dep_var}) "
                        "(Non-separable differential equation)."
                    )
                    method_detail = "Phương trình không thể phân tách thành tích f(t)*g(y)."

                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="separability_check",
                        details=method_detail,
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=(warn_msg,),
                    execution_time_ms=elapsed,
                )

            if f_cand.could_extract_minus_sign():
                f_cand = -f_cand
                g_cand = -g_cand

            f_expr = sp.simplify(f_cand)
            g_expr = sp.simplify(g_cand)

            # Check denominator singularities in g(y) and f(x)
            try:
                _, g_denom = sp.fraction(g_expr)
                if g_denom != 1 and dep_var in g_denom.free_symbols:
                    denom_roots = sp.solve(g_denom, dep_var)
                    for dr in denom_roots:
                        if dr.is_real is not False and not dr.has(sp.I):
                            domain_restrictions.append(f"Điều kiện xác định: {dep_var} khác {dr} (mẫu số của g({dep_var}) khác 0).")
            except Exception:
                pass

            try:
                _, f_denom = sp.fraction(f_expr)
                if f_denom != 1 and var in f_denom.free_symbols:
                    f_denom_roots = sp.solve(f_denom, var)
                    for fdr in f_denom_roots:
                        if fdr.is_real is not False and not fdr.has(sp.I):
                            domain_restrictions.append(f"Điều kiện xác định: {var} khác {fdr} (mẫu số của f({var}) khác 0).")
            except Exception:
                pass

            # Equilibrium solutions g(y) = 0
            try:
                is_per, is_per_verified, fam_str, fam_latex, reps, per_assump = _detect_periodic_trig_family(g_expr, dep_var)
                if is_per:
                    is_periodic_trig_eq = True
                    is_periodic_complete_verified = is_per_verified
                    periodic_family_str = fam_str
                    periodic_family_latex = fam_latex
                    if per_assump:
                        domain_restrictions.extend(per_assump)
                    for r in reps:
                        # Verify against the original standard_expr
                        res_eq = parsed.standard_expr.subs([(yp_sym, 0), (dep_var, r)])
                        if _prove_symbolic_zero(res_eq, variable=var, domain_interval=parsed.interval):
                            verified_eq_roots.add(r)
                else:
                    raw_roots = sp.solve(g_expr, dep_var)
                    for r in raw_roots:
                        r_simp = sp.simplify(r)
                        if r_simp.is_real is not False and not r_simp.has(sp.I):
                            # Verify against the original standard_expr
                            res_eq = parsed.standard_expr.subs([(yp_sym, 0), (dep_var, r_simp)])
                            if _prove_symbolic_zero(res_eq, variable=var, domain_interval=parsed.interval):
                                verified_eq_roots.add(r_simp)
            except Exception:
                pass

            # Step: Identification (for first branch or each branch)
            branch_label = f" (Nhánh {b_idx})" if len(real_branches) > 1 else ""
            std_latex = f"\\frac{{d{dep_var}}}{{d{var}}} = \\left( {expr_to_latex(f_expr)} \\right) \\left( {expr_to_latex(g_expr)} \\right)"
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Nhận dạng dạng phương trình",
                    title=f"Nhận dạng phương trình vi phân tách biến{branch_label}",
                    description=(
                        f"Đưa phương trình về dạng chuẩn sau: ${dep_var}' = f({var}) g({dep_var})$ với "
                        f"$f({var}) = {expr_to_latex(f_expr)}$ và $g({dep_var}) = {expr_to_latex(g_expr)}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=parsed.canonical_eq,
                        expression_after=f"y' = ({f_expr})*({g_expr})",
                        latex_before=expr_to_latex(parsed.lhs_expr) + " = " + expr_to_latex(parsed.rhs_expr),
                        latex_after=std_latex,
                    ),
                )
            )
            step_num += 1

            # Step: Separate variables
            sep_latex = f"\\frac{{1}}{{{expr_to_latex(g_expr)}}} d{dep_var} = \\left( {expr_to_latex(f_expr)} \\right) d{var}"
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Phân tách biến số",
                    title=f"Phân tách biến số hai vế{branch_label}",
                    description=(
                        f"Vì $g({dep_var}) = {expr_to_latex(g_expr)}$, ta xét trường hợp ${expr_to_latex(g_expr)} \\ne 0$ "
                        f"và phân tách các biến về hai vế: "
                        f"$\\frac{{1}}{{{expr_to_latex(g_expr)}}}\\,d{dep_var} = {expr_to_latex(f_expr)}\\,d{var}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"d{dep_var}/d{var} = ({f_expr})*({g_expr})",
                        expression_after=f"(1/({g_expr}))*d{dep_var} = ({f_expr})*d{var}",
                        latex_before=std_latex,
                        latex_after=sep_latex,
                    ),
                )
            )
            step_num += 1

            # Integrate both sides with real calculus
            int_g = _real_integrate_reciprocal(g_expr, dep_var)
            int_f = sp.integrate(f_expr, var)

            if any(isinstance(node, sp.Integral) for node in sp.preorder_traversal(int_g)) or any(
                isinstance(node, sp.Integral) for node in sp.preorder_traversal(int_f)
            ):
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="separation_integration",
                        details="Một trong các tích phân phân tách không có nguyên hàm sơ cấp.",
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=("Tích phân không có dạng hàm sơ cấp (Non-elementary integral).",),
                    execution_time_ms=elapsed,
                )

            # Solve for explicit real y(t) branches with unrestricted real integration constant in R
            explicit_cands = _solve_explicit_separable_candidates(f_expr, g_expr, var, dep_var, c_branch_sym)
            explicit_sols = [c.expr for c in explicit_cands] if explicit_cands is not None else None

            branch_solutions.append({
                "rhs_expr": rhs_expr,
                "f_expr": f_expr,
                "g_expr": g_expr,
                "int_g": int_g,
                "int_f": int_f,
                "explicit_cands": explicit_cands,
                "explicit_sols": explicit_sols,
                "c_sym": c_branch_sym,
                "b_idx": b_idx,
            })

        # Step: Equilibrium solutions summary
        eq_roots_sorted = sorted(verified_eq_roots, key=str)
        if is_periodic_trig_eq and periodic_family_str:
            eq_desc = f"Họ nghiệm cân bằng tuần hoàn: ${periodic_family_latex}$ (đại diện: {', '.join(f'${dep_var} = {expr_to_latex(r)}$' for r in eq_roots_sorted)})"
            eq_roots_latex = f"{periodic_family_latex} \\; (\\text{{đại diện: }} {', '.join(expr_to_latex(r) for r in eq_roots_sorted)})"
        else:
            eq_desc_roots = f"${', '.join(f'{dep_var}_{{eq}} = {expr_to_latex(r)}' for r in eq_roots_sorted)}$" if eq_roots_sorted else "Không có nghiệm thực"
            first_g_rep = branch_solutions[0]["g_expr"] if branch_solutions else dep_var
            eq_desc = f"Xét phương trình $g({dep_var}) = 0 \\iff {expr_to_latex(first_g_rep)} = 0$ để tránh mất nghiệm khi chia hai vế: {eq_desc_roots}."
            eq_roots_latex = ", ".join(f"{dep_var} = {expr_to_latex(r)}" for r in eq_roots_sorted) if eq_roots_sorted else r"\emptyset"

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Nghiệm cân bằng",
                title="Xác định các nghiệm cân bằng (Equilibrium Solutions)",
                description=eq_desc,
                content=ExpressionStepContent(
                    expression_before=f"g({dep_var}) = 0",
                    expression_after=f"y_eq in [{', '.join(str(r) for r in eq_roots_sorted)}]",
                    latex_before=r"g(y) = 0",
                    latex_after=f"{dep_var}_{{eq}}: {eq_roots_latex}",
                ),
            )
        )
        step_num += 1

        # Check if initial condition hits an equilibrium solution directly
        if parsed.initial_condition is not None:
            t0, y0 = parsed.initial_condition
            hit_eq_val: sp.Expr | None = None
            for r in eq_roots_sorted:
                if _prove_symbolic_zero(y0 - r):
                    hit_eq_val = r
                    break

            if hit_eq_val is not None:
                first_g = branch_solutions[0]["g_expr"]
                first_f = branch_solutions[0]["f_expr"]
                uniq_status, uniq_reason, alt_sol, alt_dom = _check_equilibrium_uniqueness(
                    first_g, first_f, var, dep_var, t0, y0
                )

                if uniq_status == EquilibriumUniqueness.UNIQUE_PROVEN:
                    part_sol = hit_eq_val
                    part_sol_latex = f"{dep_var}({var}) = {expr_to_latex(hit_eq_val)}"
                    final_res_str = f"{dep_var}({var}) = {hit_eq_val}"
                    final_res_latex = part_sol_latex
                    eq_rule_name = "Áp dụng điều kiện ban đầu (Picard-Lindelöf)"
                    eq_title = "Nghiệm riêng trùng với nghiệm cân bằng duy nhất"
                    eq_desc = (
                        f"Giá trị ban đầu ${dep_var}({expr_to_latex(t0)}) = {expr_to_latex(y0)}$ trùng với nghiệm cân bằng ${dep_var} = {expr_to_latex(hit_eq_val)}$. "
                        f"Hàm $f({var}) g({dep_var})$ thỏa mãn điều kiện Lipschitz cục bộ theo ${dep_var}$ tại lân cận điểm ban đầu; "
                        f"theo định lý tồn tại và duy nhất nghiệm Picard–Lindelöf, nghiệm duy nhất của bài toán là hàm hằng ${dep_var}({var}) = {expr_to_latex(hit_eq_val)}$."
                    )
                    eq_method = "equilibrium_ivp_picard_lindelof_unique"
                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name=eq_rule_name,
                            title=eq_title,
                            description=eq_desc,
                            content=ExpressionStepContent(
                                expression_before=f"y({t0}) = {y0}",
                                expression_after=f"y({var}) = {hit_eq_val}",
                                latex_before=f"{dep_var}({expr_to_latex(t0)}) = {expr_to_latex(y0)}",
                                latex_after=part_sol_latex,
                            ),
                        )
                    )
                    verif_res = VerificationResult(
                        status=VerificationStatus.VERIFIED,
                        method=eq_method,
                        details=(
                            f"Kiểm chứng độc lập thành công ({eq_method}, Picard–Lindelöf nghiệm duy nhất): "
                            f"Biểu thức dư R({var}) ≡ 0 và nghiệm thỏa mãn điều kiện ban đầu {dep_var}({t0}) = {y0}."
                        ),
                    )

                elif uniq_status == EquilibriumUniqueness.NONUNIQUE_PROVEN:
                    part_sol = hit_eq_val
                    part_sol_latex = f"{dep_var}({var}) = {expr_to_latex(hit_eq_val)}"
                    final_res_str = f"{dep_var}_1({var}) = {hit_eq_val}, {dep_var}_2({var}) = {alt_sol} (cho {alt_dom})"
                    final_res_latex = (
                        f"{dep_var}_1({var}) = {expr_to_latex(hit_eq_val)}, \\quad "
                        f"{dep_var}_2({var}) = {expr_to_latex(alt_sol)} \\; ({alt_dom})"
                    )
                    eq_rule_name = "Áp dụng điều kiện ban đầu (Rẽ nhánh không duy nhất)"
                    eq_title = "Nghiệm không duy nhất do vi phạm điều kiện Lipschitz"
                    eq_desc = (
                        f"Giá trị ban đầu ${dep_var}({expr_to_latex(t0)}) = {expr_to_latex(y0)}$ trùng với nghiệm cân bằng ${dep_var} = {expr_to_latex(hit_eq_val)}$. "
                        f"Tuy nhiên, điều kiện Lipschitz bị vi phạm tại điểm $({expr_to_latex(t0)}, {expr_to_latex(y0)})$ và tích phân tách biến hội tụ ({uniq_reason}). "
                        f"Do đó, bài toán Cauchy có ít nhất hai nghiệm thực phân biệt:\n"
                        f"1) Nghiệm cân bằng: ${dep_var}_1({var}) = {expr_to_latex(hit_eq_val)}$\n"
                        f"2) Nhánh nghiệm rẽ: ${dep_var}_2({var}) = {expr_to_latex(alt_sol)}$ (${alt_dom}$)"
                    )
                    eq_method = "equilibrium_ivp_nonunique"
                    user_warnings.append(
                        f"Cảnh báo toán học: Điều kiện Lipschitz theo {dep_var} bị vi phạm tại điểm ({t0}, {y0}). "
                        f"Bài toán Cauchy tồn tại nhiều hơn một nghiệm thực: {final_res_str}."
                    )
                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name=eq_rule_name,
                            title=eq_title,
                            description=eq_desc,
                            content=ExpressionStepContent(
                                expression_before=f"y({t0}) = {y0}",
                                expression_after=final_res_str,
                                latex_before=f"{dep_var}({expr_to_latex(t0)}) = {expr_to_latex(y0)}",
                                latex_after=final_res_latex,
                            ),
                        )
                    )
                    verif_res = VerificationResult(
                        status=VerificationStatus.VERIFIED,
                        method=eq_method,
                        details=(
                            f"Kiểm chứng độc lập thành công ({eq_method}): Tồn tại ít nhất hai nghiệm thực phân biệt "
                            f"y_1 = {hit_eq_val} và y_2 = {alt_sol} ({alt_dom}) cùng thỏa mãn phương trình vi phân và điều kiện ban đầu."
                        ),
                    )

                else:  # UNIQUENESS_NOT_ESTABLISHED
                    part_sol = hit_eq_val
                    part_sol_latex = f"{dep_var}({var}) = {expr_to_latex(hit_eq_val)}"
                    final_res_str = f"{dep_var}({var}) = {hit_eq_val}"
                    final_res_latex = part_sol_latex
                    eq_rule_name = "Áp dụng điều kiện ban đầu (Tính duy nhất chưa khẳng định)"
                    eq_title = "Nghiệm cân bằng (Điều kiện Picard–Lindelöf không áp dụng)"
                    eq_desc = (
                        f"Giá trị ban đầu ${dep_var}({expr_to_latex(t0)}) = {expr_to_latex(y0)}$ trùng với nghiệm cân bằng ${dep_var} = {expr_to_latex(hit_eq_val)}$. "
                        f"Điều kiện đủ Picard–Lindelöf không áp dụng vì đạo hàm riêng không bị chặn ({uniq_reason}). "
                        f"Nghiệm cân bằng ${dep_var}({var}) = {expr_to_latex(hit_eq_val)}$ là một nghiệm của bài toán, "
                        "nhưng tính duy nhất của nghiệm chưa được khẳng định."
                    )
                    eq_method = "equilibrium_ivp_uniqueness_not_established"
                    user_warnings.append(
                        f"Lưu ý toán học: Điều kiện Picard–Lindelöf không áp dụng tại ({t0}, {y0}) ({uniq_reason}). "
                        "Tính duy nhất của nghiệm chưa được khẳng định (Uniqueness not established)."
                    )
                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name=eq_rule_name,
                            title=eq_title,
                            description=eq_desc,
                            content=ExpressionStepContent(
                                expression_before=f"y({t0}) = {y0}",
                                expression_after=f"y({var}) = {hit_eq_val}",
                                latex_before=f"{dep_var}({expr_to_latex(t0)}) = {expr_to_latex(y0)}",
                                latex_after=part_sol_latex,
                            ),
                        )
                    )
                    verif_res = VerificationResult(
                        status=VerificationStatus.VERIFIED,
                        method=eq_method,
                        details=(
                            f"Kiểm chứng thành công ({eq_method}): Nghiệm cân bằng y({var}) = {hit_eq_val} thỏa mãn "
                            f"phương trình vi phân và điều kiện ban đầu (tính duy nhất chưa khẳng định)."
                        ),
                    )

                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.SUCCESS if verif_res.status == VerificationStatus.VERIFIED else SolutionStatus.DISCREPANCY_DETECTED,
                    verification=verif_res,
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result=final_res_str,
                    final_latex=final_res_latex,
                    steps=tuple(steps),
                    domain_restrictions=tuple(dict.fromkeys(domain_restrictions)),
                    warnings=tuple(user_warnings),
                    execution_time_ms=elapsed,
                )

        # Build integration and resolution steps
        emitted_solutions: list[EmittedBranchSolution] = []

        for b_data in branch_solutions:
            b_idx = b_data["b_idx"]
            rhs_expr = b_data["rhs_expr"]
            f_expr = b_data["f_expr"]
            g_expr = b_data["g_expr"]
            int_g = b_data["int_g"]
            int_f = b_data["int_f"]
            explicit_sols = b_data["explicit_sols"]
            c_branch_sym = b_data["c_sym"]
            branch_label = f" (Nhánh {b_idx})" if len(branch_solutions) > 1 else ""

            int_latex = f"{expr_to_latex(int_g)} = {expr_to_latex(int_f)} + {expr_to_latex(c_branch_sym)}"
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Tích phân hai vế",
                    title=f"Tính tích phân hai vế và bổ sung hằng số tích phân ${c_branch_sym}${branch_label}",
                    description=(
                        f"Tính nguyên hàm trên tập số thực hai vế: "
                        f"$\\int \\frac{{1}}{{{expr_to_latex(g_expr)}}}\\,d{dep_var} = {expr_to_latex(int_g)}$ và "
                        f"$\\int \\left( {expr_to_latex(f_expr)} \\right)\\,d{var} = {expr_to_latex(int_f)} + {expr_to_latex(c_branch_sym)}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"int(1/({g_expr})) d{dep_var} = int({f_expr}) d{var}",
                        expression_after=f"{int_g} = {int_f} + {c_branch_sym}",
                        latex_before=f"\\int \\frac{{1}}{{{expr_to_latex(g_expr)}}} d{dep_var} = \\int \\left( {expr_to_latex(f_expr)} \\right) d{var}",
                        latex_after=int_latex,
                    ),
                )
            )
            step_num += 1

            # Handle initial condition for this branch if present
            explicit_cands = b_data.get("explicit_cands")
            if parsed.initial_condition is not None:
                t0, y0 = parsed.initial_condition
                if explicit_cands is not None:
                    for cand in explicit_cands:
                        explicit_sol = cand.expr
                        try:
                            c_sols = sp.solve(sp.Eq(explicit_sol.subs(var, t0), y0), c_branch_sym)
                            valid_c_sols = [c for c in c_sols if not c.has(sp.I)]
                        except Exception:
                            valid_c_sols = []

                        for c_val in valid_c_sols:
                            part_sol = sp.simplify(explicit_sol.subs(c_branch_sym, c_val))
                            # Confirm that part_sol at t0 genuinely equals y0 and is real
                            val_at_t0 = sp.simplify(part_sol.subs(var, t0))
                            if val_at_t0.has(sp.I) or not val_at_t0.is_real or not _prove_symbolic_zero(val_at_t0 - y0):
                                continue
                            part_str = f"{dep_var}({var}) = {part_sol}"
                            part_latex = f"{dep_var}({var}) = {expr_to_latex(part_sol)}"
                            b_restrs = list(domain_restrictions) + list(cand.real_root_restrictions) + list(cand.denominator_exclusions)
                            b_dom_int = _find_connected_domain_interval(part_sol, var, t0=t0, given_interval=parsed.interval)
                            emitted_solutions.append(
                                EmittedBranchSolution(
                                    solution_str=part_str,
                                    solution_latex=part_latex,
                                    explicit_expr=part_sol,
                                    derivative_branch=rhs_expr,
                                    f_expr=f_expr,
                                    g_expr=g_expr,
                                    int_f=int_f,
                                    int_g=int_g,
                                    c_sym=c_branch_sym,
                                    c_val=c_val,
                                    real_root_restrictions=cand.real_root_restrictions,
                                    denominator_exclusions=cand.denominator_exclusions,
                                    domain_interval=b_dom_int,
                                    domain_restrictions=tuple(dict.fromkeys(b_restrs)),
                                    branch_index=b_idx,
                                    branch_identity=cand.branch_identity,
                                )
                            )
                else:
                    c_val = sp.simplify(int_g.subs(dep_var, y0) - int_f.subs(var, t0))
                    if not (c_val.has(sp.I) or c_val.has(sp.nan) or c_val.has(sp.zoo)):
                        if c_val == 0:
                            part_str = f"{int_g} = {int_f}"
                            part_latex = f"{expr_to_latex(int_g)} = {expr_to_latex(int_f)}"
                        else:
                            part_str = f"{int_g} = {int_f + c_val}" if not c_val.is_number or c_val > 0 else f"{int_g} = {int_f} - {-c_val}"
                            part_latex = f"{expr_to_latex(int_g)} = {expr_to_latex(int_f + c_val)}"
                        b_dom_int = _find_connected_domain_interval(None, var, t0=t0, given_interval=parsed.interval)
                        emitted_solutions.append(
                            EmittedBranchSolution(
                                solution_str=part_str,
                                solution_latex=part_latex,
                                explicit_expr=None,
                                derivative_branch=rhs_expr,
                                f_expr=f_expr,
                                g_expr=g_expr,
                                int_f=int_f,
                                int_g=int_g,
                                c_sym=c_branch_sym,
                                c_val=c_val,
                                domain_interval=b_dom_int,
                                domain_restrictions=tuple(domain_restrictions),
                                branch_index=b_idx,
                                branch_identity=f"Hệ thức nghiệm ẩn nhánh {b_idx}",
                            )
                        )
            else:
                # General solution
                if explicit_cands is not None:
                    for cand in explicit_cands:
                        explicit_sol = cand.expr
                        gen_str = f"{dep_var}({var}) = {explicit_sol}"
                        gen_latex = f"{dep_var}({var}) = {expr_to_latex(explicit_sol)}"
                        b_restrs = list(domain_restrictions) + list(cand.real_root_restrictions) + list(cand.denominator_exclusions)
                        b_dom_int = _find_connected_domain_interval(explicit_sol, var, t0=None, given_interval=parsed.interval)
                        emitted_solutions.append(
                            EmittedBranchSolution(
                                solution_str=gen_str,
                                solution_latex=gen_latex,
                                explicit_expr=explicit_sol,
                                derivative_branch=rhs_expr,
                                f_expr=f_expr,
                                g_expr=g_expr,
                                int_f=int_f,
                                int_g=int_g,
                                c_sym=c_branch_sym,
                                c_val=None,
                                real_root_restrictions=cand.real_root_restrictions,
                                denominator_exclusions=cand.denominator_exclusions,
                                domain_interval=b_dom_int,
                                domain_restrictions=tuple(dict.fromkeys(b_restrs)),
                                branch_index=b_idx,
                                branch_identity=cand.branch_identity,
                            )
                        )
                else:
                    gen_str = f"{int_g} = {int_f} + {c_branch_sym}"
                    gen_latex = f"{expr_to_latex(int_g)} = {expr_to_latex(int_f)} + {expr_to_latex(c_branch_sym)}"
                    b_dom_int = _find_connected_domain_interval(None, var, t0=None, given_interval=parsed.interval)
                    emitted_solutions.append(
                        EmittedBranchSolution(
                            solution_str=gen_str,
                            solution_latex=gen_latex,
                            explicit_expr=None,
                            derivative_branch=rhs_expr,
                            f_expr=f_expr,
                            g_expr=g_expr,
                            int_f=int_f,
                            int_g=int_g,
                            c_sym=c_branch_sym,
                            c_val=None,
                            domain_interval=b_dom_int,
                            domain_restrictions=tuple(domain_restrictions),
                            branch_index=b_idx,
                            branch_identity=f"Hệ thức nghiệm ẩn nhánh {b_idx}",
                        )
                    )

        if not emitted_solutions:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="ivp_domain_mismatch",
                    details="Điều kiện ban đầu nằm ngoài miền xác định thực của các nhánh đạo hàm.",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=("Không tìm thấy nghiệm thực thỏa mãn điều kiện ban đầu đã cho.",),
                execution_time_ms=elapsed,
            )

        # Deduplicate identical branch results (e.g. y = 0 from multiple branches)
        seen_strs: set[str] = set()
        dedup_solutions: list[EmittedBranchSolution] = []
        for em in emitted_solutions:
            if em.solution_str not in seen_strs:
                seen_strs.add(em.solution_str)
                dedup_solutions.append(em)
        emitted_solutions = dedup_solutions

        # Assemble final result and final LaTeX
        if len(emitted_solutions) == 1:
            final_sol_str = emitted_solutions[0].solution_str
            final_latex_sol = emitted_solutions[0].solution_latex
        else:
            final_sol_str = "  hoặc  ".join(em.solution_str for em in emitted_solutions)
            final_latex_sol = r" \quad\text{hoặc}\quad ".join(em.solution_latex for em in emitted_solutions)

        # In general solution mode, append verified equilibrium solutions if present
        if parsed.initial_condition is None and eq_roots_sorted:
            if is_periodic_trig_eq and periodic_family_str:
                eq_suffix_str = f" ; Nghiệm cân bằng: {periodic_family_str} (đại diện: " + ", ".join(f"{dep_var} = {r}" for r in eq_roots_sorted) + ")"
                eq_suffix_latex = r" \quad\text{hoặc nghiệm cân bằng: } " + f"{periodic_family_latex} \\; (\\text{{đại diện: }} " + ", ".join(f"{dep_var} = {expr_to_latex(r)}" for r in eq_roots_sorted) + ")"
            else:
                eq_suffix_str = " ; Nghiệm cân bằng: " + ", ".join(f"{dep_var} = {r}" for r in eq_roots_sorted)
                eq_suffix_latex = r" \quad\text{hoặc nghiệm cân bằng: } " + ", ".join(f"{dep_var} = {expr_to_latex(r)}" for r in eq_roots_sorted)
            final_sol_str += eq_suffix_str
            final_latex_sol += eq_suffix_latex

        # Verification: check all branch solutions with explicit provenance
        for em in emitted_solutions:
            if em.explicit_expr is not None:
                # Direct check: compute dy/dt and substitute into parsed.standard_expr and derivative_branch
                try:
                    dy_dt = sp.diff(em.explicit_expr, var)
                    # Verify against original ODE
                    res_ode = sp.simplify(parsed.standard_expr.subs([(yp_sym, dy_dt), (dep_var, em.explicit_expr)]))
                    is_res_ode_zero = _prove_symbolic_zero(
                        res_ode,
                        (em.c_sym,),
                        domain_interval=em.domain_interval,
                        variable=var,
                    )

                    # Verify against original derivative branch
                    res_branch = sp.simplify(dy_dt - em.derivative_branch.subs(dep_var, em.explicit_expr))
                    is_res_branch_zero = _prove_symbolic_zero(
                        res_branch,
                        (em.c_sym,),
                        domain_interval=em.domain_interval,
                        variable=var,
                    )

                    # Also verify initial condition if present
                    ic_ok = True
                    if parsed.initial_condition is not None:
                        t0, y0 = parsed.initial_condition
                        ic_diff = sp.simplify(em.explicit_expr.subs(var, t0) - y0)
                        ic_ok = _prove_symbolic_zero(
                            ic_diff,
                            (em.c_sym,),
                            domain_interval=em.domain_interval,
                            variable=var,
                        )

                    if is_res_ode_zero and is_res_branch_zero and ic_ok:
                        em.verification = VerificationResult(
                            status=VerificationStatus.VERIFIED,
                            method="ode_residual_symbolic_zero_check",
                            details=f"Kiểm chứng độc lập thành công: Biểu thức dư R({var}) ≡ 0 bằng phương pháp ký hiệu cho nhánh {em.branch_index}.",
                        )
                    elif not is_res_ode_zero or not is_res_branch_zero:
                        em.verification = VerificationResult(
                            status=VerificationStatus.FAILED,
                            method="ode_residual_mismatch",
                            details=f"Biểu thức dư R({var}) khác 0 đối với nhánh {em.branch_index}.",
                        )
                    else:
                        em.verification = VerificationResult(
                            status=VerificationStatus.FAILED,
                            method="initial_condition_mismatch",
                            details=f"Nghiệm không thỏa mãn điều kiện ban đầu đối với nhánh {em.branch_index}.",
                        )
                except Exception as exc:
                    em.verification = VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="verification_exception",
                        details=f"Không thể kiểm chứng nhánh {em.branch_index}: {exc}",
                    )
            else:
                # Implicit verification
                v_res = self.verifier.verify_implicit(
                    potential_phi=em.int_g - em.int_f,
                    x_sym=var,
                    y_sym=dep_var,
                    rhs_f_expr=em.f_expr,
                    rhs_g_expr=em.g_expr,
                    initial_condition=parsed.initial_condition,
                    c_val=em.c_val,
                    domain_interval=em.domain_interval,
                    domain_restrictions=tuple(domain_restrictions),
                )
                em.verification = v_res

        verif_results: list[VerificationResult] = [
            em.verification for em in emitted_solutions if em.verification is not None
        ]

        # Check branch completeness in general solution mode
        covered_branches = {em.branch_index for em in emitted_solutions}
        all_branches_covered = len(covered_branches) >= len(real_branches)

        # Synthesize verification result
        if any(v.status == VerificationStatus.FAILED for v in verif_results):
            failed_v = next(v for v in verif_results if v.status == VerificationStatus.FAILED)
            final_verif = failed_v
            sol_status = SolutionStatus.DISCREPANCY_DETECTED
        elif any(v.status == VerificationStatus.UNVERIFIED for v in verif_results):
            final_verif = VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="branch_inconclusive",
                details="Một số nhánh không thể kiểm chứng hoàn toàn bằng phương pháp ký hiệu.",
            )
            sol_status = SolutionStatus.UNVERIFIED
        elif parsed.initial_condition is None and not all_branches_covered:
            final_verif = VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="incomplete_branch_coverage",
                details="Không thể giải hoặc kiểm chứng đầy đủ tất cả các nhánh đạo hàm thực của phương trình.",
            )
            sol_status = SolutionStatus.UNVERIFIED
        elif is_periodic_trig_eq and not is_periodic_complete_verified:
            final_verif = VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="incomplete_periodic_equilibrium_coverage",
                details="Không thể khẳng định tính đầy đủ của họ nghiệm cân bằng tuần hoàn do tham số chưa xác định thực khác 0.",
            )
            sol_status = SolutionStatus.UNVERIFIED
        else:
            final_verif = VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="ode_all_branches_symbolic_verified",
                details="Kiểm chứng độc lập thành công: Tất cả các nhánh nghiệm đều thỏa mãn phương trình vi phân bằng phương pháp ký hiệu.",
            )
            sol_status = SolutionStatus.SUCCESS

        elapsed = (time.perf_counter() - t0_start) * 1000.0
        all_dom_restrs = list(domain_restrictions)
        for em in emitted_solutions:
            all_dom_restrs.extend(em.domain_restrictions)
        return SolutionResponse(
            status=sol_status,
            verification=final_verif,
            raw_input=request.raw_input,
            canonical_input=parsed.canonical_eq,
            final_result=final_sol_str,
            final_latex=final_latex_sol,
            steps=tuple(steps),
            domain_restrictions=tuple(dict.fromkeys(all_dom_restrs)),
            warnings=tuple(user_warnings),
            execution_time_ms=elapsed,
            branch_solutions=tuple(em.to_branch_solution() for em in emitted_solutions),
        )

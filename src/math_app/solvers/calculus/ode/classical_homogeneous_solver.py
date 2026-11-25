"""Dedicated solver for classical degree-0 homogeneous first-order ODEs: y' = F(y/x)."""

from __future__ import annotations

from dataclasses import dataclass
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
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.input.ode_parser import ParsedODE, parse_ode_input
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.verification.calculus.ode_verifier import (
    ODEVerifier,
    _prove_symbolic_zero,
    evaluate_initial_point_domain,
)


def _detect_periodic_trig_family(
    g_expr: sp.Expr,
    dep_var: sp.Symbol,
) -> tuple[bool, bool, str, str, list[sp.Expr], list[str]]:
    """Detect if g(v) has periodic roots from sin(a*v) or cos(a*v).

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


@dataclass(frozen=True)
class HomogeneousBranchCandidate:
    """Explicit candidate branch for v(x) with domain provenance."""

    v_expr: sp.Expr
    branch_identity: str
    real_root_restrictions: tuple[str, ...] = ()
    denominator_exclusions: tuple[str, ...] = ()
    u_expr: sp.Expr | None = None
    branch_sign: str = "any"  # "pos" (U > 0), "neg" (U < 0), "nonzero" (U != 0), "any"
    p_power: int = 1
    coeff_val: sp.Expr = sp.Integer(1)
    b_val: sp.Expr = sp.Integer(0)


def _invert_homogeneous_relation_candidates(
    int_v_expr: sp.Expr,
    v_sym: sp.Symbol,
    var: sp.Symbol,
    c_sym: sp.Symbol,
) -> list[HomogeneousBranchCandidate] | None:
    """Invert int_v(v) = ln|x| + C for v conservatively without unrestricted sp.solve().

    Returns list of explicit real branch candidates for v(x) with domain provenance, or None if transcendental.
    """
    int_x = sp.log(sp.Abs(var)) + c_sym

    # 1. Constant int_v (degenerate)
    if v_sym not in int_v_expr.free_symbols:
        return None

    # 2. Linear or monomial quadratic in v
    if int_v_expr.is_polynomial(v_sym):
        poly_v = sp.Poly(int_v_expr, v_sym)
        deg = poly_v.degree()
        coeffs = poly_v.all_coeffs()
        if deg == 1:
            a, b = coeffs[0], coeffs[1]
            if a != 0:
                sol = sp.simplify((int_x - b) / a)
                return [
                    HomogeneousBranchCandidate(
                        v_expr=sol,
                        branch_identity="Nhánh tuyến tính",
                        u_expr=sol,
                        branch_sign="any",
                        p_power=1,
                        coeff_val=a,
                        b_val=b,
                    )
                ]
        elif deg == 2 and coeffs[1] == 0:
            # Monomial quadratic: a*v^2 + c0 = ln|x| + C => v^2 = (ln|x| + C - c0) / a = U
            a, c0 = coeffs[0], coeffs[2]
            U = sp.simplify((int_x - c0) / a)
            # Two real branches: +sqrt(U) and -sqrt(U) on U >= 0 (strictly U > 0 if y != 0)
            u_cond = f"{U} >= 0"
            return [
                HomogeneousBranchCandidate(
                    v_expr=sp.sqrt(U),
                    branch_identity="Nhánh thực dương (+)",
                    real_root_restrictions=(u_cond,),
                    u_expr=U,
                    branch_sign="pos",
                    p_power=2,
                    coeff_val=a,
                    b_val=c0,
                ),
                HomogeneousBranchCandidate(
                    v_expr=-sp.sqrt(U),
                    branch_identity="Nhánh thực âm (-)",
                    real_root_restrictions=(u_cond,),
                    u_expr=U,
                    branch_sign="pos",
                    p_power=2,
                    coeff_val=a,
                    b_val=c0,
                ),
            ]

    # 3. Pure power: a * v^p + b with integer p != 0
    p_val = None
    coeff_val = None
    b_val = sp.Integer(0)

    cand = int_v_expr
    if cand.is_Add:
        const_terms = []
        v_terms = []
        for arg in cand.args:
            if v_sym in arg.free_symbols:
                v_terms.append(arg)
            else:
                const_terms.append(arg)
        if len(v_terms) == 1:
            cand = v_terms[0]
            b_val = sum(const_terms)
        else:
            cand = None

    if cand is not None:
        if cand.is_Pow and cand.base == v_sym:
            coeff_val = sp.Integer(1)
            p_val = cand.exp
        elif cand.is_Mul:
            c_part, rest = cand.as_coeff_Mul()
            if rest.is_Pow and rest.base == v_sym:
                coeff_val = c_part
                p_val = rest.exp
            elif rest == v_sym:
                coeff_val = c_part
                p_val = sp.Integer(1)
        elif cand == v_sym:
            coeff_val = sp.Integer(1)
            p_val = sp.Integer(1)

    if coeff_val is not None and p_val is not None and p_val.is_integer and p_val != 0:
        p_int = int(p_val)
        U = sp.simplify((int_x - b_val) / coeff_val)
        if p_int == 1:
            return [
                HomogeneousBranchCandidate(
                    v_expr=sp.simplify(U),
                    branch_identity="Nhánh lũy thừa bậc 1",
                    u_expr=U,
                    branch_sign="any",
                    p_power=1,
                    coeff_val=coeff_val,
                    b_val=b_val,
                )
            ]
        elif p_int == -1:
            denom_cond = f"{U} khác 0"
            return [
                HomogeneousBranchCandidate(
                    v_expr=sp.simplify(1 / U),
                    branch_identity="Nhánh lũy thừa bậc -1",
                    denominator_exclusions=(denom_cond,),
                    u_expr=U,
                    branch_sign="nonzero",
                    p_power=-1,
                    coeff_val=coeff_val,
                    b_val=b_val,
                )
            ]
        elif p_int % 2 == 0:
            exp_val = sp.Rational(1, p_int)
            pos_b = U ** exp_val
            neg_b = -(U ** exp_val)
            if p_int > 0:
                rad_cond = f"{U} >= 0"
                denoms: tuple[str, ...] = ()
            else:
                rad_cond = f"{U} > 0"
                denoms = (f"{U} khác 0",)
            return [
                HomogeneousBranchCandidate(
                    v_expr=pos_b,
                    branch_identity="Nhánh căn chẵn thực dương (+)",
                    real_root_restrictions=(rad_cond,),
                    denominator_exclusions=denoms,
                    u_expr=U,
                    branch_sign="pos",
                    p_power=p_int,
                    coeff_val=coeff_val,
                    b_val=b_val,
                ),
                HomogeneousBranchCandidate(
                    v_expr=neg_b,
                    branch_identity="Nhánh căn chẵn thực âm (-)",
                    real_root_restrictions=(rad_cond,),
                    denominator_exclusions=denoms,
                    u_expr=U,
                    branch_sign="pos",
                    p_power=p_int,
                    coeff_val=coeff_val,
                    b_val=b_val,
                ),
            ]
        else:
            # Odd integer p_int with |p_int| >= 3 (e.g. 3, -3, 5, -5)
            # Mathematically correct real odd-root semantics without complex principal roots:
            # For U > 0: v = U^(1/p) > 0
            # For U < 0: -U > 0, v = - (-U)^(1/p) < 0
            # For U = 0: v = 0 (when p > 0; when p < 0, U = 0 is excluded).
            exp_val = sp.Rational(1, p_int)
            pos_b = U ** exp_val
            neg_b = -((-U) ** exp_val)
            if p_int > 0:
                pos_rad = f"{U} >= 0"
                neg_rad = f"-({U}) >= 0"
                denoms_odd: tuple[str, ...] = ()
            else:
                pos_rad = f"{U} > 0"
                neg_rad = f"-({U}) > 0"
                denoms_odd = (f"{U} khác 0",)
            return [
                HomogeneousBranchCandidate(
                    v_expr=pos_b,
                    branch_identity="Nhánh căn lẻ thực (radicand >= 0)",
                    real_root_restrictions=(pos_rad,),
                    denominator_exclusions=denoms_odd,
                    u_expr=U,
                    branch_sign="pos",
                    p_power=p_int,
                    coeff_val=coeff_val,
                    b_val=b_val,
                ),
                HomogeneousBranchCandidate(
                    v_expr=neg_b,
                    branch_identity="Nhánh căn lẻ thực (radicand <= 0)",
                    real_root_restrictions=(neg_rad,),
                    denominator_exclusions=denoms_odd,
                    u_expr=U,
                    branch_sign="neg",
                    p_power=p_int,
                    coeff_val=coeff_val,
                    b_val=b_val,
                ),
            ]

    # For logarithmic, trigonometric, or transcendental relations,
    # return None to strictly preserve the exact real implicit relation.
    return None


def _invert_homogeneous_relation_conservative(
    int_v_expr: sp.Expr,
    v_sym: sp.Symbol,
    var: sp.Symbol,
    c_sym: sp.Symbol,
) -> list[sp.Expr] | None:
    """Invert int_v(v) = ln|x| + C for v conservatively without unrestricted sp.solve().

    Returns list of explicit real expressions for v(x), or None if transcendental.
    """
    cands = _invert_homogeneous_relation_candidates(int_v_expr, v_sym, var, c_sym)
    if cands is None:
        return None
    return [c.v_expr for c in cands]


def _resolve_homogeneous_branch_domain(
    cand: HomogeneousBranchCandidate,
    var: sp.Symbol,
    c_val: sp.Expr | float | None,
    x0: sp.Expr | float | None = None,
    parsed: ParsedODE | None = None,
) -> tuple[tuple[sp.Expr | float, sp.Expr | float], tuple[str, ...]]:
    """Resolve mathematically exact connected domain interval and restrictions for a branch.

    Returns ((dom_low, dom_high), domain_restrictions).
    """
    # 1. Determine base connected component side with respect to singularity x = 0
    if x0 is not None:
        try:
            x0_num = float(sp.N(x0))
            is_x_pos = x0_num > 0
        except Exception:
            is_x_pos = True
    else:
        is_x_pos = True

    # 2. Check if y = 0 is excluded by the differential equation
    y_zero_excluded = False
    if parsed is not None:
        dep_var = parsed.dependent_var
        for d in parsed.original_denominators:
            if dep_var in d.free_symbols:
                try:
                    if sp.simplify(d.subs(dep_var, 0)) == 0:
                        y_zero_excluded = True
                        break
                except Exception:
                    pass
        if not y_zero_excluded and parsed.homogeneous_F_v is not None:
            v_sym = sp.Symbol("_v_ratio")
            for node in sp.preorder_traversal(parsed.homogeneous_F_v):
                if isinstance(node, sp.Pow) and node.exp.is_negative:
                    if v_sym in node.base.free_symbols and node.base.subs(v_sym, 0) == 0:
                        y_zero_excluded = True
                        break
    if cand.p_power < 0:
        y_zero_excluded = True

    # 3. If no U expression or no coeff_val (e.g. constant ray y = Cx), interval is (0, oo) or (-oo, 0)
    if cand.u_expr is None or cand.coeff_val is None:
        if is_x_pos:
            return (0, sp.oo), (f"{var} > 0",)
        else:
            return (-sp.oo, 0), (f"{var} < 0",)

    # 4. Resolve boundary point |x| = exp(b - C)
    c_eff = c_val if c_val is not None else sp.Symbol("C")
    b_val = cand.b_val if cand.b_val is not None else sp.Integer(0)
    coeff_val = cand.coeff_val if cand.coeff_val is not None else sp.Integer(1)

    try:
        coeff_num = float(sp.N(coeff_val))
    except Exception:
        coeff_num = 1.0

    K = b_val - c_eff
    bound = sp.exp(K)

    # Effective branch direction
    branch_sign = cand.branch_sign
    if coeff_num < 0:
        if branch_sign == "pos":
            branch_sign = "neg"
        elif branch_sign == "neg":
            branch_sign = "pos"

    restrs: list[str] = []
    if branch_sign == "pos":
        # Requires |x| > bound
        if is_x_pos:
            dom = (bound, sp.oo)
            restrs.append(f"{var} > {bound}")
        else:
            dom = (-sp.oo, -bound)
            restrs.append(f"{var} < -{bound}")
        if c_val is None:
            restrs.append(f"|{var}| > exp({b_val} - C)" if b_val != 0 else f"|{var}| > exp(-C)")
            restrs.append(f"Thành phần chính ({var} > 0): ({bound}, oo)")
            restrs.append(f"Thành phần đối xứng ({var} < 0): (-oo, -{bound})")
    elif branch_sign == "neg":
        # Requires |x| < bound (and x != 0)
        if is_x_pos:
            dom = (0, bound)
            restrs.append(f"0 < {var} < {bound}")
        else:
            dom = (-bound, 0)
            restrs.append(f"-{bound} < {var} < 0")
        if c_val is None:
            restrs.append(f"0 < |{var}| < exp({b_val} - C)" if b_val != 0 else f"0 < |{var}| < exp(-C)")
            restrs.append(f"Thành phần chính ({var} > 0): (0, {bound})")
            restrs.append(f"Thành phần đối xứng ({var} < 0): (-{bound}, 0)")
    elif branch_sign == "nonzero" or y_zero_excluded:
        # Requires |x| != bound (and x != 0)
        if x0 is not None:
            try:
                x0_n = abs(float(sp.N(x0)))
                bound_n = float(sp.N(bound))
                if x0_n > bound_n:
                    dom = (bound, sp.oo) if is_x_pos else (-sp.oo, -bound)
                else:
                    dom = (0, bound) if is_x_pos else (-bound, 0)
            except Exception:
                dom = (0, sp.oo) if is_x_pos else (-sp.oo, 0)
        else:
            dom = (bound, sp.oo) if is_x_pos else (-sp.oo, -bound)
        restrs.append(f"|{var}| khác {bound}")
    else:
        dom = (0, sp.oo) if is_x_pos else (-sp.oo, 0)
        restrs.append(f"{var} khác 0")

    if y_zero_excluded:
        restrs.append(f"{parsed.dependent_var} khác 0" if parsed else "y khác 0")

    return dom, tuple(dict.fromkeys(restrs))


class ODEClassicalHomogeneousSolver(Solver):
    """Solver for first-order classical homogeneous differential equations:

    y' = F(y / x) (homogeneous of degree 0).

    Standard method of solution:
    1. Identify independent variable x and dependent variable y. Domain restriction: x != 0.
    2. Substitute v = y / x <=> y = v * x => y' = v + x * (dv/dx).
    3. Equation becomes: x * (dv/dx) = F(v) - v.
    4. If F(v) - v = 0 has roots v0: straight-line equilibrium rays y = v0 * x.
    5. Non-equilibrium: separate variables dv / (F(v) - v) = dx / x.
    6. Integrate: \\int dv / (F(v) - v) = ln|x| + C.
    7. Back-substitute v = y / x and solve for y(x).
    8. Independently verify the solution.
    """

    def __init__(self, verifier: ODEVerifier | None = None) -> None:
        self.verifier = verifier or ODEVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type in (
            ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
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
        c_sym = sp.Symbol("C")
        v_sym = sp.Symbol("v", real=True)

        if not parsed.is_classical_homogeneous or parsed.homogeneous_F_v is None:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="classical_homogeneity_check",
                    details="Phương trình không phải phương trình vi phân thuần nhất bậc 0 dạng y' = F(y/x).",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=("Phương trình không có dạng vi phân thuần nhất bậc 0 y' = F(y/x).",),
                execution_time_ms=elapsed,
            )

        # F(v) where _v_ratio is replaced by v_sym
        F_v = sp.simplify(parsed.homogeneous_F_v.subs(sp.Symbol("_v_ratio", real=True), v_sym))
        rhs_f_xy = sp.simplify(F_v.subs(v_sym, dep_var / var))

        domain_restrictions: list[str] = [
            f"Điều kiện xác định: {var} khác 0 (Miền xác định không chứa điểm kỳ dị {var} = 0)."
        ]
        if parsed.original_domain_restrictions:
            domain_restrictions.extend(parsed.original_domain_restrictions)

        user_warnings: list[str] = []

        # Validate Cauchy IVP conditions
        if parsed.initial_condition is not None:
            x0, y0 = parsed.initial_condition

            if x0.has(sp.zoo, sp.nan, sp.oo, -sp.oo) or y0.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
                raise InvalidInputError(
                    "Điều kiện ban đầu phải là các số thực hữu hạn (Initial condition coordinates must be finite real numbers)."
                )
            if x0.is_real is False or y0.is_real is False or (x0.has(sp.I) and not sp.simplify(x0).is_real):
                raise InvalidInputError(
                    "Điều kiện ban đầu phải là số thực (Initial condition coordinates must be real numbers)."
                )

            if _prove_symbolic_zero(x0) or sp.simplify(x0) == 0:
                raise InvalidInputError(
                    f"Điểm ban đầu {var}0 = 0 là điểm kỳ dị của phương trình thuần nhất cấp một (x0 cannot be zero)."
                )

            pt_stat, pt_err = evaluate_initial_point_domain(
                None,
                var,
                dep_var,
                x0,
                y0,
                original_denominators=parsed.original_denominators,
                leading_coeffs=parsed.leading_coeffs,
                source_constraints=getattr(parsed, "original_domain_constraints", ()),
            )
            if pt_stat == "invalid":
                raise InvalidInputError(f"Điều kiện ban đầu ({x0}, {y0}) không hợp lệ: {pt_err}")
            if pt_stat == "unknown":
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.UNVERIFIED,
                    verification=VerificationResult(
                        status=VerificationStatus.UNVERIFIED,
                        method="initial_condition_domain_unverified",
                        details=f"Không thể xác nhận điều kiện ban đầu ({x0}, {y0}) thuộc miền xác định: {pt_err}",
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=tuple(domain_restrictions),
                    warnings=(f"Không thể xác nhận điều kiện ban đầu ({x0}, {y0}): {pt_err}",),
                    execution_time_ms=elapsed,
                )

        steps: list[SolutionStep] = []
        step_num = 1

        # Step 1: Classification & Identification
        f_v_latex = expr_to_latex(F_v)
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Nhận dạng phương trình thuần nhất bậc 0",
                title="Kiểm tra tính thuần nhất bậc 0 và đặt biến phụ",
                description=(
                    f"Phương trình có dạng vi phân thuần nhất bậc 0: ${dep_var}' = F\\left(\\frac{{{dep_var}}}{{{var}}}\\right)$ "
                    f"với $F(v) = {f_v_latex}$. "
                    f"Miền xác định đòi hỏi ${var} \\ne 0$."
                ),
                content=ExpressionStepContent(
                    expression_before=parsed.canonical_eq,
                    expression_after=f"{dep_var}' = F({dep_var}/{var}) = {F_v}",
                    latex_before=expr_to_latex(parsed.lhs_expr) + " = " + expr_to_latex(parsed.rhs_expr),
                    latex_after=f"{dep_var}' = {f_v_latex}",
                ),
                equation_latex=f"{dep_var}' = {f_v_latex}",
            )
        )
        step_num += 1

        # Step 2: Substitution y = v*x => y' = v + x*v'
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Phép thế hàm phụ v = y/x",
                title="Biến đổi đạo hàm theo biến phụ v(x)",
                description=(
                    f"Đặt $v = \\frac{{{dep_var}}}{{{var}}} \\iff {dep_var} = v \\cdot {var}$. "
                    f"Lấy đạo hàm theo biến ${var}$ bằng quy tắc tích số: "
                    f"${dep_var}' = v + {var} \\frac{{dv}}{{{dvar_name(var)}}}$."
                ),
                content=ExpressionStepContent(
                    expression_before=f"{dep_var} = v*{var}",
                    expression_after=f"{dep_var}' = v + {var}*v'",
                    latex_before=f"{dep_var} = v \\cdot {var}",
                    latex_after=f"{dep_var}' = v + {var}\\frac{{dv}}{{{dvar_name(var)}}}",
                ),
                equation_latex=f"{dep_var}' = v + {var}\\frac{{dv}}{{{dvar_name(var)}}}",
            )
        )
        step_num += 1

        # Step 3: Transformed equation x * v' = F(v) - v
        G_v = sp.simplify(F_v - v_sym)
        g_v_latex = expr_to_latex(G_v)

        # -------------------------------------------------------------
        # Case 2.1: Critical case F(v) - v is identically zero (y' = y/x)
        # -------------------------------------------------------------
        if _prove_symbolic_zero(G_v):
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Biến đổi về phương trình vi phân biến phụ",
                    title="Thu gọn phương trình cho hàm phụ v(x)",
                    description=(
                        f"Thay vào phương trình ta được: $v + {var}\\frac{{dv}}{{{dvar_name(var)}}} = F(v) "
                        f"\\iff {var}\\frac{{dv}}{{{dvar_name(var)}}} = F(v) - v = 0$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"v + {var}*v' = {F_v}",
                        expression_after=f"{var}*v' = 0",
                        latex_before=f"v + {var}\\frac{{dv}}{{{dvar_name(var)}}} = {f_v_latex}",
                        latex_after=f"{var}\\frac{{dv}}{{{dvar_name(var)}}} = 0",
                    ),
                    equation_latex=f"{var}\\frac{{dv}}{{{dvar_name(var)}}} = 0",
                )
            )
            step_num += 1

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Giải phương trình hàm phụ đồng nhất",
                    title="Xác định hàm phụ v(x) là hàm hằng",
                    description=(
                        f"Vì $F(v) - v \\equiv 0$ đồng nhất, phương trình trở thành ${var}\\frac{{dv}}{{{dvar_name(var)}}} = 0$. "
                        f"Với điều kiện ${var} \\ne 0$, ta có $\\frac{{dv}}{{{dvar_name(var)}}} = 0$. "
                        f"Tích phân suy ra hàm phụ là hằng số: $v({var}) = C$ với $C \\in \\mathbb{{R}}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"{var}*v' = 0",
                        expression_after="v = C",
                        latex_before=f"{var}\\frac{{dv}}{{{dvar_name(var)}}} = 0",
                        latex_after=f"v({var}) = C",
                    ),
                    equation_latex=f"v({var}) = C",
                )
            )
            step_num += 1

            gen_sol = sp.simplify(c_sym * var)
            gen_latex = f"{dep_var}({var}) = C {var}"
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Thế ngược và kết luận nghiệm tổng quát",
                    title="Nghiệm tổng quát của phương trình thuần nhất",
                    description=(
                        f"Thế ngược $v = \\frac{{{dep_var}}}{{{var}}}$: "
                        f"$\\frac{{{dep_var}}}{{{var}}} = C \\iff {dep_var}({var}) = C {var}$ "
                        f"(xác định trên từng khoảng rời nhau $(-\\infty, 0)$ và $(0, \\infty)$ do điều kiện ${var} \\ne 0$)."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"{dep_var}/{var} = C",
                        expression_after=f"{dep_var}({var}) = C*{var}",
                        latex_before=f"\\frac{{{dep_var}}}{{{var}}} = C",
                        latex_after=gen_latex,
                    ),
                    equation_latex=gen_latex,
                )
            )
            step_num += 1

            if parsed.initial_condition is not None:
                x0, y0 = parsed.initial_condition
                c_val = sp.simplify(y0 / x0)
                part_sol = sp.simplify(c_val * var)
                part_latex = f"{dep_var}({var}) = {expr_to_latex(part_sol)}"
                steps.append(
                    SolutionStep(
                        step_number=step_num,
                        rule_name="Áp dụng điều kiện ban đầu",
                        title=f"Xác định hằng số C từ điều kiện ban đầu {dep_var}({x0}) = {y0}",
                        description=(
                            f"Thay điều kiện ban đầu ${dep_var}({expr_to_latex(x0)}) = {expr_to_latex(y0)}$: "
                            f"$C \\cdot {expr_to_latex(x0)} = {expr_to_latex(y0)} \\implies C = \\frac{{{expr_to_latex(y0)}}}{{{expr_to_latex(x0)}}} = {expr_to_latex(c_val)}$. "
                            f"Nghiệm riêng Cauchy là: ${part_latex}$."
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"{dep_var}({x0}) = {y0}",
                            expression_after=f"{dep_var}({var}) = {part_sol}",
                            latex_before=f"{dep_var}({expr_to_latex(x0)}) = {expr_to_latex(y0)}",
                            latex_after=part_latex,
                        ),
                        equation_latex=part_latex,
                    )
                )
                step_num += 1

                x0_val = float(sp.N(x0))
                dom_int = (0, sp.oo) if x0_val > 0 else (-sp.oo, 0)
                verif_res = self.verifier.verify_explicit(
                    part_sol,
                    var,
                    rhs_f=rhs_f_xy,
                    dep_var=dep_var,
                    initial_condition=parsed.initial_condition,
                    domain_interval=dom_int,
                    domain_restrictions=tuple(domain_restrictions),
                )
                branch_sol = BranchSolution(
                    expression=part_sol,
                    solution_str=f"{dep_var}({var}) = {part_sol}",
                    solution_latex=part_latex,
                    branch_identity="Nghiệm riêng Cauchy đồng nhất",
                    integration_constant=c_sym,
                    integration_constant_val=c_val,
                    domain_interval=dom_int,
                    domain_restrictions=tuple(dict.fromkeys(domain_restrictions)),
                    verification=verif_res,
                )
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.SUCCESS if verif_res.status == VerificationStatus.VERIFIED else SolutionStatus.DISCREPANCY_DETECTED,
                    verification=verif_res,
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result=f"{dep_var}({var}) = {part_sol}",
                    final_latex=part_latex,
                    steps=tuple(steps),
                    domain_restrictions=tuple(dict.fromkeys(domain_restrictions)),
                    warnings=tuple(user_warnings),
                    execution_time_ms=elapsed,
                    branch_solutions=(branch_sol,),
                )

            # General solution without IC
            verif_res = self.verifier.verify_explicit(
                gen_sol,
                var,
                rhs_f=rhs_f_xy,
                dep_var=dep_var,
                integration_constant=c_sym,
                domain_interval=(0, sp.oo),
                domain_restrictions=tuple(domain_restrictions),
            )
            branch_sol = BranchSolution(
                expression=gen_sol,
                solution_str=f"{dep_var}({var}) = {gen_sol}",
                solution_latex=gen_latex,
                branch_identity="Nghiệm tổng quát đồng nhất",
                integration_constant=c_sym,
                domain_interval=(0, sp.oo),
                domain_restrictions=tuple(dict.fromkeys(domain_restrictions)),
                verification=verif_res,
            )
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.SUCCESS if verif_res.status == VerificationStatus.VERIFIED else SolutionStatus.DISCREPANCY_DETECTED,
                verification=verif_res,
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result=f"{dep_var}({var}) = {gen_sol}",
                final_latex=gen_latex,
                steps=tuple(steps),
                domain_restrictions=tuple(dict.fromkeys(domain_restrictions)),
                warnings=tuple(user_warnings),
                execution_time_ms=elapsed,
                branch_solutions=(branch_sol,),
            )

        # -------------------------------------------------------------
        # Non-degenerate case: G(v) = F(v) - v is not identically zero
        # -------------------------------------------------------------
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Biến đổi về phương trình tách biến",
                title="Thu gọn phương trình vi phân cho hàm phụ v",
                description=(
                    f"Thay vào phương trình ta được: $v + {var}\\frac{{dv}}{{{dvar_name(var)}}} = F(v) "
                    f"\\iff {var}\\frac{{dv}}{{{dvar_name(var)}}} = F(v) - v = {g_v_latex}$."
                ),
                content=ExpressionStepContent(
                    expression_before=f"v + {var}*v' = {F_v}",
                    expression_after=f"{var}*v' = {G_v}",
                    latex_before=f"v + {var}\\frac{{dv}}{{{dvar_name(var)}}} = {f_v_latex}",
                    latex_after=f"{var}\\frac{{dv}}{{{dvar_name(var)}}} = {g_v_latex}",
                ),
                equation_latex=f"{var}\\frac{{dv}}{{{dvar_name(var)}}} = {g_v_latex}",
            )
        )
        step_num += 1

        # Step 4: Equilibrium solutions (Straight-line rays: F(v) - v = 0)
        eq_roots: list[sp.Expr] = []
        is_periodic_trig_eq = False
        is_periodic_complete_verified = True
        periodic_family_str = ""
        periodic_family_latex = ""
        is_per, is_per_verified, fam_str, fam_latex, reps, per_assump = _detect_periodic_trig_family(G_v, v_sym)
        if is_per:
            is_periodic_trig_eq = True
            is_periodic_complete_verified = is_per_verified
            periodic_family_str = fam_str
            periodic_family_latex = fam_latex
            if per_assump:
                domain_restrictions.extend(per_assump)
            eq_roots = reps
            eq_lines_str = f"Họ nghiệm tia cân bằng tuần hoàn: {dep_var} = ({periodic_family_str}) * {var} (đại diện: " + ", ".join(f"{dep_var} = {r}*{var}" for r in eq_roots) + ")"
            eq_lines_latex = f"{dep_var}({var}) = v_{{eq}} {var}, \\; {periodic_family_latex} \\; (\\text{{đại diện: }} " + ", ".join(f"{dep_var} = {expr_to_latex(r)}\\,{var}" for r in eq_roots) + ")"
            step4_desc = (
                f"Xét phương trình $F(v) - v = 0 \\iff {g_v_latex} = 0$. "
                f"Phương trình có họ nghiệm cân bằng tuần hoàn: ${periodic_family_latex}$, "
                f"tương ứng với họ vô số đường thẳng qua gốc tọa độ: ${eq_lines_latex}$."
            )
        else:
            try:
                raw_roots = sp.solve(G_v, v_sym)
                eq_roots = [r for r in raw_roots if r.is_real]
            except Exception:
                pass
            eq_lines_str = ", ".join(f"{dep_var}({var}) = {r}*{var}" for r in eq_roots) if eq_roots else "Không có nghiệm tia cân bằng"
            eq_lines_latex = (
                f"{dep_var}({var}) = v_0 {var}, \\; v_0 \\in \\{{{', '.join(expr_to_latex(r) for r in eq_roots)}\\}}"
                if eq_roots
                else "\\text{Không có nghiệm tia cân bằng}"
            )
            step4_desc = (
                f"Xét phương trình $F(v) - v = 0 \\iff {g_v_latex} = 0$. "
                + (
                    f"Phương trình có các nghiệm: $v_0 \\in \\{{{', '.join(expr_to_latex(r) for r in eq_roots)}\\}}$ tương ứng với các nghiệm tia thẳng: ${', '.join(f'{dep_var} = {expr_to_latex(r)}\\,{var}' for r in eq_roots)}$."
                    if eq_roots
                    else "Phương trình không có nghiệm thực cân bằng; không tồn tại nghiệm tia thẳng."
                )
            )

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Nghiệm đường thẳng cân bằng",
                title="Khảo sát các nghiệm đường thẳng cân bằng qua gốc tọa độ",
                description=step4_desc,
                content=ExpressionStepContent(
                    expression_before=f"{G_v} = 0",
                    expression_after=eq_lines_str,
                    latex_before=f"{g_v_latex} = 0",
                    latex_after=eq_lines_latex,
                ),
            )
        )
        step_num += 1

        # Check if initial condition hits an equilibrium straight line directly
        if parsed.initial_condition is not None:
            x0, y0 = parsed.initial_condition
            v_init = sp.simplify(y0 / x0)
            hit_eq_root: sp.Expr | None = None
            for r in eq_roots:
                if _prove_symbolic_zero(v_init - r):
                    hit_eq_root = r
                    break

            if hit_eq_root is not None:
                part_sol = sp.simplify(hit_eq_root * var)
                part_sol_latex = f"{dep_var}({var}) = {expr_to_latex(part_sol)}"
                steps.append(
                    SolutionStep(
                        step_number=step_num,
                        rule_name="Áp dụng điều kiện ban đầu",
                        title="Điểm ban đầu thuộc nghiệm tia thẳng cân bằng",
                        description=(
                            f"Điều kiện ban đầu $({expr_to_latex(x0)}, {expr_to_latex(y0)})$ có tỉ số $\\frac{{{expr_to_latex(y0)}}}{{{expr_to_latex(x0)}}} = {expr_to_latex(v_init)}$ "
                            f"trùng với nghiệm cân bằng $v = {expr_to_latex(hit_eq_root)}$. "
                            f"Do đó nghiệm riêng của bài toán là đường thẳng qua gốc tọa độ: ${part_sol_latex}$."
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"{dep_var}({x0}) = {y0}",
                            expression_after=f"{dep_var}({var}) = {part_sol}",
                            latex_before=f"{dep_var}({expr_to_latex(x0)}) = {expr_to_latex(y0)}",
                            latex_after=part_sol_latex,
                        ),
                        equation_latex=part_sol_latex,
                    )
                )

                x0_val = float(sp.N(x0))
                dom_int = (0, sp.oo) if x0_val > 0 else (-sp.oo, 0)
                verif_res = self.verifier.verify_explicit(
                    part_sol,
                    var,
                    rhs_f=rhs_f_xy,
                    dep_var=dep_var,
                    initial_condition=parsed.initial_condition,
                    domain_interval=dom_int,
                    domain_restrictions=tuple(domain_restrictions),
                )

                branch_sol = BranchSolution(
                    expression=part_sol,
                    solution_str=f"{dep_var}({var}) = {part_sol}",
                    solution_latex=part_sol_latex,
                    branch_identity="Nghiệm tia thẳng cân bằng",
                    domain_interval=dom_int,
                    domain_restrictions=tuple(dict.fromkeys(domain_restrictions)),
                    verification=verif_res,
                )

                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.SUCCESS if verif_res.status == VerificationStatus.VERIFIED else SolutionStatus.DISCREPANCY_DETECTED,
                    verification=verif_res,
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result=f"{dep_var}({var}) = {part_sol}",
                    final_latex=part_sol_latex,
                    steps=tuple(steps),
                    domain_restrictions=tuple(dict.fromkeys(domain_restrictions)),
                    warnings=tuple(user_warnings),
                    execution_time_ms=elapsed,
                    branch_solutions=(branch_sol,),
                )

        # Step 5: Separation of variables & Integration: \int dv / (F(v) - v) = \int dx / x = ln|x| + C
        int_v = sp.integrate(1 / G_v, v_sym)
        # Ensure log in int_v has Abs
        int_v_abs = int_v.replace(sp.log, lambda a: sp.log(sp.Abs(a)))
        int_x_abs = sp.log(sp.Abs(var))

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Tách biến và lấy tích phân",
                title="Tích phân hai vế theo v và biến độc lập",
                description=(
                    f"Tách biến: $\\frac{{dv}}{{{g_v_latex}}} = \\frac{{d{var_name(var)}}}{{{var}}}$. "
                    f"Lấy nguyên hàm hai vế: $\\int \\frac{{dv}}{{{g_v_latex}}} = \\int \\frac{{d{var_name(var)}}}{{{var}}} = \\ln|{var}| + C$."
                ),
                content=ExpressionStepContent(
                    expression_before=f"1/({G_v}) dv = 1/{var} d{var}",
                    expression_after=f"{int_v_abs} = {int_x_abs} + C",
                    latex_before=f"\\int \\frac{{dv}}{{{g_v_latex}}} = \\int \\frac{{d{var_name(var)}}}{{{var}}}",
                    latex_after=f"{expr_to_latex(int_v_abs)} = \\ln|{var}| + C",
                ),
                equation_latex=f"{expr_to_latex(int_v_abs)} = \\ln|{var}| + C",
            )
        )
        step_num += 1

        # Step 6: Conservative inversion for v without unrestricted sp.solve()
        branch_cands = _invert_homogeneous_relation_candidates(int_v_abs, v_sym, var, c_sym)

        if branch_cands:
            explicit_general_ys = [sp.simplify(c.v_expr * var) for c in branch_cands]
            if len(explicit_general_ys) == 1:
                gen_latex = f"{dep_var}({var}) = {expr_to_latex(explicit_general_ys[0])}"
                gen_res_str = f"{dep_var}({var}) = {explicit_general_ys[0]}"
            else:
                gen_latex = r" \quad\text{hoặc}\quad ".join(f"{dep_var}({var}) = {expr_to_latex(s)}" for s in explicit_general_ys)
                gen_res_str = "  hoặc  ".join(f"{dep_var}({var}) = {s}" for s in explicit_general_ys)

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Thế ngược và rút gọn nghiệm tổng quát",
                    title="Giải nghiệm tường minh y(x)",
                    description=f"Thay $v = \\frac{{{dep_var}}}{{{var}}}$ và rút gọn nghiệm tường minh ${gen_latex}$.",
                    content=ExpressionStepContent(
                        expression_before=f"{int_v_abs.subs(v_sym, dep_var / var)} = {int_x_abs} + C",
                        expression_after=gen_res_str,
                        latex_before=f"{expr_to_latex(int_v_abs.subs(v_sym, dep_var / var))} = \\ln|{var}| + C",
                        latex_after=gen_latex,
                    ),
                    equation_latex=gen_latex,
                )
            )
            step_num += 1

            # Step 7: Apply Cauchy initial condition (if provided)
            if parsed.initial_condition is not None:
                x0, y0 = parsed.initial_condition
                c_val = sp.simplify(int_v_abs.subs(v_sym, y0 / x0) - int_x_abs.subs(var, x0))

                # Identify which explicit branch matches (x0, y0)
                matching_part_data: list[tuple[HomogeneousBranchCandidate, sp.Expr, tuple[sp.Expr | float, sp.Expr | float], tuple[str, ...]]] = []
                for cand in branch_cands:
                    cand_y = sp.simplify(cand.v_expr * var)
                    sub_cand = sp.simplify(cand_y.subs(c_sym, c_val))
                    val_x0 = sp.simplify(sub_cand.subs(var, x0))
                    if val_x0.is_real is not False and not val_x0.has(sp.I) and _prove_symbolic_zero(val_x0 - y0):
                        c_dom_int, c_restrs = _resolve_homogeneous_branch_domain(
                            cand, var, c_val=c_val, x0=x0, parsed=parsed
                        )
                        low, high = c_dom_int
                        is_inside = True
                        try:
                            x0_n = float(sp.N(x0))
                            if low is not None and low != -sp.oo:
                                if x0_n <= float(sp.N(low)):
                                    is_inside = False
                            if high is not None and high != sp.oo:
                                if x0_n >= float(sp.N(high)):
                                    is_inside = False
                        except Exception:
                            pass
                        if is_inside:
                            matching_part_data.append((cand, sub_cand, c_dom_int, c_restrs))

                if not matching_part_data:
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    return SolutionResponse(
                        status=SolutionStatus.CANNOT_SOLVE,
                        verification=VerificationResult(
                            status=VerificationStatus.NOT_APPLICABLE,
                            method="ivp_branch_mismatch",
                            details=f"Không có nhánh nghiệm thực nào thỏa mãn điều kiện ban đầu {dep_var}({x0}) = {y0}.",
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        steps=tuple(steps),
                        domain_restrictions=tuple(dict.fromkeys(domain_restrictions)),
                        warnings=tuple(user_warnings) + ("Không tìm thấy nhánh nghiệm thực nào thỏa mãn điều kiện ban đầu.",),
                        execution_time_ms=elapsed,
                        branch_solutions=(),
                    )

                matching_part_sols = [p[1] for p in matching_part_data]
                particular_y = matching_part_sols[0]
                part_latex = (
                    f"{dep_var}({var}) = {expr_to_latex(particular_y)}"
                    if len(matching_part_sols) == 1
                    else r" \quad\text{hoặc}\quad ".join(f"{dep_var}({var}) = {expr_to_latex(s)}" for s in matching_part_sols)
                )
                part_res_str = (
                    f"{dep_var}({var}) = {particular_y}"
                    if len(matching_part_sols) == 1
                    else "  hoặc  ".join(f"{dep_var}({var}) = {s}" for s in matching_part_sols)
                )

                steps.append(
                    SolutionStep(
                        step_number=step_num,
                        rule_name="Xác định hằng số tích phân Cauchy",
                        title=f"Áp dụng điều kiện ban đầu {dep_var}({x0}) = {y0}",
                        description=(
                            f"Thay ${var} = {expr_to_latex(x0)}$ và ${dep_var} = {expr_to_latex(y0)}$ vào hệ thức tích phân để tìm hằng số $C$: "
                            f"$C = {expr_to_latex(c_val)}$. "
                            f"Ta được nghiệm riêng Cauchy: ${part_latex}$."
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"{dep_var}({x0}) = {y0}",
                            expression_after=part_res_str,
                            latex_before=f"{dep_var}({expr_to_latex(x0)}) = {expr_to_latex(y0)}",
                            latex_after=part_latex,
                        ),
                        equation_latex=part_latex,
                    )
                )

                branch_sols: list[BranchSolution] = []
                for cand, p_sol, b_dom_int, b_extra_restrs in matching_part_data:
                    b_restrs = list(domain_restrictions) + list(cand.real_root_restrictions) + list(cand.denominator_exclusions) + list(b_extra_restrs)
                    v_res = self.verifier.verify_explicit(
                        p_sol,
                        var,
                        rhs_f=rhs_f_xy,
                        dep_var=dep_var,
                        initial_condition=parsed.initial_condition,
                        domain_interval=b_dom_int,
                        domain_restrictions=tuple(dict.fromkeys(b_restrs)),
                    )
                    branch_sols.append(
                        BranchSolution(
                            expression=p_sol,
                            solution_str=f"{dep_var}({var}) = {p_sol}",
                            solution_latex=f"{dep_var}({var}) = {expr_to_latex(p_sol)}",
                            branch_identity=cand.branch_identity,
                            integration_constant=c_sym,
                            integration_constant_val=c_val,
                            real_root_restrictions=cand.real_root_restrictions,
                            denominator_exclusions=cand.denominator_exclusions,
                            domain_interval=b_dom_int,
                            domain_restrictions=tuple(dict.fromkeys(b_restrs)),
                            verification=v_res,
                        )
                    )

                verif_results = [b.verification for b in branch_sols if b.verification is not None]
                if any(v.status == VerificationStatus.FAILED for v in verif_results):
                    verif_res = next(v for v in verif_results if v.status == VerificationStatus.FAILED)
                    sol_status = SolutionStatus.DISCREPANCY_DETECTED
                elif any(v.status == VerificationStatus.UNVERIFIED for v in verif_results):
                    verif_res = next(v for v in verif_results if v.status == VerificationStatus.UNVERIFIED)
                    sol_status = SolutionStatus.UNVERIFIED
                else:
                    verif_res = verif_results[0]
                    sol_status = SolutionStatus.SUCCESS

                elapsed = (time.perf_counter() - t0_start) * 1000.0
                all_dom_restrs = list(domain_restrictions)
                for b in branch_sols:
                    all_dom_restrs.extend(b.domain_restrictions)
                return SolutionResponse(
                    status=sol_status,
                    verification=verif_res,
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result=part_res_str,
                    final_latex=part_latex,
                    steps=tuple(steps),
                    domain_restrictions=tuple(dict.fromkeys(all_dom_restrs)),
                    warnings=tuple(user_warnings),
                    execution_time_ms=elapsed,
                    branch_solutions=tuple(branch_sols),
                )

            # General solution without IC: Verify EVERY branch independently
            branch_sols = []
            for cand in branch_cands:
                cand_y = sp.simplify(cand.v_expr * var)
                gen_dom_int, gen_extra_restrs = _resolve_homogeneous_branch_domain(
                    cand, var, c_val=None, x0=None, parsed=parsed
                )
                b_restrs = list(domain_restrictions) + list(cand.real_root_restrictions) + list(cand.denominator_exclusions) + list(gen_extra_restrs)
                v_res = self.verifier.verify_explicit(
                    cand_y,
                    var,
                    rhs_f=rhs_f_xy,
                    dep_var=dep_var,
                    integration_constant=c_sym,
                    domain_interval=gen_dom_int,
                    domain_restrictions=tuple(dict.fromkeys(b_restrs)),
                )
                branch_sols.append(
                    BranchSolution(
                        expression=cand_y,
                        solution_str=f"{dep_var}({var}) = {cand_y}",
                        solution_latex=f"{dep_var}({var}) = {expr_to_latex(cand_y)}",
                        branch_identity=cand.branch_identity,
                        integration_constant=c_sym,
                        integration_constant_val=None,
                        real_root_restrictions=cand.real_root_restrictions,
                        denominator_exclusions=cand.denominator_exclusions,
                        domain_interval=gen_dom_int,
                        domain_restrictions=tuple(dict.fromkeys(b_restrs)),
                        verification=v_res,
                    )
                )

            branch_verif_results = [b.verification for b in branch_sols if b.verification is not None]
            if any(v.status == VerificationStatus.FAILED for v in branch_verif_results):
                final_verif = next(v for v in branch_verif_results if v.status == VerificationStatus.FAILED)
                sol_status = SolutionStatus.DISCREPANCY_DETECTED
            elif any(v.status == VerificationStatus.UNVERIFIED for v in branch_verif_results):
                final_verif = VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    method="branch_inconclusive",
                    details="Một số nhánh nghiệm thực của phương trình thuần nhất không thể kiểm chứng hoàn toàn bằng phương pháp ký hiệu.",
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
                    method="classical_homogeneous_all_branches_verified",
                    details="Kiểm chứng thành công: Tất cả các nhánh nghiệm tường minh đều thỏa mãn phương trình vi phân thuần nhất bậc 0.",
                )
                sol_status = SolutionStatus.SUCCESS

            elapsed = (time.perf_counter() - t0_start) * 1000.0
            all_dom_restrs = list(domain_restrictions)
            for b in branch_sols:
                all_dom_restrs.extend(b.domain_restrictions)
            return SolutionResponse(
                status=sol_status,
                verification=final_verif,
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result=gen_res_str,
                final_latex=gen_latex,
                steps=tuple(steps),
                domain_restrictions=tuple(dict.fromkeys(all_dom_restrs)),
                warnings=tuple(user_warnings),
                execution_time_ms=elapsed,
                branch_solutions=tuple(branch_sols),
            )

        # Implicit solution when explicit inversion for v is transcendental
        implicit_phi = sp.simplify(int_v_abs.subs(v_sym, dep_var / var) - int_x_abs)
        imp_str = f"{int_v_abs.subs(v_sym, dep_var / var)} = {int_x_abs} + C"
        imp_latex = f"{expr_to_latex(int_v_abs.subs(v_sym, dep_var / var))} = \\ln|{var}| + C"

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Nghiệm ẩn phương trình thuần nhất",
                title="Hệ thức nghiệm ẩn sau khi thế ngược v = y/x",
                description="Do phương trình sau khi tích phân là siêu việt đối với $v$, nghiệm được bảo toàn ở dạng phương trình ẩn chính xác để đảm bảo độ tin cậy toán học.",
                content=ExpressionStepContent(
                    expression_before=f"{int_v_abs} = {int_x_abs} + C",
                    expression_after=imp_str,
                    latex_before=f"{expr_to_latex(int_v_abs)} = \\ln|{var}| + C",
                    latex_after=imp_latex,
                ),
                equation_latex=imp_latex,
            )
        )
        step_num += 1

        # Check IC for implicit solution
        c_ic_val: sp.Expr | None = None
        if parsed.initial_condition is not None:
            x0, y0 = parsed.initial_condition
            c_ic_val = sp.simplify(int_v_abs.subs(v_sym, y0 / x0) - int_x_abs.subs(var, x0))
            imp_part_str = f"{int_v_abs.subs(v_sym, dep_var / var)} = {int_x_abs} + {c_ic_val}"
            imp_part_latex = f"{expr_to_latex(int_v_abs.subs(v_sym, dep_var / var))} = \\ln|{var}| + {expr_to_latex(c_ic_val)}"

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Áp dụng điều kiện ban đầu",
                    title=f"Xác định hằng số C từ điều kiện ban đầu {dep_var}({x0}) = {y0}",
                    description=(
                        f"Thay ${var} = {expr_to_latex(x0)}$ và ${dep_var} = {expr_to_latex(y0)}$ vào hệ thức ẩn để tìm hằng số $C$: "
                        f"$C = {expr_to_latex(c_ic_val)}$. "
                        f"Ta được nghiệm ẩn Cauchy: ${imp_part_latex}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"{dep_var}({x0}) = {y0}",
                        expression_after=imp_part_str,
                        latex_before=f"{dep_var}({expr_to_latex(x0)}) = {expr_to_latex(y0)}",
                        latex_after=imp_part_latex,
                    ),
                    equation_latex=imp_part_latex,
                )
            )

            x0_val = float(sp.N(x0))
            dom_int = (0, sp.oo) if x0_val > 0 else (-sp.oo, 0)
            verif_res = self.verifier.verify_classical_homogeneous_implicit(
                potential_phi=implicit_phi,
                x_sym=var,
                y_sym=dep_var,
                F_v_expr=F_v,
                initial_condition=parsed.initial_condition,
                c_val=c_ic_val,
                domain_interval=dom_int,
                domain_restrictions=tuple(domain_restrictions),
            )

            branch_sol = BranchSolution(
                expression=None,
                solution_str=imp_part_str,
                solution_latex=imp_part_latex,
                branch_identity="Nghiệm ẩn Cauchy",
                integration_constant=c_sym,
                integration_constant_val=c_ic_val,
                domain_interval=dom_int,
                domain_restrictions=tuple(dict.fromkeys(domain_restrictions)),
                verification=verif_res,
            )

            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.SUCCESS if verif_res.status == VerificationStatus.VERIFIED else SolutionStatus.DISCREPANCY_DETECTED,
                verification=verif_res,
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result=imp_part_str,
                final_latex=imp_part_latex,
                steps=tuple(steps),
                domain_restrictions=tuple(dict.fromkeys(domain_restrictions)),
                warnings=tuple(user_warnings),
                execution_time_ms=elapsed,
                branch_solutions=(branch_sol,),
            )

        verif_res = self.verifier.verify_classical_homogeneous_implicit(
            potential_phi=implicit_phi,
            x_sym=var,
            y_sym=dep_var,
            F_v_expr=F_v,
            domain_interval=(0, sp.oo),
            domain_restrictions=tuple(domain_restrictions),
        )
        if verif_res.status == VerificationStatus.VERIFIED and is_periodic_trig_eq and not is_periodic_complete_verified:
            verif_res = VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="incomplete_periodic_equilibrium_coverage",
                details="Không thể khẳng định tính đầy đủ của họ nghiệm cân bằng tuần hoàn do tham số chưa xác định thực khác 0.",
            )

        branch_sol = BranchSolution(
            expression=None,
            solution_str=imp_str,
            solution_latex=imp_latex,
            branch_identity="Hệ thức nghiệm ẩn",
            integration_constant=c_sym,
            domain_interval=(0, sp.oo),
            domain_restrictions=tuple(dict.fromkeys(domain_restrictions)),
            verification=verif_res,
        )

        elapsed = (time.perf_counter() - t0_start) * 1000.0
        return SolutionResponse(
            status=SolutionStatus.SUCCESS if verif_res.status == VerificationStatus.VERIFIED else SolutionStatus.UNVERIFIED if verif_res.status == VerificationStatus.UNVERIFIED else SolutionStatus.DISCREPANCY_DETECTED,
            verification=verif_res,
            raw_input=request.raw_input,
            canonical_input=parsed.canonical_eq,
            final_result=imp_str,
            final_latex=imp_latex,
            steps=tuple(steps),
            domain_restrictions=tuple(dict.fromkeys(domain_restrictions)),
            warnings=tuple(user_warnings),
            execution_time_ms=elapsed,
            branch_solutions=(branch_sol,),
        )


def var_name(sym: sp.Symbol) -> str:
    return sym.name


def dvar_name(sym: sp.Symbol) -> str:
    return f"d{sym.name}"

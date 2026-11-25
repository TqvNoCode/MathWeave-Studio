"""Method of Undetermined Coefficients Engine for Second-Order Nonhomogeneous Linear ODEs.

Solves:
    a*y'' + b*y' + c*y = g(t),  a != 0, g(t) != 0,
where g(t) belongs to polynomial, exponential, trigonometric, or mixed product families,
with exact resonance multiplier t^s (s in {0, 1, 2}) and superposition decomposition.
"""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp

from math_app.application.dtos import SolutionStep
from math_app.domain.step_content import ExpressionStepContent
from math_app.rendering.latex.formatter import expr_to_latex


@dataclass(frozen=True)
class ForcingComponent:
    """A classified forcing term or frequency group: e^(alpha*t) * [P(t)*cos(beta*t) + Q(t)*sin(beta*t)]."""

    alpha: sp.Expr
    beta: sp.Expr
    P_poly: sp.Expr  # Coefficient of cos(beta*t), or pure polynomial if beta=0
    Q_poly: sp.Expr  # Coefficient of sin(beta*t), 0 if beta=0
    degree: int
    raw_expr: sp.Expr


class UndeterminedCoefficientsError(Exception):
    """Base exception for Method of Undetermined Coefficients failures."""


class InconclusiveResonanceError(UndeterminedCoefficientsError):
    """Raised when resonance multiplicity cannot be determined conclusively due to symbolic parameters."""


@dataclass(frozen=True)
class SolvedGroup:
    """Result of solving a single frequency group via undetermined coefficients."""

    component: ForcingComponent
    resonance_s: int
    ansatz_expr: sp.Expr
    unknown_symbols: tuple[sp.Symbol, ...]
    system_equations: tuple[sp.Expr, ...]
    solved_coefficients: dict[sp.Symbol, sp.Expr]
    particular_solution: sp.Expr
    steps: tuple[SolutionStep, ...]


@dataclass(frozen=True)
class UndeterminedCoefficientsResult:
    """Complete result returned by the Undetermined Coefficients engine."""

    is_supported: bool
    particular_solution: sp.Expr | None = None
    solved_groups: tuple[SolvedGroup, ...] = ()
    steps: tuple[SolutionStep, ...] = ()
    unsupported_reason: str | None = None


def classify_single_term(term: sp.Expr, var: sp.Symbol) -> tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr] | None:
    """Classify a single multiplicative term into (alpha, beta, P_poly, Q_poly) or return None if unsupported.

    Matches:
    - Pure constants / polynomials in var
    - exp(alpha * var) or P(var) * exp(alpha * var)
    - cos(beta * var), sin(beta * var), or P(var) * cos/sin
    - Products: P(var) * exp(alpha * var) * cos/sin(beta * var)

    Rejects:
    - log, tan, sec, csc, cot, 1/var, sqrt(var), exp(var^2), sin(var^2), etc.
    """
    if not term.has(var):
        # Pure constant
        return (sp.Integer(0), sp.Integer(0), term, sp.Integer(0))

    if term.is_polynomial(var):
        # Pure polynomial in var
        return (sp.Integer(0), sp.Integer(0), term, sp.Integer(0))

    coeff, rest = term.as_coeff_Mul()
    factors = sp.Mul.make_args(rest)

    alpha = sp.Integer(0)
    beta = sp.Integer(0)
    is_sin = False
    is_cos = False
    poly_factors: list[sp.Expr] = []

    for f in factors:
        if not f.has(var):
            coeff *= f
            continue

        if isinstance(f, sp.exp):
            arg = f.args[0]
            if arg.has(var):
                if alpha != 0:
                    # Multiple distinct exponential factors not combined
                    return None
                d = sp.diff(arg, var)
                if d.has(var):
                    # Non-linear exponential argument, e.g. exp(t^2)
                    return None
                alpha_val = sp.simplify(d)
                # Ensure arg is purely alpha_val * var (+ optional constant)
                rem = sp.simplify(arg - alpha_val * var)
                if rem.has(var):
                    return None
                if rem != 0:
                    coeff *= sp.exp(rem)
                alpha = alpha_val

        elif isinstance(f, sp.sin):
            arg = f.args[0]
            if beta != 0 or is_sin or is_cos:
                # Product of trigonometric functions without prior linearization
                return None
            d = sp.diff(arg, var)
            if d.has(var):
                # Non-linear argument, e.g. sin(t^2)
                return None
            b_val = sp.simplify(d)
            rem = sp.simplify(arg - b_val * var)
            if rem != 0:
                # Non-zero phase shift not pre-expanded, e.g. sin(t + 1)
                return None
            if b_val < 0:
                b_val = -b_val
                coeff = -coeff
            beta = b_val
            is_sin = True

        elif isinstance(f, sp.cos):
            arg = f.args[0]
            if beta != 0 or is_sin or is_cos:
                return None
            d = sp.diff(arg, var)
            if d.has(var):
                return None
            b_val = sp.simplify(d)
            rem = sp.simplify(arg - b_val * var)
            if rem != 0:
                return None
            if b_val < 0:
                b_val = -b_val
            beta = b_val
            is_cos = True

        elif f.is_polynomial(var):
            poly_factors.append(f)

        else:
            # Any other transcendental or unsupported function, e.g. log, tan
            return None

    poly_term = sp.simplify(coeff * sp.Mul(*poly_factors))

    if is_sin:
        return (alpha, beta, sp.Integer(0), poly_term)
    elif is_cos:
        return (alpha, beta, poly_term, sp.Integer(0))
    else:
        return (alpha, beta, poly_term, sp.Integer(0))


def decompose_and_group_forcing(g_expr: sp.Expr, var: sp.Symbol) -> list[ForcingComponent] | None:
    """Decompose forcing function g(t) into frequency groups (alpha, beta).

    Terms sharing the same (alpha, beta) frequency are combined to prevent
    redundant or dependent undetermined-coefficients systems.

    Returns a list of ForcingComponent objects, or None if g(t) contains unsupported terms.
    """
    expanded = sp.expand(g_expr)
    terms = sp.Add.make_args(expanded)

    # Dictionary mapping (alpha, beta) -> list of (P_part, Q_part)
    groups_dict: dict[tuple[sp.Expr, sp.Expr], list[tuple[sp.Expr, sp.Expr]]] = {}

    for term in terms:
        res = classify_single_term(term, var)
        if res is None:
            return None
        alpha_val, beta_val, p_part, q_part = res
        # Canonicalize key using simplified expressions
        key = (sp.simplify(alpha_val), sp.simplify(beta_val))
        if key not in groups_dict:
            groups_dict[key] = []
        groups_dict[key].append((p_part, q_part))

    components: list[ForcingComponent] = []

    for (alpha_val, beta_val), parts in groups_dict.items():
        total_p = sp.simplify(sum(p for p, _ in parts))
        total_q = sp.simplify(sum(q for _, q in parts))

        # Determine maximum polynomial degree
        deg_p = sp.degree(total_p, var) if total_p.has(var) else 0
        deg_q = sp.degree(total_q, var) if total_q.has(var) else 0
        degree_val = max(int(deg_p or 0), int(deg_q or 0))

        if beta_val == 0:
            raw_k = total_p if alpha_val == 0 else sp.simplify(sp.exp(alpha_val * var) * total_p)
        else:
            trig_sum = total_p * sp.cos(beta_val * var) + total_q * sp.sin(beta_val * var)
            raw_k = trig_sum if alpha_val == 0 else sp.simplify(sp.exp(alpha_val * var) * trig_sum)

        components.append(
            ForcingComponent(
                alpha=alpha_val,
                beta=beta_val,
                P_poly=total_p,
                Q_poly=total_q,
                degree=degree_val,
                raw_expr=raw_k,
            )
        )

    return components


def evaluate_zero_state(expr: sp.Expr) -> bool | None:
    """Evaluate whether an expression is definitely zero (True), definitely nonzero (False),

    or undetermined/inconclusive (None).
    """
    s_expr = sp.simplify(expr)
    if s_expr == 0 or s_expr.is_zero is True:
        return True
    if s_expr.is_zero is False:
        return False

    # Check for free symbols whose values could alter the zero-status
    if s_expr.free_symbols:
        return None

    # Number with no free symbols
    if s_expr.is_number:
        try:
            val = complex(s_expr.evalf())
            if abs(val) > 1e-12:
                return False
            refined = sp.nsimplify(sp.trigsimp(sp.expand(s_expr)))
            if refined == 0 or refined.is_zero is True:
                return True
            if refined.is_zero is False:
                return False
        except (TypeError, ValueError):
            pass

    return None


def get_resonance_multiplicity(
    a: sp.Expr,
    b: sp.Expr,
    c: sp.Expr,
    alpha: sp.Expr,
    beta: sp.Expr,
) -> int | None:
    """Determine the exact resonance multiplier s in {0, 1, 2} for characteristic frequency lambda = alpha + i*beta.

    P(r) = a*r^2 + b*r + c.
    - If P(lambda) is definitely nonzero: s = 0 (no resonance).
    - If P(lambda) == 0 and P'(lambda) is definitely nonzero: s = 1 (simple root resonance).
    - If P(lambda) == 0 and P'(lambda) == 0: s = 2 (double root resonance).
    - If zero-status of P(lambda) or P'(lambda) is undetermined/inconclusive: returns None.
    """
    lam = alpha + sp.I * beta
    r = sp.Symbol("_r")
    p_poly = a * r**2 + b * r + c

    p_val = p_poly.subs(r, lam)
    p_zero = evaluate_zero_state(p_val)

    if p_zero is False:
        return 0
    elif p_zero is None:
        return None

    # P(lambda) == 0. Check derivative P'(lambda):
    p_prime = sp.diff(p_poly, r)
    p_prime_val = p_prime.subs(r, lam)
    p_prime_zero = evaluate_zero_state(p_prime_val)

    if p_prime_zero is False:
        return 1
    elif p_prime_zero is True:
        return 2
    else:
        return None


def solve_component_group(
    a: sp.Expr,
    b: sp.Expr,
    c: sp.Expr,
    comp: ForcingComponent,
    var: sp.Symbol,
    group_idx: int,
    step_num: int,
    total_groups: int,
) -> SolvedGroup:
    """Construct ansatz, solve linear system for undetermined coefficients, and generate pedagogical steps."""
    alpha = comp.alpha
    beta = comp.beta
    deg = comp.degree
    s = get_resonance_multiplicity(a, b, c, alpha, beta)
    if s is None:
        lam_expr = alpha + sp.I * beta
        raise InconclusiveResonanceError(
            f"Hiện tượng cộng hưởng cho tần số đặc trưng lambda = {expr_to_latex(lam_expr)} "
            "không thể xác định dứt khoát do chứa tham số ký hiệu chưa có giả thiết ràng buộc "
            "(Resonance status is inconclusive due to symbolic parameters without assumptions)."
        )

    # 1. Unknown symbols creation
    prefix = f"A_{group_idx}_" if total_groups > 1 else "A_"
    prefix_b = f"B_{group_idx}_" if total_groups > 1 else "B_"

    a_syms = [sp.Symbol(f"{prefix}{j}") for j in range(deg + 1)]
    poly_a = sum(a_syms[j] * var**j for j in range(deg + 1))

    if beta == 0:
        ansatz = var**s * sp.exp(alpha * var) * poly_a
        all_syms = tuple(a_syms)
    else:
        b_syms = [sp.Symbol(f"{prefix_b}{j}") for j in range(deg + 1)]
        poly_b = sum(b_syms[j] * var**j for j in range(deg + 1))
        ansatz = var**s * sp.exp(alpha * var) * (poly_a * sp.cos(beta * var) + poly_b * sp.sin(beta * var))
        all_syms = tuple(a_syms + b_syms)

    # 2. Derivatives and differential operator
    d1 = sp.diff(ansatz, var)
    d2 = sp.diff(d1, var)
    l_ansatz = a * d2 + b * d1 + c * ansatz
    diff = l_ansatz - comp.raw_expr

    # 3. Extract linear equations by matching basis functions
    if alpha != 0:
        e_expr = sp.expand(sp.simplify(diff * sp.exp(-alpha * var)))
    else:
        e_expr = sp.expand(diff)

    equations: list[sp.Expr] = []

    if beta == 0:
        poly_e = sp.Poly(e_expr, var)
        equations.extend(poly_e.all_coeffs())
    else:
        cos_b = sp.cos(beta * var)
        sin_b = sp.sin(beta * var)
        p_t = sp.expand(e_expr).coeff(cos_b, 1)
        q_t = sp.expand(e_expr).coeff(sin_b, 1)
        if p_t != 0:
            equations.extend(sp.Poly(p_t, var).all_coeffs())
        if q_t != 0:
            equations.extend(sp.Poly(q_t, var).all_coeffs())

    # 4. Solve algebraic linear system
    try:
        sol = sp.solve(equations, all_syms, dict=True)
    except Exception as e:
        raise UndeterminedCoefficientsError(
            f"Không thể giải hệ phương trình hệ số bất định do lỗi đại số ký hiệu: {e}"
        ) from e

    if not sol:
        raise UndeterminedCoefficientsError(
            f"Hệ phương trình xác định hệ số bất định vô nghiệm (inconsistent system) cho thành phần: {comp.raw_expr}"
        )

    sol_dict: dict[sp.Symbol, sp.Expr] = sol[0]
    # Set any unassigned free symbols to 0
    subs_map = [(sym, sol_dict.get(sym, sp.Integer(0))) for sym in all_syms]
    particular_sol = sp.simplify(ansatz.subs(subs_map))

    # Guard: verify no unknown trial symbols remain in particular_sol
    if any(sym in particular_sol.free_symbols for sym in all_syms):
        raise UndeterminedCoefficientsError(
            f"Hệ phương trình xác định hệ số bất định không giải dứt điểm được các hệ số: {all_syms}"
        )

    # Verification of group particular solution
    res_check = sp.simplify(a * sp.diff(particular_sol, var, 2) + b * sp.diff(particular_sol, var) + c * particular_sol - comp.raw_expr)
    if res_check != 0:
        res_check = sp.simplify(sp.trigsimp(res_check))
    if res_check != 0:
        raise UndeterminedCoefficientsError(f"Nghiệm riêng Yp không triệt tiêu biểu thức dư: {res_check} != 0")

    # 5. Pedagogical Steps Generation
    steps: list[SolutionStep] = []
    cur_step = step_num

    group_label = f" cho thành phần $g_{group_idx}({var}) = {expr_to_latex(comp.raw_expr)}$" if total_groups > 1 else ""

    # Step A: Resonance explanation & trial solution proposal
    lam_latex = expr_to_latex(alpha + sp.I * beta)
    if s == 0:
        res_reason = (
            f"Tần số đặc trưng $\\lambda = {lam_latex}$ không phải là nghiệm của phương trình đặc trưng ($P(\\lambda) \\ne 0$). "
            f"Do đó, không xảy ra hiện tượng cộng hưởng: số mũ nhân tử $s = 0$ ($t^0 = 1$)."
        )
    elif s == 1:
        res_reason = (
            f"Tần số đặc trưng $\\lambda = {lam_latex}$ trùng với một nghiệm đơn của phương trình đặc trưng ($P(\\lambda) = 0, P'(\\lambda) \\ne 0$). "
            f"Do đó, xảy ra hiện tượng cộng hưởng cấp một: nhân thêm thừa số $t^1$ ($s = 1$) vào nghiệm thử."
        )
    else:
        res_reason = (
            f"Tần số đặc trưng $\\lambda = {lam_latex}$ trùng với nghiệm kép của phương trình đặc trưng ($P(\\lambda) = 0, P'(\\lambda) = 0$). "
            f"Do đó, xảy ra hiện tượng cộng hưởng kép: nhân thêm thừa số $t^2$ ($s = 2$) vào nghiệm thử."
        )

    ansatz_desc = (
        f"Xét thành phần cưỡng bức $g{f'_{group_idx}' if total_groups > 1 else ''}({var}) = {expr_to_latex(comp.raw_expr)}$:\n\n"
        f"1. Xác định tần số đặc trưng: $\\lambda = \\alpha + i\\beta = {lam_latex}$, bậc đa thức $N = {deg}$.\n"
        f"2. Kiểm tra cộng hưởng: {res_reason}\n"
        f"3. Dạng nghiệm riêng đề xuất ($Y_p$):\n"
        f"$${expr_to_latex(sp.Symbol('Y_p'))}({var}) = {expr_to_latex(ansatz)}$$"
    )

    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Dạng nghiệm riêng đề xuất",
            title=f"Đề xuất dạng nghiệm riêng theo phương pháp hệ số bất định{group_label}",
            description=ansatz_desc,
            content=ExpressionStepContent(
                expression_before=f"g({var}) = {comp.raw_expr}",
                expression_after=f"Y_p({var}) = {ansatz}",
                latex_before=f"g({var}) = {expr_to_latex(comp.raw_expr)}",
                latex_after=f"Y_p({var}) = {expr_to_latex(ansatz)}",
            ),
            equation_latex=f"Y_p({var}) = {expr_to_latex(ansatz)}",
        )
    )
    cur_step += 1

    # Step B: Derivatives & Substitution
    subst_desc = (
        f"Tính các đạo hàm cấp một và cấp hai của nghiệm thử $Y_p({var})$:\n"
        f"- Đạo hàm cấp 1: $Y_p'({var}) = {expr_to_latex(d1)}$\n"
        f"- Đạo hàm cấp 2: $Y_p''({var}) = {expr_to_latex(d2)}$\n\n"
        f"Thay vào vế trái toán tử vi phân $L[Y_p] = a Y_p'' + b Y_p' + c Y_p$ và đồng nhất với vế phải:"
    )
    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Đạo hàm và thế toán tử",
            title=f"Tính đạo hàm nghiệm thử và thay vào phương trình vi phân{group_label}",
            description=subst_desc,
            content=ExpressionStepContent(
                expression_before=f"Y_p = {ansatz}",
                expression_after=f"L[Y_p] = {l_ansatz}",
                latex_before=f"Y_p({var}) = {expr_to_latex(ansatz)}",
                latex_after=f"L[Y_p] = {expr_to_latex(l_ansatz)}",
            ),
            equation_latex=f"L[Y_p] = {expr_to_latex(l_ansatz)}",
        )
    )
    cur_step += 1

    # Step C: Coefficient equations & solution
    eq_lines = [f"{expr_to_latex(eq)} = 0" for eq in equations]
    eq_cases_latex = "\\begin{cases} " + " \\\\ ".join(eq_lines) + " \\end{cases}"
    sol_lines = [f"{expr_to_latex(sym)} = {expr_to_latex(sol_dict.get(sym, sp.Integer(0)))}" for sym in all_syms]
    sol_latex = ", \\quad ".join(sol_lines)

    coeff_desc = (
        f"Khai triển, nhóm theo các hàm cơ sở độc lập tuyến tính và đồng nhất hệ số với $g({var})$:\n"
        f"$${eq_cases_latex}$$\n\n"
        f"Giải hệ phương trình đại số tuyến tính tìm được các hệ số:\n"
        f"$${sol_latex}$$"
    )

    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Hệ phương trình hệ số bất định",
            title=f"Thiết lập và giải hệ phương trình tìm hệ số bất định{group_label}",
            description=coeff_desc,
            content=ExpressionStepContent(
                expression_before=", ".join(str(eq) + " = 0" for eq in equations),
                expression_after=sol_latex,
                latex_before=eq_cases_latex,
                latex_after=sol_latex,
            ),
            equation_latex=sol_latex,
        )
    )
    cur_step += 1

    # Step D: Particular solution formulation
    steps.append(
        SolutionStep(
            step_number=cur_step,
            rule_name="Nghiệm riêng thành phần",
            title=f"Xác định nghiệm riêng thành phần Y_p({var}){group_label}",
            description=(
                f"Thay các hệ số vừa tìm được vào dạng nghiệm thử ban đầu thu được nghiệm riêng:\n"
                f"$$Y_p({var}) = {expr_to_latex(particular_sol)}$$"
            ),
            content=ExpressionStepContent(
                expression_before=f"Y_p({var}) = {ansatz}",
                expression_after=f"Y_p({var}) = {particular_sol}",
                latex_before=f"Y_p({var}) = {expr_to_latex(ansatz)}",
                latex_after=f"Y_p({var}) = {expr_to_latex(particular_sol)}",
            ),
            equation_latex=f"Y_p({var}) = {expr_to_latex(particular_sol)}",
        )
    )

    return SolvedGroup(
        component=comp,
        resonance_s=s,
        ansatz_expr=ansatz,
        unknown_symbols=all_syms,
        system_equations=tuple(equations),
        solved_coefficients=sol_dict,
        particular_solution=particular_sol,
        steps=tuple(steps),
    )


def solve_undetermined_coefficients(
    a: sp.Expr,
    b: sp.Expr,
    c: sp.Expr,
    g_expr: sp.Expr,
    var: sp.Symbol,
    start_step_num: int = 5,
) -> UndeterminedCoefficientsResult:
    """Execute the Method of Undetermined Coefficients for a*y'' + b*y' + c*y = g(t).

    Returns an UndeterminedCoefficientsResult containing the particular solution,
    solved groups, and all structured pedagogical derivation steps.
    """
    components = decompose_and_group_forcing(g_expr, var)
    if components is None:
        return UndeterminedCoefficientsResult(
            is_supported=False,
            unsupported_reason=(
                f"Vế phải g({var}) = {expr_to_latex(g_expr)} chứa hàm số không thuộc các họ giải được bằng "
                "phương pháp Hệ số bất định (Method of Undetermined Coefficients). "
                "Phương pháp Biến thiên hằng số (Variation of Parameters / Lagrange) được áp dụng thay thế."
            ),
        )

    all_steps: list[SolutionStep] = []
    solved_groups: list[SolvedGroup] = []
    cur_step = start_step_num

    # Step: Forcing function decomposition & Superposition explanation
    total_groups = len(components)
    if total_groups > 1:
        comp_desc_lines = [
            f"Vế phải $g({var}) = {expr_to_latex(g_expr)}$ gồm {total_groups} thành phần độc lập thuộc các họ hàm cơ bản:\n"
        ]
        for idx, comp in enumerate(components, 1):
            comp_desc_lines.append(f"- Thành phần {idx}: $g_{idx}({var}) = {expr_to_latex(comp.raw_expr)}$")
        comp_desc_lines.append(
            f"\nTheo nguyên lý chồng chất nghiệm (Superposition Principle), nghiệm riêng tổng quát có dạng:\n"
            f"$$Y_p({var}) = " + " + ".join(f"Y_{{p,{i}}}({var})" for i in range(1, total_groups + 1)) + "$$"
        )
        superpos_desc = "\n".join(comp_desc_lines)

        all_steps.append(
            SolutionStep(
                step_number=cur_step,
                rule_name="Nguyên lý chồng chất",
                title="Phân tích vế phải và áp dụng nguyên lý chồng chất nghiệm",
                description=superpos_desc,
                content=ExpressionStepContent(
                    expression_before=f"g({var}) = {g_expr}",
                    expression_after=" + ".join(f"Y_p{i}" for i in range(1, total_groups + 1)),
                    latex_before=f"g({var}) = {expr_to_latex(g_expr)}",
                    latex_after="Y_p(" + str(var) + ") = " + " + ".join(f"Y_{{p,{i}}}({var})" for i in range(1, total_groups + 1)),
                ),
                equation_latex="Y_p(" + str(var) + ") = " + " + ".join(f"Y_{{p,{i}}}({var})" for i in range(1, total_groups + 1)),
            )
        )
        cur_step += 1

    # Solve each frequency group
    try:
        for idx, comp in enumerate(components, 1):
            solved_group = solve_component_group(
                a=a,
                b=b,
                c=c,
                comp=comp,
                var=var,
                group_idx=idx,
                step_num=cur_step,
                total_groups=total_groups,
            )
            solved_groups.append(solved_group)
            all_steps.extend(solved_group.steps)
            cur_step = all_steps[-1].step_number + 1
    except UndeterminedCoefficientsError as err:
        return UndeterminedCoefficientsResult(
            is_supported=False,
            unsupported_reason=str(err),
        )

    # Total particular solution
    total_yp = sp.simplify(sum(sg.particular_solution for sg in solved_groups))

    # Superposition combination step if multiple groups
    if total_groups > 1:
        sum_terms_latex = " + ".join(f"\\left({expr_to_latex(sg.particular_solution)}\\right)" for sg in solved_groups)
        all_steps.append(
            SolutionStep(
                step_number=cur_step,
                rule_name="Tổng hợp nghiệm riêng",
                title="Tổng hợp nghiệm riêng toàn phần theo nguyên lý chồng chất",
                description=(
                    f"Cộng các nghiệm riêng thành phần theo nguyên lý chồng chất:\n"
                    f"$$\\begin{{aligned}} Y_p({var}) &= {sum_terms_latex} \\\\ &= {expr_to_latex(total_yp)} \\end{{aligned}}$$"
                ),
                content=ExpressionStepContent(
                    expression_before=" + ".join(str(sg.particular_solution) for sg in solved_groups),
                    expression_after=f"Y_p({var}) = {total_yp}",
                    latex_before=sum_terms_latex,
                    latex_after=f"Y_p({var}) = {expr_to_latex(total_yp)}",
                ),
                equation_latex=f"Y_p({var}) = {expr_to_latex(total_yp)}",
            )
        )

    return UndeterminedCoefficientsResult(
        is_supported=True,
        particular_solution=total_yp,
        solved_groups=tuple(solved_groups),
        steps=tuple(all_steps),
    )

"""Separable ordinary differential equations solver: y' = f(t)*g(y)."""

from __future__ import annotations

import time
import sympy as sp

from math_app.application.dtos import (
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
from math_app.verification.calculus.ode_verifier import ODEVerifier


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
            rhs_expr = sp.simplify(yp_sols[0])
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
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="separability_check",
                    details="Phương trình không thể phân tách thành tích f(t)*g(y).",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=(
                    f"Biểu thức vế phải {rhs_expr} không có dạng tách biến f({var})*g({dep_var}) "
                    "(Non-separable differential equation).",
                ),
                execution_time_ms=elapsed,
            )

        if f_cand.could_extract_minus_sign():
            f_cand = -f_cand
            g_cand = -g_cand

        f_expr = sp.simplify(f_cand)
        g_expr = sp.simplify(g_cand)

        steps: list[SolutionStep] = []
        step_num = 1
        domain_restrictions: list[str] = []

        # Step 1: Identification
        std_latex = f"\\frac{{d{dep_var}}}{{d{var}}} = \\left( {expr_to_latex(f_expr)} \\right) \\left( {expr_to_latex(g_expr)} \\right)"
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Nhận dạng dạng phương trình",
                title="Nhận dạng phương trình vi phân tách biến (Separable ODE)",
                description=(
                    f"Đưa phương trình về dạng chuẩn y' = f({var})*g({dep_var}) với "
                    f"f({var}) = {f_expr} và g({dep_var}) = {g_expr}."
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

        # Step 2: Equilibrium solutions g(y) = 0 and denominator singularities
        eq_roots: list[sp.Expr] = []
        try:
            raw_roots = sp.solve(g_expr, dep_var)
            eq_roots = [sp.simplify(r) for r in raw_roots if r.is_real is not False]
        except Exception:
            pass

        # Check denominator singularities in g(y) and f(x)
        try:
            _, g_denom = sp.fraction(g_expr)
            if g_denom != 1 and dep_var in g_denom.free_symbols:
                denom_roots = sp.solve(g_denom, dep_var)
                for dr in denom_roots:
                    if dr.is_real is not False:
                        domain_restrictions.append(f"Điều kiện xác định: {dep_var} khác {dr} (mẫu số của g({dep_var}) khác 0).")
        except Exception:
            pass

        try:
            _, f_denom = sp.fraction(f_expr)
            if f_denom != 1 and var in f_denom.free_symbols:
                f_denom_roots = sp.solve(f_denom, var)
                for fdr in f_denom_roots:
                    if fdr.is_real is not False:
                        domain_restrictions.append(f"Điều kiện xác định: {var} khác {fdr} (mẫu số của f({var}) khác 0).")
        except Exception:
            pass

        eq_roots_latex = ", ".join(f"{dep_var} = {expr_to_latex(r)}" for r in eq_roots) if eq_roots else "\\emptyset"
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Nghiệm cân bằng",
                title="Xác định các nghiệm cân bằng (Equilibrium Solutions)",
                description=(
                    f"Tìm các giá trị làm g({dep_var}) = 0 để tránh mất nghiệm khi chia: "
                    f"{g_expr} = 0 => {', '.join(str(r) for r in eq_roots) if eq_roots else 'Không có nghiệm thực'}."
                ),
                content=ExpressionStepContent(
                    expression_before=f"{g_expr} = 0",
                    expression_after=f"y_eq in [{', '.join(str(r) for r in eq_roots)}]",
                    latex_before=f"{expr_to_latex(g_expr)} = 0",
                    latex_after=f"{dep_var}_{{eq}}: {eq_roots_latex}",
                ),
            )
        )
        step_num += 1

        # Check if initial condition hits an equilibrium solution directly
        is_equilibrium_hit = False
        hit_eq_val: sp.Expr | None = None
        if parsed.initial_condition is not None:
            _, y0 = parsed.initial_condition
            for r in eq_roots:
                if sp.simplify(y0 - r) == 0:
                    is_equilibrium_hit = True
                    hit_eq_val = r
                    break

        if is_equilibrium_hit and hit_eq_val is not None:
            part_sol = hit_eq_val
            part_sol_latex = f"{dep_var}({var}) = {expr_to_latex(hit_eq_val)}"

            t0, y0 = parsed.initial_condition  # type: ignore[misc]
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Áp dụng điều kiện ban đầu",
                    title="Nghiệm riêng trùng với nghiệm cân bằng",
                    description=(
                        f"Giá trị ban đầu y({t0}) = {y0} trùng với nghiệm cân bằng g({y0}) = 0. "
                        f"Theo định lý tồn tại và duy nhất nghiệm Picard–Lindelöf, nghiệm duy nhất của bài toán là hàm hằng y({var}) = {hit_eq_val}."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"y({t0}) = {y0}",
                        expression_after=f"y({var}) = {hit_eq_val}",
                        latex_before=f"{dep_var}({expr_to_latex(t0)}) = {expr_to_latex(y0)}",
                        latex_after=part_sol_latex,
                    ),
                )
            )

            # Verification of constant solution
            verif_res = self.verifier.verify_explicit(
                solution=part_sol,
                variable=var,
                p_expr=sp.Integer(0),
                g_expr=rhs_expr.subs(dep_var, hit_eq_val),
                initial_condition=parsed.initial_condition,
            )

            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.SUCCESS,
                verification=verif_res,
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result=f"{dep_var}({var}) = {part_sol}",
                final_latex=part_sol_latex,
                steps=tuple(steps),
                domain_restrictions=tuple(domain_restrictions),
                warnings=(),
                execution_time_ms=elapsed,
            )

        # Step 3: Separate variables: 1/g(y) dy = f(t) dt
        domain_restrictions.append(f"Điều kiện phân tách biến: g({dep_var}) = {g_expr} khác 0.")
        sep_latex = f"\\frac{{1}}{{{expr_to_latex(g_expr)}}} d{dep_var} = \\left( {expr_to_latex(f_expr)} \\right) d{var}"

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Phân tách biến số",
                title="Phân tách biến số hai vế",
                description=(
                    f"Chia hai vế cho g({dep_var}) = {g_expr} (với điều kiện {g_expr} khác 0) "
                    f"và nhân với d{var}: (1 / {g_expr}) d{dep_var} = {f_expr} d{var}."
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

        # Step 4: Integrate both sides
        int_g = sp.integrate(1 / g_expr, dep_var)
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

        int_latex = f"{expr_to_latex(int_g)} = {expr_to_latex(int_f)} + C"

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Tích phân hai vế",
                title="Tính tích phân hai vế và bổ sung hằng số tích phân C",
                description=(
                    f"Tính nguyên hàm: int(1 / {g_expr}) d{dep_var} = {int_g} và "
                    f"int({f_expr}) d{var} = {int_f} + C."
                ),
                content=ExpressionStepContent(
                    expression_before=f"int(1/({g_expr})) d{dep_var} = int({f_expr}) d{var}",
                    expression_after=f"{int_g} = {int_f} + C",
                    latex_before=f"\\int \\frac{{1}}{{{expr_to_latex(g_expr)}}} d{dep_var} = \\int \\left( {expr_to_latex(f_expr)} \\right) d{var}",
                    latex_after=int_latex,
                ),
            )
        )
        step_num += 1

        # Step 5: Solve for y(t) if possible
        explicit_sol: sp.Expr | None = None
        is_poly_in_y = False
        poly_deg = 0
        try:
            poly_deg = sp.degree(int_g, dep_var)
            is_poly_in_y = True
        except Exception:
            is_poly_in_y = False

        can_attempt_explicit = False
        if is_poly_in_y and poly_deg == 1:
            can_attempt_explicit = True
        elif not is_poly_in_y and len(int_g.atoms(sp.log)) <= 1:
            can_attempt_explicit = True

        if can_attempt_explicit:
            try:
                solved_y = sp.solve(int_g - (int_f + c_sym), dep_var)
                if solved_y and len(solved_y) == 1:
                    cand = sp.simplify(solved_y[0])
                    if sp.I not in cand.free_symbols:
                        explicit_sol = cand
            except Exception:
                explicit_sol = None

        if explicit_sol is not None:
            gen_latex = f"{dep_var}({var}) = {expr_to_latex(explicit_sol)}"
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Rút ra nghiệm tổng quát",
                    title="Giải phương trình đại số để tìm nghiệm tường minh y(t)",
                    description=f"Cô lập biến {dep_var} từ hệ thức tích phân để thu được nghiệm tường minh: y({var}) = {explicit_sol}.",
                    content=ExpressionStepContent(
                        expression_before=f"{int_g} = {int_f} + C",
                        expression_after=f"y({var}) = {explicit_sol}",
                        latex_before=int_latex,
                        latex_after=gen_latex,
                    ),
                )
            )
            step_num += 1
            final_sol_str = f"{dep_var}({var}) = {explicit_sol}"
            final_latex_sol = gen_latex
            sol_for_verif = explicit_sol
        else:
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Nghiệm ẩn",
                    title="Nghiệm tổng quát dưới dạng ẩn",
                    description=f"Hệ thức tích phân nghiệm ẩn: {int_g} = {int_f} + C.",
                    content=ExpressionStepContent(
                        expression_before=int_latex,
                        expression_after=f"{int_g} = {int_f} + C",
                        latex_before=int_latex,
                        latex_after=f"{expr_to_latex(int_g)} = {expr_to_latex(int_f)} + C",
                    ),
                )
            )
            step_num += 1
            final_sol_str = f"{int_g} = {int_f} + C"
            final_latex_sol = f"{expr_to_latex(int_g)} = {expr_to_latex(int_f)} + C"
            sol_for_verif = None

        # Step 6: Initial condition if given
        c_val_ic: sp.Expr | None = None
        if parsed.initial_condition is not None:
            t0, y0 = parsed.initial_condition
            c_val = sp.simplify(int_g.subs(dep_var, y0) - int_f.subs(var, t0))
            c_val_ic = c_val

            if explicit_sol is not None:
                part_sol = sp.simplify(explicit_sol.subs(c_sym, c_val))
                part_latex = f"{dep_var}({var}) = {expr_to_latex(part_sol)}"
                steps.append(
                    SolutionStep(
                        step_number=step_num,
                        rule_name="Áp dụng điều kiện ban đầu",
                        title="Xác định hằng số C và kết luận nghiệm riêng",
                        description=(
                            f"Thay {var} = {t0} và {dep_var} = {y0} vào hệ thức: "
                            f"C = {c_val} => Nghiệm riêng y({var}) = {part_sol}."
                        ),
                        content=ExpressionStepContent(
                            expression_before=f"C = ({int_g}) - ({int_f})",
                            expression_after=f"y({var}) = {part_sol}",
                            latex_before=f"C = {expr_to_latex(c_val)}",
                            latex_after=part_latex,
                        ),
                    )
                )
                final_sol_str = f"{dep_var}({var}) = {part_sol}"
                final_latex_sol = part_latex
                sol_for_verif = part_sol
            else:
                if c_val == 0:
                    part_str = f"{int_g} = {int_f}"
                    part_latex = f"{expr_to_latex(int_g)} = {expr_to_latex(int_f)}"
                else:
                    part_str = f"{int_g} = {int_f + c_val}" if not c_val.is_number or c_val > 0 else f"{int_g} = {int_f} - {-c_val}"
                    part_latex = f"{expr_to_latex(int_g)} = {expr_to_latex(int_f + c_val)}"
                steps.append(
                    SolutionStep(
                        step_number=step_num,
                        rule_name="Áp dụng điều kiện ban đầu",
                        title="Xác định hằng số C cho nghiệm ẩn",
                        description=f"Thay {var} = {t0} và {dep_var} = {y0}: C = {c_val}.",
                        content=ExpressionStepContent(
                            expression_before=f"{int_g} = {int_f} + C",
                            expression_after=part_str,
                            latex_before=f"{expr_to_latex(int_g)} = {expr_to_latex(int_f)} + C",
                            latex_after=part_latex,
                        ),
                    )
                )
                final_sol_str = part_str
                final_latex_sol = part_latex

        # Verification
        if sol_for_verif is not None:
            # Explicit verification
            verif_res = self.verifier.verify_explicit(
                solution=sol_for_verif,
                variable=var,
                p_expr=sp.Integer(0),
                g_expr=rhs_expr.subs(dep_var, sol_for_verif),
                initial_condition=parsed.initial_condition,
                integration_constant=c_sym,
            )
        else:
            verif_res = self.verifier.verify_implicit(
                potential_phi=int_g - int_f,
                x_sym=var,
                y_sym=dep_var,
                rhs_f_expr=f_expr,
                rhs_g_expr=g_expr,
                initial_condition=parsed.initial_condition,
                c_val=c_val_ic,
            )

        # Determine overall solution status
        warnings_list: list[str] = []
        if verif_res.status == VerificationStatus.FAILED:
            sol_status = SolutionStatus.DISCREPANCY_DETECTED
            warnings_list.append(f"Cảnh báo kiểm định toán học: {verif_res.details}")
        elif verif_res.status == VerificationStatus.UNVERIFIED:
            sol_status = SolutionStatus.UNVERIFIED
            warnings_list.append(f"Không thể kiểm chứng độc lập hoàn toàn: {verif_res.details}")
        else:
            sol_status = SolutionStatus.SUCCESS

        elapsed = (time.perf_counter() - t0_start) * 1000.0
        return SolutionResponse(
            status=sol_status,
            verification=verif_res,
            raw_input=request.raw_input,
            canonical_input=parsed.canonical_eq,
            final_result=final_sol_str,
            final_latex=final_latex_sol,
            steps=tuple(steps),
            domain_restrictions=tuple(domain_restrictions),
            warnings=tuple(warnings_list),
            execution_time_ms=elapsed,
        )

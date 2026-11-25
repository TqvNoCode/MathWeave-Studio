"""Integrating factor solver for non-exact ordinary differential equations: M dx + N dy = 0."""

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
from math_app.solvers.calculus.ode._real_calculus import (
    classify_finite_real_scalar,
    compute_differential_form_domain_metadata,
    real_integrate_expression,
    strip_log_abs,
    validate_differential_form_ic,
)
from math_app.verification.calculus.ode_verifier import (
    ODEVerifier,
    _prove_symbolic_zero,
    evaluate_initial_point_domain,
)


class ODEIntegratingFactorSolver(Solver):
    """Solver for differential equations with integrating factors: mu(x) or mu(y)."""

    def __init__(self, verifier: ODEVerifier | None = None) -> None:
        self.verifier = verifier or ODEVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type in (
            ProblemType.ODE_INTEGRATING_FACTOR,
            ProblemType.ODE_EXACT,
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

        x_var = parsed.independent_var
        y_var = parsed.dependent_var
        yp_sym = sp.Symbol("y_prime")

        # Standard form: M(x, y) + N(x, y)*y' = 0
        expanded_std = sp.expand(parsed.standard_expr)
        N_cand = expanded_std.coeff(yp_sym, 1)
        M_cand = expanded_std.coeff(yp_sym, 0)

        if N_cand == 0:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="integrating_factor_form_check",
                    details="Phương trình không có đạo hàm y' (hệ số N(x, y) = 0).",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=("Không tìm thấy thành phần N(x, y)*dy trong phương trình.",),
                execution_time_ms=elapsed,
            )

        M_expr = sp.simplify(M_cand)
        N_expr = sp.simplify(N_cand)

        invalid_resp = validate_differential_form_ic(
            raw_input=request.raw_input,
            parsed=parsed,
            x_var=x_var,
            y_var=y_var,
            M_expr=M_expr,
            N_expr=N_expr,
            elapsed_ms_fn=lambda: (time.perf_counter() - t0_start) * 1000.0,
        )
        if invalid_resp is not None:
            return invalid_resp

        ic_subs = (
            [(x_var, parsed.initial_condition[0]), (y_var, parsed.initial_condition[1])]
            if parsed.initial_condition is not None
            else None
        )

        steps: list[SolutionStep] = []
        step_num = 1

        # Step 1: Check exactness condition: dM/dy == dN/dx
        dM_dy = sp.simplify(sp.diff(M_expr, y_var))
        dN_dx = sp.simplify(sp.diff(N_expr, x_var))
        exactness_diff = sp.simplify(dM_dy - dN_dx)

        check_latex = (
            f"\\frac{{\\partial M}}{{\\partial {y_var}}} = {expr_to_latex(dM_dy)}, \\quad "
            f"\\frac{{\\partial N}}{{\\partial {x_var}}} = {expr_to_latex(dN_dx)}"
        )

        # Case 0: Already exact (mu = 1)
        if exactness_diff == 0:
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Kiểm tra tính vi phân toàn phần",
                    title="Kiểm tra điều kiện vi phân toàn phần ban đầu",
                    description=(
                        f"Tính các đạo hàm riêng: $\\frac{{\\partial M}}{{\\partial {y_var}}} = {expr_to_latex(dM_dy)}$ "
                        f"và $\\frac{{\\partial N}}{{\\partial {x_var}}} = {expr_to_latex(dN_dx)}$. "
                        f"Vì $\\frac{{\\partial M}}{{\\partial {y_var}}} = \\frac{{\\partial N}}{{\\partial {x_var}}}$, "
                        f"phương trình đã là vi phân toàn phần với thừa số tích phân $\\mu = 1$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"M = {M_expr}, N = {N_expr}",
                        expression_after=f"dM/d{y_var} = {dM_dy} == dN/d{x_var} = {dN_dx}",
                        latex_before=f"M({x_var}, {y_var}) = {expr_to_latex(M_expr)}, \\quad N({x_var}, {y_var}) = {expr_to_latex(N_expr)}",
                        latex_after=f"{check_latex} \\implies \\mu = 1",
                    ),
                )
            )
            step_num += 1
            mu_expr = sp.Integer(1)
            M_trans = M_expr
            N_trans = N_expr
        else:
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Kiểm tra tính vi phân toàn phần",
                    title="Kiểm tra điều kiện vi phân toàn phần ban đầu",
                    description=(
                        f"Xác định $M({x_var}, {y_var}) = {expr_to_latex(M_expr)}$ và $N({x_var}, {y_var}) = {expr_to_latex(N_expr)}$. "
                        f"Tính đạo hàm riêng: $\\frac{{\\partial M}}{{\\partial {y_var}}} = {expr_to_latex(dM_dy)}$ "
                        f"và $\\frac{{\\partial N}}{{\\partial {x_var}}} = {expr_to_latex(dN_dx)}$. "
                        f"Vì $\\frac{{\\partial M}}{{\\partial {y_var}}} \\ne \\frac{{\\partial N}}{{\\partial {x_var}}}$, "
                        f"phương trình ban đầu không phải vi phân toàn phần. Cần tìm thừa số tích phân $\\mu$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"M = {M_expr}, N = {N_expr}",
                        expression_after=f"dM/d{y_var} = {dM_dy} != dN/d{x_var} = {dN_dx}",
                        latex_before=f"M = {expr_to_latex(M_expr)}, \\quad N = {expr_to_latex(N_expr)}",
                        latex_after=check_latex,
                    ),
                )
            )
            step_num += 1

            # Step 2: Test integrating factor depending only on x: (M_y - N_x) / N = f(x)
            found_mu = False
            mu_expr = sp.Integer(1)
            M_trans = M_expr
            N_trans = N_expr

            if N_expr != 0:
                diff_over_N = sp.simplify((dM_dy - dN_dx) / N_expr)
                if y_var not in diff_over_N.free_symbols:
                    # Depends only on x!
                    f_x = diff_over_N
                    int_f = real_integrate_expression(f_x, x_var, source_expr=f_x, eval_subs=ic_subs)
                    if int_f is None:
                        elapsed = (time.perf_counter() - t0_start) * 1000.0
                        return SolutionResponse(
                            status=SolutionStatus.CANNOT_SOLVE,
                            verification=VerificationResult(
                                status=VerificationStatus.NOT_APPLICABLE,
                                method="integrating_factor_integration",
                                details=f"Tích phân int(f({x_var}) d{x_var}) không thể biểu diễn dưới dạng sơ cấp.",
                            ),
                            raw_input=request.raw_input,
                            canonical_input=parsed.canonical_eq,
                            final_result="",
                            final_latex="",
                            warnings=(f"Tích phân int(({f_x}) d{x_var}) không có nguyên hàm sơ cấp.",),
                            execution_time_ms=elapsed,
                        )

                    mu_expr = sp.simplify(sp.exp(int_f))
                    found_mu = True

                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name="Thừa số tích phân mu(x)",
                            title=f"Xác định thừa số tích phân phụ thuộc biến ${x_var}$: $\\mu({x_var})$",
                            description=(
                                f"Tính tỉ số $\\frac{{\\frac{{\\partial M}}{{\\partial {y_var}}} - \\frac{{\\partial N}}{{\\partial {x_var}}}}}{{N}} = "
                                f"\\frac{{{expr_to_latex(dM_dy)} - \\left({expr_to_latex(dN_dx)}\\right)}}{{{expr_to_latex(N_expr)}}} = {expr_to_latex(f_x)}$. "
                                f"Vì biểu thức này chỉ phụ thuộc vào biến ${x_var}$, thừa số tích phân là: "
                                f"$\\mu({x_var}) = \\exp\\left(\\int \\left({expr_to_latex(f_x)}\\right)\\,d{x_var}\\right) = {expr_to_latex(mu_expr)}$."
                            ),
                            content=ExpressionStepContent(
                                expression_before=f"(M_y - N_x) / N = {f_x}",
                                expression_after=f"mu({x_var}) = {mu_expr}",
                                latex_before=f"\\frac{{M_{{{y_var}}} - N_{{{x_var}}}}}{{N}} = {expr_to_latex(f_x)} = f({x_var})",
                                latex_after=f"\\mu({x_var}) = e^{{\\int {expr_to_latex(f_x)}\\,d{x_var}}} = {expr_to_latex(mu_expr)}",
                            ),
                        )
                    )
                    step_num += 1

            # Step 3: If not found, test integrating factor depending only on y: (N_x - M_y) / M = g(y)
            if not found_mu and M_expr != 0:
                diff_over_M = sp.simplify((dN_dx - dM_dy) / M_expr)
                if x_var not in diff_over_M.free_symbols:
                    # Depends only on y!
                    g_y = diff_over_M
                    int_g = real_integrate_expression(g_y, y_var, source_expr=g_y, eval_subs=ic_subs)
                    if int_g is None:
                        elapsed = (time.perf_counter() - t0_start) * 1000.0
                        return SolutionResponse(
                            status=SolutionStatus.CANNOT_SOLVE,
                            verification=VerificationResult(
                                status=VerificationStatus.NOT_APPLICABLE,
                                method="integrating_factor_integration",
                                details=f"Tích phân int(g({y_var}) d{y_var}) không thể biểu diễn dưới dạng sơ cấp.",
                            ),
                            raw_input=request.raw_input,
                            canonical_input=parsed.canonical_eq,
                            final_result="",
                            final_latex="",
                            warnings=(f"Tích phân int(({g_y}) d{y_var}) không có nguyên hàm sơ cấp.",),
                            execution_time_ms=elapsed,
                        )

                    mu_expr = sp.simplify(sp.exp(int_g))
                    found_mu = True

                    steps.append(
                        SolutionStep(
                            step_number=step_num,
                            rule_name="Thừa số tích phân mu(y)",
                            title=f"Xác định thừa số tích phân phụ thuộc biến ${y_var}$: $\\mu({y_var})$",
                            description=(
                                f"Tính tỉ số $\\frac{{\\frac{{\\partial N}}{{\\partial {x_var}}} - \\frac{{\\partial M}}{{\\partial {y_var}}}}}{{M}} = "
                                f"\\frac{{{expr_to_latex(dN_dx)} - \\left({expr_to_latex(dM_dy)}\\right)}}{{{expr_to_latex(M_expr)}}} = {expr_to_latex(g_y)}$. "
                                f"Vì biểu thức này chỉ phụ thuộc vào biến ${y_var}$, thừa số tích phân là: "
                                f"$\\mu({y_var}) = \\exp\\left(\\int \\left({expr_to_latex(g_y)}\\right)\\,d{y_var}\\right) = {expr_to_latex(mu_expr)}$."
                            ),
                            content=ExpressionStepContent(
                                expression_before=f"(N_x - M_y) / M = {g_y}",
                                expression_after=f"mu({y_var}) = {mu_expr}",
                                latex_before=f"\\frac{{N_{{{x_var}}} - M_{{{y_var}}}}}{{M}} = {expr_to_latex(g_y)} = g({y_var})",
                                latex_after=f"\\mu({y_var}) = e^{{\\int {expr_to_latex(g_y)}\\,d{y_var}}} = {expr_to_latex(mu_expr)}",
                            ),
                        )
                    )
                    step_num += 1

            if not found_mu:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="no_single_variable_integrating_factor",
                        details="Phương trình không có thừa số tích phân dạng \u03bc(x) hoặc \u03bc(y).",
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=(
                        f"Phương trình không phải vi phân toàn phần và không tồn tại thừa số tích phân phụ thuộc "
                        f"đơn biến \u03bc({x_var}) hoặc \u03bc({y_var}) (Unsupported integrating factor form).",
                    ),
                    execution_time_ms=elapsed,
                )

            # Multiply both M and N by mu
            if parsed.initial_condition is not None:
                x0, y0 = parsed.initial_condition
                allow_complex = M_expr.has(sp.I) or N_expr.has(sp.I)
                mu_dom_stat, err_mu = evaluate_initial_point_domain(
                    mu_expr, x_var, y_var, x0, y0, allow_complex=allow_complex
                )
                mu_ic_val = (
                    sp.simplify(mu_expr.subs([(x_var, x0), (y_var, y0)]))
                    if mu_dom_stat != "invalid"
                    else sp.nan
                )
                mu_scalar_stat, mu_scalar_err = (
                    classify_finite_real_scalar(mu_ic_val, (M_expr, N_expr))
                    if mu_dom_stat != "invalid"
                    else ("invalid", err_mu)
                )
                if mu_dom_stat == "invalid" or mu_scalar_stat == "invalid" or _prove_symbolic_zero(mu_ic_val):
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    reason = err_mu if mu_dom_stat == "invalid" else (mu_scalar_err or "mu = 0")
                    return SolutionResponse(
                        status=SolutionStatus.CANNOT_SOLVE,
                        verification=VerificationResult(
                            status=VerificationStatus.NOT_APPLICABLE,
                            method="integrating_factor_invalid_at_ic",
                            details=f"Thừa số tích phân μ = {mu_expr} triệt tiêu hoặc không xác định tại điểm ban đầu ({x0}, {y0}): {reason}.",
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        warnings=(
                            f"Thừa số tích phân \u03bc = {mu_expr} không hợp lệ (triệt tiêu hoặc chia cho 0) tại ({x0}, {y0}): {reason}.",
                        ),
                        execution_time_ms=elapsed,
                    )
                if mu_dom_stat == "unknown" or mu_scalar_stat == "unknown":
                    domain_meta_mu = compute_differential_form_domain_metadata(
                        parsed=parsed,
                        x_var=x_var,
                        y_var=y_var,
                        M_expr=M_expr,
                        N_expr=N_expr,
                        mu_expr=mu_expr,
                    )
                    elapsed = (time.perf_counter() - t0_start) * 1000.0
                    reason = err_mu if mu_dom_stat == "unknown" else mu_scalar_err
                    return SolutionResponse(
                        status=SolutionStatus.UNVERIFIED,
                        verification=VerificationResult(
                            status=VerificationStatus.UNVERIFIED,
                            method="integrating_factor_symbolic_unverified",
                            details=f"Không thể xác nhận tính hợp lệ thực hữu hạn khác 0 của thừa số tích phân μ = {mu_expr} tại ({x0}, {y0}): {reason}.",
                        ),
                        raw_input=request.raw_input,
                        canonical_input=parsed.canonical_eq,
                        final_result="",
                        final_latex="",
                        domain_restrictions=domain_meta_mu.domain_restrictions,
                        original_domain_latex=domain_meta_mu.original_domain_latex,
                        normalized_domain_latex=domain_meta_mu.normalized_domain_latex,
                        domain_completeness=domain_meta_mu.completeness,
                        warnings=(f"Không thể xác nhận thừa số tích phân μ = {mu_expr} tại ({x0}, {y0}): {reason}.",),
                        execution_time_ms=elapsed,
                    )

            M_trans = sp.simplify(mu_expr * M_expr)
            N_trans = sp.simplify(mu_expr * N_expr)

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Nhân thừa số tích phân (ODE không toàn phần)",
                    title=f"Nhân phương trình với thừa số tích phân $\\mu({x_var if found_mu and 'mu(x)' in steps[-1].rule_name else y_var})$",
                    description=(
                        f"Nhân $M$ và $N$ với $\\mu = {expr_to_latex(mu_expr)}$ thu được phương trình tương đương: "
                        f"$\\left({expr_to_latex(M_trans)}\\right)\\,d{x_var} + \\left({expr_to_latex(N_trans)}\\right)\\,d{y_var} = 0$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"({M_expr})*dx + ({N_expr})*dy = 0",
                        expression_after=f"({M_trans})*dx + ({N_trans})*dy = 0",
                        latex_before=f"({expr_to_latex(M_expr)})\\,d{x_var} + ({expr_to_latex(N_expr)})\\,d{y_var} = 0",
                        latex_after=f"({expr_to_latex(M_trans)})\\,d{x_var} + ({expr_to_latex(N_trans)})\\,d{y_var} = 0",
                    ),
                )
            )
            step_num += 1

            # Verify that the transformed equation is exact: d(mu*M)/dy == d(mu*N)/dx
            dM_trans_dy = sp.simplify(sp.diff(M_trans, y_var))
            dN_trans_dx = sp.simplify(sp.diff(N_trans, x_var))
            trans_exact_diff = sp.simplify(dM_trans_dy - dN_trans_dx)

            if trans_exact_diff != 0:
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.ERROR,
                    verification=VerificationResult(
                        status=VerificationStatus.FAILED,
                        method="transformed_exactness_verification_failed",
                        details="Phương trình sau khi nhân thừa số tích phân vẫn không thỏa mãn tính vi phân toàn phần.",
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    warnings=("Sai lệch trong quá trình biến đổi thừa số tích phân.",),
                    execution_time_ms=elapsed,
                )

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Kiểm tra tính vi phân toàn phần sau khi nhân mu",
                    title="Xác nhận phương trình mới là vi phân toàn phần",
                    description=(
                        f"Tính đạo hàm riêng của các hệ số mới: "
                        f"$\\frac{{\\partial M_{{\\text{{new}}}}}}{{\\partial {y_var}}} = {expr_to_latex(dM_trans_dy)}$ "
                        f"và $\\frac{{\\partial N_{{\\text{{new}}}}}}{{\\partial {x_var}}} = {expr_to_latex(dN_trans_dx)}$. "
                        f"Vì $\\frac{{\\partial M_{{\\text{{new}}}}}}{{\\partial {y_var}}} = \\frac{{\\partial N_{{\\text{{new}}}}}}{{\\partial {x_var}}}$, "
                        f"phương trình mới là vi phân toàn phần."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"M_new = {M_trans}, N_new = {N_trans}",
                        expression_after=f"dM_new/d{y_var} = {dM_trans_dy} == dN_new/d{x_var} = {dN_trans_dx}",
                        latex_before=f"M_{{new}} = {expr_to_latex(M_trans)}, \\quad N_{{new}} = {expr_to_latex(N_trans)}",
                        latex_after=f"\\frac{{\\partial M_{{new}}}}{{\\partial {y_var}}} = {expr_to_latex(dM_trans_dy)} = \\frac{{\\partial N_{{new}}}}{{\\partial {x_var}}}",
                    ),
                )
            )
            step_num += 1

        # Preserve source restrictions and build integrating-factor / denominator metadata
        domain_meta = compute_differential_form_domain_metadata(
            parsed=parsed,
            x_var=x_var,
            y_var=y_var,
            M_expr=M_expr,
            N_expr=N_expr,
            mu_expr=mu_expr,
        )

        # Construct potential function Psi(x, y):
        # Psi_1 = int(M_trans dx)
        psi_expr = real_integrate_expression(M_trans, x_var, source_expr=M_trans, eval_subs=ic_subs)
        if psi_expr is None:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="integrating_factor_potential_integration",
                    details=f"Tích phân int({M_trans} d{x_var}) không có nguyên hàm sơ cấp thực.",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=(f"Không thể tìm nguyên hàm sơ cấp thực cho M_new({x_var}, {y_var}).",),
                execution_time_ms=elapsed,
            )
        psi_latex = f"\\Psi({x_var}, {y_var}) = \\int \\left( {expr_to_latex(M_trans)} \\right) d{x_var} = {expr_to_latex(psi_expr)}"

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Tích phân hai vế",
                title=f"Tích phân hàm $M_{{\\text{{new}}}}({x_var}, {y_var})$ theo biến ${x_var}$",
                description=(
                    f"Lấy nguyên hàm theo biến ${x_var}$ (coi ${y_var}$ là hằng số): "
                    f"$\\Psi({x_var}, {y_var}) = \\int \\left({expr_to_latex(M_trans)}\\right)\\,d{x_var} = {expr_to_latex(psi_expr)} + h({y_var})$."
                ),
                content=ExpressionStepContent(
                    expression_before=f"int({M_trans}) d{x_var}",
                    expression_after=f"Psi = {psi_expr} + h({y_var})",
                    latex_before=f"\\int M_{{new}}({x_var}, {y_var})\\,d{x_var}",
                    latex_after=f"{psi_latex} + h({y_var})",
                ),
            )
        )
        step_num += 1

        # Find h(y): dPsi/dy + h'(y) = N_trans => h'(y) = N_trans - dPsi/dy
        dpsi_dy = sp.simplify(sp.diff(strip_log_abs(psi_expr), y_var))
        h_prime = sp.simplify(N_trans - dpsi_dy)

        if x_var in h_prime.free_symbols:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.ERROR,
                verification=VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="integrating_factor_potential_construction",
                    details=f"h'({y_var}) vẫn phụ thuộc vào biến {x_var}; vi phạm tính giải tích.",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=("Không thể xây dựng hàm thế do sai lệch trong tích phân.",),
                execution_time_ms=elapsed,
            )

        h_expr = real_integrate_expression(h_prime, y_var, source_expr=h_prime, eval_subs=ic_subs)
        if h_expr is None:
            elapsed = (time.perf_counter() - t0_start) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="integrating_factor_potential_integration",
                    details=f"Tích phân int({h_prime} d{y_var}) không có nguyên hàm sơ cấp thực.",
                ),
                raw_input=request.raw_input,
                canonical_input=parsed.canonical_eq,
                final_result="",
                final_latex="",
                warnings=(f"Không thể tìm nguyên hàm sơ cấp thực cho h'({y_var}).",),
                execution_time_ms=elapsed,
            )
        h_latex = f"h'({y_var}) = {expr_to_latex(h_prime)} \\implies h({y_var}) = {expr_to_latex(h_expr)}"

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Xác định hệ số",
                title=f"Xác định hàm số phụ $h({y_var})$",
                description=(
                    f"Đạo hàm riêng theo ${y_var}$: $\\frac{{\\partial \\Psi}}{{\\partial {y_var}}} = {expr_to_latex(dpsi_dy)}$. "
                    f"So sánh với $N_{{\\text{{new}}}}$: $h'({y_var}) = N_{{\\text{{new}}}} - \\frac{{\\partial \\Psi}}{{\\partial {y_var}}} = {expr_to_latex(h_prime)}$. "
                    f"Tích phân suy ra: $h({y_var}) = {expr_to_latex(h_expr)}$."
                ),
                content=ExpressionStepContent(
                    expression_before=f"h'({y_var}) = {N_trans} - ({dpsi_dy})",
                    expression_after=f"h({y_var}) = {h_expr}",
                    latex_before=f"h'({y_var}) = N_{{new}} - \\frac{{\\partial \\Psi}}{{\\partial {y_var}}}",
                    latex_after=h_latex,
                ),
            )
        )
        step_num += 1

        # Construct potential function F(x, y) = Psi + h
        potential_F = sp.expand(psi_expr + h_expr)
        potential_latex = f"F({x_var}, {y_var}) = {expr_to_latex(potential_F)}"

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Xây dựng hàm thế",
                title=f"Xây dựng hàm thế vi phân toàn phần $F({x_var}, {y_var})$",
                description=(
                    f"Hàm thế là $F({x_var}, {y_var}) = \\Psi({x_var}, {y_var}) + h({y_var}) = {expr_to_latex(potential_F)}$. "
                    f"Nghiệm ẩn tổng quát của phương trình là $F({x_var}, {y_var}) = C$, tức ${expr_to_latex(potential_F)} = C$."
                ),
                content=ExpressionStepContent(
                    expression_before=f"F = ({psi_expr}) + ({h_expr})",
                    expression_after=f"F({x_var}, {y_var}) = {potential_F} = C",
                    latex_before=f"F({x_var}, {y_var}) = \\Psi + h({y_var})",
                    latex_after=f"{potential_latex} = C",
                ),
            )
        )
        step_num += 1

        final_sol_str = f"{potential_F} = C"
        final_latex_sol = f"{expr_to_latex(potential_F)} = C"

        # Initial condition if provided
        if parsed.initial_condition is not None:
            x0, y0 = parsed.initial_condition
            c_val = sp.simplify(potential_F.subs([(x_var, x0), (y_var, y0)]))
            c_stat, c_err = classify_finite_real_scalar(c_val, (M_expr, N_expr))
            if c_stat == "invalid":
                elapsed = (time.perf_counter() - t0_start) * 1000.0
                return SolutionResponse(
                    status=SolutionStatus.CANNOT_SOLVE,
                    verification=VerificationResult(
                        status=VerificationStatus.NOT_APPLICABLE,
                        method="integrating_factor_ic_domain_violation",
                        details=f"Không thể xác định hằng số thực hữu hạn tại ({x0}, {y0}): {c_err}.",
                    ),
                    raw_input=request.raw_input,
                    canonical_input=parsed.canonical_eq,
                    final_result="",
                    final_latex="",
                    domain_restrictions=domain_meta.domain_restrictions,
                    original_domain_latex=domain_meta.original_domain_latex,
                    normalized_domain_latex=domain_meta.normalized_domain_latex,
                    domain_completeness=domain_meta.completeness,
                    warnings=(f"Hàm thế không cho giá trị thực hữu hạn tại điều kiện ban đầu ({x0}, {y0}): {c_err}.",),
                    execution_time_ms=elapsed,
                )
            part_latex = f"{expr_to_latex(potential_F)} = {expr_to_latex(c_val)}"

            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Áp dụng điều kiện ban đầu",
                    title="Xác định hằng số C từ điều kiện ban đầu",
                    description=(
                        f"Thay ${x_var} = {expr_to_latex(x0)}$ và ${y_var} = {expr_to_latex(y0)}$ vào hàm thế để tìm hằng số $C$: "
                        f"$C = F({expr_to_latex(x0)}, {expr_to_latex(y0)}) = {expr_to_latex(c_val)}$. "
                        f"Nghiệm riêng của bài toán là ${part_latex}$."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"C = F({x0}, {y0})",
                        expression_after=f"{potential_F} = {c_val}",
                        latex_before=f"C = F({expr_to_latex(x0)}, {expr_to_latex(y0)})",
                        latex_after=part_latex,
                    ),
                )
            )
            step_num += 1
            final_sol_str = f"{potential_F} = {c_val}"
            final_latex_sol = part_latex

        # Verification of integrating factor gradient
        verif_res = self.verifier.verify_integrating_factor(
            potential_F=potential_F,
            mu_expr=mu_expr,
            M_expr=M_expr,
            N_expr=N_expr,
            x_sym=x_var,
            y_sym=y_var,
            initial_condition=parsed.initial_condition,
            source_constraints=getattr(parsed, "original_domain_constraints", ()),
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
            domain_restrictions=domain_meta.domain_restrictions,
            original_domain_latex=domain_meta.original_domain_latex,
            normalized_domain_latex=domain_meta.normalized_domain_latex,
            domain_completeness=domain_meta.completeness,
            warnings=tuple(warnings_list),
            execution_time_ms=elapsed,
        )

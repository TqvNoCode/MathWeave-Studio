"""Integration solver for definite and indefinite calculus integrals."""

from __future__ import annotations

import time
import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionResponse
from math_app.application.ports.solver import Solver
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.input.parser import parse_mathematical_input, parse_safe_expression
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.solvers.calculus.integration.rule_engine import IntegrationRuleEngine
from math_app.solvers.calculus.integration.step_builder import IntegrationStepBuilder
from math_app.verification.calculus.integral_verifier import IntegralVerifier


class IntegralSolver(Solver):
    """Calculus solver for indefinite and definite integration with pedagogical steps."""

    def __init__(self, verifier: IntegralVerifier | None = None) -> None:
        self._verifier = verifier or IntegralVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type in {
            ProblemType.INTEGRAL,
            ProblemType.INDEFINITE_INTEGRAL,
            ProblemType.DEFINITE_INTEGRAL,
        }

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        start_time = time.perf_counter()

        # 1. Parse and validate input
        expr, var = parse_mathematical_input(request.raw_input, request.target_variable)

        is_definite = (
            request.problem_type == ProblemType.DEFINITE_INTEGRAL
            or ("lower_bound" in request.parameters and "upper_bound" in request.parameters)
        )

        builder = IntegrationStepBuilder()
        engine = IntegrationRuleEngine()

        # Compute antiderivative F(x)
        raw_antiderivative = engine.integrate(expr, var, builder, is_definite=is_definite)

        if isinstance(raw_antiderivative, sp.Add):
            antiderivative = raw_antiderivative
        else:
            try:
                antiderivative = sp.simplify(raw_antiderivative)
            except Exception:
                antiderivative = raw_antiderivative

        domain_restrictions: list[str] = []
        try:
            _, denom = expr.as_numer_denom()
            if denom.has(var) and denom != sp.Integer(1):
                base_denom = sp.sqf_part(denom)
                domain_restrictions.append(f"Điều kiện mẫu số xác định: Mẫu số {base_denom} != 0")
            if expr.has(sp.tan) or expr.has(sp.sec):
                domain_restrictions.append(f"Điều kiện hàm tan / sec: cos({var.name}) != 0 (tức {var.name} != π/2 + kπ)")
            if expr.has(sp.cot) or expr.has(sp.csc):
                domain_restrictions.append(f"Điều kiện hàm cot / csc: sin({var.name}) != 0 (tức {var.name} != kπ)")
        except Exception:
            pass

        warnings: list[str] = []

        if is_definite:
            # Definite integral
            raw_a = str(request.parameters.get("lower_bound", "0")).strip()
            raw_b = str(request.parameters.get("upper_bound", "1")).strip()

            try:
                a_bound = parse_safe_expression(raw_a, evaluate=True)
                b_bound = parse_safe_expression(raw_b, evaluate=True)
            except Exception as exc:
                raise InvalidInputError(f"Cận tích phân không hợp lệ: {exc}") from exc

            # Fundamental Theorem of Calculus: F(b) - F(a)
            try:
                fb = antiderivative.subs(var, b_bound)
                fa = antiderivative.subs(var, a_bound)
                definite_val = sp.simplify(fb - fa)
            except Exception as exc:
                # Direct fallback
                try:
                    definite_val = sp.integrate(expr, (var, a_bound, b_bound))
                    fb = definite_val
                    fa = sp.Integer(0)
                except Exception as direct_exc:
                    raise InvalidInputError(f"Không thể tính giá trị tích phân xác định trong cận đã cho: {direct_exc}") from exc

            a_ltx = expr_to_latex(a_bound)
            b_ltx = expr_to_latex(b_bound)
            aligned_def = (
                f"\\begin{{aligned}}\n"
                f"  \\int_{{{a_ltx}}}^{{{b_ltx}}} \\left( {expr_to_latex(expr)} \\right) d{var.name}\n"
                f"  &= \\left[ {expr_to_latex(antiderivative)} \\right]_{{{a_ltx}}}^{{{b_ltx}}} \\\\\n"
                f"  &= \\left[ {expr_to_latex(fb)} \\right] - \\left[ {expr_to_latex(fa)} \\right] \\\\\n"
                f"  &= {expr_to_latex(definite_val)}\n"
                f"\\end{{aligned}}"
            )

            builder.add_step(
                rule_name="Định lý cơ bản của Giải tích",
                title="Áp dụng công thức Newton–Leibniz",
                description=(
                    f"Thế cận: F({b_bound}) - F({a_bound}) = "
                    f"[{fb}] - [{fa}] = {definite_val}"
                ),
                before=f"F({b_bound}) - F({a_bound})",
                after=definite_val,
                equation_latex=aligned_def,
                notes="Thế cận tích phân",
            )

            verification_result = self._verifier.verify_definite(expr, definite_val, var, a_bound, b_bound)

            final_result_str = str(definite_val)
            final_latex_str = expr_to_latex(definite_val)

        else:
            # Indefinite integral: F(x) + C
            verification_result = self._verifier.verify_indefinite(expr, antiderivative, var)

            anti_latex = expr_to_latex(antiderivative)
            has_c_in_steps = any("+ C" in s.content.latex_after for s in builder.get_steps())
            if not has_c_in_steps:
                builder.add_step(
                    rule_name="Hằng số tích phân",
                    title="Bổ sung hằng số tích phân C",
                    description="Bổ sung hằng số tích phân C để biểu diễn họ nguyên hàm tổng quát.",
                    before=anti_latex,
                    after=f"{anti_latex} + C",
                    equation_latex=f"\\int f({var.name})\\,d{var.name} = {anti_latex} + C",
                    notes="Hằng số C",
                )

            final_result_str = f"{antiderivative} + C"
            final_latex_str = f"{anti_latex} + C"

        # Determine overall solution status
        if verification_result.status == VerificationStatus.FAILED:
            status = SolutionStatus.DISCREPANCY_DETECTED
            warnings.append(f"Cảnh báo kiểm định toán học: {verification_result.details}")
        elif engine.had_fallback:
            status = SolutionStatus.PARTIAL
            warnings.append("Một số bước tích phân được giải trực tiếp bằng công cụ ký hiệu do chưa có phân rã từng bước sư phạm.")
        else:
            status = SolutionStatus.SUCCESS

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return SolutionResponse(
            status=status,
            verification=verification_result,
            raw_input=request.raw_input,
            canonical_input=str(expr),
            final_result=final_result_str,
            final_latex=final_latex_str,
            steps=builder.get_steps(),
            domain_restrictions=tuple(domain_restrictions),
            warnings=tuple(warnings),
            execution_time_ms=elapsed_ms,
        )

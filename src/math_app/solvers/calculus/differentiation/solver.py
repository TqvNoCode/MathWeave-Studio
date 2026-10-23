"""Derivative solver providing step-by-step differentiation and verification."""

from __future__ import annotations

import time
import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionResponse
from math_app.application.ports.solver import Solver
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.input.parser import parse_mathematical_input
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.solvers.calculus.differentiation.rule_engine import DifferentiationRuleEngine
from math_app.solvers.calculus.differentiation.step_builder import DifferentiationStepBuilder
from math_app.verification.calculus.derivative_verifier import DerivativeVerifier


class DerivativeSolver(Solver):
    """Calculus solver for single-variable differentiation with pedagogical steps."""

    def __init__(self, verifier: DerivativeVerifier | None = None) -> None:
        self._verifier = verifier or DerivativeVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type in {
            ProblemType.DERIVATIVE,
            ProblemType.HIGHER_ORDER_DERIVATIVE,
            ProblemType.PARTIAL_DERIVATIVE,
        }

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        start_time = time.perf_counter()

        # 1. Parse and validate input
        expr, var = parse_mathematical_input(request.raw_input, request.target_variable)

        order = 1
        if "order" in request.parameters:
            try:
                order = max(1, int(request.parameters["order"]))
            except (ValueError, TypeError):
                order = 1

        # 2. Derive steps using rule engine
        builder = DifferentiationStepBuilder()
        engine = DifferentiationRuleEngine()

        current_expr = expr
        raw_derived = expr
        for step_order in range(1, order + 1):
            if order > 1:
                # Add milestone note for higher order
                builder.add_step(
                    rule_name=f"Khởi tạo đạo hàm cấp {step_order}" if step_order > 1 else "Đạo hàm cấp 1",
                    rule_name_vi=f"Đạo hàm cấp {step_order}",
                    title=f"Tính đạo hàm cấp {step_order}",
                    description=f"Tính đạo hàm cấp {step_order} theo biến {var.name} của biểu thức toán học:",
                    before=current_expr,
                    after=current_expr,
                    notes=f"Cấp {step_order}",
                )
            raw_derived = engine.differentiate(current_expr, var, builder)
            current_expr = raw_derived

        # Simplify final result for presentation
        try:
            final_expr = sp.simplify(raw_derived)
        except Exception:
            final_expr = raw_derived

        # 3. Independent mathematical verification
        if order > 1:
            try:
                verification_result = self._verifier.verify(expr, raw_derived, var, order=order)
            except TypeError:
                verification_result = self._verifier.verify(expr, raw_derived, var)
        else:
            verification_result = self._verifier.verify(expr, raw_derived, var)

        # 4. Detect structural domain restrictions
        domain_restrictions: list[str] = []
        try:
            seen_denoms = set()
            for e in (expr, final_expr):
                _, denom = e.as_numer_denom()
                if denom.has(var) and denom != sp.Integer(1):
                    base_denom = sp.sqf_part(denom)
                    if base_denom not in seen_denoms:
                        seen_denoms.add(base_denom)
                        domain_restrictions.append(f"Điều kiện mẫu số xác định: Mẫu số {base_denom} != 0")
            if expr.has(sp.tan) or final_expr.has(sp.tan) or expr.has(sp.sec) or final_expr.has(sp.sec):
                domain_restrictions.append(f"Điều kiện hàm tan / sec: cos({var.name}) != 0 (tức {var.name} != π/2 + kπ)")
            if expr.has(sp.cot) or final_expr.has(sp.cot) or expr.has(sp.csc) or final_expr.has(sp.csc):
                domain_restrictions.append(f"Điều kiện hàm cot / csc: sin({var.name}) != 0 (tức {var.name} != kπ)")
            if expr.has(sp.log) or final_expr.has(sp.log):
                domain_restrictions.append("Điều kiện hàm logarit tự nhiên: Biểu thức dưới dấu ln phải dương (> 0)")
        except Exception:
            pass

        # 5. Determine overall solution status
        warnings: list[str] = []
        if verification_result.status == VerificationStatus.FAILED:
            status = SolutionStatus.DISCREPANCY_DETECTED
            warnings.append(
                f"Cảnh báo kiểm định toán học: {verification_result.details}"
            )
        elif engine.had_fallback:
            status = SolutionStatus.PARTIAL
            warnings.append("Một số bước được giải trực tiếp bằng công cụ ký hiệu do chưa có phân rã từng bước sư phạm.")
        else:
            status = SolutionStatus.SUCCESS

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return SolutionResponse(
            status=status,
            verification=verification_result,
            raw_input=request.raw_input,
            canonical_input=str(expr),
            final_result=str(final_expr),
            final_latex=expr_to_latex(final_expr),
            steps=builder.get_steps(),
            domain_restrictions=tuple(domain_restrictions),
            warnings=tuple(warnings),
            execution_time_ms=elapsed_ms,
        )

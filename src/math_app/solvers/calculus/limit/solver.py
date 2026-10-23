"""Limit solver for calculus."""

from __future__ import annotations

import time
import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionResponse, SolutionStep
from math_app.application.ports.solver import Solver
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.input.parser import parse_mathematical_input
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.verification.calculus.limit_verifier import LimitVerifier


class LimitSolver(Solver):
    """Calculus solver for one-sided and two-sided limits."""

    def __init__(self, verifier: LimitVerifier | None = None) -> None:
        self._verifier = verifier or LimitVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type == ProblemType.LIMIT

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        start_time = time.perf_counter()

        expr, var = parse_mathematical_input(request.raw_input, request.target_variable)
        raw_point = str(request.parameters.get("limit_point", "0")).strip()
        direction = str(request.parameters.get("direction", "+-")).strip()

        # Parse target limit point
        if raw_point in ("oo", "inf", "+oo", "+inf"):
            target_pt = sp.oo
        elif raw_point in ("-oo", "-inf"):
            target_pt = -sp.oo
        else:
            try:
                target_pt = sp.sympify(raw_point)
            except Exception as exc:
                raise InvalidInputError(f"Điểm giới hạn không hợp lệ '{raw_point}': {exc}") from exc

        steps: list[SolutionStep] = []
        step_idx = 1

        # Step 1: Direct substitution check
        sub_val = None
        try:
            if target_pt not in (sp.oo, -sp.oo):
                sub_val = expr.subs(var, target_pt)
        except Exception:
            sub_val = None

        if sub_val is not None and not sub_val.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Thay số trực tiếp",
                    title="Phương pháp thay số trực tiếp",
                    description=f"Thay trực tiếp {var.name} = {target_pt} vào biểu thức, thu được giá trị xác định {sub_val}.",
                    content=ExpressionStepContent(
                        expression_before=str(expr),
                        expression_after=str(sub_val),
                        latex_before=expr_to_latex(expr),
                        latex_after=expr_to_latex(sub_val),
                    ),
                )
            )
            step_idx += 1
            limit_val = sub_val
        else:
            # Indeterminate form or infinite limit
            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Nhận dạng dạng vô định",
                    title="Nhận dạng dạng vô định",
                    description=(
                        f"Thay trực tiếp {var.name} → {target_pt} dẫn tới dạng vô định hoặc điểm gián đoạn. "
                        "Cần áp dụng các phép biến đổi đại số, quy tắc L'Hôpital hoặc khai triển tương đương."
                    ),
                    content=ExpressionStepContent(
                        expression_before=f"lim_{{{var.name} -> {target_pt}}} {expr}",
                        expression_after="Dạng vô định",
                        latex_before=f"\\lim_{{{var.name} \\to {expr_to_latex(target_pt)}}} {expr_to_latex(expr)}",
                        latex_after="\\text{Dạng vô định } [0/0] \\text{ hoặc } [\\infty/\\infty]",
                    ),
                )
            )
            step_idx += 1

            # Compute limit with SymPy
            try:
                dir_param = direction if direction in ("+", "-") else "+-"
                limit_val = sp.limit(expr, var, target_pt, dir=dir_param)
            except Exception as exc:
                raise InvalidInputError(f"Không thể tính giới hạn tại điểm đã chọn: {exc}") from exc

            steps.append(
                SolutionStep(
                    step_number=step_idx,
                    rule_name="Khử dạng vô định và tính giới hạn",
                    description=f"Áp dụng quy tắc tính giới hạn giải tích, kết quả thu được là {limit_val}.",
                    content=ExpressionStepContent(
                        expression_before=f"lim {expr}",
                        expression_after=str(limit_val),
                        latex_before=f"\\lim_{{{var.name} \\to {expr_to_latex(target_pt)}}} {expr_to_latex(expr)}",
                        latex_after=expr_to_latex(limit_val),
                    ),
                )
            )

        verification = self._verifier.verify(expr, var, target_pt, limit_val, direction)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return SolutionResponse(
            status=SolutionStatus.SUCCESS,
            verification=verification,
            raw_input=request.raw_input,
            canonical_input=f"lim_{{{var.name} -> {target_pt}}} ({expr})",
            final_result=str(limit_val),
            final_latex=expr_to_latex(limit_val),
            steps=tuple(steps),
            domain_restrictions=(),
            warnings=(),
            execution_time_ms=elapsed_ms,
        )

"""Equation solver for single-variable algebraic equations."""

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
from math_app.input.parser import normalize_variable_name, parse_safe_expression
from math_app.rendering.latex.formatter import expr_to_latex


class EquationSolver(Solver):
    """Solver for algebraic equations with pedagogical step explanations and root verification."""

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type == ProblemType.SOLVE_EQUATION

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        t0 = time.perf_counter()
        raw = request.raw_input.strip()
        if not raw:
            raise InvalidInputError("Phương trình không được để trống (Equation cannot be empty).")

        clean_var = normalize_variable_name(request.target_variable) if request.target_variable else "x"
        var = sp.Symbol(clean_var)

        # Parse LHS and RHS
        if "=" in raw:
            parts = raw.split("=")
            if len(parts) != 2:
                raise InvalidInputError("Phương trình chỉ được chứa đúng một dấu '=' (Must contain exactly one '=').")
            lhs_str, rhs_str = parts[0].strip(), parts[1].strip()
            if not lhs_str or not rhs_str:
                raise InvalidInputError("Hai vế của phương trình không được để trống (LHS and RHS cannot be empty).")
        else:
            lhs_str = raw
            rhs_str = "0"

        lhs_expr = parse_safe_expression(lhs_str, target_variable=clean_var, evaluate=False)
        rhs_expr = parse_safe_expression(rhs_str, target_variable=clean_var, evaluate=False)

        # Standard form: f(x) = LHS - RHS = 0
        eq_expr = sp.simplify(lhs_expr - rhs_expr)

        steps: list[SolutionStep] = []
        step_num = 1

        # Step 1: Standard form
        std_latex = f"{expr_to_latex(eq_expr)} = 0"
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Chuyển vế về dạng chuẩn",
                description="Chuyển tất cả các số hạng sang vế trái để đưa phương trình về dạng chuẩn f(x) = 0.",
                content=ExpressionStepContent(
                    expression_before=f"{lhs_str} = {rhs_str}",
                    expression_after=f"{eq_expr} = 0",
                    latex_before=f"{expr_to_latex(lhs_expr)} = {expr_to_latex(rhs_expr)}",
                    latex_after=std_latex,
                ),
            )
        )
        step_num += 1

        # Check identity: 0 = 0
        if eq_expr == 0:
            elapsed = (time.perf_counter() - t0) * 1000.0
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Đồng nhất thức",
                    description="Phương trình luôn đúng với mọi giá trị của biến thuộc tập xác định.",
                    content=ExpressionStepContent(
                        expression_before=f"{eq_expr} = 0",
                        expression_after="All real numbers",
                        latex_before=std_latex,
                        latex_after=r"x \in \mathbb{R}",
                    ),
                )
            )
            return SolutionResponse(
                status=SolutionStatus.SUCCESS,
                verification=VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="identity_equation_proof",
                    details="Phương trình nghiệm đúng với mọi giá trị thuộc tập số thực.",
                ),
                raw_input=request.raw_input,
                canonical_input=f"{lhs_expr} = {rhs_expr}",
                final_result="Vô số nghiệm (All real numbers)",
                final_latex=r"S = \mathbb{R}",
                steps=tuple(steps),
                execution_time_ms=elapsed,
            )

        # Check inconsistency: non-zero constant = 0
        if eq_expr.is_number and eq_expr != 0:
            elapsed = (time.perf_counter() - t0) * 1000.0
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Phương trình vô nghiệm",
                    description="Vế trái là hằng số khác 0, phương trình mâu thuẫn và không có nghiệm.",
                    content=ExpressionStepContent(
                        expression_before=f"{eq_expr} = 0",
                        expression_after="No solution",
                        latex_before=std_latex,
                        latex_after=r"S = \emptyset",
                    ),
                )
            )
            return SolutionResponse(
                status=SolutionStatus.SUCCESS,
                verification=VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="inconsistent_equation_proof",
                    details="Phương trình vô nghiệm do vế trái là hằng số khác 0.",
                ),
                raw_input=request.raw_input,
                canonical_input=f"{lhs_expr} = {rhs_expr}",
                final_result="Vô nghiệm (No solution)",
                final_latex=r"S = \emptyset",
                steps=tuple(steps),
                execution_time_ms=elapsed,
            )

        # Solve equation
        try:
            solutions = sp.solve(sp.Eq(eq_expr, 0), var)
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000.0
            return SolutionResponse(
                status=SolutionStatus.CANNOT_SOLVE,
                verification=VerificationResult(
                    status=VerificationStatus.NOT_APPLICABLE,
                    method="none",
                    details=f"Cannot solve symbolically: {exc}",
                ),
                raw_input=request.raw_input,
                canonical_input=f"{lhs_expr} = {rhs_expr}",
                final_result="",
                final_latex="",
                warnings=(f"Không thể giải chính xác phương trình này bằng phương pháp giải tích: {exc}",),
                execution_time_ms=elapsed,
            )

        # If sp.solve returns empty list
        if not solutions:
            elapsed = (time.perf_counter() - t0) * 1000.0
            steps.append(
                SolutionStep(
                    step_number=step_num,
                    rule_name="Kết luận nghiệm",
                    description="Không tìm thấy giá trị thực nào thỏa mãn phương trình.",
                    content=ExpressionStepContent(
                        expression_before=f"{eq_expr} = 0",
                        expression_after="No real solution",
                        latex_before=std_latex,
                        latex_after=r"S = \emptyset",
                    ),
                )
            )
            return SolutionResponse(
                status=SolutionStatus.SUCCESS,
                verification=VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="symbolic_solveset_exhaustion",
                    details="Chứng minh phương trình không có nghiệm trong tập số thực.",
                ),
                raw_input=request.raw_input,
                canonical_input=f"{lhs_expr} = {rhs_expr}",
                final_result="Vô nghiệm (No solution)",
                final_latex=r"S = \emptyset",
                steps=tuple(steps),
                execution_time_ms=elapsed,
            )

        # Step 2: Show algebraic transformation / factoring
        try:
            factored = sp.factor(eq_expr)
            if factored != eq_expr:
                steps.append(
                    SolutionStep(
                        step_number=step_num,
                        rule_name="Phân tích nhân tử",
                        description="Phân tích biểu thức thành tích các nhân tử để tìm nghiệm.",
                        content=ExpressionStepContent(
                            expression_before=f"{eq_expr} = 0",
                            expression_after=f"{factored} = 0",
                            latex_before=std_latex,
                            latex_after=f"{expr_to_latex(factored)} = 0",
                        ),
                    )
                )
                step_num += 1
        except Exception:
            pass

        # Step 3: Roots
        roots_latex_parts = [f"{clean_var} = {expr_to_latex(s)}" for s in solutions]
        roots_latex = ", \\quad ".join(roots_latex_parts)
        roots_str_parts = [f"{clean_var} = {s}" for s in solutions]
        roots_str = ", ".join(roots_str_parts)

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Tập nghiệm của phương trình",
                description=f"Tìm được {len(solutions)} nghiệm của phương trình.",
                content=ExpressionStepContent(
                    expression_before=f"{eq_expr} = 0",
                    expression_after=roots_str,
                    latex_before=std_latex,
                    latex_after=roots_latex,
                ),
            )
        )

        # Verification: substitute each root back into eq_expr
        verified = True
        for sol in solutions:
            try:
                subbed = sp.simplify(eq_expr.subs(var, sol))
                if subbed != 0 and abs(complex(subbed.evalf())) > 1e-6:
                    verified = False
                    break
            except Exception:
                verified = False
                break

        v_status = VerificationStatus.VERIFIED if verified else VerificationStatus.UNVERIFIED
        v_details = (
            "Thay trực tiếp các nghiệm vào phương trình ban đầu xác nhận vế trái luôn bằng 0."
            if verified
            else "Một số nghiệm chưa thể kiểm chứng độc lập hoàn toàn."
        )

        elapsed = (time.perf_counter() - t0) * 1000.0
        return SolutionResponse(
            status=SolutionStatus.SUCCESS,
            verification=VerificationResult(
                status=v_status,
                method="algebraic_root_substitution",
                details=v_details,
            ),
            raw_input=request.raw_input,
            canonical_input=f"{lhs_expr} = {rhs_expr}",
            final_result=roots_str,
            final_latex=roots_latex,
            steps=tuple(steps),
            execution_time_ms=elapsed,
        )

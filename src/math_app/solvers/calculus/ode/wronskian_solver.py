"""Wronskian Determinant and Linear Independence Solver for Second-Order ODEs."""

from __future__ import annotations

import time
import sympy as sp

from math_app.application.dtos import (
    ProblemRequest,
    SolutionResponse,
    SolutionStep,
)
from math_app.application.ports.solver import Solver
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.domain.step_content import ExpressionStepContent
from math_app.input.ode_parser import parse_wronskian_input
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.verification.calculus.ode_verifier import ODEVerifier


class WronskianSolver(Solver):
    """Solver for computing the Wronskian determinant W(y1, y2) and analyzing linear independence:

    W(y1, y2) = det([[y1, y2], [y1', y2']]) = y1*y2' - y1'*y2.
    """

    def __init__(self, verifier: ODEVerifier | None = None) -> None:
        self.verifier = verifier or ODEVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type in (
            ProblemType.WRONSKIAN,
            ProblemType.SOLVE_EQUATION,
        )

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        t0_start = time.perf_counter()
        raw = request.raw_input.strip()
        if not raw and not request.parameters:
            raise InvalidInputError("Dữ liệu đầu vào không được để trống (Input cannot be empty).")

        y1, y2, var = parse_wronskian_input(
            raw,
            target_variable=request.target_variable,
            parameters=dict(request.parameters),
        )

        steps: list[SolutionStep] = []
        step_num = 1

        # Step 1: Definition of functions
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Hệ nghiệm cơ bản",
                title="Xác định hai hàm số y1 và y2",
                description=(
                    f"Xét hai hàm số cần kiểm tra độc lập tuyến tính: "
                    f"$y_1({var}) = {expr_to_latex(y1)}$ và $y_2({var}) = {expr_to_latex(y2)}$."
                ),
                content=ExpressionStepContent(
                    expression_before="y1, y2",
                    expression_after=f"y1 = {y1}, y2 = {y2}",
                    latex_before="y_1, y_2",
                    latex_after=f"y_1({var}) = {expr_to_latex(y1)}, \\quad y_2({var}) = {expr_to_latex(y2)}",
                ),
                equation_latex=f"y_1({var}) = {expr_to_latex(y1)}, \\quad y_2({var}) = {expr_to_latex(y2)}",
            )
        )
        step_num += 1

        # Step 2: First-order derivatives
        dy1 = sp.diff(y1, var)
        dy2 = sp.diff(y2, var)

        deriv_latex = f"y_1'({var}) = {expr_to_latex(dy1)}, \\quad y_2'({var}) = {expr_to_latex(dy2)}"
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Đạo hàm cấp một và cấp hai",
                title="Tính đạo hàm cấp một của từng hàm số",
                description=(
                    f"Tính đạo hàm cấp một theo biến ${var}$: "
                    f"$y_1'({var}) = {expr_to_latex(dy1)}$ và $y_2'({var}) = {expr_to_latex(dy2)}$."
                ),
                content=ExpressionStepContent(
                    expression_before=f"y1 = {y1}, y2 = {y2}",
                    expression_after=f"y1' = {dy1}, y2' = {dy2}",
                    latex_before=f"y_1({var}) = {expr_to_latex(y1)}, \\quad y_2({var}) = {expr_to_latex(y2)}",
                    latex_after=deriv_latex,
                ),
                equation_latex=deriv_latex,
            )
        )
        step_num += 1

        # Step 3: Wronskian Matrix & Determinant Formula
        w_raw = y1 * dy2 - dy1 * y2
        w_simp = sp.simplify(w_raw)
        if w_simp != 0:
            w_simp = sp.simplify(sp.trigsimp(w_simp))

        w_matrix_latex = (
            f"W(y_1, y_2)({var}) = \\begin{{vmatrix}} y_1 & y_2 \\\\ y_1' & y_2' \\end{{vmatrix}} "
            f"= y_1 y_2' - y_1' y_2 = ({expr_to_latex(y1)})({expr_to_latex(dy2)}) - ({expr_to_latex(dy1)})({expr_to_latex(y2)})"
        )
        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Định thức Wronskian",
                title="Lập định thức Wronskian cấp hai",
                description=(
                    "Định thức Wronskian của hai hàm khả vi được xác định bởi: "
                    "$W(y_1, y_2) = y_1 y_2' - y_1' y_2$."
                ),
                content=ExpressionStepContent(
                    expression_before="W = y1*y2' - y1'*y2",
                    expression_after=f"W = ({y1})*({dy2}) - ({dy1})*({y2})",
                    latex_before="W(y_1, y_2) = y_1 y_2' - y_1' y_2",
                    latex_after=w_matrix_latex,
                ),
                equation_latex=w_matrix_latex,
            )
        )
        step_num += 1

        # Step 4: Simplification and Independence Analysis
        is_identically_zero = bool(w_simp == 0)
        domain_restrictions: list[str] = []
        warnings: list[str] = []

        if is_identically_zero:
            conclusion_text = (
                f"Định thức Wronskian $W(y_1, y_2)({var}) \\equiv 0$ trên toàn miền xác định. "
                "Theo lý thuyết giải tích phương trình vi phân, đối với hai hàm khả vi bất kỳ, "
                "điều kiện $W \\equiv 0$ chưa đủ để kết luận phụ thuộc tuyến tính (ví dụ phản chứng Peano "
                "$t^2$ và $t|t|$ có Wronskian triệt tiêu trên $\\mathbb{R}$ nhưng độc lập tuyến tính). "
                "Cần xác định phương trình vi phân liên kết có hệ số liên tục để áp dụng định lý Abel. "
                "Kết luận: Chưa đủ điều kiện kết luận (Inconclusive / Unverified)."
            )
            independence_latex = f"W(y_1, y_2)({var}) \\equiv 0"
            warnings.append(
                "Định thức Wronskian đồng nhất bằng 0. Đối với hai hàm khả vi bất kỳ, W(y1, y2) ≡ 0 không đảm bảo tính phụ thuộc tuyến tính "
                "nếu chưa kiểm chứng chúng là nghiệm của cùng một phương trình vi phân tuyến tính cấp 2 thuần nhất có hệ số liên tục "
                "(Wronskian identically zero is inconclusive for arbitrary functions)."
            )
        else:
            conclusion_text = (
                f"Định thức Wronskian rút gọn được: $W(y_1, y_2)({var}) = {expr_to_latex(w_simp)}$. "
                f"Vì $W(y_1, y_2) \\ne 0$ tại ít nhất một điểm trên miền xác định, theo định lý Wronski, "
                f"hai hàm số $y_1$ và $y_2$ độc lập tuyến tính (Linearly independent)."
            )
            independence_latex = f"W(y_1, y_2)({var}) = {expr_to_latex(w_simp)} \\not\\equiv 0"

        # Check for isolated zeros or singularities
        if not is_identically_zero:
            if var in w_simp.free_symbols:
                domain_restrictions.append(f"Wronskian phụ thuộc {var}: W({var}) = {w_simp}. Độc lập tuyến tính trên các khoảng mà W({var}) != 0.")

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Định thức Wronski",
                title="Rút gọn Wronskian và kết luận độc lập tuyến tính",
                description=conclusion_text,
                content=ExpressionStepContent(
                    expression_before=f"W = ({y1})*({dy2}) - ({dy1})*({y2})",
                    expression_after=f"W = {w_simp}",
                    latex_before="W(y_1, y_2) = y_1 y_2' - y_1' y_2",
                    latex_after=independence_latex,
                ),
                equation_latex=independence_latex,
            )
        )
        step_num += 1

        # Verification
        _, verif_result = self.verifier.verify_wronskian(y1, y2, var)

        steps.append(
            SolutionStep(
                step_number=step_num,
                rule_name="Kiểm chứng nghiệm",
                title="Kiểm chứng toán học độc lập",
                description=verif_result.details,
                content=ExpressionStepContent(
                    expression_before=f"W({var}) = {w_simp}",
                    expression_after="Verified" if verif_result.status == VerificationStatus.VERIFIED else "Inconclusive",
                    latex_before=f"W(y_1, y_2) = {expr_to_latex(w_simp)}",
                    latex_after=f"W(y_1, y_2) = {expr_to_latex(w_simp)}" + (" \\not\\equiv 0" if not is_identically_zero else " \\equiv 0"),
                ),
                notes=verif_result.details,
            )
        )

        status = SolutionStatus.SUCCESS if verif_result.status == VerificationStatus.VERIFIED else SolutionStatus.UNVERIFIED
        elapsed = (time.perf_counter() - t0_start) * 1000.0

        return SolutionResponse(
            status=status,
            verification=verif_result,
            raw_input=request.raw_input,
            canonical_input=f"W({y1}, {y2})",
            final_result=f"W(y1, y2)({var}) = {w_simp}",
            final_latex=f"W(y_1, y_2)({var}) = {expr_to_latex(w_simp)}",
            steps=tuple(steps),
            domain_restrictions=tuple(domain_restrictions),
            warnings=tuple(warnings),
            execution_time_ms=elapsed,
        )

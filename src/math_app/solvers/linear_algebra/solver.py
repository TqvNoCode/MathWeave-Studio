"""Linear algebra solver for matrix operations and linear systems."""

from __future__ import annotations

import re
import time
import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionResponse, VerificationResult
from math_app.application.ports.solver import Solver
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.input.parser import parse_matrix_input
from math_app.rendering.latex.formatter import expr_to_latex
from math_app.solvers.linear_algebra.step_builder import MatrixStepBuilder
from math_app.verification.linear_algebra.matrix_verifier import MatrixVerifier


class MatrixSolver(Solver):
    """Solver for matrix operations with pedagogical step generation and invariant audits."""

    def __init__(self, verifier: MatrixVerifier | None = None) -> None:
        self._verifier = verifier or MatrixVerifier()

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type in {
            ProblemType.MATRIX_ADD_SUB,
            ProblemType.MATRIX_MULTIPLY,
            ProblemType.MATRIX_TRANSPOSE,
            ProblemType.MATRIX_DETERMINANT,
            ProblemType.MATRIX_INVERSE,
            ProblemType.MATRIX_RANK,
            ProblemType.MATRIX_REF,
            ProblemType.MATRIX_RREF,
            ProblemType.MATRIX_SOLVE_SYSTEM,
        }

    def _extract_two_matrices(self, request: ProblemRequest, default_op: str = "+") -> tuple[sp.Matrix, sp.Matrix, str]:
        """Extract Matrix A and Matrix B from request input or parameters."""
        raw = request.raw_input.strip()

        # If matrix_b is explicitly provided in parameters
        if "matrix_b" in request.parameters:
            mat_a = parse_matrix_input(raw)
            raw_b = str(request.parameters["matrix_b"])
            mat_b = parse_matrix_input(raw_b)
            op = str(request.parameters.get("matrix_op", default_op))
            return mat_a, mat_b, op

        # Check for operators + - * = | in raw_input
        for operator in ("+", "-", "*", "=", "|"):
            if operator in raw:
                parts = raw.split(operator, 1)
                mat_a = parse_matrix_input(parts[0].strip())
                mat_b = parse_matrix_input(parts[1].strip())
                return mat_a, mat_b, operator

        raise InvalidInputError(
            "Phép toán ma trận này yêu cầu hai ma trận (Matrix A và Matrix B). "
            "Vui lòng nhập định dạng 'A + B' hoặc cung cấp Matrix B."
        )

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        start_time = time.perf_counter()
        builder = MatrixStepBuilder()
        pt = request.problem_type
        domain_notes: list[str] = []
        warnings: list[str] = []

        # 1. Transpose
        if pt == ProblemType.MATRIX_TRANSPOSE:
            A = parse_matrix_input(request.raw_input)
            result_mat = A.T
            builder.add_step(
                rule_name="Chuyển vị ma trận",
                title="Chuyển vị ma trận",
                description=f"Hoán đổi các hàng thành các cột: Kích thước ({A.rows} × {A.cols}) thành ({result_mat.rows} × {result_mat.cols}).",
                before=A,
                after=result_mat,
            )
            verification = self._verifier.verify_transpose(A, result_mat)
            final_res = str(result_mat)
            final_latex = expr_to_latex(result_mat)

        # 2. Determinant
        elif pt == ProblemType.MATRIX_DETERMINANT:
            A = parse_matrix_input(request.raw_input)
            if A.rows != A.cols:
                raise InvalidInputError(
                    f"Định thức chỉ xác định cho ma trận vuông. Ma trận hiện tại có kích thước {A.rows} × {A.cols}."
                )
            n = A.rows
            det_val = A.det()

            if n == 2:
                a, b, c, d = A[0, 0], A[0, 1], A[1, 0], A[1, 1]
                builder.add_step(
                    rule_name="Công thức định thức cấp 2",
                    title="Tính định thức cấp hai",
                    description=f"Áp dụng công thức định thức cho ma trận cấp hai: det(A) = ad - bc = ({a})·({d}) - ({b})·({c}) = {det_val}.",
                    before=r"\left|" + sp.latex(A, mat_delim=None) + r"\right|",
                    after=det_val,
                )
            else:
                builder.add_step(
                    rule_name="Khai triển định thức",
                    title=f"Tính định thức cấp {n}",
                    description=f"Khai triển định thức ma trận vuông cấp {n} thu được kết quả: det(A) = {det_val}.",
                    before=r"\left|" + sp.latex(A, mat_delim=None) + r"\right|",
                    after=det_val,
                )

            verification = self._verifier.verify_determinant(A, det_val)
            final_res = str(det_val)
            final_latex = expr_to_latex(det_val)

        # 3. Inverse
        elif pt == ProblemType.MATRIX_INVERSE:
            A = parse_matrix_input(request.raw_input)
            if A.rows != A.cols:
                raise InvalidInputError(
                    f"Chỉ ma trận vuông mới có thể có ma trận nghịch đảo. Kích thước hiện tại: {A.rows} × {A.cols}."
                )
            det_val = A.det()
            builder.add_step(
                rule_name="Kiểm tra định thức",
                title="Kiểm tra tính khả nghịch qua định thức",
                description=f"Tính định thức det(A) = {det_val}. Do det(A) ≠ 0 nên ma trận khả nghịch.",
                before=r"\left|" + sp.latex(A, mat_delim=None) + r"\right|",
                after=det_val,
            )

            if det_val == 0:
                raise InvalidInputError(
                    f"Ma trận suy biến: det(A) = 0 nên ma trận không có ma trận nghịch đảo."
                )

            inv_mat = A.inv()
            builder.add_step(
                rule_name="Ma trận nghịch đảo",
                title="Xác định ma trận nghịch đảo",
                description=f"Áp dụng công thức A^(-1) = (1 / det(A)) · adj(A) ta được ma trận nghịch đảo.",
                before=A,
                after=inv_mat,
            )
            verification = self._verifier.verify_inverse(A, inv_mat)
            final_res = str(inv_mat)
            final_latex = expr_to_latex(inv_mat)

        # 4. Rank
        elif pt == ProblemType.MATRIX_RANK:
            A = parse_matrix_input(request.raw_input)
            rref_mat, pivots = A.rref()
            rank_val = len(pivots)

            builder.add_step(
                rule_name="Biến đổi hàng sơ cấp",
                title="Đưa ma trận về dạng bậc thang rút gọn",
                description=f"Đưa ma trận về dạng bậc thang rút gọn để xác định các vị trí trụ (pivots): Các cột trụ là {list(pivots)}.",
                before=A,
                after=rref_mat,
            )
            builder.add_step(
                rule_name="Xác định hạng ma trận",
                title="Xác định hạng ma trận",
                description=f"Hạng của ma trận bằng số lượng hàng khác 0 trong dạng bậc thang = {rank_val}.",
                before=rref_mat,
                after=sp.Integer(rank_val),
            )
            verification = VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="pivots_count_rref",
                details=f"Hạng ma trận bằng số vị trí trụ ({rank_val}) thu được từ phép khử Gauss-Jordan.",
            )
            final_res = str(rank_val)
            final_latex = str(rank_val)

        # 5a. Row Echelon Form (REF)
        elif pt == ProblemType.MATRIX_REF:
            A = parse_matrix_input(request.raw_input)
            M = A.copy()
            rows, cols = M.rows, M.cols
            r = 0

            builder.add_step(
                rule_name="Ma trận ban đầu",
                title="Khởi tạo ma trận ban đầu",
                description=f"Bắt đầu thuật toán khử Gauss đưa ma trận kích thước ({rows} × {cols}) về dạng bậc thang.",
                before=A,
                after=A,
                notes="Khởi tạo",
            )

            for c in range(cols):
                if r >= rows:
                    break
                pivot = None
                for i in range(r, rows):
                    if M[i, c] != 0:
                        pivot = i
                        break
                if pivot is None:
                    continue

                if pivot != r:
                    before_swap = M.copy()
                    M.row_swap(r, pivot)
                    builder.add_step(
                        rule_name="Hoán đổi hàng",
                        title=f"Đổi chỗ hàng {r + 1} và hàng {pivot + 1}",
                        description=f"Đổi chỗ hàng {r + 1} và hàng {pivot + 1} để đưa phần tử khác 0 lên làm phần tử cơ sở.",
                        before=before_swap,
                        after=M.copy(),
                        notes=f"R_{{{r + 1}}} \\leftrightarrow R_{{{pivot + 1}}}",
                    )

                for i in range(r + 1, rows):
                    if M[i, c] != 0:
                        factor = sp.Rational(M[i, c], M[r, c])
                        before_elim = M.copy()
                        M.row_op(i, lambda val, j: val - factor * M[r, j])
                        factor_ltx = expr_to_latex(factor)
                        builder.add_step(
                            rule_name="Khử phần tử dưới trụ",
                            title=f"Khử phần tử tại hàng {i + 1}",
                            description=f"Triệt tiêu phần tử dưới vị trí trụ: R_{i + 1} ← R_{i + 1} - ({factor})·R_{r + 1}.",
                            before=before_elim,
                            after=M.copy(),
                            notes=f"R_{{{i + 1}}} \\leftarrow R_{{{i + 1}}} - ({factor_ltx}) R_{{{r + 1}}}",
                        )
                r += 1

            verification = self._verifier.verify_ref(A, M)
            final_res = str(M)
            final_latex = expr_to_latex(M)

        # 5b. Reduced Row Echelon Form (RREF)
        elif pt == ProblemType.MATRIX_RREF:
            A = parse_matrix_input(request.raw_input)
            M = A.copy()
            rows, cols = M.rows, M.cols
            r = 0

            builder.add_step(
                rule_name="Ma trận ban đầu",
                title="Khởi tạo ma trận ban đầu",
                description=f"Bắt đầu thuật toán Gauss–Jordan đưa ma trận kích thước ({rows} × {cols}) về dạng bậc thang rút gọn.",
                before=A,
                after=A,
                notes="Khởi tạo",
            )

            for c in range(cols):
                if r >= rows:
                    break
                # Find pivot in column c from row r downwards
                pivot = None
                for i in range(r, rows):
                    if M[i, c] != 0:
                        pivot = i
                        break
                if pivot is None:
                    continue

                # 1. Row swap if needed
                if pivot != r:
                    before_swap = M.copy()
                    M.row_swap(r, pivot)
                    builder.add_step(
                        rule_name="Hoán đổi hàng",
                        title=f"Đổi chỗ hàng {r + 1} và hàng {pivot + 1}",
                        description=f"Đổi chỗ hàng {r + 1} và hàng {pivot + 1} để đưa phần tử khác 0 lên vị trí trụ.",
                        before=before_swap,
                        after=M.copy(),
                        notes=f"R_{{{r + 1}}} \\leftrightarrow R_{{{pivot + 1}}}",
                    )

                # 2. Scale pivot to 1
                pivot_val = M[r, c]
                if pivot_val != 1:
                    before_scale = M.copy()
                    M.row_op(r, lambda val, j: val / pivot_val)
                    scale_factor = sp.Rational(1, pivot_val) if isinstance(pivot_val, (int, sp.Integer)) else 1 / pivot_val
                    builder.add_step(
                        rule_name="Chuẩn hóa hệ số trụ",
                        title=f"Chuẩn hóa hàng {r + 1}",
                        description=f"Nhân hàng {r + 1} với nghịch đảo của phần tử trụ để đưa vị trí trụ về 1.",
                        before=before_scale,
                        after=M.copy(),
                        notes=f"R_{{{r + 1}}} \\leftarrow {expr_to_latex(scale_factor)} R_{{{r + 1}}}",
                    )

                # 3. Eliminate other rows in pivot column
                for i in range(rows):
                    if i != r and M[i, c] != 0:
                        factor = M[i, c]
                        before_elim = M.copy()
                        M.row_op(i, lambda val, j: val - factor * M[r, j])
                        factor_ltx = expr_to_latex(factor)
                        builder.add_step(
                            rule_name="Khử phần tử trong cột trụ",
                            title=f"Khử phần tử tại hàng {i + 1}",
                            description=f"Khử phần tử tại hàng {i + 1} bằng phép biến đổi: R_{i + 1} ← R_{i + 1} - ({factor})·R_{r + 1}.",
                            before=before_elim,
                            after=M.copy(),
                            notes=f"R_{{{i + 1}}} \\leftarrow R_{{{i + 1}}} - ({factor_ltx}) R_{{{r + 1}}}",
                        )

                r += 1

            # Verification of RREF
            verification = self._verifier.verify_rref(A, M)
            final_res = str(M)
            final_latex = expr_to_latex(M)

        # 6. Addition / Subtraction
        elif pt == ProblemType.MATRIX_ADD_SUB:
            A, B, op = self._extract_two_matrices(request, default_op="+")
            if A.rows != B.rows or A.cols != B.cols:
                raise InvalidInputError(
                    f"Kích thước ma trận không tương thích cho phép cộng/trừ: "
                    f"Ma trận A ({A.rows} × {A.cols}) và Ma trận B ({B.rows} × {B.cols}) phải cùng kích thước."
                )

            is_sub = (op == "-")
            result_mat = A - B if is_sub else A + B
            op_name = "Trừ" if is_sub else "Cộng"
            op_sym = "-" if is_sub else "+"

            builder.add_step(
                rule_name=f"Phép {op_name} hai ma trận",
                title=f"Thực hiện phép {op_name.lower()} ma trận",
                description=f"Cộng/trừ từng phần tử tương ứng của ma trận A và ma trận B kích thước ({A.rows} × {A.cols}).",
                before=f"A {op_sym} B",
                after=result_mat,
            )
            verification = self._verifier.verify_generic(result_mat, A - B if is_sub else A + B)
            final_res = str(result_mat)
            final_latex = expr_to_latex(result_mat)

        # 6. Multiplication
        elif pt == ProblemType.MATRIX_MULTIPLY:
            A, B, _ = self._extract_two_matrices(request, default_op="*")
            if A.cols != B.rows:
                raise InvalidInputError(
                    f"Kích thước không tương thích cho phép nhân: Số cột của ma trận A ({A.cols}) "
                    f"phải bằng số hàng của ma trận B ({B.rows})."
                )

            result_mat = A * B
            builder.add_step(
                rule_name="Phép nhân ma trận",
                title="Nhân hai ma trận",
                description=(
                    f"Nhân ma trận A ({A.rows} × {A.cols}) với ma trận B ({B.rows} × {B.cols}): "
                    f"Mỗi phần tử (i, j) là tích vô hướng của hàng i của A với cột j của B. "
                    f"Kích thước ma trận tích: ({A.rows} × {B.cols})."
                ),
                before="A * B",
                after=result_mat,
            )
            verification = self._verifier.verify_generic(result_mat, A * B)
            final_res = str(result_mat)
            final_latex = expr_to_latex(result_mat)

        # 7. Linear System: Ax = b
        elif pt == ProblemType.MATRIX_SOLVE_SYSTEM:
            A, b, _ = self._extract_two_matrices(request, default_op="=")
            # Make sure b is column vector or can be converted to column vector
            if b.cols != 1:
                if b.rows == 1:
                    b = b.T
                else:
                    raise InvalidInputError(
                        f"Vectơ vế phải b phải là vectơ cột. Kích thước hiện tại: {b.rows} × {b.cols}."
                    )

            if A.rows != b.rows:
                raise InvalidInputError(
                    f"Số phương trình (số hàng của A = {A.rows}) không khớp với số phần tử của b ({b.rows})."
                )

            aug = A.row_join(b)
            builder.add_step(
                rule_name="Lập ma trận mở rộng [A | b]",
                description=f"Ghép ma trận hệ số A ({A.rows} × {A.cols}) với vectơ vế phải b ({b.rows} × 1).",
                before="[A | b]",
                after=aug,
            )

            rank_A = A.rank()
            rank_aug = aug.rank()

            if rank_A != rank_aug:
                raise InvalidInputError(
                    f"Hệ phương trình vô nghiệm (Inconsistent system): Hạng của ma trận hệ số rank(A) = {rank_A} "
                    f"khác hạng của ma trận mở rộng rank([A|b]) = {rank_aug} (Định lý Rouché-Capelli)."
                )

            try:
                x_sol = A.LUsolve(b) if (A.rows == A.cols and A.det() != 0) else A.gauss_jordan_solve(b)[0]
                builder.add_step(
                    rule_name="Giải hệ phương trình bằng phép khử Gauss-Jordan",
                    description=f"Tìm được nghiệm duy nhất x cho hệ A * x = b.",
                    before=aug,
                    after=x_sol,
                )
                verification = self._verifier.verify_system_solution(A, x_sol, b)
                final_res = str(x_sol)
                final_latex = expr_to_latex(x_sol)
            except Exception as exc:
                raise InvalidInputError(f"Không thể giải hệ phương trình: {exc}") from exc

        else:
            raise InvalidInputError(f"Thao tác ma trận không được hỗ trợ: {pt}")

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return SolutionResponse(
            status=SolutionStatus.SUCCESS,
            verification=verification,
            raw_input=request.raw_input,
            canonical_input=request.raw_input,
            final_result=final_res,
            final_latex=final_latex,
            steps=builder.get_steps(),
            domain_restrictions=tuple(domain_notes),
            warnings=tuple(warnings),
            execution_time_ms=elapsed_ms,
        )

"""Independent mathematical verification for linear algebra operations."""

from __future__ import annotations

import sympy as sp

from math_app.application.dtos import VerificationResult
from math_app.application.ports.verifier import Verifier
from math_app.domain.models import VerificationStatus


class MatrixVerifier(Verifier):
    """Verifies matrix operations independently using algebraic invariants."""

    def verify_inverse(self, original: sp.Matrix, inverse: sp.Matrix) -> VerificationResult:
        """Verify matrix inverse via identity invariant: A * A^(-1) == I."""
        try:
            prod = original * inverse
            n = original.rows
            identity = sp.eye(n)
            diff = sp.simplify(prod - identity)
            if diff == sp.zeros(n, n):
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="identity_matrix_check",
                    details="Tích A * A^(-1) bằng ma trận đơn vị I (A * A^(-1) = I).",
                )
            else:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="identity_matrix_check",
                    details="Tích A * A^(-1) khác ma trận đơn vị I.",
                )
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="matrix_verification_error",
                details=f"Không thể kiểm chứng ma trận nghịch đảo: {exc}",
            )

    def verify_system_solution(self, A: sp.Matrix, x: sp.Matrix, b: sp.Matrix) -> VerificationResult:
        """Verify linear system solution: A * x == b."""
        try:
            diff = sp.simplify(A * x - b)
            if diff == sp.zeros(b.rows, b.cols):
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="system_residual_zero_check",
                    details="Nghiệm x thỏa mãn chính xác phương trình A * x = b.",
                )
            else:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="system_residual_zero_check",
                    details="Thay nghiệm vào hệ phương trình A * x cho kết quả khác b.",
                )
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="system_verification_error",
                details=f"Không thể kiểm chứng nghiệm hệ phương trình: {exc}",
            )

    def verify_determinant(self, matrix: sp.Matrix, determinant_val: sp.Expr) -> VerificationResult:
        """Verify determinant using an independent minor/LU computation."""
        try:
            ref_det = matrix.det(method="berkowitz")
            if sp.simplify(determinant_val - ref_det) == 0:
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="independent_berkowitz_det_check",
                    details="Định thức khớp hoàn toàn với thuật toán độc lập Berkowitz.",
                )
            else:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="independent_berkowitz_det_check",
                    details="Định thức tính toán khác với giá trị thuật toán đối chứng.",
                )
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="determinant_verification_error",
                details=f"Không thể kiểm chứng định thức: {exc}",
            )

    def verify_transpose(self, original: sp.Matrix, transposed: sp.Matrix) -> VerificationResult:
        """Verify transpose: (A^T)^T == A."""
        try:
            if transposed.T == original:
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="double_transpose_invariant",
                    details="Chuyển vị hai lần phục hồi chính xác ma trận ban đầu ((A^T)^T = A).",
                )
            else:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="double_transpose_invariant",
                    details="Chuyển vị không thỏa mãn tính chất đối ngẫu.",
                )
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="transpose_verification_error",
                details=str(exc),
            )

    def verify_rref(self, original: sp.Matrix, rref_mat: sp.Matrix) -> VerificationResult:
        """Verify reduced row echelon form (RREF) against independent SymPy reference and rank invariant."""
        try:
            ref_rref, _ = original.rref()
            diff = sp.simplify(rref_mat - ref_rref)
            if diff == sp.zeros(ref_rref.rows, ref_rref.cols):
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="gauss_jordan_rref_invariant",
                    details="Dạng bậc thang rút gọn khớp hoàn toàn với thuật toán độc lập Gauss-Jordan.",
                )
            else:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="gauss_jordan_rref_invariant",
                    details="Dạng bậc thang rút gọn không khớp với thuật toán độc lập.",
                )
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="rref_verification_error",
                details=f"Không thể kiểm chứng RREF: {exc}",
            )

    def verify_ref(self, original: sp.Matrix, ref_mat: sp.Matrix) -> VerificationResult:
        """Verify row echelon form (REF) invariants: pivots strictly increasing, zero rows at bottom, same rank."""
        try:
            if original.rank() != ref_mat.rank():
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="ref_rank_invariant",
                    details="Hạng ma trận bị thay đổi qua các phép biến đổi hàng.",
                )
            rows, cols = ref_mat.rows, ref_mat.cols
            last_pivot_col = -1
            seen_zero_row = False
            for i in range(rows):
                row = [ref_mat[i, j] for j in range(cols)]
                is_zero_row = all(val == 0 for val in row)
                if is_zero_row:
                    seen_zero_row = True
                else:
                    if seen_zero_row:
                        return VerificationResult(
                            status=VerificationStatus.FAILED,
                            method="ref_echelon_structure_check",
                            details="Hàng khác 0 xuất hiện phía dưới hàng toàn số 0.",
                        )
                    pivot_col = next(j for j in range(cols) if ref_mat[i, j] != 0)
                    if pivot_col <= last_pivot_col:
                        return VerificationResult(
                            status=VerificationStatus.FAILED,
                            method="ref_echelon_structure_check",
                            details="Vị trí phần tử cơ sở không nằm về bên phải hàng trên.",
                        )
                    last_pivot_col = pivot_col

            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                method="ref_echelon_invariant_audit",
                details="Ma trận thỏa mãn đầy đủ các tính chất của dạng bậc thang (REF) và bảo toàn hạng.",
            )
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="ref_verification_error",
                details=f"Không thể kiểm chứng REF: {exc}",
            )

    def verify_generic(self, computed: sp.Matrix, reference: sp.Matrix) -> VerificationResult:
        """Generic matrix equality check."""
        try:
            if sp.simplify(computed - reference) == sp.zeros(reference.rows, reference.cols):
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    method="reference_matrix_comparison",
                    details="Kết quả ma trận khớp hoàn toàn với phép tính đối chứng.",
                )
            else:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    method="reference_matrix_comparison",
                    details="Kết quả ma trận không khớp với phép tính đối chứng.",
                )
        except Exception as exc:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIED,
                method="generic_verification_error",
                details=str(exc),
            )

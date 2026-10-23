"""Unit tests for linear algebra matrix solver and invariant verifier."""

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.linear_algebra.solver import MatrixSolver


def test_matrix_transpose():
    solver = MatrixSolver()
    req = ProblemRequest("[[1, 2, 3], [4, 5, 6]]", ProblemType.MATRIX_TRANSPOSE)
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "Matrix([[1, 4], [2, 5], [3, 6]])" in res.final_result


def test_matrix_determinant_2x2():
    solver = MatrixSolver()
    req = ProblemRequest("[[1, 2], [3, 4]]", ProblemType.MATRIX_DETERMINANT)
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.final_result == "-2"


def test_matrix_determinant_non_square_fails():
    solver = MatrixSolver()
    req = ProblemRequest("[[1, 2, 3], [4, 5, 6]]", ProblemType.MATRIX_DETERMINANT)
    with pytest.raises(InvalidInputError):
        solver.solve(req)


def test_matrix_inverse_invertible():
    solver = MatrixSolver()
    req = ProblemRequest("[[1, 2], [3, 4]]", ProblemType.MATRIX_INVERSE)
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Invariant: A * A^(-1) == I
    A = sp.Matrix([[1, 2], [3, 4]])
    inv = sp.sympify(res.final_result)
    assert A * inv == sp.eye(2)


def test_matrix_inverse_singular_fails():
    solver = MatrixSolver()
    req = ProblemRequest("[[1, 2], [2, 4]]", ProblemType.MATRIX_INVERSE)
    with pytest.raises(InvalidInputError, match="suy biến|Singular"):
        solver.solve(req)


def test_matrix_rank():
    solver = MatrixSolver()
    req = ProblemRequest("[[1, 2, 3], [2, 4, 6], [1, 1, 1]]", ProblemType.MATRIX_RANK)
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.final_result == "2"


def test_matrix_multiplication():
    solver = MatrixSolver()
    req = ProblemRequest("[[1, 2], [3, 4]] * [[5, 6], [7, 8]]", ProblemType.MATRIX_MULTIPLY)
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "Matrix([[19, 22], [43, 50]])" in res.final_result


def test_matrix_multiplication_dimension_mismatch():
    solver = MatrixSolver()
    req = ProblemRequest("[[1, 2]] * [[1, 2]]", ProblemType.MATRIX_MULTIPLY)
    with pytest.raises(InvalidInputError):
        solver.solve(req)


def test_matrix_solve_linear_system():
    solver = MatrixSolver()
    req = ProblemRequest("[[1, 2], [3, 4]] = [5, 11]", ProblemType.MATRIX_SOLVE_SYSTEM)
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Unique solution: x = 1, y = 2
    x_sol = sp.sympify(res.final_result)
    assert x_sol[0] == 1 and x_sol[1] == 2


def test_matrix_rref_computation():
    solver = MatrixSolver()
    req = ProblemRequest("[[1, 2, -1, -4], [2, 3, -1, -11], [-2, 0, -3, 22]]", ProblemType.MATRIX_RREF)
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # RREF must match sympy rref
    A = sp.Matrix([[1, 2, -1, -4], [2, 3, -1, -11], [-2, 0, -3, 22]])
    expected_rref, _ = A.rref()
    assert sp.sympify(res.final_result) == expected_rref
    assert len(res.steps) >= 1
    # Check that each step contains meaningful row operations
    assert any("Row Elimination" in s.rule_name or "Khử phần tử" in s.rule_name for s in res.steps)


def test_matrix_rref_zero_rows_and_dependent():
    solver = MatrixSolver()
    req = ProblemRequest("[[1, 2], [2, 4]]", ProblemType.MATRIX_RREF)
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert sp.sympify(res.final_result) == sp.Matrix([[1, 2], [0, 0]])


def test_matrix_ref_computation():
    """Verify Gaussian elimination to row echelon form (REF) with verifiable echelon structure."""
    solver = MatrixSolver()
    req = ProblemRequest("[[2, 1, -1], [-3, -1, 2], [-2, 1, 2]]", ProblemType.MATRIX_REF)
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.steps) >= 1
    # Check rank is preserved and entries below pivots are zero
    M = sp.sympify(res.final_result)
    assert M[1, 0] == 0
    assert M[2, 0] == 0
    assert M[2, 1] == 0
    assert M.rank() == 3


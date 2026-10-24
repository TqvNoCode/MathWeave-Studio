"""Unit tests for EquationSolver (SOLVE_EQUATION)."""

import pytest

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.algebra.equation_solver import EquationSolver


@pytest.fixture
def solver() -> EquationSolver:
    return EquationSolver()


def test_can_solve(solver: EquationSolver):
    assert solver.can_solve(ProblemRequest("x = 0", ProblemType.SOLVE_EQUATION))
    assert not solver.can_solve(ProblemRequest("x", ProblemType.DERIVATIVE))


def test_solve_linear_equation(solver: EquationSolver):
    req = ProblemRequest(raw_input="2*x + 4 = 0", problem_type=ProblemType.SOLVE_EQUATION, target_variable="x")
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "x = -2" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED
    assert len(res.steps) >= 2


def test_solve_quadratic_multiple_solutions(solver: EquationSolver):
    req = ProblemRequest(raw_input="x^2 - 5*x + 6 = 0", problem_type=ProblemType.SOLVE_EQUATION, target_variable="x")
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "2" in res.final_result and "3" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


def test_solve_implicit_zero_rhs(solver: EquationSolver):
    req = ProblemRequest(raw_input="3*x - 9", problem_type=ProblemType.SOLVE_EQUATION, target_variable="x")
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "x = 3" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


def test_solve_no_solution_inconsistent(solver: EquationSolver):
    req = ProblemRequest(raw_input="x + 1 = x", problem_type=ProblemType.SOLVE_EQUATION, target_variable="x")
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "Vô nghiệm" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.final_latex == r"S = \emptyset"


def test_solve_infinitely_many_solutions(solver: EquationSolver):
    req = ProblemRequest(raw_input="2*x = 2*x", problem_type=ProblemType.SOLVE_EQUATION, target_variable="x")
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "Vô số nghiệm" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED
    assert res.final_latex == r"S = \mathbb{R}"


def test_solve_malformed_inputs(solver: EquationSolver):
    # Empty
    with pytest.raises(InvalidInputError):
        solver.solve(ProblemRequest(raw_input="", problem_type=ProblemType.SOLVE_EQUATION))

    # Multiple '='
    with pytest.raises(InvalidInputError, match="đúng một dấu"):
        solver.solve(ProblemRequest(raw_input="x = 2 = 3", problem_type=ProblemType.SOLVE_EQUATION))

    # Empty side
    with pytest.raises(InvalidInputError, match="không được để trống"):
        solver.solve(ProblemRequest(raw_input="x =", problem_type=ProblemType.SOLVE_EQUATION))

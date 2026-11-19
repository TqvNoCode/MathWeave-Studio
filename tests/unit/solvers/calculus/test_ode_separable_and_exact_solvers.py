"""Unit tests for Phase C (Separable) and Phase D (Exact) ODE solvers."""

import pytest

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.exact_solver import ODEExactSolver
from math_app.solvers.calculus.ode.separable_solver import ODESeparableSolver


@pytest.fixture
def sep_solver() -> ODESeparableSolver:
    return ODESeparableSolver()


@pytest.fixture
def exact_solver() -> ODEExactSolver:
    return ODEExactSolver()


# =========================================================================
# Phase C — Separable ODEs
# =========================================================================

def test_separable_standard_solve(sep_solver: ODESeparableSolver):
    """Test y' = 2*t*y with general solution y(t) = exp(C + t^2)."""
    req = ProblemRequest(raw_input="y' = 2*t*y", problem_type=ProblemType.ODE_SEPARABLE, target_variable="t")
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "t**2" in res.final_result or "t^2" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED
    # Should identify equilibrium solution y = 0
    step_titles = [s.title for s in res.steps]
    assert any("cân bằng" in t.lower() for t in step_titles)
    assert any("phân tách biến số" in s.rule_name.lower() for s in res.steps)


def test_separable_with_initial_condition(sep_solver: ODESeparableSolver):
    """Test y' = 2*t*y with y(0) = 5 => y(t) = 5*exp(t^2)."""
    req = ProblemRequest(
        raw_input="y' = 2*t*y, y(0) = 5",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="t",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "5*exp(t**2)" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


def test_separable_preserves_multiple_equilibrium_solutions(sep_solver: ODESeparableSolver):
    """Test y' = t*(y^2 - 1) preserves equilibrium solutions y = -1 and y = 1."""
    req = ProblemRequest(
        raw_input="y' = t*(y^2 - 1)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="t",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    eq_step = next(s for s in res.steps if "cân bằng" in s.title.lower())
    assert "-1" in eq_step.content.expression_after and "1" in eq_step.content.expression_after


def test_separable_initial_condition_hitting_equilibrium(sep_solver: ODESeparableSolver):
    """If initial condition is y(0) = 1 for y' = t*(y^2 - 1), the unique solution is constant y(t) = 1."""
    req = ProblemRequest(
        raw_input="y' = t*(y^2 - 1), y(0) = 1",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="t",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "y(t) = 1" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


def test_separable_section8_example(sep_solver: ODESeparableSolver):
    """Test Section 8 example: dy/dx = x^2 / (1 - y^2) => y - y^3/3 = x^3/3 + C."""
    req = ProblemRequest(
        raw_input="dy/dx = x^2 / (1 - y^2)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    # Final result is implicit relation
    assert "y**3/3" in res.final_result or "y^3/3" in res.final_latex
    assert "x**3/3" in res.final_result or "x^3/3" in res.final_latex
    assert res.verification.status == VerificationStatus.VERIFIED
    # Denominator restrictions: y != 1 and y != -1
    assert any("1" in r for r in res.domain_restrictions)


def test_separable_rejects_non_separable_equation(sep_solver: ODESeparableSolver):
    """Test that non-separable equation y' = t + y reports CANNOT_SOLVE."""
    req = ProblemRequest(raw_input="y' = t + y", problem_type=ProblemType.ODE_SEPARABLE, target_variable="t")
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert any("không có dạng tách biến" in w for w in res.warnings)


# =========================================================================
# Phase D — Exact ODEs
# =========================================================================

def test_exact_ode_standard_implicit_solve(exact_solver: ODEExactSolver):
    """Test (2*x*y + 3) + (x^2 + 4*y)*y' = 0 with potential F(x, y) = x^2*y + 3*x + 2*y^2 = C."""
    req = ProblemRequest(
        raw_input="(2*x*y + 3) + (x^2 + 4*y)*y' = 0",
        problem_type=ProblemType.ODE_EXACT,
        target_variable="x",
    )
    res = exact_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "= C" in res.final_result
    assert "3*x" in res.final_result
    assert "2*y**2" in res.final_result or "2*y^2" in res.final_latex
    assert res.verification.status == VerificationStatus.VERIFIED
    step_titles = [s.title for s in res.steps]
    assert any("điều kiện vi phân toàn phần" in t.lower() for t in step_titles)
    assert any("xây dựng hàm thế" in t.lower() for t in step_titles)


def test_exact_ode_differential_form_with_ivp(exact_solver: ODEExactSolver):
    """Test (2*x*y + 3)*dx + (x^2 + 4*y)*dy = 0 with y(0) = 1 => C = F(0, 1) = 2."""
    req = ProblemRequest(
        raw_input="(2*x*y + 3)*dx + (x^2 + 4*y)*dy = 0, y(0) = 1",
        problem_type=ProblemType.ODE_EXACT,
        target_variable="x",
    )
    res = exact_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "= 2" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


def test_exact_ode_rejects_non_exact_equation(exact_solver: ODEExactSolver):
    """Test (2*x*y) + x*y' = 0: dM/dy = 2x != dN/dx = 1 => rejects with clear explanation."""
    req = ProblemRequest(
        raw_input="(2*x*y) + x*y' = 0",
        problem_type=ProblemType.ODE_EXACT,
        target_variable="x",
    )
    res = exact_solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert any("không phải là phương trình vi phân toàn phần" in w for w in res.warnings)


def test_exact_ode_section8_example(exact_solver: ODEExactSolver):
    """Test Section 8 example: (3x^2 + 4x + 2)dx + (2y - 2)dy = 0 => x^3 + 2x^2 + 2x + y^2 - 2y = C."""
    req = ProblemRequest(
        raw_input="(3*x^2 + 4*x + 2)*dx + (2*y - 2)*dy = 0",
        problem_type=ProblemType.ODE_EXACT,
        target_variable="x",
    )
    res = exact_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "x**3 + 2*x**2 + 2*x + y**2 - 2*y" in res.final_result
    assert "= C" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


def test_exact_ode_rejects_missing_derivative(exact_solver: ODEExactSolver):
    """Missing y' or dy in equation should fail with InvalidInputError."""
    with pytest.raises(InvalidInputError, match="không chứa đạo hàm cấp 1"):
        exact_solver.solve(ProblemRequest("2*x*y + 3 = 0", ProblemType.ODE_EXACT, target_variable="x"))


# =========================================================================
# Phase 3 — Multi-branch, Real branches & Equilibrium Solutions
# =========================================================================

def test_separable_multi_branch_square_derivative(sep_solver: ODESeparableSolver):
    """Case 1: (y')^2 = x produces both branches y = ±(2/3*x^(3/2) + C) and domain x >= 0."""
    req = ProblemRequest(raw_input="(y')^2 = x", problem_type=ProblemType.ODE_SEPARABLE, target_variable="x")
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "x**(3/2)" in res.final_result or "x^(3/2)" in res.final_latex
    assert "hoặc" in res.final_result
    assert any("x >= 0" in r for r in res.domain_restrictions)
    assert res.verification.status == VerificationStatus.VERIFIED


def test_separable_rejects_purely_imaginary_derivative_branch(sep_solver: ODESeparableSolver):
    """Case 2: (y')^2 + 1 = 0 has no real derivative branches; must return CANNOT_SOLVE, not an imaginary solution."""
    req = ProblemRequest(raw_input="(y')^2 + 1 = 0", problem_type=ProblemType.ODE_SEPARABLE, target_variable="x")
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert "không có nghiệm thực" in res.final_result.lower()
    assert res.verification.status == VerificationStatus.NOT_APPLICABLE
    assert any("không có nghiệm thực" in w.lower() for w in res.warnings)


def test_separable_multi_branch_exponential_and_equilibrium(sep_solver: ODESeparableSolver):
    """Case 4: (y')^2 = y^2 produces both branches y = exp(±x + C) and equilibrium y = 0."""
    req = ProblemRequest(raw_input="(y')^2 = y^2", problem_type=ProblemType.ODE_SEPARABLE, target_variable="x")
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "exp" in res.final_result
    assert "hoặc" in res.final_result
    assert "y = 0" in res.final_result  # equilibrium preserved
    assert res.verification.status == VerificationStatus.VERIFIED


def test_separable_logistic_preserves_both_equilibria(sep_solver: ODESeparableSolver):
    """Case 3: y' = y*(1 - y) preserves both equilibrium solutions y = 0 and y = 1 in final result."""
    req = ProblemRequest(raw_input="y' = y*(1 - y)", problem_type=ProblemType.ODE_SEPARABLE, target_variable="x")
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "0" in res.final_result and "1" in res.final_result
    assert "cân bằng" in res.final_result.lower()
    assert res.verification.status == VerificationStatus.VERIFIED


def test_separable_transcendental_sine_ode(sep_solver: ODESeparableSolver):
    """Case 5: y' = sin(y) parses safely and solves as non-polynomial separable ODE."""
    req = ProblemRequest(raw_input="y' = sin(y)", problem_type=ProblemType.ODE_SEPARABLE, target_variable="x")
    res = sep_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "y = 0" in res.final_result or "sin" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED



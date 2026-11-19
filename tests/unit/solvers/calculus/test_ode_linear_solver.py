"""Unit tests for Phase A and Phase B First-Order Linear ODE solver."""

import pytest

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.linear_solver import ODELinearSolver


@pytest.fixture
def solver() -> ODELinearSolver:
    return ODELinearSolver()


# =========================================================================
# Phase A — First-order linear ODE with constant coefficients
# =========================================================================

def test_phase_a_standard_constant_coefficients(solver: ODELinearSolver):
    """Test y' = 2y + 3 with general solution y(t) = C*e^(2t) - 3/2."""
    req = ProblemRequest(raw_input="y' = 2*y + 3", problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR, target_variable="t")
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "exp(2*t)" in res.final_result
    assert "3/2" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED
    # Should identify equilibrium solution y_eq = -3/2
    step_titles = [s.title for s in res.steps]
    assert any("cân bằng" in t for t in step_titles)
    assert any("thừa số tích phân" in t.lower() or "nghiệm tổng quát" in t.lower() for t in step_titles)


def test_phase_a_zero_a_coefficient(solver: ODELinearSolver):
    """Test y' = 0y + 3 => direct integration y(t) = 3t + C."""
    req = ProblemRequest(raw_input="y' = 0*y + 3", problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR, target_variable="t")
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "3*t" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED
    step_titles = [s.title for s in res.steps]
    assert any("a = 0" in t for t in step_titles)


def test_phase_a_zero_b_coefficient(solver: ODELinearSolver):
    """Test y' = 2y => y(t) = C*e^(2t)."""
    req = ProblemRequest(raw_input="y' = 2*y", problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR, target_variable="t")
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "exp(2*t)" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED
    # Equilibrium solution is y = 0
    assert any("y_eq = 0" in s.content.expression_after for s in res.steps if "cân bằng" in s.title)


def test_phase_a_zero_derivative(solver: ODELinearSolver):
    """Test y' = 0 => y(t) = C."""
    req = ProblemRequest(raw_input="y' = 0", problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR, target_variable="t")
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "y(t) = C" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


def test_phase_a_initial_value_problem(solver: ODELinearSolver):
    """Test y' = 2y + 3 with y(0) = 1 => particular solution y(t) = (5/2)*e^(2t) - 3/2."""
    req = ProblemRequest(
        raw_input="y' = 2*y + 3, y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "5*exp(2*t)/2 - 3/2" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED
    step_titles = [s.title for s in res.steps]
    assert any("điều kiện ban đầu" in t.lower() for t in step_titles)
    assert any("nghiệm riêng" in t.lower() for t in step_titles)


def test_phase_a_symbolic_coefficient(solver: ODELinearSolver):
    """Test y' = k*y with symbolic parameter k."""
    req = ProblemRequest(raw_input="y' = k*y", problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR, target_variable="t")
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "exp(k*t)" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


# =========================================================================
# Phase B — First-order linear ODE with variable coefficients
# =========================================================================

def test_phase_b_simple_variable_homogeneous(solver: ODELinearSolver):
    """Test y' + y = 0 => y(t) = C*e^(-t)."""
    req = ProblemRequest(raw_input="y' + y = 0", problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR, target_variable="t")
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "exp(-t)" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


def test_phase_b_integrating_factor_method(solver: ODELinearSolver):
    """Test y' + (1/2)*y = t + 2 => y(t) = C*e^(-t/2) + 2t."""
    req = ProblemRequest(
        raw_input="y' + (1/2)*y = t + 2",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "exp(-t/2)" in res.final_result
    assert "2*t" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED

    # Check that all 6 required integrating factor steps are present
    assert len(res.steps) == 6
    assert any("Xác định hệ số" in s.rule_name or "Nhận dạng" in s.title for s in res.steps)
    assert any("Thừa số tích phân" in s.rule_name for s in res.steps)
    assert any("Nhân hai vế" in s.title for s in res.steps)
    assert any("đạo hàm của tích" in s.title.lower() for s in res.steps)
    assert any("Tích phân hai vế" in s.rule_name for s in res.steps)
    assert any("Rút ra nghiệm tổng quát" in s.title for s in res.steps)


def test_phase_b_zero_forcing_term(solver: ODELinearSolver):
    """Test y' + 2*t*y = 0 with p(t) = 2t and g(t) = 0 => y(t) = C*e^(-t^2)."""
    req = ProblemRequest(
        raw_input="y' + 2*t*y = 0",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "exp(-t**2)" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


def test_phase_b_variable_coeff_ivp(solver: ODELinearSolver):
    """Test y' + 2*t*y = 0 with y(0) = 3 => y(t) = 3*e^(-t^2)."""
    req = ProblemRequest(
        raw_input="y' + 2*t*y = 0, y(0) = 3",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "3*exp(-t**2)" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


def test_phase_b_non_elementary_integral_unsupported(solver: ODELinearSolver):
    """Test y' + y = exp(t^2) where int(mu*g dt) has non-elementary antiderivative."""
    req = ProblemRequest(
        raw_input="y' + y = exp(t^2)",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert any("không có nguyên hàm sơ cấp" in w for w in res.warnings)


def test_linear_ode_section8_example_constant_x(solver: ODELinearSolver):
    """Test Section 8 example: y' + 2y = 3 => y(x) = 3/2 + C*e^(-2x)."""
    req = ProblemRequest(raw_input="y' + 2*y = 3", problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR, target_variable="x")
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "exp(-2*x)" in res.final_result or "exp(-2*x)" in str(res.final_result)
    assert "3/2" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


def test_linear_ode_section8_example_variable_x(solver: ODELinearSolver):
    """Test Section 8 example: y' + (1/2)*y = 2 + x => y(x) = 2x + C*e^(-x/2)."""
    req = ProblemRequest(raw_input="y' + (1/2)*y = 2 + x", problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR, target_variable="x")
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "2*x" in res.final_result
    assert "exp(-x/2)" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


# =========================================================================
# Security and Robustness Tests
# =========================================================================

def test_security_rejects_arbitrary_code(solver: ODELinearSolver):
    """Test that malicious Python expressions are strictly rejected."""
    malicious_inputs = [
        "__import__('os').system('echo pwned')",
        "eval('2 + 2')",
        "exec('y = 1')",
        "y' = os.system('ls')",
        "y' = [x for x in ().__class__.__base__.__subclasses__()]",
    ]
    for bad in malicious_inputs:
        with pytest.raises(InvalidInputError):
            solver.solve(ProblemRequest(bad, ProblemType.ODE_FIRST_ORDER_LINEAR))


def test_malformed_ode_inputs(solver: ODELinearSolver):
    """Test that malformed ODE expressions fail safely with InvalidInputError."""
    # Empty
    with pytest.raises(InvalidInputError, match="không được để trống"):
        solver.solve(ProblemRequest("", ProblemType.ODE_FIRST_ORDER_LINEAR))

    # Missing y'
    with pytest.raises(InvalidInputError, match="không chứa đạo hàm cấp 1"):
        solver.solve(ProblemRequest("2*y + 3 = 0", ProblemType.ODE_FIRST_ORDER_LINEAR))

    # Multiple '='
    with pytest.raises(InvalidInputError, match="đúng một dấu"):
        solver.solve(ProblemRequest("y' = 2 = 3", ProblemType.ODE_FIRST_ORDER_LINEAR))

    # Empty RHS
    with pytest.raises(InvalidInputError, match="không được để trống"):
        solver.solve(ProblemRequest("y' =", ProblemType.ODE_FIRST_ORDER_LINEAR))


def test_nonlinear_equation_reports_cannot_solve(solver: ODELinearSolver):
    """Nonlinear equations (e.g. y' = y^2 or (y')^2 = y) should report CANNOT_SOLVE gracefully."""
    req = ProblemRequest("y' = y^2", ProblemType.ODE_FIRST_ORDER_LINEAR, target_variable="t")
    res = solver.solve(req)
    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert any("phi tuyến tính" in w for w in res.warnings)

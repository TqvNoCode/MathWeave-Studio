"""Unit tests for Integrating Factor ODE solver: mu(x) and mu(y)."""

import pytest

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.integrating_factor_solver import ODEIntegratingFactorSolver


@pytest.fixture
def if_solver() -> ODEIntegratingFactorSolver:
    return ODEIntegratingFactorSolver()


# =========================================================================
# Case 1: Integrating factor depending only on x: mu(x)
# =========================================================================

def test_integrating_factor_depending_on_x(if_solver: ODEIntegratingFactorSolver):
    """Test (3xy + y^2)dx + (x^2 + xy)dy = 0:

    M_y = 3x + 2y, N_x = 2x + y => (M_y - N_x)/N = (x + y)/(x(x + y)) = 1/x = f(x).
    mu(x) = exp(int(1/x dx)) = x.
    Transformed: (3x^2*y + x*y^2)dx + (x^3 + x^2*y)dy = 0 is exact.
    Potential: F(x, y) = x^3*y + x^2*y^2 / 2 = C.
    """
    req = ProblemRequest(
        raw_input="(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0",
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
        target_variable="x",
    )
    res = if_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "= C" in res.final_result
    assert "x**3*y" in res.final_result
    assert "x**2*y**2/2" in res.final_result or "x^2*y^2" in res.final_latex
    assert res.verification.status == VerificationStatus.VERIFIED

    # Check pedagogical steps
    step_rules = [s.rule_name for s in res.steps]
    assert any("Kiểm tra tính vi phân toàn phần" in r for r in step_rules)
    assert any("mu(x)" in r for r in step_rules)
    assert any("sau khi nhân mu" in r for r in step_rules)
    assert any("Xây dựng hàm thế" in r for r in step_rules)


def test_integrating_factor_depending_on_x_with_ivp(if_solver: ODEIntegratingFactorSolver):
    """Test (3xy + y^2)dx + (x^2 + xy)dy = 0 with y(1) = 2:

    C = F(1, 2) = 1^3 * 2 + 1^2 * 2^2 / 2 = 2 + 2 = 4.
    """
    req = ProblemRequest(
        raw_input="(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0, y(1) = 2",
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
        target_variable="x",
    )
    res = if_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "= 4" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED
    assert any("điều kiện ban đầu" in s.title.lower() for s in res.steps)


# =========================================================================
# Case 2: Integrating factor depending only on y: mu(y)
# =========================================================================

def test_integrating_factor_depending_on_y(if_solver: ODEIntegratingFactorSolver):
    """Test y dx + (2xy - exp(-2y)) dy = 0:

    M = y, N = 2xy - exp(-2y).
    M_y = 1, N_x = 2y.
    (N_x - M_y)/M = (2y - 1)/y = 2 - 1/y = g(y).
    mu(y) = exp(2y - ln(y)) = exp(2y)/y.
    Transformed: exp(2y) dx + (2x*exp(2y) - exp(-2y)*exp(2y)/y) dy = 0.
    Potential: F(x, y) = x*exp(2*y) - log(y) = C.
    """
    req = ProblemRequest(
        raw_input="y*dx + (2*x*y - exp(-2*y))*dy = 0",
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
        target_variable="x",
    )
    res = if_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "= C" in res.final_result
    assert "x*exp(2*y)" in res.final_result
    assert "log(y)" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED

    step_rules = [s.rule_name for s in res.steps]
    assert any("mu(y)" in r for r in step_rules)


# =========================================================================
# Case 3: Already exact equation
# =========================================================================

def test_integrating_factor_already_exact_equation(if_solver: ODEIntegratingFactorSolver):
    """When an already exact equation is passed, mu = 1 and solves directly."""
    req = ProblemRequest(
        raw_input="(3*x^2 + 4*x + 2)*dx + (2*y - 2)*dy = 0",
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
        target_variable="x",
    )
    res = if_solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "= C" in res.final_result
    assert "x**3 + 2*x**2 + 2*x + y**2 - 2*y" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED
    assert any("đã là vi phân toàn phần" in s.description for s in res.steps)


# =========================================================================
# Case 4: Unsupported non-exact equations (neither mu(x) nor mu(y))
# =========================================================================

def test_integrating_factor_unsupported_two_variable_defect(if_solver: ODEIntegratingFactorSolver):
    """Equation (x + y^2)dx + (x^2 + y)dy = 0:

    M_y = 2y, N_x = 2x.
    (M_y - N_x)/N = (2y - 2x)/(x^2 + y) depends on both x and y.
    (N_x - M_y)/M = (2x - 2y)/(x + y^2) depends on both x and y.
    Solver must report CANNOT_SOLVE and not claim bogus solution.
    """
    req = ProblemRequest(
        raw_input="(x + y^2)*dx + (x^2 + y)*dy = 0",
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
        target_variable="x",
    )
    res = if_solver.solve(req)

    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert any("không tồn tại thừa số tích phân" in w for w in res.warnings)


# =========================================================================
# Case 5: Missing derivative and error handling
# =========================================================================

def test_integrating_factor_rejects_missing_derivative(if_solver: ODEIntegratingFactorSolver):
    with pytest.raises(InvalidInputError, match="không chứa đạo hàm cấp 1"):
        if_solver.solve(ProblemRequest("x*y + 2 = 0", ProblemType.ODE_INTEGRATING_FACTOR))

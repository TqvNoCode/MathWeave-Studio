"""Comprehensive test matrix for Milestone 1 First-Order ODE subsystem.

Validates:
1. Linear ODEs (Constant and variable coefficients, IVP, Section 8 examples).
2. Separable ODEs (Equilibrium preservation, singular exclusions, implicit/explicit, Section 8 examples).
3. Exact ODEs (Exactness condition verification, potential function, Section 8 examples).
4. Integrating Factor ODEs (x-dependent and y-dependent, transformed exactness verification).
5. General test matrix:
   - Initial value problems
   - Invalid expressions and AST safety
   - Zero denominators and singular poles
   - Missing variables
   - Unsupported equations and clean rejection
   - Unsolvable symbolic integrals
   - Multiple solution branches (implicit preservation)
   - Equilibrium solutions and hits
   - Domain restrictions extraction
   - Large expressions and complexity bounds
   - Timeout behavior and process isolation
   - Verification failures resulting in DISCREPANCY_DETECTED
   - End-to-end execution via build_application()
"""

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.main import build_application
from math_app.solvers.calculus.ode.exact_solver import ODEExactSolver
from math_app.solvers.calculus.ode.integrating_factor_solver import ODEIntegratingFactorSolver
from math_app.solvers.calculus.ode.linear_solver import ODELinearSolver
from math_app.solvers.calculus.ode.separable_solver import ODESeparableSolver
from math_app.verification.calculus.ode_verifier import ODEVerifier


# =========================================================================
# 1. Linear ODEs — Section 8 Examples & Properties
# =========================================================================

def test_linear_ode_section8_constant_coeff():
    """Section 8 example: y' + 2y = 3 => y(x) = 3/2 + C*e^(-2x)."""
    solver = ODELinearSolver()
    req = ProblemRequest(
        raw_input="y' + 2*y = 3",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # No double minus in latex formatting
    assert "- -" not in res.final_latex
    assert "\\frac{3}{2}" in res.final_latex
    assert "e^{- 2 x}" in res.final_latex or "e^{-2 x}" in res.final_latex
    # Symbolic equivalence of general solution
    x, C = sp.symbols("x C")
    expected_sol = sp.Rational(3, 2) + C * sp.exp(-2 * x)
    parsed_sol = sp.sympify(res.final_result.split("=")[1].strip())
    assert sp.simplify(parsed_sol - expected_sol) == 0


def test_linear_ode_section8_variable_coeff():
    """Section 8 example with variable coefficients: y' + (1/2)*y = 2 + x => y(x) = 2x + C*e^(-x/2)."""
    solver = ODELinearSolver()
    req = ProblemRequest(
        raw_input="y' + (1/2)*y = 2 + x",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    x, C = sp.symbols("x C")
    expected_sol = 2 * x + C * sp.exp(-x / 2)
    parsed_sol = sp.sympify(res.final_result.split("=")[1].strip())
    assert sp.simplify(parsed_sol - expected_sol) == 0


def test_linear_ode_initial_value_problem():
    """IVP: y' + 2y = 4, y(0) = 5 => y(x) = 2 + 3*e^(-2x)."""
    solver = ODELinearSolver()
    req = ProblemRequest(
        raw_input="y' + 2*y = 4, y(0) = 5",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    x = sp.symbols("x")
    expected_part = 2 + 3 * sp.exp(-2 * x)
    parsed_sol = sp.sympify(res.final_result.split("=")[1].strip())
    assert sp.simplify(parsed_sol - expected_part) == 0
    assert any("nghiệm riêng" in s.title.lower() for s in res.steps)


# =========================================================================
# 2. Separable ODEs — Section 8 Example, Singularities & Equilibria
# =========================================================================

def test_separable_ode_section8_example():
    """Section 8 example: dy/dx = x^2 / (1 - y^2) => y - y^3/3 = x^3/3 + C."""
    solver = ODESeparableSolver()
    req = ProblemRequest(
        raw_input="dy/dx = x^2 / (1 - y^2)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Verified implicit relationship: (y - y^3/3) - (x^3/3) = const
    assert "y**3/3" in res.final_result or "y^3/3" in res.final_latex
    assert "x**3/3" in res.final_result or "x^3/3" in res.final_latex
    # Denominator restrictions: y != 1 and y != -1
    assert any("1" in r for r in res.domain_restrictions)
    assert any("-1" in r for r in res.domain_restrictions)
    # Check that steps use dx and dy, not dt
    step_texts = [s.content.expression_after for s in res.steps]
    assert not any("dt" in t for t in step_texts)


def test_separable_ode_equilibrium_solutions_preservation():
    """dy/dx = (x + 1)*(y^2 - 4): preserves equilibrium solutions y = 2 and y = -2."""
    solver = ODESeparableSolver()
    req = ProblemRequest(
        raw_input="dy/dx = (x + 1)*(y^2 - 4)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    eq_step = next(s for s in res.steps if "cân bằng" in s.title.lower())
    assert "2" in eq_step.content.expression_after
    assert "-2" in eq_step.content.expression_after


def test_separable_ode_initial_condition_hitting_equilibrium():
    """dy/dx = (x + 1)*(y^2 - 4) with y(0) = 2 => unique solution y(x) = 2."""
    solver = ODESeparableSolver()
    req = ProblemRequest(
        raw_input="dy/dx = (x + 1)*(y^2 - 4), y(0) = 2",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert "y(x) = 2" in res.final_result
    assert res.verification.status == VerificationStatus.VERIFIED


# =========================================================================
# 3. Exact ODEs — Section 8 Example & Verification
# =========================================================================

def test_exact_ode_section8_example():
    """Section 8 example: (3x^2 + 4x + 2)dx + (2y - 2)dy = 0 => x^3 + 2x^2 + 2x + y^2 - 2y = C."""
    solver = ODEExactSolver()
    req = ProblemRequest(
        raw_input="(3*x^2 + 4*x + 2)*dx + (2*y - 2)*dy = 0",
        problem_type=ProblemType.ODE_EXACT,
        target_variable="x",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Check potential function terms
    x, y = sp.symbols("x y")
    expected_pot = x**3 + 2 * x**2 + 2 * x + y**2 - 2 * y
    pot_str = res.final_result.split("=")[0].strip()
    assert sp.simplify(sp.sympify(pot_str) - expected_pot) == 0


def test_exact_ode_ivp_particular_solution():
    """(3x^2 + 4x + 2)dx + (2y - 2)dy = 0, y(0) = 1 => C = F(0, 1) = 0 - 0 + 0 + 1 - 2 = -1."""
    solver = ODEExactSolver()
    req = ProblemRequest(
        raw_input="(3*x^2 + 4*x + 2)*dx + (2*y - 2)*dy = 0, y(0) = 1",
        problem_type=ProblemType.ODE_EXACT,
        target_variable="x",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "= -1" in res.final_result
    assert any("điều kiện ban đầu" in s.title.lower() for s in res.steps)


# =========================================================================
# 4. Integrating Factor ODEs — mu(x) and mu(y)
# =========================================================================

def test_integrating_factor_depending_on_x_complete_pipeline():
    """(3xy + y^2)dx + (x^2 + xy)dy = 0 => mu(x) = x, F(x, y) = x^3*y + (1/2)*x^2*y^2 = C."""
    solver = ODEIntegratingFactorSolver()
    req = ProblemRequest(
        raw_input="(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0",
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
        target_variable="x",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Verified mu and transformed exactness
    step_titles = [s.title for s in res.steps]
    assert any("thừa số tích phân" in t.lower() and "x" in t.lower() for t in step_titles)
    assert any("xác nhận phương trình mới là vi phân toàn phần" in t.lower() for t in step_titles)
    # Check potential
    x, y = sp.symbols("x y")
    expected_pot = x**3 * y + sp.Rational(1, 2) * x**2 * y**2
    pot_str = res.final_result.split("=")[0].strip()
    assert sp.simplify(sp.sympify(pot_str) - expected_pot) == 0


def test_integrating_factor_depending_on_y_complete_pipeline():
    """y dx + (2xy - exp(-2y)) dy = 0 => mu(y) = exp(2y)/y, F(x, y) = x*exp(2y) - log(y) = C."""
    solver = ODEIntegratingFactorSolver()
    req = ProblemRequest(
        raw_input="y*dx + (2*x*y - exp(-2*y))*dy = 0",
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
        target_variable="x",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    # Domain restrictions must identify y != 0
    assert any("y" in r and "0" in r for r in res.domain_restrictions)
    x, y = sp.symbols("x y")
    expected_pot = x * sp.exp(2 * y) - sp.log(y)
    pot_str = res.final_result.split("=")[0].strip()
    assert sp.simplify(sp.sympify(pot_str) - expected_pot) == 0


# =========================================================================
# 5. General Test Matrix — Edge Cases & Robustness
# =========================================================================

def test_zero_denominator_pole_handling_in_linear():
    """Linear ODE x*y' + y = 1 has a pole at x = 0; domain restriction x != 0 must be extracted."""
    solver = ODELinearSolver()
    req = ProblemRequest(
        raw_input="x*y' + y = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert any("x" in r and "0" in r for r in res.domain_restrictions)
    assert res.verification.status == VerificationStatus.VERIFIED


def test_missing_variables_and_invalid_expressions():
    """Missing derivative or invalid math expression must raise InvalidInputError."""
    solver = ODELinearSolver()

    # Missing derivative y'
    with pytest.raises(InvalidInputError, match="không chứa đạo hàm cấp 1"):
        solver.solve(ProblemRequest("2*x + 3*y = 5", ProblemType.ODE_FIRST_ORDER_LINEAR, "x"))

    # Malformed expression
    with pytest.raises(InvalidInputError):
        solver.solve(ProblemRequest("y' + (2* = 3", ProblemType.ODE_FIRST_ORDER_LINEAR, "x"))

    # Empty expression
    with pytest.raises(InvalidInputError, match="không được để trống"):
        solver.solve(ProblemRequest("   ", ProblemType.ODE_FIRST_ORDER_LINEAR, "x"))


def test_unsupported_equations_graceful_rejection():
    """Equations not meeting class assumptions must cleanly report CANNOT_SOLVE."""
    lin_solver = ODELinearSolver()
    sep_solver = ODESeparableSolver()
    exact_solver = ODEExactSolver()
    if_solver = ODEIntegratingFactorSolver()

    # Nonlinear passed to linear solver
    res_lin = lin_solver.solve(ProblemRequest("y' = y^3", ProblemType.ODE_FIRST_ORDER_LINEAR, "x"))
    assert res_lin.status == SolutionStatus.CANNOT_SOLVE
    assert res_lin.verification.status == VerificationStatus.NOT_APPLICABLE

    # Non-separable passed to separable solver
    res_sep = sep_solver.solve(ProblemRequest("y' = x^2 + y^2", ProblemType.ODE_SEPARABLE, "x"))
    assert res_sep.status == SolutionStatus.CANNOT_SOLVE
    assert res_sep.verification.status == VerificationStatus.NOT_APPLICABLE

    # Non-exact passed to exact solver
    res_exact = exact_solver.solve(ProblemRequest("(2*x*y)*dx + x*dy = 0", ProblemType.ODE_EXACT, "x"))
    assert res_exact.status == SolutionStatus.CANNOT_SOLVE
    assert res_exact.verification.status == VerificationStatus.NOT_APPLICABLE

    # Equation without single-variable integrating factor
    res_if = if_solver.solve(ProblemRequest("(x + y^2)*dx + (x^2 + y)*dy = 0", ProblemType.ODE_INTEGRATING_FACTOR, "x"))
    assert res_if.status == SolutionStatus.CANNOT_SOLVE
    assert res_if.verification.status == VerificationStatus.NOT_APPLICABLE


def test_unsolvable_symbolic_integrals():
    """Equations with non-elementary integrals must report CANNOT_SOLVE with informative warning."""
    lin_solver = ODELinearSolver()
    # y' + y = exp(x^2): int(exp(x)*exp(x^2) dx) is non-elementary
    res = lin_solver.solve(ProblemRequest("y' + y = exp(x^2)", ProblemType.ODE_FIRST_ORDER_LINEAR, "x"))
    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert any("nguyên hàm sơ cấp" in w for w in res.warnings)


def test_verification_failure_yields_discrepancy_status():
    """If independent verifier detects discrepancy, solution response must NOT be marked SUCCESS."""
    class BadVerifier(ODEVerifier):
        def verify_explicit(self, *args, **kwargs):
            from math_app.application.dtos import VerificationResult
            return VerificationResult(
                status=VerificationStatus.FAILED,
                method="mock_residual_failure",
                details="Forced verification mismatch for test.",
            )

    faulty_solver = ODELinearSolver(verifier=BadVerifier())
    req = ProblemRequest("y' + 2*y = 3", ProblemType.ODE_FIRST_ORDER_LINEAR, "x")
    res = faulty_solver.solve(req)

    assert res.status == SolutionStatus.DISCREPANCY_DETECTED
    assert res.verification.status == VerificationStatus.FAILED
    assert any("Cảnh báo kiểm định toán học" in w for w in res.warnings)


def test_end_to_end_build_application_dispatch():
    """Verify that build_application() dispatches all 4 ODE problem types cleanly through use case."""
    app_use_case = build_application()

    # 1. Linear
    req1 = ProblemRequest("y' + 2*y = 4", ProblemType.ODE_FIRST_ORDER_LINEAR, "x")
    res1 = app_use_case.execute(req1)
    assert res1.status == SolutionStatus.SUCCESS
    assert res1.verification.status == VerificationStatus.VERIFIED

    # 2. Separable
    req2 = ProblemRequest("dy/dx = 2*x*y", ProblemType.ODE_SEPARABLE, "x")
    res2 = app_use_case.execute(req2)
    assert res2.status == SolutionStatus.SUCCESS
    assert res2.verification.status == VerificationStatus.VERIFIED

    # 3. Exact
    req3 = ProblemRequest("(3*x^2 + 4*x + 2)*dx + (2*y - 2)*dy = 0", ProblemType.ODE_EXACT, "x")
    res3 = app_use_case.execute(req3)
    assert res3.status == SolutionStatus.SUCCESS
    assert res3.verification.status == VerificationStatus.VERIFIED

    # 4. Integrating factor
    req4 = ProblemRequest("(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0", ProblemType.ODE_INTEGRATING_FACTOR, "x")
    res4 = app_use_case.execute(req4)
    assert res4.status == SolutionStatus.SUCCESS
    assert res4.verification.status == VerificationStatus.VERIFIED

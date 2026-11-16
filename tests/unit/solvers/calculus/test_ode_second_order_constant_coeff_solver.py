"""Unit tests for Second-Order Linear ODE solver with constant coefficients & IVP."""

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.solvers.calculus.ode.second_order_constant_coeff_solver import ODESecondOrderConstantCoeffSolver


@pytest.fixture
def solver() -> ODESecondOrderConstantCoeffSolver:
    return ODESecondOrderConstantCoeffSolver()


# =========================================================================
# Module A — Constant-Coefficient Homogeneous ODEs
# =========================================================================

def test_case_1_distinct_real_roots(solver: ODESecondOrderConstantCoeffSolver):
    """Test y'' + 5y' + 6y = 0 with Delta > 0, r1 = -2, r2 = -3."""
    req = ProblemRequest(
        raw_input="y'' + 5*y' + 6*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(-2*t)" in res.final_result or "exp(-3*t)" in res.final_result
    # Steps
    titles = [s.title for s in res.steps]
    assert any("phương trình đặc trưng" in t.lower() for t in titles)
    assert any("delta" in t.lower() for t in titles)
    assert any("hai nghiệm thực phân biệt" in t.lower() for t in titles)


def test_case_2_complex_conjugate_roots_pure_imaginary(solver: ODESecondOrderConstantCoeffSolver):
    """Test y'' + 9y = 0 with Delta < 0, roots = +- 3i => real cos(3t), sin(3t)."""
    req = ProblemRequest(
        raw_input="y'' + 9*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "cos(3*t)" in res.final_result
    assert "sin(3*t)" in res.final_result
    assert "I" not in res.final_result  # No imaginary units in real general solution
    titles = [s.title for s in res.steps]
    assert any("nghiệm phức" in t.lower() for t in titles)
    assert any("euler" in t.lower() for t in titles)


def test_case_2_complex_conjugate_roots_with_real_part(solver: ODESecondOrderConstantCoeffSolver):
    """Test y'' + 2y' + 5y = 0 with roots = -1 +- 2i => e^(-t)(C1*cos(2t) + C2*sin(2t))."""
    req = ProblemRequest(
        raw_input="y'' + 2*y' + 5*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(-t)" in res.final_result
    assert "cos(2*t)" in res.final_result
    assert "sin(2*t)" in res.final_result
    assert "I" not in res.final_result


def test_case_3_repeated_real_root(solver: ODESecondOrderConstantCoeffSolver):
    """Test y'' - 2y' + y = 0 with Delta = 0, root = 1 repeated => (C1 + C2*t)*e^t."""
    req = ProblemRequest(
        raw_input="y'' - 2*y' + y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(t)" in res.final_result
    assert "*t" in res.final_result or "C2*t" in res.final_result
    titles = [s.title for s in res.steps]
    assert any("nghiệm kép" in t.lower() for t in titles)
    assert any("thừa số nhân t" in t.lower() for t in titles)


def test_edge_case_zero_roots(solver: ODESecondOrderConstantCoeffSolver):
    """Test y'' = 0 => repeated root r = 0 => y = C1 + C2*t."""
    req = ProblemRequest(
        raw_input="y'' = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "C1" in res.final_result
    assert "C2*t" in res.final_result


def test_edge_case_zero_c_coeff(solver: ODESecondOrderConstantCoeffSolver):
    """Test y'' - 4y' = 0 => roots r1 = 0, r2 = 4 => y = C1 + C2*e^(4t)."""
    req = ProblemRequest(
        raw_input="y'' - 4*y' = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(4*t)" in res.final_result


def test_rational_coefficients(solver: ODESecondOrderConstantCoeffSolver):
    """Test 4y'' - 4y' + y = 0 with repeated root r = 1/2 => (C1 + C2*t)*e^(t/2)."""
    req = ProblemRequest(
        raw_input="4*y'' - 4*y' + y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED
    assert "exp(t/2)" in res.final_result


def test_rejection_of_nonhomogeneous_ode(solver: ODESecondOrderConstantCoeffSolver):
    """Verify nonhomogeneous equation is cleanly rejected."""
    req = ProblemRequest(
        raw_input="y'' + y = sin(t)",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert any("không thuần nhất" in w.lower() for w in res.warnings)


def test_rejection_of_variable_coefficients(solver: ODESecondOrderConstantCoeffSolver):
    """Verify variable-coefficient equation is rejected by constant-coeff solver."""
    req = ProblemRequest(
        raw_input="2*t^2*y'' + 3*t*y' - y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="t",
    )
    res = solver.solve(req)
    assert res.status == SolutionStatus.CANNOT_SOLVE
    assert any("hệ số phụ thuộc biến số" in w.lower() for w in res.warnings)


# =========================================================================
# Module B — Second-Order Initial Value Problems (IVP)
# =========================================================================

def test_mandatory_reference_example_ivp(solver: ODESecondOrderConstantCoeffSolver):
    """Mandatory Reference Example:

    y'' + 5y' + 6y = 0,  y(0) = 2,  y'(0) = 3.
    Expected: y(t) = 9*e^(-2t) - 7*e^(-3t).
    """
    req = ProblemRequest(
        raw_input="y'' + 5*y' + 6*y = 0, y(0) = 2, y'(0) = 3",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    # Mathematical verification of the solution expression
    t = sp.Symbol("t")
    expected_sol = 9 * sp.exp(-2 * t) - 7 * sp.exp(-3 * t)

    # Parse resulting solution from final_result string y(t) = ...
    res_str = res.final_result.split("=", 1)[1].strip()
    parsed_sol = sp.sympify(res_str)

    # Check exact mathematical identity
    assert sp.simplify(parsed_sol - expected_sol) == 0

    # Verify initial conditions directly
    assert sp.simplify(parsed_sol.subs(t, 0)) == 2
    assert sp.simplify(sp.diff(parsed_sol, t).subs(t, 0)) == 3

    # Verify ODE residual
    d2 = sp.diff(parsed_sol, t, 2)
    d1 = sp.diff(parsed_sol, t, 1)
    assert sp.simplify(d2 + 5 * d1 + 6 * parsed_sol) == 0


def test_ivp_complex_conjugate_roots(solver: ODESecondOrderConstantCoeffSolver):
    """Test IVP with pure imaginary roots:

    y'' + 9y = 0, y(0) = 2, y'(0) = 3 => y(t) = 2*cos(3t) + sin(3t).
    """
    req = ProblemRequest(
        raw_input="y'' + 9*y = 0, y(0) = 2, y'(0) = 3",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    expected = 2 * sp.cos(3 * t) + sp.sin(3 * t)
    res_str = res.final_result.split("=", 1)[1].strip()
    assert sp.simplify(sp.sympify(res_str) - expected) == 0


def test_ivp_repeated_root(solver: ODESecondOrderConstantCoeffSolver):
    """Test IVP with repeated root:

    y'' - 2y' + y = 0, y(0) = 1, y'(0) = 4 => y(t) = (1 + 3t)*e^t.
    """
    req = ProblemRequest(
        raw_input="y'' - 2*y' + y = 0, y(0) = 1, y'(0) = 4",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    expected = (1 + 3 * t) * sp.exp(t)
    res_str = res.final_result.split("=", 1)[1].strip()
    assert sp.simplify(sp.sympify(res_str) - expected) == 0


def test_ivp_via_parameters(solver: ODESecondOrderConstantCoeffSolver):
    """Test providing initial conditions through request parameters."""
    req = ProblemRequest(
        raw_input="y'' + 5*y' + 6*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
        parameters={"t0": 0, "y0": 2, "v0": 3},
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    expected_sol = 9 * sp.exp(-2 * t) - 7 * sp.exp(-3 * t)
    res_str = res.final_result.split("=", 1)[1].strip()
    assert sp.simplify(sp.sympify(res_str) - expected_sol) == 0


def test_reported_problem_square_root_preservation_and_ivp(solver: ODESecondOrderConstantCoeffSolver):
    r"""Regression test for Reported Issue A:

    2y'' + y' - 4y = 0, y(0) = 0, y'(0) = 1.
    Tests:
    - Delta = 33
    - Roots r1, r2 with radical \sqrt{33}
    - Exact constants C1 = 2*sqrt(33)/33, C2 = -2*sqrt(33)/33
    - Symbolic solution identity
    - Initial conditions y(0) = 0, y'(0) = 1
    - ODE residual identically 0
    - LaTeX preserves \sqrt{33} in roots, derivative, system, particular solution, final latex
    - MathML rendering contains <msqrt>
    """
    from math_app.rendering.text_math_renderer import render_math_in_text_html

    req = ProblemRequest(
        raw_input="2*y'' + y' - 4*y = 0, y(0) = 0, y'(0) = 1",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="t",
    )
    res = solver.solve(req)

    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    t = sp.Symbol("t")
    # Expected particular solution: 2*sqrt(33)/33 * (e^(sqrt(33)*t/2) - 1) * e^(-(1+sqrt(33))*t/4)
    expected_sol = (2 * sp.sqrt(33) / 33) * (sp.exp(sp.sqrt(33) * t / 2) - 1) * sp.exp(-(1 + sp.sqrt(33)) * t / 4)

    res_str = res.final_result.split("=", 1)[1].strip()
    parsed_sol = sp.sympify(res_str)
    assert sp.simplify(parsed_sol - expected_sol) == 0

    # 1. Verify initial conditions
    assert sp.simplify(parsed_sol.subs(t, 0)) == 0
    d_sol = sp.diff(parsed_sol, t)
    assert sp.simplify(d_sol.subs(t, 0)) == 1

    # 2. Verify ODE residual identically zero
    d2_sol = sp.diff(d_sol, t)
    residual = sp.simplify(2 * d2_sol + d_sol - 4 * parsed_sol)
    assert residual == 0

    # 3. Verify final LaTeX preserves \sqrt{33}
    assert r"\sqrt{33}" in res.final_latex

    # 4. Verify derivation steps contain square root radicals and proper equations
    step_titles = [s.title for s in res.steps]
    assert any("phương trình đặc trưng" in t_str.lower() for t_str in step_titles)
    assert any("delta" in t_str.lower() for t_str in step_titles)
    assert any("hai nghiệm thực phân biệt" in t_str.lower() for t_str in step_titles)
    assert any("nghiệm tổng quát" in t_str.lower() for t_str in step_titles)
    assert any("đạo hàm" in t_str.lower() for t_str in step_titles)
    assert any("hệ phương trình" in t_str.lower() for t_str in step_titles)
    assert any("nghiệm riêng" in t_str.lower() for t_str in step_titles)
    assert any("kiểm chứng" in t_str.lower() for t_str in step_titles)

    # 5. Check equation LaTeX in specific steps for radical preservation
    # Step 3: roots
    step_roots = next(s for s in res.steps if "hai nghiệm thực phân biệt" in s.title.lower())
    assert r"\sqrt{33}" in step_roots.equation_latex
    assert r"\Delta" in step_roots.equation_latex or "33" in step_roots.equation_latex

    # Step 5: derivative
    step_deriv = next(s for s in res.steps if "đạo hàm cấp một" in s.title.lower())
    assert r"\sqrt{33}" in step_deriv.equation_latex

    # Step 6: system
    step_sys = next(s for s in res.steps if "hệ phương trình" in s.title.lower())
    assert r"\sqrt{33}" in step_sys.equation_latex
    assert "C_1 + C_2 = 0" in step_sys.equation_latex

    # Step 7: particular solution
    step_part = next(s for s in res.steps if "nghiệm riêng" in s.title.lower())
    assert r"\sqrt{33}" in step_part.equation_latex

    # 6. Verify HTML rendering produces valid MathML with radical tags
    html_desc = render_math_in_text_html(step_roots.description)
    assert "<msqrt>" in html_desc
    assert "33" in html_desc

    html_sys = render_math_in_text_html(step_sys.description)
    assert "<math" in html_sys


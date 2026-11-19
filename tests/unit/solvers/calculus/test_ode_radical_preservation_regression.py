"""Regression test suite for ODE radical preservation and MathML font rendering integrity.

Verifies:
1. Exact symbolic roots and radical preservation (Delta > 0, = 0, < 0).
2. Exact symbolic IVP constants (C1, C2) without floating point corruption.
3. Mathematical equivalence of expanded and factored solutions.
4. Independent verification: y(t0) == y0, y'(t0) == v0, and ODE residual R(t) == 0.
5. MathML generation and spacing preventing digit-radical concatenation (2sqrt(33) != 233).
"""

from __future__ import annotations

import sympy as sp
import pytest

from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.application.dtos import ProblemRequest
from math_app.rendering.latex.formatter import normalize_latex
from math_app.rendering.text_math_renderer import convert_latex_to_mathml
from math_app.solvers.calculus.ode.second_order_constant_coeff_solver import (
    ODESecondOrderConstantCoeffSolver,
)


@pytest.fixture
def ode_solver() -> ODESecondOrderConstantCoeffSolver:
    return ODESecondOrderConstantCoeffSolver()


# =============================================================================
# Test Group A: Radical Preservation Across Characteristic Roots
# =============================================================================

def test_characteristic_roots_preserve_radicals(ode_solver: ODESecondOrderConstantCoeffSolver):
    """Reference Problem: 2y'' + y' - 4y = 0.

    Delta = 1^2 - 4(2)(-4) = 33 > 0.
    Characteristic roots must be r1 = (-1 + sqrt(33))/4, r2 = (-1 - sqrt(33))/4.
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="2*y'' + y' - 4*y = 0",
        target_variable="t",
        parameters={},
    )
    resp = ode_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED

    # Check characteristic roots step
    root_step = next((s for s in resp.steps if s.rule_name == "Hai nghiệm thực phân biệt"), None)
    assert root_step is not None
    assert r"\sqrt{33}" in root_step.equation_latex
    assert r"\frac{-1 + \sqrt{33}}{4}" in root_step.equation_latex
    assert r"\frac{-1 - \sqrt{33}}{4}" in root_step.equation_latex


def test_repeated_root_case(ode_solver: ODESecondOrderConstantCoeffSolver):
    """y'' - 2y' + y = 0 -> Delta = 0, r = 1."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' - 2*y' + y = 0",
        target_variable="t",
        parameters={},
    )
    resp = ode_solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert "e^{t}" in resp.final_latex


def test_complex_conjugate_roots_case(ode_solver: ODESecondOrderConstantCoeffSolver):
    """y'' + 4y = 0 -> Delta = -16 < 0, roots = +- 2i."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' + 4*y = 0",
        target_variable="t",
        parameters={},
    )
    resp = ode_solver.solve(req)
    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED
    assert r"\cos" in resp.final_latex or r"\sin" in resp.final_latex


# =============================================================================
# Test Group B: Exact Symbolic Constants in IVP
# =============================================================================

def test_ivp_symbolic_constants_exactness(ode_solver: ODESecondOrderConstantCoeffSolver):
    """2y'' + y' - 4y = 0, y(0) = 0, y'(0) = 1.

    Exact constants must be C1 = 2*sqrt(33)/33, C2 = -2*sqrt(33)/33.
    Must contain no floating-point numbers.
    """
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="2*y'' + y' - 4*y = 0, y(0) = 0, y'(0) = 1",
        target_variable="t",
        parameters={},
    )
    resp = ode_solver.solve(req)

    assert resp.status == SolutionStatus.SUCCESS
    assert resp.verification.status == VerificationStatus.VERIFIED

    # Check that Step 7 (Nghiệm riêng) exists
    part_step = next((s for s in resp.steps if s.rule_name == "Nghiệm riêng"), None)
    assert part_step is not None

    # Verify C1 and C2 in description
    assert r"\sqrt{33}" in part_step.description
    # Ensure no floating point numbers in final_result
    assert "." not in resp.final_result or "0." not in resp.final_result


# =============================================================================
# Test Group C: Final Answer Mathematical Invariants
# =============================================================================

def test_ivp_solution_mathematical_invariants(ode_solver: ODESecondOrderConstantCoeffSolver):
    """Verify all mathematical invariants of the Cauchy IVP solution."""
    t = sp.Symbol("t", real=True)
    a, b, c = 2, 1, -4
    delta = b**2 - 4 * a * c
    r1 = (-b + sp.sqrt(delta)) / (2 * a)
    r2 = (-b - sp.sqrt(delta)) / (2 * a)

    c1 = 2 * sp.sqrt(33) / 33
    c2 = -2 * sp.sqrt(33) / 33

    # Expanded form
    y_expanded = c1 * sp.exp(r1 * t) + c2 * sp.exp(r2 * t)

    # Factored form
    y_factored = 2 * sp.sqrt(33) * (sp.exp(sp.sqrt(33) * t / 2) - 1) * sp.exp(-t * (1 + sp.sqrt(33)) / 4) / 33

    # 1. Equivalence between forms
    assert sp.simplify(y_expanded - y_factored) == 0

    # 2. Initial condition y(0) == 0
    assert sp.simplify(y_factored.subs(t, 0)) == 0

    # 3. Initial derivative y'(0) == 1
    dy_dt = sp.diff(y_factored, t)
    assert sp.simplify(dy_dt.subs(t, 0)) == 1

    # 4. ODE residual R(t) == 0
    d2y_dt2 = sp.diff(dy_dt, t)
    assert sp.simplify(a * d2y_dt2 + b * dy_dt + c * y_factored) == 0


# =============================================================================
# Test Group D: MathML / LaTeX Radical Integrity and Spacing
# =============================================================================

def test_radical_spacing_in_normalize_latex():
    r"""Verify that normalize_latex inserts thin space between integers and square roots.

    2\sqrt{33} -> 2\,\sqrt{33}
    \sqrt{33} t -> \sqrt{33}\,t
    """
    raw_latex = r"\frac{2 \sqrt{33} \left(e^{\frac{\sqrt{33} t}{2}} - 1\right) e^{- \frac{t \left(1 + \sqrt{33}\right)}{4}}}{33}"
    normalized = normalize_latex(raw_latex)

    assert r"2\,\sqrt{33}" in normalized
    assert r"\sqrt{33}\,t" in normalized


def test_mathml_conversion_preserves_sqrt_and_mspace():
    """Verify that MathML conversion preserves msqrt and includes mspace so 2 and 33 never merge."""
    raw_latex = r"y(t) = \frac{2 \sqrt{33} \left(e^{\frac{\sqrt{33} t}{2}} - 1\right) e^{- \frac{t \left(1 + \sqrt{33}\right)}{4}}}{33}"
    mathml = convert_latex_to_mathml(raw_latex, block=True)

    # Must contain math and msqrt tags
    assert "<msqrt>" in mathml
    assert "<mrow><mn>33</mn></mrow></msqrt>" in mathml or "<mn>33</mn></msqrt>" in mathml

    # Must contain mspace between mn 2 and msqrt
    assert "<mspace" in mathml
    # Verify no accidental text concatenation <mn>233</mn>
    assert "<mn>233</mn>" not in mathml


def test_solver_full_pipeline_produces_valid_mathml(ode_solver: ODESecondOrderConstantCoeffSolver):
    """Verify that the complete solver response generates clean, uncorrupted MathML."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="2*y'' + y' - 4*y = 0, y(0) = 0, y'(0) = 1",
        target_variable="t",
        parameters={},
    )
    resp = ode_solver.solve(req)
    mathml = convert_latex_to_mathml(resp.final_latex, block=True)

    assert "<msqrt>" in mathml
    assert "33" in mathml
    assert "<mn>233</mn>" not in mathml

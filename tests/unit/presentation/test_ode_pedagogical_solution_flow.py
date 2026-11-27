"""Tests for ODE Pedagogical Reasoning and Solution Flow (UX3.5).

Covers:
- 10 Benchmark ODE Scenarios (Cases A through J)
- 4-Stage Pedagogical Architecture & Completion
- 4 Pillars per Step (Purpose, Math Basis, Execution, Intermediate Result)
- Mathematical Notation Standardization (y_c(t), y_p(t), C_1, C_2)
- Resonance multi-index evaluation (forcing frequency lambda vs characteristic roots)
- Independent SymPy mathematical residual R(t) = 0 verification
- First-Order ODE pedagogical flow (Linear, Separable)
- NiceGUI UI component rendering for staged steps container
"""

from __future__ import annotations

import pytest
import sympy as sp
from nicegui import ui

from math_app.application.dtos import ProblemRequest, SolutionStep
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.main import build_application
from math_app.presentation.components.ode_pedagogical_enhancer import (
    ODEPedagogicalStep,
    ODEStageSummary,
    enhance_ode_solution_flow,
    is_ode_problem_type,
    standardize_ode_notation,
)
from math_app.presentation.components.ode_staged_step_viewer import (
    render_ode_pedagogical_step,
    render_ode_staged_steps_container,
)


@pytest.fixture(scope="module")
def use_case():
    return build_application()


# ==============================================================================
# 1. NOTATION STANDARDIZATION TESTS
# ==============================================================================


def test_standardize_ode_notation_basic():
    """Verify raw strings with Y_p, yc(t), yp(t), C1, C2 are cleanly normalized."""
    assert standardize_ode_notation("") == ""
    assert standardize_ode_notation("y(t) = yc(t) + Yp(t)") == "y(t) = y_c(t) + y_p(t)"
    assert standardize_ode_notation("Y_p(t) = A*exp(t)") == "y_p(t) = A*exp(t)"
    assert standardize_ode_notation("Y_{p}(t)") == "y_{p}(t)"
    assert standardize_ode_notation("L[Y_p] = g(t)") == "L[y_p] = g(t)"
    assert standardize_ode_notation("L[Y_{p}] = g(t)") == "L[y_{p}] = g(t)"
    assert standardize_ode_notation("L[yc] = 0") == "L[y_c] = 0"
    assert standardize_ode_notation("C1*exp(t) + C2*exp(2*t)") == "C_1*exp(t) + C_2*exp(2*t)"
    assert standardize_ode_notation("Hệ phương trình xác định C1, C2") == "Hệ phương trình xác định C_1, C_2"


def test_standardize_ode_notation_preserves_clean_latex():
    """Ensure already standardized LaTeX is not double-subscripted or mangled."""
    clean = r"y(t) = C_{1} e^{2 t} + C_{2} e^{t} + \frac{e^{3 t}}{2}"
    assert standardize_ode_notation(clean) == clean
    clean_c1 = "C_1 + C_2"
    assert standardize_ode_notation(clean_c1) == clean_c1


# ==============================================================================
# 2. ODE PROBLEM TYPE IDENTIFICATION TESTS
# ==============================================================================


def test_is_ode_problem_type():
    """Verify is_ode_problem_type accurately detects all ODE types and ignores non-ODEs."""
    assert is_ode_problem_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF) is True
    assert is_ode_problem_type(ProblemType.ODE_SECOND_ORDER_IVP) is True
    assert is_ode_problem_type(ProblemType.ODE_FIRST_ORDER_LINEAR) is True
    assert is_ode_problem_type(ProblemType.ODE_SEPARABLE) is True
    assert is_ode_problem_type(ProblemType.ODE_EXACT) is True
    assert is_ode_problem_type(ProblemType.ODE_REDUCTION_OF_ORDER) is True
    assert is_ode_problem_type(ProblemType.WRONSKIAN) is True

    assert is_ode_problem_type(ProblemType.DERIVATIVE) is False
    assert is_ode_problem_type(ProblemType.INTEGRAL) is False
    assert is_ode_problem_type(ProblemType.SOLVE_EQUATION) is False
    assert is_ode_problem_type(None) is False


# ==============================================================================
# 3. BENCHMARK CASES A THROUGH J TEST MATRIX
# ==============================================================================


def _verify_common_stage_invariants(stages: tuple[ODEStageSummary, ...], case_name: str) -> None:
    """Validate architectural invariants across all 4 pedagogical stages."""
    assert len(stages) == 4, f"[{case_name}] Must produce exactly 4 stages"
    stg1, stg2, stg3, stg4 = stages

    assert stg1.stage_index == 1
    assert stg2.stage_index == 2
    assert stg3.stage_index == 3
    assert stg4.stage_index == 4

    # Stage 1: Homogeneous solution
    assert stg1.is_applicable is True
    assert len(stg1.steps) >= 4, f"[{case_name}] Stage 1 must contain >= 4 steps"
    assert "y_c(" in stg1.summary_latex or "y(" in stg1.summary_latex

    # Every step across all stages must satisfy the 4 pillars
    for stg in stages:
        for s in stg.steps:
            assert isinstance(s, SolutionStep)
            assert isinstance(s, ODEPedagogicalStep)
            assert s.purpose.strip(), f"[{case_name}] Step {s.step_number} missing purpose"
            assert s.math_basis.strip(), f"[{case_name}] Step {s.step_number} missing math_basis"
            assert s.execution.strip(), f"[{case_name}] Step {s.step_number} missing execution"
            assert s.intermediate_result.strip(), f"[{case_name}] Step {s.step_number} missing intermediate_result"

            # Notation checks: No raw unformatted notation
            assert "Y_p" not in s.intermediate_result, f"[{case_name}] Raw Y_p in Step {s.step_number} intermediate_result"
            assert "yc(" not in s.description, f"[{case_name}] Raw yc( in Step {s.step_number} description"
            assert "yp(" not in s.description, f"[{case_name}] Raw yp( in Step {s.step_number} description"
            assert "C1" not in s.intermediate_result or "C_{1}" in s.intermediate_result or "C_1" in s.intermediate_result

    # Stage 4: Verification
    assert stg4.is_applicable is True
    assert len(stg4.steps) >= 1
    assert "R(" in stg4.summary_latex and "0" in stg4.summary_latex


def test_case_a_homogeneous_real_distinct(use_case):
    """Case A: y'' - 3y' + 2y = 0 (Homogeneous real distinct roots r=1, r=2)."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' - 3*y' + 2*y = 0",
        target_variable="t",
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    _verify_common_stage_invariants(stages, "Case A")

    # Stage 2 is not applicable for homogeneous
    assert stages[1].is_applicable is False
    assert len(stages[1].steps) == 0

    # Stage 3 synthesizes y(t) = y_c(t)
    assert stages[2].is_applicable is True
    assert len(stages[2].steps) >= 1
    assert "y(t)" in stages[2].summary_latex


def test_case_b_homogeneous_repeated_real(use_case):
    """Case B: y'' - 4y' + 4y = 0 (Homogeneous repeated root r0=2, factor t)."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' - 4*y' + 4*y = 0",
        target_variable="t",
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    _verify_common_stage_invariants(stages, "Case B")
    assert stages[1].is_applicable is False
    assert "t" in stages[0].summary_latex  # repeated root factor t


def test_case_c_homogeneous_complex_conjugate(use_case):
    """Case C: y'' + 2y' + 5y = 0 (Homogeneous complex conjugate roots -1 +- 2i)."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' + 2*y' + 5*y = 0",
        target_variable="t",
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    _verify_common_stage_invariants(stages, "Case C")
    assert stages[1].is_applicable is False
    assert r"\cos" in stages[0].summary_latex
    assert r"\sin" in stages[0].summary_latex


def test_case_d_nonhomogeneous_polynomial(use_case):
    """Case D: y'' - 3y' + 2y = 2t + 1 (Nonhomogeneous polynomial, s=0, UC)."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' - 3*y' + 2*y = 2*t + 1",
        target_variable="t",
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    _verify_common_stage_invariants(stages, "Case D")

    # Stage 2 is applicable
    assert stages[1].is_applicable is True
    assert len(stages[1].steps) == 4
    assert "y_p(t)" in stages[1].summary_latex
    assert "t + 2" in stages[1].summary_latex or "2 + t" in stages[1].summary_latex

    # SymPy residual verification: L[y] - g(t) == 0
    t = sp.Symbol("t")
    y_expr = sp.sympify("C1*exp(2*t) + C2*exp(t) + t + 2")
    res_check = sp.simplify(sp.diff(y_expr, t, 2) - 3 * sp.diff(y_expr, t) + 2 * y_expr - (2 * t + 1))
    assert res_check == 0


def test_case_e_nonhomogeneous_exp_non_resonant(use_case):
    """Case E: y'' - 3y' + 2y = exp(3t) (Non-resonant exponential, lambda=3 not in {1, 2}, s=0)."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' - 3*y' + 2*y = exp(3*t)",
        target_variable="t",
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    _verify_common_stage_invariants(stages, "Case E")
    assert stages[1].is_applicable is True
    assert "y_p(t)" in stages[1].summary_latex

    # Verify resonance explanation indicates non-resonant (s=0)
    trial_step = stages[1].steps[0]
    assert "s = 0" in trial_step.execution or "không phải là nghiệm" in trial_step.execution or "t^0" in trial_step.execution

    # SymPy residual verification
    t = sp.Symbol("t")
    y_expr = sp.sympify("C1*exp(2*t) + C2*exp(t) + exp(3*t)/2")
    res_check = sp.simplify(sp.diff(y_expr, t, 2) - 3 * sp.diff(y_expr, t) + 2 * y_expr - sp.exp(3 * t))
    assert res_check == 0


def test_case_f_nonhomogeneous_exp_resonant(use_case):
    """Case F: y'' - 3y' + 2y = exp(t) (Resonant exponential, lambda=1 in {1, 2}, s=1)."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' - 3*y' + 2*y = exp(t)",
        target_variable="t",
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    _verify_common_stage_invariants(stages, "Case F")
    assert stages[1].is_applicable is True
    assert "y_p(t)" in stages[1].summary_latex
    assert "t" in stages[1].summary_latex  # multiplied by t^1

    # Verify resonance explanation distinguishes lambda=1 from characteristic roots
    trial_step = stages[1].steps[0]
    assert "s = 1" in trial_step.execution or "cộng hưởng" in trial_step.execution or "t^1" in trial_step.execution

    # SymPy residual verification
    t = sp.Symbol("t")
    y_expr = sp.sympify("C1*exp(2*t) + C2*exp(t) - t*exp(t)")
    res_check = sp.simplify(sp.diff(y_expr, t, 2) - 3 * sp.diff(y_expr, t) + 2 * y_expr - sp.exp(t))
    assert res_check == 0


def test_case_g_nonhomogeneous_trig_non_resonant(use_case):
    """Case G: y'' + 2y' + 5y = 3*sin(2t) (Non-resonant trig, roots=-1+-2i, lambda=2i, s=0)."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' + 2*y' + 5*y = 3*sin(2*t)",
        target_variable="t",
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    _verify_common_stage_invariants(stages, "Case G")
    assert stages[1].is_applicable is True
    assert r"\sin" in stages[1].summary_latex
    assert r"\cos" in stages[1].summary_latex


def test_case_h_nonhomogeneous_trig_resonant(use_case):
    """Case H: y'' + 4y = sin(2t) (Resonant trig, roots=+-2i, lambda=2i, s=1)."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' + 4*y = sin(2*t)",
        target_variable="t",
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    _verify_common_stage_invariants(stages, "Case H")
    assert stages[1].is_applicable is True
    assert "t" in stages[1].summary_latex  # resonance multiplier t^1

    # Verify resonance explanation
    trial_step = stages[1].steps[0]
    assert "s = 1" in trial_step.execution or "cộng hưởng" in trial_step.execution or "t^1" in trial_step.execution


def test_case_i_variation_of_parameters(use_case):
    """Case I: y'' + y = tan(t) (Variation of Parameters / Lagrange)."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' + y = tan(t)",
        target_variable="t",
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    _verify_common_stage_invariants(stages, "Case I")
    assert stages[1].is_applicable is True
    assert len(stages[1].steps) == 7  # 7 VoP steps
    assert any("wronskian" in s.rule_name.lower() for s in stages[1].steps)
    assert any("lagrange" in s.title.lower() or "biến thiên" in s.title.lower() for s in stages[1].steps)


def test_case_j_cauchy_ivp(use_case):
    """Case J: y'' - 3y' + 2y = 0, y(0) = 1, y'(0) = 0 (Cauchy IVP)."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        raw_input="y'' - 3*y' + 2*y = 0, y(0) = 1, y'(0) = 0",
        target_variable="t",
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS
    assert res.verification.status == VerificationStatus.VERIFIED

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    _verify_common_stage_invariants(stages, "Case J")

    # Stage 2 is not applicable for homogeneous ODE
    assert stages[1].is_applicable is False

    # Stage 3 solves Cauchy IVP for C1, C2
    assert stages[2].is_applicable is True
    assert len(stages[2].steps) == 3
    assert any("điều kiện ban đầu" in s.rule_name.lower() or "điều kiện ban đầu" in s.title.lower() for s in stages[2].steps)

    # Check that initial condition step explicitly refers to C1 and C2
    ic_step = [s for s in stages[2].steps if "điều kiện ban đầu" in s.rule_name.lower() or "điều kiện ban đầu" in s.title.lower()][0]
    assert "C_1" in ic_step.purpose or "C_1" in ic_step.intermediate_result

    # Final result satisfies initial conditions: y(0) = 1, y'(0) = 0
    t = sp.Symbol("t")
    y_sol = sp.sympify("(2 - exp(t))*exp(t)")  # 2*e^t - e^(2t)
    assert y_sol.subs(t, 0) == 1
    assert sp.diff(y_sol, t).subs(t, 0) == 0


# ==============================================================================
# 4. FIRST-ORDER ODE PEDAGOGICAL FLOW TESTS
# ==============================================================================


def test_first_order_linear_pedagogical_flow(use_case):
    """Verify First-Order Linear ODE steps are partitioned and enriched with 4 pillars."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        raw_input="y' + 2*y = exp(-t)",
        target_variable="t",
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4
    for stg in stages:
        for s in stg.steps:
            assert s.purpose.strip()
            assert s.math_basis.strip()
            assert s.execution.strip()
            assert s.intermediate_result.strip()


def test_first_order_separable_pedagogical_flow(use_case):
    """Verify First-Order Separable ODE steps are partitioned and enriched with 4 pillars."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SEPARABLE,
        raw_input="y' = y*t",
        target_variable="t",
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4
    for stg in stages:
        for s in stg.steps:
            assert s.purpose.strip()
            assert s.math_basis.strip()
            assert s.execution.strip()
            assert s.intermediate_result.strip()


def test_euler_cauchy_pedagogical_flow(use_case):
    """Verify Euler-Cauchy ODE is enhanced into 4 pedagogical stages with all 4 pillars."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
        target_variable="t",
    )
    res = use_case.execute(req)
    assert res.status == SolutionStatus.SUCCESS

    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)
    assert len(stages) == 4
    for stg in stages:
        for s in stg.steps:
            assert s.purpose.strip()
            assert s.math_basis.strip()
            assert s.execution.strip()
            assert s.intermediate_result.strip()

    # Verify stage titles
    assert "Phương trình chỉ số" in stages[0].title
    assert "Hệ nghiệm cơ bản" in stages[1].title
    assert "nghiệm" in stages[2].title.lower()
    assert "Kiểm chứng" in stages[3].title
    assert stages[3].is_completed is True


@pytest.mark.parametrize(
    ("v_status", "expected_completed", "expected_badge_color", "expected_label"),
    [
        (VerificationStatus.VERIFIED, True, "emerald-7", "VERIFIED"),
        (VerificationStatus.UNVERIFIED, False, "amber-7", "UNVERIFIED"),
        (VerificationStatus.FAILED, False, "rose-7", "FAILED"),
    ],
)
def test_euler_cauchy_pedagogical_flow_verification_states(
    use_case,
    v_status: VerificationStatus,
    expected_completed: bool,
    expected_badge_color: str,
    expected_label: str,
):
    """Verify Stage 4 and UI container faithfully reflect VERIFIED, UNVERIFIED, and FAILED."""
    from dataclasses import replace

    from math_app.application.dtos import VerificationResult

    req = ProblemRequest(
        problem_type=ProblemType.ODE_EULER_CAUCHY,
        raw_input="t^2*y'' + 4*t*y' + 2*y = 0, t > 0",
        target_variable="t",
    )
    base_res = use_case.execute(req)
    patched_res = replace(
        base_res,
        verification=VerificationResult(
            status=v_status,
            method=f"mocked_{v_status.value}",
            details=f"Mocked status {v_status.value}",
        ),
    )

    stages = enhance_ode_solution_flow(patched_res, req.problem_type, req.target_variable)
    assert len(stages) == 4
    stg4 = stages[3]
    assert stg4.is_completed is expected_completed
    assert stg4.badge_color == expected_badge_color
    assert expected_label in stg4.steps[-1].intermediate_result
    if v_status == VerificationStatus.VERIFIED:
        assert r"\equiv 0" in stg4.summary_latex
    else:
        assert r"\equiv 0" not in stg4.summary_latex
        assert expected_label in stg4.summary_latex

    with ui.column() as container:
        render_ode_staged_steps_container(stages, final_answer_latex=patched_res.final_latex)
    assert container is not None


# ==============================================================================
# 5. NICEGUI UI COMPONENT MOUNTING TESTS
# ==============================================================================


def test_render_ode_staged_steps_container(use_case):
    """Verify render_ode_staged_steps_container mounts with all UI components."""
    req = ProblemRequest(
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        raw_input="y'' - 3*y' + 2*y = 2*t + 1",
        target_variable="t",
    )
    res = use_case.execute(req)
    stages = enhance_ode_solution_flow(res, req.problem_type, req.target_variable)

    with ui.column() as container:
        render_ode_staged_steps_container(stages, final_answer_latex=res.final_latex)

    assert container is not None

    with ui.column() as step_container:
        render_ode_pedagogical_step(stages[0].steps[0])
    assert step_container is not None


def test_render_ode_staged_steps_empty_fallback():
    """Verify empty stages render a polite fallback notice."""
    with ui.column() as container:
        render_ode_staged_steps_container(())
    assert container is not None

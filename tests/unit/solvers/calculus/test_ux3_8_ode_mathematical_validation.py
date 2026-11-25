"""UX3.8 — End-to-End ODE Mathematical Validation & Regression Test Suite.

Covers:
- Category A: Standard first-order linear, separable, classical homogeneous, exact, integrating factor (general & negative-domain IVPs)
- Category B: Mandatory degenerate/singular Cauchy cases 1-5, branch extension resolution (B6-B11), ordinary-point IVP across singularity boundaries, T03 regression
- Category C: Non-elementary integrals and complex-polar branch safety
- Category D: Second-order constant-coefficient (homogeneous via verifier, nonhomogeneous UC/VoP), reduction of order (auto negative interval & IVP verification), Wronskian Peano counterexamples
- Category E: Adversarial & domain-boundary rejection, verifier fail-closed guarantees, SolveProblemUseCase DTO field preservation, and Clean Architecture / E2E UI-state-to-MathML consistency
"""

from __future__ import annotations

import pathlib
import time
import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionResponse, VerificationResult
from math_app.application.ports.solver import Solver
from math_app.application.registry import DefaultSolverRegistry
from math_app.application.use_cases.solve_problem import SolveProblemUseCase
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.input.ode_parser import parse_wronskian_input
from math_app.main import build_application
from math_app.presentation.components.ode_pedagogical_enhancer import enhance_ode_solution_flow
from math_app.presentation.components.problem_statement import format_final_answer_latex
from math_app.presentation.components.workspace.ode.ode_state import (
    ODEClassification,
    ODEMode,
    ODEOrder,
    ODEState,
)
from math_app.rendering.text_math_renderer import convert_latex_to_mathml
from math_app.solvers.calculus.ode.classical_homogeneous_solver import ODEClassicalHomogeneousSolver
from math_app.solvers.calculus.ode.exact_solver import ODEExactSolver
from math_app.solvers.calculus.ode.integrating_factor_solver import ODEIntegratingFactorSolver
from math_app.solvers.calculus.ode.linear_solver import ODELinearSolver
from math_app.solvers.calculus.ode.reduction_of_order_solver import ODEReductionOfOrderSolver
from math_app.solvers.calculus.ode.second_order_constant_coeff_solver import ODESecondOrderConstantCoeffSolver
from math_app.solvers.calculus.ode.separable_solver import ODESeparableSolver
from math_app.solvers.calculus.ode.wronskian_solver import WronskianSolver
from math_app.verification.calculus.ode_verifier import ODEVerifier


def _use_case() -> SolveProblemUseCase:
    return build_application()


# =============================================================================
# Category A: Standard & Negative-Domain First-Order ODEs
# =============================================================================


def test_cat_a_linear_negative_domain_real_logs_and_fractional_powers():
    """Negative-t linear IVPs must compute strictly real antiderivatives without I*pi or imaginary sqrt."""
    uc = _use_case()

    # t*y' - y = t, y(-1) = 1 => y(t) = t*(ln(-t) - 1) on (-oo, 0)
    r1 = uc.execute(ProblemRequest("t*y' - y = t, y(-1) = 1", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
    assert r1.status == SolutionStatus.SUCCESS
    assert r1.verification.status == VerificationStatus.PARTIALLY_VERIFIED
    assert "I" not in r1.final_result
    t = sp.Symbol("t", negative=True)
    y_neg = sp.sympify(r1.branch_solutions[0].expression).subs(sp.Symbol("t"), t)
    assert sp.simplify(t * sp.diff(y_neg, t) - y_neg - t) == 0
    assert sp.simplify(y_neg.subs(t, -1) - 1) == 0

    # y' + 1/(2*t)*y = 1, y(-1) = 2 => y(t) = 2*t/3 + 8/(3*sqrt(-t)) on (-oo, 0)
    r2 = uc.execute(ProblemRequest("y' + 1/(2*t)*y = 1, y(-1) = 2", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
    assert r2.status == SolutionStatus.SUCCESS
    assert r2.verification.status == VerificationStatus.PARTIALLY_VERIFIED
    assert "I" not in r2.final_result
    y2_neg = sp.sympify(r2.branch_solutions[0].expression).subs(sp.Symbol("t"), t)
    assert sp.simplify(sp.diff(y2_neg, t) + y2_neg / (2 * t) - 1) == 0
    assert sp.simplify(y2_neg.subs(t, -1) - 2) == 0


def test_cat_a_separable_negative_domain_real_solutions():
    """Separable ODEs on t < 0 must stay real with log(|t|) / sqrt(|t|) instead of dropping branches."""
    ss = ODESeparableSolver()

    # y' = y/(2*t), y(-1) = 2 => y(t) = 2*sqrt(|t|)
    r_ivp = ss.solve(ProblemRequest("y' = y/(2*t), y(-1) = 2", ProblemType.ODE_SEPARABLE, "t"))
    assert r_ivp.status == SolutionStatus.SUCCESS
    assert r_ivp.verification.status == VerificationStatus.VERIFIED
    assert "sqrt(Abs(t))" in r_ivp.final_result
    assert "I" not in r_ivp.final_result

    # General y' = y/(2*t) => C*sqrt(|t|) plus equilibrium y = 0, both verified cleanly
    r_gen = ss.solve(ProblemRequest("y' = y/(2*t)", ProblemType.ODE_SEPARABLE, "t"))
    assert r_gen.status == SolutionStatus.SUCCESS
    assert r_gen.verification.status == VerificationStatus.VERIFIED
    assert "y = 0" in r_gen.final_result

    # Conic separable y' = 1/(t*y), y(-1) = 2 => y^2/2 = log(|t|) + 2
    r_conic = ss.solve(ProblemRequest("y' = 1/(t*y), y(-1) = 2", ProblemType.ODE_SEPARABLE, "t"))
    assert r_conic.status == SolutionStatus.SUCCESS
    assert r_conic.verification.status == VerificationStatus.VERIFIED
    assert "I" not in r_conic.final_result


def test_cat_a_classical_homogeneous_lhs_product_form():
    """x*y' = y + x must normalize F(y/x) cleanly during explicit verification (not pass x*y_prime)."""
    hom = ODEClassicalHomogeneousSolver()
    r = hom.solve(ProblemRequest("x*y' = y + x", ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS, "x"))
    assert r.status == SolutionStatus.SUCCESS
    assert r.verification.status == VerificationStatus.VERIFIED
    assert "log(Abs(x))" in r.final_result


def test_cat_a_exact_and_integrating_factor_negative_branch_no_complex_leak():
    """Exact and Integrating Factor IVPs at negative log arguments must produce real potentials (no I*pi)."""
    ex = ODEExactSolver()
    r_ex = ex.solve(ProblemRequest("(1/(x - 1))*dx + dy = 0, y(0) = 1", ProblemType.ODE_EXACT, "x"))
    assert r_ex.status == SolutionStatus.SUCCESS
    assert r_ex.verification.status == VerificationStatus.VERIFIED
    assert "I*pi" not in r_ex.final_result and "Abs(x - 1)" in r_ex.final_result

    iff = ODEIntegratingFactorSolver()
    r_if = iff.solve(ProblemRequest("(1/x)*dx + dy = 0, y(-1) = 1", ProblemType.ODE_INTEGRATING_FACTOR, "x"))
    assert r_if.status == SolutionStatus.SUCCESS
    assert r_if.verification.status == VerificationStatus.VERIFIED
    assert "I*pi" not in r_if.final_result and "Abs(x)" in r_if.final_result

    # Existing positive/general integrating factor behavior preserved cleanly
    r_if_gen = iff.solve(ProblemRequest("y*dx + (2*x*y - exp(-2*y))*dy = 0", ProblemType.ODE_INTEGRATING_FACTOR, "x"))
    assert r_if_gen.status == SolutionStatus.SUCCESS
    assert r_if_gen.verification.status == VerificationStatus.VERIFIED
    assert "log(y)" in r_if_gen.final_result


# =============================================================================
# Category B: Mandatory Singular Cauchy Matrix + T03 + Branch Extensions
# =============================================================================


def test_cat_b_mandatory_five_singular_cauchy_cases():
    """Validate all 5 mandatory singular Cauchy classification cases."""
    uc = _use_case()

    r1 = uc.execute(ProblemRequest("t*y' = t, y(0) = 5", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
    assert r1.status == SolutionStatus.SUCCESS
    assert r1.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED
    assert "t + 5" in r1.final_result

    r2 = uc.execute(ProblemRequest("x*y' + 2*x*y = 0, y(0) = 1", ProblemType.ODE_FIRST_ORDER_LINEAR, "x"))
    assert r2.status == SolutionStatus.SUCCESS
    assert r2.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED
    assert "exp(-2*x)" in r2.final_result

    r3 = uc.execute(ProblemRequest("x*y' = 1, y(0) = 5", ProblemType.ODE_FIRST_ORDER_LINEAR, "x"))
    assert r3.status == SolutionStatus.INVALID_INPUT

    r4 = uc.execute(ProblemRequest("x*y' + y = 0, y(0) = 1", ProblemType.ODE_FIRST_ORDER_LINEAR, "x"))
    assert r4.status == SolutionStatus.INVALID_INPUT

    r5 = uc.execute(ProblemRequest("t*y' + t*y = t, y(0) = 5", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
    assert r5.status == SolutionStatus.SUCCESS
    assert r5.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED
    assert sp.simplify(sp.sympify(r5.final_result.split("=")[1].strip()) - (1 + 4 * sp.exp(-sp.Symbol("t")))) == 0


def test_cat_b_singular_extension_unique_constant_and_honest_reporting():
    """Singular Cauchy with pole cancellation must substitute unique constant (y=t/3) and never claim unverified text."""
    ls = ODELinearSolver()

    # B8: t*y' + 2*y = t, y(0) = 0 => C1 = 0, C2 = 0 => unique C1 solution y(t) = t/3
    r_b8 = ls.solve(ProblemRequest("t*y' + 2*y = t, y(0) = 0", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
    assert r_b8.status == SolutionStatus.SUCCESS
    assert r_b8.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED
    assert r_b8.final_result.strip() == "y(t) = t/3"
    assert "C_{1}" not in r_b8.final_latex
    assert "chưa được chứng minh" not in r_b8.final_result

    # B9: t*y' - 2*y = t^2, y(0) = 0 => genuine infinite C1 family with real log(-t) / log(t)
    r_b9 = ls.solve(ProblemRequest("t*y' - 2*y = t^2, y(0) = 0", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
    assert r_b9.status == SolutionStatus.SUCCESS
    assert r_b9.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED
    assert "I*pi" not in r_b9.final_result
    assert "chưa được chứng minh" not in r_b9.final_result


def test_cat_b_ordinary_ivp_with_singular_boundary_blowup_stays_verified_on_branch():
    """(t - 3)*y' + y = 0, y(1) = 2 is valid on (-oo, 3); blowup at boundary t=3 must not fail the IVP."""
    ls = ODELinearSolver()
    r = ls.solve(ProblemRequest("(t - 3)*y' + y = 0, y(1) = 2", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
    assert r.status == SolutionStatus.SUCCESS
    assert r.verification.status == VerificationStatus.PARTIALLY_VERIFIED
    assert "-4/(t - 3)" in r.final_result


def test_cat_b_three_branch_rational_extension_completes_quickly():
    """(t^2 - 1)*y' + 2*t*y = t must cancel 0/0 terms before limits and finish fast without hanging."""
    ls = ODELinearSolver()
    t0 = time.perf_counter()
    r = ls.solve(ProblemRequest("(t^2 - 1)*y' + 2*t*y = t", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0
    assert r.status == SolutionStatus.SUCCESS
    assert r.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED


def test_cat_b_t03_regression_full_matrix():
    """Verify full T03 (t - 3)*y' + ln(t)*y = 2*t matrix (general, left/right IVPs, invalid/singular ICs)."""
    uc = _use_case()

    r_gen = uc.execute(ProblemRequest("(t - 3)*y' + ln(t)*y = 2*t", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
    assert r_gen.status == SolutionStatus.SUCCESS
    assert r_gen.verification.status == VerificationStatus.PARTIALLY_VERIFIED
    assert "(0, +\\infty)" in r_gen.original_domain_latex

    r_left = uc.execute(ProblemRequest("(t - 3)*y' + ln(t)*y = 2*t, y(1) = 0", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
    assert r_left.status == SolutionStatus.SUCCESS
    assert r_left.verification.status == VerificationStatus.PARTIALLY_VERIFIED

    r_right = uc.execute(ProblemRequest("(t - 3)*y' + ln(t)*y = 2*t, y(4) = 5", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
    assert r_right.status == SolutionStatus.SUCCESS
    assert r_right.verification.status == VerificationStatus.PARTIALLY_VERIFIED

    r_bad = uc.execute(ProblemRequest("(t - 3)*y' + ln(t)*y = 2*t, y(3) = 1", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
    assert r_bad.status == SolutionStatus.INVALID_INPUT

    r_compat = uc.execute(ProblemRequest("(t - 3)*y' + ln(t)*y = 2*t, y(3) = 6/ln(3)", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
    assert r_compat.status == SolutionStatus.UNVERIFIED
    assert r_compat.verification.status == VerificationStatus.UNVERIFIED


# =============================================================================
# Category C: Non-Elementary Integrals & Complex-Polar Branch Safety
# =============================================================================


def test_cat_c_non_elementary_and_polar_branch_handling():
    """Exact solver must not emit complex exp_polar discrepancy; erf/Ci real integrals remain verified."""
    ex = ODEExactSolver()

    r_polar = ex.solve(ProblemRequest("exp(x^3)*dx + dy = 0", ProblemType.ODE_EXACT, "x"))
    assert r_polar.status == SolutionStatus.CANNOT_SOLVE
    assert r_polar.verification.status == VerificationStatus.NOT_APPLICABLE
    assert "exp_polar" not in r_polar.final_result

    r_erf = ex.solve(ProblemRequest("exp(-x^2)*dx + dy = 0", ProblemType.ODE_EXACT, "x"))
    assert r_erf.status == SolutionStatus.SUCCESS
    assert r_erf.verification.status == VerificationStatus.VERIFIED
    assert "erf(x)" in r_erf.final_result


# =============================================================================
# Category D: Second-Order Constant Coeff, Reduction of Order & Wronskian
# =============================================================================


def test_cat_d_second_order_homogeneous_uses_verifier_cleanly():
    """Homogeneous second-order IVP must verify through ODEVerifier and preserve domain/status integrity."""
    so = ODESecondOrderConstantCoeffSolver()
    r = so.solve(
        ProblemRequest(
            "y'' + 4*y = 0, y(0) = 0, y'(0) = 2",
            ProblemType.ODE_SECOND_ORDER_IVP,
            "t",
            parameters={"expected_classification": "HOMOGENEOUS", "problem_mode": "CAUCHY_IVP"},
        )
    )
    assert r.status == SolutionStatus.SUCCESS
    assert r.verification.status == VerificationStatus.VERIFIED
    t = sp.Symbol("t")
    assert sp.simplify(sp.sympify(r.final_result.split("=")[1].strip()) - sp.sin(2 * t)) == 0


def test_cat_d_reduction_of_order_negative_ivp_and_verification():
    """RO IVP with t0 < 0 and singularity at 0 must infer real t < 0 branch cleanly and verify both ICs."""
    ro = ODEReductionOfOrderSolver()
    r = ro.solve(
        ProblemRequest(
            "2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t, y(-1) = 2, y'(-1) = 1",
            ProblemType.ODE_REDUCTION_OF_ORDER,
            "t",
        )
    )
    assert r.status == SolutionStatus.SUCCESS
    assert r.verification.status == VerificationStatus.VERIFIED
    assert "I" not in r.final_result
    t = sp.Symbol("t", negative=True)
    y_expr = sp.sympify(r.final_result.split("=")[1].strip()).subs(sp.Symbol("t"), t)
    assert sp.simplify(2 * t**2 * sp.diff(y_expr, t, 2) + 3 * t * sp.diff(y_expr, t) - y_expr) == 0
    assert sp.simplify(y_expr.subs(t, -1) - 2) == 0
    assert sp.simplify(sp.diff(y_expr, t).subs(t, -1) - 1) == 0


def test_cat_d_wronskian_peano_counterexamples_and_parser_contract():
    """Peano pairs t^2, t*|t| must yield W === 0 and UNVERIFIED; parser preserves plain variable equality."""
    y1, y2, var = parse_wronskian_input("cos(t), sin(t)", target_variable="t")
    assert var == sp.Symbol("t")

    ws = WronskianSolver()
    for pair in ("t^2, t*abs(t)", "(t-1)^2, (t-1)*abs(t-1)"):
        rw = ws.solve(ProblemRequest(pair, ProblemType.WRONSKIAN, "t"))
        assert rw.status == SolutionStatus.UNVERIFIED
        assert rw.verification.status == VerificationStatus.UNVERIFIED
        assert rw.final_result == "W(y1, y2)(t) = 0"

    rind = ws.solve(ProblemRequest("cos(t), sin(t)", ProblemType.WRONSKIAN, "t"))
    assert rind.status == SolutionStatus.SUCCESS
    assert rind.verification.status == VerificationStatus.VERIFIED


# =============================================================================
# Category E & Phase C: Adversarial Rejections, Verifier Fail-Closed, DTO & E2E
# =============================================================================


def test_cat_e_integrating_factor_rejects_singular_or_zero_ic_and_verifier_blocks_zoo():
    """IF solver & verifier must never pass zoo, nan, unexpected I, or mu(x0, y0) == 0."""
    iff = ODEIntegratingFactorSolver()

    r_sing = iff.solve(ProblemRequest("y*dx - x*dy = 0, y(0) = 1", ProblemType.ODE_INTEGRATING_FACTOR, "x"))
    assert r_sing.status == SolutionStatus.INVALID_INPUT

    r_mu_pole = iff.solve(
        ProblemRequest("y*dx + (2*x*y - exp(-2*y))*dy = 0, y(1) = 0", ProblemType.ODE_INTEGRATING_FACTOR, "x")
    )
    assert r_mu_pole.status == SolutionStatus.CANNOT_SOLVE
    assert r_mu_pole.verification.status == VerificationStatus.NOT_APPLICABLE

    r_deg = iff.solve(ProblemRequest("2*y*dx + x*dy = 0, y(0) = 1", ProblemType.ODE_INTEGRATING_FACTOR, "x"))
    assert r_deg.status == SolutionStatus.INVALID_INPUT

    # Verifier defense-in-depth checks
    v = ODEVerifier()
    x, y, t = sp.symbols("x y t")
    assert v.verify_exact(sp.log(x) + y, 1 / x, sp.Integer(1), x, y, initial_condition=(sp.Integer(-1), sp.Integer(1))).status == VerificationStatus.FAILED
    assert v.verify_integrating_factor(x * sp.exp(2 * y) - sp.log(y), sp.exp(2 * y) / y, y, 2 * x * y - sp.exp(-2 * y), x, y, initial_condition=(sp.Integer(1), sp.Integer(0))).status == VerificationStatus.FAILED
    assert v.verify_second_order(-sp.I * t**(sp.Rational(3, 2)), t, sp.Integer(1), sp.Integer(0), sp.Integer(0)).status == VerificationStatus.FAILED


class _FastStubSolver(Solver):
    """Top-level stub solver (picklable for isolated subprocess timeout test)."""

    def can_solve(self, request: ProblemRequest) -> bool:
        return request.problem_type == ProblemType.ODE_FIRST_ORDER_LINEAR

    def solve(self, request: ProblemRequest) -> SolutionResponse:
        return SolutionResponse(
            status=SolutionStatus.SUCCESS,
            verification=VerificationResult(VerificationStatus.VERIFIED, "stub", "ok"),
            raw_input=request.raw_input,
            canonical_input=request.raw_input,
            final_result="y(t) = t",
            final_latex="y(t) = t",
            original_domain_latex=r"\mathcal{D}_{\text{orig}} = \mathbb{R}",
            normalized_domain_latex=r"\mathcal{D}_{\text{norm}} = (0, +\infty)",
            execution_time_ms=0.0,
        )


def test_phase_c_use_case_preserves_domain_latex_when_execution_time_zero():
    """SolveProblemUseCase must preserve original_domain_latex & normalized_domain_latex when elapsed is filled."""
    reg = DefaultSolverRegistry()
    reg.register(ProblemType.ODE_FIRST_ORDER_LINEAR, _FastStubSolver())
    for timeout_val in (None, 5.0):
        uc = SolveProblemUseCase(registry=reg, default_timeout=timeout_val)
        resp = uc.execute(ProblemRequest("y' = 1", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
        assert resp.execution_time_ms > 0.0
        assert resp.original_domain_latex == r"\mathcal{D}_{\text{orig}} = \mathbb{R}"
        assert resp.normalized_domain_latex == r"\mathcal{D}_{\text{norm}} = (0, +\infty)"


def test_phase_c_e2e_ui_state_to_mathml_and_clean_architecture_boundary():
    """Verify full ODEState -> SolveProblemUseCase -> LaTeX formatter -> Enhancer -> MathML & layer boundary."""
    uc = _use_case()

    for eq, ic, cls, expected_status, expected_verif in (
        ("t*y' = t", "y(0) = 5", ODEClassification.FIRST_ORDER_LINEAR, SolutionStatus.SUCCESS, VerificationStatus.C1_EXTENSION_VERIFIED),
        ("(t - 3)*y' + ln(t)*y = 2*t", "y(1) = 0", ODEClassification.FIRST_ORDER_LINEAR, SolutionStatus.SUCCESS, VerificationStatus.PARTIALLY_VERIFIED),
    ):
        state = ODEState(
            order=ODEOrder.FIRST_ORDER,
            classification=cls,
            mode=ODEMode.CAUCHY_IVP,
            equation=eq,
            initial_condition=ic,
            target_var="t",
        )
        req = state.build_problem_request()
        resp = uc.execute(req)
        assert resp.status == expected_status
        assert resp.verification.status == expected_verif
        formatted = format_final_answer_latex(resp.final_latex, req.problem_type, req.target_variable, dict(req.parameters))
        assert formatted
        mathml = convert_latex_to_mathml(formatted)
        assert "<math" in mathml
        stages = enhance_ode_solution_flow(resp, req.problem_type, target_var=req.target_variable, params=dict(req.parameters))
        assert len(stages) >= 3

    # Verify Clean Architecture independence of domain, input, application, solvers, verification from UI/Plotly
    src_root = pathlib.Path(__file__).resolve().parents[4] / "src" / "math_app"
    for layer in ("domain", "input", "application", "solvers", "verification"):
        for py_file in (src_root / layer).rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "nicegui" not in content, f"UI leakage in {py_file}"
            assert "plotly" not in content, f"Plot library leakage in {py_file}"
            assert "math_app.presentation" not in content, f"Presentation dependency in {py_file}"

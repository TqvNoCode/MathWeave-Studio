"""Curated 24-Case Homogeneous ODE Acceptance Benchmark.

This benchmark establishes a definitive acceptance dataset covering representative
first-order and second-order differential equations across all supported solvers
in MathWeave Studio.

Pipeline evaluated:
    Input -> Parser -> Classification -> Solver -> Verification -> SolutionResponse

Structure:
    - 12 First-Order Cases (ODE-FO-01 to ODE-FO-12)
    - 12 Second-Order Cases (ODE-SO-13 to ODE-SO-24)

Every valid case requires:
    - End-to-end execution through SolveProblemUseCase (build_application()).
    - SolutionStatus.SUCCESS and VerificationStatus.VERIFIED.
    - Independent symbolic verification of original ODE residuals on stated domains.
    - Independent verification of initial conditions and domain restrictions.

Every invalid/unsupported case requires:
    - Explicit rejection (INVALID_INPUT or CANNOT_SOLVE).
    - VerificationStatus NEVER equals VERIFIED.
"""

from dataclasses import dataclass
from typing import Callable

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest, SolutionResponse
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.main import build_application
from math_app.verification.calculus.ode_verifier import _prove_symbolic_zero


@dataclass(frozen=True)
class AcceptanceCase:
    case_id: str
    name: str
    raw_input: str
    problem_type: ProblemType
    target_variable: str
    expected_method: str
    expected_result_type: str  # "explicit", "implicit", "equilibrium", "invalid_input", "unsupported"
    expected_domain: str
    is_valid: bool
    reference_derivation: str
    custom_symbolic_check: Callable[[SolutionResponse], bool] | None = None


# ------------------------------------------------------------------------------
# 24 Curated Benchmark Cases
# ------------------------------------------------------------------------------

BENCHMARK_CASES: list[AcceptanceCase] = [
    # --------------------------------------------------------------------------
    # FIRST-ORDER CASES (12 Cases)
    # --------------------------------------------------------------------------
    AcceptanceCase(
        case_id="ODE-FO-01",
        name="Separable linear-in-y equation",
        raw_input="y' = 2*x*y",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
        expected_method="Separable variables integration",
        expected_result_type="explicit",
        expected_domain="x in (-oo, oo)",
        is_valid=True,
        reference_derivation=(
            "dy/y = 2x dx => ln|y| = x^2 + C_0 => y(x) = C * exp(x^2). "
            "Residual: d/dx(C*exp(x^2)) - 2x*(C*exp(x^2)) = 0."
        ),
        custom_symbolic_check=lambda res: (
            "exp(x**2)" in res.final_result or "exp(x^2)" in res.final_latex
        ),
    ),
    AcceptanceCase(
        case_id="ODE-FO-02",
        name="Logistic separable equation",
        raw_input="y' = y*(1 - y)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
        expected_method="Separable partial fractions",
        expected_result_type="explicit",
        expected_domain="R \\ {x : 1 + C*exp(x) = 0}",
        is_valid=True,
        reference_derivation=(
            "dy/[y(1-y)] = dx => ln|y/(1-y)| = x + C => y(x) = C*exp(x)/(1 + C*exp(x)). "
            "Equilibrium solutions: y = 0, y = 1."
        ),
        custom_symbolic_check=lambda res: (
            "0" in res.final_result and "1" in res.final_result
        ),
    ),
    AcceptanceCase(
        case_id="ODE-FO-03",
        name="Separable equation with equilibrium solutions",
        raw_input="y' = y^2 - 4",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
        expected_method="Separable integration with equilibrium detection",
        expected_result_type="equilibrium",
        expected_domain="R \\ {roots of denominator}",
        is_valid=True,
        reference_derivation=(
            "y^2 - 4 = 0 => y = 2, y = -2 are constant equilibria. "
            "Residual for y = +-2: d/dx(+-2) - ((+-2)^2 - 4) = 0 - 0 = 0."
        ),
        custom_symbolic_check=lambda res: (
            "2" in res.final_result and "-2" in res.final_result
        ),
    ),
    AcceptanceCase(
        case_id="ODE-FO-04",
        name="Multiple real derivative branches",
        raw_input="(y')^2 = 4*y, y(1) = 4",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
        expected_method="Branch decomposition into y' = +2*sqrt(y) and y' = -2*sqrt(y)",
        expected_result_type="explicit",
        expected_domain="Connected intervals containing x0 = 1",
        is_valid=True,
        reference_derivation=(
            "Branch 1 (y' = +2*sqrt(y)): sqrt(y) = x + 1 => y_1(x) = (x+1)^2. "
            "Branch 2 (y' = -2*sqrt(y)): sqrt(y) = 3 - x => y_2(x) = (3-x)^2. "
            "Both satisfy (y')^2 = 4y and y(1) = 4."
        ),
        custom_symbolic_check=lambda res: (
            len(res.branch_solutions) == 2
            and all(b.verification.status == VerificationStatus.VERIFIED for b in res.branch_solutions)
        ),
    ),
    AcceptanceCase(
        case_id="ODE-FO-05",
        name="First-order linear homogeneous equation",
        raw_input="y' + 3*x^2*y = 0",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
        expected_method="Linear integrating factor mu(x) = exp(x^3)",
        expected_result_type="explicit",
        expected_domain="x in (-oo, oo)",
        is_valid=True,
        reference_derivation=(
            "mu(x) = exp(int 3x^2 dx) = exp(x^3). y(x) = C * exp(-x^3). "
            "Residual: d/dx(C*exp(-x^3)) + 3x^2*(C*exp(-x^3)) = -3x^2*C*exp(-x^3) + 3x^2*C*exp(-x^3) = 0."
        ),
        custom_symbolic_check=lambda res: (
            "exp(-x**3)" in res.final_result or "exp(-x^3)" in res.final_latex
        ),
    ),
    AcceptanceCase(
        case_id="ODE-FO-06",
        name="First-order linear homogeneous IVP",
        raw_input="y' - 2*x*y = 0, y(0) = 5",
        problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
        target_variable="x",
        expected_method="Linear IVP integrating factor with C determination",
        expected_result_type="explicit",
        expected_domain="x in (-oo, oo)",
        is_valid=True,
        reference_derivation=(
            "y(x) = C * exp(x^2). y(0) = 5 => C = 5 => y(x) = 5 * exp(x^2). "
            "Residual: 10x*exp(x^2) - 2x*(5*exp(x^2)) = 0."
        ),
        custom_symbolic_check=lambda res: (
            "5*exp(x**2)" in res.final_result or "5" in res.final_result
        ),
    ),
    AcceptanceCase(
        case_id="ODE-FO-07",
        name="Exact differential equation",
        raw_input="(2*x + y) + (x + 2*y)*y' = 0",
        problem_type=ProblemType.ODE_EXACT,
        target_variable="x",
        expected_method="Potential function Phi(x, y) = C",
        expected_result_type="implicit",
        expected_domain="R^2",
        is_valid=True,
        reference_derivation=(
            "M = 2x + y, N = x + 2y. dM/dy = 1 = dN/dx = 1 (Exact). "
            "Phi(x, y) = x^2 + x*y + y^2 = C."
        ),
        custom_symbolic_check=lambda res: (
            "x**2 + x*y + y**2" in res.final_result or "x^2 + x y + y^2" in res.final_latex
        ),
    ),
    AcceptanceCase(
        case_id="ODE-FO-08",
        name="Integrating-factor method using an existing supported example",
        raw_input="(3*x*y + y^2)*dx + (x^2 + x*y)*dy = 0",
        problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
        target_variable="x",
        expected_method="Integrating factor mu(x) = x",
        expected_result_type="implicit",
        expected_domain="x != 0",
        is_valid=True,
        reference_derivation=(
            "(M_y - N_x)/N = (x+y)/(x*(x+y)) = 1/x => mu(x) = x. "
            "Transformed: (3x^2*y + x*y^2)dx + (x^3 + x^2*y)dy = 0. "
            "Potential: Phi(x, y) = x^3*y + x^2*y^2/2 = C."
        ),
        custom_symbolic_check=lambda res: (
            "x**3*y" in res.final_result and "x**2*y**2/2" in res.final_result
        ),
    ),
    AcceptanceCase(
        case_id="ODE-FO-09",
        name="Classical homogeneous equation y' = y/x",
        raw_input="y' = y/x",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
        expected_method="Substitution v = y/x, F(v) - v = 0",
        expected_result_type="explicit",
        expected_domain="x in (0, oo) or x in (-oo, 0)",
        is_valid=True,
        reference_derivation=(
            "F(v) = v => F(v) - v = 0 => x*v' = 0 => v = C => y(x) = C*x. "
            "Residual: d/dx(C*x) - (C*x)/x = C - C = 0."
        ),
        custom_symbolic_check=lambda res: (
            "C*x" in res.final_result or "x*C" in res.final_result
        ),
    ),
    AcceptanceCase(
        case_id="ODE-FO-10",
        name="Classical homogeneous equation with nontrivial F(y/x)",
        raw_input="y' = y/x + x^2/(3*y^2)",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
        expected_method="Substitution v = y/x, odd-root conservative inversion",
        expected_result_type="explicit",
        expected_domain="x != 0, y != 0",
        is_valid=True,
        reference_derivation=(
            "v = y/x => x*v' = 1/(3v^2) => 3v^2 dv = dx/x => v^3 = ln|x| + C. "
            "Two real branches: y_1 = x*(ln|x| + C)^(1/3) and y_2 = -x*(-ln|x| - C)^(1/3)."
        ),
        custom_symbolic_check=lambda res: (
            len(res.branch_solutions) == 2
            and all(b.verification.status == VerificationStatus.VERIFIED for b in res.branch_solutions)
        ),
    ),
    AcceptanceCase(
        case_id="ODE-FO-11",
        name="Periodic trigonometric equilibrium family",
        raw_input="y' = sin(2*y)",
        problem_type=ProblemType.ODE_SEPARABLE,
        target_variable="x",
        expected_method="Periodic root detection on integer lattice Z",
        expected_result_type="equilibrium",
        expected_domain="y in R",
        is_valid=True,
        reference_derivation=(
            "sin(2y) = 0 <=> 2y = n*pi <=> y = n*pi/2 for n in Z. "
            "Representatives: 0, pi/2, -pi/2."
        ),
        custom_symbolic_check=lambda res: (
            "n*pi / 2" in res.final_result or "pi" in res.final_result
        ),
    ),
    AcceptanceCase(
        case_id="ODE-FO-12",
        name="Invalid IVP at an original domain singularity",
        raw_input="y' = y/x, y(0) = 1",
        problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        target_variable="x",
        expected_method="Domain pre-validation against singular base point",
        expected_result_type="invalid_input",
        expected_domain="Empty (x0 = 0 is singular)",
        is_valid=False,
        reference_derivation=(
            "RHS f(x, y) = y/x is not defined at x0 = 0. "
            "By Picard-Lindelof, no continuous or differentiable solution exists."
        ),
    ),
    # --------------------------------------------------------------------------
    # SECOND-ORDER CASES (12 Cases)
    # --------------------------------------------------------------------------
    AcceptanceCase(
        case_id="ODE-SO-13",
        name="Distinct real characteristic roots",
        raw_input="y'' - 5*y' + 6*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="x",
        expected_method="Characteristic roots r = 2, 3",
        expected_result_type="explicit",
        expected_domain="x in (-oo, oo)",
        is_valid=True,
        reference_derivation=(
            "r^2 - 5r + 6 = (r - 2)(r - 3) = 0 => r1 = 2, r2 = 3. "
            "y(x) = C_1*exp(2x) + C_2*exp(3x). "
            "Residual: (4C1*e^(2x)+9C2*e^(3x)) - 5(2C1*e^(2x)+3C2*e^(3x)) + 6(C1*e^(2x)+C2*e^(3x)) = 0."
        ),
        custom_symbolic_check=lambda res: (
            "exp(2*x)" in res.final_result and "exp(3*x)" in res.final_result
        ),
    ),
    AcceptanceCase(
        case_id="ODE-SO-14",
        name="Repeated real characteristic root",
        raw_input="y'' - 4*y' + 4*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="x",
        expected_method="Characteristic root r = 2 (multiplicity 2)",
        expected_result_type="explicit",
        expected_domain="x in (-oo, oo)",
        is_valid=True,
        reference_derivation=(
            "r^2 - 4r + 4 = (r - 2)^2 = 0 => r = 2. "
            "y(x) = (C_1 + C_2*x)*exp(2x)."
        ),
        custom_symbolic_check=lambda res: (
            "exp(2*x)" in res.final_result and "x" in res.final_result
        ),
    ),
    AcceptanceCase(
        case_id="ODE-SO-15",
        name="Complex conjugate characteristic roots",
        raw_input="y'' + 4*y = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        target_variable="x",
        expected_method="Characteristic roots r = +- 2i",
        expected_result_type="explicit",
        expected_domain="x in (-oo, oo)",
        is_valid=True,
        reference_derivation=(
            "r^2 + 4 = 0 => r = +- 2i. "
            "y(x) = C_1*cos(2x) + C_2*sin(2x)."
        ),
        custom_symbolic_check=lambda res: (
            "cos(2*x)" in res.final_result and "sin(2*x)" in res.final_result
        ),
    ),
    AcceptanceCase(
        case_id="ODE-SO-16",
        name="Cauchy IVP with distinct roots",
        raw_input="y'' - 5*y' + 6*y = 0, y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="x",
        expected_method="Characteristic roots r = 2, 3 with linear system for C1, C2",
        expected_result_type="explicit",
        expected_domain="x in (-oo, oo)",
        is_valid=True,
        reference_derivation=(
            "y = C1*e^(2x) + C2*e^(3x). y(0) = C1 + C2 = 1. "
            "y'(0) = 2C1 + 3C2 = 0 => C1 = 3, C2 = -2. "
            "y(x) = 3*exp(2x) - 2*exp(3x)."
        ),
        custom_symbolic_check=lambda res: _prove_symbolic_zero(
            sp.parse_expr(res.final_result.split("=")[-1].strip()) - (3 * sp.exp(2 * sp.Symbol("x")) - 2 * sp.exp(3 * sp.Symbol("x"))),
            variable=sp.Symbol("x"),
        ),
    ),
    AcceptanceCase(
        case_id="ODE-SO-17",
        name="Cauchy IVP with repeated roots",
        raw_input="y'' - 4*y' + 4*y = 0, y(0) = 1, y'(0) = 2",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="x",
        expected_method="Characteristic root r = 2 with IVP determination",
        expected_result_type="explicit",
        expected_domain="x in (-oo, oo)",
        is_valid=True,
        reference_derivation=(
            "y = (C1 + C2*x)*e^(2x). y(0) = C1 = 1. "
            "y'(0) = C2 + 2C1 = 2 => C2 = 0 => y(x) = exp(2x)."
        ),
        custom_symbolic_check=lambda res: _prove_symbolic_zero(
            sp.parse_expr(res.final_result.split("=")[-1].strip()) - sp.exp(2 * sp.Symbol("x")),
            variable=sp.Symbol("x"),
        ),
    ),
    AcceptanceCase(
        case_id="ODE-SO-18",
        name="Cauchy IVP with complex roots",
        raw_input="y'' + 4*y = 0, y(0) = 1, y'(0) = 2",
        problem_type=ProblemType.ODE_SECOND_ORDER_IVP,
        target_variable="x",
        expected_method="Harmonic oscillator with IVP determination",
        expected_result_type="explicit",
        expected_domain="x in (-oo, oo)",
        is_valid=True,
        reference_derivation=(
            "y = C1*cos(2x) + C2*sin(2x). y(0) = C1 = 1. "
            "y'(0) = 2C2 = 2 => C2 = 1 => y(x) = cos(2x) + sin(2x)."
        ),
        custom_symbolic_check=lambda res: _prove_symbolic_zero(
            sp.parse_expr(res.final_result.split("=")[-1].strip()) - (sp.cos(2 * sp.Symbol("x")) + sp.sin(2 * sp.Symbol("x"))),
            variable=sp.Symbol("x"),
        ),
    ),
    AcceptanceCase(
        case_id="ODE-SO-19",
        name="Reduction of Order with a valid known solution",
        raw_input="2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
        expected_method="Reduction of Order via Abel integral formula",
        expected_result_type="explicit",
        expected_domain="t != 0",
        is_valid=True,
        reference_derivation=(
            "P(t) = 3/(2t). exp(-int P dt)/y1^2 = t^(1/2). "
            "v(t) = 2/3 * t^(3/2) => y2(t) = (1/t)*(2/3 * t^(3/2)) = 2/3 * sqrt(t). "
            "y(t) = C1*(1/t) + C2*sqrt(t)."
        ),
        custom_symbolic_check=lambda res: (
            "1/t" in res.final_result and ("sqrt(t)" in res.final_result or "t**(1/2)" in res.final_result)
        ),
    ),
    AcceptanceCase(
        case_id="ODE-SO-20",
        name="Reduction of Order with an invalid known solution",
        raw_input="2*t^2*y'' + 3*t*y' - y = 0, y1 = exp(t)",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
        expected_method="Validation that y1 satisfies the differential equation",
        expected_result_type="invalid_input",
        expected_domain="None",
        is_valid=False,
        reference_derivation=(
            "Substitute y1 = exp(t): 2t^2*exp(t) + 3t*exp(t) - exp(t) = (2t^2 + 3t - 1)*exp(t) != 0. "
            "The candidate y1 is not a solution; must be rejected."
        ),
    ),
    AcceptanceCase(
        case_id="ODE-SO-21",
        name="Euler-Cauchy equation on x > 0",
        raw_input="2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t, t > 0",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
        expected_method="Reduction of Order on strictly positive interval t > 0",
        expected_result_type="explicit",
        expected_domain="t in (0, oo)",
        is_valid=True,
        reference_derivation=(
            "For t > 0, |t| = t. y2(t) = sqrt(t). "
            "Residual: 2t^2*(-1/(4*t^(3/2))) + 3t*(1/(2*sqrt(t))) - sqrt(t) = -1/2*sqrt(t) + 3/2*sqrt(t) - sqrt(t) = 0."
        ),
        custom_symbolic_check=lambda res: (
            "sqrt(t)" in res.final_result or "t**(1/2)" in res.final_result
        ),
    ),
    AcceptanceCase(
        case_id="ODE-SO-22",
        name="Euler-Cauchy equation on x < 0",
        raw_input="2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t, t < 0",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
        expected_method="Reduction of Order on strictly negative interval t < 0",
        expected_result_type="explicit",
        expected_domain="t in (-oo, 0)",
        is_valid=True,
        reference_derivation=(
            "For t < 0, |t| = -t. y2(t) = sqrt(-t). "
            "Residual on t < 0 is identically zero."
        ),
        custom_symbolic_check=lambda res: (
            "sqrt(-t)" in res.final_result or "(-t)**(1/2)" in res.final_result
        ),
    ),
    AcceptanceCase(
        case_id="ODE-SO-23",
        name="Wronskian independence for two solutions of a common ODE",
        raw_input="y1 = exp(2*x), y2 = exp(3*x)",
        problem_type=ProblemType.WRONSKIAN,
        target_variable="x",
        expected_method="Wronskian determinant W(y1, y2) = y1*y2' - y1'*y2",
        expected_result_type="explicit",
        expected_domain="x in (-oo, oo)",
        is_valid=True,
        reference_derivation=(
            "W(x) = exp(2x)*3*exp(3x) - 2*exp(2x)*exp(3x) = exp(5x) != 0 for all x. "
            "Since W(x) is never zero, {exp(2x), exp(3x)} forms a fundamental solution set."
        ),
        custom_symbolic_check=lambda res: (
            "exp(5*x)" in res.final_result
        ),
    ),
    AcceptanceCase(
        case_id="ODE-SO-24",
        name="Invalid Cauchy initial point at a singularity",
        raw_input="2*t^2*y'' + 3*t*y' - y = 0, y1 = 1/t, y(0) = 1, y'(0) = 0",
        problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
        target_variable="t",
        expected_method="Leading coefficient singularity check",
        expected_result_type="invalid_input",
        expected_domain="Empty (t0 = 0 is a regular singular point)",
        is_valid=False,
        reference_derivation=(
            "a2(t) = 2t^2 vanishes at t0 = 0. "
            "Normal form y'' + (3/(2t))y' - (1/(2t^2))y = 0 has a singularity at t=0. "
            "Picard-Lindelof theorem does not hold; IVP at t0 = 0 must be rejected."
        ),
    ),
]


def verify_case_independently(case: AcceptanceCase, res: SolutionResponse) -> None:
    """Perform independent symbolic ODE residual, IC, gradient, method, and domain checks."""
    cid = case.case_id

    # 1. Check result type contract
    if case.expected_result_type == "explicit":
        assert "=" in res.final_result or res.branch_solutions, f"{cid}: expected explicit equation."
    elif case.expected_result_type == "implicit":
        assert "=" in res.final_result, f"{cid}: expected implicit equation."
    elif case.expected_result_type == "equilibrium":
        assert any(k in res.final_result for k in ("=", "y =", "Nghiệm")), f"{cid}: expected equilibrium."
    elif case.expected_result_type == "invalid_input":
        assert res.status == SolutionStatus.INVALID_INPUT, f"{cid}: expected INVALID_INPUT."
        return

    # 2. Check expected_method
    step_rules = [s.rule_name for s in res.steps]
    if cid in ("ODE-FO-01", "ODE-FO-02", "ODE-FO-03", "ODE-FO-04", "ODE-FO-11"):
        assert any("Phân tách biến số" in r for r in step_rules), f"{cid}: expected separable integration method."
    elif cid in ("ODE-FO-05", "ODE-FO-06"):
        assert any("Thừa số tích phân" in r for r in step_rules), f"{cid}: expected linear integrating factor method."
    elif cid == "ODE-FO-07":
        assert any("vi phân toàn phần" in r for r in step_rules), f"{cid}: expected exact potential method."
    elif cid == "ODE-FO-08":
        assert any("Thừa số tích phân mu(x)" in r for r in step_rules), f"{cid}: expected integrating factor method."
    elif cid in ("ODE-FO-09", "ODE-FO-10"):
        assert any("v = y/x" in r for r in step_rules), f"{cid}: expected classical homogeneous substitution method."
    elif cid in ("ODE-SO-13", "ODE-SO-14", "ODE-SO-15", "ODE-SO-16", "ODE-SO-17", "ODE-SO-18"):
        assert any("Phương trình đặc trưng" in r for r in step_rules), f"{cid}: expected characteristic roots method."
    elif cid in ("ODE-SO-19", "ODE-SO-21", "ODE-SO-22"):
        assert any("hạ bậc" in r.lower() for r in step_rules), f"{cid}: expected reduction of order method."
    elif cid == "ODE-SO-23":
        assert any("Wronskian" in r for r in step_rules), f"{cid}: expected Wronskian determinant method."

    # 3. Check expected_domain metadata
    if cid == "ODE-FO-04":
        assert all(b.domain_interval is not None for b in res.branch_solutions), f"{cid}: missing domain interval."
    elif cid == "ODE-FO-08":
        assert any("x" in r and "0" in r for r in res.domain_restrictions), f"{cid}: missing domain restriction x != 0."
    elif cid == "ODE-FO-09":
        assert any("x" in r and "0" in r for r in res.domain_restrictions), f"{cid}: missing domain restriction x != 0."
        assert res.branch_solutions[0].domain_interval in ((0, sp.oo), (-sp.oo, 0)), f"{cid}: invalid branch domain interval."
    elif cid == "ODE-FO-10":
        assert any("exp(-C)" in r for r in res.domain_restrictions), f"{cid}: missing domain restriction for exp(-C)."
    elif cid == "ODE-SO-19":
        assert any("t" in r and "0" in r for r in res.domain_restrictions), f"{cid}: missing domain restriction t != 0."
    elif cid == "ODE-SO-21":
        assert any("> 0" in r or ">0" in r for r in res.domain_restrictions), f"{cid}: missing domain restriction t > 0."
    elif cid == "ODE-SO-22":
        assert any("< 0" in r or "<0" in r for r in res.domain_restrictions), f"{cid}: missing domain restriction t < 0."

    # 4. Case-specific independent mathematical checks comparing actual solver results against references
    x = sp.Symbol("x")
    t = sp.Symbol("t")
    y = sp.Symbol("y")
    c = sp.Symbol("C")
    c1 = sp.Symbol("C1")
    c2 = sp.Symbol("C2")

    if cid == "ODE-FO-01":
        # y' = 2xy => actual y(x) = C*exp(x**2)
        act_expr = sp.parse_expr(res.final_result.split(";")[0].split("=")[-1].strip())
        assert _prove_symbolic_zero(act_expr - c * sp.exp(x**2), (c,)), f"{cid}: actual expression does not match C*exp(x^2)."
        res_val = sp.diff(act_expr, x) - 2 * x * act_expr
        assert sp.simplify(res_val) == 0, f"{cid}: actual expression residual failed."

    elif cid == "ODE-FO-02":
        # Logistic y' = y(1-y) => actual y(x) = C*exp(x)/(C*exp(x) + 1)
        act_expr = sp.parse_expr(res.final_result.split(";")[0].split("=")[-1].strip())
        assert _prove_symbolic_zero(act_expr - c * sp.exp(x) / (c * sp.exp(x) + 1), (c,)), f"{cid}: actual expression does not match logistic formula."
        res_val = sp.diff(act_expr, x) - act_expr * (1 - act_expr)
        assert sp.simplify(res_val) == 0, f"{cid}: actual expression residual failed."
        for eq_val in (sp.Integer(0), sp.Integer(1)):
            eq_res = sp.diff(eq_val, x) - eq_val * (1 - eq_val)
            assert eq_res == 0, f"{cid}: equilibrium residual failed for y = {eq_val}."

    elif cid == "ODE-FO-03":
        # y' = y^2 - 4 => equilibria y = 2, y = -2
        assert "y = -2" in res.final_result and "y = 2" in res.final_result, f"{cid}: missing equilibrium solutions."
        for eq_val in (sp.Integer(2), sp.Integer(-2)):
            res_val = sp.diff(eq_val, x) - (eq_val**2 - 4)
            assert res_val == 0, f"{cid}: equilibrium residual failed for y = {eq_val}."

    elif cid == "ODE-FO-04":
        # (y')^2 = 4y, y(1) = 4
        # Separable solver emits two branches:
        # Branch 0: -2*sqrt(y) = 2x - 6 <=> y = (3-x)^2 = (x-3)^2
        # Branch 1: 2*sqrt(y) = 2x + 2 <=> y = (x+1)^2
        assert len(res.branch_solutions) == 2, f"{cid}: expected exactly 2 explicit branches."
        b0, b1 = res.branch_solutions[0], res.branch_solutions[1]

        # Solve actual emitted equations for y and compare against reference expressions
        eq0 = sp.Eq(*[sp.parse_expr(s) for s in b0.solution_str.split("=")])
        eq1 = sp.Eq(*[sp.parse_expr(s) for s in b1.solution_str.split("=")])
        act_b0_y = sp.solve(eq0, y)[0]
        act_b1_y = sp.solve(eq1, y)[0]

        # Compare actual emitted branch expressions against (3-x)**2 and (x+1)**2 allowing algebraic equivalence
        assert _prove_symbolic_zero(act_b0_y - (3 - x)**2), f"{cid}: Branch 0 actual {act_b0_y} does not match (3-x)^2."
        assert _prove_symbolic_zero(act_b1_y - (x + 1)**2), f"{cid}: Branch 1 actual {act_b1_y} does not match (x+1)^2."

        # Independently check both residuals on actual emitted branch expressions
        res0 = sp.simplify(sp.diff(act_b0_y, x)**2 - 4 * act_b0_y)
        res1 = sp.simplify(sp.diff(act_b1_y, x)**2 - 4 * act_b1_y)
        assert res0 == 0, f"{cid}: Branch 0 residual failed."
        assert res1 == 0, f"{cid}: Branch 1 residual failed."

        # Independently check both initial conditions on actual emitted branch expressions
        assert sp.simplify(act_b0_y.subs(x, 1)) == 4, f"{cid}: Branch 0 IC failed at x=1."
        assert sp.simplify(act_b1_y.subs(x, 1)) == 4, f"{cid}: Branch 1 IC failed at x=1."

        # Verify domain intervals contain x0 = 1
        low0, high0 = b0.domain_interval
        low1, high1 = b1.domain_interval
        assert float(sp.N(low0)) <= 1 <= float(sp.N(high0)), f"{cid}: Branch 0 domain does not contain x0=1."
        assert float(sp.N(low1)) <= 1 <= float(sp.N(high1)), f"{cid}: Branch 1 domain does not contain x0=1."

    elif cid == "ODE-FO-05":
        # y' + 3x^2 y = 0 => y = C*exp(-x^3)
        act_expr = sp.parse_expr(res.final_result.split("=")[-1].strip())
        assert _prove_symbolic_zero(act_expr - c * sp.exp(-x**3), (c,)), f"{cid}: actual expression does not match C*exp(-x^3)."
        res_val = sp.diff(act_expr, x) + 3 * x**2 * act_expr
        assert sp.simplify(res_val) == 0, f"{cid}: actual expression residual failed."

    elif cid == "ODE-FO-06":
        # y' - 2xy = 0, y(0) = 5 => y = 5*exp(x^2)
        act_expr = sp.parse_expr(res.final_result.split("=")[-1].strip())
        assert _prove_symbolic_zero(act_expr - 5 * sp.exp(x**2)), f"{cid}: actual expression does not match 5*exp(x^2)."
        res_val = sp.diff(act_expr, x) - 2 * x * act_expr
        assert sp.simplify(res_val) == 0, f"{cid}: actual expression residual failed."
        assert sp.simplify(act_expr.subs(x, 0)) == 5, f"{cid}: initial condition failed."

    elif cid == "ODE-FO-07":
        # Exact: (2x + y) dx + (x + 2y) dy = 0
        # Compare actual returned potential with reference potential up to an additive constant
        act_phi = sp.parse_expr(res.final_result.split("=")[0].strip())
        ref_phi = x**2 + x * y + y**2
        d_phi = sp.simplify(act_phi - ref_phi)
        assert d_phi.is_number and not d_phi.has(x, y), f"{cid}: actual potential differs from reference by non-constant {d_phi}."

        # Verify both gradient identities on the actual returned potential
        assert sp.simplify(sp.diff(act_phi, x) - (2 * x + y)) == 0, f"{cid}: gradient dPhi/dx != M(x, y)."
        assert sp.simplify(sp.diff(act_phi, y) - (x + 2 * y)) == 0, f"{cid}: gradient dPhi/dy != N(x, y)."

    elif cid == "ODE-FO-08":
        # Integrating factor mu(x) = x for (3xy + y^2)dx + (x^2 + xy)dy = 0
        # Compare actual returned potential with reference potential up to an additive constant
        act_phi = sp.parse_expr(res.final_result.split("=")[0].strip())
        ref_phi = x**3 * y + (x**2 * y**2) / 2
        d_phi = sp.simplify(act_phi - ref_phi)
        assert d_phi.is_number and not d_phi.has(x, y), f"{cid}: actual potential differs from reference by non-constant {d_phi}."

        # Verify both gradient identities on the actual returned potential
        mu = x
        assert sp.simplify(sp.diff(act_phi, x) - mu * (3 * x * y + y**2)) == 0, f"{cid}: gradient dPhi/dx != mu*M."
        assert sp.simplify(sp.diff(act_phi, y) - mu * (x**2 + x * y)) == 0, f"{cid}: gradient dPhi/dy != mu*N."

    elif cid == "ODE-FO-09":
        # y' = y/x => compare actual returned expression against C*x
        act_expr = res.branch_solutions[0].expression
        assert _prove_symbolic_zero(act_expr - c * x, (c,)), f"{cid}: actual returned expression {act_expr} does not match C*x."
        res_val = sp.diff(act_expr, x) - act_expr / x
        assert sp.simplify(res_val) == 0, f"{cid}: actual expression residual failed."

    elif cid == "ODE-FO-10":
        # y' = y/x + x^2/(3y^2) => two explicit branches
        assert len(res.branch_solutions) == 2, f"{cid}: expected 2 branches."
        b0, b1 = res.branch_solutions[0], res.branch_solutions[1]

        # Compare actual emitted branch expressions against reference branches
        ref_b0 = x * (sp.log(sp.Abs(x)) + c)**sp.Rational(1, 3)
        ref_b1 = -x * (-sp.log(sp.Abs(x)) - c)**sp.Rational(1, 3)
        assert _prove_symbolic_zero(b0.expression - ref_b0, (c,)), f"{cid}: Branch 0 does not match reference positive branch."
        assert _prove_symbolic_zero(b1.expression - ref_b1, (c,)), f"{cid}: Branch 1 does not match reference negative branch."

        # Independent residuals on actual emitted expressions on x > 0
        x_pos = sp.Symbol("x", positive=True)
        diff0 = sp.diff(b0.expression.subs(x, x_pos), x_pos)
        res0 = sp.simplify(diff0 - (b0.expression.subs(x, x_pos) / x_pos + x_pos**2 / (3 * b0.expression.subs(x, x_pos)**2)))
        assert res0 == 0, f"{cid}: Branch 0 residual failed."
        diff1 = sp.diff(b1.expression.subs(x, x_pos), x_pos)
        res1 = sp.simplify(diff1 - (b1.expression.subs(x, x_pos) / x_pos + x_pos**2 / (3 * b1.expression.subs(x, x_pos)**2)))
        assert res1 == 0, f"{cid}: Branch 1 residual failed."

        # Verify structured branch domain intervals
        assert b0.domain_interval == (sp.exp(-c), sp.oo), f"{cid}: Branch 0 domain interval mismatch."
        assert b1.domain_interval == (0, sp.exp(-c)), f"{cid}: Branch 1 domain interval mismatch."

    elif cid == "ODE-FO-11":
        # y' = sin(2y) => y = n*pi/2
        assert "n*pi / 2" in res.final_result or "n*pi/2" in res.final_result.replace(" ", "")
        n = sp.Symbol("n", integer=True)
        eq_sol = n * sp.pi / 2
        res_val = sp.diff(eq_sol, x) - sp.sin(2 * eq_sol)
        assert sp.simplify(res_val) == 0, f"{cid}: equilibrium residual failed."

    elif cid == "ODE-SO-13":
        # y'' - 5y' + 6y = 0 => actual y(x) = C1*exp(3*x) + C2*exp(2*x)
        act_expr = sp.parse_expr(res.final_result.split("=")[-1].strip())
        ref_expr = c1 * sp.exp(3 * x) + c2 * sp.exp(2 * x)
        assert _prove_symbolic_zero(act_expr - ref_expr, (c1, c2)), f"{cid}: actual expression does not match reference."
        diff2 = sp.diff(act_expr, x, 2) - 5 * sp.diff(act_expr, x) + 6 * act_expr
        assert sp.simplify(diff2) == 0, f"{cid}: residual failed."

    elif cid == "ODE-SO-14":
        # y'' - 4y' + 4y = 0 => actual y(x) = (C1 + C2*x)*exp(2*x)
        act_expr = sp.parse_expr(res.final_result.split("=")[-1].strip())
        ref_expr = (c1 + c2 * x) * sp.exp(2 * x)
        assert _prove_symbolic_zero(act_expr - ref_expr, (c1, c2)), f"{cid}: actual expression does not match reference."
        diff2 = sp.diff(act_expr, x, 2) - 4 * sp.diff(act_expr, x) + 4 * act_expr
        assert sp.simplify(diff2) == 0, f"{cid}: residual failed."

    elif cid == "ODE-SO-15":
        # y'' + 4y = 0 => actual y(x) = C1*cos(2*x) + C2*sin(2*x)
        act_expr = sp.parse_expr(res.final_result.split("=")[-1].strip())
        ref_expr = c1 * sp.cos(2 * x) + c2 * sp.sin(2 * x)
        assert _prove_symbolic_zero(act_expr - ref_expr, (c1, c2)), f"{cid}: actual expression does not match reference."
        diff2 = sp.diff(act_expr, x, 2) + 4 * act_expr
        assert sp.simplify(diff2) == 0, f"{cid}: residual failed."

    elif cid == "ODE-SO-16":
        # y'' - 5y' + 6y = 0, y(0)=1, y'(0)=0 => actual y(x) = (3 - 2*exp(x))*exp(2*x)
        act_expr = sp.parse_expr(res.final_result.split("=")[-1].strip())
        ref_expr = 3 * sp.exp(2 * x) - 2 * sp.exp(3 * x)
        assert _prove_symbolic_zero(act_expr - ref_expr), f"{cid}: actual expression does not match 3*exp(2x) - 2*exp(3x)."
        diff2 = sp.diff(act_expr, x, 2) - 5 * sp.diff(act_expr, x) + 6 * act_expr
        assert sp.simplify(diff2) == 0, f"{cid}: residual failed."
        assert sp.simplify(act_expr.subs(x, 0)) == 1, f"{cid}: initial condition y(0) != 1."
        assert sp.simplify(sp.diff(act_expr, x).subs(x, 0)) == 0, f"{cid}: initial derivative y'(0) != 0."

    elif cid == "ODE-SO-17":
        # y'' - 4y' + 4y = 0, y(0)=1, y'(0)=2 => actual y(x) = exp(2*x)
        act_expr = sp.parse_expr(res.final_result.split("=")[-1].strip())
        ref_expr = sp.exp(2 * x)
        assert _prove_symbolic_zero(act_expr - ref_expr), f"{cid}: actual expression does not match exp(2x)."
        diff2 = sp.diff(act_expr, x, 2) - 4 * sp.diff(act_expr, x) + 4 * act_expr
        assert sp.simplify(diff2) == 0, f"{cid}: residual failed."
        assert sp.simplify(act_expr.subs(x, 0)) == 1, f"{cid}: initial condition y(0) != 1."
        assert sp.simplify(sp.diff(act_expr, x).subs(x, 0)) == 2, f"{cid}: initial derivative y'(0) != 2."

    elif cid == "ODE-SO-18":
        # y'' + 4y = 0, y(0)=1, y'(0)=2 => actual y(x) = sqrt(2)*sin(2*x + pi/4)
        act_expr = sp.parse_expr(res.final_result.split("=")[-1].strip())
        ref_expr = sp.cos(2 * x) + sp.sin(2 * x)
        assert _prove_symbolic_zero(act_expr - ref_expr), f"{cid}: actual expression does not match cos(2x) + sin(2x)."
        diff2 = sp.diff(act_expr, x, 2) + 4 * act_expr
        assert sp.simplify(diff2) == 0, f"{cid}: residual failed."
        assert sp.simplify(act_expr.subs(x, 0)) == 1, f"{cid}: initial condition y(0) != 1."
        assert sp.simplify(sp.diff(act_expr, x).subs(x, 0)) == 2, f"{cid}: initial derivative y'(0) != 2."

    elif cid == "ODE-SO-19":
        # 2t^2 y'' + 3t y' - y = 0, y1 = 1/t => actual y(t) = C1/t + 2*C2*sqrt(t)/3
        act_expr = sp.parse_expr(res.final_result.split("=")[-1].strip())
        t_pos = sp.Symbol("t", positive=True)
        act_p = act_expr.subs(t, t_pos)
        ref_expr = c1 / t_pos + 2 * c2 * sp.sqrt(t_pos) / 3
        assert _prove_symbolic_zero(act_p - ref_expr, (c1, c2)), f"{cid}: actual expression does not match reference."
        diff2 = 2 * t_pos**2 * sp.diff(act_p, t_pos, 2) + 3 * t_pos * sp.diff(act_p, t_pos) - act_p
        assert sp.simplify(diff2) == 0, f"{cid}: residual failed."

    elif cid == "ODE-SO-21":
        # Euler-Cauchy t > 0
        act_expr = sp.parse_expr(res.final_result.split("=")[-1].strip())
        t_pos = sp.Symbol("t", positive=True)
        act_p = act_expr.subs(t, t_pos)
        ref_expr = c1 / t_pos + 2 * c2 * sp.sqrt(t_pos) / 3
        assert _prove_symbolic_zero(act_p - ref_expr, (c1, c2)), f"{cid}: actual expression does not match reference on t > 0."
        diff2 = 2 * t_pos**2 * sp.diff(act_p, t_pos, 2) + 3 * t_pos * sp.diff(act_p, t_pos) - act_p
        assert sp.simplify(diff2) == 0, f"{cid}: residual failed on t > 0."

    elif cid == "ODE-SO-22":
        # Euler-Cauchy t < 0
        act_expr = sp.parse_expr(res.final_result.split("=")[-1].strip())
        t_neg = sp.Symbol("t", negative=True)
        act_n = act_expr.subs(t, t_neg)
        ref_expr = c1 / t_neg + 2 * c2 * sp.sqrt(-t_neg) / 3
        assert _prove_symbolic_zero(act_n - ref_expr, (c1, c2)), f"{cid}: actual expression does not match reference on t < 0."
        diff2 = 2 * t_neg**2 * sp.diff(act_n, t_neg, 2) + 3 * t_neg * sp.diff(act_n, t_neg) - act_n
        assert sp.simplify(diff2) == 0, f"{cid}: residual failed on t < 0."

    elif cid == "ODE-SO-23":
        # W(exp(2x), exp(3x)) = exp(5x) != 0
        act_w = sp.parse_expr(res.final_result.split("=")[-1].strip())
        assert act_w == sp.exp(5 * x), f"{cid}: actual Wronskian does not match exp(5x)."
        assert not act_w.is_zero, f"{cid}: Wronskian is zero."


@pytest.fixture(scope="module")
def app_use_case():
    return build_application()


@pytest.mark.parametrize("case", BENCHMARK_CASES, ids=[c.case_id for c in BENCHMARK_CASES])
def test_homogeneous_ode_24_acceptance_benchmark(app_use_case, case: AcceptanceCase):
    """End-to-end evaluation of the 24 acceptance cases through SolveProblemUseCase."""
    req = ProblemRequest(
        raw_input=case.raw_input,
        problem_type=case.problem_type,
        target_variable=case.target_variable,
    )
    res: SolutionResponse = app_use_case.execute(req)

    if case.is_valid:
        # Valid case assertions
        assert res.status == SolutionStatus.SUCCESS, (
            f"Case {case.case_id} failed with status {res.status}. Warnings: {res.warnings}"
        )
        assert res.verification is not None, f"Case {case.case_id} has no verification record."
        assert res.verification.status == VerificationStatus.VERIFIED, (
            f"Case {case.case_id} verification failed: {res.verification.details}"
        )

        # Custom symbolic or content check
        if case.custom_symbolic_check is not None:
            assert case.custom_symbolic_check(res), (
                f"Case {case.case_id} failed custom symbolic equivalence check. Result: {res.final_result}"
            )

        # Branch verification completeness
        if res.branch_solutions:
            for b in res.branch_solutions:
                assert b.verification is not None
                assert b.verification.status == VerificationStatus.VERIFIED, (
                    f"Case {case.case_id} branch '{b.branch_identity}' failed verification: {b.verification.details}"
                )

        # Rigorous independent mathematical verification (not relying solely on verifier)
        verify_case_independently(case, res)
    else:
        # Invalid / rejected case assertions
        assert res.status in (SolutionStatus.INVALID_INPUT, SolutionStatus.CANNOT_SOLVE), (
            f"Case {case.case_id} should be rejected but got status {res.status}."
        )
        if res.verification is not None:
            assert res.verification.status != VerificationStatus.VERIFIED, (
                f"Case {case.case_id} was incorrectly marked VERIFIED."
            )

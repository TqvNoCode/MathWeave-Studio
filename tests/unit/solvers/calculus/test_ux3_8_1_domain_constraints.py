"""UX3.8.1 regression suite: preserve original ODE domain constraints & fail-closed scalar checks."""

from __future__ import annotations

import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.input.ode_parser import parse_ode_input
from math_app.presentation.components.domain_view import format_domain_condition
from math_app.solvers.calculus.ode._real_calculus import (
    classify_finite_real_scalar,
    is_finite_real_scalar,
)
from math_app.solvers.calculus.ode.exact_solver import ODEExactSolver
from math_app.solvers.calculus.ode.integrating_factor_solver import (
    ODEIntegratingFactorSolver,
)
from math_app.verification.calculus.ode_verifier import (
    ODEVerifier,
    classify_scalar_real_finite,
)


def test_exact_sqrt_squared_rejects_negative_ic_and_preserves_domain() -> None:
    """Counterexample A: sqrt(x)^2*dx + dy = 0, y(-1) = 1 must be rejected and preserve x >= 0."""
    solver = ODEExactSolver()
    resp = solver.solve(
        ProblemRequest(
            raw_input="sqrt(x)^2*dx + dy = 0, y(-1) = 1",
            problem_type=ProblemType.ODE_EXACT,
            target_variable="x",
        )
    )
    assert resp.status == SolutionStatus.INVALID_INPUT
    assert resp.verification.status != VerificationStatus.VERIFIED
    assert resp.original_domain_latex == r"[0, +\infty)"
    assert any(">= 0" in r for r in resp.domain_restrictions)


def test_exact_sqrt_squared_no_ic_and_valid_positive_ic() -> None:
    """Exact ODE sqrt(x)^2*dx + dy = 0 preserves x >= 0 without IC and verifies valid IC."""
    solver = ODEExactSolver()
    x, y = sp.symbols("x y")

    resp_gen = solver.solve(
        ProblemRequest(
            raw_input="sqrt(x)^2*dx + dy = 0",
            problem_type=ProblemType.ODE_EXACT,
            target_variable="x",
        )
    )
    assert resp_gen.status == SolutionStatus.SUCCESS
    assert resp_gen.verification.status == VerificationStatus.VERIFIED
    assert resp_gen.original_domain_latex == r"[0, +\infty)"
    assert resp_gen.normalized_domain_latex == r"[0, +\infty)"
    assert any(">= 0" in r for r in resp_gen.domain_restrictions)
    lhs_str = resp_gen.final_result.split("=")[0].strip()
    assert sp.simplify(sp.sympify(lhs_str) - (x**2 / 2 + y)) == 0

    resp_pos = solver.solve(
        ProblemRequest(
            raw_input="sqrt(x)^2*dx + dy = 0, y(4) = 1",
            problem_type=ProblemType.ODE_EXACT,
            target_variable="x",
        )
    )
    assert resp_pos.status == SolutionStatus.SUCCESS
    assert resp_pos.verification.status == VerificationStatus.VERIFIED
    assert resp_pos.original_domain_latex == r"[0, +\infty)"
    lhs_p, rhs_p = (s.strip() for s in resp_pos.final_result.split("="))
    assert sp.simplify((sp.sympify(lhs_p) - sp.sympify(rhs_p)).subs([(x, 4), (y, 1)])) == 0


def test_integrating_factor_sqrt_squared_rejects_invalid_ic_and_separates_domains() -> None:
    """Counterexample B: sqrt(x)^2*dx + x^2*dy = 0 keeps original [0, oo) and normalized (0, oo)."""
    solver = ODEIntegratingFactorSolver()
    x, y = sp.symbols("x y")

    resp_neg = solver.solve(
        ProblemRequest(
            raw_input="sqrt(x)^2*dx + x^2*dy = 0, y(-1) = 1",
            problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
            target_variable="x",
        )
    )
    assert resp_neg.status == SolutionStatus.INVALID_INPUT
    assert resp_neg.verification.status != VerificationStatus.VERIFIED
    assert resp_neg.original_domain_latex == r"[0, +\infty)"
    assert any(">= 0" in r for r in resp_neg.domain_restrictions)

    resp_zero = solver.solve(
        ProblemRequest(
            raw_input="sqrt(x)^2*dx + x^2*dy = 0, y(0) = 1",
            problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
            target_variable="x",
        )
    )
    assert resp_zero.status == SolutionStatus.INVALID_INPUT

    resp_gen = solver.solve(
        ProblemRequest(
            raw_input="sqrt(x)^2*dx + x^2*dy = 0",
            problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
            target_variable="x",
        )
    )
    assert resp_gen.status == SolutionStatus.SUCCESS
    assert resp_gen.verification.status == VerificationStatus.VERIFIED
    assert resp_gen.original_domain_latex == r"[0, +\infty)"
    assert resp_gen.normalized_domain_latex == r"(0, +\infty)"
    lhs_g = resp_gen.final_result.split("=")[0].strip()
    potential = sp.sympify(lhs_g)
    assert sp.simplify(sp.diff(potential, x) - 1 / x) == 0
    assert sp.simplify(sp.diff(potential, y) - 1) == 0

    resp_pos = solver.solve(
        ProblemRequest(
            raw_input="sqrt(x)^2*dx + x^2*dy = 0, y(1) = 2",
            problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
            target_variable="x",
        )
    )
    assert resp_pos.status == SolutionStatus.SUCCESS
    assert resp_pos.verification.status == VerificationStatus.VERIFIED
    assert resp_pos.original_domain_latex == r"[0, +\infty)"
    assert resp_pos.normalized_domain_latex == r"(0, +\infty)"


def test_canceled_logarithm_and_negative_fractional_root_ast_preservation() -> None:
    """Canceled log(x)-log(x), log(x)/log(x), and x**(-1/2) must preserve source restrictions."""
    solver = ODEExactSolver()

    r_cancel = solver.solve(
        ProblemRequest(
            raw_input="(log(x) - log(x) + 1)*dx + dy = 0, y(-1) = 1",
            problem_type=ProblemType.ODE_EXACT,
            target_variable="x",
        )
    )
    assert r_cancel.status == SolutionStatus.INVALID_INPUT
    assert r_cancel.original_domain_latex == r"(0, +\infty)"
    assert any("> 0" in r for r in r_cancel.domain_restrictions)

    r_ratio_neg = solver.solve(
        ProblemRequest(
            raw_input="(log(x)/log(x))*dx + dy = 0, y(-1) = 1",
            problem_type=ProblemType.ODE_EXACT,
            target_variable="x",
        )
    )
    assert r_ratio_neg.status == SolutionStatus.INVALID_INPUT
    assert r_ratio_neg.original_domain_latex == r"(0, 1) \cup (1, +\infty)"

    r_ratio_one = solver.solve(
        ProblemRequest(
            raw_input="(log(x)/log(x))*dx + dy = 0, y(1) = 1",
            problem_type=ProblemType.ODE_EXACT,
            target_variable="x",
        )
    )
    assert r_ratio_one.status == SolutionStatus.INVALID_INPUT

    r_ratio_ok = solver.solve(
        ProblemRequest(
            raw_input="(log(x)/log(x))*dx + dy = 0, y(2) = 1",
            problem_type=ProblemType.ODE_EXACT,
            target_variable="x",
        )
    )
    assert r_ratio_ok.status == SolutionStatus.SUCCESS
    assert r_ratio_ok.verification.status == VerificationStatus.VERIFIED

    parsed_neg_half = parse_ode_input("x**(-1/2)*dx + dy = 0", target_variable="x")
    relations = {c.relation for c in parsed_neg_half.original_domain_constraints}
    assert {"ne", "ge"} <= relations


def test_unassumed_symbolic_parameters_fail_closed_to_unverified() -> None:
    """Unassumed symbolic parameters in IC or constraints must fail closed as UNVERIFIED."""
    solver = ODEExactSolver()
    iff = ODEIntegratingFactorSolver()

    for raw in ("x*dx + dy = 0, y(a) = 1", "sqrt(x)^2*dx + dy = 0, y(a) = 1"):
        res = solver.solve(
            ProblemRequest(raw_input=raw, problem_type=ProblemType.ODE_EXACT, target_variable="x")
        )
        assert res.status == SolutionStatus.UNVERIFIED
        assert res.verification.status == VerificationStatus.UNVERIFIED

    res_if = iff.solve(
        ProblemRequest(
            raw_input="sqrt(x)^2*dx + x^2*dy = 0, y(a) = 1",
            problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
            target_variable="x",
        )
    )
    assert res_if.status == SolutionStatus.UNVERIFIED
    assert res_if.verification.status == VerificationStatus.UNVERIFIED

    a_unassumed = sp.Symbol("a")
    a_real = sp.Symbol("a", real=True)
    a_pos = sp.Symbol("a", positive=True)

    assert classify_scalar_real_finite(a_unassumed)[0] == "unknown"
    assert classify_finite_real_scalar(a_unassumed)[0] == "unknown"
    assert not is_finite_real_scalar(a_unassumed)[0]
    assert classify_scalar_real_finite(sp.log(a_real))[0] == "unknown"
    assert classify_scalar_real_finite(1 / (a_real - 1))[0] == "unknown"
    assert classify_scalar_real_finite(a_real)[0] == "valid"
    assert classify_scalar_real_finite(sp.log(a_pos))[0] == "valid"
    assert is_finite_real_scalar(sp.Ci(sp.exp(1)))[0]
    assert is_finite_real_scalar(sp.Si(1))[0]
    assert is_finite_real_scalar(sp.erf(1))[0]
    assert classify_scalar_real_finite(sp.zoo)[0] == "invalid"
    assert classify_scalar_real_finite(sp.log(-2))[0] == "invalid"

    verifier = ODEVerifier()
    x, y = sp.symbols("x y")
    parsed_sqrt = parse_ode_input("sqrt(x)^2*dx + dy = 0", target_variable="x")
    ver_bad = verifier.verify_exact(
        x**2 / 2 + y,
        x,
        sp.Integer(1),
        x,
        y,
        initial_condition=(sp.Integer(-1), sp.Integer(1)),
        source_constraints=parsed_sqrt.original_domain_constraints,
    )
    assert ver_bad.status == VerificationStatus.FAILED

    ver_sym = verifier.verify_exact(
        x**2 / 2 + y,
        x,
        sp.Integer(1),
        x,
        y,
        initial_condition=(a_unassumed, sp.Integer(1)),
    )
    assert ver_sym.status == VerificationStatus.UNVERIFIED


def test_negative_domain_permitted_by_source_remains_verified() -> None:
    """Rational differential forms allowing negative x must succeed and verify cleanly."""
    solver = ODEExactSolver()
    x, y = sp.symbols("x y")

    r1 = solver.solve(
        ProblemRequest(
            raw_input="(1/(x - 1))*dx + dy = 0, y(0) = 1",
            problem_type=ProblemType.ODE_EXACT,
            target_variable="x",
        )
    )
    assert r1.status == SolutionStatus.SUCCESS
    assert r1.verification.status == VerificationStatus.VERIFIED
    assert r1.original_domain_latex == r"\mathbb{R} \setminus \{1\}"
    lhs1, rhs1 = (s.strip() for s in r1.final_result.split("="))
    assert sp.simplify((sp.sympify(lhs1) - sp.sympify(rhs1)).subs([(x, 0), (y, 1)])) == 0

    r2 = solver.solve(
        ProblemRequest(
            raw_input="(1/x)*dx + dy = 0, y(-1) = 1",
            problem_type=ProblemType.ODE_EXACT,
            target_variable="x",
        )
    )
    assert r2.status == SolutionStatus.SUCCESS
    assert r2.verification.status == VerificationStatus.VERIFIED
    assert r2.original_domain_latex == r"\mathbb{R} \setminus \{0\}"
    lhs2, rhs2 = (s.strip() for s in r2.final_result.split("="))
    assert sp.simplify((sp.sympify(lhs2) - sp.sympify(rhs2)).subs([(x, -1), (y, 1)])) == 0


def test_domain_view_formats_even_root_condition() -> None:
    """UI formatter renders preserved even-root source restrictions into clean LaTeX."""
    key, label, formula = format_domain_condition(
        "Điều kiện xác định ban đầu: x >= 0 (căn bậc chẵn).",
        "x",
    )
    assert key == "sqrt_x"
    assert "căn bậc chẵn" in label.lower()
    assert formula == r"x \ge 0"

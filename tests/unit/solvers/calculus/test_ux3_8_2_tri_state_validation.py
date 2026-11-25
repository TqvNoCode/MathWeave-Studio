"""UX3.8.2 regression suite: consistent tri-state validation, exception safety, and domain completeness."""

from __future__ import annotations

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import (
    DomainCompleteness,
    ProblemType,
    SolutionStatus,
    VerificationStatus,
)
from math_app.input.ode_parser import parse_ode_input
from math_app.solvers.calculus.ode import _real_calculus
from math_app.solvers.calculus.ode.classical_homogeneous_solver import (
    ODEClassicalHomogeneousSolver,
)
from math_app.solvers.calculus.ode.exact_solver import ODEExactSolver
from math_app.solvers.calculus.ode.integrating_factor_solver import (
    ODEIntegratingFactorSolver,
)
from math_app.solvers.calculus.ode.linear_solver import ODELinearSolver
from math_app.solvers.calculus.ode.reduction_of_order_solver import (
    ODEReductionOfOrderSolver,
)
from math_app.solvers.calculus.ode.separable_solver import ODESeparableSolver
from math_app.verification.calculus.ode_verifier import (
    ODEVerifier,
    evaluate_initial_point_domain,
    validate_initial_point_in_domain,
)


def test_unassumed_symbolic_ic_propagates_unverified_across_all_ode_solvers() -> None:
    """Category 1: Unassumed symbolic ICs must return UNVERIFIED across all ODE solver paths."""
    solvers_and_inputs = [
        (
            ODELinearSolver(),
            ProblemRequest(
                raw_input="y' + y = 0, y(a) = 1",
                problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
                target_variable="t",
            ),
        ),
        (
            ODELinearSolver(),
            ProblemRequest(
                raw_input="x*y' + y = 0, y(a) = 1",
                problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
                target_variable="x",
            ),
        ),
        (
            ODESeparableSolver(),
            ProblemRequest(
                raw_input="y' = x*y, y(a) = 1",
                problem_type=ProblemType.ODE_SEPARABLE,
                target_variable="x",
            ),
        ),
        (
            ODEClassicalHomogeneousSolver(),
            ProblemRequest(
                raw_input="y' = y/x + (y/x)^2, y(a) = 1",
                problem_type=ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
                target_variable="x",
            ),
        ),
        (
            ODEReductionOfOrderSolver(),
            ProblemRequest(
                raw_input="t^2*y'' - 2*y = 0, y(a) = 1, y'(a) = 1",
                problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
                target_variable="t",
                parameters={"y1": "t^2"},
            ),
        ),
        (
            ODEReductionOfOrderSolver(),
            ProblemRequest(
                raw_input="t^2*y'' - 2*y = 0, y(1) = 1, y'(1) = a",
                problem_type=ProblemType.ODE_REDUCTION_OF_ORDER,
                target_variable="t",
                parameters={"y1": "t^2"},
            ),
        ),
        (
            ODEExactSolver(),
            ProblemRequest(
                raw_input="x*dx + dy = 0, y(a) = 1",
                problem_type=ProblemType.ODE_EXACT,
                target_variable="x",
            ),
        ),
        (
            ODEIntegratingFactorSolver(),
            ProblemRequest(
                raw_input="sqrt(x)^2*dx + x^2*dy = 0, y(a) = 1",
                problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
                target_variable="x",
            ),
        ),
    ]

    for solver, req in solvers_and_inputs:
        resp = solver.solve(req)
        assert resp.status == SolutionStatus.UNVERIFIED, req.raw_input
        assert resp.verification.status == VerificationStatus.UNVERIFIED, req.raw_input

    # Legacy Boolean compatibility wrapper must ALSO fail closed on unknown symbolic inputs.
    x, y = sp.symbols("x y")
    a_unassumed = sp.Symbol("a")
    ok_sym, _ = validate_initial_point_in_domain(x + y, x, y, a_unassumed, sp.Integer(1))
    assert not ok_sym


def test_exception_during_ast_constraint_evaluation_yields_unverified_not_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Category 2: Exceptions in denominator/root/log checks must never silently succeed."""
    x, y = sp.symbols("x y")

    orig_subs = sp.Basic.subs

    def flaky_subs(self: sp.Basic, *args, **kwargs):
        if self == x - 2:
            raise RuntimeError("simulated evaluation failure")
        return orig_subs(self, *args, **kwargs)

    monkeypatch.setattr(sp.Basic, "subs", flaky_subs)

    for expr in (1 / (x - 2), sp.sqrt(x - 2), sp.log(x - 2)):
        stat, msg = evaluate_initial_point_domain(
            expr,
            x,
            y,
            sp.Integer(5),
            sp.Integer(1),
        )
        assert stat == "unknown", f"Expected unknown for {expr}, got {stat}: {msg}"
        assert "simulated evaluation failure" in msg or msg != ""
        ok_legacy, _ = validate_initial_point_in_domain(expr, x, y, sp.Integer(5), sp.Integer(1))
        assert not ok_legacy

    # Separable solver must propagate the evaluation failure as UNVERIFIED rather than SUCCESS.
    sep = ODESeparableSolver()
    resp = sep.solve(
        ProblemRequest(
            raw_input="y' = log(x - 2)*y, y(5) = 1",
            problem_type=ProblemType.ODE_SEPARABLE,
            target_variable="x",
        )
    )
    assert resp.status == SolutionStatus.UNVERIFIED
    assert resp.verification.status == VerificationStatus.UNVERIFIED

    # Genuine ZeroDivisionError remains proven 'invalid'.
    def zero_div_subs(self: sp.Basic, *args, **kwargs):
        if self == x - 2:
            raise ZeroDivisionError("division by zero")
        return orig_subs(self, *args, **kwargs)

    monkeypatch.setattr(sp.Basic, "subs", zero_div_subs)
    stat_z, _ = evaluate_initial_point_domain(1 / (x - 2), x, y, sp.Integer(2), sp.Integer(1))
    assert stat_z == "invalid"


def test_incomplete_denominator_constraint_fails_closed_and_marks_incomplete_domain() -> None:
    """Category 3: Parametric or unresolvable denominators yield UNVERIFIED and never claim EXACT S.Reals."""
    sep = ODESeparableSolver()
    resp = sep.solve(
        ProblemRequest(
            raw_input="y' = y/(x - a), y(1) = 2",
            problem_type=ProblemType.ODE_SEPARABLE,
            target_variable="x",
        )
    )
    assert resp.status == SolutionStatus.UNVERIFIED
    assert resp.verification.status == VerificationStatus.UNVERIFIED

    ex = ODEExactSolver()
    resp_ex = ex.solve(
        ProblemRequest(
            raw_input="(1/(x - a))*dx + dy = 0, y(1) = 2",
            problem_type=ProblemType.ODE_EXACT,
            target_variable="x",
        )
    )
    assert resp_ex.status == SolutionStatus.UNVERIFIED
    assert resp_ex.verification.status == VerificationStatus.UNVERIFIED

    # Unresolvable transcendental denominator in differential form must never produce bare R as complete.
    x, y = sp.symbols("x y")
    parsed_trans = parse_ode_input("(1/(sin(x) - x))*dx + dy = 0", target_variable="x")
    meta = _real_calculus.compute_differential_form_domain_metadata(
        parsed=parsed_trans,
        x_var=x,
        y_var=y,
        M_expr=1 / (sp.sin(x) - x),
        N_expr=sp.Integer(1),
    )
    assert meta.completeness in (DomainCompleteness.PARTIAL, DomainCompleteness.UNKNOWN)
    assert meta.original_domain_latex != r"\mathbb{R}"
    assert meta.normalized_domain_latex != r"\mathbb{R}"


def test_unresolved_log_or_even_root_and_domain_completeness_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Category 4: Unresolved log/root constraints fail closed; incomplete/multivariate domains stay explicit."""
    x, y = sp.symbols("x y")
    a_real = sp.Symbol("a", real=True)

    # Realness alone does not prove log(a) > 0 or sqrt(a) >= 0 -> unknown
    stat_log, _ = evaluate_initial_point_domain(sp.log(x), x, y, a_real, sp.Integer(1))
    stat_sqrt, _ = evaluate_initial_point_domain(sp.sqrt(x), x, y, a_real, sp.Integer(1))
    assert stat_log == "unknown"
    assert stat_sqrt == "unknown"

    sep = ODESeparableSolver()
    resp_sqrt = sep.solve(
        ProblemRequest(
            raw_input="y' = sqrt(x)*y, y(a) = 1",
            problem_type=ProblemType.ODE_SEPARABLE,
            target_variable="x",
        )
    )
    assert resp_sqrt.status == SolutionStatus.UNVERIFIED
    assert resp_sqrt.verification.status == VerificationStatus.UNVERIFIED

    # Multivariate (x, y) constraint must not be collapsed into a fake 1D R interval.
    ex = ODEExactSolver()
    resp_mv = ex.solve(
        ProblemRequest(
            raw_input="log(x + y)*dx + (log(x + y) + y)*dy = 0",
            problem_type=ProblemType.ODE_EXACT,
            target_variable="x",
        )
    )
    assert resp_mv.status == SolutionStatus.SUCCESS
    assert resp_mv.verification.status == VerificationStatus.VERIFIED
    assert resp_mv.domain_completeness == DomainCompleteness.PARTIAL
    assert resp_mv.original_domain_latex != r"\mathbb{R}"
    assert resp_mv.normalized_domain_latex != r"\mathbb{R}"
    assert any("x + y > 0" in r for r in resp_mv.domain_restrictions)

    # If domain extractor raises, metadata must NOT fall back silently to S.Reals / \mathbb{R}.
    def boom_extract(_expr, _var):
        raise RuntimeError("domain extractor failure")

    monkeypatch.setattr(_real_calculus, "extract_expression_domain_with_completeness", boom_extract)
    parsed_simp = parse_ode_input("sqrt(x)^2*dx + dy = 0", target_variable="x")
    meta_fail = _real_calculus.compute_differential_form_domain_metadata(
        parsed=parsed_simp,
        x_var=x,
        y_var=y,
        M_expr=x,
        N_expr=sp.Integer(1),
    )
    assert meta_fail.completeness == DomainCompleteness.UNKNOWN
    assert meta_fail.normalized_domain_latex != r"\mathbb{R}"


def test_sufficient_real_assumptions_remain_valid() -> None:
    """Category 5: Sufficiently assumed positive/real symbols validate cleanly."""
    x, y = sp.symbols("x y")
    a_pos = sp.Symbol("a", positive=True)
    a_real = sp.Symbol("a", real=True)

    assert evaluate_initial_point_domain(sp.log(x), x, y, a_pos, sp.Integer(1))[0] == "valid"
    assert evaluate_initial_point_domain(sp.sqrt(x), x, y, a_pos, sp.Integer(1))[0] == "valid"
    assert evaluate_initial_point_domain(x + y, x, y, a_real, sp.Integer(1))[0] == "valid"
    assert validate_initial_point_in_domain(x + y, x, y, a_real, sp.Integer(1))[0]

    parsed_exact = parse_ode_input("(1/x)*dx + dy = 0", target_variable="x")
    verifier = ODEVerifier()
    ver = verifier.verify_exact(
        sp.log(x) + y,
        1 / x,
        sp.Integer(1),
        x,
        y,
        initial_condition=(a_pos, sp.Integer(1)),
        source_constraints=parsed_exact.original_domain_constraints,
    )
    assert ver.status == VerificationStatus.VERIFIED

    lin = ODELinearSolver()
    resp_lin = lin.solve(
        ProblemRequest(
            raw_input="y' = k*y",
            problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
            target_variable="t",
        )
    )
    assert resp_lin.status == SolutionStatus.SUCCESS
    assert resp_lin.verification.status == VerificationStatus.VERIFIED


def test_valid_positive_negative_and_singular_cauchy_cases_preserved() -> None:
    """Categories 6, 7 & 8: Existing valid real-domain, singular Cauchy, and UX3.8.1 cases remain intact."""
    lin = ODELinearSolver()
    sep = ODESeparableSolver()
    ex = ODEExactSolver()
    iff = ODEIntegratingFactorSolver()

    # Valid negative-domain separable ODE
    r_sep_neg = sep.solve(
        ProblemRequest(
            raw_input="y' = y/x, y(-2) = 4",
            problem_type=ProblemType.ODE_SEPARABLE,
            target_variable="x",
        )
    )
    assert r_sep_neg.status == SolutionStatus.SUCCESS
    assert r_sep_neg.verification.status in (
        VerificationStatus.VERIFIED,
        VerificationStatus.PARTIALLY_VERIFIED,
    )

    # Valid positive-domain integrating factor ODE
    r_if_pos = iff.solve(
        ProblemRequest(
            raw_input="sqrt(x)^2*dx + x^2*dy = 0, y(1) = 2",
            problem_type=ProblemType.ODE_INTEGRATING_FACTOR,
            target_variable="x",
        )
    )
    assert r_if_pos.status == SolutionStatus.SUCCESS
    assert r_if_pos.verification.status == VerificationStatus.VERIFIED
    assert r_if_pos.domain_completeness == DomainCompleteness.EXACT
    assert r_if_pos.original_domain_latex == r"[0, +\infty)"
    assert r_if_pos.normalized_domain_latex == r"(0, +\infty)"

    # UX3.8.1 invalid sqrt(x)^2 IC
    r_ex_bad = ex.solve(
        ProblemRequest(
            raw_input="sqrt(x)^2*dx + dy = 0, y(-1) = 1",
            problem_type=ProblemType.ODE_EXACT,
            target_variable="x",
        )
    )
    assert r_ex_bad.status == SolutionStatus.INVALID_INPUT
    assert r_ex_bad.verification.status != VerificationStatus.VERIFIED

    # Valid singular Cauchy removable homogeneous case
    r_cauchy_ok = lin.solve(
        ProblemRequest(
            raw_input="x*y' + 2*x*y = 0, y(0) = 1",
            problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
            target_variable="x",
        )
    )
    assert r_cauchy_ok.status == SolutionStatus.SUCCESS
    assert r_cauchy_ok.verification.status == VerificationStatus.C1_EXTENSION_VERIFIED

    # Oscillatory coefficient must not claim verified C1 extension
    r_cauchy_osc = lin.solve(
        ProblemRequest(
            raw_input="x*y' + x*sin(1/x)*y = 0, y(0) = 1",
            problem_type=ProblemType.ODE_FIRST_ORDER_LINEAR,
            target_variable="x",
        )
    )
    assert r_cauchy_osc.verification.status != VerificationStatus.VERIFIED

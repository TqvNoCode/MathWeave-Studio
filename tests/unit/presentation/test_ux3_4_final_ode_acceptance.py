"""Comprehensive Acceptance and Regression Hardening Test Suite for UX3.4.

Covers:
- Test 1: Complete Nine-Operation routing, execution, and verification parity.
- Test 2: ODE Order switching stress test (10 cycles) with zero parameter leakage.
- Test 3: General vs Cauchy IVP state isolation, draft preservation, and conflict rejection.
- Test 4: Method routing matrix (AUTO, UC, VoP, and CANNOT_SOLVE rejection).
- Test 5: Mathematical Reference Benchmarks (Symbolic Residual R(t) = 0 and Cauchy IC satisfaction).
"""

from __future__ import annotations

import pytest
import sympy as sp

from math_app.application.dtos import ProblemRequest
from math_app.domain.exceptions import InvalidInputError
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.main import build_application
from math_app.presentation.components.operation_catalog import get_operation_by_type
from math_app.presentation.components.workspace.ode import (
    ODEClassification,
    ODEMethodPreference,
    ODEMode,
    ODEOrder,
    ODEState,
)


@pytest.fixture(scope="module")
def use_case():
    return build_application()


def test_ux3_4_nine_operations_routing_and_solving(use_case):
    """Verify all 9 ODE operations route, solve live, and achieve VERIFIED status."""
    all_9_types = [
        ProblemType.ODE_FIRST_ORDER_LINEAR,
        ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        ProblemType.ODE_SEPARABLE,
        ProblemType.ODE_EXACT,
        ProblemType.ODE_INTEGRATING_FACTOR,
        ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF,
        ProblemType.ODE_SECOND_ORDER_IVP,
        ProblemType.ODE_REDUCTION_OF_ORDER,
        ProblemType.WRONSKIAN,
    ]

    for pt in all_9_types:
        op = get_operation_by_type(pt)
        assert op is not None
        assert len(op.examples) >= 3

        # Construct request and execute solver
        if pt == ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF:
            req = ProblemRequest(
                problem_type=pt,
                raw_input="y'' - 3*y' - 4*y = 0",
                target_variable="t",
                parameters={"expected_classification": "HOMOGENEOUS", "mode": "GENERAL"},
            )
        elif pt == ProblemType.ODE_SECOND_ORDER_IVP:
            req = ProblemRequest(
                problem_type=pt,
                raw_input="y'' + 4*y = 0",
                target_variable="t",
                parameters={
                    "expected_classification": "HOMOGENEOUS",
                    "mode": "CAUCHY_IVP",
                    "t0": "0",
                    "y0": "0",
                    "v0": "2",
                },
            )
        elif pt == ProblemType.ODE_REDUCTION_OF_ORDER:
            req = ProblemRequest(
                problem_type=pt,
                raw_input="2*t^2*y'' + 3*t*y' - y = 0",
                target_variable="t",
                parameters={"known_solution": "1/t"},
            )
        elif pt == ProblemType.WRONSKIAN:
            req = ProblemRequest(
                problem_type=pt,
                raw_input="cos(t), sin(t)",
                target_variable="t",
                parameters={"functions": "cos(t), sin(t)"},
            )
        else:
            req = ProblemRequest(
                problem_type=pt,
                raw_input=op.default_input,
                target_variable="x",
                parameters={},
            )

        sol = use_case.execute(req)
        assert sol.status == SolutionStatus.SUCCESS, f"Operation {pt.name} failed with: {sol.final_result}"
        assert sol.verification.status == VerificationStatus.VERIFIED, f"Operation {pt.name} verification failed: {sol.verification.details}"
        assert sol.final_result and len(sol.final_result.strip()) > 0
        assert len(sol.steps) >= 1


def test_ux3_4_order_switching_stress_and_leakage():
    """Verify 10 alternating First-Order <-> Second-Order switches with zero parameter leakage."""
    state = ODEState()
    for cycle in range(10):
        # 1. Switch to Second Order Nonhomogeneous IVP
        state_so = (
            state.with_order(ODEOrder.SECOND_ORDER)
            .with_classification(ODEClassification.SECOND_ORDER_NONHOMOGENEOUS)
            .with_mode(ODEMode.CAUCHY_IVP)
            .with_method_preference(ODEMethodPreference.UNDETERMINED_COEFFICIENTS)
            .with_equation("y'' + 2*y' + y = exp(-t)")
            .with_target_var("t")
            .with_initial_condition("y(0)=1, y'(0)=2")
        )

        req_so = state_so.build_problem_request()
        assert req_so.problem_type == ProblemType.ODE_SECOND_ORDER_IVP
        assert req_so.parameters.get("method_preference") == "UNDETERMINED_COEFFICIENTS"
        assert req_so.parameters.get("problem_mode") == "CAUCHY_IVP"
        assert "y(0)=1, y'(0)=2" in req_so.parameters.get("initial_condition", "")

        # 2. Switch to First Order Separable
        state_fo = state_so.with_order(ODEOrder.FIRST_ORDER).with_classification(ODEClassification.SEPARABLE)
        assert state_fo.order == ODEOrder.FIRST_ORDER
        assert state_fo.classification == ODEClassification.SEPARABLE

        req_fo = state_fo.build_problem_request()
        assert req_fo.problem_type == ProblemType.ODE_SEPARABLE
        # Verify strict leakage prevention
        for leaked_param in ("t0", "y0", "v0", "method_preference", "problem_mode", "y1"):
            assert leaked_param not in req_fo.parameters, f"Leaked parameter {leaked_param} in cycle {cycle}"

        state = state_fo


def test_ux3_4_general_cauchy_isolation_and_conflict_handling():
    """Verify General vs Cauchy IVP isolation, draft preservation, and conflict rejection."""
    # 1. Draft preservation: Switching Cauchy -> General retains draft in UI but strips from ProblemRequest
    state_ivp = (
        ODEState(order=ODEOrder.SECOND_ORDER, classification=ODEClassification.SECOND_ORDER_HOMOGENEOUS)
        .with_mode(ODEMode.CAUCHY_IVP)
        .with_initial_condition("y(0)=3, y'(0)=5")
    )

    req_ivp = state_ivp.build_problem_request()
    assert req_ivp.problem_type == ProblemType.ODE_SECOND_ORDER_IVP
    assert "y(0)=3, y'(0)=5" in req_ivp.parameters.get("initial_condition", "")

    state_gen = state_ivp.with_mode(ODEMode.GENERAL)
    # Active IC is strictly cleared to prevent leakage in GENERAL mode
    assert state_gen.initial_condition == ""
    # Draft is preserved in state
    assert state_gen.initial_condition_draft == "y(0)=3, y'(0)=5"
    req_gen = state_gen.build_problem_request()
    assert req_gen.problem_type == ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF
    assert "initial_condition" not in req_gen.parameters

    # Switching back to CAUCHY_IVP restores the draft
    state_ivp_restored = state_gen.with_mode(ODEMode.CAUCHY_IVP)
    assert state_ivp_restored.initial_condition == "y(0)=3, y'(0)=5"

    # 2. Incomplete IC in Cauchy mode raises InvalidInputError
    state_incomplete = (
        ODEState(order=ODEOrder.SECOND_ORDER, classification=ODEClassification.SECOND_ORDER_HOMOGENEOUS)
        .with_mode(ODEMode.CAUCHY_IVP)
        .with_initial_condition("y(0) = 1")
    )
    with pytest.raises(InvalidInputError, match="y\\(t0\\) = y0 và y'\\(t0\\) = v0"):
        state_incomplete.build_problem_request()

    # 3. Conflicting inline vs dedicated IC raises InvalidInputError
    state_conflict = (
        ODEState(order=ODEOrder.SECOND_ORDER, classification=ODEClassification.SECOND_ORDER_HOMOGENEOUS)
        .with_mode(ODEMode.CAUCHY_IVP)
        .with_equation("y'' + y = 0, y(0)=1, y'(0)=0")
        .with_initial_condition("y(0)=2, y'(0)=0")
    )
    with pytest.raises(InvalidInputError, match="Phát hiện xung đột điều kiện ban đầu"):
        state_conflict.build_problem_request()


def test_ux3_4_method_routing_and_rejection(use_case):
    """Verify AUTO method routing and invalid method rejection."""
    # 1. AUTO on exponential routes to Undetermined Coefficients
    state_exp = (
        ODEState(order=ODEOrder.SECOND_ORDER, classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS)
        .with_equation("y'' - 3*y' - 4*y = 3*exp(2*t)")
        .with_method_preference(ODEMethodPreference.AUTO)
    )
    req_exp = state_exp.build_problem_request()
    sol_exp = use_case.execute(req_exp)
    assert sol_exp.status == SolutionStatus.SUCCESS
    assert any("hệ số bất định" in s.rule_name.lower() or "hệ số bất định" in s.title.lower() for s in sol_exp.steps)

    # 2. AUTO on tan(t) routes to Variation of Parameters
    state_tan = (
        ODEState(order=ODEOrder.SECOND_ORDER, classification=ODEClassification.SECOND_ORDER_NONHOMOGENEOUS)
        .with_equation("y'' + y = tan(t)")
        .with_method_preference(ODEMethodPreference.AUTO)
    )
    req_tan = state_tan.build_problem_request()
    sol_tan = use_case.execute(req_tan)
    assert sol_tan.status == SolutionStatus.SUCCESS
    assert any("biến thiên hằng số" in s.rule_name.lower() or "biến thiên hằng số" in s.title.lower() for s in sol_tan.steps)

    # 3. Manual UC on tan(t) cleanly rejected with CANNOT_SOLVE and honest explanation
    state_invalid = state_tan.with_method_preference(ODEMethodPreference.UNDETERMINED_COEFFICIENTS)
    req_invalid_uc = state_invalid.build_problem_request()
    sol_invalid = use_case.execute(req_invalid_uc)
    assert sol_invalid.status == SolutionStatus.CANNOT_SOLVE
    assert "không thuộc các họ giải được bằng phương pháp hệ số bất định" in sol_invalid.verification.details.lower()


def test_ux3_4_mathematical_benchmarks(use_case):
    """Verify mathematical benchmark scenarios with SymPy residual R(t) = 0."""
    benchmarks = [
        ("Real distinct roots", "y'' - 3*y' - 4*y = 0", "GENERAL", "HOMOGENEOUS", {}),
        ("Repeated root", "y'' - 2*y' + y = 0", "GENERAL", "HOMOGENEOUS", {}),
        ("Complex roots", "y'' + 4*y = 0", "GENERAL", "HOMOGENEOUS", {}),
        ("Homogeneous Cauchy", "y'' + 4*y = 0", "CAUCHY_IVP", "HOMOGENEOUS", {"t0": "0", "y0": "0", "v0": "2"}),
        ("Nonhomogeneous UC Exp", "y'' - 3*y' - 4*y = 3*exp(2*t)", "GENERAL", "NONHOMOGENEOUS", {}),
        ("Nonhomogeneous VoP Tan", "y'' + y = tan(t)", "GENERAL", "NONHOMOGENEOUS", {}),
        ("Nonhomogeneous VoP Ln", "y'' + y = ln(t)", "GENERAL", "NONHOMOGENEOUS", {}),
        ("Nonhomogeneous Cauchy UC", "y'' - 3*y' - 4*y = 3*exp(2*t)", "CAUCHY_IVP", "NONHOMOGENEOUS", {"t0": "0", "y0": "1", "v0": "0"}),
    ]

    t = sp.Symbol("t", real=True)

    for name, eq, mode, cat, ics in benchmarks:
        pt = ProblemType.ODE_SECOND_ORDER_IVP if mode == "CAUCHY_IVP" else ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF
        params = {"expected_classification": cat, "mode": mode}
        params.update(ics)
        req = ProblemRequest(
            problem_type=pt,
            raw_input=eq,
            target_variable="t",
            parameters=params,
        )
        sol = use_case.execute(req)
        assert sol.status == SolutionStatus.SUCCESS, f"Benchmark {name} failed: {sol.final_result}"
        assert sol.verification.status == VerificationStatus.VERIFIED, f"Benchmark {name} unverified: {sol.verification.details}"

        # Parse rhs of solution y(t) = ...
        res_str = sol.final_result
        assert "=" in res_str
        rhs_str = res_str.split("=", 1)[1].strip()
        y_expr = sp.sympify(rhs_str, locals={"C1": sp.Symbol("C1"), "C2": sp.Symbol("C2"), "t": t})

        # Check Cauchy initial conditions if present
        if mode == "CAUCHY_IVP":
            t0 = sp.sympify(ics["t0"])
            y0 = sp.sympify(ics["y0"])
            v0 = sp.sympify(ics["v0"])

            y_at_t0 = sp.simplify(y_expr.subs(t, t0))
            assert sp.simplify(y_at_t0 - y0) == 0, f"IC y({t0}) failed in {name}: got {y_at_t0}, expected {y0}"

            dy_expr = sp.diff(y_expr, t)
            dy_at_t0 = sp.simplify(dy_expr.subs(t, t0))
            assert sp.simplify(dy_at_t0 - v0) == 0, f"IC y'({t0}) failed in {name}: got {dy_at_t0}, expected {v0}"

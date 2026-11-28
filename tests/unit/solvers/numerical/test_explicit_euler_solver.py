"""Comprehensive unit tests for ExplicitEulerSolver and AnalyticalComparisonService."""

from __future__ import annotations

import math

import pytest

from math_app.application.use_cases.solve_numerical_ode import SolveNumericalODEUseCase
from math_app.domain.numerical_ode import (
    NumericalODEMethod,
    NumericalODEOrder,
    NumericalODERequest,
    NumericalODEStatus,
)
from math_app.main import build_application, build_numerical_ode_use_case
from math_app.solvers.numerical.explicit_euler_solver import ExplicitEulerSolver


def _make_use_case(*, with_analytical: bool = True) -> SolveNumericalODEUseCase:
    if with_analytical:
        app_uc = build_application()
        return app_uc._numerical_ode_use_case  # type: ignore[attr-defined]
    return build_numerical_ode_use_case(None)


# =============================================================================
# 7.1 First-Order Test Cases (Tests A - F)
# =============================================================================


def test_first_order_test_a_exponential_growth() -> None:
    """Test A: y' = y, y(0) = 1, h = 0.1, T = 1 -> y_n = (1.1)^n, y_10 = 2.5937424601."""
    uc = _make_use_case(with_analytical=True)
    req = NumericalODERequest(
        raw_equation="y' = y",
        order=NumericalODEOrder.FIRST_ORDER,
        t0="0",
        y0="1",
        t_end="1",
        step_size="0.1",
    )
    resp = uc.execute(req)

    assert resp.status == NumericalODEStatus.SUCCESS
    assert resp.total_steps == 10
    assert len(resp.rows) == 11
    assert resp.final_t == pytest.approx(1.0, abs=1e-12)
    assert resp.final_y == pytest.approx(2.5937424601, rel=1e-12, abs=1e-12)

    for n, row in enumerate(resp.rows):
        expected_y = 1.1**n
        assert row.t == pytest.approx(n * 0.1, abs=1e-12)
        assert row.y == pytest.approx(expected_y, rel=1e-12, abs=1e-12)
        assert row.slope_y == pytest.approx(expected_y, rel=1e-12, abs=1e-12)

    assert resp.verification is not None and resp.verification.is_verified is True
    assert resp.analytical_comparison is not None and resp.analytical_comparison.available is True
    assert resp.analytical_comparison.points[-1].y_exact == pytest.approx(math.e, rel=1e-12)
    assert resp.analytical_comparison.final_abs_error == pytest.approx(math.e - 2.5937424601, rel=1e-10)
    assert resp.analytical_comparison.final_abs_error > 0.1


@pytest.mark.parametrize(
    ("h_str", "expected_steps"),
    [("0.2", 5), ("0.1", 10), ("0.05", 20)],
)
def test_first_order_test_b_exponential_decay_multiple_steps(h_str: str, expected_steps: int) -> None:
    """Test B: y' = -2y, y(0) = 1 across multiple step sizes; compare with e^(-2t)."""
    uc = _make_use_case(with_analytical=True)
    h_val = float(h_str)
    req = NumericalODERequest(
        raw_equation="y' = -2*y",
        order=NumericalODEOrder.FIRST_ORDER,
        t0="0",
        y0="1",
        t_end="1",
        step_size=h_str,
    )
    resp = uc.execute(req)

    assert resp.status == NumericalODEStatus.SUCCESS
    assert resp.total_steps == expected_steps
    factor = 1.0 - 2.0 * h_val
    for n, row in enumerate(resp.rows):
        assert row.y == pytest.approx(factor**n, rel=1e-12, abs=1e-12)

    assert resp.analytical_comparison is not None and resp.analytical_comparison.available is True
    assert resp.analytical_comparison.points[-1].y_exact == pytest.approx(math.exp(-2.0), rel=1e-12)


def test_first_order_test_c_constant_derivative_exact_linear() -> None:
    """Test C: y' = 3, y(0) = 2 reproduces exact linear solution y(t) = 2 + 3t."""
    uc = _make_use_case(with_analytical=True)
    req = NumericalODERequest(
        raw_equation="y' = 3",
        order=NumericalODEOrder.FIRST_ORDER,
        t0="0",
        y0="2",
        t_end="2",
        step_size="0.25",
    )
    resp = uc.execute(req)

    assert resp.status == NumericalODEStatus.SUCCESS
    for row in resp.rows:
        exact = 2.0 + 3.0 * row.t
        assert row.y == pytest.approx(exact, abs=1e-12)
        assert row.slope_y == pytest.approx(3.0, abs=1e-12)
    assert resp.final_y == pytest.approx(8.0, abs=1e-12)
    assert resp.analytical_comparison is not None and resp.analytical_comparison.available is True
    assert resp.analytical_comparison.max_abs_error == pytest.approx(0.0, abs=1e-12)


def test_first_order_test_d_nonhomogeneous_consecutive_iterations() -> None:
    """Test D: y' = t + y, y(0) = 1, h = 0.1 verified against hand recurrence."""
    uc = _make_use_case(with_analytical=True)
    req = NumericalODERequest(
        raw_equation="y' = t + y",
        order=NumericalODEOrder.FIRST_ORDER,
        t0="0",
        y0="1",
        t_end="0.5",
        step_size="0.1",
    )
    resp = uc.execute(req)
    assert resp.status == NumericalODEStatus.SUCCESS

    t, y, h = 0.0, 1.0, 0.1
    for n in range(5):
        assert resp.rows[n].t == pytest.approx(t, abs=1e-12)
        assert resp.rows[n].y == pytest.approx(y, abs=1e-12)
        slope = t + y
        assert resp.rows[n].slope_y == pytest.approx(slope, abs=1e-12)
        y = y + h * slope
        t = (n + 1) * h
    assert resp.final_y == pytest.approx(y, abs=1e-12)


def test_first_order_test_e_backward_integration() -> None:
    """Test E: Backward integration on [1, 0] for y' = -y, y(1) = 1."""
    uc = _make_use_case(with_analytical=True)
    req = NumericalODERequest(
        raw_equation="y' = -y",
        order=NumericalODEOrder.FIRST_ORDER,
        t0="1",
        y0="1",
        t_end="0",
        step_size="0.2",
    )
    resp = uc.execute(req)
    assert resp.status == NumericalODEStatus.SUCCESS
    assert resp.direction == -1
    assert resp.total_steps == 5
    assert resp.final_t == pytest.approx(0.0, abs=1e-12)

    # With h_n = -0.2 and slope = -y_n: y_{n+1} = y_n + (-0.2)*(-y_n) = 1.2 * y_n
    for n, row in enumerate(resp.rows):
        assert row.t == pytest.approx(1.0 - 0.2 * n, abs=1e-12)
        assert row.y == pytest.approx(1.2**n, rel=1e-12, abs=1e-12)
    assert resp.verification is not None and resp.verification.is_verified is True


def test_first_order_test_f_non_divisible_interval_no_overshoot() -> None:
    """Test F: [0, 1] with h = 0.3 uses 3 full steps + 1 shortened step h_3 = 0.1 without overshooting."""
    uc = _make_use_case(with_analytical=False)
    req = NumericalODERequest(
        raw_equation="y' = y",
        order=NumericalODEOrder.FIRST_ORDER,
        t0="0",
        y0="1",
        t_end="1",
        step_size="0.3",
    )
    resp = uc.execute(req)

    assert resp.status == NumericalODEStatus.SUCCESS
    assert resp.total_steps == 4
    assert resp.has_shortened_final_step is True
    assert resp.final_step_size == pytest.approx(0.1, abs=1e-12)
    assert [r.t for r in resp.rows] == pytest.approx([0.0, 0.3, 0.6, 0.9, 1.0], abs=1e-12)
    expected_y4 = (1.3**3) * 1.1
    assert resp.final_y == pytest.approx(expected_y4, rel=1e-12)
    assert resp.verification is not None and resp.verification.is_verified is True


def test_first_order_nonlinear_omits_unavailable_analytical_comparison() -> None:
    """Nonlinear 1st-order ODE y' = sin(t*y) solves numerically and omits unavailable analytical comparison."""
    uc = _make_use_case(with_analytical=True)
    req = NumericalODERequest(
        raw_equation="y' = sin(t*y)",
        order=NumericalODEOrder.FIRST_ORDER,
        t0="0",
        y0="1",
        t_end="0.4",
        step_size="0.2",
    )
    resp = uc.execute(req)
    assert resp.status == NumericalODEStatus.SUCCESS
    assert resp.verification is not None and resp.verification.is_verified is True
    assert resp.analytical_comparison is not None and resp.analytical_comparison.available is False


# =============================================================================
# 7.2 Second-Order Test Cases (Tests G - J)
# =============================================================================


def test_second_order_test_g_simple_harmonic_oscillator_simultaneous_updates() -> None:
    """Test G: y'' = -y, y(0)=0, y'(0)=1; explicitly distinguishes simultaneous Euler from semi-implicit Euler."""
    uc = _make_use_case(with_analytical=True)
    req = NumericalODERequest(
        raw_equation="y'' = -y",
        order=NumericalODEOrder.SECOND_ORDER,
        t0="0",
        y0="0",
        v0="1",
        t_end="0.3",
        step_size="0.1",
    )
    resp = uc.execute(req)
    assert resp.status == NumericalODEStatus.SUCCESS
    assert resp.total_steps == 3

    # Step 0: y0=0, v0=1, F0=0 -> y1 = 0 + 0.1*1 = 0.1, v1 = 1 + 0.1*0 = 1.0
    assert resp.rows[1].y == pytest.approx(0.1, abs=1e-12)
    assert resp.rows[1].v == pytest.approx(1.0, abs=1e-12)

    # Step 1: y1=0.1, v1=1.0, F1=-0.1 -> y2 = 0.1 + 0.1*1.0 = 0.2, v2 = 1.0 + 0.1*(-0.1) = 0.99
    assert resp.rows[2].y == pytest.approx(0.2, abs=1e-12)
    assert resp.rows[2].v == pytest.approx(0.99, abs=1e-12)

    # Step 2: y2=0.2, v2=0.99, F2=-0.2 -> y3 = 0.2 + 0.1*0.99 = 0.299, v3 = 0.99 + 0.1*(-0.2) = 0.97
    assert resp.rows[3].y == pytest.approx(0.299, abs=1e-12)
    assert resp.rows[3].v == pytest.approx(0.97, abs=1e-12)
    assert resp.verification is not None and resp.verification.is_verified is True
    assert resp.analytical_comparison is not None and resp.analytical_comparison.available is True
    assert resp.analytical_comparison.points[-1].y_exact == pytest.approx(math.sin(0.3), rel=1e-12)


def test_second_order_test_h_constant_velocity_exact_linear() -> None:
    """Test H: y'' = 0, y(0) = 2, y'(0) = 3 produces exact y(t) = 2 + 3t."""
    uc = _make_use_case(with_analytical=True)
    req = NumericalODERequest(
        raw_equation="y'' = 0",
        order=NumericalODEOrder.SECOND_ORDER,
        t0="0",
        y0="2",
        v0="3",
        t_end="2",
        step_size="0.5",
    )
    resp = uc.execute(req)
    assert resp.status == NumericalODEStatus.SUCCESS
    for row in resp.rows:
        assert row.y == pytest.approx(2.0 + 3.0 * row.t, abs=1e-12)
        assert row.v == pytest.approx(3.0, abs=1e-12)
    assert resp.final_y == pytest.approx(8.0, abs=1e-12)
    assert resp.final_v == pytest.approx(3.0, abs=1e-12)


def test_second_order_test_i_nonhomogeneous_equation() -> None:
    """Test I: y'' + y = t, y(0) = 1, y'(0) = 0 -> exact y(t) = cos(t) - sin(t) + t."""
    uc = _make_use_case(with_analytical=True)
    req = NumericalODERequest(
        raw_equation="y'' + y = t",
        order=NumericalODEOrder.SECOND_ORDER,
        t0="0",
        y0="1",
        v0="0",
        t_end="0.3",
        step_size="0.1",
    )
    resp = uc.execute(req)
    assert resp.status == NumericalODEStatus.SUCCESS

    # Step 0: y0=1, v0=0, F0=0-1=-1 -> y1=1.0, v1=-0.1
    assert resp.rows[1].y == pytest.approx(1.0, abs=1e-12)
    assert resp.rows[1].v == pytest.approx(-0.1, abs=1e-12)
    # Step 1: y1=1.0, v1=-0.1, F1=0.1-1.0=-0.9 -> y2=0.99, v2=-0.19
    assert resp.rows[2].y == pytest.approx(0.99, abs=1e-12)
    assert resp.rows[2].v == pytest.approx(-0.19, abs=1e-12)
    # Step 2: y2=0.99, v2=-0.19, F2=0.2-0.99=-0.79 -> y3=0.971, v3=-0.269
    assert resp.rows[3].y == pytest.approx(0.971, abs=1e-12)
    assert resp.rows[3].v == pytest.approx(-0.269, abs=1e-12)

    assert resp.analytical_comparison is not None and resp.analytical_comparison.available is True
    exact_03 = math.cos(0.3) - math.sin(0.3) + 0.3
    assert resp.analytical_comparison.points[-1].y_exact == pytest.approx(exact_03, rel=1e-12)


def test_second_order_test_j_euler_cauchy_positive_negative_and_singularity_guard() -> None:
    """Test J: Euler-Cauchy numerical support on t>0 and t<0, plus strict rejection of t=0 crossings."""
    uc = _make_use_case(with_analytical=True)

    # Positive regular interval [1, 2]
    req_pos = NumericalODERequest(
        raw_equation="t^2*y'' - t*y' + y = t^2",
        order=NumericalODEOrder.SECOND_ORDER,
        t0="1",
        y0="0",
        v0="0",
        t_end="2",
        step_size="0.1",
    )
    resp_pos = uc.execute(req_pos)
    assert resp_pos.status == NumericalODEStatus.SUCCESS
    assert resp_pos.is_euler_cauchy_transformed is True
    assert resp_pos.verification is not None and resp_pos.verification.is_verified is True
    assert resp_pos.analytical_comparison is not None and resp_pos.analytical_comparison.available is True

    # Negative regular interval [-2, -1]
    req_neg = NumericalODERequest(
        raw_equation="t^2*y'' + 4*t*y' + 2*y = 0",
        order=NumericalODEOrder.SECOND_ORDER,
        t0="-2",
        y0="1",
        v0="0",
        t_end="-1",
        step_size="0.25",
    )
    resp_neg = uc.execute(req_neg)
    assert resp_neg.status == NumericalODEStatus.SUCCESS
    assert resp_neg.is_euler_cauchy_transformed is True
    assert resp_neg.verification is not None and resp_neg.verification.is_verified is True

    # Singular intervals crossing or touching t = 0 MUST be rejected
    for bad_t0, bad_end in [("-1", "1"), ("0", "1"), ("-1", "0"), ("1", "-1")]:
        bad_req = NumericalODERequest(
            raw_equation="t^2*y'' + 4*t*y' + 2*y = 0",
            order=NumericalODEOrder.SECOND_ORDER,
            t0=bad_t0,
            y0="1",
            v0="0",
            t_end=bad_end,
            step_size="0.1",
        )
        bad_resp = uc.execute(bad_req)
        assert bad_resp.status == NumericalODEStatus.SINGULARITY_ERROR
        assert "0" in bad_resp.error_message


# =============================================================================
# 7.3 Invalid Inputs, Security & Singularities
# =============================================================================


@pytest.mark.parametrize(
    ("kwargs", "expected_status", "msg_fragment"),
    [
        ({"step_size": "0"}, NumericalODEStatus.INVALID_INPUT, "h > 0"),
        ({"step_size": "-0.1"}, NumericalODEStatus.INVALID_INPUT, "h > 0"),
        ({"t0": "1", "t_end": "1"}, NumericalODEStatus.INVALID_INPUT, "khác nhau"),
        ({"y0": ""}, NumericalODEStatus.INVALID_INPUT, "y₀"),
        ({"order": NumericalODEOrder.SECOND_ORDER, "raw_equation": "y'' = -y", "v0": ""}, NumericalODEStatus.INVALID_INPUT, "v₀"),
        ({"t0": "nan"}, NumericalODEStatus.INVALID_INPUT, "hữu hạn"),
        ({"t_end": "oo"}, NumericalODEStatus.INVALID_INPUT, "hữu hạn"),
        ({"step_size": "inf"}, NumericalODEStatus.INVALID_INPUT, "hữu hạn"),
        ({"raw_equation": "y' = ("}, NumericalODEStatus.INVALID_INPUT, ""),
        ({"raw_equation": "y' = __import__('os').system('ls')"}, NumericalODEStatus.INVALID_INPUT, ""),
        ({"raw_equation": "y' = k*y"}, NumericalODEStatus.INVALID_INPUT, "không xác định"),
        ({"raw_equation": "y'' = -y", "order": NumericalODEOrder.FIRST_ORDER}, NumericalODEStatus.INVALID_INPUT, "cấp 2"),
        ({"raw_equation": "y' = y", "order": NumericalODEOrder.SECOND_ORDER, "v0": "1"}, NumericalODEStatus.INVALID_INPUT, "cấp 1"),
        ({"raw_equation": "y' = 1/(t - 0.5)", "t0": "0", "t_end": "1", "step_size": "0.1"}, NumericalODEStatus.SINGULARITY_ERROR, "kỳ dị"),
        ({"raw_equation": "y' = log(y)", "t0": "0", "y0": "-1", "t_end": "1", "step_size": "0.1"}, NumericalODEStatus.NUMERICAL_ERROR, "logarit"),
        ({"raw_equation": "y' = sqrt(y)", "t0": "0", "y0": "-4", "t_end": "1", "step_size": "0.1"}, NumericalODEStatus.NUMERICAL_ERROR, "số âm"),
        ({"raw_equation": "y' = tan(t)", "t0": "0", "y0": "0", "t_end": "2", "step_size": "0.1"}, NumericalODEStatus.SINGULARITY_ERROR, "tan"),
        ({"t0": "0", "t_end": "200", "step_size": "0.01", "max_steps": 10_000}, NumericalODEStatus.ITERATION_LIMIT_EXCEEDED, "10,000"),
    ],
)
def test_invalid_inputs_and_singularities(
    kwargs: dict[str, object],
    expected_status: NumericalODEStatus,
    msg_fragment: str,
) -> None:
    """Every invalid input, unsafe expression, singularity, or limit exceedance returns a structured error."""
    solver = ExplicitEulerSolver()
    base = {
        "raw_equation": "y' = y",
        "order": NumericalODEOrder.FIRST_ORDER,
        "t0": "0",
        "y0": "1",
        "t_end": "1",
        "step_size": "0.1",
        "v0": None,
        "method": NumericalODEMethod.EXPLICIT_EULER,
        "max_steps": 10_000,
        "compute_analytical_comparison": False,
    }
    base.update(kwargs)
    req = NumericalODERequest(**base)  # type: ignore[arg-type]
    resp = solver.solve(req)
    assert resp.status == expected_status
    if msg_fragment:
        assert msg_fragment in resp.error_message


def test_overflow_at_failing_step() -> None:
    """Fast-growing equation y' = y^2 from y(0)=1000 reports NUMERICAL_ERROR with failing_step."""
    solver = ExplicitEulerSolver()
    req = NumericalODERequest(
        raw_equation="y' = y^2",
        order=NumericalODEOrder.FIRST_ORDER,
        t0="0",
        y0="1000",
        t_end="1",
        step_size="0.1",
    )
    resp = solver.solve(req)
    assert resp.status == NumericalODEStatus.NUMERICAL_ERROR
    assert resp.failing_step is not None and resp.failing_step >= 0
    assert f"n = {resp.failing_step}" in resp.error_message

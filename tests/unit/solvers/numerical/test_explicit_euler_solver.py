"""Comprehensive mathematical, error-analysis, and edge-case tests for ExplicitEulerSolver."""

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
# 1. First-Order Mathematical Test Cases
# =============================================================================


def test_first_order_test_a_exponential_growth() -> None:
    """y' = y, y(0) = 1, h = 0.1, T = 1 -> y_n = (1.1)^n, y_10 = 2.5937424601."""
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


@pytest.mark.parametrize(
    ("h_str", "expected_steps"),
    [("0.2", 5), ("0.1", 10), ("0.05", 20)],
)
def test_first_order_test_b_exponential_decay_multiple_steps(h_str: str, expected_steps: int) -> None:
    """y' = -2y, y(0) = 1 across multiple step sizes; compare with e^(-2t)."""
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
    """y' = 3, y(0) = 2 reproduces exact linear solution y(t) = 2 + 3t with zero defects."""
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
    assert resp.error_analysis is not None
    assert resp.error_analysis.has_exact_reference is True
    assert resp.error_analysis.max_global_error_y == pytest.approx(0.0, abs=1e-12)
    assert resp.error_analysis.max_abs_local_defect_y == pytest.approx(0.0, abs=1e-12)


def test_first_order_test_d_nonhomogeneous_consecutive_iterations() -> None:
    """y' = t + y, y(0) = 1, h = 0.1 verified against hand recurrence and exact solution 2e^t - t - 1."""
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
    exact_05 = 2.0 * math.exp(0.5) - 1.5
    assert resp.error_analysis is not None
    assert resp.error_analysis.final_global_error_y == pytest.approx(abs(exact_05 - y), rel=1e-12)


def test_first_order_test_e_backward_integration() -> None:
    """Backward integration on [1, 0] for y' = -y, y(1) = 1 with positive displayed h = 0.2."""
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
    assert resp.step_size == pytest.approx(0.2, abs=1e-12)
    assert resp.total_steps == 5
    assert resp.final_t == pytest.approx(0.0, abs=1e-12)

    for n, row in enumerate(resp.rows):
        assert row.t == pytest.approx(1.0 - 0.2 * n, abs=1e-12)
        assert row.y == pytest.approx(1.2**n, rel=1e-12, abs=1e-12)
    assert resp.verification is not None and resp.verification.is_verified is True


def test_first_order_test_f_non_divisible_interval_no_overshoot() -> None:
    """[0, 1] with h = 0.3 uses 3 full steps + 1 shortened step h_3 = 0.1 without overshooting."""
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
    # Step halving still aligns all coarse nodes including shortened final step!
    assert resp.error_analysis is not None
    assert resp.error_analysis.step_halving is not None
    assert resp.error_analysis.step_halving.available is True
    assert [pt.t for pt in resp.error_analysis.step_halving.points] == pytest.approx([0.0, 0.3, 0.6, 0.9, 1.0], abs=1e-12)


# =============================================================================
# 2. Second-Order Mathematical Test Cases
# =============================================================================


def test_second_order_test_g_simple_harmonic_oscillator_simultaneous_updates() -> None:
    """y'' = -y, y(0)=0, y'(0)=1; verifies simultaneous Euler update and both position & derivative errors."""
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

    # Step 0: y0=0, v0=1, F0=0 -> y1=0.1, v1=1.0
    assert resp.rows[1].y == pytest.approx(0.1, abs=1e-12)
    assert resp.rows[1].v == pytest.approx(1.0, abs=1e-12)
    # Step 1: y1=0.1, v1=1.0, F1=-0.1 -> y2=0.2, v2=0.99
    assert resp.rows[2].y == pytest.approx(0.2, abs=1e-12)
    assert resp.rows[2].v == pytest.approx(0.99, abs=1e-12)
    # Step 2: y2=0.2, v2=0.99, F2=-0.2 -> y3=0.299, v3=0.97
    assert resp.rows[3].y == pytest.approx(0.299, abs=1e-12)
    assert resp.rows[3].v == pytest.approx(0.97, abs=1e-12)
    assert resp.final_y == pytest.approx(0.299, abs=1e-12)
    assert resp.final_v == pytest.approx(0.97, abs=1e-12)

    assert resp.verification is not None and resp.verification.is_verified is True
    assert resp.analytical_comparison is not None and resp.analytical_comparison.available is True
    assert resp.analytical_comparison.points[-1].y_exact == pytest.approx(math.sin(0.3), rel=1e-12)
    assert resp.analytical_comparison.points[-1].v_exact == pytest.approx(math.cos(0.3), rel=1e-12)
    assert resp.analytical_comparison.final_v_abs_error == pytest.approx(abs(math.cos(0.3) - 0.97), rel=1e-12)


def test_second_order_test_h_constant_velocity_exact_linear() -> None:
    """y'' = 0, y(0) = 2, y'(0) = 3 produces exact y(t) = 2 + 3t and v(t) = 3."""
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
    assert resp.error_analysis is not None
    assert resp.error_analysis.max_global_error_y == pytest.approx(0.0, abs=1e-12)
    assert resp.error_analysis.max_global_error_v == pytest.approx(0.0, abs=1e-12)
    assert resp.error_analysis.max_abs_local_defect_y == pytest.approx(0.0, abs=1e-12)
    assert resp.error_analysis.max_abs_local_defect_v == pytest.approx(0.0, abs=1e-12)


def test_second_order_test_i_nonhomogeneous_equation() -> None:
    """y'' + y = t, y(0) = 1, y'(0) = 0 -> exact y(t) = cos(t) - sin(t) + t."""
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
    assert resp.rows[1].y == pytest.approx(1.0, abs=1e-12)
    assert resp.rows[1].v == pytest.approx(-0.1, abs=1e-12)
    assert resp.rows[2].y == pytest.approx(0.99, abs=1e-12)
    assert resp.rows[2].v == pytest.approx(-0.19, abs=1e-12)
    assert resp.rows[3].y == pytest.approx(0.971, abs=1e-12)
    assert resp.rows[3].v == pytest.approx(-0.269, abs=1e-12)

    assert resp.analytical_comparison is not None and resp.analytical_comparison.available is True
    exact_03 = math.cos(0.3) - math.sin(0.3) + 0.3
    exact_v03 = -math.sin(0.3) - math.cos(0.3) + 1.0
    assert resp.analytical_comparison.points[-1].y_exact == pytest.approx(exact_03, rel=1e-12)
    assert resp.analytical_comparison.points[-1].v_exact == pytest.approx(exact_v03, rel=1e-12)


def test_second_order_nonuniform_final_step_and_backward_integration() -> None:
    """Second-order ODE supports nonuniform final step and backward integration cleanly."""
    uc = _make_use_case(with_analytical=True)

    # Nonuniform final step on [0, 1] with h = 0.3 for y'' = -y, y(0)=0, y'(0)=1
    resp_nu = uc.execute(
        NumericalODERequest(
            raw_equation="y'' = -y",
            order=NumericalODEOrder.SECOND_ORDER,
            t0="0",
            y0="0",
            v0="1",
            t_end="1",
            step_size="0.3",
        )
    )
    assert resp_nu.status == NumericalODEStatus.SUCCESS
    assert resp_nu.has_shortened_final_step is True
    assert resp_nu.final_step_size == pytest.approx(0.1, abs=1e-12)
    assert [r.t for r in resp_nu.rows] == pytest.approx([0.0, 0.3, 0.6, 0.9, 1.0], abs=1e-12)
    assert resp_nu.verification is not None and resp_nu.verification.is_verified is True

    # Backward integration [1, 0] for y'' - 3*y' + 2*y = 0, y(1)=1, y'(1)=0
    resp_bw = uc.execute(
        NumericalODERequest(
            raw_equation="y'' - 3*y' + 2*y = 0",
            order=NumericalODEOrder.SECOND_ORDER,
            t0="1",
            y0="1",
            v0="0",
            t_end="0",
            step_size="0.25",
        )
    )
    assert resp_bw.status == NumericalODEStatus.SUCCESS
    assert resp_bw.direction == -1
    assert resp_bw.step_size == pytest.approx(0.25, abs=1e-12)
    assert [r.t for r in resp_bw.rows] == pytest.approx([1.0, 0.75, 0.5, 0.25, 0.0], abs=1e-12)
    assert resp_bw.verification is not None and resp_bw.verification.is_verified is True
    assert resp_bw.analytical_comparison is not None and resp_bw.analytical_comparison.available is True


def test_second_order_test_j_euler_cauchy_positive_negative_and_singularity_guard() -> None:
    """Euler-Cauchy numerical support on t>0 and t<0, plus strict rejection of t=0 crossings."""
    uc = _make_use_case(with_analytical=True)

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
# 3. Rigorous Local & Global Error-Analysis Verification
# =============================================================================


def test_error_analysis_local_defect_global_error_and_convergence_scaling() -> None:
    """Independently verify unnormalized local defect O(h^2), global error O(h), and Richardson scaling."""
    uc = _make_use_case(with_analytical=True)

    # First-order y' = y, y(0)=1 at h=0.1 and h=0.05
    r_coarse = uc.execute(
        NumericalODERequest(
            raw_equation="y' = y",
            order=NumericalODEOrder.FIRST_ORDER,
            t0="0",
            y0="1",
            t_end="1",
            step_size="0.1",
        )
    )
    r_fine = uc.execute(
        NumericalODERequest(
            raw_equation="y' = y",
            order=NumericalODEOrder.FIRST_ORDER,
            t0="0",
            y0="1",
            t_end="1",
            step_size="0.05",
        )
    )

    assert r_coarse.error_analysis is not None and r_coarse.error_analysis.has_exact_reference is True
    assert r_coarse.error_analysis.local_error_order_label == "O(h²)"
    assert r_coarse.error_analysis.global_error_order_label == "O(h)"
    assert r_coarse.analytical_comparison is not None

    # Independently check unnormalized local defect delta_n = e^{t_n} - e^{t_{n-1}} - h*e^{t_{n-1}}
    assert r_coarse.analytical_comparison.points[0].local_defect_y is None
    expected_def_1 = math.exp(0.1) - 1.0 - 0.1 * 1.0
    assert r_coarse.analytical_comparison.points[1].local_defect_y == pytest.approx(expected_def_1, rel=1e-12)
    expected_def_final = math.exp(1.0) - math.exp(0.9) - 0.1 * math.exp(0.9)
    assert r_coarse.error_analysis.final_local_defect_y == pytest.approx(expected_def_final, rel=1e-11)

    # Halving step size shrinks single-step local defect by ~4x (O(h^2)) and global error by ~2x (O(h))
    def_1_fine = r_fine.analytical_comparison.points[1].local_defect_y  # type: ignore[union-attr]
    assert def_1_fine is not None
    ratio_local = abs(def_1_fine) / abs(expected_def_1)
    assert 0.22 <= ratio_local <= 0.27

    assert r_coarse.error_analysis.final_global_error_y is not None
    assert r_fine.error_analysis is not None and r_fine.error_analysis.final_global_error_y is not None
    ratio_global = r_fine.error_analysis.final_global_error_y / r_coarse.error_analysis.final_global_error_y
    assert 0.45 <= ratio_global <= 0.56

    # Richardson step-halving estimate matches independent 2 * |y_{h/2} - y_h|
    sh = r_coarse.error_analysis.step_halving
    assert sh is not None and sh.available is True
    assert sh.richardson_factor == 2.0
    assert sh.final_estimated_error_y == pytest.approx(
        2.0 * abs(r_fine.final_y - r_coarse.final_y),  # type: ignore[operator]
        rel=1e-11,
    )
    assert r_coarse.error_analysis.max_global_error_y == pytest.approx(
        max(pt.abs_error for pt in r_coarse.analytical_comparison.points),
        rel=1e-12,
    )


def test_error_analysis_second_order_local_defects_and_both_state_errors() -> None:
    """Independently verify 2nd-order local defects (delta^y, delta^v) and both E^y_n, E^v_n."""
    uc = _make_use_case(with_analytical=True)
    resp = uc.execute(
        NumericalODERequest(
            raw_equation="y'' = -y",
            order=NumericalODEOrder.SECOND_ORDER,
            t0="0",
            y0="0",
            v0="1",
            t_end="0.5",
            step_size="0.1",
        )
    )
    assert resp.status == NumericalODEStatus.SUCCESS
    ana = resp.analytical_comparison
    ea = resp.error_analysis
    assert ana is not None and ana.available is True
    assert ea is not None and ea.has_exact_reference is True

    # Independently derive y_exact(t) = sin(t), v_exact(t) = cos(t)
    expected_ey: list[float] = []
    expected_ev: list[float] = []
    expected_dy: list[float] = []
    expected_dv: list[float] = []
    for n, row in enumerate(resp.rows):
        pt = ana.points[n]
        y_ex = math.sin(row.t)
        v_ex = math.cos(row.t)
        ey = abs(y_ex - row.y)
        ev = abs(v_ex - float(row.v))  # type: ignore[arg-type]
        expected_ey.append(ey)
        expected_ev.append(ev)
        assert pt.abs_error == pytest.approx(ey, abs=1e-12)
        assert pt.v_abs_error == pytest.approx(ev, abs=1e-12)
        if n >= 1:
            t_prev = resp.rows[n - 1].t
            h_prev = row.t - t_prev
            dy = y_ex - math.sin(t_prev) - h_prev * math.cos(t_prev)
            dv = v_ex - math.cos(t_prev) - h_prev * (-math.sin(t_prev))
            expected_dy.append(abs(dy))
            expected_dv.append(abs(dv))
            assert pt.local_defect_y == pytest.approx(dy, abs=1e-12)
            assert pt.local_defect_v == pytest.approx(dv, abs=1e-12)

    assert ea.final_global_error_y == pytest.approx(expected_ey[-1], abs=1e-12)
    assert ea.max_global_error_y == pytest.approx(max(expected_ey), abs=1e-12)
    assert ea.final_global_error_v == pytest.approx(expected_ev[-1], abs=1e-12)
    assert ea.max_global_error_v == pytest.approx(max(expected_ev), abs=1e-12)
    assert ea.max_abs_local_defect_y == pytest.approx(max(expected_dy), abs=1e-12)
    assert ea.max_abs_local_defect_v == pytest.approx(max(expected_dv), abs=1e-12)


@pytest.mark.parametrize(
    ("eq", "order", "v0"),
    [
        ("y' = sin(t*y)", NumericalODEOrder.FIRST_ORDER, None),
        ("y'' = -sin(y)", NumericalODEOrder.SECOND_ORDER, "0"),
    ],
)
def test_no_fabricated_exact_errors_when_analytical_solution_unavailable(
    eq: str,
    order: NumericalODEOrder,
    v0: str | None,
) -> None:
    """When no analytical reference exists, exact error fields stay None while Richardson h/2 is labeled as estimate."""
    uc = _make_use_case(with_analytical=True)
    resp = uc.execute(
        NumericalODERequest(
            raw_equation=eq,
            order=order,
            t0="0",
            y0="1",
            v0=v0,
            t_end="0.4",
            step_size="0.1",
            compute_analytical_comparison=True,
        )
    )
    assert resp.status == NumericalODEStatus.SUCCESS
    assert resp.verification is not None and resp.verification.is_verified is True
    assert resp.analytical_comparison is not None and resp.analytical_comparison.available is False

    ea = resp.error_analysis
    assert ea is not None
    assert ea.has_exact_reference is False
    assert ea.final_global_error_y is None
    assert ea.max_global_error_y is None
    assert ea.final_global_error_v is None
    assert ea.max_global_error_v is None
    assert ea.final_local_defect_y is None
    assert ea.max_abs_local_defect_y is None
    assert ea.final_local_defect_v is None
    assert ea.max_abs_local_defect_v is None
    assert ea.local_error_order_label == "O(h²)"
    assert ea.global_error_order_label == "O(h)"
    assert ea.step_halving is not None and ea.step_halving.available is True
    assert "ước lượng" in ea.step_halving.notes.lower()


# =============================================================================
# 4. Invalid Inputs, Security & Singularities
# =============================================================================


@pytest.mark.parametrize(
    ("kwargs", "expected_status", "msg_fragment"),
    [
        ({"step_size": "0"}, NumericalODEStatus.INVALID_INPUT, "h > 0"),
        ({"step_size": "-0.1"}, NumericalODEStatus.INVALID_INPUT, "h > 0"),
        ({"t0": "1", "t_end": "1"}, NumericalODEStatus.INVALID_INPUT, "khác nhau"),
        ({"y0": ""}, NumericalODEStatus.INVALID_INPUT, "y₀"),
        ({"t0": ""}, NumericalODEStatus.INVALID_INPUT, "t₀"),
        ({"order": NumericalODEOrder.SECOND_ORDER, "raw_equation": "y'' = -y", "v0": ""}, NumericalODEStatus.INVALID_INPUT, "v₀"),
        ({"order": NumericalODEOrder.SECOND_ORDER, "raw_equation": "y'' = -y", "v0": "nan"}, NumericalODEStatus.INVALID_INPUT, "hữu hạn"),
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


@pytest.mark.parametrize(
    ("raw_eq", "order", "v0"),
    [
        ("y' = y^2", NumericalODEOrder.FIRST_ORDER, None),
        ("y'' = y^2", NumericalODEOrder.SECOND_ORDER, "0"),
    ],
)
def test_overflow_at_failing_step(raw_eq: str, order: NumericalODEOrder, v0: str | None) -> None:
    """Fast-growing 1st- and 2nd-order equations report NUMERICAL_ERROR with failing_step."""
    solver = ExplicitEulerSolver()
    req = NumericalODERequest(
        raw_equation=raw_eq,
        order=order,
        t0="0",
        y0="1000",
        v0=v0,
        t_end="2",
        step_size="0.1",
    )
    resp = solver.solve(req)
    assert resp.status == NumericalODEStatus.NUMERICAL_ERROR
    assert resp.failing_step is not None and resp.failing_step >= 0
    assert f"n = {resp.failing_step}" in resp.error_message

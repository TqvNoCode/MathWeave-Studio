"""Independent numerical verifier tests and analytical regression protection tests."""

from __future__ import annotations

from dataclasses import replace

from math_app.application.dtos import ProblemRequest
from math_app.domain.models import ProblemType, SolutionStatus, VerificationStatus
from math_app.domain.numerical_ode import (
    AnalyticalComparisonPoint,
    NumericalIterationRow,
    NumericalODEOrder,
    NumericalODERequest,
    NumericalODEStatus,
)
from math_app.main import build_application
from math_app.verification.numerical.euler_verifier import ExplicitEulerVerifier


def test_verifier_passes_valid_first_order_second_order_and_large_grid() -> None:
    """Verifier passes all 10 independent checks on 1st-order, 2nd-order, and 1000-step problems."""
    app_uc = build_application()
    num_uc = app_uc._numerical_ode_use_case  # type: ignore[attr-defined]

    for req in (
        NumericalODERequest(raw_equation="y' = y", order=NumericalODEOrder.FIRST_ORDER, t0="0", y0="1", t_end="1", step_size="0.1"),
        NumericalODERequest(raw_equation="y'' = -y", order=NumericalODEOrder.SECOND_ORDER, t0="0", y0="0", v0="1", t_end="1", step_size="0.1"),
        NumericalODERequest(raw_equation="y' = -y", order=NumericalODEOrder.FIRST_ORDER, t0="0", y0="1", t_end="1", step_size="0.001", compute_analytical_comparison=False),
    ):
        resp = num_uc.execute(req)
        assert resp.status == NumericalODEStatus.SUCCESS
        assert resp.verification is not None
        assert resp.verification.is_verified is True
        assert len(resp.verification.checks) == 9
        assert all(c.passed for c in resp.verification.checks)
        assert resp.verification.max_recurrence_residual < 1e-11


def test_verifier_detects_tampered_recurrence_and_semi_implicit_bug() -> None:
    """Verifier catches tampered y_n, semi-implicit 2nd-order update, overshot endpoint, and bad count."""
    app_uc = build_application()
    num_uc = app_uc._numerical_ode_use_case  # type: ignore[attr-defined]
    verifier = ExplicitEulerVerifier()

    # 1. Tampered first-order y_1
    req1 = NumericalODERequest(raw_equation="y' = y", order=NumericalODEOrder.FIRST_ORDER, t0="0", y0="1", t_end="0.3", step_size="0.1", compute_analytical_comparison=False)
    resp1 = num_uc.execute(req1)
    bad_rows_1 = list(resp1.rows)
    bad_rows_1[1] = replace(bad_rows_1[1], y=bad_rows_1[1].y + 0.05)
    report1 = verifier.verify(req1, replace(resp1, rows=tuple(bad_rows_1)))
    assert report1.is_verified is False

    # 2. Semi-implicit 2nd-order bug (using y_{n+1} instead of y_n when computing v_{n+1})
    req2 = NumericalODERequest(raw_equation="y'' = -y", order=NumericalODEOrder.SECOND_ORDER, t0="0", y0="0", v0="1", t_end="0.3", step_size="0.1", compute_analytical_comparison=False)
    resp2 = num_uc.execute(req2)
    bad_rows_2 = list(resp2.rows)
    # In step 1 (y1=0.1, v1=1.0), true y2=0.2; semi-implicit uses F(t1, y2, v1)=-0.2 -> v2=0.98 instead of 0.99
    bad_rows_2[2] = replace(bad_rows_2[2], v=0.98)
    report2 = verifier.verify(req2, replace(resp2, rows=tuple(bad_rows_2)))
    assert report2.is_verified is False

    # 3. Overshot final endpoint
    bad_rows_3 = list(resp1.rows)
    bad_rows_3[-1] = replace(bad_rows_3[-1], t=0.35)
    report3 = verifier.verify(req1, replace(resp1, rows=tuple(bad_rows_3), final_t=0.35))
    assert report3.is_verified is False

    # 4. NaN value in row
    bad_rows_4 = list(resp1.rows)
    bad_rows_4[1] = replace(bad_rows_4[1], y=float("nan"))
    report4 = verifier.verify(req1, replace(resp1, rows=tuple(bad_rows_4)))
    assert report4.is_verified is False

    # 5. Inconsistent analytical comparison error
    resp5 = num_uc.execute(replace(req1, compute_analytical_comparison=True))
    assert resp5.analytical_comparison is not None
    bad_pts = list(resp5.analytical_comparison.points)
    bad_pts[0] = AnalyticalComparisonPoint(0, 0.0, 1.0, 1.0, 0.5)
    report5 = verifier.verify(req1, replace(resp5, analytical_comparison=replace(resp5.analytical_comparison, points=tuple(bad_pts))))
    assert report5.is_verified is False

    # 6. Bad iteration row count
    report6 = verifier.verify(req1, replace(resp1, rows=resp1.rows[:-1]))
    assert report6.is_verified is False

    # 7. Euler-Cauchy crossing zero rejected even if forged
    ec_req = NumericalODERequest(raw_equation="t^2*y'' + 4*t*y' + 2*y = 0", order=NumericalODEOrder.SECOND_ORDER, t0="-1", y0="1", v0="0", t_end="1", step_size="1")
    forged_ec = replace(
        resp2,
        t0=-1.0,
        t_end=1.0,
        rows=(
            NumericalIterationRow(0, -1.0, 1.0, 0.0, 1.0, 0.0, -2.0),
            NumericalIterationRow(1, 0.0, 1.0, -2.0, 1.0, -2.0, 0.0),
            NumericalIterationRow(2, 1.0, -1.0, -2.0, None, -2.0, 10.0),
        ),
        final_t=1.0,
        final_y=-1.0,
        final_v=-2.0,
        total_steps=2,
    )
    report7 = verifier.verify(ec_req, forged_ec)
    assert report7.is_verified is False


def test_existing_analytical_ode_solvers_remain_unchanged() -> None:
    """Regression check confirming analytical 1st-order, 2nd-order, and Euler-Cauchy solvers remain intact."""
    app_uc = build_application()

    r1 = app_uc.execute(ProblemRequest("y' = y, y(0) = 1", ProblemType.ODE_FIRST_ORDER_LINEAR, "t"))
    assert r1.status == SolutionStatus.SUCCESS
    assert r1.verification.status == VerificationStatus.VERIFIED
    assert "exp(t)" in r1.final_result

    r2 = app_uc.execute(
        ProblemRequest(
            "y'' + y = 0",
            ProblemType.ODE_SECOND_ORDER_IVP,
            "t",
            parameters={"problem_mode": "CAUCHY_IVP", "initial_condition": "y(0) = 0, y'(0) = 1"},
        )
    )
    assert r2.status == SolutionStatus.SUCCESS
    assert r2.verification.status == VerificationStatus.VERIFIED
    assert "sin(t)" in r2.final_result

    r3 = app_uc.execute(ProblemRequest("t^2*y'' - t*y' + y = t^2, t > 0", ProblemType.ODE_EULER_CAUCHY, "t"))
    assert r3.status == SolutionStatus.SUCCESS
    assert r3.verification.status == VerificationStatus.VERIFIED

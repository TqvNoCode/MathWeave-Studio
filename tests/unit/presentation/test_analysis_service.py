"""Unit tests for UI analysis service (2D, 3D plotting, and variation table)."""

import numpy as np

from math_app.presentation.services.analysis_service import (
    can_compute_variation_table,
    can_plot_2d,
    can_plot_3d,
    compute_variation_table,
    create_2d_plot,
    create_3d_plot,
    sample_function_2d,
)


def test_can_plot_2d_eligibility():
    assert can_plot_2d("x^2", "x") is True
    assert can_plot_2d("cos(x) - tan(x)", "x") is True
    # Matrix input is not eligible for 2D plot
    assert can_plot_2d("[[1, 2], [3, 4]]", "x") is False
    # Empty input is not eligible
    assert can_plot_2d("", "x") is False
    # Two-variable function is not eligible for 2D
    assert can_plot_2d("x^2 + y^2", "x") is False


def test_create_2d_plot():
    fig = create_2d_plot("x^2 - 4", "x")
    assert fig is not None
    assert len(fig.data) == 1
    assert fig.data[0].mode == "lines"


def test_2d_plot_sampling_arbitrary_viewport():
    """Verify plotting resamples across arbitrary viewports including x around -20 and 100."""
    # 1. sin(x) near origin
    res_origin = sample_function_2d("sin(x)", "x", -10.0, 10.0, 500)
    assert res_origin is not None
    xs_orig, ys_orig, _, _ = res_origin
    assert len(xs_orig) == 500
    assert np.all(np.isfinite(ys_orig))
    assert np.max(ys_orig) <= 1.001 and np.min(ys_orig) >= -1.001

    # 2. sin(x) panned to x around -20 (e.g. [-24, -4])
    res_panned = sample_function_2d("sin(x)", "x", -24.0, -4.0, 600)
    assert res_panned is not None
    xs_pan, ys_pan, _, _ = res_panned
    assert len(xs_pan) == 600
    assert np.all(np.isfinite(ys_pan))
    assert xs_pan[0] == -24.0 and xs_pan[-1] == -4.0

    # 3. y = x^3
    res_cubic = sample_function_2d("x^3", "x", -5.0, 5.0, 400)
    assert res_cubic is not None
    _, ys_cubic, _, _ = res_cubic
    assert np.all(np.isfinite(ys_cubic))

    # 4. y = exp(x)/(x^2 + 1)
    res_exp = sample_function_2d("exp(x)/(x^2 + 1)", "x", -5.0, 5.0, 400)
    assert res_exp is not None
    _, ys_exp, _, _ = res_exp
    assert np.all(np.isfinite(ys_exp))

    # 5. y = 1/(x - 1) with discontinuity/pole at x = 1
    res_pole = sample_function_2d("1/(x - 1)", "x", -4.0, 4.0, 800)
    assert res_pole is not None
    xs_p, ys_p, _, _ = res_pole
    # At least some points around x = 1 should be NaN to avoid drawing connecting line
    assert np.any(np.isnan(ys_p))

    # 6. y = sqrt(x) handles x < 0 without crashing by setting NaN
    res_sqrt = sample_function_2d("sqrt(x)", "x", -5.0, 5.0, 500)
    assert res_sqrt is not None
    xs_sq, ys_sq, _, _ = res_sqrt
    # Points with x < 0 must be NaN
    neg_mask = xs_sq < -0.01
    assert np.all(np.isnan(ys_sq[neg_mask]))
    # Points with x > 0 must be finite
    pos_mask = xs_sq > 0.1
    assert np.all(np.isfinite(ys_sq[pos_mask]))


def test_variation_table_regression_cases():
    """Verify all 3 required variation table regression cases (Cubic, Parabola, Rational with pole)."""
    # Example A: Strictly increasing cubic f(x) = 2x^3 + 6x - 8
    tbl_a = compute_variation_table("2*x^3 + 6*x - 8", "x")
    assert tbl_a is not None
    assert len(tbl_a["critical_points"]) == 0
    assert len(tbl_a["intervals"]) == 1
    int_a = tbl_a["intervals"][0]
    assert int_a["sign"] == "+"
    assert int_a["start_val"] == r"-\infty"
    assert int_a["end_val"] in (r"\infty", r"+\infty")
    assert "Đồng biến" in int_a["behavior"]

    # Example B: Parabola f(x) = x^2, f'(x) = 2x
    tbl_b = compute_variation_table("x^2", "x")
    assert tbl_b is not None
    assert len(tbl_b["critical_points"]) == 1
    assert tbl_b["critical_points"][0]["x"] == 0.0
    assert len(tbl_b["intervals"]) == 2
    # Interval 1: (-oo, 0), sign -
    assert tbl_b["intervals"][0]["sign"] == "-"
    assert tbl_b["intervals"][0]["start_val"] in (r"\infty", r"+\infty")
    assert tbl_b["intervals"][0]["end_val"] == "0"
    # Interval 2: (0, +oo), sign +
    assert tbl_b["intervals"][1]["sign"] == "+"
    assert tbl_b["intervals"][1]["start_val"] == "0"
    assert tbl_b["intervals"][1]["end_val"] in (r"\infty", r"+\infty")

    # Example C: Rational function with pole f(x) = (2x - 1)/(x + 1)
    tbl_c = compute_variation_table("(2*x - 1)/(x + 1)", "x")
    assert tbl_c is not None
    assert len(tbl_c["transition_points"]) == 1
    pole = tbl_c["transition_points"][0]
    assert pole["type"] == "pole"
    assert pole["val_float"] == -1.0
    # Must have 2 separate intervals around the pole
    assert len(tbl_c["intervals"]) == 2
    # Both intervals are increasing (f'(x) = 3/(x+1)^2 > 0)
    assert tbl_c["intervals"][0]["sign"] == "+"
    assert tbl_c["intervals"][1]["sign"] == "+"
    # Check limit values: as x -> -oo: 2; as x -> -1^-: +oo
    assert tbl_c["intervals"][0]["start_val"] == "2"
    assert tbl_c["intervals"][0]["end_val"] in (r"\infty", r"+\infty")
    # as x -> -1^+: -oo; as x -> +oo: 2
    assert tbl_c["intervals"][1]["start_val"] == r"-\infty"
    assert tbl_c["intervals"][1]["end_val"] == "2"


def test_can_plot_3d_eligibility():
    assert can_plot_3d("x^2 + y^2") is True
    assert can_plot_3d("x*sin(y)") is True
    # Single variable is not eligible for 3D surface
    assert can_plot_3d("x^2") is False
    # Matrix is not eligible
    assert can_plot_3d("[[1, 2], [3, 4]]") is False


def test_create_3d_plot():
    fig = create_3d_plot("x^2 + y^2")
    assert fig is not None
    # Main surface trace
    assert fig.data[0].type == "surface"
    # Includes RGB axes traces and isometric cube layout
    assert len(fig.data) == 4
    assert fig.layout.scene.aspectmode == "cube"
    assert fig.layout.scene.xaxis.linecolor == "#dc2626"
    assert fig.layout.scene.yaxis.linecolor == "#16a34a"
    assert fig.layout.scene.zaxis.linecolor == "#2563eb"


def test_variation_table_computation():
    # f(x) = x^3 - 3*x has critical points at x = -1, 1
    table = compute_variation_table("x**3 - 3*x", "x")
    assert table is not None
    assert len(table["critical_points"]) == 2
    pts_x = [p["x"] for p in table["critical_points"]]
    assert -1.0 in pts_x and 1.0 in pts_x
    # 3 intervals: (-inf, -1): +, (-1, 1): -, (1, +inf): +
    assert len(table["intervals"]) == 3
    signs = [i["sign"] for i in table["intervals"]]
    assert signs == ["+", "-", "+"]


def test_matrix_not_eligible_for_variation_table():
    assert can_compute_variation_table("[[1, 2], [3, 4]]", "x") is False

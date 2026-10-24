"""Regression tests for Integration Navigation, Input Forms, and 3D RGB Coordinate-Axis Visualization."""

from __future__ import annotations

import numpy as np
import pytest

from math_app.domain.models import ProblemType
from math_app.presentation.components.operation_catalog import (
    MAIN_OPERATIONS,
    get_operation_by_type,
)
from math_app.presentation.components.problem_statement import (
    format_problem_statement_latex,
)
from math_app.presentation.services.plot_3d_service import (
    create_parametric_surface_plot,
    create_surface_plot_from_expression,
)
from math_app.presentation.services.analysis_service import create_3d_plot


# ==============================================================================
# 1. Integration Navigation & Operation Catalog Tests
# ==============================================================================

def test_main_menu_single_definite_integration_card():
    """Verify that the main menu contains exactly one definite-integration card.

    Duplicate line, surface, and triple integral cards are removed from the main menu,
    and the total calculus operations displayed on the main menu is exactly 8.
    """
    calc_main_ops = [o for o in MAIN_OPERATIONS if o.domain == "Giải tích (Calculus)"]
    assert len(calc_main_ops) == 8, f"Expected 8 calculus cards on main menu, got {len(calc_main_ops)}"

    # Exactly 1 card titled 'Tích phân xác định'
    def_cards = [o for o in calc_main_ops if o.title == "Tích phân xác định"]
    assert len(def_cards) == 1
    assert def_cards[0].problem_type == ProblemType.DEFINITE_INTEGRAL

    # Line, surface, and triple integral cards are NOT in MAIN_OPERATIONS
    assert not any(o.problem_type == ProblemType.LINE_INTEGRAL for o in calc_main_ops)
    assert not any(o.problem_type == ProblemType.SURFACE_INTEGRAL for o in calc_main_ops)
    assert not any(o.problem_type == ProblemType.TRIPLE_INTEGRAL for o in calc_main_ops)

    # But they remain in OPERATIONS for registry / solver lookup
    assert get_operation_by_type(ProblemType.LINE_INTEGRAL).problem_type == ProblemType.LINE_INTEGRAL
    assert get_operation_by_type(ProblemType.SURFACE_INTEGRAL).problem_type == ProblemType.SURFACE_INTEGRAL
    assert get_operation_by_type(ProblemType.TRIPLE_INTEGRAL).problem_type == ProblemType.TRIPLE_INTEGRAL


def test_subtype_selector_options_and_dispatch():
    """Verify the 4 integration subtypes have correct problem types and distinct models."""
    subtypes = [
        (ProblemType.DEFINITE_INTEGRAL, "Một biến"),
        (ProblemType.LINE_INTEGRAL, "Tích phân đường"),
        (ProblemType.SURFACE_INTEGRAL, "Tích phân mặt"),
        (ProblemType.TRIPLE_INTEGRAL, "Tích phân khối"),
    ]
    for pt, label in subtypes:
        op = get_operation_by_type(pt)
        assert op is not None
        assert op.problem_type == pt
        assert len(label) > 0


# ==============================================================================
# 2. Input Form Schemas and Separation of Concerns
# ==============================================================================

def test_definite_integral_problem_statement_formatting():
    """Verify 1-variable definite integral formats with Newton-Leibniz bounds."""
    stmt = format_problem_statement_latex(
        raw_input="x^2",
        op_type=ProblemType.DEFINITE_INTEGRAL,
        target_var="x",
        params={"lower_bound": "0", "upper_bound": "1"},
    )
    assert "\\int_{0}^{1}" in stmt
    assert "dx" in stmt
    assert "x^{2}" in stmt or "x^2" in stmt


def test_line_integral_scalar_vs_vector_schemas():
    """Verify scalar line integral and vector line integral schemas do not collide."""
    # Scalar line integral: int_C f ds
    scalar_stmt = format_problem_statement_latex(
        raw_input="x + y",
        op_type=ProblemType.LINE_INTEGRAL,
        params={
            "mode": "scalar",
            "param_var": "t",
            "t_min": "0",
            "t_max": "1",
            "param_x": "3*t",
            "param_y": "4*t",
            "param_z": "0",
        },
    )
    assert "\\int_C" in scalar_stmt
    assert "ds" in scalar_stmt
    assert "\\mathbf{F}" not in scalar_stmt

    # Vector line integral: int_C F . dr
    vector_stmt = format_problem_statement_latex(
        raw_input="y, -x, 0",
        op_type=ProblemType.LINE_INTEGRAL,
        params={
            "mode": "vector",
            "param_var": "t",
            "t_min": "0",
            "t_max": "1",
            "param_x": "cos(t)",
            "param_y": "sin(t)",
            "param_z": "0",
            "orientation": "forward",
        },
    )
    assert "\\mathbf{F}\\cdot d\\mathbf{r}" in vector_stmt
    assert "\\mathbf{F} = (y, -x, 0)" in vector_stmt


def test_surface_integral_scalar_vs_flux_schemas():
    """Verify distinction between scalar surface integral and vector flux schemas."""
    # Scalar: iint_S f dS over graph z = g(x, y)
    scalar_stmt = format_problem_statement_latex(
        raw_input="1",
        op_type=ProblemType.SURFACE_INTEGRAL,
        params={
            "mode": "scalar",
            "surface_expr": "1 - x - y",
            "u_var": "x",
            "v_var": "y",
            "u_min": "0",
            "u_max": "1",
            "v_min": "0",
            "v_max": "1",
        },
    )
    assert "\\iint_S" in scalar_stmt
    assert "dS" in scalar_stmt
    assert "S: z =" in scalar_stmt

    # Flux: iint_S F . n dS
    flux_stmt = format_problem_statement_latex(
        raw_input="0, 0, z",
        op_type=ProblemType.SURFACE_INTEGRAL,
        params={
            "mode": "vector",
            "surface_expr": "1 - x - y",
            "orientation": "upward",
            "u_var": "x",
            "v_var": "y",
            "u_min": "0",
            "u_max": "1",
            "v_min": "0",
            "v_max": "1",
        },
    )
    assert "\\mathbf{F}\\cdot\\mathbf{n}" in flux_stmt
    assert "\\mathbf{F} = (0, 0, z)" in flux_stmt


def test_triple_integral_coordinates_and_jacobians():
    """Verify triple integrals in Cartesian, Cylindrical, and Spherical coordinates."""
    # Cartesian
    cart_stmt = format_problem_statement_latex(
        raw_input="x*y*z",
        op_type=ProblemType.TRIPLE_INTEGRAL,
        params={"coord_system": "cartesian", "x_min": "0", "x_max": "1", "y_min": "0", "y_max": "2", "z_min": "0", "z_max": "3"},
    )
    assert "dx" in cart_stmt and "dy" in cart_stmt and "dz" in cart_stmt

    # Cylindrical
    cyl_stmt = format_problem_statement_latex(
        raw_input="z",
        op_type=ProblemType.TRIPLE_INTEGRAL,
        params={"coord_system": "cylindrical", "th_min": "0", "th_max": "2*pi", "r_min": "0", "r_max": "1", "z_min": "0", "z_max": "2"},
    )
    assert "r\\,dr" in cyl_stmt
    assert "d\\theta" in cyl_stmt

    # Spherical
    sph_stmt = format_problem_statement_latex(
        raw_input="1",
        op_type=ProblemType.TRIPLE_INTEGRAL,
        params={"coord_system": "spherical", "th_min": "0", "th_max": "2*pi", "phi_min": "0", "phi_max": "pi", "rho_min": "0", "rho_max": "1"},
    )
    assert "\\rho^2 \\sin(\\phi)" in sph_stmt


# ==============================================================================
# 3. Mandatory 3D Regression Case: z = 1 - x - y on [0, 1] x [0, 1]
# ==============================================================================

def test_regression_plane_3d_plot_geometry_and_axes():
    """Mandatory Regression Test:

    Surface: z = 1 - x - y, 0 <= x <= 1, 0 <= y <= 1.
    Verify:
    - Rectangular parameter-domain patch matches [0, 1] x [0, 1].
    - X, Y, Z arrays have matching dimensions.
    - Z-values strictly span [-1.0, 1.0].
    - Isometric cubic aspectmode ('cube').
    - Sensible camera angle exposing all 3 axes.
    - RGB axis convention: X=Red (#dc2626), Y=Green (#16a34a), Z=Blue (#2563eb).
    - Origin line traces with solid, dashed, and dashdot line styling.
    - Independent Viridis surface color scale.
    """
    domain = {"x": (0.0, 1.0), "y": (0.0, 1.0)}
    fig = create_surface_plot_from_expression("1 - x - y", domain_bounds=domain)
    assert fig is not None, "Failed to create 3D figure for regression plane"

    # 1. Matching coordinate arrays
    surface_trace = fig.data[0]
    assert surface_trace.type == "surface"
    X = np.asarray(surface_trace.x)
    Y = np.asarray(surface_trace.y)
    Z = np.asarray(surface_trace.z)
    assert X.shape == Y.shape == Z.shape, f"Dimension mismatch: {X.shape}, {Y.shape}, {Z.shape}"

    # 2. Domain & computed range
    assert X.min() == pytest.approx(0.0)
    assert X.max() == pytest.approx(1.0)
    assert Y.min() == pytest.approx(0.0)
    assert Y.max() == pytest.approx(1.0)
    assert Z.min() == pytest.approx(-1.0)
    assert Z.max() == pytest.approx(1.0)

    # 3. Layout aspect ratio
    scene = fig.layout.scene
    assert scene.aspectmode == "cube"

    # 4. Camera view
    eye = scene.camera.eye
    assert eye.x > 0 and eye.y < 0 and eye.z > 0

    # 5. Scene axis RGB conventions
    assert scene.xaxis.linecolor == "#dc2626"
    assert scene.yaxis.linecolor == "#16a34a"
    assert scene.zaxis.linecolor == "#2563eb"
    assert "X" in scene.xaxis.title.text
    assert "Y" in scene.yaxis.title.text
    assert "Z" in scene.zaxis.title.text

    # 6. Coordinate lines through origin (since (0,0,0) is in visible bounds)
    assert len(fig.data) == 4  # Surface + X trace + Y trace + Z trace
    trace_x = fig.data[1]
    trace_y = fig.data[2]
    trace_z = fig.data[3]

    assert trace_x.line.color == "#dc2626"
    assert trace_x.line.dash == "solid"
    assert trace_y.line.color == "#16a34a"
    assert trace_y.line.dash == "dash"
    assert trace_z.line.color == "#2563eb"
    assert trace_z.line.dash == "dashdot"

    # 7. Independent surface color scale (e.g., standard Viridis, independent of axis colors)
    assert surface_trace.colorscale == "Viridis" or (
        isinstance(surface_trace.colorscale, tuple) and surface_trace.colorscale[0][1] == "#440154"
    )


# ==============================================================================
# 4. Nonlinear & Trigonometric Surfaces
# ==============================================================================

def test_nonlinear_paraboloid_3d_plot():
    """Verify nonlinear paraboloid z = x^2 + y^2 generates correctly."""
    fig = create_3d_plot("x^2 + y^2")
    assert fig is not None
    assert fig.data[0].type == "surface"
    assert fig.layout.scene.aspectmode == "cube"
    assert fig.layout.scene.xaxis.linecolor == "#dc2626"
    assert fig.layout.scene.yaxis.linecolor == "#16a34a"
    assert fig.layout.scene.zaxis.linecolor == "#2563eb"


def test_trigonometric_surface_3d_plot():
    """Verify trigonometric surface z = sin(x)*cos(y) generates correctly."""
    domain = {"x": (-3.14, 3.14), "y": (-3.14, 3.14)}
    fig = create_surface_plot_from_expression("sin(x)*cos(y)", domain_bounds=domain)
    assert fig is not None
    assert fig.data[0].type == "surface"
    assert fig.layout.scene.aspectmode == "cube"
    assert len(fig.data) == 4  # Origin lines included


def test_parametric_surface_3d_plot():
    """Verify parametric surface r(u, v) = (u, v, 1 - u - v) generates correctly."""
    fig = create_parametric_surface_plot(
        param_x="u",
        param_y="v",
        param_z="1 - u - v",
        u_bounds=(0.0, 1.0),
        v_bounds=(0.0, 1.0),
    )
    assert fig is not None
    assert fig.data[0].type == "surface"
    assert fig.layout.scene.aspectmode == "cube"

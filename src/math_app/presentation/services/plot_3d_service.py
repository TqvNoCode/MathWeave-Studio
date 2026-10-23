"""Reusable 3D plotting service using Plotly for MathWeave Studio.

Provides standardized RGB coordinate axes (X=Red, Y=Green, Z=Blue),
isometric cubic aspect ratio, robust sampling, and structured configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import numpy as np
import plotly.graph_objects as go
import sympy as sp

from math_app.input.parser import parse_mathematical_input


@dataclass(frozen=True)
class AxisDisplayPolicy:
    """Styling policy for 3D coordinate axes."""

    show_origin_axes: bool = True
    x_color: str = "#dc2626"  # Red
    y_color: str = "#16a34a"  # Green
    z_color: str = "#2563eb"  # Blue
    x_tick_color: str = "#991b1b"
    y_tick_color: str = "#166534"
    z_tick_color: str = "#1e40af"
    axis_line_width: int = 4
    origin_line_width: int = 5
    grid_color: str = "#e2e8f0"
    background_color: str = "#f8fafc"


@dataclass
class Plot3DConfig:
    """Structured configuration for 3D surface or curve visualization."""

    x_coords: np.ndarray
    y_coords: np.ndarray
    z_coords: np.ndarray
    x_bounds: tuple[float, float]
    y_bounds: tuple[float, float]
    z_bounds: tuple[float, float]
    title: str | None = None
    x_label: str = "X"
    y_label: str = "Y"
    z_label: str = "Z"
    color_scale: str = "Viridis"
    camera_eye: dict[str, float] = field(default_factory=lambda: {"x": 1.6, "y": -1.6, "z": 1.3})
    aspect_mode: str = "cube"
    axis_policy: AxisDisplayPolicy = field(default_factory=AxisDisplayPolicy)
    is_curve: bool = False


def build_3d_figure(config: Plot3DConfig) -> go.Figure:
    """Assemble a standardized, accessible Plotly 3D Figure from Plot3DConfig."""
    fig = go.Figure()
    pol = config.axis_policy

    # 1. Main Geometry Trace (Surface or 3D Curve)
    if config.is_curve:
        fig.add_trace(
            go.Scatter3d(
                x=config.x_coords,
                y=config.y_coords,
                z=config.z_coords,
                mode="lines",
                line=dict(color="#4f46e5", width=6),
                name="Đường cong C",
                hoverinfo="x+y+z",
            )
        )
    else:
        fig.add_trace(
            go.Surface(
                x=config.x_coords,
                y=config.y_coords,
                z=config.z_coords,
                colorscale=config.color_scale,
                showscale=True,
                colorbar=dict(
                    title=dict(text=config.z_label, side="top", font=dict(size=12, color="#334155")),
                    len=0.65,
                    thickness=14,
                    x=1.02,
                    tickfont=dict(size=10, color="#475569"),
                ),
                name="Mặt cong S",
                hoverinfo="x+y+z",
            )
        )

    # 2. Origin-crossing coordinate axes (when origin is inside visible bounds)
    x_min, x_max = config.x_bounds
    y_min, y_max = config.y_bounds
    z_min, z_max = config.z_bounds

    tol = 0.05
    origin_in_view = (
        (x_min - tol <= 0.0 <= x_max + tol)
        and (y_min - tol <= 0.0 <= y_max + tol)
        and (z_min - tol <= 0.0 <= z_max + tol)
    )

    if pol.show_origin_axes and origin_in_view:
        # Effective origin lines clipped to bounds
        ox_start, ox_end = min(x_min, 0.0), max(x_max, 0.0)
        oy_start, oy_end = min(y_min, 0.0), max(y_max, 0.0)
        oz_start, oz_end = min(z_min, 0.0), max(z_max, 0.0)

        # X-Axis through origin: Solid line, Red, labeled "X"
        fig.add_trace(
            go.Scatter3d(
                x=[ox_start, ox_end],
                y=[0.0, 0.0],
                z=[0.0, 0.0],
                mode="lines+text",
                line=dict(color=pol.x_color, width=pol.origin_line_width, dash="solid"),
                text=["", "  X"],
                textposition="top right",
                textfont=dict(color=pol.x_color, size=13),
                name="Trục X (Đỏ - Nét liền)",
                hoverinfo="name+x",
                showlegend=False,
            )
        )
        # Y-Axis through origin: Dashed line, Green, labeled "Y"
        fig.add_trace(
            go.Scatter3d(
                x=[0.0, 0.0],
                y=[oy_start, oy_end],
                z=[0.0, 0.0],
                mode="lines+text",
                line=dict(color=pol.y_color, width=pol.origin_line_width, dash="dash"),
                text=["", "  Y"],
                textposition="top right",
                textfont=dict(color=pol.y_color, size=13),
                name="Trục Y (Xanh lá - Nét đứt)",
                hoverinfo="name+y",
                showlegend=False,
            )
        )
        # Z-Axis through origin: Dashdot line, Blue, labeled "Z"
        fig.add_trace(
            go.Scatter3d(
                x=[0.0, 0.0],
                y=[0.0, 0.0],
                z=[oz_start, oz_end],
                mode="lines+text",
                line=dict(color=pol.z_color, width=pol.origin_line_width, dash="dashdot"),
                text=["", "  Z"],
                textposition="top right",
                textfont=dict(color=pol.z_color, size=13),
                name="Trục Z (Xanh dương - Nét chấm gạch)",
                hoverinfo="name+z",
                showlegend=False,
            )
        )

    # 3. Scene layout and RGB Scene Axes
    fig.update_layout(
        title=dict(text=config.title) if config.title else None,
        scene=dict(
            xaxis=dict(
                title=dict(text=f"<b>{config.x_label}</b>", font=dict(color=pol.x_color, size=13)),
                tickfont=dict(color=pol.x_tick_color, size=10),
                linecolor=pol.x_color,
                linewidth=pol.axis_line_width,
                showline=True,
                mirror=False,
                gridcolor=pol.grid_color,
                zerolinecolor=pol.x_color,
                zerolinewidth=2,
                backgroundcolor=pol.background_color,
                showbackground=True,
                range=[x_min, x_max],
            ),
            yaxis=dict(
                title=dict(text=f"<b>{config.y_label}</b>", font=dict(color=pol.y_color, size=13)),
                tickfont=dict(color=pol.y_tick_color, size=10),
                linecolor=pol.y_color,
                linewidth=pol.axis_line_width,
                showline=True,
                mirror=False,
                gridcolor=pol.grid_color,
                zerolinecolor=pol.y_color,
                zerolinewidth=2,
                backgroundcolor=pol.background_color,
                showbackground=True,
                range=[y_min, y_max],
            ),
            zaxis=dict(
                title=dict(text=f"<b>{config.z_label}</b>", font=dict(color=pol.z_color, size=13)),
                tickfont=dict(color=pol.z_tick_color, size=10),
                linecolor=pol.z_color,
                linewidth=pol.axis_line_width,
                showline=True,
                mirror=False,
                gridcolor=pol.grid_color,
                zerolinecolor=pol.z_color,
                zerolinewidth=2,
                backgroundcolor=pol.background_color,
                showbackground=True,
                range=[z_min, z_max],
            ),
            aspectmode=config.aspect_mode,
            camera=dict(
                eye=config.camera_eye,
            ),
        ),
        template="plotly_white",
        margin=dict(l=15, r=15, t=15, b=15),
        height=480,
    )
    return fig


def create_surface_plot_from_expression(
    raw_expr: str,
    domain_bounds: dict[str, tuple[float, float]] | None = None,
    var_override: tuple[str, str] | None = None,
) -> go.Figure | None:
    """Generate interactive 3D surface plot for z = f(x, y) with designated domain bounds."""
    try:
        expr, _ = parse_mathematical_input(raw_expr, "x")
        symbols = sorted(list(expr.free_symbols), key=lambda s: s.name)
        if len(symbols) != 2:
            return None

        var_x, var_y = symbols[0], symbols[1]
        if var_override:
            var_x_name, var_y_name = var_override
        else:
            var_x_name, var_y_name = var_x.name, var_y.name

        f = sp.lambdify((var_x, var_y), expr, modules=["numpy"])

        # Determine domain bounds
        bounds_map = domain_bounds or {}
        x_min, x_max = bounds_map.get(var_x_name, (-4.0, 4.0))
        y_min, y_max = bounds_map.get(var_y_name, (-4.0, 4.0))

        if x_min >= x_max:
            x_min, x_max = x_max - 1.0, x_max
        if y_min >= y_max:
            y_min, y_max = y_max - 1.0, y_max

        # Sampling bounded grid
        grid_density = 40
        xs = np.linspace(float(x_min), float(x_max), grid_density)
        ys = np.linspace(float(y_min), float(y_max), grid_density)
        X, Y = np.meshgrid(xs, ys)

        try:
            raw_z = f(X, Y)
            if np.iscomplexobj(raw_z):
                Z = np.where(np.abs(np.imag(raw_z)) < 1e-12, np.real(raw_z), np.nan)
            elif np.isscalar(raw_z):
                Z = np.full_like(X, float(raw_z))
            else:
                Z = np.asarray(raw_z, dtype=float)
        except Exception:
            z_list = []
            for xi, yi in zip(X.ravel(), Y.ravel()):
                try:
                    val = complex(f(xi, yi))
                    z_list.append(val.real if abs(val.imag) < 1e-12 else np.nan)
                except Exception:
                    z_list.append(np.nan)
            Z = np.array(z_list, dtype=float).reshape(X.shape)

        # Eliminate infinities
        Z = np.where(np.isfinite(Z), Z, np.nan)
        valid_z = Z[np.isfinite(Z)]

        if len(valid_z) == 0:
            return None

        z_min = float(np.nanmin(valid_z))
        z_max = float(np.nanmax(valid_z))

        # Handle flat surface (constant z)
        if abs(z_max - z_min) < 1e-6:
            z_min -= 1.0
            z_max += 1.0
        else:
            # Check percentile clipping only if extreme outliers exist
            p_low, p_high = np.percentile(valid_z, [0.5, 99.5])
            if (p_high - p_low) > 0 and (z_max - z_min) > 4.0 * (p_high - p_low):
                z_span = float(p_high - p_low)
                z_min = max(z_min, float(p_low - 0.2 * z_span))
                z_max = min(z_max, float(p_high + 0.2 * z_span))
                Z = np.clip(Z, z_min, z_max)

        config = Plot3DConfig(
            x_coords=X,
            y_coords=Y,
            z_coords=Z,
            x_bounds=(float(x_min), float(x_max)),
            y_bounds=(float(y_min), float(y_max)),
            z_bounds=(float(z_min), float(z_max)),
            x_label=f"X ({var_x_name})",
            y_label=f"Y ({var_y_name})",
            z_label=f"Z (f({var_x_name}, {var_y_name}))",
            title=None,
            aspect_mode="cube",
        )
        return build_3d_figure(config)
    except Exception:
        return None


def create_parametric_surface_plot(
    param_x: str,
    param_y: str,
    param_z: str,
    u_bounds: tuple[float, float],
    v_bounds: tuple[float, float],
    u_var: str = "u",
    v_var: str = "v",
) -> go.Figure | None:
    """Generate 3D plot for parametric surface r(u, v) = (x(u,v), y(u,v), z(u,v))."""
    try:
        u_sym = sp.Symbol(u_var)
        v_sym = sp.Symbol(v_var)
        x_expr = sp.sympify(param_x)
        y_expr = sp.sympify(param_y)
        z_expr = sp.sympify(param_z)

        fx = sp.lambdify((u_sym, v_sym), x_expr, modules=["numpy"])
        fy = sp.lambdify((u_sym, v_sym), y_expr, modules=["numpy"])
        fz = sp.lambdify((u_sym, v_sym), z_expr, modules=["numpy"])

        u_vals = np.linspace(u_bounds[0], u_bounds[1], 35)
        v_vals = np.linspace(v_bounds[0], v_bounds[1], 35)
        U, V = np.meshgrid(u_vals, v_vals)

        X = np.asarray(fx(U, V), dtype=float)
        Y = np.asarray(fy(U, V), dtype=float)
        Z = np.asarray(fz(U, V), dtype=float)

        x_min, x_max = float(np.nanmin(X)), float(np.nanmax(X))
        y_min, y_max = float(np.nanmin(Y)), float(np.nanmax(Y))
        z_min, z_max = float(np.nanmin(Z)), float(np.nanmax(Z))

        if abs(x_max - x_min) < 1e-6:
            x_min, x_max = x_min - 1.0, x_max + 1.0
        if abs(y_max - y_min) < 1e-6:
            y_min, y_max = y_min - 1.0, y_max + 1.0
        if abs(z_max - z_min) < 1e-6:
            z_min, z_max = z_min - 1.0, z_max + 1.0

        config = Plot3DConfig(
            x_coords=X,
            y_coords=Y,
            z_coords=Z,
            x_bounds=(x_min, x_max),
            y_bounds=(y_min, y_max),
            z_bounds=(z_min, z_max),
            x_label="X",
            y_label="Y",
            z_label="Z",
            title=None,
            aspect_mode="cube",
        )
        return build_3d_figure(config)
    except Exception:
        return None

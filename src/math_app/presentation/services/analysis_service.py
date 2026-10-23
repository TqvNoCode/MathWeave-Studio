"""Contextual mathematical analysis and visualization service for UI."""

from __future__ import annotations

from typing import Any
import numpy as np
import plotly.graph_objects as go
import sympy as sp

from math_app.input.parser import normalize_variable_name, parse_mathematical_input
from math_app.rendering.latex.formatter import expr_to_latex


def can_plot_2d(raw_expr: str, target_var: str = "x") -> bool:
    """Check if expression represents a single-variable real function suitable for 2D plotting."""
    cleaned = raw_expr.strip()
    if not cleaned or cleaned.startswith("[") or "=" in cleaned:
        return False
    try:
        clean_var = normalize_variable_name(target_var)
        expr, var = parse_mathematical_input(cleaned, clean_var)
        symbols = expr.free_symbols
        # Must have at most one free symbol, which is the variable
        return len(symbols) <= 1 and (not symbols or var in symbols)
    except Exception:
        return False


def sample_function_2d(
    raw_expr: str,
    target_var: str = "x",
    x_min: float = -10.0,
    x_max: float = 10.0,
    num_points: int = 800,
) -> tuple[np.ndarray, np.ndarray, float, float] | None:
    """Sample single-variable function over arbitrary finite viewport with discontinuity detection."""
    try:
        clean_var = normalize_variable_name(target_var)
        expr, var = parse_mathematical_input(raw_expr, clean_var)

        # Lambdify for fast numpy evaluation
        f = sp.lambdify(var, expr, modules=["numpy", {"nan": np.nan}])

        # Bounded point sampling adapted to viewport
        num_points = max(200, min(2000, num_points))
        xs = np.linspace(x_min, x_max, num_points)

        try:
            raw_ys = f(xs)
            if np.iscomplexobj(raw_ys):
                ys = np.where(np.abs(np.imag(raw_ys)) < 1e-12, np.real(raw_ys), np.nan)
            elif np.isscalar(raw_ys):
                ys = np.full_like(xs, float(raw_ys))
            else:
                ys = np.asarray(raw_ys, dtype=float)
        except Exception:
            ys_list = []
            for x_val in xs:
                try:
                    v = complex(f(x_val))
                    if abs(v.imag) < 1e-12:
                        ys_list.append(v.real)
                    else:
                        ys_list.append(np.nan)
                except Exception:
                    ys_list.append(np.nan)
            ys = np.array(ys_list, dtype=float)

        # Detect and clean poles / asymptotes
        try:
            _, denom = expr.as_numer_denom()
            if denom != 1 and denom.has(var):
                roots = sp.solve(sp.sqf_part(denom), var)
                dx = (x_max - x_min) / num_points
                for r in roots:
                    if r.is_real is True or (r.is_number and r.as_real_imag()[1] == 0):
                        val = float(r.evalf())
                        if x_min - 2 * dx <= val <= x_max + 2 * dx:
                            ys[np.abs(xs - val) <= max(1.8 * dx, 0.05)] = np.nan
        except Exception:
            pass

        # Detect and clean asymptotic jumps across undefined regions
        diffs = np.abs(np.diff(ys))
        jump_indices = np.where(diffs > 25.0)[0]
        ys_clean = ys.copy()
        ys_clean[jump_indices] = np.nan
        ys_clean[jump_indices + 1] = np.nan
        ys_clean[ys_clean > 1e4] = np.nan
        ys_clean[ys_clean < -1e4] = np.nan

        # Compute reasonable y-range to prevent spikes from compressing the curve
        valid_y = ys_clean[np.isfinite(ys_clean)]
        if len(valid_y) > 0:
            min_v = float(np.min(valid_y))
            max_v = float(np.max(valid_y))
            if -1.05 <= min_v and max_v <= 1.05:
                # Naturally bounded functions (e.g. sin, cos)
                y_min, y_max = -1.5, 1.5
            else:
                p_low, p_high = np.percentile(valid_y, [2, 98])
                y_span = max(1.0, float(p_high - p_low))
                y_min = max(-500.0, float(p_low - 0.25 * y_span))
                y_max = min(500.0, float(p_high + 0.25 * y_span))
        else:
            y_min, y_max = -10.0, 10.0

        return xs, ys_clean, y_min, y_max
    except Exception:
        return None


def create_2d_plot(
    raw_expr: str,
    target_var: str = "x",
    x_range: tuple[float, float] | None = None,
    num_points: int = 800,
) -> go.Figure | None:
    """Generate interactive 2D Plotly curve with dynamic viewing domain and clean formatting."""
    try:
        clean_var = normalize_variable_name(target_var)

        # Default viewport
        if x_range is not None:
            x_min, x_max = x_range
        else:
            x_min, x_max = -10.0, 10.0

        data = sample_function_2d(raw_expr, clean_var, x_min, x_max, num_points)
        if data is None:
            return None

        xs, ys_clean, y_min, y_max = data

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys_clean,
                mode="lines",
                name=f"y = f({clean_var})",
                line=dict(color="#2563eb", width=2.5),
                hovertemplate=f"<b>{clean_var}:</b> %{{x:.3f}}<br><b>y:</b> %{{y:.3f}}<extra></extra>",
            )
        )

        fig.update_layout(
            xaxis_title=clean_var,
            yaxis_title=f"f({clean_var})",
            template="plotly_white",
            margin=dict(l=40, r=40, t=30, b=40),
            height=420,
            hovermode="x",
            dragmode="pan",
            uirevision="mathweave_plot",
            xaxis=dict(
                range=[x_min, x_max],
                showgrid=True,
                zeroline=True,
                gridcolor="#f1f5f9",
                zerolinecolor="#94a3b8",
            ),
            yaxis=dict(
                range=[y_min, y_max],
                showgrid=True,
                zeroline=True,
                gridcolor="#f1f5f9",
                zerolinecolor="#94a3b8",
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return fig
    except Exception:
        return None


from math_app.presentation.services.plot_3d_service import (
    create_surface_plot_from_expression,
    create_parametric_surface_plot,
    build_3d_figure,
    Plot3DConfig,
    AxisDisplayPolicy,
)


def can_plot_3d(raw_expr: str) -> bool:
    """Check if expression represents a two-variable real function suitable for 3D surface plotting."""
    cleaned = raw_expr.strip()
    if not cleaned or cleaned.startswith("["):
        return False
    if "=" in cleaned:
        parts = cleaned.split("=", 1)
        cleaned = parts[1].strip()
    try:
        expr, _ = parse_mathematical_input(cleaned, "x")
        symbols = expr.free_symbols
        return len(symbols) == 2
    except Exception:
        return False


def create_3d_plot(
    raw_expr: str,
    domain_bounds: dict[str, tuple[float, float]] | None = None,
) -> go.Figure | None:
    """Generate interactive 3D surface plot for two-variable functions z = f(x, y).

    Uses standardized RGB axes (X=Red, Y=Green, Z=Blue) and cubic isometric aspect ratio.
    """
    cleaned = raw_expr.strip()
    if "=" in cleaned:
        cleaned = cleaned.split("=", 1)[1].strip()
    return create_surface_plot_from_expression(cleaned, domain_bounds=domain_bounds)


def can_compute_variation_table(raw_expr: str, target_var: str = "x") -> bool:
    """Check if variation table can be computed for this single-variable function."""
    return can_plot_2d(raw_expr, target_var)


def compute_variation_table(raw_expr: str, target_var: str = "x") -> dict[str, Any] | None:
    """Compute mathematically rigorous variation table data: critical points, signs of f'(x), and monotonic behavior."""
    try:
        clean_var = normalize_variable_name(target_var)
        expr, var = parse_mathematical_input(raw_expr, clean_var)

        # Compute first derivative
        d_expr = sp.diff(expr, var)

        # 1. Poles / singularities where denominator of f or f' is 0
        poles = set()
        for e in (expr, d_expr):
            _, denom = e.as_numer_denom()
            if denom != 1 and denom.has(var):
                try:
                    base = sp.sqf_part(denom)
                    for r in sp.solve(base, var):
                        if r.is_real is True or (r.is_number and r.as_real_imag()[1] == 0):
                            poles.add(r)
                except Exception:
                    pass

        # 2. Critical points where f'(x) == 0
        crit_pts = set()
        is_complete = True
        limitations: list[str] = []
        try:
            solutions = sp.solve(sp.Eq(d_expr, 0), var)
            for r in solutions:
                if r.is_real is True or (r.is_number and r.as_real_imag()[1] == 0):
                    if r not in poles:
                        crit_pts.add(r)
        except Exception as exc:
            is_complete = False
            limitations.append(f"Không thể giải chính xác phương trình f'({clean_var}) = 0: {exc}")

        # Combine transition points
        trans_pts = []
        for p in poles:
            try:
                val_flt = round(float(p.evalf()), 4)
            except Exception:
                val_flt = 0.0
            trans_pts.append({"sym": p, "type": "pole", "val_float": val_flt})

        for c in crit_pts:
            try:
                val_flt = round(float(c.evalf()), 4)
            except Exception:
                val_flt = 0.0
            trans_pts.append({"sym": c, "type": "critical", "val_float": val_flt})

        trans_pts.sort(key=lambda item: item["val_float"])

        def format_limit_val(val_expr: Any) -> str:
            if val_expr == -sp.oo:
                return r"-\infty"
            if val_expr == sp.oo:
                return r"+\infty"
            return expr_to_latex(val_expr)

        # Compute point values / one-sided limits
        for pt in trans_pts:
            pt["val_latex"] = expr_to_latex(pt["sym"])
            if pt["type"] == "critical":
                try:
                    val = sp.simplify(expr.subs(var, pt["sym"]))
                    pt["y_disp"] = str(val)
                    pt["y_latex"] = format_limit_val(val)
                except Exception:
                    pt["y_disp"] = "Không xác định"
                    pt["y_latex"] = "?"
            else:
                try:
                    ll = sp.limit(expr, var, pt["sym"], dir="-")
                    pt["lim_left"] = format_limit_val(ll)
                except Exception:
                    pt["lim_left"] = "?"
                try:
                    lr = sp.limit(expr, var, pt["sym"], dir="+")
                    pt["lim_right"] = format_limit_val(lr)
                except Exception:
                    pt["lim_right"] = "?"

        # Infinite limits
        try:
            lim_neg = sp.limit(expr, var, -sp.oo)
            lim_neg_inf = format_limit_val(lim_neg)
        except Exception:
            lim_neg_inf = r"-\infty"
        try:
            lim_pos = sp.limit(expr, var, sp.oo)
            lim_pos_inf = format_limit_val(lim_pos)
        except Exception:
            lim_pos_inf = r"+\infty"

        # Build intervals
        bounds = [-sp.oo] + [pt["sym"] for pt in trans_pts] + [sp.oo]
        intervals: list[dict[str, Any]] = []

        for i in range(len(bounds) - 1):
            left_sym = bounds[i]
            right_sym = bounds[i + 1]

            if left_sym == -sp.oo and right_sym == sp.oo:
                sample_x = 0.0
                left_str = r"-\infty"
                right_str = r"+\infty"
            elif left_sym == -sp.oo:
                left_str = r"-\infty"
                right_str = expr_to_latex(right_sym)
                sample_x = float(right_sym.evalf()) - 1.0
            elif right_sym == sp.oo:
                left_str = expr_to_latex(left_sym)
                right_str = r"+\infty"
                sample_x = float(left_sym.evalf()) + 1.0
            else:
                left_str = expr_to_latex(left_sym)
                right_str = expr_to_latex(right_sym)
                sample_x = (float(left_sym.evalf()) + float(right_sym.evalf())) / 2.0

            try:
                val_sign = float(d_expr.subs(var, sample_x).evalf())
                if val_sign > 1e-6:
                    sign_str = "+"
                    behavior = "Đồng biến ↗"
                    arrow = "↗"
                elif val_sign < -1e-6:
                    sign_str = "-"
                    behavior = "Nghịch biến ↘"
                    arrow = "↘"
                else:
                    sign_str = "0"
                    behavior = "Hằng số"
                    arrow = "→"
            except Exception:
                sign_str = "?"
                behavior = "Không xác định"
                arrow = "→"

            # Start value (at left bound)
            if left_sym == -sp.oo:
                start_val = lim_neg_inf
            else:
                left_pt = trans_pts[i - 1]
                start_val = left_pt["lim_right"] if left_pt["type"] == "pole" else left_pt.get("y_latex", "")

            # End value (at right bound)
            if right_sym == sp.oo:
                end_val = lim_pos_inf
            else:
                right_pt = trans_pts[i]
                end_val = right_pt["lim_left"] if right_pt["type"] == "pole" else right_pt.get("y_latex", "")

            intervals.append({
                "left": left_str,
                "right": right_str,
                "interval_str": f"({left_str}, {right_str})",
                "sign": sign_str,
                "behavior": behavior,
                "arrow": arrow,
                "start_val": start_val,
                "end_val": end_val,
            })

        # Values at critical points (compatible with existing tests)
        crit_points_data = [
            {
                "x": pt["val_float"],
                "y": pt.get("y_disp", ""),
                "latex_x": pt["val_latex"],
                "latex_y": pt.get("y_latex", ""),
            }
            for pt in trans_pts
            if pt["type"] == "critical"
        ]

        # Domain LaTeX
        if not poles:
            domain_str = r"\mathcal{D} = \mathbb{R}"
        else:
            sorted_poles = sorted(list(poles), key=lambda val: float(val.evalf()))
            domain_str = (
                r"\mathcal{D} = \mathbb{R} \setminus \{"
                + ", ".join(expr_to_latex(p) for p in sorted_poles)
                + r"\}"
            )

        return {
            "variable": clean_var,
            "expression": str(expr),
            "expression_latex": expr_to_latex(expr),
            "derivative": str(d_expr),
            "derivative_latex": expr_to_latex(d_expr),
            "domain_latex": domain_str,
            "critical_points": crit_points_data,
            "transition_points": trans_pts,
            "intervals": intervals,
            "is_complete": is_complete,
            "limitations": limitations,
        }
    except Exception:
        return None
    except Exception:
        return None

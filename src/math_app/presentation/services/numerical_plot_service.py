"""Plotly visualization service for numerical ODE approximations."""

from __future__ import annotations

import plotly.graph_objects as go

from math_app.domain.numerical_ode import NumericalODEOrder, NumericalODEResponse


def create_numerical_euler_plot(
    response: NumericalODEResponse,
    *,
    show_exact: bool = True,
) -> go.Figure | None:
    """Create interactive 2D Plotly figure for y(t) from actual Explicit Euler solver rows."""
    if not response.rows:
        return None

    indep = response.independent_var
    dep = response.dependent_var
    xs = [row.t for row in response.rows]
    ys = [row.y for row in response.rows]
    use_markers = len(xs) <= 150

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines+markers" if use_markers else "lines",
            name=f"Euler tiến — xấp xỉ {dep}ₙ",
            line=dict(color="#2563eb", width=2.5),
            marker=dict(size=6, color="#1d4ed8") if use_markers else None,
            hovertemplate=f"<b>{indep}:</b> %{{x:.6g}}<br><b>{dep}ₙ (xấp xỉ):</b> %{{y:.6g}}<extra></extra>",
        )
    )

    if not use_markers:
        fig.add_trace(
            go.Scatter(
                x=[xs[0], xs[-1]],
                y=[ys[0], ys[-1]],
                mode="markers",
                name="Điểm đầu & điểm cuối",
                marker=dict(size=8, color="#1d4ed8"),
                hovertemplate=f"<b>{indep}:</b> %{{x:.6g}}<br><b>{dep}ₙ:</b> %{{y:.6g}}<extra></extra>",
            )
        )

    ana = response.analytical_comparison
    if show_exact and ana is not None and ana.available and ana.points:
        ex_xs = [pt.t for pt in ana.points]
        ex_ys = [pt.y_exact for pt in ana.points]
        fig.add_trace(
            go.Scatter(
                x=ex_xs,
                y=ex_ys,
                mode="lines",
                name=f"Nghiệm giải tích chính xác {dep}({indep})",
                line=dict(color="#059669", width=2.2, dash="dash"),
                hovertemplate=f"<b>{indep}:</b> %{{x:.6g}}<br><b>{dep} chính xác:</b> %{{y:.6g}}<extra></extra>",
            )
        )

    fig.update_layout(
        xaxis_title=indep,
        yaxis_title=f"{dep}({indep})",
        template="plotly_white",
        margin=dict(l=48, r=20, t=40, b=76),
        height=390,
        hovermode="x unified",
        dragmode="pan",
        uirevision="numerical_euler_y",
        xaxis=dict(
            showgrid=True,
            zeroline=True,
            gridcolor="#f1f5f9",
            zerolinecolor="#94a3b8",
        ),
        yaxis=dict(
            showgrid=True,
            zeroline=True,
            gridcolor="#f1f5f9",
            zerolinecolor="#94a3b8",
        ),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
    )
    return fig


def create_numerical_derivative_plot(
    response: NumericalODEResponse,
    *,
    show_exact: bool = True,
) -> go.Figure | None:
    """Create optional v(t) = y'(t) plot for second-order Explicit Euler with optional exact overlay."""
    if response.order != NumericalODEOrder.SECOND_ORDER or not response.rows:
        return None
    if any(row.v is None for row in response.rows):
        return None

    indep = response.independent_var
    dep = response.dependent_var
    xs = [row.t for row in response.rows]
    vs = [float(row.v) for row in response.rows if row.v is not None]
    use_markers = len(xs) <= 150

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=vs,
            mode="lines+markers" if use_markers else "lines",
            name=f"Euler tiến — đạo hàm vₙ ≈ {dep}'({indep})",
            line=dict(color="#4f46e5", width=2.2),
            marker=dict(size=5, color="#4338ca") if use_markers else None,
            hovertemplate=f"<b>{indep}:</b> %{{x:.6g}}<br><b>vₙ (xấp xỉ):</b> %{{y:.6g}}<extra></extra>",
        )
    )

    ana = response.analytical_comparison
    if (
        show_exact
        and ana is not None
        and ana.available
        and ana.points
        and all(pt.v_exact is not None for pt in ana.points)
    ):
        ex_xs = [pt.t for pt in ana.points]
        ex_vs = [float(pt.v_exact) for pt in ana.points if pt.v_exact is not None]
        fig.add_trace(
            go.Scatter(
                x=ex_xs,
                y=ex_vs,
                mode="lines",
                name=f"Đạo hàm giải tích chính xác {dep}'({indep})",
                line=dict(color="#059669", width=2.2, dash="dash"),
                hovertemplate=f"<b>{indep}:</b> %{{x:.6g}}<br><b>{dep}' chính xác:</b> %{{y:.6g}}<extra></extra>",
            )
        )

    fig.update_layout(
        xaxis_title=indep,
        yaxis_title=f"v({indep}) = {dep}'({indep})",
        template="plotly_white",
        margin=dict(l=48, r=20, t=40, b=72),
        height=340,
        hovermode="x unified",
        dragmode="pan",
        uirevision="numerical_euler_v",
        xaxis=dict(showgrid=True, zeroline=True, gridcolor="#f1f5f9", zerolinecolor="#94a3b8"),
        yaxis=dict(showgrid=True, zeroline=True, gridcolor="#f1f5f9", zerolinecolor="#94a3b8"),
        legend=dict(orientation="h", yanchor="top", y=-0.24, xanchor="center", x=0.5),
    )
    return fig

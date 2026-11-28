"""Dedicated First-Order Explicit Euler ODE input panel."""

from __future__ import annotations

from typing import Any, Callable

from nicegui import ui

from math_app.domain.numerical_ode import NumericalODEOrder
from math_app.presentation.components.workspace.ode.numerical_euler_shared import (
    EulerPanelConfig,
    render_order_specific_euler_form,
)
from math_app.presentation.components.workspace.ode.ode_state import ODEOrder

FIRST_ORDER_EULER_CONFIG = EulerPanelConfig(
    order=NumericalODEOrder.FIRST_ORDER,
    banner_text=(
        "PTVP cấp 1 — Euler tiến (IVP): Nhập phương trình y' = f(t, y) cùng điều kiện ban đầu y(t₀) = y₀ "
        "và bước nhảy h > 0 để tính giá trị xấp xỉ rời rạc trên [t₀, T]."
    ),
    equation_label="Phương trình vi phân cấp 1: y' = f(t, y)",
    equation_placeholder="y' = y",
    default_equation="y' = y",
    default_indep_var="t",
    default_t0="0",
    default_y0="1",
    default_v0="",
    default_t_end="1",
    default_step_size="0.1",
    ivp_section_heading="ĐIỀU KIỆN BAN ĐẦU y(t₀) = y₀ & THAM SỐ LƯỚI",
    y0_label="Giá trị ban đầu y₀ = y(t₀)",
    examples_label="Ví dụ Euler tiến (Cấp 1):",
    examples=(
        ("Tăng trưởng mũ: y' = y, y(0)=1, T=1, h=0.1", ("y' = y", "t", "0", "1", "", "1", "0.1")),
        ("Suy giảm mũ: y' = -2y, y(0)=1, T=1, h=0.2", ("y' = -2*y", "t", "0", "1", "", "1", "0.2")),
        ("Không thuần nhất: y' = t + y, y(0)=1, T=0.5, h=0.1", ("y' = t + y", "t", "0", "1", "", "0.5", "0.1")),
        ("Phi tuyến: y' = sin(t*y), y(0)=1, T=0.6, h=0.15", ("y' = sin(t*y)", "t", "0", "1", "", "0.6", "0.15")),
        ("Tích phân lùi: y' = -y, y(1)=1, T=0, h=0.2", ("y' = -y", "t", "1", "1", "", "0", "0.2")),
    ),
    cta_text="TÍNH XẤP XỈ EULER CẤP 1",
    cta_aria_label="Tính nghiệm xấp xỉ Explicit Euler cho phương trình vi phân cấp 1",
    reset_aria_label="Khôi phục tham số Euler tiến cấp 1 mặc định",
)


def render_first_order_euler_panel(
    numerical_use_case: Any,
    results_container: ui.column,
    on_switch_order: Callable[[ODEOrder], None] | None = None,
) -> None:
    """Render the dedicated First-Order Explicit Euler IVP workspace panel."""
    render_order_specific_euler_form(
        FIRST_ORDER_EULER_CONFIG,
        numerical_use_case=numerical_use_case,
        results_container=results_container,
        on_switch_order=on_switch_order,
    )

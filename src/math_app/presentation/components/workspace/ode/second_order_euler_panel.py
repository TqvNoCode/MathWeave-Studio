"""Dedicated Second-Order Explicit Euler ODE input panel."""

from __future__ import annotations

from typing import Any, Callable

from nicegui import ui

from math_app.domain.numerical_ode import NumericalODEOrder
from math_app.presentation.components.workspace.ode.numerical_euler_shared import (
    EulerPanelConfig,
    render_order_specific_euler_form,
)
from math_app.presentation.components.workspace.ode.ode_state import ODEOrder

SECOND_ORDER_EULER_CONFIG = EulerPanelConfig(
    order=NumericalODEOrder.SECOND_ORDER,
    banner_text=(
        "PTVP cấp 2 — Euler tiến (IVP): Hệ thống tự chuyển y'' = F(t, y, y') về hệ cấp 1 (z₁ = y, z₂ = y') "
        "và cập nhật đồng thời từ (yₙ, vₙ). Lưu ý: Thuật toán số Explicit Euler khác với phương trình vi phân giải tích Euler–Cauchy."
    ),
    equation_label="Phương trình vi phân cấp 2: y'' = F(t, y, y') (hoặc At²y'' + Bty' + Cy = g(t))",
    equation_placeholder="y'' = -y",
    default_equation="y'' = -y",
    default_indep_var="t",
    default_t0="0",
    default_y0="0",
    default_v0="1",
    default_t_end="3.14",
    default_step_size="0.1",
    ivp_section_heading="ĐIỀU KIỆN BAN ĐẦU y(t₀) = y₀, y'(t₀) = v₀ & THAM SỐ LƯỚI",
    y0_label="Vị trí ban đầu y₀ = y(t₀)",
    examples_label="Ví dụ Euler tiến (Cấp 2):",
    examples=(
        ("Dao động điều hòa: y'' = -y, y(0)=0, y'(0)=1", ("y'' = -y", "t", "0", "0", "1", "3.14", "0.1")),
        ("Vận tốc không đổi: y'' = 0, y(0)=2, y'(0)=3", ("y'' = 0", "t", "0", "2", "3", "2", "0.5")),
        ("Không thuần nhất: y'' + y = t, y(0)=1, y'(0)=0", ("y'' + y = t", "t", "0", "1", "0", "1", "0.1")),
        ("Con lắc phi tuyến: y'' = -sin(y), y(0)=0.5, y'(0)=0", ("y'' = -sin(y)", "t", "0", "0.5", "0", "1.5", "0.1")),
        ("Euler–Cauchy (t > 0): t^2y'' - ty' + y = t^2", ("t^2*y'' - t*y' + y = t^2", "t", "1", "0", "0", "2", "0.1")),
    ),
    cta_text="TÍNH XẤP XỈ EULER CẤP 2",
    cta_aria_label="Tính nghiệm xấp xỉ Explicit Euler cho phương trình vi phân cấp 2",
    reset_aria_label="Khôi phục tham số Euler tiến cấp 2 mặc định",
)


def render_second_order_euler_panel(
    numerical_use_case: Any,
    results_container: ui.column,
    on_switch_order: Callable[[ODEOrder], None] | None = None,
) -> None:
    """Render the dedicated Second-Order Explicit Euler IVP workspace panel."""
    render_order_specific_euler_form(
        SECOND_ORDER_EULER_CONFIG,
        numerical_use_case=numerical_use_case,
        results_container=results_container,
        on_switch_order=on_switch_order,
    )

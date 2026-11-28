"""Order-aware dispatcher delegating Explicit Euler UI to dedicated 1st- or 2nd-order panels."""

from __future__ import annotations

from typing import Any, Callable

from nicegui import ui

from math_app.presentation.components.workspace.ode.first_order_euler_panel import (
    render_first_order_euler_panel,
)
from math_app.presentation.components.workspace.ode.ode_state import ODEOrder
from math_app.presentation.components.workspace.ode.second_order_euler_panel import (
    render_second_order_euler_panel,
)


def render_numerical_euler_panel(
    initial_order: ODEOrder,
    numerical_use_case: Any,
    results_container: ui.column,
    on_order_sync: Callable[[ODEOrder], None] | None = None,
) -> None:
    """Dispatch cleanly to the dedicated First-Order or Second-Order Explicit Euler panel."""
    if initial_order == ODEOrder.FIRST_ORDER:
        render_first_order_euler_panel(
            numerical_use_case=numerical_use_case,
            results_container=results_container,
            on_switch_order=on_order_sync,
        )
    else:
        render_second_order_euler_panel(
            numerical_use_case=numerical_use_case,
            results_container=results_container,
            on_switch_order=on_order_sync,
        )

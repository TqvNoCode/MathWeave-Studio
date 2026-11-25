"""Operation Catalog (Screen A) view component for MathWeave Studio."""

from __future__ import annotations

from collections.abc import Callable
from nicegui import ui

from math_app.presentation.components.catalog.operation_card import render_operation_card
from math_app.presentation.components.operation_catalog import MAIN_OPERATIONS, OperationDef
from math_app.presentation.design_system.tokens import TYPOGRAPHY


def _get_domain_icon(domain: str) -> str:
    """Return appropriate Material icon for a mathematical domain."""
    d = domain.lower()
    if "vectơ" in d or "vector" in d:
        return "all_inclusive"
    if "vi phân" in d or "ode" in d:
        return "show_chart"
    if "tuyến tính" in d or "matrix" in d or "linear" in d:
        return "grid_view"
    if "đại số" in d or "algebra" in d:
        return "calculate"
    return "query_stats"


def render_operation_catalog(
    on_select: Callable[[OperationDef], None],
    operations: list[OperationDef] | None = None,
) -> ui.column:
    """Render the complete Screen A operation catalog grouped by domain.

    Guarantees that all 23 main catalog operations are displayed with consistent
    card primitives, clear hierarchy, and accessible styling. The `on_select`
    callback is strictly required to enforce explicit action binding.
    """
    ops = operations if operations is not None else MAIN_OPERATIONS

    # Standard pedagogical domain ordering
    domain_order = [
        "Giải tích (Calculus)",
        "Đại số & Giải tích",
        "Phương trình vi phân (Differential Equations)",
        "Giải tích vectơ (Vector Calculus)",
        "Đại số tuyến tính (Linear Algebra)",
    ]

    # Collect domains dynamically preserving order, followed by any remaining
    seen_domains: list[str] = []
    for d in domain_order:
        if any(o.domain == d for o in ops) and d not in seen_domains:
            seen_domains.append(d)
    for o in ops:
        if o.domain not in seen_domains:
            seen_domains.append(o.domain)

    with ui.column().classes("w-full gap-5") as catalog_col:
        # Main Heading
        with ui.row().classes("w-full items-center justify-between pt-1 pb-2 border-b border-slate-100"):
            ui.label("Chọn dạng toán cần giải quyết").classes(TYPOGRAPHY.PAGE_TITLE)

        for dom in seen_domains:
            domain_ops = [o for o in ops if o.domain == dom]
            if not domain_ops:
                continue

            with ui.column().classes("w-full gap-3 mt-1"):
                # Domain header row
                with ui.row().classes("items-center gap-2"):
                    ui.icon(_get_domain_icon(dom), size="1.3rem").classes("text-blue-600")
                    ui.label(dom).classes(TYPOGRAPHY.SECTION_HEADING)
                    ui.badge(f"{len(domain_ops)} dạng toán", color="slate-200").classes(
                        "text-xs text-slate-700 font-semibold rounded-md px-2"
                    )

                # Responsive 3-column grid
                with ui.grid().classes("grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 w-full"):
                    for op in domain_ops:
                        render_operation_card(op=op, on_select=on_select)

    return catalog_col

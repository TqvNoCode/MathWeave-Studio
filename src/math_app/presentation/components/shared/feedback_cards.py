"""Reusable accessible feedback, loading, and empty-state cards."""

from __future__ import annotations

from nicegui import ui

from math_app.presentation.design_system.tokens import RADIUS, ELEVATION


def render_loading_card(message: str = "Đang giải toán và thực hiện kiểm định độc lập...") -> ui.card:
    """Render a consistent centered loading card with ARIA live status semantics."""
    with ui.card().props('role="status" aria-live="polite"').classes(
        f"w-full p-6 border border-slate-200 bg-white {RADIUS.LG} {ELEVATION.XS} text-center items-center justify-center min-w-0"
    ) as card:
        ui.spinner("dots", size="2.25rem", color="primary")
        ui.label(message).classes("text-sm font-medium text-slate-700 mt-2")
    return card


def render_feedback_card(
    title: str,
    messages: list[str] | tuple[str, ...],
    variant: str = "error",
    hint: str | None = None,
) -> ui.card:
    """Render an accessible semantic feedback card with icon + text (never color alone)."""
    v = variant.lower()
    if v in ("warning", "amber"):
        surface = "border-amber-200 bg-amber-50/90 text-amber-950"
        icon_name = "warning"
        icon_color = "warning"
        title_cls = "text-amber-950"
        body_cls = "text-amber-900"
    elif v in ("info", "blue"):
        surface = "border-blue-200 bg-blue-50/80 text-blue-950"
        icon_name = "info"
        icon_color = "primary"
        title_cls = "text-blue-950"
        body_cls = "text-blue-900"
    else:
        surface = "border-rose-200 bg-rose-50/80 text-rose-950"
        icon_name = "error_outline"
        icon_color = "negative"
        title_cls = "text-rose-950"
        body_cls = "text-rose-900"

    with ui.card().props('role="alert"').classes(
        f"w-full p-4 md:p-5 border {surface} {RADIUS.LG} {ELEVATION.XS} gap-2 min-w-0"
    ) as card:
        with ui.row().classes("items-center gap-2"):
            ui.icon(icon_name, color=icon_color, size="1.35rem").classes("shrink-0")
            ui.label(title).classes(f"text-base font-bold {title_cls}")
        for msg in messages:
            if msg and msg.strip():
                prefix = "• " if len(messages) > 1 else ""
                ui.label(f"{prefix}{msg}").classes(f"text-sm {body_cls} leading-relaxed")
        if hint:
            ui.label(hint).classes(f"text-xs {body_cls} italic")
    return card


def render_empty_state_card(message: str) -> ui.card:
    """Render a consistent empty-state card."""
    with ui.card().classes(
        f"w-full p-4 border border-slate-200 bg-slate-50 {RADIUS.LG} text-center min-w-0"
    ) as card:
        ui.label(message).classes("text-slate-600 italic text-sm")
    return card

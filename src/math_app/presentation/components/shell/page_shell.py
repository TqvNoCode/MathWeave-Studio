"""Page shell layout container for MathWeave Studio."""

from __future__ import annotations

from nicegui import ui


def create_page_shell(classes: str = "") -> ui.column:
    """Create a standardized responsive fluid root container for page content.

    Provides comfortable reading widths for 1024px, 1366px, 1920px, and 2560px
    displays with responsive padding and flexible vertical alignment.
    """
    base_classes = (
        "w-full max-w-7xl mx-auto p-4 md:p-6 gap-6 min-h-screen flex flex-col justify-between"
    )
    combined = f"{base_classes} {classes}".strip() if classes else base_classes
    return ui.column().classes(combined)

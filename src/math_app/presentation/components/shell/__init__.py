"""Shell presentation components for MathWeave Studio."""

from math_app.presentation.components.shell.app_header import render_app_header
from math_app.presentation.components.shell.page_shell import create_page_shell
from math_app.presentation.components.shell.scroll_manager import (
    capture_catalog_scroll,
    reset_workspace_scroll,
    restore_catalog_scroll,
)
from math_app.presentation.components.shell.sticky_nav_bar import render_sticky_nav_bar

__all__ = [
    "capture_catalog_scroll",
    "create_page_shell",
    "render_app_header",
    "render_sticky_nav_bar",
    "reset_workspace_scroll",
    "restore_catalog_scroll",
]

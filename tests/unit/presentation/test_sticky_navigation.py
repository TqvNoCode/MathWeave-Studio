"""Unit and regression tests for sticky operation navigation bar behavior and layout."""

from __future__ import annotations

import inspect
from nicegui import ui
from math_app.presentation.app import create_app
from math_app.presentation.components.shell.page_shell import create_page_shell
from math_app.presentation.components.shell.sticky_nav_bar import render_sticky_nav_bar


def test_sticky_navigation_bar_css_classes():
    """Verify that the operation navigation bar in Screen B defines CSS sticky positioning,
    opaque background, top offset, border, and elevation shadow.
    """
    source = inspect.getsource(create_app)

    # Locate the navigation bar definition in render_screen_b
    assert "render_screen_b" in source
    assert "render_sticky_nav_bar" in source

    # Verify sticky navigation component classes directly on component instance
    with ui.card():
        navbar = render_sticky_nav_bar(
            title="Đạo hàm",
            domain="Giải tích (Calculus)",
            on_back=lambda: None,
        )
    nav_classes = navbar._classes

    # Verify sticky positioning properties
    assert "sticky" in nav_classes, "Navigation bar must declare CSS position: sticky"
    assert "top-0" in nav_classes, "Sticky navigation bar must have top-0 offset"
    assert "z-30" in nav_classes, "Sticky navigation bar must declare a high z-index"
    assert "bg-white" in nav_classes, "Sticky navigation bar must be opaque (bg-white)"
    assert "border" in nav_classes, "Sticky navigation bar must have a clean border"
    assert "shadow-sm" in nav_classes, "Sticky navigation bar must have elevation shadow"


def test_no_overflow_hidden_on_parent_containers():
    """Verify that Screen B parent containers (page_col, screen_body) do not declare
    overflow: hidden or overflow: auto which would trap/break CSS position: sticky.
    """
    source = inspect.getsource(create_app)

    # Check page_col definition uses create_page_shell
    assert "page_col = create_page_shell()" in source
    with ui.card():
        page_col = create_page_shell()
    assert "overflow-hidden" not in page_col._classes
    assert "overflow-auto" not in page_col._classes

    # Check screen_body definition
    screen_body_idx = source.find("screen_body = ui.column()")
    assert screen_body_idx != -1
    screen_body_line = source[screen_body_idx : screen_body_idx + 150]
    assert "overflow-hidden" not in screen_body_line
    assert "overflow-auto" not in screen_body_line

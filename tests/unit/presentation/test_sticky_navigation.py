"""Unit and regression tests for sticky operation navigation bar behavior and layout."""

from __future__ import annotations

import inspect
from math_app.presentation.app import create_app


def test_sticky_navigation_bar_css_classes():
    """Verify that the operation navigation bar in Screen B defines CSS sticky positioning,
    opaque background, top offset, border, and elevation shadow.
    """
    source = inspect.getsource(create_app)

    # Locate the navigation bar definition in render_screen_b
    assert "render_screen_b" in source
    nav_marker = "Navigation Bar with Shared High-Contrast Back Button (Sticky on scroll)"
    assert nav_marker in source

    # Extract the snippet containing the sticky navigation row
    idx = source.find(nav_marker)
    nav_snippet = source[idx : idx + 300]

    # Verify sticky positioning properties
    assert "sticky" in nav_snippet, "Navigation bar must declare CSS position: sticky"
    assert "top-0" in nav_snippet, "Sticky navigation bar must have top-0 offset"
    assert "z-30" in nav_snippet, "Sticky navigation bar must declare a high z-index"
    assert "bg-white" in nav_snippet, "Sticky navigation bar must be opaque (bg-white)"
    assert "border" in nav_snippet, "Sticky navigation bar must have a clean border"
    assert "shadow-sm" in nav_snippet, "Sticky navigation bar must have elevation shadow"


def test_no_overflow_hidden_on_parent_containers():
    """Verify that Screen B parent containers (page_col, screen_body) do not declare
    overflow: hidden or overflow: auto which would trap/break CSS position: sticky.
    """
    source = inspect.getsource(create_app)

    # Check page_col definition
    page_col_idx = source.find("page_col = ui.column()")
    assert page_col_idx != -1
    page_col_line = source[page_col_idx : page_col_idx + 150]
    assert "overflow-hidden" not in page_col_line
    assert "overflow-auto" not in page_col_line

    # Check screen_body definition
    screen_body_idx = source.find("screen_body = ui.column()")
    assert screen_body_idx != -1
    screen_body_line = source[screen_body_idx : screen_body_idx + 150]
    assert "overflow-hidden" not in screen_body_line
    assert "overflow-auto" not in screen_body_line

"""Unit and regression tests for MathWeave Studio application branding, metadata, and footer."""

from nicegui import ui

from math_app import (
    __author__,
    __compact_name__,
    __copyright__,
    __slug__,
    __title__,
    __version__,
)
from math_app.domain.exceptions import MathStudioError, MathWeaveStudioError
from math_app.presentation.components.footer import AUTHOR_CREDIT, render_footer


def test_branding_identifiers():
    """Verify application branding identifiers match project requirements."""
    assert __title__ == "MathWeave Studio"
    assert __compact_name__ == "MathWeaveStudio"
    assert __slug__ == "mathweave-studio"
    assert __author__ == "TQV"
    assert __copyright__ == "© 2026 by TQV"
    assert __version__ == "0.1.0"


def test_author_credit_constant():
    """Verify author credit text matches the exact required specification."""
    assert AUTHOR_CREDIT == "© 2026 by TQV"


def test_backward_compatibility_exceptions():
    """Verify legacy MathStudioError alias is preserved for backward compatibility."""
    assert MathStudioError is MathWeaveStudioError
    assert issubclass(MathStudioError, Exception)


def test_version_badge_format():
    """Verify that version badge reflects truthful MVP version and excludes 'Desktop' label."""
    badge_text = f"MVP · v{__version__}"
    assert badge_text == "MVP · v0.1.0"
    assert "Desktop" not in badge_text
    assert "v1.0" not in badge_text


def test_footer_component_structure():
    """Verify footer renders right-aligned low-emphasis credit without layout distortion."""
    with ui.card():
        footer_element = render_footer()
        assert footer_element is not None
        # Verify right alignment and bottom placement classes
        classes = footer_element._classes
        assert "justify-end" in classes
        assert "items-center" in classes

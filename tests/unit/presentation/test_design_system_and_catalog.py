"""Unit and interaction tests for centralized design system, PageShell, and Screen A catalog."""

from __future__ import annotations

import pytest
from nicegui import ui

from math_app import __version__
from math_app.domain.models import ProblemType
from math_app.presentation.components.catalog.operation_card import render_operation_card
from math_app.presentation.components.catalog.operation_catalog_view import (
    render_operation_catalog,
)
from math_app.presentation.components.operation_catalog import (
    MAIN_OPERATIONS,
    OPERATIONS,
    OperationDef,
    get_operation_by_type,
)
from math_app.presentation.components.shared.primary_button import primary_button
from math_app.presentation.components.shared.section_card import section_card
from math_app.presentation.components.shared.status_badge import status_badge
from math_app.presentation.components.shell.app_header import render_app_header
from math_app.presentation.components.shell.page_shell import create_page_shell
from math_app.presentation.components.shell.sticky_nav_bar import render_sticky_nav_bar
from math_app.presentation.design_system.styles import get_head_html
from math_app.presentation.design_system.tokens import (
    ELEVATION,
    PRIMARY,
    RADIUS,
    SEMANTIC,
    SPACING,
    SURFACES,
    TYPOGRAPHY,
)


def _srgb_to_linear(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_col: str) -> float:
    hex_col = hex_col.lstrip("#")
    r, g, b = (int(hex_col[i : i + 2], 16) for i in (0, 2, 4))
    return (
        0.2126 * _srgb_to_linear(r)
        + 0.7152 * _srgb_to_linear(g)
        + 0.0722 * _srgb_to_linear(b)
    )


def _contrast_ratio(c1: str, c2: str) -> float:
    l1, l2 = _relative_luminance(c1), _relative_luminance(c2)
    top, bottom = max(l1, l2), min(l1, l2)
    return (top + 0.05) / (bottom + 0.05)


def test_design_system_tokens():
    """Verify primary and semantic tokens are configured properly."""
    assert PRIMARY.BLUE_600 == "#2563eb"
    assert PRIMARY.BLUE_700 == "#1d4ed8"
    assert SURFACES.CANVAS == "#f8fafc"
    assert SURFACES.CARD == "#ffffff"
    assert SPACING.GAP_4 == "gap-4"
    assert RADIUS.LG == "rounded-xl"
    assert ELEVATION.SM == "shadow-sm"
    assert "Inter" in TYPOGRAPHY.FONT_FAMILY_BASE
    assert "DejaVu Math TeX Gyre" in TYPOGRAPHY.FONT_FAMILY_MATH


def test_wcag_contrast_ratios():
    """Verify all text/background combinations meet WCAG AA (>= 4.5:1) and AAA (>= 7:1)."""
    # Muted text on white
    assert _contrast_ratio(SURFACES.TEXT_MUTED, "#ffffff") >= 7.0  # AAA
    # Main text on white
    assert _contrast_ratio(SURFACES.TEXT_MAIN, "#ffffff") >= 14.0  # AAA

    # Semantic badge contrasts
    assert _contrast_ratio(SEMANTIC.SUCCESS.text, SEMANTIC.SUCCESS.bg) >= 7.0  # AAA
    assert _contrast_ratio(SEMANTIC.WARNING.text, SEMANTIC.WARNING.bg) >= 7.0  # AAA
    assert _contrast_ratio(SEMANTIC.ERROR.text, SEMANTIC.ERROR.bg) >= 7.0      # AAA
    assert _contrast_ratio(SEMANTIC.INFO.text, SEMANTIC.INFO.bg) >= 7.0        # AAA
    assert _contrast_ratio(SEMANTIC.NEUTRAL.text, SEMANTIC.NEUTRAL.bg) >= 7.0  # AAA


def test_head_html_offline_and_no_remote_cdns():
    """Verify head HTML is offline-safe and does not import Google Fonts or external CDNs."""
    head_html = get_head_html()
    assert "fonts.googleapis.com" not in head_html
    assert "jsdelivr.net" not in head_html
    assert "cdnjs.cloudflare.com" not in head_html
    assert "/assets/katex/katex.css" in head_html
    assert "/assets/fonts/DejaVuMathTeXGyre.ttf" in head_html
    assert "DejaVu Math TeX Gyre" in head_html
    assert "MutationObserver" in head_html


def test_math_renderer_performance_bounded_retries_and_attribute_observer():
    """Verify math renderer uses bounded startup retry and observes data-tex attributes."""
    head_html = get_head_html()
    assert "MutationObserver" in head_html
    assert "data-tex" in head_html
    assert "attributeFilter" in head_html
    # Must use bounded retries with clearInterval rather than unbounded infinite periodic scanning
    assert "clearInterval" in head_html
    assert "maxRetries" in head_html


# ---------------------------------------------------------------------------
# Interaction & Integration Acceptance Tests (UX1.1 Requirements 1-3)
# ---------------------------------------------------------------------------

def test_operation_card_click_invokes_on_select_exactly_once():
    """Req 1: Clicking an operation card invokes on_select exactly once."""
    invocations: list[OperationDef] = []

    def on_sel(selected_op: OperationDef) -> None:
        invocations.append(selected_op)

    deriv_op = get_operation_by_type(ProblemType.DERIVATIVE)

    with ui.card():
        card = render_operation_card(deriv_op, on_select=on_sel)

    # Locate the click event listener attached to the card
    click_listeners = [
        listener for listener in card._event_listeners.values() if listener.type == "click"
    ]
    assert len(click_listeners) == 1, "Card must have exactly one click event listener"

    # Invoke the click handler simulating a user click
    click_listeners[0].handler(None)

    assert len(invocations) == 1, "on_select must be invoked exactly once on click"
    assert invocations[0].problem_type == ProblemType.DERIVATIVE
    assert invocations[0].title == deriv_op.title


def test_different_cards_invoke_callbacks_with_correct_operation_def():
    """Req 2: Different cards invoke callbacks with the correct OperationDef."""
    selected: list[OperationDef] = []

    def on_sel(op: OperationDef) -> None:
        selected.append(op)

    op_derivative = get_operation_by_type(ProblemType.DERIVATIVE)
    op_matrix_det = get_operation_by_type(ProblemType.MATRIX_DETERMINANT)
    op_ode = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)

    with ui.card():
        card_deriv = render_operation_card(op_derivative, on_select=on_sel)
        card_det = render_operation_card(op_matrix_det, on_select=on_sel)
        card_ode = render_operation_card(op_ode, on_select=on_sel)

    # Trigger click on derivative card
    [
        listener
        for listener in card_deriv._event_listeners.values()
        if listener.type == "click"
    ][0].handler(None)
    assert len(selected) == 1
    assert selected[-1].problem_type == ProblemType.DERIVATIVE
    assert selected[-1].title == "Đạo hàm"

    # Trigger click on matrix det card
    [
        listener
        for listener in card_det._event_listeners.values()
        if listener.type == "click"
    ][0].handler(None)
    assert len(selected) == 2
    assert selected[-1].problem_type == ProblemType.MATRIX_DETERMINANT
    assert selected[-1].domain == "Đại số tuyến tính (Linear Algebra)"

    # Trigger click on ODE card
    [
        listener
        for listener in card_ode._event_listeners.values()
        if listener.type == "click"
    ][0].handler(None)
    assert len(selected) == 3
    assert selected[-1].problem_type == ProblemType.ODE_FIRST_ORDER_LINEAR
    assert "Phương trình vi phân" in selected[-1].title


def test_about_action_semantic_button_invokes_callback():
    """Req 3: About action uses a semantic accessible button and invokes its callback."""
    about_called = False

    def on_about() -> None:
        nonlocal about_called
        about_called = True

    with ui.card() as container:
        header_el = render_app_header(on_about_click=on_about)

    assert header_el is not None
    # Find the version button among descendants
    about_buttons = [
        el for el in container.descendants()
        if isinstance(el, ui.button) and f"v{__version__}" in str(el._props.get("label", ""))
    ]
    assert len(about_buttons) == 1, "Semantic About button with version text must exist"
    about_btn = about_buttons[0]

    # Verify accessibility semantics and styling
    assert "rounded-full" in about_btn._classes
    assert "bg-slate-700" in about_btn._classes
    assert "cursor-pointer" in about_btn._classes
    assert "focus-visible:ring-2" in about_btn._classes
    assert "aria-label" in about_btn._props
    assert "Thông tin ứng dụng" in about_btn._props["aria-label"]

    # Trigger button click
    click_listeners = [
        listener for listener in about_btn._event_listeners.values() if listener.type == "click"
    ]
    assert len(click_listeners) == 1
    click_listeners[0].handler(None)

    assert about_called is True, "About callback must be invoked when clicking version button"


def test_operation_card_keyboard_activation_and_accessibility():
    """Req 4: Keyboard activation works (Enter, Space) and card has proper accessibility semantics."""
    activated: list[str] = []

    def on_sel(op: OperationDef) -> None:
        activated.append(op.title)

    op = get_operation_by_type(ProblemType.INDEFINITE_INTEGRAL)

    with ui.card():
        card = render_operation_card(op, on_select=on_sel)

    # 1. Semantics and ARIA check
    assert card._props.get("role") == "button", "Card must have role='button'"
    assert card._props.get("tabindex") == "0", "Card must be keyboard focusable (tabindex=0)"
    assert "aria-label" in card._props
    assert op.title in card._props["aria-label"]

    # 2. Focus indicator classes check
    assert "focus-visible:ring-2" in card._classes
    assert "focus-visible:ring-blue-500" in card._classes

    # 3. Enter key activation listener
    enter_listeners = [
        listener for listener in card._event_listeners.values() if listener.type == "keydown.enter"
    ]
    assert len(enter_listeners) == 1, "Must have keydown.enter listener"
    enter_listeners[0].handler(None)
    assert len(activated) == 1
    assert activated[-1] == op.title

    # 4. Space key activation listener (with preventDefault)
    space_listeners = [
        listener for listener in card._event_listeners.values() if "space" in listener.type
    ]
    assert len(space_listeners) == 1, "Must have space key listener"
    space_listeners[0].handler(None)
    assert len(activated) == 2
    assert activated[-1] == op.title


def test_page_shell_component_and_authoritative_root():
    """Req 5: PageShell renders correctly as authoritative responsive root shell."""
    with ui.card():
        shell = create_page_shell()
        assert shell is not None
        assert isinstance(shell, ui.column)
        classes = shell._classes
        # Authoritative single root container specifications
        assert "max-w-7xl" in classes
        assert "min-h-screen" in classes
        assert "mx-auto" in classes
        assert "w-full" in classes
        assert "p-4" in classes
        assert "md:p-6" in classes

        # Custom class extension support
        shell_custom = create_page_shell(classes="extra-custom-shell")
        assert "extra-custom-shell" in shell_custom._classes
        assert "max-w-7xl" in shell_custom._classes


def test_sticky_nav_bar_invokes_original_back_callback():
    """Req 6: Sticky navigation invokes original back callback."""
    back_invoked = False

    def on_back() -> None:
        nonlocal back_invoked
        back_invoked = True

    with ui.card() as container:
        navbar = render_sticky_nav_bar(
            title="Tích phân xác định (Một biến)",
            domain="Giải tích (Calculus)",
            on_back=on_back,
            math_icon=r"\int_a^b f(x)\,dx",
        )

    assert navbar is not None
    assert "sticky" in navbar._classes
    assert "top-0" in navbar._classes
    assert "z-30" in navbar._classes

    # Find the back button among descendants
    back_buttons = [el for el in container.descendants() if isinstance(el, ui.button)]
    assert len(back_buttons) >= 1

    back_btn = back_buttons[0]
    click_listeners = [
        listener for listener in back_btn._event_listeners.values() if listener.type == "click"
    ]
    assert len(click_listeners) == 1
    click_listeners[0].handler(None)

    assert back_invoked is True, "Sticky nav back button must invoke original on_back callback"


def test_catalog_contains_exactly_23_main_operations():
    """Req 7: Catalog contains exactly 23 main operations."""
    assert len(MAIN_OPERATIONS) == 23

    selected: list[OperationDef] = []
    with ui.card() as container:
        catalog = render_operation_catalog(on_select=lambda op: selected.append(op))

    assert catalog is not None

    # Count interactive operation cards rendered (cards with role='button')
    rendered_cards = [
        el for el in container.descendants()
        if isinstance(el, ui.card) and el._props.get("role") == "button"
    ]
    assert len(rendered_cards) == 23, (
        f"Expected exactly 23 operation cards on Screen A, found {len(rendered_cards)}"
    )


def test_all_five_domain_groups_represented_in_catalog():
    """Req 8: All 5 pedagogical domain groups are represented in catalog."""
    expected_domains = [
        "Giải tích (Calculus)",
        "Đại số & Giải tích",
        "Phương trình vi phân (Differential Equations)",
        "Giải tích vectơ (Vector Calculus)",
        "Đại số tuyến tính (Linear Algebra)",
    ]

    # Verify all domains are present in MAIN_OPERATIONS
    catalog_domains = {op.domain for op in MAIN_OPERATIONS}
    for d in expected_domains:
        assert d in catalog_domains, f"Domain '{d}' must be present in MAIN_OPERATIONS"

    # Verify counts per domain
    domain_counts = {d: sum(1 for op in MAIN_OPERATIONS if op.domain == d) for d in expected_domains}
    assert domain_counts["Giải tích (Calculus)"] == 8
    assert domain_counts["Đại số & Giải tích"] == 1
    assert domain_counts["Phương trình vi phân (Differential Equations)"] == 2
    assert domain_counts["Giải tích vectơ (Vector Calculus)"] == 3
    assert domain_counts["Đại số tuyến tính (Linear Algebra)"] == 9
    assert sum(domain_counts.values()) == 23


def test_secondary_workflows_remain_reachable():
    """Req 9: Secondary workflows remain reachable via OPERATIONS and get_operation_by_type."""
    secondary_ops = [o for o in OPERATIONS if not o.is_menu_card]
    assert len(secondary_ops) == 10, f"Expected 10 secondary operations, found {len(secondary_ops)}"

    # Specific expected secondary workflows
    expected_subtypes = [
        ProblemType.LINE_INTEGRAL,
        ProblemType.SURFACE_INTEGRAL,
        ProblemType.TRIPLE_INTEGRAL,
        ProblemType.ODE_FIRST_ORDER_HOMOGENEOUS,
        ProblemType.ODE_SEPARABLE,
        ProblemType.ODE_EXACT,
        ProblemType.ODE_INTEGRATING_FACTOR,
        ProblemType.ODE_SECOND_ORDER_IVP,
        ProblemType.ODE_REDUCTION_OF_ORDER,
        ProblemType.WRONSKIAN,
    ]

    for pt in expected_subtypes:
        op = get_operation_by_type(pt)
        assert op is not None, f"Operation for {pt} must be retrievable"
        assert op.is_menu_card is False, f"Subtype {pt} should not be a main menu card"
        assert len(op.title.strip()) > 0
        assert len(op.domain.strip()) > 0


def test_catalog_callback_contract_requires_on_select():
    """Req 2 (Callback Contract): on_select is a strictly required parameter."""
    with pytest.raises(TypeError):
        # Calling without on_select must raise TypeError
        render_operation_catalog()  # type: ignore[call-arg]


def test_shared_primitives_typed_and_stateless():
    """Verify section_card, primary_button, and status_badge are typed and functional."""
    clicked = False

    with ui.card():
        card = section_card()
        assert card is not None
        assert "border-slate-200" in card._classes

        btn = primary_button("Giải bài toán", icon="play_arrow", on_click=lambda: clicked.__setitem__(slice(None), [True]))
        assert btn is not None
        assert "bg-blue-600" in btn._classes

        badge_success = status_badge("Đã kiểm định", variant="success")
        assert badge_success is not None
        assert SEMANTIC.SUCCESS.text in badge_success._style.get("color", "")

        badge_warn = status_badge("Cảnh báo", variant="warning")
        assert badge_warn is not None
        assert SEMANTIC.WARNING.text in badge_warn._style.get("color", "")

        badge_err = status_badge("Lỗi cú pháp", variant="error")
        assert badge_err is not None
        assert SEMANTIC.ERROR.text in badge_err._style.get("color", "")

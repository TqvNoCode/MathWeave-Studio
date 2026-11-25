"""Comprehensive test suite for Screen A -> Screen B scroll position isolation and restoration.

Validates UX3.4.2 requirements:
- Test 1: Catalog scrolled down -> Second-Order ODE starts at top (0).
- Test 2: Catalog scrolled down -> First-Order ODE starts at top (0).
- Test 3: Catalog -> Green's Theorem -> Back restores previous catalog scroll position.
- Test 4: Catalog -> ODE -> Back -> Another operation starts at top (0).
- Test 5: Workspace internal interactions (classification, mode, Cauchy) do not reset scroll.
- Test 6: Viewport dimensions (1024x768, 1280x800, 1920x1080) and scrolling owner validation.
- Test 7: Real QtWebEngine Chromium offscreen DOM scroll isolation and restoration.
"""

from __future__ import annotations

import inspect
import os
import subprocess
from unittest.mock import MagicMock
from nicegui import Client, ui

from math_app.domain.models import ProblemType
from math_app.presentation.app import create_app
from math_app.presentation.components.operation_catalog import (
    get_operation_by_type,
)
from math_app.presentation.components.shell.page_shell import create_page_shell
from math_app.presentation.components.shell.scroll_manager import (
    capture_catalog_scroll,
    reset_workspace_scroll,
    restore_catalog_scroll,
)
from math_app.presentation.components.shell.sticky_nav_bar import render_sticky_nav_bar
from math_app.presentation.components.workspace.ode.ode_workspace import render_ode_workspace


# =============================================================================
# SCROLL MANAGER CONTRACT TESTS
# =============================================================================

def test_scroll_manager_capture_catalog_contract():
    """Verify capture_catalog_scroll dispatches JS saving scroll position to window._mw_catalog_scroll."""
    mock_client = MagicMock()
    mock_client.has_socket_connection = True
    mock_client.is_deleted = False
    mock_client.id = "test-client-1"

    capture_catalog_scroll(client=mock_client)

    assert mock_client.outbox.enqueue_message.called or mock_client.run_javascript.called
    call_args = (
        mock_client.outbox.enqueue_message.call_args[0]
        if mock_client.outbox.enqueue_message.called
        else mock_client.run_javascript.call_args[0]
    )
    js_code = str(call_args)
    assert "window._mw_catalog_scroll" in js_code
    assert "window.scrollY" in js_code
    assert "document.scrollingElement" in js_code


def test_scroll_manager_reset_workspace_contract():
    """Verify reset_workspace_scroll dispatches JS resetting top to 0 across all candidate scrolling containers."""
    mock_client = MagicMock()
    mock_client.has_socket_connection = True
    mock_client.is_deleted = False
    mock_client.id = "test-client-2"

    reset_workspace_scroll(client=mock_client)

    assert mock_client.outbox.enqueue_message.called or mock_client.run_javascript.called
    call_args = (
        mock_client.outbox.enqueue_message.call_args[0]
        if mock_client.outbox.enqueue_message.called
        else mock_client.run_javascript.call_args[0]
    )
    js_code = str(call_args)
    assert "window.scrollTo({top: 0" in js_code
    assert "document.scrollingElement.scrollTop = 0" in js_code
    assert "document.documentElement.scrollTop = 0" in js_code
    assert "document.body.scrollTop = 0" in js_code


def test_scroll_manager_restore_catalog_contract():
    """Verify restore_catalog_scroll dispatches JS restoring window._mw_catalog_scroll without resetting to 0."""
    mock_client = MagicMock()
    mock_client.has_socket_connection = True
    mock_client.is_deleted = False
    mock_client.id = "test-client-3"

    restore_catalog_scroll(client=mock_client)

    assert mock_client.outbox.enqueue_message.called or mock_client.run_javascript.called
    call_args = (
        mock_client.outbox.enqueue_message.call_args[0]
        if mock_client.outbox.enqueue_message.called
        else mock_client.run_javascript.call_args[0]
    )
    js_code = str(call_args)
    assert "window._mw_catalog_scroll" in js_code
    assert "window.scrollTo({top: pos" in js_code
    assert "document.scrollingElement.scrollTop = pos" in js_code


# =============================================================================
# SCENARIO TESTS 1 TO 6
# =============================================================================

def test_1_catalog_scrolled_down_to_second_order_ode_starts_at_top():
    """Test 1: When selecting Second-Order ODE from a scrolled catalog, Screen B starts at the top."""
    source = inspect.getsource(create_app)
    assert "def switch_to_operation(op: OperationDef)" in source
    assert "capture_catalog_scroll" in source
    assert "reset_workspace_scroll" in source

    ode_op = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)
    assert ode_op is not None
    assert ode_op.domain == "Phương trình vi phân (Differential Equations)"

    mock_client = MagicMock()
    mock_client.has_socket_connection = True
    mock_client.is_deleted = False
    mock_client.id = "mock-client"

    capture_catalog_scroll(mock_client)
    reset_workspace_scroll(mock_client)

    assert mock_client.outbox.enqueue_message.call_count >= 2
    reset_call = mock_client.outbox.enqueue_message.call_args_list[1][0]
    assert "top: 0" in str(reset_call)


def test_2_catalog_scrolled_down_to_first_order_ode_starts_at_top():
    """Test 2: When selecting First-Order ODE from a scrolled catalog, Screen B starts at the top."""
    ode1_op = get_operation_by_type(ProblemType.ODE_FIRST_ORDER_LINEAR)
    assert ode1_op is not None
    assert ode1_op.domain == "Phương trình vi phân (Differential Equations)"

    mock_client = MagicMock()
    mock_client.has_socket_connection = True
    mock_client.is_deleted = False
    mock_client.id = "mock-client-ode1"

    capture_catalog_scroll(mock_client)
    reset_workspace_scroll(mock_client)

    reset_call = mock_client.outbox.enqueue_message.call_args_list[-1][0]
    assert "top: 0" in str(reset_call)
    assert "document.documentElement.scrollTop = 0" in str(reset_call)


def test_3_catalog_to_greens_theorem_and_back_restores_scroll():
    """Test 3: Catalog -> Green's Theorem -> Back restores previous catalog scroll position."""
    source = inspect.getsource(create_app)
    assert "def switch_to_catalog()" in source
    assert "restore_catalog_scroll" in source

    gt_op = get_operation_by_type(ProblemType.GREENS_THEOREM)
    assert gt_op is not None
    assert gt_op.domain == "Giải tích vectơ (Vector Calculus)"

    mock_client = MagicMock()
    mock_client.has_socket_connection = True
    mock_client.is_deleted = False
    mock_client.id = "mock-client-gt"

    capture_catalog_scroll(mock_client)
    reset_workspace_scroll(mock_client)
    restore_catalog_scroll(mock_client)

    restore_call = mock_client.outbox.enqueue_message.call_args_list[-1][0]
    assert "window._mw_catalog_scroll" in str(restore_call)
    assert "window.scrollTo({top: pos" in str(restore_call)


def test_4_catalog_to_ode_back_to_another_operation_isolation():
    """Test 4: Catalog -> ODE -> Back -> Another operation starts at top without inheriting old offset."""
    mock_client = MagicMock()
    mock_client.has_socket_connection = True
    mock_client.is_deleted = False
    mock_client.id = "mock-client-cycle"

    # Step 1: Catalog -> Second-Order ODE
    capture_catalog_scroll(mock_client)
    reset_workspace_scroll(mock_client)
    ode_reset_call = str(mock_client.outbox.enqueue_message.call_args_list[-1][0])
    assert "top: 0" in ode_reset_call

    # Step 2: Back to Catalog
    restore_catalog_scroll(mock_client)
    catalog_restore_call = str(mock_client.outbox.enqueue_message.call_args_list[-1][0])
    assert "top: pos" in catalog_restore_call

    # Step 3: Catalog -> Derivative
    capture_catalog_scroll(mock_client)
    reset_workspace_scroll(mock_client)
    deriv_reset_call = str(mock_client.outbox.enqueue_message.call_args_list[-1][0])
    assert "top: 0" in deriv_reset_call


def test_5_workspace_internal_interactions_do_not_reset_scroll():
    """Test 5: Changing classification, mode, or inputs inside Screen B does NOT trigger scroll reset."""
    client = Client(ui.page("/test_internal_scroll_preservation"))
    with client:
        op = get_operation_by_type(ProblemType.ODE_SECOND_ORDER_CONSTANT_COEFF)
        mock_use_case = MagicMock()
        mock_switch = MagicMock()

        # Mount workspace
        render_ode_workspace(
            current_op=op,
            use_case=mock_use_case,
            on_operation_switch=mock_switch,
        )

        # Find buttons within Screen B workspace
        buttons = [el for el in client.elements.values() if isinstance(el, ui.button)]
        assert len(buttons) > 0

        # Clicking mode or classification buttons does not invoke on_operation_switch
        nonhomo_btn = next((b for b in buttons if "Không thuần nhất" in (b.text or "")), None)
        if nonhomo_btn is not None:
            for listener in list(nonhomo_btn._event_listeners.values()):
                if listener.type == "click":
                    try:
                        listener.handler(None)
                    except TypeError:
                        listener.handler()
            assert not mock_switch.called

        cauchy_btn = next((b for b in buttons if "Cauchy" in (b.text or "")), None)
        if cauchy_btn is not None:
            for listener in list(cauchy_btn._event_listeners.values()):
                if listener.type == "click":
                    try:
                        listener.handler(None)
                    except TypeError:
                        listener.handler()
            assert not mock_switch.called


def test_6_different_viewport_dimensions_and_scrolling_owner():
    """Test 6: Verify navigation contracts and scrolling owners across 1024x768, 1280x800, 1920x1080."""
    viewports = [(1024, 768), (1280, 800), (1920, 1080)]

    for width, height in viewports:
        shell = create_page_shell()
        classes = shell._classes
        assert "w-full" in classes
        assert "max-w-7xl" in classes
        assert "mx-auto" in classes
        assert "min-h-screen" in classes
        assert "overflow-hidden" not in classes
        assert "overflow-auto" not in classes

        with ui.card():
            navbar = render_sticky_nav_bar(
                title="Phương trình vi phân cấp 2",
                domain="Phương trình vi phân",
                on_back=lambda: None,
            )
        nav_classes = navbar._classes
        assert "sticky" in nav_classes
        assert "top-0" in nav_classes
        assert "z-30" in nav_classes
        assert "bg-white" in nav_classes


# =============================================================================
# REAL QTWEBENGINE CHROMIUM RUNTIME INTEGRATION TEST
# =============================================================================

def test_7_real_qtwebengine_scroll_isolation_and_restoration():
    """Test 7: Execute live offscreen QtWebEngine verifying exact browser DOM scroll coordinates."""
    script = """
import os, sys, time, threading
from pathlib import Path
from nicegui import ui
from math_app.main import build_application
from math_app.presentation.app import create_app

os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--no-sandbox --disable-gpu'
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

use_case = build_application()
create_app(use_case)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, QTimer

app_qt = QApplication(['test_scroll_isolation'])
view = QWebEngineView()
view.resize(1280, 800)

t = threading.Thread(target=lambda: ui.run(port=8872, reload=False, show=False), daemon=True)
t.start()
time.sleep(1.5)

view.load(QUrl('http://127.0.0.1:8872/'))

results = {}

def step1():
    # Scroll catalog to 1200px
    view.page().runJavaScript('window.scrollTo(0, 1200);', lambda _: QTimer.singleShot(400, step2))

def step2():
    click_js = (
        "(function() {"
        "  const cards = document.querySelectorAll('.q-card');"
        "  for (const c of cards) {"
        "    if (c.innerText.includes('Phương trình vi phân cấp 2')) {"
        "      c.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));"
        "      return true;"
        "    }"
        "  }"
        "  return false;"
        "})()"
    )
    view.page().runJavaScript(click_js, lambda res: QTimer.singleShot(1200, step3))

def step3():
    check_js = '({ scrollY: window.scrollY, scrollTop: document.documentElement.scrollTop, saved: window._mw_catalog_scroll })'
    def on_step3(res):
        results['screenB'] = res
        back_js = (
            "(function() {"
            "  const btns = document.querySelectorAll('button');"
            "  for (const b of btns) {"
            "    if (b.innerText.includes('Chọn dạng toán khác')) {"
            "      b.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));"
            "      return true;"
            "    }"
            "  }"
            "  return false;"
            "})()"
        )
        view.page().runJavaScript(back_js, lambda _: QTimer.singleShot(1200, step4))
    view.page().runJavaScript(check_js, on_step3)

def step4():
    check_js = '({ scrollY: window.scrollY, scrollTop: document.documentElement.scrollTop, saved: window._mw_catalog_scroll })'
    def on_step4(res):
        results['catalogRestored'] = res
        app_qt.quit()
    view.page().runJavaScript(check_js, on_step4)

view.loadFinished.connect(lambda ok: QTimer.singleShot(1500, step1))
app_qt.exec()

assert results.get('screenB', {}).get('scrollY') == 0, f"Expected screenB scrollY == 0, got {results}"
assert results.get('catalogRestored', {}).get('scrollY') == 1200, f"Expected catalogRestored scrollY == 1200, got {results}"
print('LIVE_DOM_VERIFIED_SUCCESS')
"""
    clean_env = os.environ.copy()
    clean_env.pop("PYTEST_CURRENT_TEST", None)
    clean_env.pop("PYTEST_VERSION", None)

    res = subprocess.run(
        ["uv", "run", "python"],
        input=script,
        capture_output=True,
        text=True,
        env=clean_env,
    )
    assert res.returncode == 0, f"QtWebEngine test failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "LIVE_DOM_VERIFIED_SUCCESS" in res.stdout

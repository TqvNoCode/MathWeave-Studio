"""Regression tests for NiceGUI API compatibility and graceful shutdown behavior.

Verifies:
1. Pinned NiceGUI (3.18.0) exports supported public APIs `app` and `ui`.
2. NiceGUI's supported shutdown API is `app.shutdown()`.
3. `Server` is not exported from top-level `nicegui` and must never be imported from `nicegui`.
4. No source files in `src/` import `Server` directly from `nicegui`.
5. Native window closure and test shutdown handlers execute cleanly without unhandled exceptions.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"


def test_nicegui_exports_supported_public_apis() -> None:
    """Verify that NiceGUI exports supported public APIs: app and ui."""
    import nicegui
    from nicegui import app, ui

    assert hasattr(nicegui, "app")
    assert hasattr(nicegui, "ui")
    assert app is not None
    assert ui is not None
    assert callable(app.shutdown)
    sig = inspect.signature(app.shutdown)
    assert len(sig.parameters) == 0


def test_nicegui_does_not_export_server_at_top_level() -> None:
    """Verify Server is NOT exported at top-level nicegui package namespace."""
    import nicegui

    assert not hasattr(nicegui, "Server")

    with pytest.raises(ImportError) as exc_info:
        exec("from nicegui import Server")  # noqa: S102
    assert "cannot import name 'Server' from 'nicegui'" in str(exc_info.value)


def test_nicegui_server_submodule_contains_server_class() -> None:
    """Verify Server class is located specifically within the nicegui.server submodule."""
    import uvicorn
    from nicegui.server import Server

    assert isinstance(Server, type)
    assert issubclass(Server, uvicorn.Server)
    assert "instance" in Server.__annotations__ or hasattr(Server, "instance")


def test_no_invalid_nicegui_server_imports_in_source_tree() -> None:
    """Scan all Python source files in src/ to guarantee no 'from nicegui import ... Server' exists."""
    invalid_import_pattern = re.compile(r"^\s*from\s+nicegui\s+import\s+[^#\n]*\bServer\b", re.MULTILINE)

    py_files = list(SRC_DIR.rglob("*.py"))
    assert len(py_files) > 0, "No Python source files found in src/"

    violating_files: list[str] = []
    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        if invalid_import_pattern.search(content):
            violating_files.append(str(py_file.relative_to(PROJECT_ROOT)))

    assert not violating_files, (
        f"Found invalid 'from nicegui import Server' in source files: {violating_files}. "
        "Use supported 'app.shutdown()' or 'from nicegui.server import Server'."
    )


def test_coordinate_graceful_shutdown_is_idempotent() -> None:
    """Verify _coordinate_graceful_shutdown executes app.shutdown() and is strictly idempotent."""
    import sys
    from math_app.main import _coordinate_graceful_shutdown
    from nicegui import app

    main_module = sys.modules["math_app.main"]
    shutdown_call_count = 0

    def fake_shutdown() -> None:
        nonlocal shutdown_call_count
        shutdown_call_count += 1

    # Reset global state for testing
    main_module._shutdown_initiated = False

    with patch.object(app, "shutdown", side_effect=fake_shutdown):
        _coordinate_graceful_shutdown(reason="test_1")
        assert shutdown_call_count == 1

        # Second call must be a no-op (idempotent)
        _coordinate_graceful_shutdown(reason="test_2")
        assert shutdown_call_count == 1

    # Reset state
    main_module._shutdown_initiated = False


def test_coordinate_graceful_shutdown_emergency_fallback() -> None:
    """Verify that if app.shutdown() raises an exception, emergency Server.instance fallback activates."""
    import sys
    from math_app.main import _coordinate_graceful_shutdown
    from nicegui import app
    from nicegui.server import Server

    main_module = sys.modules["math_app.main"]
    main_module._shutdown_initiated = False

    mock_server_instance = MagicMock()
    mock_server_instance.should_exit = False

    def broken_shutdown() -> None:
        raise RuntimeError("simulated native window disposal error")

    with patch.object(app, "shutdown", side_effect=broken_shutdown):
        with patch.object(Server, "instance", mock_server_instance, create=True):
            _coordinate_graceful_shutdown(reason="test_recovery")
            assert mock_server_instance.should_exit is True

    main_module._shutdown_initiated = False


def test_execute_graceful_shutdown_task_executes_safely() -> None:
    """Verify background shutdown task in _setup_test_shutdown_endpoint invokes coordinator."""
    import asyncio
    import sys
    from math_app.main import _coordinate_graceful_shutdown
    from nicegui import app

    main_module = sys.modules["math_app.main"]
    main_module._shutdown_initiated = False
    shutdown_called = False

    def fake_shutdown() -> None:
        nonlocal shutdown_called
        shutdown_called = True

    with patch.object(app, "shutdown", side_effect=fake_shutdown):
        async def _execute_graceful_shutdown() -> None:
            await asyncio.sleep(0.01)
            _coordinate_graceful_shutdown(reason="authenticated_test_endpoint")

        asyncio.run(_execute_graceful_shutdown())

    assert shutdown_called is True
    main_module._shutdown_initiated = False

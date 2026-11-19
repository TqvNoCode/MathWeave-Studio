"""Tests for cross-platform desktop startup-mode resolution and native backend configuration."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from math_app.presentation.startup import (
    HeadlessEnvironmentError,
    NativeBackendError,
    StartupMode,
    resolve_startup_mode,
    validate_and_prepare_native_backend,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_linux_with_x11_display_chooses_native_mode():
    """Verify Linux with DISPLAY set defaults to native desktop window mode."""
    mode = resolve_startup_mode(
        argv=["run.py"],
        platform="linux",
        environ={"DISPLAY": ":0.0"},
    )
    assert mode == StartupMode.NATIVE
    assert mode.is_native is True
    assert mode.is_browser is False


def test_linux_with_wayland_display_chooses_native_mode():
    """Verify Linux with WAYLAND_DISPLAY set defaults to native desktop window mode."""
    mode = resolve_startup_mode(
        argv=["run.py"],
        platform="linux",
        environ={"WAYLAND_DISPLAY": "wayland-1"},
    )
    assert mode == StartupMode.NATIVE
    assert mode.is_native is True
    assert mode.is_browser is False


def test_linux_headless_without_display_raises_actionable_error():
    """Verify Linux without graphical display fails with an actionable diagnostic."""
    with pytest.raises(HeadlessEnvironmentError) as exc_info:
        resolve_startup_mode(
            argv=["run.py"],
            platform="linux",
            environ={},
        )
    msg = str(exc_info.value)
    assert "DISPLAY" in msg
    assert "WAYLAND_DISPLAY" in msg
    assert "--browser" in msg


def test_windows_chooses_native_mode_by_default():
    """Verify Windows defaults to native desktop mode without requiring display env vars."""
    mode = resolve_startup_mode(
        argv=["run.py"],
        platform="win32",
        environ={},
    )
    assert mode == StartupMode.NATIVE
    assert mode.is_native is True
    assert mode.is_browser is False


@pytest.mark.parametrize("platform_name", ["linux", "win32", "darwin"])
def test_browser_flag_overrides_native_on_all_platforms(platform_name: str):
    """Verify --browser flag explicitly forces browser mode on all supported operating systems."""
    mode = resolve_startup_mode(
        argv=["run.py", "--browser"],
        platform=platform_name,
        environ={"DISPLAY": ":0.0"},
    )
    assert mode == StartupMode.BROWSER
    assert mode.is_browser is True
    assert mode.is_native is False


def test_browser_flag_works_in_headless_linux():
    """Verify --browser succeeds on Linux even when no graphical display server is present."""
    mode = resolve_startup_mode(
        argv=["run.py", "--browser"],
        platform="linux",
        environ={},
    )
    assert mode == StartupMode.BROWSER
    assert mode.is_browser is True


def test_browser_mode_does_not_import_or_initialize_qt():
    """Verify browser mode does not import PyQt6, qtpy, or pywebview platforms in an isolated subprocess."""
    code = (
        "import sys\n"
        "from math_app.presentation.startup import resolve_startup_mode, StartupMode\n"
        "mode = resolve_startup_mode(argv=['run.py', '--browser'])\n"
        "assert mode == StartupMode.BROWSER\n"
        "qt_modules = [m for m in sys.modules if 'PyQt' in m or 'webview.platforms' in m]\n"
        "assert not qt_modules, f'Unexpected backend modules imported: {qt_modules}'\n"
    )
    res = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, f"Subprocess failed with stderr:\n{res.stderr}"


def test_missing_linux_qt_bindings_raises_actionable_diagnostic():
    """Verify missing Qt bindings on Linux raise NativeBackendError with package instructions."""
    with patch.dict(sys.modules, {"PyQt6": None}):
        with pytest.raises(NativeBackendError) as exc_info:
            validate_and_prepare_native_backend(platform="linux")

    err_msg = str(exc_info.value)
    assert "PyQt6" in err_msg
    assert "QtWebEngine" in err_msg
    assert "pacman -S" in err_msg
    assert "apt install" in err_msg
    assert "--browser" in err_msg


def test_missing_windows_webview2_raises_actionable_diagnostic():
    """Verify missing WebView2 on Windows raises NativeBackendError with download link and guidance."""
    mock_winforms = MagicMock()
    mock_winforms._is_chromium.return_value = False

    with patch.dict(sys.modules, {"webview.platforms.winforms": mock_winforms}):
        with pytest.raises(NativeBackendError) as exc_info:
            validate_and_prepare_native_backend(platform="win32")

    err_msg = str(exc_info.value)
    assert "Microsoft Edge WebView2 Runtime" in err_msg
    assert "https://go.microsoft.com/fwlink/p/?LinkId=2124703" in err_msg
    assert "--browser" in err_msg


def test_missing_windows_winforms_backend_raises_diagnostic():
    """Verify import failure of winforms backend on Windows raises NativeBackendError."""
    with patch.dict(sys.modules, {"webview.platforms.winforms": None}):
        with pytest.raises(NativeBackendError) as exc_info:
            validate_and_prepare_native_backend(platform="win32")

    err_msg = str(exc_info.value)
    assert "pythonnet" in err_msg


def test_linux_native_backend_configures_qt_and_resizable():
    """Verify Linux backend preparation configures pywebview for Qt and sets resizable."""
    from nicegui import app

    validate_and_prepare_native_backend(platform="linux")
    assert app.native.start_args.get("gui") == "qt"
    assert app.native.window_args.get("resizable") is True


def test_startup_mode_resolution_is_pure_and_does_not_open_window():
    """Verify startup mode resolution can be thoroughly exercised without opening GUI windows."""
    mode1 = resolve_startup_mode(argv=["app"], platform="linux", environ={"DISPLAY": ":1"})
    mode2 = resolve_startup_mode(argv=["app", "--browser"], platform="linux", environ={"DISPLAY": ":1"})
    mode3 = resolve_startup_mode(argv=["app"], platform="win32", environ={})
    assert mode1 == StartupMode.NATIVE
    assert mode2 == StartupMode.BROWSER
    assert mode3 == StartupMode.NATIVE

"""Cross-platform desktop startup-mode resolution and native backend preparation."""

from __future__ import annotations

import enum
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path


class StartupMode(enum.Enum):
    """Application startup mode."""

    NATIVE = "native"
    BROWSER = "browser"

    @property
    def is_native(self) -> bool:
        """Return True if native desktop window mode is active."""
        return self == StartupMode.NATIVE

    @property
    def is_browser(self) -> bool:
        """Return True if browser mode is active."""
        return self == StartupMode.BROWSER


class HeadlessEnvironmentError(RuntimeError):
    """Raised when native desktop mode is requested without an available graphical display."""


class NativeBackendError(RuntimeError):
    """Raised when native window backend dependencies or system libraries fail to initialize."""


def resolve_startup_mode(
    argv: Sequence[str] | None = None,
    platform: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> StartupMode:
    """Resolve the intended startup mode based on CLI arguments, platform, and environment.

    Args:
        argv: Command-line arguments sequence (defaults to sys.argv).
        platform: Platform identifier string (defaults to sys.platform).
        environ: Environment variables mapping (defaults to os.environ).

    Returns:
        StartupMode: NATIVE or BROWSER.

    Raises:
        HeadlessEnvironmentError: If native desktop mode is selected on Linux without
            an active graphical session (neither DISPLAY nor WAYLAND_DISPLAY is set).
    """
    if argv is None:
        argv = sys.argv
    if platform is None:
        platform = sys.platform
    if environ is None:
        environ = os.environ

    # Explicit flag --browser forces browser mode on any platform
    if "--browser" in argv:
        return StartupMode.BROWSER

    # Linux desktop environments require an active X11 or Wayland display server
    if platform.startswith("linux"):
        has_display = bool(environ.get("DISPLAY") or environ.get("WAYLAND_DISPLAY"))
        if not has_display:
            raise HeadlessEnvironmentError(
                "Không tìm thấy phiên làm việc đồ họa (X11 hoặc Wayland) để chạy giao diện desktop trên Linux.\n"
                "Biến môi trường DISPLAY hoặc WAYLAND_DISPLAY chưa được thiết lập.\n"
                "Để chạy ứng dụng ở chế độ trình duyệt hoặc trên máy chủ không có giao diện, vui lòng sử dụng:\n"
                "    uv run run.py --browser\n"
                "--------------------------------------------------\n"
                "No graphical session (X11 or Wayland) detected on Linux.\n"
                "Neither DISPLAY nor WAYLAND_DISPLAY environment variable is set.\n"
                "MathWeave Studio requires a graphical display session to launch in native desktop mode.\n"
                "To run in browser mode without a display session, launch with:\n"
                "    uv run run.py --browser"
            )
        return StartupMode.NATIVE

    # Windows and other desktop platforms default to native mode
    return StartupMode.NATIVE


def validate_and_prepare_native_backend(
    platform: str | None = None,
    icon_path: str | Path | None = None,
) -> None:
    """Validate backend dependencies and configure NiceGUI native window properties.

    Must only be called when native mode is active. Never called in browser mode.

    Args:
        platform: Platform identifier string (defaults to sys.platform).
        icon_path: Optional path to window icon.

    Raises:
        NativeBackendError: If backend dependencies or runtime components are unavailable.
    """
    if platform is None:
        platform = sys.platform

    if platform.startswith("linux"):
        # On Linux, pywebview uses Qt (PyQt6) for native desktop mode
        try:
            import qtpy  # noqa: F401
            from PyQt6 import QtCore, QtWebEngineWidgets  # noqa: F401
        except ImportError as exc:
            raise NativeBackendError(
                "MathWeave Studio yêu cầu PyQt6 và QtWebEngine để khởi chạy cửa sổ desktop trên Linux.\n"
                f"Lỗi khi tải thư viện Qt: {exc}\n\n"
                "Cách khắc phục:\n"
                "1. Đảm bảo các gói phụ thuộc Python đã được đồng bộ đầy đủ:\n"
                "    uv sync\n"
                "   hoặc cài đặt pywebview với tùy chọn Qt:\n"
                '    pip install "pywebview[qt]>=6.2.1"\n\n'
                "2. Kiểm tra thư viện hệ thống cần thiết:\n"
                "   - Arch Linux: sudo pacman -S qt6-webengine qt6-webchannel\n"
                "   - Ubuntu/Debian: sudo apt install libgl1 libegl1 libxkbcommon0 libdbus-1-3 libxcb1 libxcb-cursor0\n\n"
                "3. Hoặc khởi chạy ứng dụng qua trình duyệt web bằng tham số:\n"
                "    uv run run.py --browser\n"
                "--------------------------------------------------\n"
                "MathWeave Studio requires PyQt6 and QtWebEngine for native desktop mode on Linux.\n"
                f"Failed to load Qt bindings: {exc}\n\n"
                "Resolution steps:\n"
                "1. Synchronize locked Python dependencies:\n"
                "    uv sync\n"
                "   or install pywebview with qt extra:\n"
                '    pip install "pywebview[qt]>=6.2.1"\n\n'
                "2. Ensure required system packages are installed:\n"
                "   - Arch Linux: sudo pacman -S qt6-webengine qt6-webchannel\n"
                "   - Ubuntu/Debian: sudo apt install libgl1 libegl1 libxkbcommon0 libdbus-1-3 libxcb1 libxcb-cursor0\n\n"
                "3. Alternatively, launch in browser mode:\n"
                "    uv run run.py --browser"
            ) from exc

        from nicegui import app

        app.native.start_args["gui"] = "qt"
        app.native.window_args["resizable"] = True
        if icon_path is not None and Path(icon_path).is_file():
            app.native.start_args["icon"] = str(icon_path)

    elif platform == "win32":
        # On Windows, pywebview uses WinForms + EdgeChromium (WebView2).
        try:
            from webview.platforms.winforms import _is_chromium
        except ImportError as exc:
            raise NativeBackendError(
                f"Không thể khởi tạo backend Windows pywebview: {exc}\n"
                "Vui lòng kiểm tra gói pythonnet đã được cài đặt chính xác.\n"
                "--------------------------------------------------\n"
                f"Failed to load Windows pywebview native backend: {exc}\n"
                "Please verify pythonnet is installed properly."
            ) from exc

        if not _is_chromium():
            msg = (
                "Microsoft Edge WebView2 Runtime chưa được cài đặt trên hệ thống Windows này.\n"
                "MathWeave Studio yêu cầu WebView2 Runtime để chạy ở chế độ cửa sổ ứng dụng desktop.\n\n"
                "Vui lòng tải và cài đặt Microsoft Edge WebView2 Runtime từ:\n"
                "https://go.microsoft.com/fwlink/p/?LinkId=2124703\n\n"
                "Hoặc khởi chạy ứng dụng từ dòng lệnh với tham số --browser để mở qua trình duyệt.\n"
                "--------------------------------------------------\n"
                "Microsoft Edge WebView2 Runtime is not installed on this system.\n"
                "MathWeave Studio requires WebView2 Runtime to run in native desktop mode.\n"
                "Please install Microsoft Edge WebView2 Runtime from the link above or launch with --browser."
            )
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(
                    0,
                    msg,
                    "MathWeave Studio — Cần WebView2 Runtime",
                    0x10,  # MB_ICONERROR
                )
            except Exception:
                pass
            raise NativeBackendError(msg)

        from nicegui import app

        app.native.window_args["resizable"] = True

    else:
        from nicegui import app

        app.native.window_args["resizable"] = True

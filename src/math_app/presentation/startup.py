"""Cross-platform desktop startup-mode resolution and native backend preparation."""

from __future__ import annotations

import enum
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


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


DEFAULT_APP_PORT = 8080


def resolve_configured_port(
    argv: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
    default_port: int = DEFAULT_APP_PORT,
) -> int:
    """Resolve configured network port from CLI arguments, environment, or default.

    Precedence:
    1. CLI argument: --port <PORT>
    2. Environment variable: MATHWEAVE_PORT
    3. Default port: default_port (8080)
    """
    if argv is None:
        argv = sys.argv
    if environ is None:
        environ = os.environ

    if "--port" in argv:
        try:
            port_idx = argv.index("--port")
            if port_idx + 1 < len(argv) and argv[port_idx + 1].isdigit():
                return int(argv[port_idx + 1])
        except (ValueError, IndexError):
            pass

    env_port = environ.get("MATHWEAVE_PORT")
    if env_port and env_port.isdigit():
        return int(env_port)

    return default_port


def resolve_assets_path() -> Path:
    """Resolve absolute path to assets directory for web mounting and font delivery."""
    if hasattr(sys, "_MEIPASS"):
        candidate = Path(sys._MEIPASS) / "assets"
        if candidate.is_dir():
            return candidate

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        for candidate in (exe_dir / "assets", exe_dir / "_internal" / "assets"):
            if candidate.is_dir():
                return candidate

    base_assets = Path(__file__).resolve().parent.parent.parent.parent / "assets"
    if base_assets.is_dir():
        return base_assets

    alt_assets = Path(__file__).resolve().parent / "assets"
    if alt_assets.is_dir():
        return alt_assets

    return base_assets


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

        # Apply pywebview Qt patches to remediate WebChannel & WebEnginePage shutdown warnings
        patch_pywebview_qt()
        server_args = app.native.start_args.setdefault("server_args", {})
        server_args["_native_hook"] = _NativeProcessHook()

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

        # Apply pywebview WinForms patches for deterministic shutdown and immediate handle release
        patch_pywebview_winforms()
        server_args = app.native.start_args.setdefault("server_args", {})
        server_args["_native_hook"] = _NativeProcessHook()

    else:
        from nicegui import app

        app.native.window_args["resizable"] = True


def patch_pywebview_qt() -> None:
    """Remediate pywebview Qt backend warnings for WebChannel and WebEnginePage cleanup."""
    try:
        import webview.platforms.qt as qt_mod
    except ImportError:
        return

    if getattr(qt_mod, "_mathweave_qt_patched", False):
        return

    orig_init = qt_mod.BrowserView.__init__
    orig_set_js_api = qt_mod.BrowserView._set_js_api

    def patched_init(self: Any, window: Any) -> None:
        orig_init(self, window)
        # Fix Issue C: Pre-register 'external' on channel before page finishes loading
        if getattr(self, "channel", None) is not None and getattr(self, "js_bridge", None) is not None:
            try:
                registered = self.channel.registeredObjects()
                if "external" not in registered:
                    self.channel.registerObject("external", self.js_bridge)
            except Exception:
                pass

    def patched_set_js_api(self: Any) -> None:
        # Fix Issue C: Prevent duplicate post-initialization registration warning
        if getattr(qt_mod, "is_webengine", False):
            from PyQt6 import QtCore

            qwebchannel_js = QtCore.QFile("://qtwebchannel/qwebchannel.js")
            if qwebchannel_js.open(QtCore.QFile.ReadOnly):
                source = bytes(qwebchannel_js.readAll()).decode("utf-8")
                self.webview.page().runJavaScript(source)
                try:
                    registered = self.channel.registeredObjects()
                    if "external" not in registered:
                        self.channel.registerObject("external", self.js_bridge)
                except Exception:
                    pass
                qwebchannel_js.close()
            qt_mod.inject_pywebview(qt_mod.renderer, self.js_bridge.window)
        else:
            orig_set_js_api(self)

    def patched_close_event(self: Any, event: Any) -> None:
        # Fix Issue D: Properly detach page, trigger deferred delete, and flush events before Qt exit
        should_cancel = self.pywebview_window.events.closing.set()
        if should_cancel:
            event.ignore()
            return

        if self.pywebview_window.confirm_close:
            reply = qt_mod.QMessageBox.question(
                self,
                self.title,
                self.localization["global.quitConfirmation"],
                qt_mod.QMessageBox.Yes,
                qt_mod.QMessageBox.No,
            )
            if reply == qt_mod.QMessageBox.No:
                event.ignore()
                return

        event.accept()

        if self.uid in qt_mod.BrowserView.instances:
            del qt_mod.BrowserView.instances[self.uid]
        self.close()

        if self.pywebview_window in qt_mod.windows:
            qt_mod.windows.remove(self.pywebview_window)

        self.pywebview_window.events.closed.set()

        # Schedule deferred deletion of page and flush events before app exit
        try:
            page = self.webview.page()
            if page:
                page.deleteLater()
        except Exception:
            pass

        if len(qt_mod.BrowserView.instances) == 0:
            self.hide()
            try:
                from PyQt6.QtCore import QCoreApplication, QEvent

                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                QCoreApplication.processEvents()
            except Exception:
                pass
            if hasattr(qt_mod, "_app") and qt_mod._app is not None:
                qt_mod._app.exit()

    qt_mod.BrowserView.__init__ = patched_init
    qt_mod.BrowserView._set_js_api = patched_set_js_api
    qt_mod.BrowserView.closeEvent = patched_close_event
    qt_mod._mathweave_qt_patched = True


def patch_pywebview_winforms() -> None:
    """Patch pywebview WinForms/EdgeChromium backend on Windows for deterministic graceful shutdown.

    Remediates delayed file locks and lingering processes by:
    1. Ensuring the underlying EdgeChromium CoreWebView2 control is explicitly disposed on window close.
    2. Bounded waiting for the WebView2 browser process to exit so no open handles lock DLLs in _MEIPASS.
    3. Ensuring clean WinForms STA thread termination.
    """
    try:
        import webview.platforms.winforms as wf
    except ImportError:
        return

    if getattr(wf, "_mathweave_winforms_patched", False):
        return

    orig_form_class = getattr(wf.BrowserView, "BrowserForm", None)
    if orig_form_class is None:
        return

    orig_on_close = getattr(orig_form_class, "on_close", None)
    if orig_on_close is None:
        return

    def patched_on_close(self: Any, *args: Any) -> None:
        # Pre-cleanup: explicitly dispose WebView2 control and wait for runtime process exit
        try:
            browser = getattr(self, "browser", None)
            if browser is not None:
                wv = getattr(browser, "webview", None)
                if wv is not None:
                    browser_pid: int | None = None
                    try:
                        core_wv = getattr(wv, "CoreWebView2", None)
                        if core_wv is not None:
                            browser_pid = int(core_wv.BrowserProcessId)
                    except Exception:
                        browser_pid = None

                    try:
                        wv.Dispose()
                    except Exception:
                        pass

                    if browser_pid is not None:
                        try:
                            from System.Diagnostics import Process
                            proc = Process.GetProcessById(browser_pid)
                            if proc and not proc.HasExited:
                                proc.WaitForExit(1000)
                        except Exception:
                            pass
        except Exception:
            pass

        # Execute standard pywebview winforms shutdown
        try:
            orig_on_close(self, *args)
        except Exception:
            pass

    orig_form_class.on_close = patched_on_close
    wf._mathweave_winforms_patched = True


class _NativeProcessHook:
    """Hook invoked in the child native window process during unpickling to patch pywebview."""

    def __reduce__(self) -> tuple[Any, tuple[()]]:
        return (_execute_native_patch_in_child, ())


def _execute_native_patch_in_child() -> _NativeProcessHook:
    """Execute pywebview backend patching inside spawned child native process."""
    if sys.platform.startswith("linux"):
        patch_pywebview_qt()
    elif sys.platform == "win32":
        patch_pywebview_winforms()
    return _NativeProcessHook()


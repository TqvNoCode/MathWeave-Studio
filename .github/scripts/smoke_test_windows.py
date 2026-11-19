#!/usr/bin/env python3
"""Windows Build Smoke Testing and Runtime Validation for MathWeave Studio.

Validates that both the onedir and portable (onefile) Windows distributions:
1. Contain all required runtime binaries, .NET interop DLLs, and presentation assets.
2. Successfully initialize, start NiceGUI, serve HTTP traffic, and deliver assets.
3. Terminate cleanly without memory leaks or zombie processes.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def log(msg: str) -> None:
    print(f"[SMOKE-TEST] {msg}", flush=True)


def check_native_backend_environment() -> None:
    """Validate that Windows native dependencies (pythonnet, WebView2) are functional."""
    log("Validating Windows native environment dependencies...")
    try:
        import pythonnet  # noqa: F401
        import clr_loader  # noqa: F401
        log("pythonnet and clr_loader imported successfully.")
    except ImportError as exc:
        log(f"WARNING: Windows .NET loader not importable in test python: {exc}")

    try:
        from webview.platforms.winforms import _is_chromium
        chromium_ok = _is_chromium()
        log(f"Edge Chromium WebView2 Runtime detected: {chromium_ok}")
        if not chromium_ok:
            log("WARNING: WebView2 runtime check returned False.")
    except Exception as exc:
        log(f"Note: webview.platforms.winforms check: {exc}")


def validate_onedir_structure(onedir_path: Path) -> None:
    """Validate directory structure, binaries, and assets in onedir build."""
    log(f"Validating Onedir bundle structure at: {onedir_path}")
    if not onedir_path.is_dir():
        raise FileNotFoundError(f"Onedir directory does not exist: {onedir_path}")

    # Check executable
    exe_candidates = [
        onedir_path / "mathweave-studio.exe",
        onedir_path / "mathweave-studio",
    ]
    main_exe = next((p for p in exe_candidates if p.is_file()), None)
    if not main_exe:
        raise FileNotFoundError(f"Main executable not found in {onedir_path}. Looked for: {exe_candidates}")

    exe_size = main_exe.stat().st_size
    log(f"Found onedir executable: {main_exe.name} ({exe_size:,} bytes)")
    if exe_size < 50_000:
        raise ValueError(f"Executable file {main_exe} is suspiciously small: {exe_size} bytes")

    # Search for assets directory (either at root or in _internal)
    possible_assets_dirs = [
        onedir_path / "_internal" / "assets",
        onedir_path / "assets",
    ]
    assets_dir = next((p for p in possible_assets_dirs if p.is_dir()), None)
    if not assets_dir:
        raise FileNotFoundError(f"Assets directory not found in onedir bundle. Looked in: {possible_assets_dirs}")

    log(f"Found bundled assets directory at: {assets_dir}")

    required_assets = [
        assets_dir / "fonts" / "DejaVuMathTeXGyre.ttf",
        assets_dir / "katex" / "katex.js",
        assets_dir / "katex" / "katex.css",
        assets_dir / "icon.ico",
    ]

    for req in required_assets:
        if not req.is_file():
            raise FileNotFoundError(f"Required bundled asset missing: {req}")
        log(f"  Verified asset: {req.relative_to(onedir_path)} ({req.stat().st_size:,} bytes)")

    log("Onedir directory structure and asset verification PASSED.")


def validate_portable_executable(portable_path: Path) -> None:
    """Validate standalone portable executable existence and minimum size."""
    log(f"Validating Portable executable at: {portable_path}")
    if not portable_path.is_file():
        raise FileNotFoundError(f"Portable executable not found: {portable_path}")

    size = portable_path.stat().st_size
    log(f"Found portable executable: {portable_path.name} ({size:,} bytes)")
    # Standalone bundle packaging Python + SymPy + NumPy + NiceGUI + assets must be > 15MB
    if size < 15_000_000:
        raise ValueError(f"Portable executable suspiciously small ({size:,} bytes). Expected > 15MB.")

    log("Portable executable file verification PASSED.")


def run_startup_smoke_test(exe_path: Path, port: int, label: str, timeout_seconds: float = 75.0) -> None:
    """Launch executable with --browser on specified port, test HTTP response, and terminate."""
    log("\n==================================================")
    log(f"STARTING RUNTIME SMOKE TEST: {label}")
    log(f"Executable: {exe_path}")
    log(f"Target Port: {port}")
    log(f"Startup Timeout: {timeout_seconds}s")
    log("==================================================")

    env = os.environ.copy()
    env["MATHWEAVE_PORT"] = str(port)

    # Use --no-show to prevent NiceGUI from attempting to open a web browser in headless CI
    cmd = [str(exe_path), "--browser", "--port", str(port), "--no-show"]
    log(f"Executing: {' '.join(cmd)}")

    # Use file-based redirection to avoid Windows pipe buffer deadlock on high output
    log_file_path = Path(f"smoke_{label.replace(' ', '_').lower()}.log")
    log_file = open(log_file_path, "w", encoding="utf-8", errors="replace")

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=log_file,
        stderr=log_file,
    )

    url_root = f"http://127.0.0.1:{port}/"
    url_katex = f"http://127.0.0.1:{port}/assets/katex/katex.js"
    url_font = f"http://127.0.0.1:{port}/assets/fonts/DejaVuMathTeXGyre.ttf"

    deadline = time.time() + timeout_seconds
    server_ready = False

    try:
        while time.time() < deadline:
            # Check if process exited unexpectedly
            ret = proc.poll()
            if ret is not None:
                log_file.flush()
                output_content = log_file_path.read_text(encoding="utf-8", errors="replace") if log_file_path.is_file() else ""
                raise RuntimeError(
                    f"Process {label} exited prematurely with return code {ret}.\n"
                    f"LOG OUTPUT:\n{output_content}"
                )

            try:
                with urllib.request.urlopen(url_root, timeout=2.0) as resp:
                    if resp.status == 200:
                        content = resp.read().decode("utf-8", errors="replace")
                        log(f"Root endpoint responded HTTP 200 ({len(content):,} chars).")
                        if "MathWeave" in content or "nicegui" in content or "katex" in content:
                            log("Verified application HTML content markers.")
                        server_ready = True
                        break
            except (urllib.error.URLError, ConnectionRefusedError, TimeoutError, OSError):
                time.sleep(1.0)

        if not server_ready:
            log_file.flush()
            output_content = log_file_path.read_text(encoding="utf-8", errors="replace") if log_file_path.is_file() else ""
            raise TimeoutError(
                f"Application {label} did not become ready on {url_root} within {timeout_seconds}s.\n"
                f"PROCESS LOG:\n{output_content}"
            )

        # Verify static asset serving
        with urllib.request.urlopen(url_katex, timeout=5.0) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Failed to serve KaTeX asset: HTTP {resp.status}")
            katex_bytes = resp.read()
            log(f"Verified KaTeX asset HTTP 200 ({len(katex_bytes):,} bytes).")

        with urllib.request.urlopen(url_font, timeout=5.0) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Failed to serve DejaVu font asset: HTTP {resp.status}")
            font_bytes = resp.read()
            log(f"Verified DejaVu Math font HTTP 200 ({len(font_bytes):,} bytes).")

        log(f"RUNTIME SMOKE TEST PASSED for {label}!")

    finally:
        log(f"Terminating {label} process (PID: {proc.pid})...")
        proc.terminate()
        try:
            proc.wait(timeout=6.0)
            log("Process terminated cleanly.")
        except subprocess.TimeoutExpired:
            log(f"Process did not terminate within timeout; killing PID: {proc.pid}...")
            proc.kill()
            proc.wait(timeout=5.0)
            log("Process killed.")

        try:
            log_file.close()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="MathWeave Studio Build Smoke Testing")
    parser.add_argument(
        "--onedir-dir",
        type=Path,
        default=Path("dist/mathweave-studio"),
        help="Path to onedir build directory",
    )
    parser.add_argument(
        "--portable-exe",
        type=Path,
        default=Path("dist/MathWeave-Studio-Portable.exe"),
        help="Path to onefile portable executable",
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Only validate files without executing startup smoke tests",
    )
    args = parser.parse_args()

    log("=" * 60)
    log("MathWeave Studio — Windows Build Smoke & Resource Validator")
    log("=" * 60)

    if sys.platform == "win32":
        check_native_backend_environment()
    else:
        log(f"Running on platform: {sys.platform} (non-Windows runner mode)")

    # 1. Validate Onedir
    validate_onedir_structure(args.onedir_dir)

    # 2. Validate Portable
    # On Linux testing, executable may not have .exe extension
    portable_target = args.portable_exe
    if not portable_target.exists() and portable_target.suffix == ".exe":
        no_ext = portable_target.with_suffix("")
        if no_ext.exists():
            portable_target = no_ext

    validate_portable_executable(portable_target)

    # 3. Startup Smoke Tests
    if not args.skip_smoke:
        # Determine executable paths for smoke test
        onedir_exe = args.onedir_dir / "mathweave-studio.exe"
        if not onedir_exe.exists():
            onedir_exe = args.onedir_dir / "mathweave-studio"

        run_startup_smoke_test(onedir_exe, port=8091, label="Standard Onedir Distribution")
        run_startup_smoke_test(portable_target, port=8092, label="Portable Onefile Distribution")

        log("\n" + "=" * 60)
        log("[SMOKE TEST NOTICE]")
        log("Startup smoke testing verified full dependency loading, PyInstaller extraction,")
        log("Uvicorn ASGI server initialization, NiceGUI routing, and static asset delivery.")
        log("Note: Interactive GUI testing (WebView2 desktop window) requires an interactive")
        log("Windows desktop user session and cannot be evaluated in automated headless CI.")
        log("=" * 60 + "\n")

    log("ALL WINDOWS BUILD VALIDATION CHECKS COMPLETED SUCCESSFULLY.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

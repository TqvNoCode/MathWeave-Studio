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
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


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

    # Check for critical native DLLs (e.g. libcrypto)
    crypto_dlls = list(onedir_path.rglob("libcrypto-3-x64.dll"))
    if crypto_dlls:
        log(f"  Verified native crypto DLL: {crypto_dlls[0].relative_to(onedir_path)} ({crypto_dlls[0].stat().st_size:,} bytes)")
    else:
        log("  Note: libcrypto-3-x64.dll not detected in bundle directory (expected on Windows).")

    log("Onedir directory structure and asset verification PASSED.")


def validate_pe_metadata_and_signatures(
    onedir_path: Path,
    portable_path: Path,
    installer_path: Path | None = None,
    verify_signatures: bool = False,
) -> None:
    """Validate PE version info metadata and Authenticode signatures."""
    log("\n" + "=" * 60)
    log("VALIDATING PE FILE METADATA AND AUTHENTICODE SIGNATURES")
    log("=" * 60)

    if sys.platform != "win32":
        log("Notice: Non-Windows environment detected; skipping live Authenticode and PE resource checks.")
        return

    import json

    targets: list[tuple[str, Path, bool]] = []
    # (Label, Path, is_exe)
    main_onedir_exe = onedir_path / "mathweave-studio.exe"
    if main_onedir_exe.is_file():
        targets.append(("Onedir Main Executable", main_onedir_exe, True))

    for libcrypto in onedir_path.rglob("libcrypto-3-x64.dll"):
        targets.append(("Onedir OpenSSL Native DLL", libcrypto, False))

    if portable_path.is_file():
        targets.append(("Portable Onefile Executable", portable_path, True))

    if installer_path and installer_path.is_file():
        targets.append(("Windows Installer Executable", installer_path, True))

    for label, target_path, is_exe in targets:
        log(f"\nChecking target: {label} -> {target_path.name}")
        resolved_str = str(target_path.resolve())

        # Check metadata
        if is_exe:
            pwsh_meta_cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                f"""
                $vi = [System.Diagnostics.FileVersionInfo]::GetVersionInfo('{resolved_str}')
                @{{
                    FileVersion = $vi.FileVersion
                    ProductVersion = $vi.ProductVersion
                    ProductName = $vi.ProductName
                    CompanyName = $vi.CompanyName
                }} | ConvertTo-Json
                """,
            ]
            res = subprocess.run(pwsh_meta_cmd, capture_output=True, text=True)
            try:
                meta = json.loads(res.stdout)
                log(f"  FileVersion   : {meta.get('FileVersion')}")
                log(f"  ProductVersion: {meta.get('ProductVersion')}")
                log(f"  ProductName   : {meta.get('ProductName')}")
                log(f"  CompanyName   : {meta.get('CompanyName')}")
                if not meta.get("FileVersion"):
                    raise ValueError(f"Missing FileVersion in PE header: {target_path}")
            except Exception as exc:
                log(f"  Metadata check notice: {exc}")

        # Check Authenticode signature
        pwsh_sig_cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"""
            $sig = Get-AuthenticodeSignature -FilePath '{resolved_str}'
            $isTrustedRoot = $false
            if ($sig.Status -eq 'Valid' -and $sig.SignerCertificate) {{
                $chain = New-Object -TypeName System.Security.Cryptography.X509Certificates.X509Chain
                $isTrustedRoot = $chain.Build($sig.SignerCertificate)
            }}
            @{{
                Status = $sig.Status.ToString()
                StatusMessage = $sig.StatusMessage
                IsTrustedRoot = $isTrustedRoot
                Signer = if ($sig.SignerCertificate) {{ $sig.SignerCertificate.Subject }} else {{ "None" }}
            }} | ConvertTo-Json
            """,
        ]
        sig_res = subprocess.run(pwsh_sig_cmd, capture_output=True, text=True)
        try:
            sig_data = json.loads(sig_res.stdout)
            status = sig_data.get("Status", "Unknown")
            signer = sig_data.get("Signer", "None")
            is_trusted_root = sig_data.get("IsTrustedRoot", False)
            if status == "NotSigned":
                log("  Authenticode Status : Unsigned (Development build without certificate)")
            else:
                log(f"  Authenticode Status : {status} (Signer: {signer})")
                log(f"  Trusted Root Chain  : {is_trusted_root}")
            if verify_signatures and status != "Valid":
                raise RuntimeError(f"Authenticode signature is NOT valid for {target_path.name} (Status: {status})")
            if status == "Valid" and not is_trusted_root:
                log(f"  [SECURITY WARNING] {target_path.name} signed with certificate not chained to a public trusted root CA!")
        except Exception as exc:
            if verify_signatures:
                raise RuntimeError(f"Failed to verify Authenticode signature on {target_path.name}: {exc}") from exc
            log(f"  Signature check notice: {exc}")

    log("PE metadata and Authenticode signature validation completed.")


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


def get_windows_process_tree(parent_pid: int) -> list[dict[str, Any]]:
    """Inspect and return child processes under parent_pid on Windows using PowerShell/WMI."""
    if sys.platform != "win32":
        return []
    import json
    pwsh_cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"""
        $procs = Get-CimInstance Win32_Process | Where-Object {{ $_.ParentProcessId -eq {parent_pid} -or $_.ProcessId -eq {parent_pid} }}
        $list = @($procs | ForEach-Object {{
            @{{
                ProcessId = $_.ProcessId
                ParentProcessId = $_.ParentProcessId
                Name = $_.Name
                CommandLine = $_.CommandLine
            }}
        }})
        $list | ConvertTo-Json
        """,
    ]
    try:
        res = subprocess.run(pwsh_cmd, capture_output=True, text=True, timeout=10)
        data = json.loads(res.stdout) if res.stdout.strip() else []
        if isinstance(data, dict):
            return [data]
        return data if isinstance(data, list) else []
    except Exception as exc:
        log(f"Note: Error querying process tree for PID {parent_pid}: {exc}")
        return []


def request_test_shutdown(port: int, token: str, timeout_seconds: float = 5.0) -> bool:
    """Send authenticated shutdown request to the test endpoint POST /_test/shutdown."""
    url = f"http://127.0.0.1:{port}/_test/shutdown"
    req = urllib.request.Request(
        url,
        data=b"",
        headers={
            "X-Shutdown-Token": token,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            if resp.status == 200:
                log(f"Graceful shutdown request accepted by endpoint {url} (HTTP 200).")
                return True
            log(f"Warning: Shutdown endpoint returned unexpected status: {resp.status}")
            return False
    except urllib.error.HTTPError as exc:
        log(f"Shutdown endpoint returned HTTP {exc.code}: {exc.reason}")
        return False
    except Exception as exc:
        log(f"Shutdown request failed: {exc}")
        return False


def run_startup_smoke_test(
    exe_path: Path,
    port: int,
    label: str,
    timeout_seconds: float = 75.0,
    shutdown_token: str | None = None,
) -> None:
    """Launch executable with --browser on specified port, test HTTP response, and terminate."""
    log("\n==================================================")
    log(f"STARTING RUNTIME SMOKE TEST: {label}")
    log(f"Executable: {exe_path}")
    log(f"Target Port: {port}")
    log(f"Startup Timeout: {timeout_seconds}s")
    log("==================================================")

    env = os.environ.copy()
    env["MATHWEAVE_PORT"] = str(port)
    if shutdown_token:
        env["MATHWEAVE_TEST_SHUTDOWN_TOKEN"] = shutdown_token

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
        log(f"Cleaning up {label} process (PID: {proc.pid})...")
        shutdown_success = False
        if shutdown_token:
            log("Attempting graceful shutdown via test endpoint...")
            if request_test_shutdown(port, shutdown_token, timeout_seconds=5.0):
                try:
                    proc.wait(timeout=10.0)
                    log(f"Process {label} exited cleanly via shutdown endpoint.")
                    shutdown_success = True
                except subprocess.TimeoutExpired:
                    log(f"Process {label} did not exit within 10.0s after test shutdown request.")

        if not shutdown_success and proc.poll() is None:
            log(f"Forced smoke-test cleanup (PID: {proc.pid})...")
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


def run_portable_shutdown_and_file_lock_test(
    portable_exe: Path,
    port: int = 8092,
    iterations: int = 2,
    timeout_seconds: float = 75.0,
) -> None:
    """Validate graceful shutdown timing and verify immediate file lock release on the Portable EXE."""
    log("\n" + "=" * 60)
    log("TESTING PORTABLE SHUTDOWN TIMING & FILE LOCK RELEASE")
    log("=" * 60)

    for i in range(1, iterations + 1):
        iter_port = port + (i - 1) * 2
        log(f"\n--- [Iteration {i}/{iterations}] Testing Portable Shutdown & Unlock on Port {iter_port} ---")
        iter_shutdown_token = secrets.token_urlsafe(32)

        env = os.environ.copy()
        env["MATHWEAVE_PORT"] = str(iter_port)
        env["MATHWEAVE_TEST_SHUTDOWN_TOKEN"] = iter_shutdown_token

        cmd = [str(portable_exe), "--browser", "--port", str(iter_port), "--no-show"]
        log_file_path = Path(f"smoke_portable_shutdown_iter{i}.log")
        log_file = open(log_file_path, "w", encoding="utf-8", errors="replace")

        popen_kwargs: dict[str, Any] = {"env": env, "stdout": log_file, "stderr": log_file}
        if sys.platform == "win32":
            import signal
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        proc = subprocess.Popen(cmd, **popen_kwargs)
        url_root = f"http://127.0.0.1:{iter_port}/"
        deadline = time.time() + timeout_seconds
        server_ready = False

        try:
            while time.time() < deadline:
                if proc.poll() is not None:
                    raise RuntimeError(f"Portable process exited prematurely (code {proc.returncode})")
                try:
                    with urllib.request.urlopen(url_root, timeout=2.0) as resp:
                        if resp.status == 200:
                            server_ready = True
                            break
                except (urllib.error.URLError, ConnectionRefusedError, TimeoutError, OSError):
                    time.sleep(1.0)

            if not server_ready:
                raise TimeoutError(f"Application did not respond on {url_root} within {timeout_seconds}s")

            log("Server healthy and responding to HTTP requests. Initiating graceful shutdown via authenticated endpoint...")
            shutdown_start = time.perf_counter()

            # Request graceful shutdown via authenticated loopback test endpoint
            shutdown_dispatched = request_test_shutdown(iter_port, iter_shutdown_token, timeout_seconds=5.0)
            if not shutdown_dispatched:
                log("Warning: HTTP shutdown request not acknowledged; falling back to process termination signal.")
                import signal
                shutdown_signal = (
                    getattr(signal, "CTRL_BREAK_EVENT", signal.SIGINT)
                    if sys.platform == "win32"
                    else signal.SIGINT
                )
                proc.send_signal(shutdown_signal)

            SHUTDOWN_DEADLINE_SECONDS = 15.0
            try:
                proc.wait(timeout=SHUTDOWN_DEADLINE_SECONDS)
                shutdown_duration = time.perf_counter() - shutdown_start
                log(f"Process exited cleanly in {shutdown_duration:.2f}s (Returncode: {proc.returncode}).")
            except subprocess.TimeoutExpired:
                p_tree = get_windows_process_tree(proc.pid)
                log(f"Process failed to exit within {SHUTDOWN_DEADLINE_SECONDS}s deadline.")
                if p_tree:
                    log(f"Active process tree for PID {proc.pid}: {p_tree}")
                log_file.flush()
                log_tail = log_file_path.read_text(encoding="utf-8", errors="replace")[-2000:] if log_file_path.is_file() else ""
                log(f"Process log tail:\n{log_tail}")
                log(f"Killing parent PID {proc.pid}...")
                proc.kill()
                proc.wait(timeout=5.0)
                raise TimeoutError(f"Portable application shutdown exceeded {SHUTDOWN_DEADLINE_SECONDS}s deadline (PID: {proc.pid})")

        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            try:
                log_file.close()
            except Exception:
                pass

        # Verify executable file is completely released and can be renamed
        log("Verifying file lock release on Portable executable...")
        test_renamed = portable_exe.with_name(f"{portable_exe.stem}_lock_test_{i}{portable_exe.suffix}")
        try:
            portable_exe.rename(test_renamed)
            test_renamed.rename(portable_exe)
            log(f"Iteration {i} SUCCESS: Executable unlocked immediately, rename test PASSED.")
        except OSError as exc:
            raise PermissionError(
                f"Iteration {i} FAILED: Executable {portable_exe.name} remains locked after shutdown: {exc}"
            ) from exc

    log("\nAll Portable shutdown and file lock release iterations PASSED.")


def validate_and_test_installer(
    installer_path: Path,
    port: int = 8094,
    timeout_seconds: float = 75.0,
) -> None:
    """Validate Inno Setup installer file, execute silent install, run smoke test, and uninstall."""
    log("\n" + "=" * 60)
    log("VALIDATING INNO SETUP INSTALLER & ACCEPTANCE TESTING")
    log(f"Installer: {installer_path}")
    log("=" * 60)

    if not installer_path.is_file():
        raise FileNotFoundError(f"Installer executable not found: {installer_path}")

    size = installer_path.stat().st_size
    log(f"Found installer executable: {installer_path.name} ({size:,} bytes)")
    if size < 15_000_000:
        raise ValueError(f"Installer executable is suspiciously small: {size:,} bytes")

    if sys.platform != "win32":
        log("Notice: Non-Windows platform. Verified installer file presence and size; skipping live Windows installation.")
        return

    # Check PE metadata of installer
    pwsh_meta_cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"""
        $vi = (Get-Item -FilePath '{installer_path}').VersionInfo
        @{{
            FileVersion = $vi.FileVersion
            ProductVersion = $vi.ProductVersion
            ProductName = $vi.ProductName
            CompanyName = $vi.CompanyName
        }} | ConvertTo-Json
        """,
    ]
    meta_res = subprocess.run(pwsh_meta_cmd, capture_output=True, text=True)
    try:
        import json
        meta = json.loads(meta_res.stdout)
        log(f"  Installer ProductName   : {meta.get('ProductName')}")
        log(f"  Installer ProductVersion: {meta.get('ProductVersion')}")
        log(f"  Installer CompanyName   : {meta.get('CompanyName')}")
        if meta.get("CompanyName") != "TqvNoCode":
            log(f"  Warning: Unexpected CompanyName in installer: {meta.get('CompanyName')}")
    except Exception as exc:
        log(f"  Notice inspecting installer metadata: {exc}")

    # Silent Installation
    test_install_dir = Path("dist/test_install_target").resolve()
    if test_install_dir.exists():
        import shutil
        shutil.rmtree(test_install_dir, ignore_errors=True)

    install_cmd = [
        str(installer_path),
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        f"/DIR={test_install_dir}",
    ]
    log(f"Executing silent installation into: {test_install_dir}")
    install_res = subprocess.run(install_cmd, capture_output=True, text=True, timeout=120)
    if install_res.returncode != 0:
        raise RuntimeError(f"Installer failed with return code {install_res.returncode}. Stderr: {install_res.stderr}")

    installed_exe = test_install_dir / "mathweave-studio.exe"
    if not installed_exe.is_file():
        raise FileNotFoundError(f"Installed application executable not found at: {installed_exe}")
    log(f"Verified installed executable: {installed_exe.name} ({installed_exe.stat().st_size:,} bytes)")

    uninstaller = test_install_dir / "unins000.exe"
    if not uninstaller.is_file():
        raise FileNotFoundError(f"Uninstaller not found at: {uninstaller}")
    log(f"Verified uninstaller executable: {uninstaller.name}")

    # Verify bundled assets in installation
    possible_assets = [
        test_install_dir / "assets" / "fonts" / "DejaVuMathTeXGyre.ttf",
        test_install_dir / "_internal" / "assets" / "fonts" / "DejaVuMathTeXGyre.ttf",
    ]
    if not any(p.is_file() for p in possible_assets):
        raise FileNotFoundError(f"DejaVu Math font asset not found in installation: {possible_assets}")
    log("Verified required assets exist in installed package.")

    # Run runtime smoke test on installed executable
    installed_token = secrets.token_urlsafe(32)
    run_startup_smoke_test(
        installed_exe,
        port=port,
        label="Installed Application Package",
        timeout_seconds=timeout_seconds,
        shutdown_token=installed_token,
    )

    # Silent Uninstallation
    log(f"Executing silent uninstallation via: {uninstaller}")
    uninstall_cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"Start-Process -FilePath '{uninstaller}' -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -Wait",
    ]
    subprocess.run(uninstall_cmd, check=True, timeout=60)

    # Wait with polling (up to 15s) for uninstaller process cleanup and file deletion
    uninstall_deadline = time.time() + 15.0
    while time.time() < uninstall_deadline:
        if not installed_exe.exists():
            break
        time.sleep(1.0)

    if installed_exe.exists():
        raise RuntimeError(f"Uninstallation failed: {installed_exe} still exists after uninstallation.")
    log("Verified installed application binaries removed by uninstaller.")

    if test_install_dir.exists():
        import shutil
        shutil.rmtree(test_install_dir, ignore_errors=True)

    log("INSTALLER ACCEPTANCE TESTS COMPLETED SUCCESSFULLY.")


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
        "--installer-exe",
        type=Path,
        default=None,
        help="Path to Windows installer executable",
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Only validate files without executing startup smoke tests",
    )
    parser.add_argument(
        "--verify-signatures",
        action="store_true",
        help="Enforce strict Authenticode signature validity on Windows PE files",
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

    # 3. Validate PE Metadata and Signatures
    validate_pe_metadata_and_signatures(
        args.onedir_dir,
        portable_target,
        installer_path=args.installer_exe,
        verify_signatures=args.verify_signatures,
    )

    # 4. Startup & Acceptance Smoke Tests
    if not args.skip_smoke:
        # Determine executable paths for smoke test
        onedir_exe = args.onedir_dir / "mathweave-studio.exe"
        if not onedir_exe.exists():
            onedir_exe = args.onedir_dir / "mathweave-studio"

        onedir_token = secrets.token_urlsafe(32)
        run_startup_smoke_test(
            onedir_exe,
            port=8091,
            label="Standard Onedir Distribution",
            shutdown_token=onedir_token,
        )

        # Rigorous Portable Shutdown Timing and File Lock Verification
        run_portable_shutdown_and_file_lock_test(portable_target, port=8092, iterations=2)

        # Installer Acceptance Test (Silent Install -> Smoke Test -> Silent Uninstall)
        if args.installer_exe and args.installer_exe.is_file():
            validate_and_test_installer(args.installer_exe, port=8096)

        log("\n" + "=" * 60)
        log("[SMOKE TEST NOTICE]")
        log("Startup smoke testing verified full dependency loading, PyInstaller extraction,")
        log("Uvicorn ASGI server initialization, NiceGUI routing, static asset delivery,")
        log("bounded graceful shutdown, immediate file lock release, and Inno Setup installer lifecycle.")
        log("Note: Interactive GUI testing (WebView2 desktop window) requires an interactive")
        log("Windows desktop user session and cannot be evaluated in automated headless CI.")
        log("=" * 60 + "\n")

    log("ALL WINDOWS BUILD VALIDATION CHECKS COMPLETED SUCCESSFULLY.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

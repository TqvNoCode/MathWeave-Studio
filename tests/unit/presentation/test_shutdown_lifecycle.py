"""Tests for clean application lifecycle and bounded shutdown."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import IO, Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]

SHUTDOWN_SIGNAL = (
    getattr(signal, "CTRL_BREAK_EVENT", signal.SIGINT)
    if sys.platform == "win32"
    else signal.SIGINT
)

VALID_RETURNCODES = (
    (0, 1, 0xC000013A, -1073741510)
    if sys.platform == "win32"
    else (0, 1, -signal.SIGINT)
)


class _StdoutReader:
    """Non-blocking reader wrapper around temporary file capture."""

    def __init__(self, raw_file: IO[bytes]) -> None:
        self._raw_file = raw_file
        self._pos = 0

    def readline(self, timeout: float = 5.0) -> bytes:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._raw_file.seek(self._pos)
            line = self._raw_file.readline()
            if line and line.endswith(b"\n"):
                self._pos = self._raw_file.tell()
                return line
            time.sleep(0.05)
        self._raw_file.seek(self._pos)
        line = self._raw_file.readline()
        self._pos = self._raw_file.tell()
        return line

    def read(self) -> bytes:
        self._raw_file.seek(self._pos)
        data = self._raw_file.read()
        self._pos = self._raw_file.tell()
        return data


class ManagedPopen(subprocess.Popen[bytes]):
    """Subprocess manager that captures stdout and stderr via temporary files.

    On Windows, when descendant processes (e.g. browser or background workers)
    inherit anonymous pipe handles, Popen.communicate() deadlocks in ReadFile
    waiting for an EOF that never arrives even after the main application process
    exits cleanly. Writing to temporary files decouples process lifecycle from
    handle inheritance, ensuring bounded, reliable shutdown verification without
    pipe deadlock across all platforms.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._stdout_file: IO[bytes] = tempfile.TemporaryFile()
        self._stderr_file: IO[bytes] = tempfile.TemporaryFile()
        kwargs["stdout"] = self._stdout_file
        kwargs["stderr"] = self._stderr_file
        super().__init__(*args, **kwargs)
        self.stdout = _StdoutReader(self._stdout_file)  # type: ignore[assignment]
        self.stderr = _StdoutReader(self._stderr_file)  # type: ignore[assignment]

    def communicate(  # type: ignore[override]
        self,
        input: bytes | None = None,
        timeout: float | None = None,
    ) -> tuple[bytes, bytes]:
        try:
            self.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            self._stdout_file.seek(0)
            self._stderr_file.seek(0)
            exc.stdout = self._stdout_file.read()
            exc.stderr = self._stderr_file.read()
            raise

        self._stdout_file.seek(0)
        self._stderr_file.seek(0)
        stdout = self._stdout_file.read()
        stderr = self._stderr_file.read()
        return stdout, stderr

    def close_files(self) -> None:
        try:
            self._stdout_file.close()
        except Exception:
            pass
        try:
            self._stderr_file.close()
        except Exception:
            pass


def _start_app_process() -> ManagedPopen:
    env = os.environ.copy()
    # NiceGUI checks PYTEST_CURRENT_TEST to enforce test fixtures mode with
    # NICEGUI_SCREEN_TEST_PORT. As a standalone subprocess, strip this variable.
    env.pop("PYTEST_CURRENT_TEST", None)

    kwargs: dict[str, Any] = {
        "cwd": str(PROJECT_ROOT),
        "env": env,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    return ManagedPopen(
        [sys.executable, "run.py", "--browser"],
        **kwargs,
    )


def _ensure_process_terminated(p: subprocess.Popen[bytes]) -> None:
    """Reliable cleanup safeguard so failed tests do not leak child processes."""
    if p.poll() is None:
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                    capture_output=True,
                    check=False,
                )
            else:
                p.kill()
            p.communicate(timeout=3)
        except Exception:
            pass
    if hasattr(p, "close_files"):
        p.close_files()


def test_clean_shutdown_without_calculation():
    """Verify application starts and shuts down cleanly on signal within deadline."""
    p = _start_app_process()
    try:
        # Verify application remains alive while starting up
        time.sleep(2.0)
        assert p.poll() is None, f"Application exited prematurely with code {p.returncode}"

        # Request graceful shutdown
        p.send_signal(SHUTDOWN_SIGNAL)
        try:
            stdout, stderr = p.communicate(timeout=6)
        except subprocess.TimeoutExpired as exc:
            out_str = exc.stdout.decode("utf-8", errors="replace") if exc.stdout else ""
            err_str = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            pytest.fail(
                f"Application failed to shut down cleanly within timeout.\n"
                f"Process alive: {p.poll() is None}, returncode: {p.returncode}\n"
                f"STDOUT:\n{out_str}\n"
                f"STDERR:\n{err_str}"
            )

        assert p.returncode in VALID_RETURNCODES
        assert b"asyncio.exceptions.CancelledError" not in stderr
        assert b"leaked semaphore objects" not in stderr
    finally:
        _ensure_process_terminated(p)


def test_clean_shutdown_after_page_load():
    """Verify application starts, responds to HTTP request, and shuts down cleanly."""
    p = _start_app_process()
    try:
        # Bounded readiness loop to verify the server is ready and serving HTTP requests
        readiness_deadline = time.monotonic() + 10.0
        server_ready = False
        last_error: Exception | None = None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        # Dynamically determine the URL NiceGUI bound to
        url = "http://127.0.0.1:8080"
        if p.stdout is not None:
            line = p.stdout.readline().decode("utf-8", errors="replace")
            m = re.search(r"http://[^\s]+", line)
            if m:
                url = m.group(0).rstrip("/")

        target_url = f"{url}/"
        while time.monotonic() < readiness_deadline:
            assert p.poll() is None, f"Application exited prematurely with code {p.returncode}"
            try:
                with opener.open(target_url, timeout=1.0) as resp:
                    if resp.status == 200:
                        server_ready = True
                        break
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                time.sleep(0.1)

        assert server_ready, (
            f"Server failed to respond with HTTP 200 at {target_url} within readiness deadline. Last error: {last_error}"
        )

        # Request graceful shutdown
        p.send_signal(SHUTDOWN_SIGNAL)
        try:
            stdout, stderr = p.communicate(timeout=6)
        except subprocess.TimeoutExpired as exc:
            out_str = exc.stdout.decode("utf-8", errors="replace") if exc.stdout else ""
            err_str = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            pytest.fail(
                f"Application failed to shut down cleanly after web request.\n"
                f"Process alive: {p.poll() is None}, returncode: {p.returncode}\n"
                f"STDOUT:\n{out_str}\n"
                f"STDERR:\n{err_str}"
            )

        assert p.returncode in VALID_RETURNCODES
        assert b"asyncio.exceptions.CancelledError" not in stderr
        assert b"leaked semaphore objects" not in stderr
    finally:
        _ensure_process_terminated(p)


def test_repeated_sigint_does_not_deadlock():
    """Verify repeated interrupt signals trigger immediate exit without deadlock."""
    p = _start_app_process()
    try:
        # Verify application remains alive while starting up
        time.sleep(2.0)
        assert p.poll() is None, f"Application exited prematurely with code {p.returncode}"

        # Request graceful shutdown
        p.send_signal(SHUTDOWN_SIGNAL)
        time.sleep(0.05)
        # Send repeated signal to verify prompt exit without hanging
        p.send_signal(SHUTDOWN_SIGNAL)

        try:
            stdout, stderr = p.communicate(timeout=6)
        except subprocess.TimeoutExpired as exc:
            out_str = exc.stdout.decode("utf-8", errors="replace") if exc.stdout else ""
            err_str = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            pytest.fail(
                f"Repeated interrupt signals deadlocked on shutdown.\n"
                f"Process alive: {p.poll() is None}, returncode: {p.returncode}\n"
                f"STDOUT:\n{out_str}\n"
                f"STDERR:\n{err_str}"
            )

        assert p.returncode in VALID_RETURNCODES
        assert b"asyncio.exceptions.CancelledError" not in stderr
        assert b"leaked semaphore objects" not in stderr
    finally:
        _ensure_process_terminated(p)

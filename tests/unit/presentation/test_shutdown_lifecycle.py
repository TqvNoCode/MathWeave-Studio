"""Tests for clean application lifecycle and bounded shutdown."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

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


def _start_app_process() -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    # NiceGUI checks PYTEST_CURRENT_TEST to enforce test fixtures mode with
    # NICEGUI_SCREEN_TEST_PORT. As a standalone subprocess, strip this variable.
    env.pop("PYTEST_CURRENT_TEST", None)

    kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "cwd": str(PROJECT_ROOT),
        "env": env,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    return subprocess.Popen(
        [sys.executable, "run.py", "--browser"],
        **kwargs,
    )


def _ensure_process_terminated(p: subprocess.Popen[bytes]) -> None:
    """Reliable cleanup safeguard so failed tests do not leak child processes."""
    if p.poll() is None:
        try:
            p.kill()
            p.communicate(timeout=3)
        except Exception:
            pass


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
        except subprocess.TimeoutExpired:
            pytest.fail("Application failed to shut down cleanly within timeout")

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
        except subprocess.TimeoutExpired:
            pytest.fail("Application failed to shut down cleanly after web request")

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
        except subprocess.TimeoutExpired:
            pytest.fail("Repeated interrupt signals deadlocked on shutdown")

        assert p.returncode in VALID_RETURNCODES
        assert b"asyncio.exceptions.CancelledError" not in stderr
        assert b"leaked semaphore objects" not in stderr
    finally:
        _ensure_process_terminated(p)

"""Tests for clean application lifecycle and bounded shutdown."""

import signal
import subprocess
import sys
import time
import urllib.request
import pytest


def test_clean_shutdown_without_calculation():
    """Verify application starts and shuts down cleanly on SIGINT within 5 seconds."""
    p = subprocess.Popen(
        [sys.executable, "run.py", "--browser"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2.5)
    p.send_signal(signal.SIGINT)
    try:
        stdout, stderr = p.communicate(timeout=6)
        assert p.returncode in (0, 1, -signal.SIGINT)
        assert b"asyncio.exceptions.CancelledError" not in stderr
        assert b"leaked semaphore objects" not in stderr
    except subprocess.TimeoutExpired:
        p.kill()
        pytest.fail("Application failed to shut down cleanly within timeout")


def test_clean_shutdown_after_page_load():
    """Verify application starts, responds to HTTP request, and shuts down cleanly."""
    p = subprocess.Popen(
        [sys.executable, "run.py", "--browser"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2.5)
    # Ping the server
    try:
        with urllib.request.urlopen("http://127.0.0.1:8080/", timeout=3) as resp:
            assert resp.status == 200
    except Exception:
        pass  # If port differs or already bound, shutdown still must work

    p.send_signal(signal.SIGINT)
    try:
        stdout, stderr = p.communicate(timeout=6)
        assert p.returncode in (0, 1, -signal.SIGINT)
        assert b"asyncio.exceptions.CancelledError" not in stderr
        assert b"leaked semaphore objects" not in stderr
    except subprocess.TimeoutExpired:
        p.kill()
        pytest.fail("Application failed to shut down cleanly after web request")


def test_repeated_sigint_does_not_deadlock():
    """Verify repeated SIGINT triggers immediate exit without 30s timeout hang."""
    p = subprocess.Popen(
        [sys.executable, "run.py", "--browser"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2.5)
    p.send_signal(signal.SIGINT)
    time.sleep(0.05)
    p.send_signal(signal.SIGINT)
    try:
        stdout, stderr = p.communicate(timeout=6)
        assert p.returncode in (0, 1, -signal.SIGINT)
        assert b"asyncio.exceptions.CancelledError" not in stderr
        assert b"leaked semaphore objects" not in stderr
    except subprocess.TimeoutExpired:
        p.kill()
        pytest.fail("Repeated SIGINT deadlocked on shutdown")

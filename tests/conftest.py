"""Test configuration and shared fixtures."""

import sys
from pathlib import Path

import pytest
from nicegui import Client, core

# Ensure src is on sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture(autouse=True)
def _reset_nicegui_context():
    yield
    core.script_mode = False
    Client.instances.clear()

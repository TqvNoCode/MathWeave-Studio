"""Presentation layer for NiceGUI user interface."""

from math_app.presentation.app import create_app
from math_app.presentation.startup import (
    HeadlessEnvironmentError,
    NativeBackendError,
    StartupMode,
    resolve_startup_mode,
    validate_and_prepare_native_backend,
)

__all__ = [
    "create_app",
    "StartupMode",
    "HeadlessEnvironmentError",
    "NativeBackendError",
    "resolve_startup_mode",
    "validate_and_prepare_native_backend",
]

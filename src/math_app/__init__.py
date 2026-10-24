"""MathWeave Studio package."""

from __future__ import annotations

try:
    from importlib.metadata import version

    __version__ = version("mathweave-studio")
except Exception:
    __version__ = "0.1.0"

__title__ = "MathWeave Studio"
__compact_name__ = "MathWeaveStudio"
__slug__ = "mathweave-studio"
__author__ = "TQV"
__copyright__ = "© 2026 by TQV"

from math_app.main import main

__all__ = [
    "__title__",
    "__compact_name__",
    "__slug__",
    "__version__",
    "__author__",
    "__copyright__",
    "main",
]


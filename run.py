#!/usr/bin/env python3
"""Convenience launcher for MathWeave Studio.

Allows running MathWeave Studio directly via:
    python run.py
or
    uv run run.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from math_app.main import main

if __name__ in {"__main__", "__mp_main__"}:
    main()

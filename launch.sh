#!/usr/bin/env bash
# MathWeave Studio Linux Desktop Application Launcher

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Prefer packaged standalone binary if built
if [ -x "$SCRIPT_DIR/dist/mathweave-studio/mathweave-studio" ]; then
    exec "$SCRIPT_DIR/dist/mathweave-studio/mathweave-studio" "$@"
elif [ -x "$SCRIPT_DIR/dist/mathstudio/mathstudio" ]; then
    exec "$SCRIPT_DIR/dist/mathstudio/mathstudio" "$@"
fi

# 2. Fall back to local virtual environment
if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    exec "$SCRIPT_DIR/.venv/bin/python" run.py "$@"
fi

# 3. Fall back to uv run
if command -v uv >/dev/null 2>&1; then
    exec uv run run.py "$@"
fi

echo "Error: Python runtime not found. Please run 'uv sync' or execute within the workspace." >&2
exit 1

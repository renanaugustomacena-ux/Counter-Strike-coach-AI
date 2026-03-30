#!/bin/bash
# Macena CS2 Analyzer — Qt App Launcher
# Usage: ./launch.sh
set -e
cd "$(dirname "$0")"

# Use the project venv explicitly (not system Python)
VENV_PYTHON="$HOME/.venvs/cs2analyzer/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Virtual environment not found at $VENV_PYTHON"
    echo "Create it with: python3.10 -m venv ~/.venvs/cs2analyzer"
    exit 1
fi

# Verify Python version (must be 3.10.x)
PY_VERSION=$("$VENV_PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [ "$PY_VERSION" != "3.10" ]; then
    echo "ERROR: Expected Python 3.10, got $PY_VERSION"
    exit 1
fi

# Clear stale bytecode before launch
find Programma_CS2_RENAN -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

exec "$VENV_PYTHON" -m Programma_CS2_RENAN.apps.qt_app.app "$@"

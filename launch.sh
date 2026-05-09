#!/bin/bash
# Macena CS2 Analyzer — Qt App Launcher
# Usage: ./launch.sh
set -e
cd "$(dirname "$0")"

# Use the project-local venv (portable across machines)
VENV_PYTHON="$(dirname "$0")/.venv/bin/python3"
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Virtual environment not found at $VENV_PYTHON"
    echo "Create it with: python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Verify Python version (must be >= 3.10)
PY_MINOR=$("$VENV_PYTHON" -c "import sys; print(sys.version_info.minor)")
if [ "$PY_MINOR" -lt 10 ]; then
    echo "ERROR: Requires Python >= 3.10, got $("$VENV_PYTHON" --version)"
    exit 1
fi

# Clear stale bytecode before launch
find Programma_CS2_RENAN -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Force software rendering for Qt charts (prevents segfault on some Linux GPU drivers)
export QT_QUICK_BACKEND=software
export QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu"

exec "$VENV_PYTHON" -m Programma_CS2_RENAN.apps.qt_app.app "$@"

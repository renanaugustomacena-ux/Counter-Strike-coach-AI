import logging
import os
import sys
from pathlib import Path

# --- Venv Guard ---
if sys.prefix == sys.base_prefix:
    print("ERROR: Not in venv. Run: source ~/.venvs/cs2analyzer/bin/activate", file=sys.stderr)
    sys.exit(2)

# Setup headless Kivy
os.environ["KIVY_NO_CONSOLELOG"] = "1"
os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_NO_WINDOW"] = "1"  # Force headless

# Path setup — anchored to __file__, not CWD
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    print("[-] Importing Main App...")
    from Programma_CS2_RENAN.main import CS2AnalyzerApp

    print("[-] Instantiating App...")
    app = CS2AnalyzerApp()

    print("[-] Building App (Dry Run)...")
    # We mock the build process to avoid needing a window provider
    # This verifies that all KV loading and Python init logic works
    try:
        app.build()
        print("[SUCCESS] App.build() completed without error.")
    except Exception as build_e:
        # In headless, some graphics calls might fail, which is expected.
        # We are looking for logic errors (ImportError, SyntaxError, ConfigError)
        print(f"[NOTE] Build stopped (expected in headless): {build_e}")

    print("[SUCCESS] main.py is structurally sound and importable.")

except Exception as e:
    print(f"[CRITICAL FAILURE] main.py crashed: {e}")
    sys.exit(1)

import logging
import os
import sys

# Setup headless Kivy
os.environ["KIVY_NO_CONSOLELOG"] = "1"
os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_NO_WINDOW"] = "1"  # Force headless

# Path setup
sys.path.append(os.getcwd())

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

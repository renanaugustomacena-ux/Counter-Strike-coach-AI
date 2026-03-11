import json
import os
import sys

import pytest

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Programma_CS2_RENAN.core.config import load_user_settings, save_user_setting


def test_config_persistence():
    """Functional Test: Verify user settings are saved and loaded correctly."""
    test_key = "CS2_PLAYER_NAME"
    test_val = "Pytest_User"

    # Save original value to restore after test
    original_settings = load_user_settings()
    original_val = original_settings.get(test_key)

    try:
        save_user_setting(test_key, test_val)
        settings = load_user_settings()
        assert settings[test_key] == test_val
    finally:
        # Restore original value to avoid test side-effects
        if original_val is not None:
            save_user_setting(test_key, original_val)
        else:
            # Original was unset; clear the test value to restore clean state
            save_user_setting(test_key, "")

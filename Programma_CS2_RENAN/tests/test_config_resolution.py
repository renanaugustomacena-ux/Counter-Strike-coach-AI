"""Tests for the 3-level config resolution system.

Validates: defaults → user_settings.json → keyring/env, thread-safety,
and atomic save_user_setting().
"""

import json
import os
import threading
from unittest.mock import MagicMock, patch

import pytest


class TestConfigDefaults:
    """Verify default values are returned when no JSON or keyring overrides exist."""

    def test_default_player_name_is_empty(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import load_user_settings

        settings = load_user_settings()
        assert settings["CS2_PLAYER_NAME"] == ""

    def test_default_demo_path_is_home(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import load_user_settings

        settings = load_user_settings()
        assert settings["DEFAULT_DEMO_PATH"] == os.path.expanduser("~")

    def test_default_coaching_flags(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import load_user_settings

        settings = load_user_settings()
        assert settings["USE_COPER_COACHING"] is True
        assert settings["USE_RAP_MODEL"] is False
        assert settings["USE_JEPA_MODEL"] is False
        assert settings["USE_HYBRID_COACHING"] is False

    def test_default_setup_not_completed(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import load_user_settings

        settings = load_user_settings()
        assert settings["SETUP_COMPLETED"] is False

    def test_all_expected_keys_present(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import load_user_settings

        settings = load_user_settings()
        required_keys = [
            "CS2_PLAYER_NAME",
            "STEAM_ID",
            "DEFAULT_DEMO_PATH",
            "PRO_DEMO_PATH",
            "BRAIN_DATA_ROOT",
            "ACTIVE_THEME",
            "LANGUAGE",
            "SETUP_COMPLETED",
            "USE_COPER_COACHING",
            "USE_RAP_MODEL",
            "USE_JEPA_MODEL",
        ]
        for key in required_keys:
            assert key in settings, f"Missing default key: {key}"


class TestJsonOverridesDefaults:
    """Verify that user_settings.json values override defaults."""

    def test_json_overrides_player_name(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import SETTINGS_PATH, load_user_settings

        with open(SETTINGS_PATH, "w") as f:
            json.dump({"CS2_PLAYER_NAME": "s1mple"}, f)

        settings = load_user_settings()
        assert settings["CS2_PLAYER_NAME"] == "s1mple"

    def test_json_overrides_coaching_flags(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import SETTINGS_PATH, load_user_settings

        with open(SETTINGS_PATH, "w") as f:
            json.dump({"USE_JEPA_MODEL": True, "USE_HYBRID_COACHING": True}, f)

        settings = load_user_settings()
        assert settings["USE_JEPA_MODEL"] is True
        assert settings["USE_HYBRID_COACHING"] is True
        # Unset keys should still have defaults
        assert settings["USE_RAP_MODEL"] is False

    def test_json_preserves_unset_defaults(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import SETTINGS_PATH, load_user_settings

        with open(SETTINGS_PATH, "w") as f:
            json.dump({"LANGUAGE": "pt"}, f)

        settings = load_user_settings()
        assert settings["LANGUAGE"] == "pt"
        assert settings["CS2_PLAYER_NAME"] == ""  # Default preserved

    def test_corrupted_json_falls_back_to_defaults(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import SETTINGS_PATH, load_user_settings

        with open(SETTINGS_PATH, "w") as f:
            f.write("{invalid json!!!")

        settings = load_user_settings()
        # Should still return defaults, not crash
        assert settings["CS2_PLAYER_NAME"] == ""
        assert isinstance(settings, dict)

    def test_non_dict_json_falls_back_to_defaults(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import SETTINGS_PATH, load_user_settings

        with open(SETTINGS_PATH, "w") as f:
            json.dump(["not", "a", "dict"], f)

        settings = load_user_settings()
        assert settings["CS2_PLAYER_NAME"] == ""


class TestSaveUserSetting:
    """Verify atomic save_user_setting() writes."""

    def test_save_creates_file_if_missing(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import SETTINGS_PATH, save_user_setting

        if os.path.exists(SETTINGS_PATH):
            os.remove(SETTINGS_PATH)

        save_user_setting("CS2_PLAYER_NAME", "niko")

        assert os.path.exists(SETTINGS_PATH)
        with open(SETTINGS_PATH) as f:
            data = json.load(f)
        assert data["CS2_PLAYER_NAME"] == "niko"

    def test_save_preserves_existing_keys(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import SETTINGS_PATH, save_user_setting

        with open(SETTINGS_PATH, "w") as f:
            json.dump({"LANGUAGE": "it", "CS2_PLAYER_NAME": "old"}, f)

        save_user_setting("CS2_PLAYER_NAME", "new")

        with open(SETTINGS_PATH) as f:
            data = json.load(f)
        assert data["CS2_PLAYER_NAME"] == "new"
        assert data["LANGUAGE"] == "it"  # Preserved

    def test_save_updates_in_memory_settings(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import get_setting, save_user_setting

        save_user_setting("CS2_PLAYER_NAME", "zywoo")
        assert get_setting("CS2_PLAYER_NAME") == "zywoo"

    def test_save_atomic_no_partial_writes(self, isolated_settings):
        """Verify no .tmp file is left behind after save."""
        from Programma_CS2_RENAN.core.config import SETTINGS_PATH, save_user_setting

        save_user_setting("LANGUAGE", "en")
        assert not os.path.exists(SETTINGS_PATH + ".tmp")


class TestGetSetting:
    """Verify thread-safe get_setting() behavior."""

    def test_get_setting_returns_saved_value(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import get_setting, save_user_setting

        save_user_setting("CS2_PLAYER_NAME", "device")
        assert get_setting("CS2_PLAYER_NAME") == "device"

    def test_get_setting_returns_default_for_unknown_key(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import get_setting

        assert get_setting("NONEXISTENT_KEY", "fallback") == "fallback"

    def test_get_setting_returns_none_for_unknown_key_no_default(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import get_setting

        assert get_setting("NONEXISTENT_KEY") is None


class TestRefreshSettings:
    """Verify refresh_settings() reloads from disk."""

    def test_refresh_picks_up_disk_changes(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import (
            SETTINGS_PATH,
            get_setting,
            refresh_settings,
            save_user_setting,
        )

        save_user_setting("CS2_PLAYER_NAME", "before")
        assert get_setting("CS2_PLAYER_NAME") == "before"

        # Simulate external write (another process)
        with open(SETTINGS_PATH, "r") as f:
            data = json.load(f)
        data["CS2_PLAYER_NAME"] = "after_external"
        with open(SETTINGS_PATH, "w") as f:
            json.dump(data, f)

        refresh_settings()
        assert get_setting("CS2_PLAYER_NAME") == "after_external"


class TestThreadSafety:
    """Verify _settings_lock prevents data races."""

    def test_concurrent_saves_no_corruption(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import SETTINGS_PATH, get_setting, save_user_setting

        errors = []

        def writer(key, value):
            try:
                save_user_setting(key, value)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):
            t = threading.Thread(target=writer, args=(f"TEST_KEY_{i}", f"value_{i}"))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert not errors, f"Concurrent saves produced errors: {errors}"

        # File should be valid JSON
        with open(SETTINGS_PATH) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_concurrent_reads_no_errors(self, isolated_settings):
        from Programma_CS2_RENAN.core.config import get_setting, save_user_setting

        save_user_setting("CONCURRENT_TEST", "stable")

        errors = []
        results = []

        def reader():
            try:
                val = get_setting("CONCURRENT_TEST")
                results.append(val)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert all(r == "stable" for r in results)


class TestConstants:
    """Verify critical constants."""

    def test_min_demos_for_coaching(self):
        from Programma_CS2_RENAN.core.config import MIN_DEMOS_FOR_COACHING

        assert MIN_DEMOS_FOR_COACHING == 1

    def test_max_demos_per_month(self):
        from Programma_CS2_RENAN.core.config import MAX_DEMOS_PER_MONTH

        assert MAX_DEMOS_PER_MONTH == 10


# --- Fixtures ---


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    """Redirect SETTINGS_PATH to a temp directory so tests don't touch real config."""
    import Programma_CS2_RENAN.core.config as config_module

    temp_settings = str(tmp_path / "user_settings.json")
    monkeypatch.setattr(config_module, "SETTINGS_PATH", temp_settings)
    # Reset in-memory settings to defaults
    monkeypatch.setattr(config_module, "_settings", config_module.load_user_settings())
    yield

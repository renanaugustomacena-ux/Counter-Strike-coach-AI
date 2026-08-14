"""F-0007 regression: set_secret degrades like get_secret — a keyring
backend failure returns False (routing save_user_setting to the FE-04
plaintext fallback) instead of raising out of the UI save path."""

from unittest.mock import patch

from Programma_CS2_RENAN.core import config


def test_backend_failure_returns_false_not_raise():
    with patch.object(config, "keyring") as kr:
        kr.set_password.side_effect = RuntimeError("no backend")
        assert config.set_secret("STEAM_API_KEY", "x") is False


def test_save_user_setting_survives_keyring_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SETTINGS_PATH", str(tmp_path / "user_settings.json"))
    snapshot = config._settings.copy()
    try:
        with patch.object(config, "keyring") as kr:
            kr.set_password.side_effect = RuntimeError("no backend")
            config.save_user_setting("STEAM_API_KEY", "sk-test-123")  # must not raise
        import json

        on_disk = json.loads((tmp_path / "user_settings.json").read_text())
        assert on_disk.get("STEAM_API_KEY") == "sk-test-123", "plaintext fallback not taken"
    finally:
        config._settings.clear()
        config._settings.update(snapshot)

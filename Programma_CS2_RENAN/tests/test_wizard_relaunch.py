"""Install round (WP4a) — a brain root chosen in the wizard is applied by a
relaunch, and only when it differs from the root config resolved at import.
The demo step also offers the optional pro-demo folder.
"""

from __future__ import annotations

import os
import sys

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MACENA_UI_ANIMATIONS", "0")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class _App:
    def __init__(self):
        self.quit_calls = 0

    def quit(self):
        self.quit_calls += 1


def _settings(brain_root: str):
    return lambda key, default=None: brain_root if key == "BRAIN_DATA_ROOT" else default


def test_root_unchanged_when_the_wizard_kept_the_default(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.apps.qt_app import app as app_module
    from Programma_CS2_RENAN.core import config

    monkeypatch.setattr(config, "USER_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "get_setting", _settings(""))
    assert app_module._data_root_changed() is False
    monkeypatch.setattr(config, "get_setting", _settings(str(tmp_path) + os.sep))
    assert app_module._data_root_changed() is False


def test_root_changed_when_the_wizard_picked_another_folder(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.apps.qt_app import app as app_module
    from Programma_CS2_RENAN.core import config

    monkeypatch.setattr(config, "USER_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "get_setting", _settings(str(tmp_path / "elsewhere")))
    assert app_module._data_root_changed() is True


def test_relaunch_only_when_the_root_changed(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.apps.qt_app import app as app_module
    from Programma_CS2_RENAN.core import config
    from Programma_CS2_RENAN.core import lifecycle as lifecycle_module

    monkeypatch.setattr(config, "USER_DATA_ROOT", str(tmp_path))
    shut: list[bool] = []
    spawned: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(lifecycle_module.lifecycle, "shutdown", lambda: shut.append(True))

    def spawn(program, args):
        spawned.append((program, list(args)))
        return True

    app = _App()
    monkeypatch.setattr(config, "get_setting", _settings(""))
    assert app_module._relaunch_for_new_data_root(app, spawn=spawn) is False
    assert spawned == [] and shut == [] and app.quit_calls == 0

    monkeypatch.setattr(config, "get_setting", _settings(str(tmp_path / "new")))
    assert app_module._relaunch_for_new_data_root(app, spawn=spawn) is True
    argv = lifecycle_module.lifecycle.relaunch_command()
    assert shut == [True]
    assert spawned == [(argv[0], argv[1:])]
    assert app.quit_calls == 1


def test_failed_spawn_keeps_the_current_process_alive(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.apps.qt_app import app as app_module
    from Programma_CS2_RENAN.core import config
    from Programma_CS2_RENAN.core import lifecycle as lifecycle_module

    monkeypatch.setattr(config, "USER_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "get_setting", _settings(str(tmp_path / "new")))
    monkeypatch.setattr(lifecycle_module.lifecycle, "shutdown", lambda: None)
    rearmed: list[bool] = []
    monkeypatch.setattr(
        lifecycle_module.lifecycle, "ensure_single_instance", lambda: rearmed.append(True) or True
    )
    app = _App()
    assert app_module._relaunch_for_new_data_root(app, spawn=lambda p, a: False) is False
    assert app.quit_calls == 0
    assert rearmed == [True], "the released single-instance lock must be re-armed"


def test_relaunch_command_matches_the_launch_mode(monkeypatch):
    from Programma_CS2_RENAN.core import lifecycle as lifecycle_module

    monkeypatch.setattr(lifecycle_module, "_is_frozen", lambda: False)
    assert lifecycle_module.lifecycle.relaunch_command() == [
        sys.executable,
        "-m",
        "Programma_CS2_RENAN.apps.qt_app.app",
    ]
    monkeypatch.setattr(lifecycle_module, "_is_frozen", lambda: True)
    assert lifecycle_module.lifecycle.relaunch_command() == [sys.executable]


def test_wizard_saves_the_optional_pro_demo_folder(qapp, monkeypatch, tmp_path):
    import Programma_CS2_RENAN.apps.qt_app.screens.wizard_screen as wizard_screen

    saved: list[tuple[str, object]] = []
    monkeypatch.setattr(wizard_screen, "save_user_setting", lambda k, v: saved.append((k, v)))
    widget = wizard_screen.WizardScreen()
    try:
        widget._demo_input.setText(str(tmp_path / "mine"))
        widget._pro_demo_input.setText(str(tmp_path / "pros"))
        widget._validate_demo()
        assert ("DEFAULT_DEMO_PATH", os.path.normpath(str(tmp_path / "mine"))) in saved
        assert ("PRO_DEMO_PATH", os.path.normpath(str(tmp_path / "pros"))) in saved

        saved.clear()
        widget._pro_demo_input.setText("")
        widget._validate_demo()
        assert not any(key == "PRO_DEMO_PATH" for key, _ in saved)
    finally:
        widget.deleteLater()
        qapp.processEvents()

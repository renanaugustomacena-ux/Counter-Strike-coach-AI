"""Boot round (WP3) — the ingestion watchdog must not die on unset folders.

``daemon_err.log`` on the author's machine showed the Session Engine's
watcher crashing at start with ``FileNotFoundError: [WinError 3] ... ''``:
``PRO_DEMO_PATH`` defaults to an empty string (deliberately, OI-8) and the
watcher ran ``os.makedirs('')`` on it.
"""

from __future__ import annotations

import os

import pytest


class _FakeObserver:
    def __init__(self):
        self.scheduled = []
        self.started = False

    def schedule(self, handler, path, recursive=False):
        self.scheduled.append(path)

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    def join(self):
        pass


@pytest.fixture
def watcher_module(monkeypatch):
    import Programma_CS2_RENAN.backend.ingestion.watcher as w

    monkeypatch.setattr(w, "Observer", _FakeObserver)
    monkeypatch.setattr(w, "get_db_manager", lambda: object())
    return w


def _settings(monkeypatch, module, values: dict):
    monkeypatch.setattr(module, "get_setting", lambda key, default=None: values.get(key, default))


def test_start_skips_an_empty_pro_path(watcher_module, monkeypatch, tmp_path):
    user_dir = tmp_path / "demos"
    user_dir.mkdir()
    _settings(
        monkeypatch, watcher_module, {"DEFAULT_DEMO_PATH": str(user_dir), "PRO_DEMO_PATH": ""}
    )

    watcher = watcher_module.IngestionWatcher()
    watcher.start()

    assert watcher.observer.scheduled == [str(user_dir)]
    assert watcher.running is True


def test_start_with_no_folders_does_not_start_the_observer(watcher_module, monkeypatch):
    _settings(monkeypatch, watcher_module, {"DEFAULT_DEMO_PATH": "", "PRO_DEMO_PATH": ""})

    watcher = watcher_module.IngestionWatcher()
    watcher.start()

    assert watcher.observer.scheduled == []
    assert watcher.observer.started is False
    assert watcher.running is False


def test_start_never_watches_the_home_directory(watcher_module, monkeypatch, tmp_path):
    """OI-8: $HOME is never a demo root — watching it would flood the queue."""
    pro_dir = tmp_path / "pro"
    pro_dir.mkdir()
    _settings(
        monkeypatch,
        watcher_module,
        {"DEFAULT_DEMO_PATH": os.path.expanduser("~"), "PRO_DEMO_PATH": str(pro_dir)},
    )

    watcher = watcher_module.IngestionWatcher()
    watcher.start()

    assert watcher.observer.scheduled == [str(pro_dir)]


def test_start_creates_a_configured_but_missing_folder(watcher_module, monkeypatch, tmp_path):
    """A folder the user chose is created (previous behaviour, kept)."""
    missing = tmp_path / "later"
    _settings(monkeypatch, watcher_module, {"DEFAULT_DEMO_PATH": str(missing), "PRO_DEMO_PATH": ""})

    watcher = watcher_module.IngestionWatcher()
    watcher.start()

    assert missing.is_dir()
    assert watcher.observer.scheduled == [str(missing)]

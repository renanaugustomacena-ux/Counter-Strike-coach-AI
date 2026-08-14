"""F-0008 regression: get_pro_demo_base never falls back to $HOME.

$HOME always exists, so a $HOME default silently pointed pro-demo
sweeps at the user profile (the baseline integration run rglobbed the
whole home dir and fed an arbitrary .dem to the parser -> F-0006)."""

import os
from pathlib import Path

from Programma_CS2_RENAN.core import config


def test_unset_path_falls_back_in_project(monkeypatch):
    monkeypatch.setitem(config._settings, "PRO_DEMO_PATH", "")
    base = config.get_pro_demo_base()
    home = Path(os.path.expanduser("~")).resolve()
    assert base.resolve() != home, "fell back to $HOME again"
    assert "Programma_CS2_RENAN" in str(base), f"unexpected fallback {base}"


def test_missing_configured_path_never_yields_home(monkeypatch, tmp_path):
    monkeypatch.setitem(
        config._settings, "PRO_DEMO_PATH", str(tmp_path / "unplugged" / "DEMO_PRO_PLAYERS")
    )
    base = config.get_pro_demo_base()
    assert base.resolve() != Path(os.path.expanduser("~")).resolve()


def test_existing_configured_path_is_honoured(monkeypatch, tmp_path):
    pool = tmp_path / "DEMO_PRO_PLAYERS"
    pool.mkdir()
    monkeypatch.setitem(config._settings, "PRO_DEMO_PATH", str(pool))
    assert config.get_pro_demo_base() == pool

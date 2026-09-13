"""Packaging round (WP4c) — the packaged selftest also writes its report to a
file (a windowed exe has no stdout for CI to read) and checks the bundle
pieces the runtime needs.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_main_writes_the_report_beside_the_user_data(monkeypatch, tmp_path, capsys):
    import Programma_CS2_RENAN.core.config as config
    from Programma_CS2_RENAN.core import selftest

    monkeypatch.setattr(config, "USER_DATA_ROOT", str(tmp_path))
    code = selftest.main([])
    printed = json.loads(capsys.readouterr().out)
    written = json.loads((tmp_path / "selftest_report.json").read_text(encoding="utf-8"))

    assert code == 0, printed
    assert written["ok"] is True
    assert written["report_path"] == str(tmp_path / "selftest_report.json")
    assert printed["report_path"] == written["report_path"]


def test_report_checks_alembic_and_the_bundle_seed():
    from Programma_CS2_RENAN.core.selftest import run_selftest

    report = run_selftest()
    assert report["alembic_ini"] == str(PROJECT_ROOT / "alembic.ini")
    assert report["alembic_ini_ok"] is True
    assert "hltv_seed" in report and isinstance(report["hltv_seed_present"], bool)
    assert isinstance(report["factory_models"], list)
    assert "warnings" in report and isinstance(report["warnings"], list)


def test_a_missing_alembic_ini_fails_the_selftest(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.backend.storage import db_migrate
    from Programma_CS2_RENAN.core.selftest import run_selftest

    monkeypatch.setattr(
        db_migrate,
        "_alembic_paths",
        lambda: (str(tmp_path / "alembic.ini"), str(tmp_path / "alembic")),
    )
    report = run_selftest()
    assert report["alembic_ini_ok"] is False
    assert report["ok"] is False

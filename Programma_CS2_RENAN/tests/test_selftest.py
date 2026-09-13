"""Boot round (WP3) — ``Macena_CS2_Analyzer.exe --selftest`` contract.

The packaged build was never executed anywhere (CI packs it and uploads).
The selftest is a headless probe the build script and CI can run against
the frozen exe: resolve every runtime path, prove the data root is
writable, open the database if it exists, list bundled models — and exit
non-zero when any of that fails.  No Qt, no daemon, no network.
"""

from __future__ import annotations

import json

from Programma_CS2_RENAN.core.selftest import run_selftest

_REQUIRED = (
    "frozen",
    "base_dir",
    "user_data_root",
    "user_data_root_writable",
    "db_path",
    "db_exists",
    "db_ok",
    "models_dir",
    "models",
    "log_dir",
    "resource_docs_dir",
    "resource_docs_ok",
    "ok",
)


def test_selftest_reports_every_runtime_path_and_passes_in_dev():
    report = run_selftest()
    for key in _REQUIRED:
        assert key in report, key
    assert report["frozen"] is False
    assert report["ok"] is True, report
    assert report["user_data_root_writable"] is True
    assert report["resource_docs_ok"] is True
    assert isinstance(report["models"], list)


def test_selftest_report_is_json_serialisable():
    json.dumps(run_selftest())


def test_selftest_fails_when_the_data_root_is_not_writable(monkeypatch, tmp_path):
    import Programma_CS2_RENAN.core.config as config

    locked = tmp_path / "locked"
    locked.mkdir()
    monkeypatch.setattr(config, "USER_DATA_ROOT", str(locked))
    monkeypatch.setattr("Programma_CS2_RENAN.core.selftest._can_write", lambda path: False)
    report = run_selftest()
    assert report["user_data_root_writable"] is False
    assert report["ok"] is False

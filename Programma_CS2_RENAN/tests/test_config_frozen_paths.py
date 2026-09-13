"""Install round (WP4a) — a frozen build keeps every writable path under the
user's data root and every bundled resource under _MEIPASS/Programma_CS2_RENAN.

config.py resolves its paths at import, so the frozen environment
(``sys.frozen``, ``sys._MEIPASS``, ``sys.executable`` inside a fake install
directory, ``LOCALAPPDATA`` in a temp dir) has to exist before the first
import: these tests run the import in a subprocess.  The fake install
directory must stay byte-identical — under Program Files any write there
is a PermissionError and the packaged app dies before showing a window.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_CHILD = r"""
import json, os, sys
sys.frozen = True
sys._MEIPASS = os.environ["FAKE_MEIPASS"]
sys.executable = os.environ["FAKE_EXE"]
os.chdir(sys._MEIPASS)  # what core/frozen_hook.py does in the real build
from Programma_CS2_RENAN.core import config
print(json.dumps({
    "BASE_DIR": config.BASE_DIR,
    "USER_DATA_ROOT": config.USER_DATA_ROOT,
    "CORE_DB_DIR": config.CORE_DB_DIR,
    "DATABASE_URL": config.DATABASE_URL,
    "HLTV_DATABASE_URL": config.HLTV_DATABASE_URL,
    "LOG_DIR": config.LOG_DIR,
    "DATA_DIR": config.DATA_DIR,
    "MODELS_DIR": config.MODELS_DIR,
    "MATCH_DATA_PATH": config.MATCH_DATA_PATH,
    "SETTINGS_PATH": config.SETTINGS_PATH,
    "docs": config.get_resource_path(os.path.join("data", "docs")),
    "pro_demo_base": str(config.get_pro_demo_base()),
}))
"""

_SQLITE = "sqlite:///"
_PATH_KEYS = (
    "LOG_DIR",
    "DATA_DIR",
    "MODELS_DIR",
    "MATCH_DATA_PATH",
    "SETTINGS_PATH",
    "pro_demo_base",
)


def _snapshot(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*")}


def _under(path: str, root: Path) -> bool:
    return Path(path).resolve().is_relative_to(root.resolve())


def _run_frozen(tmp_path: Path, extra_env: dict | None = None):
    install = tmp_path / "Program Files" / "Macena CS2 Analyzer"
    meipass = install / "_internal"
    docs = meipass / "Programma_CS2_RENAN" / "data" / "docs"
    docs.mkdir(parents=True)
    (docs / "getting_started.md").write_text("# hi\n", encoding="utf-8")
    exe = install / "Macena_CS2_Analyzer.exe"
    exe.write_bytes(b"MZ")
    local = tmp_path / "LocalAppData"
    local.mkdir()

    scrub = ("BRAIN_DATA_ROOT", "CUSTOM_STORAGE_PATH", "PRO_DEMO_PATH", "DEFAULT_DEMO_PATH")
    env = {k: v for k, v in os.environ.items() if k not in scrub}
    env.update(
        {
            "FAKE_MEIPASS": str(meipass),
            "FAKE_EXE": str(exe),
            "LOCALAPPDATA": str(local),
            "PYTHONPATH": str(PROJECT_ROOT),
            "KIVY_NO_ARGS": "1",
        }
    )
    env.update(extra_env or {})
    before = _snapshot(install)
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    created = _snapshot(install) - before
    return report, install, local, created


def test_frozen_default_root_is_localappdata_and_the_install_dir_stays_untouched(tmp_path):
    report, install, local, created = _run_frozen(tmp_path)
    root = local / "MacenaCS2Analyzer"

    assert Path(report["BASE_DIR"]) == install
    assert Path(report["USER_DATA_ROOT"]) == root
    assert Path(report["CORE_DB_DIR"]) == root / "db"
    assert Path(report["DATABASE_URL"][len(_SQLITE) :]) == root / "db" / "database.db"
    assert Path(report["HLTV_DATABASE_URL"][len(_SQLITE) :]) == root / "db" / "hltv_metadata.db"
    for key in _PATH_KEYS:
        assert _under(report[key], root), (key, report[key])
    assert created == set(), sorted(created)


def test_frozen_resources_live_under_meipass_programma_dir(tmp_path):
    report, install, _, _ = _run_frozen(tmp_path)
    docs = Path(report["docs"])
    assert docs == install / "_internal" / "Programma_CS2_RENAN" / "data" / "docs"
    assert docs.is_dir()


def test_frozen_brain_root_relocates_the_database_too(tmp_path):
    brain = tmp_path / "brain"
    brain.mkdir()
    report, _, _, created = _run_frozen(tmp_path, {"BRAIN_DATA_ROOT": str(brain)})

    assert Path(report["USER_DATA_ROOT"]) == brain
    assert Path(report["DATABASE_URL"][len(_SQLITE) :]) == brain / "db" / "database.db"
    assert Path(report["MODELS_DIR"]) == brain / "models"
    assert Path(report["LOG_DIR"]) == brain / "logs"
    assert created == set(), sorted(created)


def test_get_resource_path_frozen_mirrors_the_bundle_layout(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.core import config

    monkeypatch.setattr(config, "IS_FROZEN", True)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    resolved = Path(config.get_resource_path(os.path.join("data", "docs")))
    assert resolved == tmp_path / "Programma_CS2_RENAN" / "data" / "docs"


def test_dev_checkout_paths_are_unchanged():
    from Programma_CS2_RENAN.core import config

    if config.IS_FROZEN:
        pytest.skip("dev-checkout contract")
    base = Path(config.BASE_DIR)
    assert Path(config.CORE_DB_DIR) == base / "backend" / "storage"
    assert Path(config.get_resource_path("core")) == base / "core"
    assert Path(config.DATABASE_URL[len(_SQLITE) :]) == base / "backend" / "storage" / "database.db"


def test_frozen_dotenv_is_read_from_the_writable_dir(tmp_path, monkeypatch):
    from Programma_CS2_RENAN.core import config

    monkeypatch.delenv("CS2_TEST_FROZEN_DOTENV", raising=False)
    (tmp_path / ".env").write_text("CS2_TEST_FROZEN_DOTENV=yes\n", encoding="utf-8")
    monkeypatch.setattr(config, "IS_FROZEN", True)
    monkeypatch.setattr(config, "get_writeable_dir", lambda: str(tmp_path))
    try:
        config._load_dotenv_file()
        assert os.environ.get("CS2_TEST_FROZEN_DOTENV") == "yes"
    finally:
        monkeypatch.delenv("CS2_TEST_FROZEN_DOTENV", raising=False)


def test_logger_default_dir_is_writable_when_frozen_and_unconfigured(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.observability import logger_setup

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(logger_setup, "_log_dir", None)
    assert Path(logger_setup._default_log_dir()) == tmp_path / "MacenaCS2Analyzer" / "logs"

    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert logger_setup._default_log_dir() == "logs"

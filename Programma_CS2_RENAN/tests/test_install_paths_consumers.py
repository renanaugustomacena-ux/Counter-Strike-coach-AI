"""Install round (WP4a) — no runtime module composes data paths from BASE_DIR
(the install directory when frozen).  Bundled resources go through
get_resource_path; user-written files live under the writable roots.
"""

from __future__ import annotations

import re
import sys
from dataclasses import asdict, fields
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PKG = PROJECT_ROOT / "Programma_CS2_RENAN"

# config.py defines BASE_DIR; selftest.py only reports it.
_ALLOWED = {"core/config.py", "core/selftest.py"}
_IMPORTS_BASE_DIR = re.compile(
    r"from Programma_CS2_RENAN\.core\.config import \(?[^)\n]*?\bBASE_DIR\b|"
    r"from Programma_CS2_RENAN\.core\.config import \([^)]*\bBASE_DIR\b",
    re.S,
)


def test_no_runtime_module_imports_base_dir_from_config():
    offenders = []
    for path in sorted(PKG.rglob("*.py")):
        rel = path.relative_to(PKG).as_posix()
        if rel.startswith("tests/") or rel in _ALLOWED:
            continue
        if _IMPORTS_BASE_DIR.search(path.read_text(encoding="utf-8", errors="replace")):
            offenders.append(rel)
    assert offenders == []


def test_learned_heuristics_live_beside_the_database(tmp_path, monkeypatch):
    from Programma_CS2_RENAN.backend.processing.feature_engineering import base_features
    from Programma_CS2_RENAN.core import config

    monkeypatch.setattr(config, "CORE_DB_DIR", str(tmp_path))
    first = fields(base_features.HeuristicConfig)[0]
    data = asdict(base_features.HeuristicConfig())
    value = data[first.name]
    if isinstance(value, bool):
        data[first.name] = not value
    elif isinstance(value, (int, float)):
        data[first.name] = value + 1
    else:
        data[first.name] = f"{value}x"
    cfg = base_features.HeuristicConfig.from_dict(data)

    base_features.save_heuristic_config(cfg)

    assert (tmp_path / "heuristic_config.json").is_file()
    assert base_features.load_learned_heuristics() == cfg


def test_alembic_paths_are_the_repo_root_in_dev_and_meipass_when_frozen(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.backend.storage import db_migrate

    ini, scripts = db_migrate._alembic_paths()
    assert Path(ini) == PROJECT_ROOT / "alembic.ini"
    assert Path(scripts) == PROJECT_ROOT / "alembic"
    assert Path(ini).is_file() and Path(scripts).is_dir()

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    ini, scripts = db_migrate._alembic_paths()
    assert Path(ini) == tmp_path / "alembic.ini"
    assert Path(scripts) == tmp_path / "alembic"


def test_storage_manager_fallback_brain_dir_is_the_user_data_root(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.backend.storage import storage_manager

    monkeypatch.setattr(storage_manager, "USER_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(storage_manager, "DATA_DIR", str(tmp_path / "data"))
    unset = {"BRAIN_DATA_ROOT", "DEFAULT_DEMO_PATH", "PRO_DEMO_PATH"}
    monkeypatch.setattr(
        storage_manager,
        "get_setting",
        lambda key, default=None: "" if key in unset else default,
    )

    manager = storage_manager.StorageManager()

    assert manager.brain_dir == tmp_path / "data"
    assert manager.archive_dir == tmp_path / "data" / "archive"
    assert manager.pro_archive_dir == tmp_path / "data" / "pro_archive"

"""Train-in-app round (WP4b) — the episode exporter lives in the package
(the frozen build ships no ``tools/``), re-exports only what changed, and
never opens a console window or spawns git in a frozen build.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from types import SimpleNamespace

import pytest

from Programma_CS2_RENAN.tests.test_export_episodes import _create_test_db, _make_demo_data

pytestmark = pytest.mark.timeout(120)


def _db(tmp_path, demos) -> str:
    path = tmp_path / "monolith.sqlite"
    _create_test_db(str(path), demos)
    return str(path)


def _two_demo_db(tmp_path) -> str:
    return _db(
        tmp_path,
        [_make_demo_data("d1", "PlayerA", "TRAIN"), _make_demo_data("d2", "PlayerB", "VAL")],
    )


def test_second_export_reuses_unchanged_shards_and_full_rewrites_them(tmp_path):
    from Programma_CS2_RENAN.backend.storage import episode_export

    db = _two_demo_db(tmp_path)
    out = tmp_path / "out"

    first = episode_export.export_episodes(out, db_path=db, profile="full")
    assert first.shards == 2 and first.reused == 0
    assert first.by_split == {"train": 1, "val": 1}
    stamps = {p: p.stat().st_mtime_ns for p in out.rglob("*.safetensors")}
    assert len(stamps) == 2

    second = episode_export.export_episodes(out, db_path=db, profile="full")
    assert second.shards == 2 and second.reused == 2
    assert {p: p.stat().st_mtime_ns for p in out.rglob("*.safetensors")} == stamps

    third = episode_export.export_episodes(out, db_path=db, profile="full", full=True)
    assert third.shards == 2 and third.reused == 0


def test_manifest_entries_record_the_shard_size(tmp_path):
    from Programma_CS2_RENAN.backend.storage import episode_export

    db = _two_demo_db(tmp_path)
    out = tmp_path / "out"
    episode_export.export_episodes(out, db_path=db, profile="full")

    manifest = json.loads((out / "train" / "manifest.json").read_text(encoding="utf-8"))
    (entry,) = manifest["demos"]
    assert entry["size"] == (out / "train" / entry["file"]).stat().st_size
    assert manifest["totals"]["n_demos"] == 1


def test_a_demo_that_changed_split_is_moved_and_the_old_shard_parked(tmp_path):
    from Programma_CS2_RENAN.backend.storage import episode_export

    db = _two_demo_db(tmp_path)
    out = tmp_path / "out"
    episode_export.export_episodes(out, db_path=db, profile="full")

    con = sqlite3.connect(db)
    con.execute("UPDATE playermatchstats SET dataset_split = 'VAL' WHERE demo_name = 'd1'")
    con.commit()
    con.close()

    result = episode_export.export_episodes(out, db_path=db, profile="full")

    assert result.by_split == {"val": 2}
    assert result.reused == 1
    assert (out / "val" / "d1.safetensors").exists()
    assert not (out / "train" / "d1.safetensors").exists()
    assert (out / "train" / "_stale" / "d1.safetensors").exists()
    train_manifest = json.loads((out / "train" / "manifest.json").read_text(encoding="utf-8"))
    assert train_manifest["totals"]["n_demos"] == 0


def test_git_sha_never_spawns_git_in_a_frozen_build(monkeypatch):
    from Programma_CS2_RENAN import __version__
    from Programma_CS2_RENAN.backend.storage import episode_export

    monkeypatch.setattr(sys, "frozen", True, raising=False)

    def _boom(*args, **kwargs):
        raise AssertionError("git must not be spawned in a frozen build")

    monkeypatch.setattr(episode_export.subprocess, "run", _boom)
    assert episode_export._git_sha() == f"app-{__version__}"

    monkeypatch.setattr(sys, "frozen", False, raising=False)
    seen: dict = {}

    def _fake_run(cmd, **kwargs):
        seen.update(kwargs)
        return SimpleNamespace(stdout="abc123\n")

    monkeypatch.setattr(episode_export.subprocess, "run", _fake_run)
    assert episode_export._git_sha() == "abc123"
    if os.name == "nt":
        assert seen.get("creationflags") == subprocess.CREATE_NO_WINDOW


def test_the_tool_is_a_thin_wrapper_over_the_package_module():
    from Programma_CS2_RENAN.backend.storage import episode_export
    from tools import export_episodes as tool

    assert tool.run_export is episode_export.run_export
    assert tool.main is episode_export.main
    assert tool._normalize_demo_name is episode_export._normalize_demo_name
    assert tool._wrap_delta_yaw is episode_export._wrap_delta_yaw

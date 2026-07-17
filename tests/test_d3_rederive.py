"""Tests for tools/d3_recover_shard_metadata.py --rederive-v1 (P2-10 follow-up).

The 2026-05-06 recovery run wrote parser_version='v1-d3-recovered' rows with a
HARDCODED tick_rate=64.0. The re-derive mode must fix them from .dem headers
when the file exists and re-mark them honestly (default-rate sentinel) when it
does not — never silently bless a fabricated rate as header-derived.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from tools import d3_recover_shard_metadata as mod


def _make_shard(
    path: Path,
    demo_name: str,
    parser_version: str = mod.V1_RECOVERED,
    tick_rate: float = 64.0,
    with_table: bool = True,
) -> None:
    con = sqlite3.connect(path)
    if with_table:
        con.execute(
            "CREATE TABLE match_metadata (match_id INTEGER, demo_name TEXT, "
            "map_name TEXT, tick_rate REAL, parser_version TEXT)"
        )
        con.execute(
            "INSERT INTO match_metadata VALUES (?, ?, ?, ?, ?)",
            (
                mod.demo_stem_to_match_id(demo_name),
                demo_name,
                "mirage",
                tick_rate,
                parser_version,
            ),
        )
    else:
        con.execute("CREATE TABLE other (x INTEGER)")
    con.commit()
    con.close()


def _read_row(path: Path) -> tuple:
    con = sqlite3.connect(path)
    row = con.execute("SELECT tick_rate, parser_version FROM match_metadata").fetchone()
    con.close()
    return row


@pytest.fixture
def shard_env(tmp_path, monkeypatch):
    demo_base = tmp_path / "DEMO_PRO_PLAYERS"
    match_data = demo_base / "match_data"
    match_data.mkdir(parents=True)
    monkeypatch.setattr(mod, "DEMO_BASE", demo_base)
    monkeypatch.setattr(mod, "MATCH_DATA", match_data)
    return demo_base, match_data


class TestRederiveV1:
    def test_header_rate_when_dem_exists(self, shard_env, tmp_path, monkeypatch):
        demo_base, match_data = shard_env
        shard = match_data / "match_1.db"
        _make_shard(shard, "demo-a-mirage")
        (demo_base / "demo-a-mirage.dem").touch()
        monkeypatch.setattr(mod, "dem_header_tick_rate", lambda p: 128.0)

        result = mod.rederive_v1_rows(apply=True, backup_dir=tmp_path / "bk")

        assert _read_row(shard) == (128.0, mod.V2_RECOVERED)
        assert len(result["header_rederived"]) == 1
        assert result["errors"] == []
        assert (tmp_path / "bk" / "match_1.db").exists()

    def test_marks_default_rate_when_dem_missing(self, shard_env, tmp_path):
        _, match_data = shard_env
        shard = match_data / "match_2.db"
        _make_shard(shard, "demo-b-dust2")

        result = mod.rederive_v1_rows(apply=True, backup_dir=tmp_path / "bk")

        # Rate kept (still 64.0) but the row is re-marked findable, not blessed.
        assert _read_row(shard) == (64.0, mod.V2_DEFAULT_RATE)
        assert len(result["marked_default_rate"]) == 1
        assert result["header_rederived"] == []

    def test_default_rate_row_upgraded_when_dem_reappears(self, shard_env, tmp_path, monkeypatch):
        demo_base, match_data = shard_env
        shard = match_data / "match_3.db"
        _make_shard(shard, "demo-c-nuke", parser_version=mod.V2_DEFAULT_RATE)
        (demo_base / "demo-c-nuke.dem").touch()
        monkeypatch.setattr(mod, "dem_header_tick_rate", lambda p: 127.9)

        result = mod.rederive_v1_rows(apply=True, backup_dir=tmp_path / "bk")

        assert _read_row(shard) == (127.9, mod.V2_RECOVERED)
        assert len(result["header_rederived"]) == 1

    def test_dry_run_writes_nothing(self, shard_env, tmp_path, monkeypatch):
        demo_base, match_data = shard_env
        shard = match_data / "match_4.db"
        _make_shard(shard, "demo-d-inferno")
        (demo_base / "demo-d-inferno.dem").touch()
        monkeypatch.setattr(mod, "dem_header_tick_rate", lambda p: 128.0)

        result = mod.rederive_v1_rows(apply=False, backup_dir=tmp_path / "bk")

        assert _read_row(shard) == (64.0, mod.V1_RECOVERED)
        assert len(result["header_rederived"]) == 1  # classified, not written
        assert not (tmp_path / "bk").exists()

    def test_shard_without_metadata_table_skipped(self, shard_env, tmp_path):
        _, match_data = shard_env
        _make_shard(match_data / "match_5.db", "demo-e-anubis", with_table=False)

        result = mod.rederive_v1_rows(apply=True, backup_dir=tmp_path / "bk")

        assert result["errors"] == []
        assert result["header_rederived"] == []
        assert result["marked_default_rate"] == []

"""Regression tests for R4 MED batch 11 tool fixes."""

import sqlite3

import pytest


class TestRegisterOrphanAggregates:
    """R4 MED: SUM(MAX(kills_this_round)) undercounts (~50% on cross-checked
    matches) because per-round counters are not reliably sampled at their
    round-end peak. MAX(kills_total) is the source of truth."""

    @staticmethod
    def _make_db():
        con = sqlite3.connect(":memory:")
        con.execute(
            """CREATE TABLE matchtickstate (
                player_name TEXT, round_number INT,
                kills_this_round INT, deaths_this_round INT,
                damage_this_round INT, headshot_kills_this_round INT,
                kills_total INT, deaths_total INT, headshot_kills_total INT
            )"""
        )
        # Player with under-sampled per-round counters: the cumulative
        # *_total says 5 kills, but per-round MAX snapshots only saw 2.
        rows = [
            # round 1: got 3 kills, sampled mid-round at 1
            ("pro", 1, 1, 0, 50, 1, 3, 0, 2),
            # round 2: got 2 kills, sampled at 1; totals reach 5
            ("pro", 2, 1, 1, 80, 0, 5, 1, 2),
        ]
        con.executemany("INSERT INTO matchtickstate VALUES (?,?,?,?,?,?,?,?,?)", rows)
        con.commit()
        return con

    def test_totals_come_from_cumulative_counters(self):
        from Programma_CS2_RENAN.tools.register_orphan_matches import _player_aggregates

        con = self._make_db()
        aggs = _player_aggregates(con)
        assert len(aggs) == 1
        agg = aggs[0]
        assert agg.total_kills == 5, "MAX(kills_total), not SUM(MAX(kills_this_round))=2"
        assert agg.total_deaths == 1
        assert agg.total_headshots == 2
        assert agg.total_damage == 130, "damage keeps SUM(MAX(damage_this_round))"
        assert agg.rounds_played == 2


class TestDeadCodeDetectorPhaseC:
    """R4 MED: `alias not in content` was always False (the import line
    contains the alias) — Phase C could never report anything."""

    def test_detects_truly_unused_import(self, tmp_path):
        import tools.dead_code_detector as dcd

        f = tmp_path / "mod_with_stale.py"
        f.write_text("import os\nimport json\n\nprint(os.getcwd())\n", encoding="utf-8")
        reports = dcd.scan_stale_imports([f])
        joined = " ".join(reports)
        assert "json" in joined, "stale import must be reported"
        assert "'os'" not in joined, "used import must not be reported"

    def test_future_and_star_imports_skipped(self, tmp_path):
        import tools.dead_code_detector as dcd

        f = tmp_path / "mod_future.py"
        f.write_text(
            "from __future__ import annotations\nfrom os.path import *\n\nx: int = 1\n",
            encoding="utf-8",
        )
        reports = dcd.scan_stale_imports([f])
        assert reports == [], f"__future__/star imports are not reportable: {reports}"

    def test_string_usage_is_safe(self, tmp_path):
        import tools.dead_code_detector as dcd

        f = tmp_path / "mod_all.py"
        f.write_text('from mypkg import helper\n\n__all__ = ["helper"]\n', encoding="utf-8")
        assert dcd.scan_stale_imports([f]) == []


class TestToolingCompiles:
    """Task #8: the headless validator's AST checks cover only the package
    root, so a SyntaxError in tools/, evals/ or a root script would sit
    unnoticed until someone launched it. This gate parses every one of them
    in-suite (and therefore in CI on both platforms)."""

    def test_all_tool_and_root_scripts_parse(self):
        import ast
        from pathlib import Path

        project_root = Path(__file__).resolve().parents[2]
        targets: list[Path] = []
        for rel in ("tools", "Programma_CS2_RENAN/tools", "evals"):
            targets.extend(sorted((project_root / rel).rglob("*.py")))
        targets.extend(sorted(project_root.glob("*.py")))

        targets = [t for t in targets if "__pycache__" not in t.parts]
        assert len(targets) >= 70, (
            f"only {len(targets)} scripts collected — the tooling tree moved; "
            "update the target list instead of letting the gate go hollow"
        )

        failures = []
        for f in targets:
            try:
                ast.parse(f.read_text(encoding="utf-8", errors="replace"), filename=str(f))
            except SyntaxError as exc:
                failures.append(f"{f.relative_to(project_root)}: {exc}")
        assert not failures, "tooling scripts with syntax errors:\n" + "\n".join(failures)


class TestDeriveWinnerFromRoundstats:
    """Pass-2 finding: the old derivation guessed winner = filename team_a
    whenever the CT-start group won more rounds — nothing in the DB links a
    starting side to a team name, so ~half of all recorded winners were
    fabricated. The outcome is now reported per starting side only, and the
    group score is the MAX across its players (robust to substitutes)."""

    @staticmethod
    def _make_db(rows):
        import sqlite3

        con = sqlite3.connect(":memory:")
        con.execute(
            """CREATE TABLE roundstats (
                demo_name TEXT, player_name TEXT, side TEXT,
                round_won INT, round_number INT
            )"""
        )
        con.executemany("INSERT INTO roundstats VALUES (?,?,?,?,?)", rows)
        con.commit()
        return con

    def test_winner_is_a_side_label_never_a_team_name(self):
        import importlib

        pmr = importlib.import_module("tools.populate_match_results")
        # 2 CT-start players win 3 rounds, 2 T-start players win 1
        rows = []
        for rnd in range(1, 5):
            ct_won = rnd <= 3
            for p in ("ct1", "ct2"):
                rows.append(("d", p, "CT", int(ct_won), rnd))
            for p in ("t1", "t2"):
                rows.append(("d", p, "T", int(not ct_won), rnd))
        con = self._make_db(rows)
        ct, t, winner = pmr.derive_winner_from_roundstats(con, "d")
        assert (ct, t, winner) == (3, 1, "CT_start")

    def test_substitute_with_partial_rounds_does_not_shrink_score(self):
        import importlib

        pmr = importlib.import_module("tools.populate_match_results")
        rows = []
        for rnd in range(1, 5):  # CT-start wins all 4
            rows.append(("d", "ct_full", "CT", 1, rnd))
            rows.append(("d", "t_full", "T", 0, rnd))
        # substitute only played (and won) round 4 — dict order puts them first
        rows.insert(0, ("d", "ct_sub", "CT", 1, 4))
        con = self._make_db(rows)
        ct, t, winner = pmr.derive_winner_from_roundstats(con, "d")
        assert ct == 4, "group score must be the max across players, not the first player's"
        assert winner == "CT_start"

    def test_draw_and_empty(self):
        import importlib

        pmr = importlib.import_module("tools.populate_match_results")
        rows = [
            ("d", "a", "CT", 1, 1),
            ("d", "b", "T", 0, 1),
            ("d", "a", "CT", 0, 2),
            ("d", "b", "T", 1, 2),
        ]
        con = self._make_db(rows)
        assert pmr.derive_winner_from_roundstats(con, "d") == (1, 1, "draw")
        assert pmr.derive_winner_from_roundstats(con, "missing") == (None, None, None)


class TestRepairTickFeaturesJoin:
    """Pass-2 finding: the repair temp table lower+strips player names but
    the monolith stores the ORIGINAL parser case ("ZywOo", "apEX") — the old
    exact join silently skipped every mixed-case player, leaving their
    is_crouching/is_blinded/has_helmet/has_defuser (all four are 25-dim
    training features) broken while reporting success."""

    def test_mixed_case_players_are_repaired(self):
        import importlib
        import sqlite3

        rtf = importlib.import_module("tools.repair_tick_features")

        con = sqlite3.connect(":memory:")
        con.execute(
            """CREATE TABLE playertickstate (
                demo_name TEXT, player_name TEXT, tick INT,
                is_crouching INT, is_blinded INT, has_helmet INT, has_defuser INT
            )"""
        )
        con.executemany(
            "INSERT INTO playertickstate VALUES (?,?,?,?,?,?,?)",
            [
                ("d", "ZywOo", 100, 0, 0, 0, 0),  # mixed case — the bug victim
                ("d", "ropz", 100, 0, 0, 0, 0),  # already lowercase
                ("other", "ZywOo", 100, 0, 0, 0, 0),  # other demo untouched
            ],
        )
        con.execute(
            "CREATE TEMP TABLE _repair (player_name TEXT, tick INT, "
            "_cr INT, _bl INT, _hm INT, _df INT)"
        )
        con.executemany(
            "INSERT INTO _repair VALUES (?,?,?,?,?,?)",
            [("zywoo", 100, 1, 1, 1, 1), ("ropz", 100, 1, 0, 1, 0)],
        )

        available = {
            "is_crouching": "_cr",
            "is_blinded": "_bl",
            "has_helmet": "_hm",
            "has_defuser": "_df",
        }
        rtf._run_repair_update(con, "d", available)

        rows = {
            r[0]: r[1:]
            for r in con.execute(
                "SELECT player_name, is_crouching, is_blinded, has_helmet, has_defuser "
                "FROM playertickstate WHERE demo_name='d'"
            )
        }
        assert rows["ZywOo"] == (1, 1, 1, 1), "mixed-case player must be repaired"
        assert rows["ropz"] == (1, 0, 1, 0)
        other = con.execute(
            "SELECT is_crouching FROM playertickstate WHERE demo_name='other'"
        ).fetchone()
        assert other == (0,), "other demos must stay untouched"

    def test_partial_field_set_updates_only_available_columns(self):
        import importlib
        import sqlite3

        rtf = importlib.import_module("tools.repair_tick_features")

        con = sqlite3.connect(":memory:")
        con.execute(
            """CREATE TABLE playertickstate (
                demo_name TEXT, player_name TEXT, tick INT,
                is_crouching INT, is_blinded INT, has_helmet INT, has_defuser INT
            )"""
        )
        con.execute("INSERT INTO playertickstate VALUES ('d', 'apEX', 5, 0, 0, 9, 9)")
        con.execute("CREATE TEMP TABLE _repair (player_name TEXT, tick INT, _cr INT)")
        con.execute("INSERT INTO _repair VALUES ('apex', 5, 1)")

        rtf._run_repair_update(con, "d", {"is_crouching": "_cr"})

        row = con.execute(
            "SELECT is_crouching, has_helmet, has_defuser FROM playertickstate"
        ).fetchone()
        assert row == (1, 9, 9), "columns without parser data must not be touched"


class TestWipeRestoreClearsStaleWal:
    """Pass-2 finding: restore extracted the snapshot .db but left the
    CURRENT -wal/-shm sidecars in place — SQLite would replay a
    post-snapshot WAL on top of the restored file, silently mixing two
    database states."""

    def test_restore_removes_current_wal_and_shm(self, tmp_path, monkeypatch):
        import importlib
        import sqlite3
        import tarfile

        wrs = importlib.import_module("tools.wipe_for_reingest_safe")
        monkeypatch.setenv(wrs.ENV_KEY_NAME, "test-key-for-restore")

        # Snapshot state: a clean checkpointed DB (no wal/shm members)
        db = tmp_path / "database.db"
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE t (x INT)")
        con.execute("INSERT INTO t VALUES (1)")
        con.commit()
        con.close()

        tar_path = tmp_path / "snapshot.tar"
        with tarfile.open(tar_path, "w") as tar:
            tar.add(db, arcname=db.name)
        sealed = tmp_path / "snapshot.tar.sealed"
        wrs._seal_snapshot(tar_path, sealed, b"test-key-for-restore")

        # Post-snapshot state: DB moved on AND has live-looking sidecars
        con = sqlite3.connect(db)
        con.execute("INSERT INTO t VALUES (2)")
        con.commit()
        con.close()
        stale_wal = tmp_path / "database.db-wal"
        stale_shm = tmp_path / "database.db-shm"
        stale_wal.write_bytes(b"stale wal bytes")
        stale_shm.write_bytes(b"stale shm bytes")

        rc = wrs._restore(sealed, db, confirm=True, dry_run=False)
        assert rc == 0

        assert not stale_wal.exists(), "current WAL must be removed before extract"
        assert not stale_shm.exists(), "current SHM must be removed before extract"
        con = sqlite3.connect(db)
        rows = [r[0] for r in con.execute("SELECT x FROM t ORDER BY x")]
        con.close()
        assert rows == [1], f"restored DB must be the snapshot state, got {rows}"

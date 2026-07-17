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

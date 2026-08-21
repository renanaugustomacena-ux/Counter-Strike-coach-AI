"""OI-2 — backfill tool + ingestion wiring for match_date provenance."""

import importlib.util
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "backfill_match_dates_under_test", REPO_ROOT / "tools" / "backfill_match_dates.py"
)
backfill = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backfill)


def _make_monolith(tmp_path):
    db = tmp_path / "database.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE playermatchstats (id INTEGER PRIMARY KEY, demo_name TEXT, "
            "match_date TEXT, match_date_source TEXT)"
        )
        conn.executemany(
            "INSERT INTO playermatchstats (demo_name, match_date, match_date_source) "
            "VALUES (?, ?, ?)",
            [
                ("2023-vitality-vs-mouz-m1-nuke", "2026-05-08T10:00:00+00:00", "ingested_at"),
                ("demo_mirage_20240615", "2026-05-08T10:00:01+00:00", None),
                ("no-date-anywhere", "2026-05-08T10:00:02+00:00", "ingested_at"),
                ("already-real", "2024-01-05T00:00:00+00:00", "filename_date"),
            ],
        )
    return db


class TestBackfillTool:
    def test_dry_run_reports_and_writes_nothing(self, tmp_path, monkeypatch, capsys):
        db = _make_monolith(tmp_path)
        monkeypatch.setattr(backfill, "HLTV_DB", tmp_path / "absent.db")
        monkeypatch.setattr("sys.argv", ["backfill_match_dates.py", "--db", str(db)])
        assert backfill.main() == 0
        out = capsys.readouterr().out
        assert "Upgradable rows: 2" in out  # year-prefix + yyyymmdd rows
        with sqlite3.connect(db) as conn:
            src = conn.execute(
                "SELECT match_date_source FROM playermatchstats WHERE demo_name LIKE '2023-%'"
            ).fetchone()[0]
        assert src == "ingested_at"  # untouched in dry-run

    def test_apply_upgrades_only_weak_sources(self, tmp_path, monkeypatch):
        db = _make_monolith(tmp_path)
        monkeypatch.setattr(backfill, "HLTV_DB", tmp_path / "absent.db")
        monkeypatch.setattr("sys.argv", ["backfill_match_dates.py", "--db", str(db), "--apply"])
        assert backfill.main() == 0
        with sqlite3.connect(db) as conn:
            rows = dict(conn.execute("SELECT demo_name, match_date_source FROM playermatchstats"))
        assert rows["2023-vitality-vs-mouz-m1-nuke"] == "filename_year"
        assert rows["demo_mirage_20240615"] == "filename_date"
        assert rows["no-date-anywhere"] == "ingested_at"
        assert rows["already-real"] == "filename_date"  # never downgraded
        with sqlite3.connect(db) as conn:
            date = conn.execute(
                "SELECT match_date FROM playermatchstats WHERE demo_name = '2023-vitality-vs-mouz-m1-nuke'"
            ).fetchone()[0]
        assert date.startswith("2023-01-01")

    def test_hltv_event_rung_unique_containment(self, tmp_path, monkeypatch):
        hltv = tmp_path / "hltv_metadata.db"
        with sqlite3.connect(hltv) as conn:
            conn.execute("CREATE TABLE proevent (name TEXT, start_date TEXT)")
            conn.executemany(
                "INSERT INTO proevent VALUES (?, ?)",
                [
                    ("IEM Katowice 2025", "2025-02-01T00:00:00+00:00"),
                    ("BLAST Premier Fall 2025", "2025-09-10T00:00:00+00:00"),
                ],
            )
        monkeypatch.setattr(backfill, "HLTV_DB", hltv)
        events = backfill._load_event_dates()
        assert len(events) == 2
        dt = backfill._hltv_event_date("vitality-vs-spirit-iem-katowice-2025-m1", events)
        assert dt is not None and dt.year == 2025 and dt.month == 2
        assert backfill._hltv_event_date("some-random-demo", events) is None


class TestIngestionWiring:
    def test_save_player_stats_carries_provenance(self):
        from Programma_CS2_RENAN import run_ingestion

        captured = {}

        class _StubDB:
            def upsert(self, obj):
                captured["obj"] = obj

        row = pd.Series(
            {
                "player_name": "tester",
                "avg_kills": 0.7,
                "avg_deaths": 0.6,
            }
        )
        when = datetime(2024, 6, 15, tzinfo=timezone.utc)
        run_ingestion._save_player_stats(
            _StubDB(),
            row,
            "demo_mirage_20240615.dem",
            is_pro=False,
            match_date=when,
            match_date_source="filename_date",
        )
        obj = captured["obj"]
        assert obj.match_date == when
        assert obj.match_date_source == "filename_date"

    def test_save_player_stats_defaults_stay_honest(self):
        from Programma_CS2_RENAN import run_ingestion

        captured = {}

        class _StubDB:
            def upsert(self, obj):
                captured["obj"] = obj

        row = pd.Series({"player_name": "tester", "avg_kills": 0.5})
        run_ingestion._save_player_stats(_StubDB(), row, "x.dem", is_pro=False)
        assert captured["obj"].match_date_source == "ingested_at"

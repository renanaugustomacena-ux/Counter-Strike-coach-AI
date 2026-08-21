"""F-0020 — elite CSV builder + EliteAnalytics per-component degradation."""

import importlib.util
import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "build_elite_csvs_under_test", REPO_ROOT / "tools" / "build_elite_csvs.py"
)
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)


@pytest.fixture
def fixture_dbs(tmp_path, monkeypatch):
    """Minimal hltv_metadata.db + database.db with 3 stat cards / 4 pro rows."""
    hltv = tmp_path / "hltv_metadata.db"
    with sqlite3.connect(hltv) as conn:
        conn.execute("CREATE TABLE proplayer (hltv_id INTEGER, nickname TEXT)")
        conn.execute(
            "CREATE TABLE proplayerstatcard (player_id INTEGER, rating_2_0 REAL, "
            "kpr REAL, dpr REAL, adr REAL, headshot_pct REAL, kast REAL, "
            "impact REAL, time_span TEXT)"
        )
        conn.executemany(
            "INSERT INTO proplayer VALUES (?, ?)",
            [(1, "ZywOo"), (2, "donk"), (3, "m0NESY")],
        )
        conn.executemany(
            "INSERT INTO proplayerstatcard VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, 1.32, 0.82, 0.60, 86.1, 0.41, 0.74, 1.28, "all_time"),
                (2, 1.29, 0.85, 0.63, 88.0, 0.48, 0.72, 1.35, "all_time"),
                (3, 1.21, 0.79, 0.61, 82.5, 0.52, 0.73, 1.18, "all_time"),
            ],
        )

    mono = tmp_path / "database.db"
    with sqlite3.connect(mono) as conn:
        conn.execute(
            "CREATE TABLE playermatchstats (player_name TEXT, demo_name TEXT, "
            "avg_adr REAL, avg_deaths REAL, avg_kills REAL, rating REAL, "
            "avg_hs REAL, accuracy REAL, econ_rating REAL, is_pro INTEGER)"
        )
        conn.executemany(
            "INSERT INTO playermatchstats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("ZywOo", "vit-vs-tm-m1", 90.0, 0.55, 0.90, 1.40, 0.40, 0.24, 1.2, 1),
                ("donk", "spirit-vs-faze-m2", 95.0, 0.60, 0.95, 1.45, 0.50, 0.26, 1.3, 1),
                ("apEX", "vit-vs-tm-m1", 70.0, 0.70, 0.65, 0.98, 0.55, 0.19, 0.9, 1),
                ("casual", "user-demo", 60.0, 0.75, 0.55, 0.85, 0.35, 0.15, 0.8, 0),
            ],
        )

    monkeypatch.setattr(builder, "HLTV_DB", hltv)
    monkeypatch.setattr(builder, "MONOLITH_DB", mono)
    return tmp_path


class TestBuilder:
    def test_hltv_csvs_written_with_percent_styling(self, fixture_dbs, tmp_path):
        out = tmp_path / "out"
        builder.build_hltv_csvs(out, apply=True)
        best = (out / "all_Time_best_Players_Stats.csv").read_text().splitlines()
        assert best[0] == "Name,Rating1.0,K/D,ADR,Headshot %,KAST,Impact"
        zywoo = best[1].split(",")
        assert zywoo[0] == "ZywOo"
        assert float(zywoo[4]) == pytest.approx(41.0)  # ratio 0.41 -> percent
        assert float(zywoo[5]) == pytest.approx(74.0)

        top = (out / "top_100_players.csv").read_text().splitlines()
        assert top[0] == "Name,CS Rating"
        assert top[1].startswith("ZywOo,")  # highest rating first

    def test_demo_csvs_only_pro_rows(self, fixture_dbs, tmp_path):
        out = tmp_path / "out"
        builder.build_demo_csvs(out, apply=True)
        match = (out / "match_players.csv").read_text()
        assert "casual" not in match  # is_pro=0 excluded
        assert "ZywOo" in match
        tourn = (out / "tournament_advanced_stats.csv").read_text().splitlines()
        assert tourn[0] == "accuracy,econ_rating"
        assert len(tourn) == 4  # header + 3 pro rows

    def test_dry_run_writes_nothing(self, fixture_dbs, tmp_path):
        out = tmp_path / "out"
        builder.build_hltv_csvs(out, apply=False)
        builder.build_demo_csvs(out, apply=False)
        assert not out.exists()

    def test_missing_dbs_skip_cleanly(self, tmp_path, monkeypatch):
        monkeypatch.setattr(builder, "HLTV_DB", tmp_path / "nope1.db")
        monkeypatch.setattr(builder, "MONOLITH_DB", tmp_path / "nope2.db")
        out = tmp_path / "out"
        builder.build_hltv_csvs(out, apply=True)
        builder.build_demo_csvs(out, apply=True)
        assert not out.exists()


class TestEliteAnalyticsRoundTrip:
    def _analytics_from(self, directory, monkeypatch):
        import Programma_CS2_RENAN.backend.processing.external_analytics as ea

        monkeypatch.setattr(ea, "get_resource_path", lambda rel: str(directory / Path(rel).name))
        return ea.EliteAnalytics()

    def test_builder_output_feeds_analytics(self, fixture_dbs, tmp_path, monkeypatch):
        out = tmp_path / "external"
        builder.build_hltv_csvs(out, apply=True)
        builder.build_demo_csvs(out, apply=True)
        analytics = self._analytics_from(out, monkeypatch)
        assert analytics.is_healthy()
        result = analytics.analyze_user_vs_elite(
            {"adr": 75.0, "rating": 1.0, "accuracy": 0.2, "econ_rating": 1.0}
        )
        assert result["elite_rating_avg"] > 1.0
        assert "adr" in result["z_scores"]
        assert "accuracy" in result["tournament_z_scores"]

    def test_per_component_degradation_without_top100(self, fixture_dbs, tmp_path, monkeypatch):
        out = tmp_path / "external"
        builder.build_demo_csvs(out, apply=True)  # tournament + match only
        analytics = self._analytics_from(out, monkeypatch)
        assert analytics.is_healthy()
        result = analytics.analyze_user_vs_elite(
            {"adr": 75.0, "rating": 1.0, "accuracy": 0.2, "econ_rating": 1.0}
        )
        # F-0020: missing top_100 must NOT blank the other components.
        assert result["elite_rating_avg"] == 0
        assert "adr" in result["z_scores"]
        assert "accuracy" in result["tournament_z_scores"]

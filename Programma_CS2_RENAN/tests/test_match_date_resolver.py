"""OI-2 — match-date resolution ladder + provenance markers."""

import os
import time
from datetime import datetime, timezone

from Programma_CS2_RENAN.backend.ingestion.match_date_resolver import (
    CHRONOLOGICAL_SOURCES,
    SOURCE_FILE_MTIME,
    SOURCE_FILENAME_DATE,
    SOURCE_FILENAME_YEAR,
    SOURCE_INGESTED_AT,
    resolve_match_date,
)


class TestResolutionLadder:
    def test_yyyymmdd_token_wins(self):
        dt, src = resolve_match_date("demo_mirage_20240615")
        assert src == SOURCE_FILENAME_DATE
        assert (dt.year, dt.month, dt.day) == (2024, 6, 15)
        assert dt.tzinfo == timezone.utc

    def test_hltv_year_prefix_is_coarse(self):
        dt, src = resolve_match_date("2023-natus-vincere-vs-faze-m1-inferno")
        assert src == SOURCE_FILENAME_YEAR
        assert (dt.year, dt.month, dt.day) == (2023, 1, 1)

    def test_invalid_date_token_falls_through(self):
        # 20241399 is 8 digits but not a valid date -> year prefix absent ->
        # no path -> ingested_at.
        dt, src = resolve_match_date("demo_20241399_x")
        assert src == SOURCE_INGESTED_AT

    def test_file_mtime_rung(self, tmp_path):
        dem = tmp_path / "vitality-vs-mouz-m2-nuke.dem"
        dem.write_bytes(b"PBDEMS2")
        stamp = time.mktime((2025, 3, 10, 12, 0, 0, 0, 0, -1))
        os.utime(dem, (stamp, stamp))
        dt, src = resolve_match_date("vitality-vs-mouz-m2-nuke", dem)
        assert src == SOURCE_FILE_MTIME
        assert dt.year == 2025

    def test_ingested_at_is_the_honest_floor(self):
        before = datetime.now(timezone.utc)
        dt, src = resolve_match_date("no-date-here")
        assert src == SOURCE_INGESTED_AT
        assert dt >= before

    def test_chronological_sources_marker_set(self):
        assert SOURCE_FILENAME_DATE in CHRONOLOGICAL_SOURCES
        assert SOURCE_FILENAME_YEAR in CHRONOLOGICAL_SOURCES
        assert SOURCE_INGESTED_AT not in CHRONOLOGICAL_SOURCES
        assert SOURCE_FILE_MTIME not in CHRONOLOGICAL_SOURCES

    def test_absurd_years_rejected(self):
        _, src = resolve_match_date("1999-old-vs-ancient-m1-dust")
        assert src == SOURCE_INGESTED_AT

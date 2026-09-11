"""Player-name normalisation tests (§2.4, D-08).

Covers ``normalize_player_name``, ``resolve_stored_names`` (in-memory
SQLite), ``resolve_name``, and the collision-warning path.
"""

from __future__ import annotations

import logging
import sqlite3

from Programma_CS2_RENAN.backend.storage.naming import (
    normalize_player_name,
    resolve_name,
    resolve_stored_names,
)

# ---------------------------------------------------------------------------
# normalize_player_name
# ---------------------------------------------------------------------------


class TestNormalizePlayerName:
    def test_strip_and_casefold(self):
        assert normalize_player_name("  ZywOo  ") == "zywoo"

    def test_casefold_not_lower(self):
        assert normalize_player_name("Straße") == "strasse"

    def test_none_returns_empty(self):
        assert normalize_player_name(None) == ""

    def test_nan_returns_empty(self):
        assert normalize_player_name(float("nan")) == ""

    def test_numeric_converts(self):
        assert normalize_player_name(42) == "42"

    def test_idempotent(self):
        raw = "  Art "
        once = normalize_player_name(raw)
        twice = normalize_player_name(once)
        assert once == twice == "art"

    def test_empty_string(self):
        assert normalize_player_name("") == ""

    def test_leading_space(self):
        assert normalize_player_name(" saffee") == "saffee"

    def test_unicode_casefold(self):
        assert normalize_player_name("FİNAL") == "fi̇nal"


# ---------------------------------------------------------------------------
# resolve_stored_names — in-memory SQLite
# ---------------------------------------------------------------------------


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE playermatchstats ("
        "  player_name TEXT NOT NULL,"
        "  demo_name   TEXT NOT NULL"
        ")"
    )
    conn.execute(
        "CREATE TABLE playertickstate ("
        "  player_name TEXT NOT NULL,"
        "  demo_name   TEXT NOT NULL,"
        "  tick         INTEGER NOT NULL"
        ")"
    )
    return conn


class TestResolveStoredNames:
    def test_basic_mapping(self):
        conn = _make_db()
        conn.execute("INSERT INTO playermatchstats VALUES (?, ?)", ("ZywOo", "demo1.dem"))
        m = resolve_stored_names(conn, "demo1.dem")
        assert m == {"zywoo": "ZywOo"}

    def test_fallback_to_playertickstate(self):
        conn = _make_db()
        conn.execute(
            "INSERT INTO playertickstate VALUES (?, ?, ?)",
            ("Art", "demo2.dem", 100),
        )
        m = resolve_stored_names(conn, "demo2.dem")
        assert m == {"art": "Art"}

    def test_no_fallback_when_pms_has_rows(self):
        conn = _make_db()
        conn.execute("INSERT INTO playermatchstats VALUES (?, ?)", ("ZywOo", "d.dem"))
        conn.execute(
            "INSERT INTO playertickstate VALUES (?, ?, ?)",
            ("GHOST", "d.dem", 1),
        )
        m = resolve_stored_names(conn, "d.dem")
        assert "ghost" not in m
        assert m == {"zywoo": "ZywOo"}

    def test_empty_demo_returns_empty(self):
        conn = _make_db()
        assert resolve_stored_names(conn, "no-such.dem") == {}

    def test_collision_keeps_first(self):
        conn = _make_db()
        conn.execute("INSERT INTO playermatchstats VALUES (?, ?)", ("Art", "d.dem"))
        conn.execute("INSERT INTO playermatchstats VALUES (?, ?)", (" art", "d.dem"))
        m = resolve_stored_names(conn, "d.dem")
        assert m["art"] == "Art"

    def test_collision_emits_warning(self, caplog):
        lg = logging.getLogger("cs2analyzer.storage.naming")
        old_propagate = lg.propagate
        try:
            lg.propagate = True
            conn = _make_db()
            conn.execute("INSERT INTO playermatchstats VALUES (?, ?)", ("Art", "d.dem"))
            conn.execute(
                "INSERT INTO playermatchstats VALUES (?, ?)",
                (" art", "d.dem"),
            )
            with caplog.at_level(logging.WARNING):
                resolve_stored_names(conn, "d.dem")
            assert any("Collision" in r.message for r in caplog.records)
        finally:
            lg.propagate = old_propagate

    def test_limit_bounded(self):
        conn = _make_db()
        for i in range(100):
            conn.execute(
                "INSERT INTO playertickstate VALUES (?, ?, ?)",
                (f"player_{i:03d}", "big.dem", i),
            )
        m = resolve_stored_names(conn, "big.dem")
        assert len(m) <= 64


# ---------------------------------------------------------------------------
# resolve_name
# ---------------------------------------------------------------------------


class TestResolveName:
    def test_found(self):
        mapping = {"art": "Art"}
        assert resolve_name(mapping, " Art ") == "Art"

    def test_miss_returns_normalised(self):
        mapping = {"art": "Art"}
        assert resolve_name(mapping, "donk") == "donk"

    def test_none_input(self):
        assert resolve_name({}, None) == ""

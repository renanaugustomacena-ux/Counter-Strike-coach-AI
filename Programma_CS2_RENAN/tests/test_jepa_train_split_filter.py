"""DOCTRINE D-15 regression — the CLI pretrain loaders must honor the split.

``jepa_train``'s loaders used to select ALL pro/user (demo, player) pairs —
including VAL- and TEST-split matches — bypassing the P4-A chronological
split machinery entirely (Law II), with engine-dependent row order (DET-01
gap). These tests run the REAL SQL against a real SQLite file seeded with
mixed-split rows.
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pytest

from Programma_CS2_RENAN.backend.nn import jepa_train as jt


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    db_path = tmp_path / "monolith.db"
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE TABLE playermatchstats ("
        "demo_name TEXT, player_name TEXT, is_pro INTEGER, "
        "sample_weight REAL, dataset_split TEXT, match_date TEXT)"
    )
    rows = [
        ("pro-train-a", "p1", 1, 1.0, "train", "2026-01-01"),
        ("pro-train-b", "p2", 1, 1.0, "train", "2026-01-02"),
        ("pro-val", "p3", 1, 1.0, "val", "2026-01-03"),
        ("pro-test", "p4", 1, 1.0, "test", "2026-01-04"),
        ("pro-legacy-null", "p5", 1, 1.0, None, "2026-01-05"),
        ("pro-ghost", "p6", 1, 0.0, "train", "2026-01-06"),
        ("user-train", "me", 0, 1.0, "train", "2026-02-01"),
        ("user-val", "me", 0, 1.0, "val", "2026-02-02"),
    ]
    con.executemany("INSERT INTO playermatchstats VALUES (?,?,?,?,?,?)", rows)
    con.commit()
    con.close()

    monkeypatch.setattr(jt, "_open_db", lambda: sqlite3.connect(db_path))
    # The loaders fetch per-pair tick sequences afterwards; stub with a
    # nonzero array so every selected pair survives (the SQL is under test).
    monkeypatch.setattr(
        jt, "_load_tick_sequence", lambda demo, player: np.ones((25, 25), dtype=np.float32)
    )
    return db_path


class TestSplitFilter:
    def test_pro_loader_selects_only_train_split(self, seeded_db):
        seqs = jt.load_pro_demo_sequences(limit=100)
        # 2 TRAIN rows only: val/test excluded (Law II), NULL legacy split
        # ineligible (honestly unknown, never assumed TRAIN), ghost
        # (sample_weight=0) excluded as before.
        assert len(seqs) == 2

    def test_user_loader_selects_only_train_split(self, seeded_db):
        X, y = jt.load_user_match_sequences(limit=100)
        assert X is not None
        assert len(X) == 1  # user-val excluded

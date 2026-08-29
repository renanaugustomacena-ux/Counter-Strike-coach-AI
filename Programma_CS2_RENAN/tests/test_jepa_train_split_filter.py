"""DOCTRINE D-15/D-15b regression — the CLI pretrain loaders must honor the split.

D-15: ``jepa_train``'s loaders used to select ALL pro/user (demo, player)
pairs — including VAL- and TEST-split matches — bypassing the P4-A
chronological split machinery entirely (Law II), with engine-dependent row
order (DET-01 gap).

D-15b (verification round 2): SQLAlchemy's Enum column stores the enum NAME
(``'TRAIN'``) on disk, not the value (``'train'``) — the first D-15 fix
filtered by value and matched ZERO rows on real databases. The loaders now
filter case-insensitively with the literal derived from the DatasetSplit
SSOT. The lockstep test below writes a row THROUGH the ORM and reads it
back through the raw-SQL loader, so any future change to the on-disk
representation fails here loudly instead of silently emptying the corpus.
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
    # D-15b: 'TRAIN'/'VAL'/'TEST' (uppercase enum NAMES) are the REAL
    # on-disk representation SQLAlchemy's Enum column writes — verified
    # against a production database. One lowercase row is kept to pin the
    # case-insensitive tolerance for any historical raw-writer rows.
    rows = [
        ("pro-train-a", "p1", 1, 1.0, "TRAIN", "2026-01-01"),
        ("pro-train-b", "p2", 1, 1.0, "TRAIN", "2026-01-02"),
        ("pro-train-legacy-lower", "p3", 1, 1.0, "train", "2026-01-03"),
        ("pro-val", "p4", 1, 1.0, "VAL", "2026-01-04"),
        ("pro-test", "p5", 1, 1.0, "TEST", "2026-01-05"),
        ("pro-legacy-null", "p6", 1, 1.0, None, "2026-01-06"),
        ("pro-ghost", "p7", 1, 0.0, "TRAIN", "2026-01-07"),
        ("user-train", "me", 0, 1.0, "TRAIN", "2026-02-01"),
        ("user-val", "me", 0, 1.0, "VAL", "2026-02-02"),
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
        # 2 uppercase TRAIN + 1 lowercase legacy 'train' (tolerated);
        # VAL/TEST excluded (Law II), NULL ineligible (honestly unknown,
        # never assumed TRAIN), ghost (sample_weight=0) excluded as before.
        assert len(seqs) == 3

    def test_user_loader_selects_only_train_split(self, seeded_db):
        X, y = jt.load_user_match_sequences(limit=100)
        assert X is not None
        assert len(X) == 1  # user-val excluded


class TestOnDiskRepresentationLockstep:
    """D-15b: pin the ACTUAL format the ORM writes, end to end."""

    def test_orm_written_row_is_visible_to_raw_loader(self, tmp_path, monkeypatch):
        from sqlmodel import Session, SQLModel, create_engine

        from Programma_CS2_RENAN.backend.storage.db_models import DatasetSplit, PlayerMatchStats

        db_path = tmp_path / "orm.db"
        engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as s:
            s.add(
                PlayerMatchStats(
                    demo_name="orm-demo",
                    player_name="p1",
                    is_pro=True,
                    sample_weight=1.0,
                    dataset_split=DatasetSplit.TRAIN,
                )
            )
            s.commit()

        # Ground truth: what did SQLAlchemy actually store?
        con = sqlite3.connect(db_path)
        stored = con.execute("SELECT dataset_split FROM playermatchstats").fetchone()[0]
        con.close()
        assert stored == DatasetSplit.TRAIN.name, (
            "SQLAlchemy's on-disk representation changed — update the "
            "jepa_train raw-SQL filters (D-15b) in the same commit"
        )

        # And the raw loader must see the ORM-written row.
        monkeypatch.setattr(jt, "_open_db", lambda: sqlite3.connect(db_path))
        monkeypatch.setattr(
            jt, "_load_tick_sequence", lambda demo, player: np.ones((25, 25), dtype=np.float32)
        )
        assert len(jt.load_pro_demo_sequences(limit=10)) == 1

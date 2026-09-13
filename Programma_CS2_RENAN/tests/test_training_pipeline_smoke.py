"""Train-in-app round (WP4b) — the in-app training cycle is the developer's
jepa_v2 run as one function: assign splits, export shards, train, register.

Runs on a private file-backed monolith (the exporter reads SQLite directly)
with tiny model dimensions; the models root is isolated by conftest.
"""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from Programma_CS2_RENAN.tests.jepa_v2_synth import TINY_CONFIG_OVERRIDES

pytestmark = pytest.mark.timeout(240)

_T0 = datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc)


class _FileDB:
    """DatabaseManager stand-in on a real SQLite file (the exporter opens it read-only)."""

    def __init__(self, path: Path):
        self.path = path
        self.engine = create_engine(f"sqlite:///{path}")
        SQLModel.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self, engine_key: str = "default"):
        with Session(self.engine, expire_on_commit=False) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise


class _FakeState:
    def __init__(self):
        self.statuses: list[tuple[str, str, str]] = []
        self.progress: list[tuple[int, int]] = []

    def update_status(self, daemon, status, detail=""):
        self.statuses.append((daemon, status, detail))

    def update_training_progress(self, epoch, total_epochs, train_loss, val_loss, eta=0.0):
        self.progress.append((int(epoch), int(total_epochs)))

    def stop_requested(self):
        return False

    def clear_stop_request(self):
        pass


def _only_model_fields(model, **values):
    return {k: v for k, v in values.items() if k in model.model_fields}


def _seed(db: _FileDB, n_demos: int, ticks_per_round: int = 120, rounds: int = 3) -> None:
    from Programma_CS2_RENAN.backend.storage.db_models import (
        PlayerMatchStats,
        PlayerTickState,
        RoundStats,
    )

    with db.get_session() as session:
        for d in range(n_demos):
            demo = f"pro_{d:02d}"
            for p, player in enumerate(("alpha", "bravo")):
                session.add(
                    PlayerMatchStats(
                        player_name=player,
                        demo_name=demo,
                        is_pro=True,
                        rating=1.1,
                        match_date=_T0 + timedelta(days=d),
                        match_date_source="filename_date",
                        kd_ratio=1.0,
                        avg_adr=80.0,
                        avg_kast=0.7,
                        avg_kills=20.0,
                    )
                )
                tick = 100
                for rnd in range(2, 2 + rounds):
                    for i in range(ticks_per_round):
                        session.add(
                            PlayerTickState(
                                tick=tick,
                                player_name=player,
                                demo_name=demo,
                                pos_x=100.0 + tick * 0.5 + p,
                                pos_y=200.0 + tick * 0.3,
                                pos_z=50.0,
                                view_x=(45.0 + tick * 0.1) % 360.0,
                                view_y=5.0,
                                health=100,
                                armor=100,
                                has_helmet=True,
                                active_weapon="ak47",
                                equipment_value=4750,
                                enemies_visible=i % 3,
                                round_number=rnd,
                                time_in_round=i * 0.015625,
                                teammates_alive=4,
                                enemies_alive=5,
                                team_economy=10000,
                                map_name="de_mirage",
                            )
                        )
                        tick += 1
                    tick += 50
                    session.add(
                        RoundStats(
                            **_only_model_fields(
                                RoundStats,
                                demo_name=demo,
                                round_number=rnd,
                                player_name=player,
                                side="CT" if rnd % 2 else "T",
                                kills=1,
                                deaths=0,
                                kast=True,
                                round_won=bool((rnd + p) % 2),
                                round_rating=1.0,
                                opening_kill=False,
                                opening_death=False,
                            )
                        )
                    )


@pytest.fixture
def monolith(tmp_path, monkeypatch):
    from Programma_CS2_RENAN.backend.nn import coach_manager

    # The P4-A shard-completeness gate lists the real per-match shards of this
    # machine; "signal unavailable" skips it. The whole-map round floor is 13.
    monkeypatch.setattr(
        coach_manager.CoachTrainingManager, "_get_completed_demo_names", staticmethod(lambda: None)
    )
    monkeypatch.setattr(coach_manager, "MIN_COMPLETE_MAP_ROUNDS", 1)
    db = _FileDB(tmp_path / "monolith.sqlite")
    _seed(db, n_demos=10)
    return db


def _run(monolith, tmp_path, **kwargs):
    from Programma_CS2_RENAN.backend.nn.training_pipeline import run_v2_training_cycle

    state = _FakeState()
    result = run_v2_training_cycle(
        db=monolith,
        db_path=str(monolith.path),
        data_dir=tmp_path / "cs2_v2",
        state=state,
        config_overrides=dict(TINY_CONFIG_OVERRIDES),
        **kwargs,
    )
    return result, state


def test_a_full_cycle_trains_and_registers_the_model(monolith, tmp_path):
    from Programma_CS2_RENAN import __version__
    from Programma_CS2_RENAN.backend.nn import persistence
    from Programma_CS2_RENAN.backend.nn.training_registry import active_trained_model
    from Programma_CS2_RENAN.backend.storage.db_models import DatasetSplit, PlayerMatchStats

    seen: list[int] = []
    result, state = _run(
        monolith,
        tmp_path,
        steps=8,
        probe_every=4,
        progress=lambda step, total, info: seen.append(step),
    )

    assert result.status == "success", result.reason
    assert result.steps == 8 and seen == list(range(1, 9))

    with monolith.get_session() as session:
        splits = {row.dataset_split for row in session.exec(select(PlayerMatchStats)).all()}
        assert DatasetSplit.TRAIN in splits and DatasetSplit.VAL in splits

    train_shards = list((tmp_path / "cs2_v2" / "train").glob("*.safetensors"))
    val_shards = list((tmp_path / "cs2_v2" / "val").glob("*.safetensors"))
    assert len(train_shards) >= 5 and len(val_shards) >= 1
    assert result.export is not None and result.export.by_split["train"] == len(train_shards)

    checkpoint = persistence.get_model_path("jepa_v2_encoder")
    assert checkpoint.exists() and result.checkpoint == str(checkpoint)

    with monolith.get_session() as session:
        row = active_trained_model(session, "jepa_v2")
        assert row is not None and row.id == result.trained_model_id
        assert row.status == "success" and row.is_active is True
        assert row.steps == 8
        assert row.demos_train == len(train_shards) and row.demos_val == len(val_shards)
        assert row.relative_path == "global/jepa_v2_encoder.pt"
        assert row.sha256 == hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        assert row.app_version == __version__ and row.device == "cpu"
        assert row.schema_fingerprint and row.export_fingerprint
        assert row.finished_at is not None

    assert ("teacher", "Learning") in {(d, s) for d, s, _ in state.statuses}
    final_daemon, final_status, final_detail = state.statuses[-1]
    assert (final_daemon, final_status) == ("teacher", "Idle") and "8 steps" in final_detail
    assert (8, 8) in state.progress and state.progress[-1] == (0, 0)


def test_a_dry_run_writes_nothing(monolith, tmp_path):
    from Programma_CS2_RENAN.backend.nn import persistence
    from Programma_CS2_RENAN.backend.storage.db_models import TrainedModel

    result, state = _run(monolith, tmp_path, steps=4, probe_every=2, dry_run=True)

    assert result.status == "dry_run"
    assert not persistence.get_model_path("jepa_v2_encoder").exists()
    assert not persistence.get_model_path("jepa_v2_full").exists()
    with monolith.get_session() as session:
        assert session.exec(select(TrainedModel)).all() == []
    assert state.statuses[-1][1] == "Idle"


def test_a_stop_request_ends_the_run_and_is_recorded_but_not_active(monolith, tmp_path):
    from Programma_CS2_RENAN.backend.nn.training_registry import active_trained_model
    from Programma_CS2_RENAN.backend.storage.db_models import TrainedModel

    seen: list[int] = []
    result, _ = _run(
        monolith,
        tmp_path,
        steps=40,
        probe_every=100,
        progress=lambda step, total, info: seen.append(step),
        stop=lambda: len(seen) >= 3,
    )

    assert result.status == "stopped"
    assert result.steps == 3
    with monolith.get_session() as session:
        rows = session.exec(select(TrainedModel)).all()
        assert [r.status for r in rows] == ["stopped"]
        assert active_trained_model(session, "jepa_v2") is None


def test_too_few_demos_skips_without_touching_the_models(tmp_path, monkeypatch):
    from Programma_CS2_RENAN.backend.nn import coach_manager, persistence

    monkeypatch.setattr(
        coach_manager.CoachTrainingManager, "_get_completed_demo_names", staticmethod(lambda: None)
    )
    monkeypatch.setattr(coach_manager, "MIN_COMPLETE_MAP_ROUNDS", 1)
    db = _FileDB(tmp_path / "small.sqlite")
    _seed(db, n_demos=2)

    result, state = _run(db, tmp_path, steps=4)

    assert result.status == "skipped"
    assert "val" in result.reason
    assert not persistence.get_model_path("jepa_v2_encoder").exists()
    assert state.statuses[-1][1] == "Idle"


def test_default_shard_root_lives_under_the_data_root(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.backend.nn.jepa_v2 import cli
    from Programma_CS2_RENAN.core import config

    data_root = tmp_path / "data"
    monkeypatch.setattr(config, "DATA_DIR", str(data_root))
    monkeypatch.setattr(
        config,
        "get_setting",
        lambda key, default=None: "" if key == "JEPA_V2_DATA_DIR" else default,
    )
    assert Path(config.jepa_v2_data_dir()) == data_root / "cs2_v2"

    corpus = tmp_path / "corpus"
    monkeypatch.setattr(
        config,
        "get_setting",
        lambda key, default=None: str(corpus) if key == "JEPA_V2_DATA_DIR" else default,
    )
    assert config.jepa_v2_data_dir() == str(corpus)

    assert "PROIECT" not in Path(cli.__file__).read_text(encoding="utf-8")
    assert "JEPA_V2_DATA_DIR" in config.load_user_settings()

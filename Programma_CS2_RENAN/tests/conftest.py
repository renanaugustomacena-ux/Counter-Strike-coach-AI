"""
Shared test fixtures for Macena CS2 Analyzer test suite.

Provides:
- Path stabilization (centralized, replaces per-file setup)
- Database fixtures (in-memory for schema tests, real DB for data tests)
- Seeded fixtures for CI-portable tests (no machine-dependent skip gates)
- Real-data fixtures with skip gates for integration tests
- Torch utilities

Fixture hierarchy:
  in_memory_db        — empty schema, for ORM/migration tests
  seeded_db_session   — in-memory DB with realistic CS2 data, CI-portable
  real_db_session      — production database.db, developer-machine only (integration)
"""

import os
import sys
from pathlib import Path

# --- Venv Guard ---
# P6-03: Allow CI runners (no venv) via CI/GITHUB_ACTIONS env vars
if (
    sys.prefix == sys.base_prefix
    and not os.environ.get("CI")
    and not os.environ.get("GITHUB_ACTIONS")
):
    import pytest

    pytest.exit("Not running in virtualenv — activate before running tests", returncode=2)

import pytest

# --- Path Stabilization (centralized for all tests) ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Prevent Kivy from hijacking CLI args
os.environ["KIVY_NO_ARGS"] = "1"


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: tests that read/write production database.db")


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless CS2_INTEGRATION_TESTS=1 is set."""
    if os.environ.get("CS2_INTEGRATION_TESTS") == "1":
        return
    skip_integration = pytest.mark.skip(
        reason="Set CS2_INTEGRATION_TESTS=1 to run integration tests on production DB"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


@pytest.fixture
def in_memory_db():
    """Create an isolated in-memory SQLite database with all tables.

    Useful for testing schema creation and ORM operations
    without touching the real database.

    Note (PT2-18): This fixture uses SQLModel.metadata.create_all() rather than
    init_database(). This is intentional: init_database() is designed for the real
    WAL-mode SQLite file and performs operations (PRAGMA journal_mode=WAL, default
    row inserts) that are not meaningful for an in-memory session. The schema created
    here is equivalent for ORM testing purposes — all SQLModel-registered tables are
    created. If init_database() ever adds schema that is NOT reflected in SQLModel
    metadata (e.g. raw CREATE TABLE via sqlite3), this fixture must be updated.
    """
    from sqlmodel import Session, SQLModel, create_engine

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture
def seeded_db_session():
    """In-memory DB pre-populated with realistic CS2 match data.

    CI-portable: works on any machine without database.db.
    Contains 6 PlayerMatchStats, 12 RoundStats, 1 PlayerProfile.
    Data values are derived from realistic CS2 gameplay ranges.
    """
    from datetime import datetime, timezone

    from sqlmodel import Session, SQLModel, create_engine

    from Programma_CS2_RENAN.backend.storage.db_models import (
        PlayerMatchStats,
        PlayerProfile,
        RoundStats,
    )

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # --- PlayerProfile ---
        session.add(PlayerProfile(player_name="TestPlayer", role="Entry", bio="Test profile"))

        # --- PlayerMatchStats: 6 records across 3 demos, 2 players ---
        _fixed_dt = datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        _demos = [
            ("demo_dust2_20240615.dem", _fixed_dt),
            ("demo_mirage_20240616.dem", datetime(2024, 6, 16, 18, 0, 0, tzinfo=timezone.utc)),
            ("demo_inferno_20240617.dem", datetime(2024, 6, 17, 20, 0, 0, tzinfo=timezone.utc)),
        ]
        _players = [
            {
                "player_name": "TestPlayer",
                "stats": [
                    # dust2: solid game
                    dict(
                        avg_kills=22.0,
                        avg_deaths=16.0,
                        avg_adr=85.3,
                        avg_hs=0.52,
                        avg_kast=0.72,
                        accuracy=0.28,
                        econ_rating=1.12,
                        kd_ratio=1.375,
                        kpr=0.75,
                        dpr=0.55,
                        rating=1.15,
                        opening_duel_win_pct=0.55,
                        clutch_win_pct=0.33,
                        trade_kill_ratio=0.18,
                        was_traded_ratio=0.25,
                    ),
                    # mirage: average game
                    dict(
                        avg_kills=17.0,
                        avg_deaths=18.0,
                        avg_adr=72.1,
                        avg_hs=0.45,
                        avg_kast=0.65,
                        accuracy=0.24,
                        econ_rating=0.95,
                        kd_ratio=0.944,
                        kpr=0.62,
                        dpr=0.65,
                        rating=0.94,
                        opening_duel_win_pct=0.40,
                        clutch_win_pct=0.00,
                        trade_kill_ratio=0.12,
                        was_traded_ratio=0.33,
                    ),
                    # inferno: great game
                    dict(
                        avg_kills=28.0,
                        avg_deaths=14.0,
                        avg_adr=98.7,
                        avg_hs=0.60,
                        avg_kast=0.80,
                        accuracy=0.31,
                        econ_rating=1.25,
                        kd_ratio=2.0,
                        kpr=0.90,
                        dpr=0.45,
                        rating=1.45,
                        opening_duel_win_pct=0.65,
                        clutch_win_pct=0.50,
                        trade_kill_ratio=0.22,
                        was_traded_ratio=0.14,
                    ),
                ],
            },
            {
                "player_name": "Teammate1",
                "stats": [
                    dict(
                        avg_kills=15.0,
                        avg_deaths=19.0,
                        avg_adr=65.0,
                        avg_hs=0.38,
                        avg_kast=0.60,
                        accuracy=0.22,
                        econ_rating=0.88,
                        kd_ratio=0.789,
                        kpr=0.54,
                        dpr=0.68,
                        rating=0.82,
                    ),
                    dict(
                        avg_kills=20.0,
                        avg_deaths=15.0,
                        avg_adr=80.0,
                        avg_hs=0.50,
                        avg_kast=0.70,
                        accuracy=0.26,
                        econ_rating=1.05,
                        kd_ratio=1.333,
                        kpr=0.71,
                        dpr=0.54,
                        rating=1.10,
                    ),
                    dict(
                        avg_kills=12.0,
                        avg_deaths=20.0,
                        avg_adr=55.0,
                        avg_hs=0.35,
                        avg_kast=0.55,
                        accuracy=0.20,
                        econ_rating=0.75,
                        kd_ratio=0.6,
                        kpr=0.43,
                        dpr=0.71,
                        rating=0.68,
                    ),
                ],
            },
        ]
        for player_data in _players:
            for i, (demo_name, match_date) in enumerate(_demos):
                s = player_data["stats"][i]
                session.add(
                    PlayerMatchStats(
                        player_name=player_data["player_name"],
                        demo_name=demo_name,
                        match_date=match_date,
                        processed_at=match_date,
                        **s,
                    )
                )

        # --- RoundStats: 4 rounds × 2 players for first demo ---
        for rnd in range(1, 5):
            for pname, side in [("TestPlayer", "CT"), ("Teammate1", "T")]:
                session.add(
                    RoundStats(
                        demo_name="demo_dust2_20240615.dem",
                        round_number=rnd,
                        player_name=pname,
                        side=side,
                        kills=min(rnd, 3),
                        deaths=1 if rnd % 2 == 0 else 0,
                        assists=1 if rnd > 2 else 0,
                        damage_dealt=55 + rnd * 15,
                        headshot_kills=1 if rnd % 2 == 1 else 0,
                        equipment_value=1000 + rnd * 1500,
                        round_won=rnd % 2 == 1,
                    )
                )

        session.commit()
        yield session


@pytest.fixture
def seeded_player_stats(seeded_db_session):
    """First PlayerMatchStats record from the seeded database."""
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

    return seeded_db_session.exec(select(PlayerMatchStats).limit(1)).first()


@pytest.fixture
def seeded_round_stats(seeded_db_session):
    """First RoundStats record from the seeded database."""
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.db_models import RoundStats

    return seeded_db_session.exec(select(RoundStats).limit(1)).first()


@pytest.fixture
def real_db_session():
    """Open a session to the real database.db.

    Skips the test if the database file doesn't exist.
    Uses the production init_database() to ensure schema is current.
    """
    from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database

    db_path = PROJECT_ROOT / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db"
    if not db_path.exists():
        pytest.skip("No real database.db found — cannot run data-dependent test")

    init_database()
    db = get_db_manager()
    with db.get_session() as session:
        yield session


@pytest.fixture
def real_player_stats(real_db_session):
    """Query the first real PlayerMatchStats record from the database.

    Skips if no match data exists.
    """
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

    record = real_db_session.exec(select(PlayerMatchStats).limit(1)).first()
    if record is None:
        pytest.skip("No real PlayerMatchStats in DB — cannot run data-dependent test")
    return record


@pytest.fixture
def real_round_stats(real_db_session):
    """Query the first real RoundStats record from the database.

    Skips if no round data exists.
    """
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.db_models import RoundStats

    record = real_db_session.exec(select(RoundStats).limit(1)).first()
    if record is None:
        pytest.skip("No real RoundStats in DB — cannot run data-dependent test")
    return record


@pytest.fixture
def torch_no_grad():
    """Context manager that wraps test in torch.no_grad()."""
    import torch

    with torch.no_grad():
        yield


@pytest.fixture
def rap_model():
    """Deterministic RAPCoachModel for unit testing (CPU-only, seed=42)."""
    import torch

    from Programma_CS2_RENAN.backend.nn.rap_coach.model import RAPCoachModel

    torch.manual_seed(42)
    model = RAPCoachModel()
    model.eval()
    return model


@pytest.fixture
def rap_inputs():
    """Deterministic input tensors for RAP model testing.

    Shapes follow TrainingTensorConfig:
      view/map/motion: (batch=2, 3, 64, 64)
      metadata: (batch=2, seq_len=5, METADATA_DIM)
      skill_vec: (batch=2, 10)
    """
    import torch

    from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

    torch.manual_seed(42)
    batch_size, seq_len = 2, 5
    return {
        "view": torch.randn(batch_size, 3, 64, 64),
        "map": torch.randn(batch_size, 3, 64, 64),
        "motion": torch.randn(batch_size, 3, 64, 64),
        "metadata": torch.randn(batch_size, seq_len, METADATA_DIM),
        "skill_vec": torch.zeros(batch_size, 10),
    }


@pytest.fixture
def mock_db_manager():
    """In-memory DatabaseManager replacement for testing DB-dependent code.

    Provides get_session() context manager and get() method without touching
    the real database.db file. Uses SQLModel.metadata.create_all() to build
    the full schema in :memory:.
    """
    from contextlib import contextmanager

    from sqlmodel import Session, SQLModel, create_engine

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    class InMemoryDBManager:
        def __init__(self):
            self.engine = engine

        @contextmanager
        def get_session(self, engine_key="default"):
            with Session(engine, expire_on_commit=False) as session:
                try:
                    yield session
                    session.commit()
                except Exception:
                    session.rollback()
                    raise

        def get(self, model_class, pk):
            with self.get_session() as session:
                return session.get(model_class, pk)

        def create_db_and_tables(self):
            SQLModel.metadata.create_all(engine)

        def upsert(self, model_instance):
            with self.get_session() as session:
                return session.merge(model_instance)

    return InMemoryDBManager()


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    """Redirect settings file I/O to a temp file.

    Prevents tests from reading/writing the real user_settings.json.
    In-memory _settings state is snapshotted and restored at teardown
    so later tests in the same process aren't polluted.
    """
    from Programma_CS2_RENAN.core import config

    # Snapshot in-memory state before the test mutates it
    settings_snapshot = config._settings.copy()
    globals_snapshot = {k: getattr(config, k, None) for k in config._SETTING_NAME_TO_GLOBAL}

    # Create temp settings file (empty — load_user_settings merges with defaults)
    tmp_settings = tmp_path / "user_settings.json"
    tmp_settings.write_text("{}")

    # Redirect all file I/O to the temp file
    monkeypatch.setattr(config, "SETTINGS_PATH", str(tmp_settings))

    yield str(tmp_settings)

    # Restore in-memory state so subsequent tests see original values
    config._settings.clear()
    config._settings.update(settings_snapshot)
    for key, val in globals_snapshot.items():
        setattr(config, key, val)


# =============================================================================
# HLTV Metadata DB Fixture
# =============================================================================


@pytest.fixture
def seeded_hltv_session():
    """In-memory DB pre-populated with realistic HLTV pro player data.

    CI-portable: works on any machine without hltv_metadata.db.
    Contains: 2 ProTeams, 4 ProPlayers, 4 ProPlayerStatCards.
    Data values derived from real HLTV top-20 player statistics.
    """
    from sqlmodel import Session, SQLModel, create_engine

    from Programma_CS2_RENAN.backend.storage.database import _HLTV_TABLES
    from Programma_CS2_RENAN.backend.storage.db_models import ProPlayer, ProPlayerStatCard, ProTeam

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine, tables=_HLTV_TABLES)

    with Session(engine) as session:
        session.add(ProTeam(hltv_id=4608, name="Natus Vincere", world_rank=1))
        session.add(ProTeam(hltv_id=6667, name="FaZe Clan", world_rank=2))

        session.add(
            ProPlayer(
                hltv_id=11893,
                nickname="s1mple",
                real_name="Oleksandr Kostyliev",
                country="Ukraine",
                age=26,
                team_id=4608,
            )
        )
        session.add(
            ProPlayer(
                hltv_id=7998,
                nickname="NiKo",
                real_name="Nikola Kovac",
                country="Bosnia",
                age=27,
                team_id=6667,
            )
        )
        session.add(
            ProPlayer(
                hltv_id=18053,
                nickname="m0NESY",
                real_name="Ilya Osipov",
                country="Russia",
                age=19,
                team_id=6667,
            )
        )
        session.add(
            ProPlayer(
                hltv_id=18987,
                nickname="donk",
                real_name="Danil Kryshkovets",
                country="Russia",
                age=17,
                team_id=None,
            )
        )

        session.add(
            ProPlayerStatCard(
                player_id=11893,
                rating_2_0=1.28,
                dpr=0.62,
                kast=73.8,
                impact=1.35,
                adr=87.5,
                kpr=0.85,
                headshot_pct=38.5,
                maps_played=150,
                time_span="last_3_months",
            )
        )
        session.add(
            ProPlayerStatCard(
                player_id=7998,
                rating_2_0=1.15,
                dpr=0.65,
                kast=70.2,
                impact=1.18,
                adr=82.3,
                kpr=0.78,
                headshot_pct=50.2,
                maps_played=180,
                time_span="last_3_months",
            )
        )
        session.add(
            ProPlayerStatCard(
                player_id=18053,
                rating_2_0=1.35,
                dpr=0.58,
                kast=75.1,
                impact=1.45,
                adr=91.2,
                kpr=0.90,
                headshot_pct=42.8,
                maps_played=120,
                time_span="last_3_months",
            )
        )
        session.add(
            ProPlayerStatCard(
                player_id=18987,
                rating_2_0=1.40,
                dpr=0.55,
                kast=77.3,
                impact=1.50,
                adr=93.0,
                kpr=0.92,
                headshot_pct=55.0,
                maps_played=80,
                time_span="2024",
            )
        )

        session.commit()
        yield session


# =============================================================================
# Per-Match Data Fixture
# =============================================================================


@pytest.fixture
def match_data_dir(tmp_path):
    """Seeded per-match DB directory with one realistic match.

    Creates a MatchDataManager backed by tmp_path with:
    - 1 match (demo_name=test_match.dem, map=de_dust2)
    - 10 tick rows (2 players x 5 ticks)
    - Basic match metadata

    Returns (MatchDataManager, match_db_path).
    """
    import sqlite3

    match_id = "test_match"
    db_path = tmp_path / f"match_{match_id}.db"

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")

    # Create tick table matching MatchDataManager schema
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS matchtickstate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tick INTEGER NOT NULL,
            round_number INTEGER DEFAULT 1,
            player_name TEXT NOT NULL,
            steamid INTEGER,
            team TEXT,
            pos_x REAL DEFAULT 0, pos_y REAL DEFAULT 0, pos_z REAL DEFAULT 0,
            health INTEGER DEFAULT 100, armor INTEGER DEFAULT 100,
            is_alive INTEGER DEFAULT 1,
            active_weapon TEXT DEFAULT 'ak47',
            equipment_value INTEGER DEFAULT 4750,
            map_name TEXT DEFAULT 'de_dust2'
        )
    """
    )

    # Seed 10 ticks (2 players x 5 ticks)
    rows = []
    for tick in range(100, 600, 100):
        for pname, team, sid in [("Player1", "CT", 12345), ("Player2", "T", 67890)]:
            rows.append(
                (
                    tick,
                    1,
                    pname,
                    sid,
                    team,
                    float(tick),
                    float(tick * 2),
                    0.0,
                    100,
                    100,
                    1,
                    "ak47",
                    4750,
                    "de_dust2",
                )
            )

    conn.executemany(
        "INSERT INTO matchtickstate (tick, round_number, player_name, steamid, team, "
        "pos_x, pos_y, pos_z, health, armor, is_alive, active_weapon, equipment_value, map_name) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()

    yield tmp_path, db_path

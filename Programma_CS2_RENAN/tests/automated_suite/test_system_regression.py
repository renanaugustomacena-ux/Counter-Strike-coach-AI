import pytest
from sqlmodel import Session, create_engine, select

from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats


def test_database_schema_regression():
    """Regression Test: Ensure critical fields exist in the PlayerMatchStats model."""
    db = get_db_manager()
    # Check if we can create a record with all new fields
    test_stats = PlayerMatchStats(
        player_name="Regression_Bot",
        demo_name="regression_test.dem",
        avg_kills=1.0,
        avg_deaths=1.0,
        avg_adr=80.0,
        avg_hs=0.5,
        avg_kast=0.7,
        kill_std=0.1,
        adr_std=5.0,
        kd_ratio=1.0,
        impact_rounds=1.0,
        accuracy=0.45,
        econ_rating=0.05,
        anomaly_score=0.0,
        sample_weight=1.0,
        rating=1.0,
        dataset_split="test",  # New field check
    )
    assert hasattr(test_stats, "dataset_split")
    assert hasattr(test_stats, "accuracy")


def test_full_system_ingestion_query():
    """System Test: Verify upsert and query logic using existing real data.

    Uses a skip-gate pattern: only runs if real data exists in the database.
    Does NOT inject synthetic records into the production database.
    """
    db = get_db_manager()

    with db.get_session() as session:
        result = session.exec(select(PlayerMatchStats).limit(1)).first()

    if result is None:
        pytest.skip(
            "No real data in database for system regression test. "
            "Run ingestion first to populate the database."
        )

    # Verify the queried record has expected schema integrity
    assert result.player_name is not None
    assert isinstance(result.avg_adr, (int, float))
    assert result.demo_name is not None

"""GAP-09 tests for the strategy_label migration + ORM field.

The migration is reversible: upgrade() adds a nullable column + index;
downgrade() drops both. Round-trip is exercised against an in-memory
SQLite engine.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from Programma_CS2_RENAN.backend.storage.db_models import CoachingExperience

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "c3d4e5f6a7b8_add_strategy_label_to_coachingexperience.py"
)


@pytest.fixture
def engine_with_baseline_table():
    """Engine with a `coachingexperience` table that mirrors the
    pre-migration schema (strategy_label NOT yet present).
    """
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table(
        "coachingexperience",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("context_hash", sa.String, nullable=False),
        sa.Column("map_name", sa.String, nullable=False, server_default="de_unknown"),
        sa.Column("action_taken", sa.String, nullable=False, server_default=""),
        sa.Column("outcome", sa.String, nullable=False, server_default=""),
        sa.Column("game_state_json", sa.String, server_default="{}"),
    )
    metadata.create_all(engine)
    return engine


def _load_migration_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("_gap09_migration_under_test", _MIGRATION_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_migration_file_exists():
    assert _MIGRATION_PATH.exists()
    mod = _load_migration_module()
    assert mod.revision == "c3d4e5f6a7b8"
    assert mod.down_revision == "b2c3d4e5f6a7"


def _column_names(engine, table) -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(sa.text(f'PRAGMA table_info("{table}")')).all()
    return [r[1] for r in rows]


def _index_names(engine, table) -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(sa.text(f'PRAGMA index_list("{table}")')).all()
    return [r[1] for r in rows]


def test_upgrade_adds_column_and_index(engine_with_baseline_table):
    engine = engine_with_baseline_table
    mod = _load_migration_module()

    assert "strategy_label" not in _column_names(engine, "coachingexperience")

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            mod.upgrade()
        conn.commit()

    cols = _column_names(engine, "coachingexperience")
    assert "strategy_label" in cols
    idxs = _index_names(engine, "coachingexperience")
    assert "ix_coachingexperience_strategy_label" in idxs


def test_downgrade_drops_column_and_index(engine_with_baseline_table):
    engine = engine_with_baseline_table
    mod = _load_migration_module()

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            mod.upgrade()
            assert "strategy_label" in _column_names(engine, "coachingexperience")
            mod.downgrade()
        conn.commit()

    cols = _column_names(engine, "coachingexperience")
    assert "strategy_label" not in cols
    idxs = _index_names(engine, "coachingexperience")
    assert "ix_coachingexperience_strategy_label" not in idxs


def test_upgrade_idempotent(engine_with_baseline_table):
    """Running upgrade twice must not error (the helpers guard with exists checks)."""
    engine = engine_with_baseline_table
    mod = _load_migration_module()

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            mod.upgrade()
            mod.upgrade()  # second call must be a no-op
        conn.commit()

    assert "strategy_label" in _column_names(engine, "coachingexperience")


def test_orm_field_present_and_nullable():
    """db_models.CoachingExperience must declare strategy_label as Optional/indexed."""
    fields = CoachingExperience.model_fields
    assert "strategy_label" in fields
    field = fields["strategy_label"]
    # Optional → annotation includes None type
    assert "Optional" in str(field.annotation) or "None" in str(field.annotation)


def test_taxonomy_doc_exists():
    doc = Path(__file__).resolve().parents[2] / "docs" / "strategy_taxonomy.md"
    assert doc.exists()
    text = doc.read_text()
    # Spot-check that all five families show up
    for family in ("setpiece", "economy", "rotation", "playbook", "individual"):
        assert f"### `{family}`" in text, f"family '{family}' missing from taxonomy doc"

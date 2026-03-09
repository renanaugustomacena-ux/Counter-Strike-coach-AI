"""add_rating_components

Revision ID: 5d5764ef9f26
Revises: b609a11e13cc
Create Date: 2026-01-22 23:26:47.779315

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d5764ef9f26"
down_revision: Union[str, Sequence[str], None] = "b609a11e13cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add Rating 2.0 Columns (The Core Goal)
    try:
        op.add_column(
            "playermatchstats", sa.Column("kpr", sa.Float(), nullable=False, server_default="0.0")
        )
        op.add_column(
            "playermatchstats", sa.Column("dpr", sa.Float(), nullable=False, server_default="0.0")
        )
        op.add_column(
            "playermatchstats",
            sa.Column("rating_impact", sa.Float(), nullable=False, server_default="0.0"),
        )
        op.add_column(
            "playermatchstats",
            sa.Column("rating_survival", sa.Float(), nullable=False, server_default="0.0"),
        )
        op.add_column(
            "playermatchstats",
            sa.Column("rating_kast", sa.Float(), nullable=False, server_default="0.0"),
        )
        op.add_column(
            "playermatchstats",
            sa.Column("rating_kpr", sa.Float(), nullable=False, server_default="0.0"),
        )
        op.add_column(
            "playermatchstats",
            sa.Column("rating_adr", sa.Float(), nullable=False, server_default="0.0"),
        )
    except Exception:
        pass  # Columns might already exist if we retry

    try:
        op.add_column(
            "playertickstate",
            sa.Column(
                "demo_name",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default="unknown",
            ),
        )
        op.create_index(
            op.f("ix_playertickstate_demo_name"), "playertickstate", ["demo_name"], unique=False
        )
    except Exception:
        pass

    # 2. Add ProPlayer Card columns
    try:
        op.add_column(
            "proplayerstatcard",
            sa.Column("headshot_pct", sa.Float(), nullable=False, server_default="0.0"),
        )
        op.add_column(
            "proplayerstatcard",
            sa.Column("maps_played", sa.Integer(), nullable=False, server_default="0"),
        )
        op.add_column(
            "proplayerstatcard",
            sa.Column("opening_kill_ratio", sa.Float(), nullable=False, server_default="0.0"),
        )
        op.add_column(
            "proplayerstatcard",
            sa.Column("opening_duel_win_pct", sa.Float(), nullable=False, server_default="0.0"),
        )
        op.add_column(
            "proplayerstatcard",
            sa.Column("clutch_win_count", sa.Integer(), nullable=False, server_default="0"),
        )
        op.add_column(
            "proplayerstatcard",
            sa.Column("multikill_round_pct", sa.Float(), nullable=False, server_default="0.0"),
        )
    except Exception:
        pass


def downgrade() -> None:
    """Downgrade schema — R2-02: reverse all columns added in upgrade()."""
    # ProPlayerStatCard columns
    for col in ("multikill_round_pct", "clutch_win_count", "opening_duel_win_pct",
                "opening_kill_ratio", "maps_played", "headshot_pct"):
        try:
            op.drop_column("proplayerstatcard", col)
        except Exception:
            pass  # Column may not exist if upgrade was partial

    # PlayerTickState columns
    try:
        op.drop_index(op.f("ix_playertickstate_demo_name"), table_name="playertickstate")
        op.drop_column("playertickstate", "demo_name")
    except Exception:
        pass

    # PlayerMatchStats rating columns
    for col in ("rating_adr", "rating_kpr", "rating_kast", "rating_survival",
                "rating_impact", "dpr", "kpr"):
        try:
            op.drop_column("playermatchstats", col)
        except Exception:
            pass

"""add_fusion_plan_columns_to_playermatchstats

Revision ID: 3c6ecb5fe20e
Revises: 19fcff36ea0a
Create Date: 2026-02-15 22:18:29.007868

Safe migration: ADD COLUMN only. No destructive operations.
Adds Fusion Plan Proposal 1 (trade kills) and Proposal 2 (utility breakdown)
columns to playermatchstats, and COPER feedback columns to coachingexperience.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c6ecb5fe20e"
down_revision: Union[str, Sequence[str], None] = "19fcff36ea0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns (safe ADD COLUMN only, no drops)."""
    # --- PlayerMatchStats: Fusion Plan Proposal 1 (Trade Kills) ---
    op.add_column(
        "playermatchstats",
        sa.Column("trade_kill_ratio", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "playermatchstats",
        sa.Column("was_traded_ratio", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "playermatchstats",
        sa.Column("avg_trade_response_ticks", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "playermatchstats",
        sa.Column("thrusmoke_kill_pct", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "playermatchstats",
        sa.Column("wallbang_kill_pct", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "playermatchstats",
        sa.Column("noscope_kill_pct", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "playermatchstats",
        sa.Column("blind_kill_pct", sa.Float(), nullable=False, server_default="0.0"),
    )

    # --- PlayerMatchStats: Fusion Plan Proposal 2 (Utility Breakdown) ---
    op.add_column(
        "playermatchstats",
        sa.Column("he_damage_per_round", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "playermatchstats",
        sa.Column("molotov_damage_per_round", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "playermatchstats",
        sa.Column("smokes_per_round", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "playermatchstats",
        sa.Column("unused_utility_per_round", sa.Float(), nullable=False, server_default="0.0"),
    )

    # --- CoachingExperience: COPER feedback columns ---
    op.add_column(
        "coachingexperience",
        sa.Column("outcome_validated", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "coachingexperience",
        sa.Column("effectiveness_score", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "coachingexperience", sa.Column("follow_up_match_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "coachingexperience",
        sa.Column("times_advice_given", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "coachingexperience",
        sa.Column("times_advice_followed", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("coachingexperience", sa.Column("last_feedback_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove added columns."""
    op.drop_column("playermatchstats", "unused_utility_per_round")
    op.drop_column("playermatchstats", "smokes_per_round")
    op.drop_column("playermatchstats", "molotov_damage_per_round")
    op.drop_column("playermatchstats", "he_damage_per_round")
    op.drop_column("playermatchstats", "blind_kill_pct")
    op.drop_column("playermatchstats", "noscope_kill_pct")
    op.drop_column("playermatchstats", "wallbang_kill_pct")
    op.drop_column("playermatchstats", "thrusmoke_kill_pct")
    op.drop_column("playermatchstats", "avg_trade_response_ticks")
    op.drop_column("playermatchstats", "was_traded_ratio")
    op.drop_column("playermatchstats", "trade_kill_ratio")
    op.drop_column("coachingexperience", "last_feedback_at")
    op.drop_column("coachingexperience", "times_advice_followed")
    op.drop_column("coachingexperience", "times_advice_given")
    op.drop_column("coachingexperience", "follow_up_match_id")
    op.drop_column("coachingexperience", "effectiveness_score")
    op.drop_column("coachingexperience", "outcome_validated")

"""add_steamid_to_playertickstate_and_playermatchstats

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-03 16:00:00.000000

Safe migration: ADD COLUMN only. Adds nullable INTEGER ``steamid`` column
to both ``playertickstate`` and ``playermatchstats``. No index is built
in this migration; the index is added in a follow-up migration AFTER the
D1 tick-migration phase finishes (~414M rows). Building the index after
the bulk load is professional ETL practice and avoids ~5-10% per-INSERT
overhead during the long write phase.

Idempotent guard: column is checked before ADD so re-running the
migration is a no-op.
"""

import re
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_id(name: str) -> str:
    if not _SAFE_IDENTIFIER_RE.match(name):
        raise ValueError(f"Unsafe identifier: {name!r}")
    return name


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists on ``table`` (idempotent guard)."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f'PRAGMA table_info("{_safe_id(table)}")'))
    return any(row[1] == column for row in result)


def upgrade() -> None:
    """Add nullable steamid INTEGER columns; no index (deferred to post-D1)."""
    targets = ("playertickstate", "playermatchstats")
    for table in targets:
        if not _column_exists(table, "steamid"):
            op.add_column(
                table,
                sa.Column("steamid", sa.BigInteger(), nullable=True),
            )


def downgrade() -> None:
    """Remove steamid columns from both tables."""
    targets = ("playermatchstats", "playertickstate")
    for table in targets:
        if _column_exists(table, "steamid"):
            op.drop_column(table, "steamid")

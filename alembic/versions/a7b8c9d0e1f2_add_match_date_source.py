"""add_match_date_source

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-21 12:00:00.000000

Safe migration: ADD COLUMN only. No destructive operations.
OI-2: adds match_date_source to playermatchstats — provenance marker for
match_date ('filename_date' / 'filename_year' / 'hltv_event_date' /
'file_mtime' / 'ingested_at'). Existing rows default to 'ingested_at',
which is the honest description of every historical value (no writer ever
set match_date; it was the ingestion wall clock).
"""

import re
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# DB-02 (AUDIT §9.1): identifier whitelist guards `sa.text(f"...")` DDL
# from injection if a future migration template copy ever substitutes a
# non-literal table name.
_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_id(name: str) -> str:
    if not _SAFE_IDENTIFIER_RE.match(name):
        raise ValueError(f"Unsafe identifier: {name!r}")
    return name


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists (idempotent guard)."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f'PRAGMA table_info("{_safe_id(table)}")'))
    return any(row[1] == column for row in result)


def upgrade() -> None:
    """Add match_date_source column if not already present."""
    if not _column_exists("playermatchstats", "match_date_source"):
        op.add_column(
            "playermatchstats",
            sa.Column(
                "match_date_source", sa.String(), nullable=True, server_default="ingested_at"
            ),
        )


def downgrade() -> None:
    """Remove match_date_source column."""
    op.drop_column("playermatchstats", "match_date_source")

"""drop_connect_state_from_ext_playerplaystyle

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-17 18:20:00.000000

26-SCHEMA-02 / TASKS#61 (owner decision 2026-07-17): remove
``steam_connected`` and ``faceit_connected`` from ``ext_playerplaystyle``.
The feature never existed end-to-end — no writer anywhere in the repo,
and the only reader queried the wrong model, so both flags were
structurally False. Dropping the columns makes the schema honest; the
connect feature returns, if ever, through a full design (writer + reader
+ DM-02 split).

Idempotent guard: column presence is checked before DROP/ADD.
Requires SQLite >= 3.35 (ALTER TABLE DROP COLUMN).
"""

import re
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "ext_playerplaystyle"
_COLUMNS = ("steam_connected", "faceit_connected")

_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_id(name: str) -> str:
    if not _SAFE_IDENTIFIER_RE.match(name):
        raise ValueError(f"Unsafe identifier: {name!r}")
    return name


def _column_exists(table: str, column: str) -> bool:
    """Check if ``column`` exists on ``table`` (idempotent guard)."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f'PRAGMA table_info("{_safe_id(table)}")'))
    return any(row[1] == column for row in result)


def upgrade() -> None:
    """Drop the dead connect-state flags (idempotent)."""
    for column in _COLUMNS:
        if _column_exists(_TABLE, column):
            op.drop_column(_TABLE, column)


def downgrade() -> None:
    """Restore the flags with their historical default (idempotent)."""
    for column in _COLUMNS:
        if not _column_exists(_TABLE, column):
            op.add_column(
                _TABLE,
                sa.Column(column, sa.Boolean(), nullable=False, server_default=sa.false()),
            )

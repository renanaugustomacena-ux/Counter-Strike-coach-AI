"""add_pov_stream_index_to_playertickstate

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-16 14:30:00.000000

Composite index (demo_name, player_name, tick) on ``playertickstate``.

R4 CRIT fix (2026-07-16): JEPA training now fetches contiguous
single-player windows (``_fetch_jepa_windows``: ~4.5k window queries per
epoch of the form WHERE demo_name=? AND player_name=? AND tick>=? ORDER BY
tick LIMIT n) and the RAP fetcher segments per (demo, player) run. The
existing single-column indexes force SQLite to scan a whole demo's rows
per query; this composite index serves the window lookups directly.

One-time cost: building the index on the full monolith (~429M rows) takes
minutes and grows the DB file — run ``alembic upgrade head`` on the data
box before the next training rung (R8 pre-flight).

Idempotent guard: index presence is checked before CREATE/DROP.
"""

import re
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX_NAME = "ix_playertickstate_demo_player_tick"
_TABLE = "playertickstate"

_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_id(name: str) -> str:
    if not _SAFE_IDENTIFIER_RE.match(name):
        raise ValueError(f"Unsafe identifier: {name!r}")
    return name


def _index_exists(table: str, index: str) -> bool:
    """Check if ``index`` already exists on ``table`` (idempotent guard)."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f'PRAGMA index_list("{_safe_id(table)}")'))
    return any(row[1] == index for row in result)


def upgrade() -> None:
    """Create the composite POV-stream index (idempotent)."""
    if not _index_exists(_TABLE, _INDEX_NAME):
        op.create_index(
            _INDEX_NAME,
            _TABLE,
            ["demo_name", "player_name", "tick"],
        )


def downgrade() -> None:
    """Drop the composite POV-stream index (idempotent)."""
    if _index_exists(_TABLE, _INDEX_NAME):
        op.drop_index(_INDEX_NAME, table_name=_TABLE)

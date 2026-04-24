"""add_strategy_label_to_coachingexperience

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-25 00:00:00.000000

GAP-09: enumerate the implicit strategy taxonomy used by the coach (RAP +
RAG retrieval) by attaching a nullable string label to coaching experiences.
The taxonomy itself lives in `docs/strategy_taxonomy.md`. The column is
nullable so legacy rows are unaffected; new mining + classification jobs
populate it going forward.

Safe: ADD COLUMN only, additive, reversible. Indexed because retrieval
will frequently filter by strategy_label.
"""

import re
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# DB-02 (AUDIT §9.1): identifier whitelist for any future f-string DDL.
_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_id(name: str) -> str:
    if not _SAFE_IDENTIFIER_RE.match(name):
        raise ValueError(f"Unsafe identifier: {name!r}")
    return name


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f'PRAGMA table_info("{_safe_id(table)}")'))
    return any(row[1] == column for row in result)


def _index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='index' AND name=:n"),
        {"n": index_name},
    )
    return result.first() is not None


def upgrade() -> None:
    """Add nullable strategy_label column + index on coachingexperience."""
    if not _column_exists("coachingexperience", "strategy_label"):
        op.add_column(
            "coachingexperience",
            sa.Column("strategy_label", sa.String(), nullable=True),
        )
    if not _index_exists("ix_coachingexperience_strategy_label"):
        op.create_index(
            "ix_coachingexperience_strategy_label",
            "coachingexperience",
            ["strategy_label"],
        )


def downgrade() -> None:
    """Drop strategy_label column + its index. Reversible."""
    if _index_exists("ix_coachingexperience_strategy_label"):
        op.drop_index(
            "ix_coachingexperience_strategy_label",
            table_name="coachingexperience",
        )
    if _column_exists("coachingexperience", "strategy_label"):
        op.drop_column("coachingexperience", "strategy_label")

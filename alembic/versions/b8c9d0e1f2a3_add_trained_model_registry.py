"""add_trained_model_registry

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-13 12:00:00.000000

Safe migration: CREATE TABLE + ADD COLUMN only. No destructive operations.
WP4b: the ``trainedmodel`` registry (one row per local training run,
``is_active`` = latest success per model type) and the GUI -> Teacher
training request channel on ``coachstate`` (``training_requested``,
``training_request_model``, ``training_request_steps``,
``training_stop_requested``).
"""

import re
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_REQUEST_COLUMNS = (
    ("training_requested", sa.Boolean(), "0"),
    ("training_request_model", sa.String(), "''"),
    ("training_request_steps", sa.Integer(), "0"),
    ("training_stop_requested", sa.Boolean(), "0"),
)


def _safe_id(name: str) -> str:
    if not _SAFE_IDENTIFIER_RE.match(name):
        raise ValueError(f"Unsafe identifier: {name!r}")
    return name


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f'PRAGMA table_info("{_safe_id(table)}")'))
    return any(row[1] == column for row in result)


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type = 'table' AND name = :name"),
        {"name": table},
    )
    return result.first() is not None


def upgrade() -> None:
    if not _table_exists("trainedmodel"):
        op.create_table(
            "trainedmodel",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("model_type", sa.String(), nullable=False),
            sa.Column("version_name", sa.String(), nullable=False, server_default=""),
            sa.Column("relative_path", sa.String(), nullable=False, server_default=""),
            sa.Column("sha256", sa.String(), nullable=False, server_default=""),
            sa.Column("steps", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("demos_train", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("demos_val", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("export_fingerprint", sa.String(), nullable=False, server_default=""),
            sa.Column("schema_fingerprint", sa.String(), nullable=False, server_default=""),
            sa.Column("device", sa.String(), nullable=False, server_default=""),
            sa.Column("app_version", sa.String(), nullable=False, server_default=""),
            sa.Column("status", sa.String(), nullable=False, server_default="running"),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("metrics_json", sa.String(), nullable=False, server_default="{}"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="0"),
        )
        op.create_index("ix_trainedmodel_model_type", "trainedmodel", ["model_type"])
        op.create_index("ix_trainedmodel_status", "trainedmodel", ["status"])
        op.create_index("ix_trainedmodel_type_active", "trainedmodel", ["model_type", "is_active"])

    for column, col_type, default in _REQUEST_COLUMNS:
        if not _column_exists("coachstate", column):
            op.add_column(
                "coachstate",
                sa.Column(column, col_type, nullable=False, server_default=sa.text(default)),
            )


def downgrade() -> None:
    with op.batch_alter_table("coachstate") as batch:
        for column, _, _ in _REQUEST_COLUMNS:
            if _column_exists("coachstate", column):
                batch.drop_column(column)
    if _table_exists("trainedmodel"):
        op.drop_table("trainedmodel")

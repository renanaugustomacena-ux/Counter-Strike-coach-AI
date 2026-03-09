"""add_sync_and_interval_to_coachstate

Revision ID: e3013f662fd4
Revises: 609fed4b4dce
Create Date: 2026-01-12 20:21:27.478166

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3013f662fd4"
down_revision: Union[str, Sequence[str], None] = "609fed4b4dce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("coachstate", sa.Column("last_ingest_sync", sa.DateTime(), nullable=True))
    op.add_column("coachstate", sa.Column("last_pro_ingest_sync", sa.DateTime(), nullable=True))
    op.add_column(
        "coachstate",
        sa.Column("pro_ingest_interval", sa.Float(), nullable=False, server_default="1.0"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("coachstate", "pro_ingest_interval")
    op.drop_column("coachstate", "last_pro_ingest_sync")
    op.drop_column("coachstate", "last_ingest_sync")

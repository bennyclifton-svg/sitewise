"""Remove the unused Hermes session mapping.

Revision ID: 033_remove_unused_hermes_session
Revises: 032_workflow_runs
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "033_remove_unused_hermes_session"
down_revision: str | None = "032_workflow_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("chat_threads", "hermes_session_id")


def downgrade() -> None:
    op.add_column(
        "chat_threads",
        sa.Column("hermes_session_id", sa.String(length=255), nullable=True),
    )

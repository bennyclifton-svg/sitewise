"""chat thread hermes session id

Revision ID: 014_chat_threads_hermes_session
Revises: 013_tender_analysis_results
Create Date: 2026-07-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_chat_threads_hermes_session"
down_revision: Union[str, Sequence[str], None] = "013_tender_analysis_results"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_threads",
        sa.Column("hermes_session_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_threads", "hermes_session_id")

"""tender extract content-hash cache (A4)

Revision ID: 020_tender_extract_cache
Revises: 019_project_decisions
Create Date: 2026-07-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "020_tender_extract_cache"
down_revision: Union[str, Sequence[str], None] = "019_project_decisions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tender_extract_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("extractor_version", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "content_hash",
            "extractor_version",
            name="uq_tender_extract_cache_project_hash_version",
        ),
    )
    op.create_index(
        "ix_tender_extract_cache_project_hash",
        "tender_extract_cache",
        ["project_id", "content_hash"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tender_extract_cache_project_hash",
        table_name="tender_extract_cache",
    )
    op.drop_table("tender_extract_cache")

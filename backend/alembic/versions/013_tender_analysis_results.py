"""tender analysis result store

Revision ID: 013_tender_analysis_results
Revises: 012_tender_mapping_support
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013_tender_analysis_results"
down_revision: Union[str, Sequence[str], None] = "012_tender_mapping_support"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tender_analysis_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comparison_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("gap_matrix", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ledgers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("questions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["comparison_id"], ["tender_comparisons.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "comparison_id", name="uq_tender_analysis_results_comparison_id"
        ),
    )
    op.create_index(
        "ix_tender_analysis_results_comparison_id",
        "tender_analysis_results",
        ["comparison_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tender_analysis_results_comparison_id",
        table_name="tender_analysis_results",
    )
    op.drop_table("tender_analysis_results")

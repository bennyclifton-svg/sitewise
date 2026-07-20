"""Create tender_project_trades for per-comparison trade taxonomy.

Revision ID: 035_tender_project_trades
Revises: 034b_cell_amount_breakdown
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "035_tender_project_trades"
down_revision: str | None = "034b_cell_amount_breakdown"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tender_project_trades",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("comparison_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("group_label", sa.String(length=64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default="generated",
        ),
        sa.Column("anchor_cell_codes", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("anchor_confidence", sa.Numeric(), nullable=True),
        sa.Column(
            "seed_assignments",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["comparison_id"],
            ["tender_comparisons.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "comparison_id",
            "code",
            name="uq_tender_project_trades_comparison_id_code",
        ),
        sa.CheckConstraint(
            "source IN ('generated', 'manual')",
            name="ck_tender_project_trades_source",
        ),
    )
    op.create_index(
        "ix_tender_project_trades_comparison_id",
        "tender_project_trades",
        ["comparison_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tender_project_trades_comparison_id",
        table_name="tender_project_trades",
    )
    op.drop_table("tender_project_trades")

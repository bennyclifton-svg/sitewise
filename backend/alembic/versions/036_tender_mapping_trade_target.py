"""Allow tender mappings and cell status to target project trades.

Revision ID: 036_tender_mapping_trade_target
Revises: 035_tender_project_trades
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "036_tender_mapping_trade_target"
down_revision: str | None = "035_tender_project_trades"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_TIERS = (
    "t0_exact",
    "t1_embedding",
    "t2_small_llm",
    "t3_frontier",
    "human",
)
_NEW_TIERS = _OLD_TIERS + ("taxonomy_seed",)


def upgrade() -> None:
    op.add_column(
        "tender_mappings",
        sa.Column("project_trade_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_tender_mappings_project_trade_id",
        "tender_mappings",
        "tender_project_trades",
        ["project_trade_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column(
        "tender_mappings",
        "cell_code",
        existing_type=sa.String(length=32),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_tender_mappings_cell_or_trade",
        "tender_mappings",
        "cell_code IS NOT NULL OR project_trade_id IS NOT NULL",
    )
    op.drop_constraint("ck_tender_mappings_tier", "tender_mappings", type_="check")
    quoted_tiers = ", ".join(f"'{tier}'" for tier in _NEW_TIERS)
    op.create_check_constraint(
        "ck_tender_mappings_tier",
        "tender_mappings",
        f"tier IN ({quoted_tiers})",
    )
    op.create_index(
        "ix_tender_mappings_project_trade_id",
        "tender_mappings",
        ["project_trade_id"],
    )

    op.add_column(
        "tender_cell_status",
        sa.Column("project_trade_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_tender_cell_status_project_trade_id",
        "tender_cell_status",
        "tender_project_trades",
        ["project_trade_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column(
        "tender_cell_status",
        "cell_code",
        existing_type=sa.String(length=32),
        nullable=True,
    )
    op.drop_constraint(
        "uq_tender_cell_status_comparison_quote_cell",
        "tender_cell_status",
        type_="unique",
    )
    op.create_index(
        "uq_tender_cell_status_comparison_quote_cell",
        "tender_cell_status",
        ["comparison_id", "quote_id", "cell_code"],
        unique=True,
        postgresql_where=sa.text("cell_code IS NOT NULL"),
    )
    op.create_index(
        "uq_tender_cell_status_comparison_quote_trade",
        "tender_cell_status",
        ["comparison_id", "quote_id", "project_trade_id"],
        unique=True,
        postgresql_where=sa.text("project_trade_id IS NOT NULL"),
    )
    op.create_check_constraint(
        "ck_tender_cell_status_cell_or_trade",
        "tender_cell_status",
        "cell_code IS NOT NULL OR project_trade_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_tender_cell_status_cell_or_trade",
        "tender_cell_status",
        type_="check",
    )
    op.drop_index(
        "uq_tender_cell_status_comparison_quote_trade",
        table_name="tender_cell_status",
    )
    op.drop_index(
        "uq_tender_cell_status_comparison_quote_cell",
        table_name="tender_cell_status",
    )
    op.create_unique_constraint(
        "uq_tender_cell_status_comparison_quote_cell",
        "tender_cell_status",
        ["comparison_id", "quote_id", "cell_code"],
    )
    op.alter_column(
        "tender_cell_status",
        "cell_code",
        existing_type=sa.String(length=32),
        nullable=False,
    )
    op.drop_constraint(
        "fk_tender_cell_status_project_trade_id",
        "tender_cell_status",
        type_="foreignkey",
    )
    op.drop_column("tender_cell_status", "project_trade_id")

    op.drop_index(
        "ix_tender_mappings_project_trade_id",
        table_name="tender_mappings",
    )
    op.drop_constraint("ck_tender_mappings_tier", "tender_mappings", type_="check")
    quoted_tiers = ", ".join(f"'{tier}'" for tier in _OLD_TIERS)
    op.create_check_constraint(
        "ck_tender_mappings_tier",
        "tender_mappings",
        f"tier IN ({quoted_tiers})",
    )
    op.drop_constraint(
        "ck_tender_mappings_cell_or_trade",
        "tender_mappings",
        type_="check",
    )
    op.alter_column(
        "tender_mappings",
        "cell_code",
        existing_type=sa.String(length=32),
        nullable=False,
    )
    op.drop_constraint(
        "fk_tender_mappings_project_trade_id",
        "tender_mappings",
        type_="foreignkey",
    )
    op.drop_column("tender_mappings", "project_trade_id")

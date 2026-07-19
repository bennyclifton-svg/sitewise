"""Ledger tree columns, reconciliation table, and new flag types.

Revision ID: 034_tender_ledger_completeness
Revises: 033_remove_unused_hermes_session
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "034_tender_ledger_completeness"
down_revision: str | None = "033_remove_unused_hermes_session"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_FLAG_TYPES = (
    "gap",
    "low_pc_allowance",
    "unrealistic_ps",
    "missing_expected",
    "scope_ambiguity",
    "price_outlier",
    "exclusion_risk",
    "statutory_missing",
    "arithmetic_inconsistency",
)
_NEW_FLAG_TYPES = _OLD_FLAG_TYPES + (
    "unreconciled_residual",
    "non_comparable_basis",
    "suspect_number_format",
)


def upgrade() -> None:
    op.add_column(
        "tender_line_items",
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_tender_line_items_parent_id",
        "tender_line_items",
        "tender_line_items",
        ["parent_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.add_column("tender_line_items", sa.Column("role", sa.String(length=32), nullable=True))
    op.create_check_constraint(
        "ck_tender_line_items_role",
        "tender_line_items",
        "role IN ('contract_component','pc_allowance','ps_allowance',"
        "'optional_upgrade','informational','excluded')",
    )
    op.add_column(
        "tender_line_items",
        sa.Column(
            "is_rollup",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "tender_line_items",
        sa.Column("duplicate_of_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_tender_line_items_duplicate_of_id",
        "tender_line_items",
        "tender_line_items",
        ["duplicate_of_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "tender_line_items",
        sa.Column("gst_basis", sa.String(length=8), nullable=True),
    )
    op.create_check_constraint(
        "ck_tender_line_items_gst_basis",
        "tender_line_items",
        "gst_basis IN ('inc','ex','unknown')",
    )
    op.add_column(
        "tender_line_items",
        sa.Column("amount_ex_gst_cents", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "tender_line_items",
        sa.Column(
            "counted_in_total",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "tender_line_items",
        sa.Column("figure_key", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_tender_line_items_quote_parent",
        "tender_line_items",
        ["quote_id", "parent_id"],
    )

    op.create_table(
        "tender_quote_reconciliations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comparison_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stated_total_cents", sa.BigInteger(), nullable=True),
        sa.Column("stated_basis", sa.String(length=8), nullable=True),
        sa.Column("gst_line_cents", sa.BigInteger(), nullable=True),
        sa.Column(
            "counted_total_cents",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("computed_ex_gst_cents", sa.BigInteger(), nullable=True),
        sa.Column(
            "residual_cents",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "checks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "uncaptured",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
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
            ["quote_id"],
            ["tender_quotes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["comparison_id"],
            ["tender_comparisons.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("quote_id", name="uq_tender_quote_reconciliations_quote_id"),
        sa.CheckConstraint(
            "stated_basis IN ('inc','ex','unknown')",
            name="ck_tender_quote_reconciliations_stated_basis",
        ),
        sa.CheckConstraint(
            "status IN ('reconciled','residual','not_stated','non_comparable')",
            name="ck_tender_quote_reconciliations_status",
        ),
    )

    op.drop_constraint("ck_tender_flags_flag_type", "tender_flags", type_="check")
    quoted = ", ".join(f"'{value}'" for value in _NEW_FLAG_TYPES)
    op.create_check_constraint(
        "ck_tender_flags_flag_type",
        "tender_flags",
        f"flag_type IN ({quoted})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tender_flags_flag_type", "tender_flags", type_="check")
    quoted = ", ".join(f"'{value}'" for value in _OLD_FLAG_TYPES)
    op.create_check_constraint(
        "ck_tender_flags_flag_type",
        "tender_flags",
        f"flag_type IN ({quoted})",
    )

    op.drop_table("tender_quote_reconciliations")

    op.drop_index("ix_tender_line_items_quote_parent", table_name="tender_line_items")
    op.drop_column("tender_line_items", "figure_key")
    op.drop_column("tender_line_items", "counted_in_total")
    op.drop_column("tender_line_items", "amount_ex_gst_cents")
    op.drop_constraint(
        "ck_tender_line_items_gst_basis", "tender_line_items", type_="check"
    )
    op.drop_column("tender_line_items", "gst_basis")
    op.drop_constraint(
        "fk_tender_line_items_duplicate_of_id", "tender_line_items", type_="foreignkey"
    )
    op.drop_column("tender_line_items", "duplicate_of_id")
    op.drop_column("tender_line_items", "is_rollup")
    op.drop_constraint("ck_tender_line_items_role", "tender_line_items", type_="check")
    op.drop_column("tender_line_items", "role")
    op.drop_constraint(
        "fk_tender_line_items_parent_id", "tender_line_items", type_="foreignkey"
    )
    op.drop_column("tender_line_items", "parent_id")

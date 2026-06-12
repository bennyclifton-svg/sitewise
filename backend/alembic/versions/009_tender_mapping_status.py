"""tender mapping, cell status, flags, corrections, reports

Revision ID: 009_tender_mapping_status
Revises: 008_tender_knowledge
Create Date: 2026-06-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009_tender_mapping_status"
down_revision: Union[str, Sequence[str], None] = "008_tender_knowledge"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tender_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cell_code", sa.String(length=32), nullable=False),
        sa.Column("allocation_fraction", sa.Numeric(), nullable=False, server_default="1.0"),
        sa.Column("tier", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column("adjudication", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "qa_state", sa.String(length=32), nullable=False, server_default="needs_review"
        ),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["line_item_id"], ["tender_line_items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["cell_code"], ["taxonomy_cells.code"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "tier IN ('t0_exact', 't1_embedding', 't2_small_llm', 't3_frontier', 'human')",
            name="ck_tender_mappings_tier",
        ),
        sa.CheckConstraint(
            "qa_state IN ('auto_pass', 'needs_review', 'confirmed', 'corrected')",
            name="ck_tender_mappings_qa_state",
        ),
    )
    op.create_index(
        "ix_tender_mappings_line_item_id", "tender_mappings", ["line_item_id"], unique=False
    )

    op.create_table(
        "tender_cell_status",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comparison_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cell_code", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=True),
        sa.Column("bundled_into_cell", sa.String(length=32), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column(
            "qa_state", sa.String(length=32), nullable=False, server_default="needs_review"
        ),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["comparison_id"], ["tender_comparisons.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["quote_id"], ["tender_quotes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cell_code"], ["taxonomy_cells.code"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "comparison_id",
            "quote_id",
            "cell_code",
            name="uq_tender_cell_status_comparison_quote_cell",
        ),
        sa.CheckConstraint(
            "status IN ('included', 'excluded_explicit', 'pc', 'ps', 'bundled', "
            "'not_required', 'silent_ambiguous')",
            name="ck_tender_cell_status_status",
        ),
        sa.CheckConstraint(
            "qa_state IN ('auto_pass', 'needs_review', 'confirmed', 'corrected')",
            name="ck_tender_cell_status_qa_state",
        ),
    )

    op.create_table(
        "tender_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comparison_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cell_code", sa.String(length=32), nullable=True),
        sa.Column("flag_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("headline", sa.String(length=512), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("include_in_report", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "qa_state", sa.String(length=32), nullable=False, server_default="needs_review"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["comparison_id"], ["tender_comparisons.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["quote_id"], ["tender_quotes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "flag_type IN ('gap', 'low_pc_allowance', 'unrealistic_ps', "
            "'missing_expected', 'scope_ambiguity', 'price_outlier', 'exclusion_risk', "
            "'statutory_missing', 'arithmetic_inconsistency')",
            name="ck_tender_flags_flag_type",
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'caution', 'warning')",
            name="ck_tender_flags_severity",
        ),
        sa.CheckConstraint(
            "qa_state IN ('needs_review', 'confirmed', 'suppressed')",
            name="ck_tender_flags_qa_state",
        ),
    )
    op.create_index(
        "ix_tender_flags_comparison_id", "tender_flags", ["comparison_id"], unique=False
    )

    op.create_table(
        "tender_corrections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field", sa.String(length=128), nullable=False),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reviewer", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["reviewer"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tender_corrections_entity_id", "tender_corrections", ["entity_id"], unique=False
    )

    # taxonomy_synonyms.correction_id was created in 008 before this table existed.
    op.create_foreign_key(
        "fk_taxonomy_synonyms_correction_id_tender_corrections",
        "taxonomy_synonyms",
        "tender_corrections",
        ["correction_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "tender_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comparison_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("html_path", sa.String(length=1024), nullable=True),
        sa.Column("pdf_path", sa.String(length=1024), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["comparison_id"], ["tender_comparisons.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["draft_id"], ["draft_artifacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tender_reports_comparison_id", "tender_reports", ["comparison_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_tender_reports_comparison_id", table_name="tender_reports")
    op.drop_table("tender_reports")

    op.drop_constraint(
        "fk_taxonomy_synonyms_correction_id_tender_corrections",
        "taxonomy_synonyms",
        type_="foreignkey",
    )

    op.drop_index("ix_tender_corrections_entity_id", table_name="tender_corrections")
    op.drop_table("tender_corrections")

    op.drop_index("ix_tender_flags_comparison_id", table_name="tender_flags")
    op.drop_table("tender_flags")

    op.drop_table("tender_cell_status")

    op.drop_index("ix_tender_mappings_line_item_id", table_name="tender_mappings")
    op.drop_table("tender_mappings")

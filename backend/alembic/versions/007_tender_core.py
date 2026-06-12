"""tender core pipeline tables

Revision ID: 007_tender_core
Revises: 006_cockpit_refresh_indexes
Create Date: 2026-06-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "007_tender_core"
down_revision: Union[str, Sequence[str], None] = "006_cockpit_refresh_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tender_comparisons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="intake"),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('intake', 'processing', 'qa', 'report_draft', 'approved', "
            "'delivered', 'failed')",
            name="ck_tender_comparisons_status",
        ),
    )
    op.create_index(
        "ix_tender_comparisons_project_id", "tender_comparisons", ["project_id"], unique=False
    )

    op.create_table(
        "tender_quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comparison_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("builder_name", sa.String(length=512), nullable=False),
        sa.Column("builder_abn", sa.String(length=32), nullable=True),
        sa.Column("quote_ref", sa.String(length=255), nullable=True),
        sa.Column("quote_date", sa.Date(), nullable=True),
        sa.Column("stated_total_cents", sa.BigInteger(), nullable=True),
        sa.Column(
            "gst_treatment", sa.String(length=16), nullable=False, server_default="unclear"
        ),
        sa.Column(
            "contract_type", sa.String(length=32), nullable=False, server_default="unknown"
        ),
        sa.Column("validity_days", sa.Integer(), nullable=True),
        sa.Column("stage", sa.String(length=64), nullable=False, server_default="intake"),
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
        sa.CheckConstraint(
            "gst_treatment IN ('inclusive', 'exclusive', 'unclear')",
            name="ck_tender_quotes_gst_treatment",
        ),
        sa.CheckConstraint(
            "contract_type IN ('hia', 'mba', 'custom', 'cost_plus', 'unknown')",
            name="ck_tender_quotes_contract_type",
        ),
        sa.CheckConstraint(
            "stage IN ('intake', 'ingest_document', 'classify_document', "
            "'extract_line_items', 'embed_items', 'map_items', 'run_expectations', "
            "'infer_silence', 'run_analysis', 'generate_flags', "
            "'assemble_report_draft', 'complete')",
            name="ck_tender_quotes_stage",
        ),
    )
    op.create_index(
        "ix_tender_quotes_comparison_id", "tender_quotes", ["comparison_id"], unique=False
    )

    op.create_table(
        "tender_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("doc_type", sa.String(length=64), nullable=True),
        sa.Column("classification_confidence", sa.Numeric(), nullable=True),
        sa.Column("ocr_applied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "ingest_status", sa.String(length=64), nullable=False, server_default="pending"
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
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
        sa.ForeignKeyConstraint(["quote_id"], ["tender_quotes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "quote_id", "content_hash", name="uq_tender_documents_quote_id_content_hash"
        ),
        sa.CheckConstraint(
            "doc_type IN ('quote_letter', 'inclusions_schedule', 'tender_form', 'boq', "
            "'trade_breakdown', 'addendum', 'drawing', 'other')",
            name="ck_tender_documents_doc_type",
        ),
        sa.CheckConstraint(
            "ingest_status IN ('pending', 'ingested', 'duplicate', "
            "'unsupported_format', 'manual_transcription_required', 'failed')",
            name="ck_tender_documents_ingest_status",
        ),
    )
    op.create_index(
        "ix_tender_documents_quote_id", "tender_documents", ["quote_id"], unique=False
    )

    op.create_table(
        "tender_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=False),
        sa.Column("image_path", sa.String(length=1024), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False, server_default=""),
        sa.Column("ocr_confidence", sa.Numeric(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["tender_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id", "page_no", name="uq_tender_pages_document_id_page_no"
        ),
    )

    op.create_table(
        "tender_line_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=False),
        sa.Column("bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("description_raw", sa.Text(), nullable=False),
        sa.Column("section_path", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("qty", sa.Numeric(), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("rate_cents", sa.BigInteger(), nullable=True),
        sa.Column("amount_cents", sa.BigInteger(), nullable=True),
        sa.Column("item_status", sa.String(length=32), nullable=False),
        sa.Column("allowance_cents", sa.BigInteger(), nullable=True),
        sa.Column("extraction_confidence", sa.Numeric(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["quote_id"], ["tender_quotes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["tender_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "item_status IN ('included', 'excluded', 'pc_allowance', 'ps_allowance', 'note')",
            name="ck_tender_line_items_item_status",
        ),
    )
    op.create_index(
        "ix_tender_line_items_quote_id", "tender_line_items", ["quote_id"], unique=False
    )
    op.create_index(
        "ix_tender_line_items_document_id", "tender_line_items", ["document_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_tender_line_items_document_id", table_name="tender_line_items")
    op.drop_index("ix_tender_line_items_quote_id", table_name="tender_line_items")
    op.drop_table("tender_line_items")

    op.drop_table("tender_pages")

    op.drop_index("ix_tender_documents_quote_id", table_name="tender_documents")
    op.drop_table("tender_documents")

    op.drop_index("ix_tender_quotes_comparison_id", table_name="tender_quotes")
    op.drop_table("tender_quotes")

    op.drop_index("ix_tender_comparisons_project_id", table_name="tender_comparisons")
    op.drop_table("tender_comparisons")

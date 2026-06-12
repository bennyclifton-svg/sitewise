"""tender jobs queue and evaluation tables

Revision ID: 010_tender_jobs_eval
Revises: 009_tender_mapping_status
Create Date: 2026-06-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_tender_jobs_eval"
down_revision: Union[str, Sequence[str], None] = "009_tender_mapping_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tender_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("comparison_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=255), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "run_after",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
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
            ["comparison_id"], ["tender_comparisons.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["quote_id"], ["tender_quotes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'done', 'failed')",
            name="ck_tender_jobs_status",
        ),
    )
    op.create_index(
        "ix_tender_jobs_status_run_after", "tender_jobs", ["status", "run_after"], unique=False
    )

    op.create_table(
        "golden_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("doc_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("anonymised", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "source IN ('real', 'synthetic')", name="ck_golden_documents_source"
        ),
        sa.CheckConstraint(
            "difficulty IN ('easy', 'medium', 'hard')",
            name="ck_golden_documents_difficulty",
        ),
    )

    op.create_table(
        "golden_annotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("golden_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("annotation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("annotator", sa.String(length=255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["golden_document_id"], ["golden_documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "eval_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("git_sha", sa.String(length=64), nullable=False),
        sa.Column("prompt_versions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("models", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "eval_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("eval_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("golden_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["eval_run_id"], ["eval_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["golden_document_id"], ["golden_documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("eval_results")
    op.drop_table("eval_runs")
    op.drop_table("golden_annotations")
    op.drop_table("golden_documents")

    op.drop_index("ix_tender_jobs_status_run_after", table_name="tender_jobs")
    op.drop_table("tender_jobs")

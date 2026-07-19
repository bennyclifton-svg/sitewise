"""Freeze immutable Tender intake provenance and file identities.

Revision ID: 030_tender_immutable_intake
Revises: 029_project_document_selections
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "030_tender_immutable_intake"
down_revision = "029_project_document_selections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tender_comparisons", sa.Column("context_provenance", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.add_column("tender_comparisons", sa.Column("input_fingerprint", sa.String(64)))
    op.add_column("tender_comparisons", sa.Column("idempotency_key", sa.String(64)))
    op.create_unique_constraint("uq_tender_comparisons_project_idempotency", "tender_comparisons", ["project_id", "idempotency_key"])
    op.add_column("tender_documents", sa.Column("workspace_file_id", postgresql.UUID(as_uuid=True)))
    op.add_column("tender_documents", sa.Column("storage_bucket", sa.String(255)))
    op.add_column("tender_documents", sa.Column("storage_version", sa.String(255)))
    op.add_column("tender_documents", sa.Column("quote_group_position", sa.Integer()))
    op.add_column("tender_documents", sa.Column("input_position", sa.Integer()))
    op.create_index("ix_tender_documents_workspace_file_id", "tender_documents", ["workspace_file_id"])


def downgrade() -> None:
    op.drop_index("ix_tender_documents_workspace_file_id", table_name="tender_documents")
    for column in ("input_position", "quote_group_position", "storage_version", "storage_bucket", "workspace_file_id"):
        op.drop_column("tender_documents", column)
    op.drop_constraint("uq_tender_comparisons_project_idempotency", "tender_comparisons", type_="unique")
    for column in ("idempotency_key", "input_fingerprint", "context_provenance"):
        op.drop_column("tender_comparisons", column)

"""Add activity_events.deduplication_key and drawing-number lookup index.

Revision ID: 052_activity_event_dedup
Revises: 051_invoice_review_state
"""

from alembic import op
import sqlalchemy as sa


revision = "052_activity_event_dedup"
down_revision = "051_invoice_review_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "activity_events",
        sa.Column("deduplication_key", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "uq_activity_events_project_dedup",
        "activity_events",
        ["project_id", "deduplication_key"],
        unique=True,
        postgresql_where=sa.text("deduplication_key IS NOT NULL"),
    )
    op.execute(
        """
        CREATE INDEX ix_source_documents_project_drawing_number
          ON source_documents (
            project_id,
            (document_metadata->>'drawing_number')
          )
          WHERE document_class = 'drawing'
            AND document_metadata->>'drawing_number' IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_source_documents_project_drawing_number")
    op.drop_index(
        "uq_activity_events_project_dedup",
        table_name="activity_events",
        postgresql_where=sa.text("deduplication_key IS NOT NULL"),
    )
    op.drop_column("activity_events", "deduplication_key")

"""Link issued procurement requests to classified submissions (X1 Stage 20).

Revision ID: 057_procurement_submissions
Revises: 056_email_drafts
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "057_procurement_submissions"
down_revision = "056_email_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_email_drafts",
        sa.Column(
            "references",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "procurement_requests",
        sa.Column(
            "issue_email_draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_email_drafts.id", ondelete="SET NULL"),
        ),
    )
    op.create_table(
        "procurement_request_submissions",
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procurement_requests.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "source_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_procurement_submissions_document",
        "procurement_request_submissions",
        ["source_document_id"],
    )
    op.execute("ALTER TABLE procurement_request_submissions ENABLE ROW LEVEL SECURITY")
    op.execute(
        """CREATE POLICY procurement_request_submissions_owner_policy
        ON procurement_request_submissions
        USING (EXISTS (
            SELECT 1 FROM procurement_requests r
            JOIN projects p ON p.id = r.project_id
            WHERE r.id = procurement_request_submissions.request_id
              AND p.owner_user_id = auth.uid()
        ))
        WITH CHECK (EXISTS (
            SELECT 1 FROM procurement_requests r
            JOIN projects p ON p.id = r.project_id
            WHERE r.id = procurement_request_submissions.request_id
              AND p.owner_user_id = auth.uid()
        ))"""
    )
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            GRANT SELECT, INSERT, UPDATE ON procurement_request_submissions TO authenticated;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON procurement_request_submissions TO service_role;
        END IF;
        END $$"""
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS procurement_request_submissions_owner_policy "
        "ON procurement_request_submissions"
    )
    op.drop_index(
        "ix_procurement_submissions_document",
        table_name="procurement_request_submissions",
    )
    op.drop_table("procurement_request_submissions")
    op.drop_column("procurement_requests", "issue_email_draft_id")
    op.drop_column("project_email_drafts", "references")

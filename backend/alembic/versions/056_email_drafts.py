"""Store project email drafts that cannot send themselves (X1 Stage 19).

Revision ID: 056_email_drafts
Revises: 055_email_intelligence
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "056_email_drafts"
down_revision = "055_email_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_email_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "in_reply_to_email_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_emails.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "to_addresses",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "cc_addresses",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), server_default="", nullable=False),
        sa.Column("provider_draft_id", sa.String(255)),
        sa.Column("provider_message_id", sa.String(255)),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
        sa.Column("send_error", sa.Text()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("sent_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.CheckConstraint(
            "status IN ('draft','sending','sent','send_failed','cancelled')",
            name="ck_email_drafts_status",
        ),
    )
    op.create_index(
        "ix_email_drafts_project_status",
        "project_email_drafts",
        ["project_id", "status"],
    )
    op.execute("ALTER TABLE project_email_drafts ENABLE ROW LEVEL SECURITY")
    op.execute(
        """CREATE POLICY project_email_drafts_owner_policy ON project_email_drafts
        USING (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = project_email_drafts.project_id
              AND p.owner_user_id = auth.uid()
        ))
        WITH CHECK (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = project_email_drafts.project_id
              AND p.owner_user_id = auth.uid()
        ))"""
    )
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            GRANT SELECT, INSERT, UPDATE ON project_email_drafts TO authenticated;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON project_email_drafts TO service_role;
        END IF;
        END $$"""
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS project_email_drafts_owner_policy ON project_email_drafts"
    )
    op.drop_index("ix_email_drafts_project_status", table_name="project_email_drafts")
    op.drop_table("project_email_drafts")

"""Add immutable project email, interpretation overlay, and attachment refs.

Revision ID: 053_project_emails
Revises: 052_activity_event_dedup
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "053_project_emails"
down_revision = "052_activity_event_dedup"
branch_labels = None
depends_on = None


def _rls_and_grants(table: str, *, owner_via: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""CREATE POLICY {table}_owner_policy ON {table}
        USING ({owner_via})
        WITH CHECK ({owner_via})"""
    )
    op.execute(
        f"""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            GRANT SELECT, INSERT, UPDATE ON {table} TO authenticated;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO service_role;
        END IF;
        END $$"""
    )


def upgrade() -> None:
    op.create_table(
        "project_emails",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mailbox_account_id", postgresql.UUID(as_uuid=True)),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=False),
        sa.Column("provider_thread_id", sa.String(255)),
        sa.Column("internet_message_id", sa.String(255)),
        sa.Column("from_address", sa.String(320), nullable=False),
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
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("body_text", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "headers",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("raw_storage_key", sa.String(512)),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_message_id",
            name="uq_project_emails_provider_message",
        ),
        sa.CheckConstraint(
            "provider IN ('fake','microsoft_graph','gmail','inbound_alias')",
            name="ck_project_emails_provider",
        ),
    )
    op.create_table(
        "project_email_interpretations",
        sa.Column(
            "email_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_emails.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
        ),
        sa.Column("match_confidence", sa.Numeric(4, 3)),
        sa.Column("match_basis", sa.String(32)),
        sa.Column("match_reviewed_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("message_category", sa.String(32)),
        sa.Column("summary", sa.Text()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "match_basis IS NULL OR match_basis IN "
            "('contact','domain','thread','alias','subject','user')",
            name="ck_email_interpretations_match_basis",
        ),
        sa.CheckConstraint(
            "match_confidence IS NULL OR "
            "(match_confidence >= 0 AND match_confidence <= 1)",
            name="ck_email_interpretations_match_confidence",
        ),
    )
    op.create_index(
        "ix_email_interpretations_project",
        "project_email_interpretations",
        ["project_id"],
    )
    op.create_table(
        "project_email_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "email_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_emails.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_attachment_id", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64)),
        sa.Column(
            "source_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_documents.id", ondelete="SET NULL"),
        ),
        sa.UniqueConstraint(
            "email_id",
            "provider_attachment_id",
            name="uq_email_attachments_email_provider",
        ),
    )

    linked_owner = """EXISTS (
            SELECT 1 FROM project_email_interpretations i
            JOIN projects p ON p.id = i.project_id
            WHERE i.email_id = project_emails.id
              AND p.owner_user_id = auth.uid()
        )"""
    interpretation_owner = """project_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = project_email_interpretations.project_id
              AND p.owner_user_id = auth.uid()
        )"""
    attachment_owner = """EXISTS (
            SELECT 1 FROM project_email_interpretations i
            JOIN projects p ON p.id = i.project_id
            WHERE i.email_id = project_email_attachments.email_id
              AND p.owner_user_id = auth.uid()
        )"""
    _rls_and_grants("project_emails", owner_via=linked_owner)
    _rls_and_grants("project_email_interpretations", owner_via=interpretation_owner)
    _rls_and_grants("project_email_attachments", owner_via=attachment_owner)


def downgrade() -> None:
    for table in (
        "project_email_attachments",
        "project_email_interpretations",
        "project_emails",
    ):
        op.execute(f"DROP POLICY IF EXISTS {table}_owner_policy ON {table}")
    op.drop_table("project_email_attachments")
    op.drop_index(
        "ix_email_interpretations_project",
        table_name="project_email_interpretations",
    )
    op.drop_table("project_email_interpretations")
    op.drop_table("project_emails")

"""Persist official web sources used by Pi answers.

Revision ID: 042_message_web_citations
Revises: 041_cost_plan_tbc_invoice_edits
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "042_message_web_citations"
down_revision = "041_cost_plan_tbc_invoice_edits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_web_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "turn_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_turns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("publisher", sa.String(512)),
        sa.Column("jurisdiction", sa.String(32)),
        sa.Column("authority_class", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("version_status", sa.String(32), nullable=False),
        sa.Column("effective_date", sa.String(128)),
        sa.Column("section", sa.String(255)),
        sa.Column("excerpt", sa.Text()),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("citation_metadata", postgresql.JSONB()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "message_id",
            "content_hash",
            name="uq_message_web_citations_message_hash",
        ),
    )
    op.create_index(
        "ix_message_web_citations_message_id",
        "message_web_citations",
        ["message_id"],
    )
    op.create_index(
        "ix_message_web_citations_project_created_at",
        "message_web_citations",
        ["project_id", "created_at"],
    )
    op.execute("ALTER TABLE message_web_citations ENABLE ROW LEVEL SECURITY")
    op.execute(
        """CREATE POLICY message_web_citations_owner_policy
        ON message_web_citations FOR ALL
        USING (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = message_web_citations.project_id
              AND p.owner_user_id = auth.uid()
        ))
        WITH CHECK (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = message_web_citations.project_id
              AND p.owner_user_id = auth.uid()
        ))"""
    )
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON message_web_citations TO authenticated;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON message_web_citations TO service_role;
        END IF;
        END $$"""
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS message_web_citations_owner_policy "
        "ON message_web_citations"
    )
    op.drop_index(
        "ix_message_web_citations_project_created_at",
        table_name="message_web_citations",
    )
    op.drop_index(
        "ix_message_web_citations_message_id",
        table_name="message_web_citations",
    )
    op.drop_table("message_web_citations")

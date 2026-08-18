"""Add document_classification_overrides for human corrections (X1 Stage 5).

Revision ID: 048_classification_overrides
Revises: 047_programme
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "048_classification_overrides"
down_revision = "047_programme"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_classification_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("relative_path", sa.String(1024), nullable=True),
        sa.Column("key_basis", sa.String(16), nullable=False),
        sa.Column("document_class", sa.String(64), nullable=False),
        sa.Column("document_subject", sa.String(64), nullable=True),
        sa.Column("previous_class", sa.String(64), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "key_basis IN ('content_hash', 'relative_path')",
            name="ck_override_key_basis",
        ),
        sa.CheckConstraint(
            "(key_basis = 'content_hash' AND content_hash IS NOT NULL) OR "
            "(key_basis = 'relative_path' AND relative_path IS NOT NULL)",
            name="ck_override_key_present",
        ),
    )
    op.create_index(
        "uq_override_project_hash",
        "document_classification_overrides",
        ["project_id", "content_hash"],
        unique=True,
        postgresql_where=sa.text("content_hash IS NOT NULL"),
    )
    op.create_index(
        "uq_override_project_path",
        "document_classification_overrides",
        ["project_id", "relative_path"],
        unique=True,
        postgresql_where=sa.text("content_hash IS NULL"),
    )
    op.execute("ALTER TABLE document_classification_overrides ENABLE ROW LEVEL SECURITY")
    op.execute(
        """CREATE POLICY document_classification_overrides_owner_policy
        ON document_classification_overrides
        USING (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = document_classification_overrides.project_id
              AND p.owner_user_id = auth.uid()
        ))
        WITH CHECK (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = document_classification_overrides.project_id
              AND p.owner_user_id = auth.uid()
        ))"""
    )
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            GRANT SELECT, INSERT, UPDATE ON document_classification_overrides
                TO authenticated;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON document_classification_overrides
                TO service_role;
        END IF;
        END $$"""
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS document_classification_overrides_owner_policy "
        "ON document_classification_overrides"
    )
    op.drop_index(
        "uq_override_project_path",
        table_name="document_classification_overrides",
    )
    op.drop_index(
        "uq_override_project_hash",
        table_name="document_classification_overrides",
    )
    op.drop_table("document_classification_overrides")

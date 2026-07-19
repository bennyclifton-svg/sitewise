"""Add canonical artefact revision export state.

Revision ID: 031_artefact_revisions
Revises: 030_tender_immutable_intake
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "031_artefact_revisions"
down_revision = "030_tender_immutable_intake"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_draft_artifacts_author_user_id_users",
        "draft_artifacts",
        "users",
        ["author_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column(
        "draft_artifacts",
        sa.Column("is_stale", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("draft_artifacts", sa.Column("stale_reason", sa.Text()))
    op.create_table(
        "artefact_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("draft_artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("export_type", sa.String(32), nullable=False),
        sa.Column("workspace_path", sa.String(1024), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("error", sa.Text()),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("draft_id", "export_type", name="uq_artefact_exports_draft_type"),
        sa.UniqueConstraint("storage_key", name="uq_artefact_exports_storage_key"),
    )
    op.create_index("ix_artefact_exports_project_status", "artefact_exports", ["project_id", "status"])
    op.create_index("ix_artefact_exports_draft_id", "artefact_exports", ["draft_id"])
    op.execute("ALTER TABLE artefact_exports ENABLE ROW LEVEL SECURITY")
    op.execute(
        """CREATE POLICY artefact_exports_owner_policy ON artefact_exports
        USING (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = artefact_exports.project_id AND p.owner_user_id = auth.uid()
        ))
        WITH CHECK (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = artefact_exports.project_id AND p.owner_user_id = auth.uid()
        ))"""
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS artefact_exports_owner_policy ON artefact_exports")
    op.drop_index("ix_artefact_exports_draft_id", table_name="artefact_exports")
    op.drop_index("ix_artefact_exports_project_status", table_name="artefact_exports")
    op.drop_table("artefact_exports")
    op.drop_column("draft_artifacts", "stale_reason")
    op.drop_column("draft_artifacts", "is_stale")
    op.drop_constraint(
        "fk_draft_artifacts_author_user_id_users",
        "draft_artifacts",
        type_="foreignkey",
    )

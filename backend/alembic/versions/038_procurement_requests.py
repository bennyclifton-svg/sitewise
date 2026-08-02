"""Add the slim project procurement request register.

Revision ID: 038_procurement_requests
Revises: 037_typed_cost_plans
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "038_procurement_requests"
down_revision = "037_typed_cost_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "procurement_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("target_name", sa.String(512), nullable=False),
        sa.Column("target_slug", sa.String(255), nullable=False),
        sa.Column("status", sa.String(24), server_default="draft", nullable=False),
        sa.Column(
            "current_draft_artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("draft_artifacts.id", ondelete="RESTRICT"),
        ),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "kind IN ('consultant_rfp','contractor_eoi','trade_rft','trade_rfq')",
            name="ck_procurement_requests_kind",
        ),
        sa.CheckConstraint(
            "status IN ('draft','issued','closed','cancelled')",
            name="ck_procurement_requests_status",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_procurement_requests_revision"),
    )
    op.create_index(
        "ix_procurement_requests_project_updated",
        "procurement_requests",
        ["project_id", "updated_at"],
    )
    op.create_index(
        "ix_procurement_requests_project_status",
        "procurement_requests",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_procurement_requests_current_draft",
        "procurement_requests",
        ["current_draft_artifact_id"],
    )
    op.execute("ALTER TABLE procurement_requests ENABLE ROW LEVEL SECURITY")
    op.execute(
        """CREATE POLICY procurement_requests_owner_policy ON procurement_requests
        USING (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = procurement_requests.project_id
              AND p.owner_user_id = auth.uid()
        ))
        WITH CHECK (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = procurement_requests.project_id
              AND p.owner_user_id = auth.uid()
        ))"""
    )
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            GRANT SELECT, INSERT, UPDATE ON procurement_requests TO authenticated;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON procurement_requests TO service_role;
        END IF;
        END $$"""
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS procurement_requests_owner_policy ON procurement_requests"
    )
    op.drop_index(
        "ix_procurement_requests_current_draft", table_name="procurement_requests"
    )
    op.drop_index(
        "ix_procurement_requests_project_status", table_name="procurement_requests"
    )
    op.drop_index(
        "ix_procurement_requests_project_updated", table_name="procurement_requests"
    )
    op.drop_table("procurement_requests")

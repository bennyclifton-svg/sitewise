"""Add typed programme versions and activities.

Revision ID: 047_programme
Revises: 046_workflow_run_queue_scope
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "047_programme"
down_revision = "046_workflow_run_queue_scope"
branch_labels = None
depends_on = None


def _owner_policy(table: str, project_expression: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""CREATE POLICY {table}_owner_policy ON {table}
        USING (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = {project_expression} AND p.owner_user_id = auth.uid()
        ))
        WITH CHECK (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = {project_expression} AND p.owner_user_id = auth.uid()
        ))"""
    )


def upgrade() -> None:
    op.create_table(
        "programme_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(24), server_default="proposed", nullable=False),
        sa.Column("view_scale", sa.String(16), server_default="month", nullable=False),
        sa.Column(
            "pmp_embed_visible",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('proposed','accepted','superseded')",
            name="ck_programme_versions_status",
        ),
        sa.CheckConstraint(
            "view_scale IN ('week','month','quarter')",
            name="ck_programme_versions_view_scale",
        ),
        sa.UniqueConstraint(
            "project_id", "version", name="uq_programme_versions_project_version"
        ),
    )
    op.create_index(
        "ix_programme_versions_project_status",
        "programme_versions",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_programme_versions_created_by",
        "programme_versions",
        ["created_by_user_id"],
    )

    op.create_table(
        "programme_activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "programme_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("programme_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("activity_key", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("parent_key", sa.String(255)),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("finish_date", sa.Date(), nullable=False),
        sa.Column("predecessor_key", sa.String(255)),
        sa.Column("lag_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("assumption", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('stage','activity','milestone')",
            name="ck_programme_activities_kind",
        ),
        sa.CheckConstraint(
            "duration_days >= 0",
            name="ck_programme_activities_duration",
        ),
        sa.CheckConstraint(
            "(kind <> 'milestone') OR duration_days = 0",
            name="ck_programme_activities_milestone_duration",
        ),
        sa.CheckConstraint(
            "(kind <> 'stage') OR parent_key IS NULL",
            name="ck_programme_activities_stage_parent",
        ),
        sa.CheckConstraint(
            "(kind = 'stage') OR parent_key IS NOT NULL",
            name="ck_programme_activities_child_parent",
        ),
        sa.UniqueConstraint(
            "programme_version_id",
            "activity_key",
            name="uq_programme_activities_version_key",
        ),
    )
    op.create_index(
        "ix_programme_activities_version",
        "programme_activities",
        ["programme_version_id"],
    )

    _owner_policy("programme_versions", "programme_versions.project_id")
    _owner_policy(
        "programme_activities",
        (
            "(SELECT v.project_id FROM programme_versions v "
            "WHERE v.id = programme_activities.programme_version_id)"
        ),
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS programme_activities_owner_policy ON programme_activities")
    op.execute("DROP POLICY IF EXISTS programme_versions_owner_policy ON programme_versions")
    op.drop_index("ix_programme_activities_version", table_name="programme_activities")
    op.drop_table("programme_activities")
    op.drop_index("ix_programme_versions_created_by", table_name="programme_versions")
    op.drop_index("ix_programme_versions_project_status", table_name="programme_versions")
    op.drop_table("programme_versions")

"""sitewise projects and draft artifacts

Revision ID: 003_sitewise_projects_and_drafts
Revises: 002_ingest_metadata
Create Date: 2026-06-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_sitewise_projects_and_drafts"
down_revision: Union[str, Sequence[str], None] = "002_ingest_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("workspace_path", sa.String(length=1024), nullable=False),
        sa.Column("phase", sa.String(length=64), nullable=False, server_default="procurement"),
        sa.Column("archetype", sa.String(length=64), nullable=True),
        sa.Column("user_role", sa.String(length=64), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="active"),
        sa.Column("project_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", "slug", name="uq_projects_owner_user_id_slug"),
    )
    op.create_index("ix_projects_owner_user_id", "projects", ["owner_user_id"], unique=False)

    op.add_column(
        "chat_threads",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_chat_threads_project_id_projects",
        "chat_threads",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_chat_threads_project_id", "chat_threads", ["project_id"], unique=False)

    op.create_table(
        "draft_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_type", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="draft"),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("workspace_path", sa.String(length=1024), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("runtime", sa.String(length=128), nullable=False, server_default="clerk-sitewise"),
        sa.Column("provenance_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "workflow_type",
            "version",
            name="uq_draft_artifacts_project_workflow_version",
        ),
    )
    op.create_index(
        "ix_draft_artifacts_project_id_workflow_type",
        "draft_artifacts",
        ["project_id", "workflow_type"],
        unique=False,
    )

    op.execute("ALTER TABLE projects ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE draft_artifacts ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY projects_owner_policy ON projects
        FOR ALL
        USING (owner_user_id = auth.uid())
        WITH CHECK (owner_user_id = auth.uid())
        """
    )
    op.execute(
        """
        CREATE POLICY draft_artifacts_owner_policy ON draft_artifacts
        FOR ALL
        USING (
            EXISTS (
                SELECT 1
                FROM projects
                WHERE projects.id = draft_artifacts.project_id
                  AND projects.owner_user_id = auth.uid()
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM projects
                WHERE projects.id = draft_artifacts.project_id
                  AND projects.owner_user_id = auth.uid()
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS draft_artifacts_owner_policy ON draft_artifacts")
    op.execute("DROP POLICY IF EXISTS projects_owner_policy ON projects")

    op.drop_index("ix_draft_artifacts_project_id_workflow_type", table_name="draft_artifacts")
    op.drop_table("draft_artifacts")

    op.drop_index("ix_chat_threads_project_id", table_name="chat_threads")
    op.drop_constraint("fk_chat_threads_project_id_projects", "chat_threads", type_="foreignkey")
    op.drop_column("chat_threads", "project_id")

    op.drop_index("ix_projects_owner_user_id", table_name="projects")
    op.drop_table("projects")

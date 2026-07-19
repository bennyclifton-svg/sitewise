"""Add immutable purpose-scoped project document selections.

Revision ID: 029_project_document_selections
Revises: 028_project_decision_revisions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "029_project_document_selections"
down_revision = "028_project_decision_revisions"
branch_labels = None
depends_on = None


def _uuid(name: str, *, nullable: bool = False) -> sa.Column:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "project_document_selections",
        _uuid("id"), _uuid("project_id"), sa.Column("purpose", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        _uuid("selected_by"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selected_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "purpose", name="uq_project_document_selections_project_purpose"),
    )
    op.create_index("ix_project_document_selections_project_id", "project_document_selections", ["project_id"])
    op.create_table(
        "project_document_selection_revisions",
        _uuid("id"), _uuid("selection_id"), _uuid("project_id"),
        sa.Column("purpose", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False), _uuid("selected_by"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["selection_id"], ["project_document_selections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selected_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("selection_id", "revision", name="uq_project_document_selection_revisions_selection_revision"),
    )
    op.create_index("ix_project_document_selection_revisions_project_purpose", "project_document_selection_revisions", ["project_id", "purpose"])
    op.create_table(
        "project_document_selection_groups",
        _uuid("id"), _uuid("selection_revision_id"), _uuid("project_id"),
        sa.Column("label", sa.String(512), nullable=False), sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["selection_revision_id"], ["project_document_selection_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("selection_revision_id", "position", name="uq_project_document_selection_groups_revision_position"),
    )
    op.create_index("ix_project_document_selection_groups_project_id", "project_document_selection_groups", ["project_id"])
    op.create_table(
        "project_document_selection_items",
        _uuid("id"), _uuid("group_id"), _uuid("project_id"), _uuid("workspace_file_id"),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["project_document_selection_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_file_id"], ["workspace_files.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "position", name="uq_project_document_selection_items_group_position"),
        sa.UniqueConstraint("group_id", "workspace_file_id", name="uq_project_document_selection_items_group_file"),
    )
    op.create_index("ix_project_document_selection_items_project_file", "project_document_selection_items", ["project_id", "workspace_file_id"])
    op.create_table(
        "workflow_input_retention_locks",
        _uuid("id"), _uuid("project_id"), _uuid("workspace_file_id"),
        sa.Column("workflow_type", sa.String(64), nullable=False), _uuid("workflow_id"),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_file_id"], ["workspace_files.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_type", "workflow_id", "workspace_file_id", name="uq_workflow_input_retention_lock"),
    )
    op.create_index("ix_workflow_input_retention_locks_project_file", "workflow_input_retention_locks", ["project_id", "workspace_file_id"])

    for table in (
        "project_document_selections", "project_document_selection_revisions",
        "project_document_selection_groups", "project_document_selection_items",
        "workflow_input_retention_locks",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""CREATE POLICY {table}_owner_policy ON {table}
            USING (EXISTS (SELECT 1 FROM projects p WHERE p.id = {table}.project_id AND p.owner_user_id = auth.uid()))
            WITH CHECK (EXISTS (SELECT 1 FROM projects p WHERE p.id = {table}.project_id AND p.owner_user_id = auth.uid()))""")


def downgrade() -> None:
    for table in (
        "workflow_input_retention_locks", "project_document_selection_items",
        "project_document_selection_groups", "project_document_selection_revisions",
        "project_document_selections",
    ):
        op.execute(f"DROP POLICY IF EXISTS {table}_owner_policy ON {table}")
    op.drop_table("workflow_input_retention_locks")
    op.drop_table("project_document_selection_items")
    op.drop_table("project_document_selection_groups")
    op.drop_table("project_document_selection_revisions")
    op.drop_table("project_document_selections")

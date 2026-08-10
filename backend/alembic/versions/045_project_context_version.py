"""Separate canonical project context version from the audit event cursor.

Revision ID: 045_project_context_version
Revises: 044_cost_plan_item_order
"""

from alembic import op
import sqlalchemy as sa


revision = "045_project_context_version"
down_revision = "044_cost_plan_item_order"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("project_context_version", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE projects
        SET project_context_version = GREATEST(COALESCE(event_sequence, 0) + 1, 1)
        """
    )
    op.alter_column(
        "projects",
        "project_context_version",
        nullable=False,
        server_default=sa.text("1"),
    )
    op.create_check_constraint(
        "ck_projects_project_context_version",
        "projects",
        "project_context_version >= 1",
    )

    op.add_column(
        "workflow_runs",
        sa.Column("frozen_project_context_version", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE workflow_runs AS run
        SET frozen_project_context_version = COALESCE(
            (run.run_brief -> 'generation_context' ->> 'context_version')::integer,
            (run.run_brief -> 'snapshot' ->> 'context_version')::integer,
            project.project_context_version
        )
        FROM projects AS project
        WHERE project.id = run.project_id
        """
    )
    op.alter_column(
        "workflow_runs",
        "frozen_project_context_version",
        nullable=False,
    )
    op.create_check_constraint(
        "ck_workflow_runs_frozen_project_context_version",
        "workflow_runs",
        "frozen_project_context_version >= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_workflow_runs_frozen_project_context_version",
        "workflow_runs",
        type_="check",
    )
    op.drop_column("workflow_runs", "frozen_project_context_version")
    op.drop_constraint(
        "ck_projects_project_context_version",
        "projects",
        type_="check",
    )
    op.drop_column("projects", "project_context_version")

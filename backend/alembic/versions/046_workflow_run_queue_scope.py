"""Scope workflow runs to the environment that enqueued them.

Every deployment pointed at this Supabase project polls the same
`workflow_runs` table, so a run queued by local dev could be claimed and
executed by production running different code. The claim query now filters on
`queue_scope`, and each environment sets `WORKFLOW_QUEUE_SCOPE` to its own name.

Existing rows default to `production` — that is where they were served from.

Revision ID: 046_workflow_run_queue_scope
Revises: 045_project_context_version
"""

from alembic import op
import sqlalchemy as sa


revision = "046_workflow_run_queue_scope"
down_revision = "045_project_context_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column(
            "queue_scope",
            sa.String(length=32),
            nullable=False,
            server_default="production",
        ),
    )
    # The claim query leads with queue_scope, so the existing index no longer
    # covers it.
    op.drop_index("ix_workflow_runs_claim", table_name="workflow_runs")
    op.create_index(
        "ix_workflow_runs_claim",
        "workflow_runs",
        ["queue_scope", "state", "run_after", "lease_expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_runs_claim", table_name="workflow_runs")
    op.create_index(
        "ix_workflow_runs_claim",
        "workflow_runs",
        ["state", "run_after", "lease_expires_at"],
    )
    op.drop_column("workflow_runs", "queue_scope")

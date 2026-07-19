"""Add durable core workflow runs.

Revision ID: 032_workflow_runs
Revises: 031_artefact_revisions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "032_workflow_runs"
down_revision = "031_artefact_revisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requested_by_thread_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_threads.id", ondelete="SET NULL")),
        sa.Column("requested_by_turn_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_turns.id", ondelete="SET NULL")),
        sa.Column("workflow_type", sa.String(64), nullable=False),
        sa.Column("run_brief", postgresql.JSONB(), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("schema_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("canonical_request_hash", sa.String(64), nullable=False),
        sa.Column("frozen_profile_revision", sa.Integer(), nullable=False),
        sa.Column("frozen_snapshot_fingerprint", sa.String(64), nullable=False),
        sa.Column("frozen_evidence_fingerprint", sa.String(64), nullable=False),
        sa.Column("frozen_decision_set_revision", sa.Integer(), nullable=False),
        sa.Column("frozen_selection_revision", sa.Integer()),
        sa.Column("frozen_artefact_version", sa.Integer()),
        sa.Column("state", sa.String(24), server_default="queued", nullable=False),
        sa.Column("attempt", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
        sa.Column("lock_owner", sa.String(255)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("run_after", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("progress", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("stage_durations_ms", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("result_artefact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("draft_artifacts.id", ondelete="SET NULL")),
        sa.Column("result_reference", postgresql.JSONB()),
        sa.Column("error_class", sa.String(255)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("state IN ('queued','running','needs_input','complete','failed','cancelled')", name="ck_workflow_runs_state"),
        sa.CheckConstraint("attempt >= 0 AND max_attempts > 0", name="ck_workflow_runs_attempts"),
        sa.UniqueConstraint("project_id", "workflow_type", "idempotency_key", name="uq_workflow_runs_project_type_idempotency"),
    )
    op.create_index("ix_workflow_runs_claim", "workflow_runs", ["state", "run_after", "lease_expires_at"])
    op.create_index("ix_workflow_runs_project_created", "workflow_runs", ["project_id", "created_at"])
    op.create_index("ix_workflow_runs_requested_by_user", "workflow_runs", ["requested_by_user_id"])
    op.execute("ALTER TABLE workflow_runs ENABLE ROW LEVEL SECURITY")
    op.execute(
        """CREATE POLICY workflow_runs_owner_policy ON workflow_runs
        USING (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = workflow_runs.project_id AND p.owner_user_id = auth.uid()
        ))
        WITH CHECK (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = workflow_runs.project_id AND p.owner_user_id = auth.uid()
        ))"""
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS workflow_runs_owner_policy ON workflow_runs")
    op.drop_index("ix_workflow_runs_requested_by_user", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_project_created", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_claim", table_name="workflow_runs")
    op.drop_table("workflow_runs")

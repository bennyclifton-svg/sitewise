"""Add revisioned, lockable Project Decisions.

Revision ID: 028_project_decision_revisions
Revises: 027_profile_proposals
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "028_project_decision_revisions"
down_revision = "027_profile_proposals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "decision_set_revision", sa.Integer(), server_default="1", nullable=False
        ),
    )
    op.add_column(
        "project_decisions",
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "project_decisions",
        sa.Column("locked", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "project_decisions",
        sa.Column(
            "evidence_conflict", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )
    op.add_column(
        "project_decisions", sa.Column("agent_suggestion", sa.String(length=128))
    )
    op.add_column(
        "project_decisions",
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.execute("UPDATE project_decisions SET locked = true WHERE source = 'user'")


def downgrade() -> None:
    op.drop_column("project_decisions", "provenance")
    op.drop_column("project_decisions", "agent_suggestion")
    op.drop_column("project_decisions", "evidence_conflict")
    op.drop_column("project_decisions", "locked")
    op.drop_column("project_decisions", "revision")
    op.drop_column("projects", "decision_set_revision")

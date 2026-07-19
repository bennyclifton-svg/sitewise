"""Bind mutation intent and persist Project Profile proposals.

Revision ID: 027_profile_proposals
Revises: 026_project_events
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "027_profile_proposals"
down_revision = "026_project_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_turns",
        sa.Column("user_message_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "agent_turns",
        sa.Column(
            "mutation_scopes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "agent_turns",
        sa.Column(
            "mutation_intent",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_table(
        "project_profile_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_revision", sa.Integer(), nullable=False),
        sa.Column("current_values", postgresql.JSONB(), nullable=False),
        sa.Column("proposed_values", postgresql.JSONB(), nullable=False),
        sa.Column(
            "evidence_references",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("proposer", sa.String(length=128), nullable=False),
        sa.Column("resolver_source", sa.String(length=128), nullable=True),
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
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_project_profile_proposals_confidence",
        ),
        sa.CheckConstraint(
            "state IN ('pending', 'accepted', 'rejected')",
            name="ck_project_profile_proposals_state",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_project_profile_proposals_project_state_created",
        "project_profile_proposals",
        ["project_id", "state", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_profile_proposals_project_state_created",
        table_name="project_profile_proposals",
    )
    op.drop_table("project_profile_proposals")
    op.drop_column("agent_turns", "mutation_intent")
    op.drop_column("agent_turns", "mutation_scopes")
    op.drop_column("agent_turns", "user_message_hash")

"""Persist revocable, chargeable agent turns.

Revision ID: 023_agent_turns
Revises: 022_source_doc_uuid_contract
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "023_agent_turns"
down_revision = "022_source_doc_uuid_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "thread_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_threads.id", ondelete="SET NULL"),
        ),
        sa.Column("user_message_id", sa.String(255), nullable=False),
        sa.Column("state", sa.String(32), nullable=False, server_default="active"),
        sa.Column("runtime", sa.String(32), nullable=False),
        sa.Column("model", sa.String(255)),
        sa.Column("status", sa.String(32), nullable=False, server_default="reserved"),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_agent_turns_project_id_created_at", "agent_turns", ["project_id", "created_at"]
    )
    op.create_index(
        "ix_agent_turns_user_id_created_at", "agent_turns", ["user_id", "created_at"]
    )
    op.create_index(
        "uq_agent_turns_user_project_message",
        "agent_turns",
        ["user_id", "project_id", "user_message_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("agent_turns")

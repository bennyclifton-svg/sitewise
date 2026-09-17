"""Durable Pi stream replay and correlated MCP calls."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "065_agent_replay"
down_revision = "064_procurement_award"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_turn_events",
        sa.Column(
            "turn_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("agent_turns.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("sequence", sa.Integer(), primary_key=True),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("terminal", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "agent_tool_calls",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "turn_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("agent_turns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tool", sa.String(128), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("error_type", sa.String(128)),
        sa.Column("committed_revisions", pg.JSONB(), nullable=False),
        sa.Column("providers", pg.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_agent_tool_calls_turn_id", "agent_tool_calls", ["turn_id"])
    # Browser clients access these through authenticated FastAPI routes only.
    for table in ("agent_turn_events", "agent_tool_calls"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("agent_tool_calls")
    op.drop_table("agent_turn_events")

"""Store server-derived UI context for durable agent turns.

Revision ID: 039_agent_turn_input_context
Revises: 038_procurement_requests
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "039_agent_turn_input_context"
down_revision = "038_procurement_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_turns",
        sa.Column(
            "input_context",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("agent_turns", "input_context")

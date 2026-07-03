"""tender telemetry events

Revision ID: 015_tender_telemetry_events
Revises: 014_chat_threads_hermes_session
Create Date: 2026-07-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015_tender_telemetry_events"
down_revision: Union[str, Sequence[str], None] = "014_chat_threads_hermes_session"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tender_telemetry_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comparison_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("llm_calls", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cache_hits", sa.Integer(), nullable=False),
        sa.Column(
            "event_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["comparison_id"],
            ["tender_comparisons.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["tender_jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tender_telemetry_events_comparison_id",
        "tender_telemetry_events",
        ["comparison_id"],
    )
    op.create_index(
        "ix_tender_telemetry_events_comparison_stage",
        "tender_telemetry_events",
        ["comparison_id", "stage"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tender_telemetry_events_comparison_stage",
        table_name="tender_telemetry_events",
    )
    op.drop_index(
        "ix_tender_telemetry_events_comparison_id",
        table_name="tender_telemetry_events",
    )
    op.drop_table("tender_telemetry_events")

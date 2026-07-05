"""project decisions

Revision ID: 019_project_decisions
Revises: 018_project_taxonomy
Create Date: 2026-07-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "019_project_decisions"
down_revision: Union[str, Sequence[str], None] = "018_project_taxonomy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", sa.String(length=128), nullable=False),
        sa.Column("section", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("label", sa.String(length=256), nullable=False),
        sa.Column(
            "options",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("selected", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="agent"),
        sa.Column(
            "workflow_type",
            sa.String(length=128),
            nullable=False,
            server_default="create_pmp",
        ),
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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "decision_id", name="uq_project_decisions_project_decision"),
    )
    op.create_index(
        "ix_project_decisions_project_id",
        "project_decisions",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_decisions_project_id", table_name="project_decisions")
    op.drop_table("project_decisions")

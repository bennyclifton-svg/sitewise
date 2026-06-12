"""tender report language table and benchmark stable-key constraint

Revision ID: 011_tender_report_language
Revises: 010_tender_jobs_eval
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011_tender_report_language"
down_revision: Union[str, Sequence[str], None] = "010_tender_jobs_eval"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_language",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_path", sa.String(length=255), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_path", name="uq_report_language_key_path"),
    )

    # The seed loader upserts benchmarks ON CONFLICT on the stable key; the
    # constraint was missing from 008.
    op.create_unique_constraint(
        "uq_benchmarks_stable_key",
        "benchmarks",
        ["benchmark_key", "state", "region", "build_type", "spec_level", "metric"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_benchmarks_stable_key", "benchmarks", type_="unique")
    op.drop_table("report_language")

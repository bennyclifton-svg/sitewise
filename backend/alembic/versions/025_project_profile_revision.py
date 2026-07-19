"""Add the optimistic revision counter for Project Profile updates.

Revision ID: 025_project_profile_revision
Revises: 024_tender_quote_total_source
"""

from alembic import op
import sqlalchemy as sa

revision = "025_project_profile_revision"
down_revision = "024_tender_quote_total_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "profile_revision",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "profile_revision")

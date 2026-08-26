"""Persist collapsed Programme parent stages.

Revision ID: 060_programme_collapsed_stages
Revises: 059_email_provider_mailgun
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "060_programme_collapsed_stages"
down_revision = "059_email_provider_mailgun"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "programme_versions",
        sa.Column(
            "collapsed_stage_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("programme_versions", "collapsed_stage_keys")

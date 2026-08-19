"""Store email action candidates and close message_category (X1 Stage 18).

Revision ID: 055_email_intelligence
Revises: 054_email_match_default
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "055_email_intelligence"
down_revision = "054_email_match_default"
branch_labels = None
depends_on = None

_CATEGORIES = (
    "action_required",
    "decision_required",
    "design_change",
    "rfi",
    "instruction",
    "programme_change",
    "document_transmittal",
    "approval",
    "invoice_notice",
    "fee_proposal",
    "tender_submission",
    "meeting",
    "information_only",
    "unknown",
)


def upgrade() -> None:
    op.add_column(
        "project_email_interpretations",
        sa.Column(
            "actions",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_email_interpretations_message_category",
        "project_email_interpretations",
        "message_category IS NULL OR message_category IN ('"
        + "','".join(_CATEGORIES)
        + "')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_email_interpretations_message_category",
        "project_email_interpretations",
        type_="check",
    )
    op.drop_column("project_email_interpretations", "actions")

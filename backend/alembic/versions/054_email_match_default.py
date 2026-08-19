"""Allow match_basis=default for unmatched project emails (X1 Stage 17).

Revision ID: 054_email_match_default
Revises: 053_project_emails
"""

from alembic import op


revision = "054_email_match_default"
down_revision = "053_project_emails"
branch_labels = None
depends_on = None

_NEW = (
    "match_basis IS NULL OR match_basis IN "
    "('contact','domain','thread','alias','subject','user','default')"
)
_OLD = (
    "match_basis IS NULL OR match_basis IN "
    "('contact','domain','thread','alias','subject','user')"
)


def upgrade() -> None:
    op.drop_constraint(
        "ck_email_interpretations_match_basis",
        "project_email_interpretations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_email_interpretations_match_basis",
        "project_email_interpretations",
        _NEW,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_email_interpretations_match_basis",
        "project_email_interpretations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_email_interpretations_match_basis",
        "project_email_interpretations",
        _OLD,
    )

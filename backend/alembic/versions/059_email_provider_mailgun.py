"""Allow 'mailgun' as an email provider.

Outbound now sends through Mailgun from the project's own alias, so the
provider check constraint has to admit it or any message row recorded against
that provider fails at write time.

Revision ID: 059_email_provider_mailgun
Revises: 058_procurement_strategy
"""

from alembic import op

revision = "059_email_provider_mailgun"
down_revision = "058_procurement_strategy"
branch_labels = None
depends_on = None

_CONSTRAINT = "ck_project_emails_provider"
_TABLE = "project_emails"
_WITH_MAILGUN = "'fake','microsoft_graph','gmail','mailgun','inbound_alias'"
_WITHOUT_MAILGUN = "'fake','microsoft_graph','gmail','inbound_alias'"


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, _TABLE, type_="check")
    op.create_check_constraint(
        _CONSTRAINT, _TABLE, f"provider IN ({_WITH_MAILGUN})"
    )


def downgrade() -> None:
    # Any mailgun rows would violate the narrower constraint; there is nothing
    # sensible to rewrite them to, so refuse rather than lose provenance.
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM project_emails WHERE provider = 'mailgun') THEN "
        "RAISE EXCEPTION 'project_emails still has mailgun rows'; "
        "END IF; END $$"
    )
    op.drop_constraint(_CONSTRAINT, _TABLE, type_="check")
    op.create_check_constraint(
        _CONSTRAINT, _TABLE, f"provider IN ({_WITHOUT_MAILGUN})"
    )

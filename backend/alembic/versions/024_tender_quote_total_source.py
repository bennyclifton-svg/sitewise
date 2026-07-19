"""Track provenance of tender quote stated totals.

Adds ``tender_quotes.stated_total_source`` ('manual' | 'extracted') so the
extraction pipeline can persist the printed quote total without clobbering
operator-entered values. Existing non-null totals all came from the
QuoteCreate request body, so they are stamped 'manual'.

Revision ID: 024_tender_quote_total_source
Revises: 023_agent_turns
"""

from alembic import op
import sqlalchemy as sa

revision = "024_tender_quote_total_source"
down_revision = "023_agent_turns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tender_quotes", sa.Column("stated_total_source", sa.String(16)))
    op.create_check_constraint(
        "ck_tender_quotes_stated_total_source",
        "tender_quotes",
        "stated_total_source IN ('manual', 'extracted')",
    )
    op.execute(
        "UPDATE tender_quotes SET stated_total_source = 'manual' "
        "WHERE stated_total_cents IS NOT NULL"
    )
    op.create_check_constraint(
        "ck_tender_quotes_stated_total_provenance",
        "tender_quotes",
        "(stated_total_cents IS NULL AND stated_total_source IS NULL) OR "
        "(stated_total_cents IS NOT NULL AND stated_total_source IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_tender_quotes_stated_total_provenance",
        "tender_quotes",
        type_="check",
    )
    op.drop_constraint(
        "ck_tender_quotes_stated_total_source", "tender_quotes", type_="check"
    )
    op.drop_column("tender_quotes", "stated_total_source")

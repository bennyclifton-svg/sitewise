"""Add mixed cell status and amount_breakdown for money-conserving grid (I4).

Revision ID: 034b_cell_amount_breakdown
Revises: 034_tender_ledger_completeness
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "034b_cell_amount_breakdown"
down_revision: str | None = "034_tender_ledger_completeness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_STATUSES = (
    "included",
    "excluded_explicit",
    "pc",
    "ps",
    "bundled",
    "not_required",
    "silent_ambiguous",
)
_NEW_STATUSES = _OLD_STATUSES + ("mixed",)


def upgrade() -> None:
    op.add_column(
        "tender_cell_status",
        sa.Column("amount_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.drop_constraint("ck_tender_cell_status_status", "tender_cell_status", type_="check")
    quoted = ", ".join(f"'{status}'" for status in _NEW_STATUSES)
    op.create_check_constraint(
        "ck_tender_cell_status_status",
        "tender_cell_status",
        f"status IN ({quoted})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tender_cell_status_status", "tender_cell_status", type_="check")
    quoted = ", ".join(f"'{status}'" for status in _OLD_STATUSES)
    op.create_check_constraint(
        "ck_tender_cell_status_status",
        "tender_cell_status",
        f"status IN ({quoted})",
    )
    op.drop_column("tender_cell_status", "amount_breakdown")

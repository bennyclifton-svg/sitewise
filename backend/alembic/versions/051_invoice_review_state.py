"""Add invoice review_state distinct from paid / processing_status.

Revision ID: 051_invoice_review_state
Revises: 050_invoice_machine_snapshot
"""

from alembic import op
import sqlalchemy as sa


revision = "051_invoice_review_state"
down_revision = "050_invoice_machine_snapshot"
branch_labels = None
depends_on = None

_REVIEW_STATES = (
    "received",
    "extracting",
    "ready_for_review",
    "needs_attention",
    "approved",
    "rejected",
    "posted",
    "duplicate",
    "conflict",
)


def upgrade() -> None:
    op.add_column(
        "cost_invoices",
        sa.Column(
            "review_state",
            sa.String(24),
            server_default="received",
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE cost_invoices
        SET review_state = CASE processing_status
            WHEN 'booked' THEN 'posted'
            WHEN 'needs_review' THEN 'needs_attention'
            WHEN 'void' THEN 'rejected'
            ELSE 'received'
        END
        """
    )
    op.create_check_constraint(
        "ck_cost_invoices_review_state",
        "cost_invoices",
        "review_state IN ('"
        + "','".join(_REVIEW_STATES)
        + "')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_cost_invoices_review_state", "cost_invoices", type_="check")
    op.drop_column("cost_invoices", "review_state")

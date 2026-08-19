"""Add immutable invoice machine snapshot, reviewed overlay, and issues JSONB.

Revision ID: 050_invoice_machine_snapshot
Revises: 049_canonical_document_taxonomy
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "050_invoice_machine_snapshot"
down_revision = "049_canonical_document_taxonomy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cost_invoices",
        sa.Column(
            "machine_extraction",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "cost_invoices",
        sa.Column(
            "reviewed_extraction",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "cost_invoices",
        sa.Column(
            "reviewed_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "cost_invoices",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "cost_invoices",
        sa.Column(
            "issues",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column("cost_invoices", "subtotal_ex_gst", nullable=True)
    op.alter_column("cost_invoices", "gst", nullable=True)
    op.alter_column("cost_invoices", "total_including_gst", nullable=True)
    op.drop_constraint("ck_cost_invoices_positive_amounts", "cost_invoices", type_="check")
    op.drop_constraint("ck_cost_invoices_total_reconciles", "cost_invoices", type_="check")
    op.create_check_constraint(
        "ck_cost_invoices_booked_amounts",
        "cost_invoices",
        """processing_status = 'needs_review'
        OR (
            subtotal_ex_gst IS NOT NULL
            AND gst IS NOT NULL
            AND total_including_gst IS NOT NULL
            AND subtotal_ex_gst > 0
            AND gst >= 0
            AND total_including_gst > 0
            AND subtotal_ex_gst + gst = total_including_gst
        )""",
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE cost_invoices
        SET
            subtotal_ex_gst = COALESCE(subtotal_ex_gst, 0.01),
            gst = COALESCE(gst, 0),
            total_including_gst = COALESCE(total_including_gst, 0.01)
        WHERE subtotal_ex_gst IS NULL OR gst IS NULL OR total_including_gst IS NULL
        """
    )
    op.drop_constraint("ck_cost_invoices_booked_amounts", "cost_invoices", type_="check")
    op.create_check_constraint(
        "ck_cost_invoices_positive_amounts",
        "cost_invoices",
        "subtotal_ex_gst > 0 AND gst >= 0 AND total_including_gst > 0",
    )
    op.create_check_constraint(
        "ck_cost_invoices_total_reconciles",
        "cost_invoices",
        "subtotal_ex_gst + gst = total_including_gst",
    )
    op.alter_column("cost_invoices", "subtotal_ex_gst", nullable=False)
    op.alter_column("cost_invoices", "gst", nullable=False)
    op.alter_column("cost_invoices", "total_including_gst", nullable=False)
    op.drop_column("cost_invoices", "issues")
    op.drop_column("cost_invoices", "reviewed_at")
    op.drop_column("cost_invoices", "reviewed_by_user_id")
    op.drop_column("cost_invoices", "reviewed_extraction")
    op.drop_column("cost_invoices", "machine_extraction")

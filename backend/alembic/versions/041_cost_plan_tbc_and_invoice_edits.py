"""Preserve TBC cost items and allow an operator-selected billing month.

Revision ID: 041_cost_plan_tbc_invoice_edits
Revises: 040_cost_plan_invoice_ledger
"""

from alembic import op


revision = "041_cost_plan_tbc_invoice_edits"
down_revision = "040_cost_plan_invoice_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("cost_plan_items", "budget", nullable=True)
    op.drop_constraint(
        "ck_cost_invoice_allocations_mapping_method",
        "cost_invoice_allocations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_cost_invoice_allocations_mapping_method",
        "cost_invoice_allocations",
        "mapping_method IN ('exact','related_reference','keyword','model','manual','unidentified')",
    )
    op.drop_constraint(
        "ck_cost_invoices_billing_month",
        "cost_invoices",
        type_="check",
    )
    op.create_check_constraint(
        "ck_cost_invoices_billing_month",
        "cost_invoices",
        "billing_month = date_trunc('month', billing_month)::date",
    )


def downgrade() -> None:
    op.execute(
        """UPDATE cost_plan_items
        SET budget = 0
        WHERE budget IS NULL"""
    )
    op.alter_column("cost_plan_items", "budget", nullable=False)
    op.execute(
        """UPDATE cost_invoice_allocations
        SET mapping_method = 'model'
        WHERE mapping_method = 'manual'"""
    )
    op.drop_constraint(
        "ck_cost_invoice_allocations_mapping_method",
        "cost_invoice_allocations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_cost_invoice_allocations_mapping_method",
        "cost_invoice_allocations",
        "mapping_method IN ('exact','related_reference','keyword','model','unidentified')",
    )
    op.drop_constraint(
        "ck_cost_invoices_billing_month",
        "cost_invoices",
        type_="check",
    )
    op.execute(
        """UPDATE cost_invoices
        SET billing_month = date_trunc('month', invoice_date)::date"""
    )
    op.create_check_constraint(
        "ck_cost_invoices_billing_month",
        "cost_invoices",
        "billing_month = date_trunc('month', invoice_date)::date",
    )

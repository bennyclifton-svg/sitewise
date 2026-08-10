"""Add stable display order for canonical Cost Plan items.

Revision ID: 044_cost_plan_item_order
Revises: 043_invoice_mapping_memory
"""

from alembic import op
import sqlalchemy as sa


revision = "044_cost_plan_item_order"
down_revision = "043_invoice_mapping_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cost_plan_items",
        sa.Column("display_order", sa.Integer(), nullable=True),
    )
    # Content rows are protected by cost_plan_items_immutable_content; disable it
    # only for this one-time ordering backfill.
    op.execute(
        "ALTER TABLE cost_plan_items DISABLE TRIGGER cost_plan_items_immutable_content"
    )
    try:
        op.execute(
            """
            WITH ordered AS (
              SELECT id, row_number() OVER (
                PARTITION BY cost_plan_version_id ORDER BY cost_code, item_key
              ) AS position
              FROM cost_plan_items
            )
            UPDATE cost_plan_items
            SET display_order = ordered.position
            FROM ordered
            WHERE cost_plan_items.id = ordered.id
            """
        )
    finally:
        op.execute(
            "ALTER TABLE cost_plan_items ENABLE TRIGGER cost_plan_items_immutable_content"
        )
    op.alter_column("cost_plan_items", "display_order", nullable=False)
    op.create_index(
        "ix_cost_plan_items_version_order",
        "cost_plan_items",
        ["cost_plan_version_id", "display_order"],
    )


def downgrade() -> None:
    op.drop_index("ix_cost_plan_items_version_order", table_name="cost_plan_items")
    op.drop_column("cost_plan_items", "display_order")

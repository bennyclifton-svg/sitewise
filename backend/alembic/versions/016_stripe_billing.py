"""stripe billing

Revision ID: 016_stripe_billing
Revises: 015_tender_telemetry_events
Create Date: 2026-07-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016_stripe_billing"
down_revision: Union[str, Sequence[str], None] = "015_tender_telemetry_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stripe_customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_customer_id"),
    )
    op.create_index(
        op.f("ix_stripe_customers_user_id"),
        "stripe_customers",
        ["user_id"],
        unique=True,
    )
    op.create_table(
        "stripe_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=False),
        sa.Column("price_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["stripe_customers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_subscription_id"),
    )
    op.create_index(
        op.f("ix_stripe_subscriptions_customer_id"),
        "stripe_subscriptions",
        ["customer_id"],
    )
    op.create_index(
        op.f("ix_stripe_subscriptions_status"),
        "stripe_subscriptions",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_stripe_subscriptions_status"), table_name="stripe_subscriptions")
    op.drop_index(
        op.f("ix_stripe_subscriptions_customer_id"),
        table_name="stripe_subscriptions",
    )
    op.drop_table("stripe_subscriptions")
    op.drop_index(op.f("ix_stripe_customers_user_id"), table_name="stripe_customers")
    op.drop_table("stripe_customers")

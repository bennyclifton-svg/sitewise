"""Remember manual invoice-to-cost-plan mappings.

Revision ID: 043_invoice_mapping_memory
Revises: 042_message_web_citations
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "043_invoice_mapping_memory"
down_revision = "042_message_web_citations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cost_invoice_mapping_memory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("supplier_key", sa.String(512), nullable=False),
        sa.Column("description_key", sa.String(1024), nullable=False),
        sa.Column("cost_item_key", sa.String(255), nullable=False),
        sa.Column("cost_item_label", sa.String(512), nullable=False),
        sa.Column(
            "updated_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "project_id",
            "supplier_key",
            "description_key",
            name="uq_invoice_mapping_memory_project_supplier_description",
        ),
    )
    op.create_index(
        "ix_invoice_mapping_memory_project",
        "cost_invoice_mapping_memory",
        ["project_id"],
    )
    op.drop_constraint(
        "ck_cost_invoice_allocations_mapping_method",
        "cost_invoice_allocations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_cost_invoice_allocations_mapping_method",
        "cost_invoice_allocations",
        "mapping_method IN ('exact','related_reference','keyword','model','manual','remembered','unidentified')",
    )
    op.execute("ALTER TABLE cost_invoice_mapping_memory ENABLE ROW LEVEL SECURITY")
    op.execute(
        """CREATE POLICY cost_invoice_mapping_memory_owner_policy
        ON cost_invoice_mapping_memory FOR ALL
        USING (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = cost_invoice_mapping_memory.project_id
              AND p.owner_user_id = auth.uid()
        ))
        WITH CHECK (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = cost_invoice_mapping_memory.project_id
              AND p.owner_user_id = auth.uid()
        ))"""
    )
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            GRANT SELECT, INSERT, UPDATE ON cost_invoice_mapping_memory TO authenticated;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON cost_invoice_mapping_memory TO service_role;
        END IF;
        END $$"""
    )


def downgrade() -> None:
    op.execute(
        """UPDATE cost_invoice_allocations
        SET mapping_method = 'manual'
        WHERE mapping_method = 'remembered'"""
    )
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
    op.execute(
        "DROP POLICY IF EXISTS cost_invoice_mapping_memory_owner_policy "
        "ON cost_invoice_mapping_memory"
    )
    op.drop_index(
        "ix_invoice_mapping_memory_project",
        table_name="cost_invoice_mapping_memory",
    )
    op.drop_table("cost_invoice_mapping_memory")

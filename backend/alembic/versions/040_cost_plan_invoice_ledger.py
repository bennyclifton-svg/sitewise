"""Add the canonical Cost Plan invoice ledger.

Revision ID: 040_cost_plan_invoice_ledger
Revises: 039_agent_turn_input_context
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "040_cost_plan_invoice_ledger"
down_revision = "039_agent_turn_input_context"
branch_labels = None
depends_on = None


def _owner_policy(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""CREATE POLICY {table}_owner_policy ON {table}
        USING (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = {table}.project_id AND p.owner_user_id = auth.uid()
        ))
        WITH CHECK (EXISTS (
            SELECT 1 FROM projects p
            WHERE p.id = {table}.project_id AND p.owner_user_id = auth.uid()
        ))"""
    )


def upgrade() -> None:
    op.create_table(
        "cost_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspace_files.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "source_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_documents.id", ondelete="SET NULL"),
        ),
        sa.Column("source_content_hash", sa.String(64), nullable=False),
        sa.Column("source_locator", sa.String(1024), nullable=False),
        sa.Column("supplier_name", sa.String(512), nullable=False),
        sa.Column("supplier_key", sa.String(512), nullable=False),
        sa.Column("supplier_abn", sa.String(32)),
        sa.Column("invoice_number", sa.String(128), nullable=False),
        sa.Column("invoice_key", sa.String(128), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("billing_month", sa.Date(), nullable=False),
        sa.Column("po_number", sa.String(128)),
        sa.Column("related_reference", sa.String(255)),
        sa.Column("subtotal_ex_gst", sa.Numeric(18, 2), nullable=False),
        sa.Column("gst", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_including_gst", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="AUD", nullable=False),
        sa.Column("paid", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "processing_status", sa.String(24), server_default="booked", nullable=False
        ),
        sa.Column(
            "extraction_provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "processed_by_workflow_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("first_published_cost_plan_version", sa.Integer()),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
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
        sa.CheckConstraint(
            "processing_status IN ('booked','needs_review','void')",
            name="ck_cost_invoices_processing_status",
        ),
        sa.CheckConstraint(
            "subtotal_ex_gst > 0 AND gst >= 0 AND total_including_gst > 0",
            name="ck_cost_invoices_positive_amounts",
        ),
        sa.CheckConstraint(
            "subtotal_ex_gst + gst = total_including_gst",
            name="ck_cost_invoices_total_reconciles",
        ),
        sa.CheckConstraint(
            "billing_month = date_trunc('month', invoice_date)::date",
            name="ck_cost_invoices_billing_month",
        ),
        sa.CheckConstraint("revision > 0", name="ck_cost_invoices_revision"),
        sa.UniqueConstraint(
            "id", "project_id", name="uq_cost_invoices_id_project"
        ),
        sa.UniqueConstraint(
            "project_id",
            "source_content_hash",
            name="uq_cost_invoices_project_content_hash",
        ),
        sa.UniqueConstraint(
            "project_id",
            "supplier_key",
            "invoice_key",
            name="uq_cost_invoices_project_supplier_number",
        ),
    )
    op.create_index(
        "ix_cost_invoices_project_date", "cost_invoices", ["project_id", "invoice_date"]
    )
    op.create_index(
        "ix_cost_invoices_workspace_file", "cost_invoices", ["workspace_file_id"]
    )
    op.create_index(
        "ix_cost_invoices_source_document", "cost_invoices", ["source_document_id"]
    )
    op.create_index(
        "ix_cost_invoices_project_published_version",
        "cost_invoices",
        ["project_id", "first_published_cost_plan_version"],
    )

    op.create_table(
        "cost_invoice_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount_ex_gst", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "gst_treatment", sa.String(24), server_default="taxable", nullable=False
        ),
        sa.Column("cost_item_key", sa.String(255)),
        sa.Column(
            "cost_item_label",
            sa.String(512),
            server_default="Unidentified",
            nullable=False,
        ),
        sa.Column(
            "mapping_method",
            sa.String(32),
            server_default="unidentified",
            nullable=False,
        ),
        sa.Column("mapping_confidence", sa.Numeric(5, 4)),
        sa.Column(
            "review_status",
            sa.String(24),
            server_default="needs_review",
            nullable=False,
        ),
        sa.Column(
            "source_locators",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id", "project_id"],
            ["cost_invoices.id", "cost_invoices.project_id"],
            ondelete="CASCADE",
            name="fk_cost_invoice_allocations_invoice_project",
        ),
        sa.CheckConstraint(
            "line_number > 0", name="ck_cost_invoice_allocations_line"
        ),
        sa.CheckConstraint(
            "amount_ex_gst > 0", name="ck_cost_invoice_allocations_positive_amount"
        ),
        sa.CheckConstraint(
            "gst_treatment IN ('taxable','gst_free','derived')",
            name="ck_cost_invoice_allocations_gst_treatment",
        ),
        sa.CheckConstraint(
            "mapping_method IN ('exact','related_reference','keyword','model','unidentified')",
            name="ck_cost_invoice_allocations_mapping_method",
        ),
        sa.CheckConstraint(
            "review_status IN ('mapped','needs_review')",
            name="ck_cost_invoice_allocations_review_status",
        ),
        sa.CheckConstraint(
            "mapping_confidence IS NULL OR (mapping_confidence >= 0 AND mapping_confidence <= 1)",
            name="ck_cost_invoice_allocations_confidence",
        ),
        sa.CheckConstraint(
            "(review_status = 'mapped' AND cost_item_key IS NOT NULL) OR "
            "(review_status = 'needs_review' AND cost_item_key IS NULL)",
            name="ck_cost_invoice_allocations_mapping_state",
        ),
        sa.UniqueConstraint(
            "invoice_id", "line_number", name="uq_cost_invoice_allocations_invoice_line"
        ),
    )
    op.create_index(
        "ix_cost_invoice_allocations_project", "cost_invoice_allocations", ["project_id"]
    )
    op.create_index(
        "ix_cost_invoice_allocations_cost_item",
        "cost_invoice_allocations",
        ["project_id", "cost_item_key"],
    )

    _owner_policy("cost_invoices")
    _owner_policy("cost_invoice_allocations")
    op.execute(
        """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            GRANT SELECT, INSERT, UPDATE ON cost_invoices, cost_invoice_allocations TO authenticated;
        END IF;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON cost_invoices, cost_invoice_allocations TO service_role;
        END IF;
        END $$"""
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS cost_invoice_allocations_owner_policy ON cost_invoice_allocations"
    )
    op.execute("DROP POLICY IF EXISTS cost_invoices_owner_policy ON cost_invoices")
    op.drop_index(
        "ix_cost_invoice_allocations_cost_item",
        table_name="cost_invoice_allocations",
    )
    op.drop_index(
        "ix_cost_invoice_allocations_project",
        table_name="cost_invoice_allocations",
    )
    op.drop_table("cost_invoice_allocations")
    op.drop_index(
        "ix_cost_invoices_project_published_version", table_name="cost_invoices"
    )
    op.drop_index("ix_cost_invoices_source_document", table_name="cost_invoices")
    op.drop_index("ix_cost_invoices_workspace_file", table_name="cost_invoices")
    op.drop_index("ix_cost_invoices_project_date", table_name="cost_invoices")
    op.drop_table("cost_invoices")

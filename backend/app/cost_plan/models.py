from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class CostPlanVersion(Base):
    __tablename__ = "cost_plan_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    artefact_revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_artifacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="proposed")
    contingency_percent: Mapped[Decimal] = mapped_column(
        Numeric(9, 4), nullable=False, default=0
    )
    escalation_percent: Mapped[Decimal] = mapped_column(
        Numeric(9, 4), nullable=False, default=0
    )
    gst_treatment: Mapped[str] = mapped_column(
        String(24), nullable=False, default="exclusive"
    )
    assumptions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    narrative: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    dependency_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    deterministic_totals: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("draft_artifacts.id", ondelete="RESTRICT")
    )
    external_idempotency_key: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    items: Mapped[list["CostPlanItem"]] = relationship(
        back_populates="cost_plan_version",
        cascade="all, delete-orphan",
        order_by="CostPlanItem.cost_code, CostPlanItem.item_key",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed','accepted','superseded')",
            name="ck_cost_plan_versions_status",
        ),
        CheckConstraint(
            "gst_treatment IN ('exclusive','inclusive','not_applicable')",
            name="ck_cost_plan_versions_gst_treatment",
        ),
        CheckConstraint(
            "contingency_percent >= 0 AND escalation_percent >= 0",
            name="ck_cost_plan_versions_nonnegative_percentages",
        ),
        UniqueConstraint(
            "project_id", "version", name="uq_cost_plan_versions_project_version"
        ),
        UniqueConstraint(
            "project_id",
            "artefact_revision_id",
            name="uq_cost_plan_versions_project_artefact",
        ),
        UniqueConstraint(
            "project_id",
            "source_draft_id",
            name="uq_cost_plan_versions_project_source_draft",
        ),
        UniqueConstraint(
            "project_id",
            "external_idempotency_key",
            name="uq_cost_plan_versions_project_external_key",
        ),
        Index("ix_cost_plan_versions_project_status", "project_id", "status"),
        Index("ix_cost_plan_versions_created_by", "created_by_user_id"),
    )


class CostPlanItem(Base):
    __tablename__ = "cost_plan_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cost_plan_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cost_plan_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_key: Mapped[str] = mapped_column(String(255), nullable=False)
    cost_code: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    item: Mapped[str] = mapped_column(String(512), nullable=False)
    budget: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    committed: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=0
    )
    forecast: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    paid: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    allowance_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="none"
    )
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    unit: Mapped[str | None] = mapped_column(String(64))
    rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    basis: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="proposed")
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    cost_plan_version: Mapped[CostPlanVersion] = relationship(back_populates="items")

    __table_args__ = (
        CheckConstraint(
            "allowance_type IN ('none','pc','ps','contingency')",
            name="ck_cost_plan_items_allowance_type",
        ),
        CheckConstraint(
            "status IN ('proposed','confirmed','manual')",
            name="ck_cost_plan_items_status",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_cost_plan_items_confidence",
        ),
        CheckConstraint(
            "(quantity IS NULL AND rate IS NULL AND unit IS NULL) OR "
            "(quantity IS NOT NULL AND rate IS NOT NULL AND unit IS NOT NULL)",
            name="ck_cost_plan_items_complete_unit_rate",
        ),
        UniqueConstraint(
            "cost_plan_version_id", "item_key", name="uq_cost_plan_items_version_key"
        ),
        UniqueConstraint(
            "cost_plan_version_id", "cost_code", name="uq_cost_plan_items_version_code"
        ),
        Index("ix_cost_plan_items_version", "cost_plan_version_id"),
    )


class CostInvoice(Base):
    __tablename__ = "cost_invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspace_files.id", ondelete="SET NULL"),
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="SET NULL"),
    )
    source_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_locator: Mapped[str] = mapped_column(String(1024), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(512), nullable=False)
    supplier_key: Mapped[str] = mapped_column(String(512), nullable=False)
    supplier_abn: Mapped[str | None] = mapped_column(String(32))
    invoice_number: Mapped[str] = mapped_column(String(128), nullable=False)
    invoice_key: Mapped[str] = mapped_column(String(128), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    billing_month: Mapped[date] = mapped_column(Date, nullable=False)
    po_number: Mapped[str | None] = mapped_column(String(128))
    related_reference: Mapped[str | None] = mapped_column(String(255))
    subtotal_ex_gst: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    gst: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_including_gst: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AUD")
    paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    processing_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="booked"
    )
    extraction_provenance: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    processed_by_workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="SET NULL")
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    first_published_cost_plan_version: Mapped[int | None] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    allocations: Mapped[list["CostInvoiceAllocation"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="CostInvoiceAllocation.line_number",
    )

    __table_args__ = (
        CheckConstraint(
            "processing_status IN ('booked','needs_review','void')",
            name="ck_cost_invoices_processing_status",
        ),
        CheckConstraint(
            "subtotal_ex_gst > 0 AND gst >= 0 AND total_including_gst > 0",
            name="ck_cost_invoices_positive_amounts",
        ),
        CheckConstraint(
            "subtotal_ex_gst + gst = total_including_gst",
            name="ck_cost_invoices_total_reconciles",
        ),
        CheckConstraint(
            "billing_month = date_trunc('month', invoice_date)::date",
            name="ck_cost_invoices_billing_month",
        ),
        CheckConstraint("revision > 0", name="ck_cost_invoices_revision"),
        UniqueConstraint(
            "id", "project_id", name="uq_cost_invoices_id_project"
        ),
        UniqueConstraint(
            "project_id",
            "source_content_hash",
            name="uq_cost_invoices_project_content_hash",
        ),
        UniqueConstraint(
            "project_id",
            "supplier_key",
            "invoice_key",
            name="uq_cost_invoices_project_supplier_number",
        ),
        Index("ix_cost_invoices_project_date", "project_id", "invoice_date"),
        Index("ix_cost_invoices_workspace_file", "workspace_file_id"),
        Index("ix_cost_invoices_source_document", "source_document_id"),
        Index(
            "ix_cost_invoices_project_published_version",
            "project_id",
            "first_published_cost_plan_version",
        ),
    )


class CostInvoiceAllocation(Base):
    __tablename__ = "cost_invoice_allocations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount_ex_gst: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    gst_treatment: Mapped[str] = mapped_column(
        String(24), nullable=False, default="taxable"
    )
    cost_item_key: Mapped[str | None] = mapped_column(String(255))
    cost_item_label: Mapped[str] = mapped_column(
        String(512), nullable=False, default="Unidentified"
    )
    mapping_method: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unidentified"
    )
    mapping_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    review_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="needs_review"
    )
    source_locators: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    invoice: Mapped[CostInvoice] = relationship(back_populates="allocations")

    __table_args__ = (
        ForeignKeyConstraint(
            ["invoice_id", "project_id"],
            ["cost_invoices.id", "cost_invoices.project_id"],
            ondelete="CASCADE",
            name="fk_cost_invoice_allocations_invoice_project",
        ),
        CheckConstraint("line_number > 0", name="ck_cost_invoice_allocations_line"),
        CheckConstraint(
            "amount_ex_gst > 0", name="ck_cost_invoice_allocations_positive_amount"
        ),
        CheckConstraint(
            "gst_treatment IN ('taxable','gst_free','derived')",
            name="ck_cost_invoice_allocations_gst_treatment",
        ),
        CheckConstraint(
            "mapping_method IN ('exact','related_reference','keyword','model','unidentified')",
            name="ck_cost_invoice_allocations_mapping_method",
        ),
        CheckConstraint(
            "review_status IN ('mapped','needs_review')",
            name="ck_cost_invoice_allocations_review_status",
        ),
        CheckConstraint(
            "mapping_confidence IS NULL OR (mapping_confidence >= 0 AND mapping_confidence <= 1)",
            name="ck_cost_invoice_allocations_confidence",
        ),
        CheckConstraint(
            "(review_status = 'mapped' AND cost_item_key IS NOT NULL) OR "
            "(review_status = 'needs_review' AND cost_item_key IS NULL)",
            name="ck_cost_invoice_allocations_mapping_state",
        ),
        UniqueConstraint(
            "invoice_id", "line_number", name="uq_cost_invoice_allocations_invoice_line"
        ),
        Index("ix_cost_invoice_allocations_project", "project_id"),
        Index("ix_cost_invoice_allocations_cost_item", "project_id", "cost_item_key"),
    )

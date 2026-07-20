from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
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

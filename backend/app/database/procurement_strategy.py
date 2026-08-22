from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ProcurementStrategy(Base):
    __tablename__ = "procurement_strategies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    tenderer_column_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default="3"
    )
    source_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", server_default=""
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    rows: Mapped[list["ProcurementStrategyRow"]] = relationship(
        back_populates="strategy",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProcurementStrategyRow.display_order",
    )

    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_procurement_strategies_revision"),
        CheckConstraint(
            "tenderer_column_count IN (3, 4)",
            name="ck_procurement_strategies_column_count",
        ),
        Index("ix_procurement_strategies_project", "project_id"),
    )


class ProcurementStrategyRow(Base):
    __tablename__ = "procurement_strategy_rows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("procurement_strategies.id", ondelete="CASCADE"),
        nullable=False,
    )
    discipline_code: Mapped[str | None] = mapped_column(String(128))
    discipline_label: Mapped[str] = mapped_column(String(512), nullable=False)
    participant_type: Mapped[str] = mapped_column(String(24), nullable=False)
    request_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_started", server_default="not_started"
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    origin: Mapped[str] = mapped_column(String(24), nullable=False)
    locked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    strategy: Mapped[ProcurementStrategy] = relationship(back_populates="rows")
    candidates: Mapped[list["ProcurementStrategyCandidate"]] = relationship(
        back_populates="row",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProcurementStrategyCandidate.slot",
    )

    __table_args__ = (
        CheckConstraint(
            "participant_type IN ('consultant','trade','supplier')",
            name="ck_procurement_strategy_rows_participant_type",
        ),
        CheckConstraint(
            "request_kind IN ('consultant_rfp','contractor_eoi','trade_rft','trade_rfq')",
            name="ck_procurement_strategy_rows_request_kind",
        ),
        CheckConstraint(
            "status IN ('not_started','researching','shortlisting','request_drafted',"
            "'issued','responses_received','evaluating','awarded','cancelled')",
            name="ck_procurement_strategy_rows_status",
        ),
        CheckConstraint(
            "origin IN ('derived','existing_request','manual')",
            name="ck_procurement_strategy_rows_origin",
        ),
        Index(
            "uq_procurement_strategy_rows_discipline",
            "strategy_id",
            "discipline_code",
            unique=True,
            postgresql_where=text("discipline_code IS NOT NULL"),
        ),
        Index(
            "ix_procurement_strategy_rows_order", "strategy_id", "display_order"
        ),
        Index("ix_procurement_strategy_rows_code", "discipline_code"),
    )


class ProcurementStrategyCandidate(Base):
    __tablename__ = "procurement_strategy_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    strategy_row_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("procurement_strategy_rows.id", ondelete="CASCADE"),
        nullable=False,
    )
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    company_name: Mapped[str] = mapped_column(String(512), nullable=False)
    website_url: Mapped[str | None] = mapped_column(String(2048))
    location_text: Mapped[str | None] = mapped_column(String(512))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    source_title: Mapped[str | None] = mapped_column(String(512))
    researched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    row: Mapped[ProcurementStrategyRow] = relationship(back_populates="candidates")

    __table_args__ = (
        CheckConstraint("slot BETWEEN 1 AND 4", name="ck_strategy_candidates_slot"),
        UniqueConstraint(
            "strategy_row_id", "slot", name="uq_strategy_candidates_row_slot"
        ),
        Index("ix_strategy_candidates_row", "strategy_row_id"),
    )

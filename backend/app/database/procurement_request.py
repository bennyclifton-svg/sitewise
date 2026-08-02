from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ProcurementRequest(Base):
    """A project-owned request register entry for a generated procurement draft."""

    __tablename__ = "procurement_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_name: Mapped[str] = mapped_column(String(512), nullable=False)
    target_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="draft", server_default="draft"
    )
    current_draft_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_artifacts.id", ondelete="RESTRICT"),
    )
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "kind IN ('consultant_rfp','contractor_eoi','trade_rft','trade_rfq')",
            name="ck_procurement_requests_kind",
        ),
        CheckConstraint(
            "status IN ('draft','issued','closed','cancelled')",
            name="ck_procurement_requests_status",
        ),
        CheckConstraint("revision >= 1", name="ck_procurement_requests_revision"),
        Index(
            "ix_procurement_requests_project_updated",
            "project_id",
            "updated_at",
        ),
        Index(
            "ix_procurement_requests_project_status",
            "project_id",
            "status",
        ),
        Index(
            "ix_procurement_requests_current_draft",
            "current_draft_artifact_id",
        ),
    )

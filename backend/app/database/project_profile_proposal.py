from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ProjectProfileProposal(Base):
    __tablename__ = "project_profile_proposals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    profile_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    current_values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    proposed_values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    evidence_references: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    confidence: Mapped[float | None] = mapped_column(Float)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    proposer: Mapped[str] = mapped_column(String(128), nullable=False)
    resolver_source: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "state IN ('pending', 'accepted', 'rejected')",
            name="ck_project_profile_proposals_state",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_project_profile_proposals_confidence",
        ),
        Index(
            "ix_project_profile_proposals_project_state_created",
            "project_id",
            "state",
            "created_at",
        ),
    )

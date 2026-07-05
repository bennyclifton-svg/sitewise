from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(64))
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    step: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_activity_events_project_created_at", "project_id", "created_at"),
        Index("ix_activity_events_project_run", "project_id", "run_id"),
    )

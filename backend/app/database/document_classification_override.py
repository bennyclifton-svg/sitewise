from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class DocumentClassificationOverride(Base):
    """A human correction of document_class. Keyed by hash, or path if hash is null (OD-3)."""

    __tablename__ = "document_classification_overrides"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_hash: Mapped[str | None] = mapped_column(String(64))
    relative_path: Mapped[str | None] = mapped_column(String(1024))
    key_basis: Mapped[str] = mapped_column(String(16), nullable=False)
    document_class: Mapped[str] = mapped_column(String(64), nullable=False)
    document_subject: Mapped[str | None] = mapped_column(String(64))
    previous_class: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(Text())
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
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
            "key_basis IN ('content_hash', 'relative_path')",
            name="ck_override_key_basis",
        ),
        CheckConstraint(
            "(key_basis = 'content_hash' AND content_hash IS NOT NULL) OR "
            "(key_basis = 'relative_path' AND relative_path IS NOT NULL)",
            name="ck_override_key_present",
        ),
        Index(
            "uq_override_project_hash",
            "project_id",
            "content_hash",
            unique=True,
            postgresql_where=text("content_hash IS NOT NULL"),
        ),
        Index(
            "uq_override_project_path",
            "project_id",
            "relative_path",
            unique=True,
            postgresql_where=text("content_hash IS NULL"),
        ),
    )

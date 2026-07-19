from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.document_chunk import DocumentChunk


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    project: Mapped[str] = mapped_column(String(255), nullable=False)
    phase: Mapped[str] = mapped_column(String(64), nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(128))
    document_class: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    ingest_mode: Mapped[str | None] = mapped_column(String(32))
    document_metadata: Mapped[dict | None] = mapped_column(JSONB)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    source_type: Mapped[str | None] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    normalized_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document")

    __table_args__ = (
        Index(
            "ix_source_documents_project_source_type_relative_path",
            "project_id",
            "source_type",
            "relative_path",
        ),
        Index(
            "uq_source_documents_project_path",
            "project_id",
            "relative_path",
            unique=True,
            postgresql_where=text("project_id IS NOT NULL"),
        ),
        Index(
            "uq_source_documents_platform_path",
            "relative_path",
            unique=True,
            postgresql_where=text(
                "project_id IS NULL AND document_metadata->>'knowledge_scope' = 'platform'"
            ),
        ),
        CheckConstraint(
            "source_type <> 'project_evidence' OR project_id IS NOT NULL",
            name="ck_source_documents_project_evidence_owner",
        ),
        CheckConstraint(
            "document_metadata->>'knowledge_scope' <> 'platform' OR project_id IS NULL",
            name="ck_source_documents_platform_projectless",
        ),
    )

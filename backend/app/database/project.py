from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.chat_thread import ChatThread
    from app.database.draft_artifact import DraftArtifact
    from app.database.user import User
    from app.database.workspace_file import WorkspaceFile


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    workspace_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    phase: Mapped[str] = mapped_column(String(64), nullable=False, default="procurement")
    archetype: Mapped[str | None] = mapped_column(String(64))
    user_role: Mapped[str | None] = mapped_column(String(64))
    state: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active")
    project_metadata: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner: Mapped["User"] = relationship(back_populates="projects")
    chat_threads: Mapped[list["ChatThread"]] = relationship(back_populates="project")
    draft_artifacts: Mapped[list["DraftArtifact"]] = relationship(back_populates="project")
    workspace_files: Mapped[list["WorkspaceFile"]] = relationship(back_populates="project")

    __table_args__ = (
        UniqueConstraint("owner_user_id", "slug", name="uq_projects_owner_user_id_slug"),
        Index("ix_projects_owner_user_id", "owner_user_id"),
    )

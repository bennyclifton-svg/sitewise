from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.chat_message import ChatMessage
    from app.database.project import Project
    from app.database.user import User


class ChatThread(Base):
    __tablename__ = "chat_threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL")
    )
    title: Mapped[str | None] = mapped_column(String(512))
    hermes_session_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="chat_threads")
    project: Mapped[Project | None] = relationship(back_populates="chat_threads")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="thread")

    __table_args__ = (
        Index("ix_chat_threads_user_id", "user_id"),
        Index("ix_chat_threads_project_id", "project_id"),
    )

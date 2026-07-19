from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ProjectDocumentSelection(Base):
    __tablename__ = "project_document_selections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    selected_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    revisions: Mapped[list["ProjectDocumentSelectionRevision"]] = relationship(
        back_populates="selection", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("project_id", "purpose", name="uq_project_document_selections_project_purpose"),
        Index("ix_project_document_selections_project_id", "project_id"),
    )


class ProjectDocumentSelectionRevision(Base):
    __tablename__ = "project_document_selection_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    selection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_document_selections.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    selection: Mapped[ProjectDocumentSelection] = relationship(back_populates="revisions")
    groups: Mapped[list["ProjectDocumentSelectionGroup"]] = relationship(
        back_populates="selection_revision", cascade="all, delete-orphan", order_by="ProjectDocumentSelectionGroup.position"
    )

    __table_args__ = (
        UniqueConstraint("selection_id", "revision", name="uq_project_document_selection_revisions_selection_revision"),
        Index("ix_project_document_selection_revisions_project_purpose", "project_id", "purpose"),
    )


class ProjectDocumentSelectionGroup(Base):
    __tablename__ = "project_document_selection_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    selection_revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_document_selection_revisions.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(512), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    selection_revision: Mapped[ProjectDocumentSelectionRevision] = relationship(back_populates="groups")
    items: Mapped[list["ProjectDocumentSelectionItem"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", order_by="ProjectDocumentSelectionItem.position"
    )

    __table_args__ = (
        UniqueConstraint("selection_revision_id", "position", name="uq_project_document_selection_groups_revision_position"),
        Index("ix_project_document_selection_groups_project_id", "project_id"),
    )


class ProjectDocumentSelectionItem(Base):
    __tablename__ = "project_document_selection_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_document_selection_groups.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    workspace_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace_files.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    group: Mapped[ProjectDocumentSelectionGroup] = relationship(back_populates="items")

    __table_args__ = (
        UniqueConstraint("group_id", "position", name="uq_project_document_selection_items_group_position"),
        UniqueConstraint("group_id", "workspace_file_id", name="uq_project_document_selection_items_group_file"),
        Index("ix_project_document_selection_items_project_file", "project_id", "workspace_file_id"),
    )


class WorkflowInputRetentionLock(Base):
    __tablename__ = "workflow_input_retention_locks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    workspace_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace_files.id", ondelete="RESTRICT"), nullable=False
    )
    workflow_type: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("workflow_type", "workflow_id", "workspace_file_id", name="uq_workflow_input_retention_lock"),
        Index("ix_workflow_input_retention_locks_project_file", "project_id", "workspace_file_id"),
    )

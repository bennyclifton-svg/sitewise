from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ProgrammeVersion(Base):
    __tablename__ = "programme_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="proposed")
    view_scale: Mapped[str] = mapped_column(String(16), nullable=False, default="month")
    pmp_embed_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    activities: Mapped[list["ProgrammeActivity"]] = relationship(
        back_populates="programme_version",
        cascade="all, delete-orphan",
        order_by="ProgrammeActivity.display_order, ProgrammeActivity.activity_key",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed','accepted','superseded')",
            name="ck_programme_versions_status",
        ),
        CheckConstraint(
            "view_scale IN ('week','month','quarter')",
            name="ck_programme_versions_view_scale",
        ),
        UniqueConstraint(
            "project_id", "version", name="uq_programme_versions_project_version"
        ),
        Index("ix_programme_versions_project_status", "project_id", "status"),
        Index("ix_programme_versions_created_by", "created_by_user_id"),
    )


class ProgrammeActivity(Base):
    __tablename__ = "programme_activities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    programme_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programme_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    activity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    parent_key: Mapped[str | None] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    finish_date: Mapped[date] = mapped_column(Date, nullable=False)
    predecessor_key: Mapped[str | None] = mapped_column(String(255))
    lag_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assumption: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    programme_version: Mapped[ProgrammeVersion] = relationship(
        back_populates="activities"
    )

    __table_args__ = (
        CheckConstraint(
            "kind IN ('stage','activity','milestone')",
            name="ck_programme_activities_kind",
        ),
        CheckConstraint(
            "duration_days >= 0",
            name="ck_programme_activities_duration",
        ),
        CheckConstraint(
            "(kind <> 'milestone') OR duration_days = 0",
            name="ck_programme_activities_milestone_duration",
        ),
        CheckConstraint(
            "(kind <> 'stage') OR parent_key IS NULL",
            name="ck_programme_activities_stage_parent",
        ),
        CheckConstraint(
            "(kind = 'stage') OR parent_key IS NOT NULL",
            name="ck_programme_activities_child_parent",
        ),
        UniqueConstraint(
            "programme_version_id",
            "activity_key",
            name="uq_programme_activities_version_key",
        ),
        Index("ix_programme_activities_version", "programme_version_id"),
    )

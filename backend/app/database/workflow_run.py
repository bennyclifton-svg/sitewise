from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    requested_by_thread_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_threads.id", ondelete="SET NULL")
    )
    requested_by_turn_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_turns.id", ondelete="SET NULL")
    )
    workflow_type: Mapped[str] = mapped_column(String(64), nullable=False)
    run_brief: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    schema_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    canonical_request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    frozen_profile_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    frozen_snapshot_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    frozen_evidence_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    frozen_decision_set_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    frozen_selection_revision: Mapped[int | None] = mapped_column(Integer)
    frozen_artefact_version: Mapped[int | None] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(24), nullable=False, server_default="queued")
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    lock_owner: Mapped[str | None] = mapped_column(String(255))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    cancel_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    progress: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    stage_durations_ms: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result_artefact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("draft_artifacts.id", ondelete="SET NULL")
    )
    result_reference: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_class: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "workflow_type",
            "idempotency_key",
            name="uq_workflow_runs_project_type_idempotency",
        ),
        CheckConstraint(
            "state IN ('queued','running','needs_input','complete','failed','cancelled')",
            name="ck_workflow_runs_state",
        ),
        CheckConstraint("attempt >= 0 AND max_attempts > 0", name="ck_workflow_runs_attempts"),
        Index("ix_workflow_runs_claim", "state", "run_after", "lease_expires_at"),
        Index("ix_workflow_runs_project_created", "project_id", "created_at"),
        Index("ix_workflow_runs_requested_by_user", "requested_by_user_id"),
    )

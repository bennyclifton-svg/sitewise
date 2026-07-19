from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


WorkflowRunState = Literal[
    "queued", "running", "needs_input", "complete", "failed", "cancelled"
]


class WorkflowRunStartRequest(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=255)
    expected_snapshot_fingerprint: str = Field(min_length=64, max_length=64)
    expected_profile_revision: int = Field(ge=1)
    expected_decision_set_revision: int = Field(ge=1)
    expected_artefact_version: int | None = Field(default=None, ge=1)
    thread_id: uuid.UUID | None = None
    turn_id: uuid.UUID | None = None
    chat_model: str | None = Field(default=None, max_length=128)
    parameters: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    requested_by_user_id: uuid.UUID
    requested_by_thread_id: uuid.UUID | None
    requested_by_turn_id: uuid.UUID | None
    workflow_type: str
    idempotency_key: str
    schema_version: int
    frozen_profile_revision: int
    frozen_snapshot_fingerprint: str
    frozen_evidence_fingerprint: str
    frozen_decision_set_revision: int
    frozen_selection_revision: int | None
    frozen_artefact_version: int | None
    state: WorkflowRunState
    attempt: int
    max_attempts: int
    cancel_requested: bool
    progress: dict[str, Any]
    stage_durations_ms: dict[str, Any]
    result_artefact_id: uuid.UUID | None
    result_reference: dict[str, Any] | None
    error_class: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime


class WorkflowRunResult(BaseModel):
    run: WorkflowRunView
    result: dict[str, Any] | None

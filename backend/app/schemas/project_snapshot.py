from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.profile_proposals import ProjectProfileProposalView
from app.schemas.projects import ProjectProfileView


class SnapshotValue(BaseModel):
    status: Literal["confirmed", "needs_input"]
    value: Any | None = None
    source: str | None = None


class ProjectSnapshotIdentity(BaseModel):
    project_id: uuid.UUID
    title: str
    slug: str
    workspace_path: str
    phase: str
    status: str
    site_address: SnapshotValue
    client: SnapshotValue


class ProjectSnapshotDecision(BaseModel):
    decision_id: str
    label: str
    selected: str
    source: str
    revision: int = Field(ge=1)
    locked: bool
    evidence_conflict: bool
    agent_suggestion: str | None = None


class ProjectSnapshotDecisions(BaseModel):
    set_revision: int = Field(ge=1)
    items: list[ProjectSnapshotDecision]
    complete: bool = True


class EvidenceIngestFailure(BaseModel):
    workspace_path: str
    error: str | None = None


class ProjectSnapshotEvidence(BaseModel):
    fingerprint: str
    active_count: int = Field(ge=0)
    fingerprint_complete: bool
    ingest_failure_count: int = Field(ge=0)
    ingest_failures: list[EvidenceIngestFailure]
    selection_status: Literal["not_persisted"] = "not_persisted"
    selection_metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectSnapshot(BaseModel):
    schema_version: Literal[1] = 1
    generated_at: datetime
    content_fingerprint: str
    identity: ProjectSnapshotIdentity
    profile: ProjectProfileView
    decisions: ProjectSnapshotDecisions
    evidence: ProjectSnapshotEvidence
    confirmed_inputs: dict[str, SnapshotValue]
    open_profile_proposals: list[ProjectProfileProposalView]
    open_profile_proposals_complete: bool = True

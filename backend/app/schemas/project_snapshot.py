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
    open_count: int = Field(default=0, ge=0)
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


class ProjectSnapshotSelection(BaseModel):
    purpose: str
    revision: int = Field(ge=0)


class ProjectSnapshotArtefact(BaseModel):
    artefact_id: uuid.UUID
    workflow_type: str
    title: str
    version: int = Field(ge=1)
    status: str
    is_stale: bool = False
    stale_reason: str | None = None


class ProjectSnapshotWorkflowRun(BaseModel):
    run_id: uuid.UUID
    workflow_type: str
    state: str
    error_class: str | None = None


class ProjectSnapshotTender(BaseModel):
    status: Literal["not_started", "draft", "qa_required", "approved"] = "not_started"
    report_id: uuid.UUID | None = None
    report_version: int | None = Field(default=None, ge=1)
    open_qa_count: int = Field(default=0, ge=0)
    qs_gate_passed: bool = False


class ProjectSnapshotBudget(BaseModel):
    status: Literal["not_available", "proposed", "accepted"] = "not_available"
    version: int | None = Field(default=None, ge=1)
    total: str | None = None
    gst_treatment: str | None = None


class ProjectNextAction(BaseModel):
    code: str
    label: str
    reason: str
    blocking_fact: str
    route: str
    tool: str


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
    purpose_selections: list[ProjectSnapshotSelection] = Field(default_factory=list)
    latest_artefacts: list[ProjectSnapshotArtefact] = Field(default_factory=list)
    active_workflow_runs: list[ProjectSnapshotWorkflowRun] = Field(default_factory=list)
    failed_workflow_runs: list[ProjectSnapshotWorkflowRun] = Field(default_factory=list)
    tender: ProjectSnapshotTender = Field(default_factory=ProjectSnapshotTender)
    budget: ProjectSnapshotBudget = Field(default_factory=ProjectSnapshotBudget)
    next_actions: list[ProjectNextAction] = Field(default_factory=list)

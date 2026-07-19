from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.projects import ProjectProfileChange


class ProfileEvidenceReference(BaseModel):
    source_document_id: uuid.UUID
    locator: str | None = Field(default=None, max_length=1024)
    claim: str | None = Field(default=None, max_length=2048)


class ProjectProfileProposalView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    profile_revision: int = Field(ge=1)
    current_values: dict[str, Any]
    proposed_values: dict[str, Any]
    evidence_references: list[ProfileEvidenceReference]
    confidence: float | None = Field(default=None, ge=0, le=1)
    state: Literal["pending", "accepted", "rejected"]
    proposer: str
    resolver_source: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class ProfileProposalResolution(BaseModel):
    proposal: ProjectProfileProposalView
    profile_change: ProjectProfileChange | None = None

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


WorkflowCapabilityStatus = Literal["supported", "needs_input", "unsupported"]


class WorkflowCapability(BaseModel):
    status: WorkflowCapabilityStatus
    reasons: list[str] = Field(default_factory=list)
    required_fields: list[str] = Field(default_factory=list)


class WorkflowCapabilityMatrix(BaseModel):
    schema_version: Literal[1] = 1
    snapshot_schema_version: Literal[1] = 1
    snapshot_content_fingerprint: str
    capabilities: dict[str, WorkflowCapability]

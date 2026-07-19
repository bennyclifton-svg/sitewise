from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence: int = Field(ge=1)
    schema_version: int = Field(ge=1)
    project_id: uuid.UUID
    actor_source: str
    resource_type: str
    resource_id: str
    resource_revision: int | None
    action: str
    payload: dict[str, Any]
    deduplication_key: str | None
    created_at: datetime


class ProjectEventListResponse(BaseModel):
    events: list[ProjectEventView]
    next_after: int = Field(ge=0)

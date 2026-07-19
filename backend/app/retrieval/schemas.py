import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RetrievalFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: uuid.UUID | None = None
    active_project_id: uuid.UUID | None = None
    authorized_project_ids: tuple[uuid.UUID, ...] = ()
    platform_knowledge_only: bool = False
    include_platform_knowledge: bool = False
    cross_project: bool = False
    phase: str | None = None
    source_type: str | None = None
    document_class: str | None = None
    procurement_stage: str | None = None
    tenderer_id: str | None = None


class NeighbourChunk(BaseModel):
    chunk_id: uuid.UUID
    chunk_index: int
    content: str
    page_or_section: str | None = None


class SourcePassage(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_or_section: str | None = None
    project: str
    project_id: uuid.UUID | None = None
    phase: str
    source_type: str | None = None
    document_class: str
    filename: str
    relative_path: str
    document_metadata: dict[str, Any] | None = None
    chunk_metadata: dict[str, Any] | None = None
    score: float = Field(description="Reciprocal Rank Fusion score")
    neighbours: list[NeighbourChunk] = Field(default_factory=list)


class ChunkSearchHit(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_or_section: str | None = None
    chunk_metadata: dict[str, Any] | None = None
    project: str
    project_id: uuid.UUID | None = None
    phase: str
    source_type: str | None = None
    document_class: str
    filename: str
    relative_path: str
    document_metadata: dict[str, Any] | None = None
    raw_score: float | None = None

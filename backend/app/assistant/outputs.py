import uuid
from enum import StrEnum

from pydantic import BaseModel, Field

from app.retrieval.schemas import SourcePassage


class EvidenceLabel(StrEnum):
    FACT = "Fact"
    ASSUMPTION = "Assumption"
    JUDGEMENT = "Judgement"
    RECOMMENDATION = "Recommendation"


class Citation(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    excerpt: str
    filename: str
    project: str
    phase: str | None = None
    source_type: str | None = None
    page_or_section: str | None = None
    label: EvidenceLabel = EvidenceLabel.FACT


class GroundedAnswer(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    cited_passages: list[SourcePassage] = Field(default_factory=list)
    evidence_sufficient: bool = True
    assumptions: list[str] = Field(default_factory=list)
    escalation_triggers: list[str] = Field(default_factory=list)
    workflow_deferred: bool = False
    workflow_note: str | None = None

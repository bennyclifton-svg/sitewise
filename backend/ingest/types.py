from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import uuid

DocumentClass = Literal[
    "drawing",
    "specification",
    "report",
    "certificate",
    "correspondence",
    "contract",
    "commercial",
    "schedule",
    "statutory_instrument",
    "photo",
    "unknown",
]

DocumentSubject = Literal[
    "planning", "heritage", "structural", "services", "hydraulic", "fire",
    "geotechnical", "survey", "cost", "programme", "contract_admin",
    "defects", "sustainability", "access", "acoustic", "none",
]

ClassificationBasis = Literal[
    "user", "structural", "filename", "content", "model", "default",
]

IngestMode = Literal["full_text", "register_only", "hybrid"]

SourceType = Literal["project_evidence", "reference", "doctrine"]

Phase = Literal["delivery", "procurement", "advisory", "consultants", "reference"]


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    absolute_path: Path
    relative_path: str
    project: str
    filename: str
    extension: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ProjectContext:
    project: str
    phase: str
    source_type: SourceType
    project_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class Classification:
    document_class: DocumentClass
    ingest_mode: IngestMode
    document_metadata: dict[str, str] = field(default_factory=dict)
    document_subject: DocumentSubject = "none"
    confidence: float = 0.0
    basis: ClassificationBasis = "default"


@dataclass(frozen=True, slots=True)
class IngestPlan:
    entry: ManifestEntry
    context: ProjectContext
    classification: Classification
    extractor: str
    chunker: str


@dataclass(frozen=True, slots=True)
class FolderSummary:
    folder: str
    discovered: int
    planned: int
    skipped: int
    by_class: dict[str, int]

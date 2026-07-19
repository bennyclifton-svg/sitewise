from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import uuid

DocumentClass = Literal[
    "unknown",
    "contract",
    "specification",
    "tender_submission",
    "trr",
    "evaluation",
    "rft",
    "addendum",
    "eoi",
    "tep",
    "drawing",
    "report",
    "certificate",
    "correspondence",
    "schedule",
    "reference_guide",
    "doctrine",
    "planning_instrument",
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

import uuid
from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.assistant.chat_models import InvalidChatModelError, resolve_chat_model
from app.sitewise.gate import OverlayStatus


def _validate_optional_chat_model(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return resolve_chat_model(stripped)
    except InvalidChatModelError as exc:
        raise ValueError(str(exc)) from exc


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    workspace_path: str
    phase: str
    archetype: str | None
    user_role: str | None
    state: str | None
    status: str
    overlay_status: OverlayStatus
    updated_at: datetime


class ProjectListResponse(BaseModel):
    projects: list[ProjectSummary]


class InboxUploadResult(BaseModel):
    id: uuid.UUID
    filename: str
    workspace_path: str
    content_hash: str
    size_bytes: int
    ingest_status: str
    message: str | None = None


class InboxUploadResponse(BaseModel):
    files: list[InboxUploadResult]


class PdfSheetProposal(BaseModel):
    index: int
    proposed_title: str
    filename: str
    has_text: bool


class PdfAnalyzeResponse(BaseModel):
    staging_id: str
    is_drawing_set: bool
    confidence: float
    page_count: int
    scores: dict = Field(default_factory=dict)
    pages: list[PdfSheetProposal] = Field(default_factory=list)


class StagedSplitRequest(BaseModel):
    source_filename: str = Field(min_length=1, max_length=512)


class CreateProjectRequest(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    archetype: str | None = Field(default=None, max_length=64)
    user_role: str | None = Field(default=None, max_length=64)
    state: str | None = Field(default=None, max_length=16)
    phase: str = Field(default="brief-planning", min_length=1, max_length=64)

    @field_validator("title", "phase")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("slug", "archetype", "user_role", "state")
    @classmethod
    def strip_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class EvidencePreview(BaseModel):
    id: uuid.UUID
    title: str
    filename: str
    relative_path: str
    source_type: str | None
    document_class: str
    excerpt: str
    content: str | None = None
    document_number: str | None = None
    revision: str | None = None
    category: str | None = None


class ProjectDetail(ProjectSummary):
    metadata: dict[str, Any] | None
    evidence_preview: EvidencePreview | None


class WorkspaceTreeNode(BaseModel):
    name: str
    path: str
    kind: str = "directory"
    description: str
    document_count: int = 0
    related_workflows: list[str] = Field(default_factory=list)
    children: list["WorkspaceTreeNode"] = Field(default_factory=list)


class ProjectWorkspaceTreeResponse(BaseModel):
    project_id: uuid.UUID
    root_path: str
    tree: list[WorkspaceTreeNode]


class PlatformKnowledgeBucket(BaseModel):
    kind: str
    document_count: int


class PlatformKnowledgeStatus(BaseModel):
    available: bool
    buckets: list[PlatformKnowledgeBucket]


class DraftArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    workflow_type: str
    version: int
    status: str
    title: str
    workspace_path: str
    author_user_id: uuid.UUID
    content_markdown: str
    model: str | None
    runtime: str
    provenance_metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class DraftArtifactSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    workflow_type: str
    version: int
    status: str
    title: str
    workspace_path: str
    author_user_id: uuid.UUID
    model: str | None
    runtime: str
    created_at: datetime
    updated_at: datetime


class ProjectCockpitBootstrapResponse(BaseModel):
    project: ProjectDetail
    projects: list[ProjectSummary]
    evidence: list[EvidencePreview]
    workspace_tree: ProjectWorkspaceTreeResponse
    platform_knowledge: PlatformKnowledgeStatus
    latest_drafts: dict[str, DraftArtifactSummary | None]
    timings_ms: dict[str, int] = Field(default_factory=dict)


class WorkflowTraceEvent(BaseModel):
    step: str
    status: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreatePmpRequest(BaseModel):
    thread_id: uuid.UUID | None = None
    chat_model: str | None = Field(
        default=None,
        max_length=128,
        validation_alias=AliasChoices("chatModel", "chat_model"),
    )

    @field_validator("chat_model")
    @classmethod
    def validate_chat_model(cls, value: str | None) -> str | None:
        return _validate_optional_chat_model(value)


class UpdatePmpRequest(BaseModel):
    thread_id: uuid.UUID | None = None
    chat_model: str | None = Field(
        default=None,
        max_length=128,
        validation_alias=AliasChoices("chatModel", "chat_model"),
    )

    @field_validator("chat_model")
    @classmethod
    def validate_chat_model(cls, value: str | None) -> str | None:
        return _validate_optional_chat_model(value)


class PatchDraftRequest(BaseModel):
    content_markdown: str = Field(min_length=1)


class CreatePmpResponse(BaseModel):
    status: str
    gate: OverlayStatus
    trace: list[WorkflowTraceEvent]
    draft: DraftArtifactResponse | None = None
    message: str | None = None


class CreateCostPlanRequest(BaseModel):
    thread_id: uuid.UUID | None = None
    chat_model: str | None = Field(
        default=None,
        max_length=128,
        validation_alias=AliasChoices("chatModel", "chat_model"),
    )

    @field_validator("chat_model")
    @classmethod
    def validate_chat_model(cls, value: str | None) -> str | None:
        return _validate_optional_chat_model(value)


class CreateCostPlanResponse(BaseModel):
    status: str
    gate: OverlayStatus
    trace: list[WorkflowTraceEvent]
    draft: DraftArtifactResponse | None = None
    message: str | None = None


class SortFilesRequest(BaseModel):
    thread_id: uuid.UUID | None = None
    chat_model: str | None = Field(
        default=None,
        max_length=128,
        validation_alias=AliasChoices("chatModel", "chat_model"),
    )

    @field_validator("chat_model")
    @classmethod
    def validate_chat_model(cls, value: str | None) -> str | None:
        return _validate_optional_chat_model(value)


class SortFilesSummary(BaseModel):
    inspected: int = 0
    moved: int = 0
    already_filed: int = 0
    unresolved: int = 0
    skipped: int = 0
    refused: int = 0


class SortFileRow(BaseModel):
    source_path: str
    filename: str
    outcome: str
    destination_path: str | None = None
    destination_filename: str | None = None
    reason: str | None = None
    document_number: str | None = None
    title: str | None = None
    revision: str | None = None
    category: str | None = None


class SortFilesResponse(BaseModel):
    status: str
    gate: OverlayStatus
    trace: list[WorkflowTraceEvent]
    summary: SortFilesSummary | None = None
    rows: list[SortFileRow] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    draft: DraftArtifactResponse | None = None
    message: str | None = None

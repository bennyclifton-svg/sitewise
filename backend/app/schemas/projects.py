import uuid
from datetime import datetime
from typing import Any, Literal, Self

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.assistant.chat_models import InvalidChatModelError, resolve_chat_model
from app.assistant.pmp_models import InvalidPmpModelError, resolve_pmp_model
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


def _validate_optional_pmp_model(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return resolve_pmp_model(stripped).configured_id
    except InvalidPmpModelError as exc:
        raise ValueError(str(exc)) from exc


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    workspace_path: str
    phase: str
    archetype: str | None
    building_class: str | None
    work_type: str | None
    user_role: str | None
    state: str | None
    profile_revision: int = Field(default=1, ge=1)
    status: str
    overlay_status: OverlayStatus
    updated_at: datetime


class ProjectListResponse(BaseModel):
    projects: list[ProjectSummary]


class RiskFlag(BaseModel):
    value: str
    severity: str
    title: str
    description: str


class ProjectSubclassSelection(BaseModel):
    value: str = Field(min_length=1, max_length=128)
    label: str | None = Field(default=None, max_length=512)

    @field_validator("value")
    @classmethod
    def strip_value(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("label")
    @classmethod
    def strip_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ProjectProfilePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    building_class: str | None = Field(default=None, max_length=64)
    work_type: str | None = Field(default=None, max_length=64)
    subclasses: list[str | ProjectSubclassSelection] | None = None
    scale: dict[str, Any] | None = None
    complexity: dict[str, Any] | None = None
    work_scope: list[str] | None = None
    user_role: str | None = Field(default=None, max_length=64)
    state: str | None = Field(default=None, max_length=16)
    clear_incompatible: bool = False

    @field_validator("building_class", "work_type", "user_role", "state")
    @classmethod
    def strip_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("subclasses")
    @classmethod
    def strip_optional_subclasses(
        cls,
        value: list[str | ProjectSubclassSelection] | None,
    ) -> list[str | ProjectSubclassSelection] | None:
        if value is None:
            return None
        stripped: list[str | ProjectSubclassSelection] = []
        for item in value:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    stripped.append(text)
            else:
                stripped.append(item)
        return stripped or None

    @field_validator("work_scope")
    @classmethod
    def strip_optional_string_lists(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        stripped = [item.strip() for item in value if item.strip()]
        return stripped or None


ProjectProfileField = Literal[
    "building_class",
    "work_type",
    "subclasses",
    "scale",
    "complexity",
    "work_scope",
    "user_role",
    "state",
]


class ProjectProfileView(BaseModel):
    project_id: uuid.UUID
    profile_revision: int = Field(ge=1)
    building_class: str | None = None
    work_type: str | None = None
    subclasses: list[str | ProjectSubclassSelection] = Field(default_factory=list)
    scale: dict[str, Any] = Field(default_factory=dict)
    complexity: dict[str, Any] = Field(default_factory=dict)
    work_scope: list[str] = Field(default_factory=list)
    user_role: str | None = None
    state: str | None = None


class ProjectProfileChange(BaseModel):
    profile: ProjectProfileView
    previous_revision: int = Field(ge=1)
    new_revision: int = Field(ge=1)
    changed_fields: list[ProjectProfileField]
    cleared_fields: list[ProjectProfileField]
    overlay_status: OverlayStatus
    risk_flags: list[RiskFlag]

    @model_validator(mode="after")
    def validate_revision_contract(self) -> Self:
        overlap = set(self.changed_fields) & set(self.cleared_fields)
        if overlap:
            raise ValueError("changed_fields and cleared_fields must not overlap")
        effective_change = bool(self.changed_fields or self.cleared_fields)
        expected_new_revision = (
            self.previous_revision + 1 if effective_change else self.previous_revision
        )
        if self.new_revision != expected_new_revision:
            raise ValueError(
                "new_revision must increment exactly once for an effective change "
                "and remain unchanged for a no-op"
            )
        if self.profile.profile_revision != self.new_revision:
            raise ValueError("profile revision must match new_revision")
        return self


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
    building_class: str | None = Field(default=None, max_length=64)
    work_type: str | None = Field(default=None, max_length=64)
    subclasses: list[str | ProjectSubclassSelection] | None = None
    scale: dict[str, Any] | None = None
    complexity: dict[str, Any] | None = None
    work_scope: list[str] | None = None
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

    @field_validator(
        "slug",
        "archetype",
        "building_class",
        "work_type",
        "user_role",
        "state",
    )
    @classmethod
    def strip_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("subclasses")
    @classmethod
    def strip_optional_subclasses(
        cls,
        value: list[str | ProjectSubclassSelection] | None,
    ) -> list[str | ProjectSubclassSelection] | None:
        if value is None:
            return None
        stripped: list[str | ProjectSubclassSelection] = []
        for item in value:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    stripped.append(text)
            else:
                stripped.append(item)
        return stripped or None

    @field_validator("work_scope")
    @classmethod
    def strip_optional_string_lists(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        stripped = [item.strip() for item in value if item.strip()]
        return stripped or None


class PatchProjectRequest(BaseModel):
    building_class: str | None = Field(default=None, max_length=64)
    work_type: str | None = Field(default=None, max_length=64)
    subclasses: list[str | ProjectSubclassSelection] | None = None
    scale: dict[str, Any] | None = None
    complexity: dict[str, Any] | None = None
    work_scope: list[str] | None = None
    user_role: str | None = Field(default=None, max_length=64)
    state: str | None = Field(default=None, max_length=16)

    @field_validator("building_class", "work_type", "user_role", "state")
    @classmethod
    def strip_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("subclasses")
    @classmethod
    def strip_optional_subclasses(
        cls,
        value: list[str | ProjectSubclassSelection] | None,
    ) -> list[str | ProjectSubclassSelection] | None:
        return CreateProjectRequest.strip_optional_subclasses(value)

    @field_validator("work_scope")
    @classmethod
    def strip_optional_string_lists(cls, value: list[str] | None) -> list[str] | None:
        return CreateProjectRequest.strip_optional_string_lists(value)


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
    risk_flags: list[RiskFlag] = Field(default_factory=list)


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


class WorkbookCellStyle(BaseModel):
    fill_color: str | None = None
    bold: bool = False


class WorkbookSheetPreview(BaseModel):
    name: str
    column_count: int
    rows: list[list[str]]
    styles: list[list[WorkbookCellStyle]] = Field(default_factory=list)


class WorkbookPreviewResponse(BaseModel):
    filename: str
    workspace_path: str
    sheets: list[WorkbookSheetPreview]
    warnings: list[str] = Field(default_factory=list)


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
    started_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectActivityEvent(WorkflowTraceEvent):
    id: uuid.UUID
    created_at: datetime


class ProjectActivityReferences(BaseModel):
    seed_consulted: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    context_refs: list[str] = Field(default_factory=list)


class ProjectActivityRun(BaseModel):
    run_id: uuid.UUID
    source: str
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    references: ProjectActivityReferences | None = None
    events: list[ProjectActivityEvent]


class ProjectActivityResponse(BaseModel):
    runs: list[ProjectActivityRun]
    newest_created_at: datetime | None = None


class DeleteProjectActivityRequest(BaseModel):
    run_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)


class DeleteProjectActivityResponse(BaseModel):
    deleted: int


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
        return _validate_optional_pmp_model(value)


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
        return _validate_optional_pmp_model(value)


class PatchDraftRequest(BaseModel):
    content_markdown: str = Field(min_length=1)


class ProjectDecisionOption(BaseModel):
    value: str
    label: str


class ProjectDecision(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    decision_id: str
    section: str
    label: str
    options: list[ProjectDecisionOption]
    selected: str
    source: str
    workflow_type: str
    revision: int = 1
    set_revision: int = 1
    locked: bool = False
    evidence_conflict: bool = False
    agent_suggestion: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ProjectDecisionListResponse(BaseModel):
    decisions: list[ProjectDecision]
    set_revision: int = 1


class UpdateProjectDecisionRequest(BaseModel):
    selected: str = Field(min_length=1, max_length=128)
    expected_revision: int = Field(ge=1)
    expected_set_revision: int = Field(ge=1)


class UpdateProjectDecisionResponse(BaseModel):
    decision: ProjectDecision
    draft: DraftArtifactResponse


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

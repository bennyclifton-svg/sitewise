"""Pydantic schemas for the Tender Comparison Module.

``ProjectContext`` is the versioned, validated shape of
``tender_comparisons.context`` (PRD §8.1) — validated at the API boundary,
stored as plain JSONB.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProjectContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_version: int = 1
    context_source: Literal["manual", "repository_selection"] = "manual"
    state: Literal["NSW", "VIC", "QLD"] | None = None
    region: Literal["metro", "regional"] | None = None
    build_type: Literal["new_build", "renovation", "addition"] | None = None
    dwelling_class: Literal["class_1a"] = "class_1a"
    storeys: int | None = None
    floor_area_m2: float | None = None
    site_area_m2: float | None = None
    soil_class: Literal["A", "S", "M", "H1", "H2", "E", "P", "unknown"] = "unknown"
    slope_class: Literal["flat", "moderate", "steep", "unknown"] = "unknown"
    bal_rating: Literal["none", "12.5", "19", "29", "40", "FZ", "unknown"] = "unknown"
    wind_rating: str | None = None
    flood_overlay: bool | None = None
    heritage_overlay: bool | None = None
    existing_dwelling_era: str | None = None
    demolition_required: bool | None = None
    spec_level: Literal["builder_base", "mid", "high", "architectural"] | None = None
    target_budget_cents: int | None = None
    notes: str | None = None

    @field_validator("target_budget_cents", mode="before")
    @classmethod
    def normalize_target_budget(cls, value: object) -> int | None:
        return currency_to_cents(value)

    @model_validator(mode="after")
    def require_manual_context_fields(self) -> "ProjectContext":
        if self.context_source != "manual":
            return self
        missing = [
            field
            for field in ("state", "region", "build_type", "storeys", "spec_level")
            if getattr(self, field) is None
        ]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"manual project context missing required fields: {joined}")
        return self


class ComparisonCreate(BaseModel):
    project_id: uuid.UUID
    context: ProjectContext


class ComparisonFromProjectFilesCreate(BaseModel):
    project_id: uuid.UUID
    workspace_paths: list[str] = Field(min_length=2, max_length=5)

    @field_validator("workspace_paths")
    @classmethod
    def normalize_workspace_paths(cls, value: list[str]) -> list[str]:
        paths = [path.strip() for path in value]
        if any(not path for path in paths):
            raise ValueError("workspace_paths cannot contain blank values")
        if len(set(paths)) != len(paths):
            raise ValueError("workspace_paths must be unique")
        return paths


class TenderPreparationRequest(BaseModel):
    project_id: uuid.UUID
    expected_profile_revision: int = Field(ge=1)
    expected_selection_revision: int = Field(ge=1)
    context_overrides: dict = Field(default_factory=dict)


class TenderPreparationResponse(BaseModel):
    supported: bool
    ready: bool
    context: ProjectContext | None = None
    missing_fields: list[str] = Field(default_factory=list)
    unsupported_reasons: list[str] = Field(default_factory=list)
    provenance: dict


class TenderIntakeRequest(TenderPreparationRequest):
    turn_id: str = Field(min_length=1, max_length=255)


class TenderIntakeResponse(BaseModel):
    comparison: "ComparisonDetail"
    idempotent_replay: bool = False


class ComparisonContextPatch(BaseModel):
    context: ProjectContext


class QuoteCreate(BaseModel):
    builder_name: str
    builder_abn: str | None = None
    quote_ref: str | None = None
    quote_date: date | None = None
    stated_total_cents: int | None = None
    gst_treatment: Literal["inclusive", "exclusive", "unclear"] = "unclear"
    contract_type: Literal["hia", "mba", "custom", "cost_plus", "unknown"] = "unknown"
    validity_days: int | None = None


class ProjectFileDocumentAttach(BaseModel):
    workspace_path: str


class DocumentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quote_id: uuid.UUID
    storage_path: str
    original_filename: str
    mime_type: str
    doc_type: str | None = None
    ocr_applied: bool
    page_count: int | None = None
    ingest_status: str
    created_at: datetime


class QuoteView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    comparison_id: uuid.UUID
    builder_name: str
    builder_abn: str | None = None
    quote_ref: str | None = None
    quote_date: date | None = None
    stated_total_cents: int | None = None
    gst_treatment: str
    contract_type: str
    validity_days: int | None = None
    stage: str
    created_at: datetime


class QuoteDetail(QuoteView):
    documents: list[DocumentView] = []


class ComparisonView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    context: ProjectContext
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ComparisonDetail(ComparisonView):
    quotes: list[QuoteDetail] = []


class ComparisonListResponse(BaseModel):
    comparisons: list[ComparisonDetail] = Field(default_factory=list)


class JobView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    comparison_id: uuid.UUID | None = None
    quote_id: uuid.UUID | None = None
    status: str
    attempts: int
    last_error: str | None = None
    run_after: datetime
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    document: DocumentView
    job: JobView


class ProgressMilestone(BaseModel):
    key: Literal["ingest", "extract", "map", "analyse", "review", "report"]
    label: str
    state: Literal["pending", "running", "done", "failed", "attention"]
    detail: str | None = None


class ProgressDocument(BaseModel):
    filename: str
    ingest_status: str


class ProgressQuote(BaseModel):
    quote_id: uuid.UUID
    builder_name: str
    stage: str
    stated_total_cents: int | None = None
    documents: list[ProgressDocument] = Field(default_factory=list)


class StageTimingView(BaseModel):
    stage: str
    duration_ms: int
    status: str
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hits: int = 0
    metadata: dict = Field(default_factory=dict)


class ComparisonProgressResponse(BaseModel):
    comparison_id: uuid.UUID
    status: str
    percent: int
    is_processing: bool
    qa_pending: int
    milestones: list[ProgressMilestone] = Field(default_factory=list)
    quotes: list[ProgressQuote] = Field(default_factory=list)
    stage_timings: list[StageTimingView] = Field(default_factory=list)


class ProcessComparisonResponse(BaseModel):
    queued: list[JobView] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class QAReviewItem(BaseModel):
    id: uuid.UUID
    entity_type: Literal[
        "cell_status",
        "mapping",
        "flag",
        "document_classification",
    ]
    report_impact_cents: int = 0
    confidence: float | None = None
    payload: dict = Field(default_factory=dict)


class QAQueueResponse(BaseModel):
    items: list[QAReviewItem] = Field(default_factory=list)


class QAResolveRequest(BaseModel):
    action: Literal["accept", "correct", "suppress"]
    corrected_value: dict | None = None
    reason: str | None = None


class QAResolveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    action: str
    qa_state: str | None = None


class QAAcceptAllResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    accepted: int
    skipped_documents: int


class MatrixMappingCandidate(BaseModel):
    cell_code: str
    name: str | None = None
    similarity: float | None = None
    via: str | None = None


class MatrixMappingChoice(BaseModel):
    mapping_id: uuid.UUID
    selected_cell_code: str
    candidates: list[MatrixMappingCandidate] = Field(default_factory=list)
    locked: bool = False


class MatrixQuoteCell(BaseModel):
    status: str
    amount_cents: int | None = None
    flags: list[str] = Field(default_factory=list)
    mapping_choices: list[MatrixMappingChoice] = Field(default_factory=list)


class MatrixCell(BaseModel):
    code: str
    name: str
    quotes: dict[str, MatrixQuoteCell] = Field(default_factory=dict)


class MatrixGroup(BaseModel):
    name: str
    cells: list[MatrixCell] = Field(default_factory=list)


class MatrixQuoteTotal(BaseModel):
    quote_id: uuid.UUID
    computed_total_cents: int
    stated_total_cents: int | None = None
    stated_total_source: Literal["manual", "extracted"] | None = None
    delta_cents: int | None = None
    delta_ratio: float | None = None
    reconciliation: Literal["match", "mismatch", "not_stated"]


class MatrixResponse(BaseModel):
    comparison_id: uuid.UUID
    groups: list[MatrixGroup] = Field(default_factory=list)
    totals: list[MatrixQuoteTotal] = Field(default_factory=list)


class TaxonomyCellView(BaseModel):
    code: str
    name: str
    group: str
    stage: str
    description: str | None = None


class TaxonomyListResponse(BaseModel):
    cells: list[TaxonomyCellView] = Field(default_factory=list)


class TaxonomySearchResult(TaxonomyCellView):
    similarity: float
    via: str


class TaxonomySearchResponse(BaseModel):
    results: list[TaxonomySearchResult] = Field(default_factory=list)


class ReportLifecycleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: uuid.UUID
    comparison_id: uuid.UUID
    draft_id: uuid.UUID
    version: int
    html_path: str | None = None
    pdf_path: str | None = None
    status: str
    approved_at: datetime | None = None
    delivered_at: datetime | None = None


class TenderReportStateResponse(BaseModel):
    comparison_id: uuid.UUID
    report: ReportLifecycleResponse | None = None
    draft: dict | None = None


class ReportDeliveredRequest(BaseModel):
    delivery_note: str | None = None


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class TenderDocumentPage(BaseModel):
    document_id: str
    page_no: int
    text_content: str
    image_path: str | None = None


class ExtractedLineItem(BaseModel):
    page_no: int
    bbox: BoundingBox | None = None
    description_raw: str
    section_path: list[str] = Field(default_factory=list)
    qty: float | None = None
    unit: str | None = None
    rate_cents: int | None = None
    amount_cents: int | None = None
    item_status: Literal["included", "excluded", "pc_allowance", "ps_allowance", "note"]
    allowance_cents: int | None = None
    extraction_confidence: float = Field(ge=0, le=1)

    @field_validator("rate_cents", "amount_cents", "allowance_cents", mode="before")
    @classmethod
    def normalize_money(cls, value: object) -> int | None:
        return currency_to_cents(value)


class ExtractedPageSubtotal(BaseModel):
    page_no: int
    label: str
    amount_cents: int
    confidence: float = Field(ge=0, le=1)

    @field_validator("amount_cents", mode="before")
    @classmethod
    def normalize_amount(cls, value: object) -> int | None:
        return currency_to_cents(value)


class ExtractionStructuredOutput(BaseModel):
    line_items: list[ExtractedLineItem] = Field(default_factory=list)
    page_subtotals: list[ExtractedPageSubtotal] = Field(default_factory=list)
    quote_total_cents: int | None = None

    @field_validator("quote_total_cents", mode="before")
    @classmethod
    def normalize_quote_total(cls, value: object) -> int | None:
        return currency_to_cents(value)


def currency_to_cents(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("currency value cannot be boolean")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value * 100))
    if not isinstance(value, str):
        raise ValueError("currency value must be int cents or dollar text")

    cleaned = (
        value.strip()
        .replace("$", "")
        .replace(",", "")
        .replace("AUD", "")
        .replace("aud", "")
        .strip()
    )
    if not cleaned:
        return None
    try:
        return int((Decimal(cleaned) * 100).quantize(Decimal("1")))
    except InvalidOperation as exc:
        raise ValueError(f"invalid currency value: {value}") from exc

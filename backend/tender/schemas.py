"""Pydantic schemas for the Tender Comparison Module.

``ProjectContext`` is the versioned, validated shape of
``tender_comparisons.context`` (PRD §8.1) — validated at the API boundary,
stored as plain JSONB.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ProjectContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_version: int = 1
    state: Literal["NSW", "VIC", "QLD"]
    region: Literal["metro", "regional"]
    build_type: Literal["new_build", "renovation", "addition"]
    dwelling_class: Literal["class_1a"] = "class_1a"
    storeys: int
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
    spec_level: Literal["builder_base", "mid", "high", "architectural"]
    target_budget_cents: int | None = None
    notes: str | None = None


class ComparisonCreate(BaseModel):
    project_id: uuid.UUID
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

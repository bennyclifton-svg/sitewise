"""SQLAlchemy models for the Tender Comparison Module (PRD §8).

All tables are prefixed ``tender_`` except the shared knowledge tables
(``taxonomy_*``, ``expectation_rules``, ``benchmarks``) and the evaluation
tables. Enum-ish columns are ``String`` + ``CheckConstraint`` (repo idiom);
the allowed-value lists mirror the PRD.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from pgvector.sqlalchemy import Vector

COMPARISON_STATUSES = (
    "intake",
    "processing",
    "qa",
    "report_draft",
    "approved",
    "delivered",
    "failed",
)
GST_TREATMENTS = ("inclusive", "exclusive", "unclear")
CONTRACT_TYPES = ("hia", "mba", "custom", "cost_plus", "unknown")
QUOTE_STAGES = (
    "intake",
    "ingest_document",
    "classify_document",
    "extract_line_items",
    "embed_items",
    "map_items",
    "run_expectations",
    "infer_silence",
    "run_analysis",
    "generate_flags",
    "assemble_report_draft",
    "complete",
)
DOC_TYPES = (
    "quote_letter",
    "inclusions_schedule",
    "tender_form",
    "boq",
    "trade_breakdown",
    "addendum",
    "drawing",
    "other",
)
INGEST_STATUSES = (
    "pending",
    "ingested",
    "duplicate",
    "unsupported_format",
    "manual_transcription_required",
    "failed",
)
LINE_ITEM_STATUSES = ("included", "excluded", "pc_allowance", "ps_allowance", "note")
TAXONOMY_STAGES = (
    "prelim",
    "base",
    "lockup",
    "fixing",
    "completion",
    "external",
    "statutory",
)
SYNONYM_SOURCES = ("seed", "correction", "auto")
RULE_SEVERITIES = ("must", "should", "conditional")
BENCHMARK_METRICS = ("absolute", "per_m2", "pct_of_build", "ratio")
BENCHMARK_SOURCES = ("model_seed", "published", "observed")
BENCHMARK_CONFIDENCES = ("low", "medium", "high")
MAPPING_TIERS = ("t0_exact", "t1_embedding", "t2_small_llm", "t3_frontier", "human")
QA_STATES = ("auto_pass", "needs_review", "confirmed", "corrected")
CELL_STATUSES = (
    "included",
    "excluded_explicit",
    "pc",
    "ps",
    "bundled",
    "not_required",
    "silent_ambiguous",
)
FLAG_TYPES = (
    "gap",
    "low_pc_allowance",
    "unrealistic_ps",
    "missing_expected",
    "scope_ambiguity",
    "price_outlier",
    "exclusion_risk",
    "statutory_missing",
    "arithmetic_inconsistency",
)
FLAG_SEVERITIES = ("info", "caution", "warning")
FLAG_QA_STATES = ("needs_review", "confirmed", "suppressed")
JOB_STATUSES = ("queued", "running", "done", "failed")
GOLDEN_SOURCES = ("real", "synthetic")
GOLDEN_DIFFICULTIES = ("easy", "medium", "hard")


def _values_check(column: str, values: tuple[str, ...], table: str) -> CheckConstraint:
    quoted = ", ".join(f"'{value}'" for value in values)
    return CheckConstraint(f"{column} IN ({quoted})", name=f"ck_{table}_{column}")


class TenderComparison(Base):
    __tablename__ = "tender_comparisons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="intake")
    context: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    quotes: Mapped[list["TenderQuote"]] = relationship(back_populates="comparison")

    __table_args__ = (
        _values_check("status", COMPARISON_STATUSES, "tender_comparisons"),
        Index("ix_tender_comparisons_project_id", "project_id"),
    )


class TenderQuote(Base):
    __tablename__ = "tender_quotes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comparison_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tender_comparisons.id", ondelete="CASCADE"),
        nullable=False,
    )
    builder_name: Mapped[str] = mapped_column(String(512), nullable=False)
    builder_abn: Mapped[str | None] = mapped_column(String(32))
    quote_ref: Mapped[str | None] = mapped_column(String(255))
    quote_date: Mapped[date | None] = mapped_column(Date)
    stated_total_cents: Mapped[int | None] = mapped_column(BigInteger)
    gst_treatment: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unclear"
    )
    contract_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unknown"
    )
    validity_days: Mapped[int | None] = mapped_column(Integer)
    stage: Mapped[str] = mapped_column(String(64), nullable=False, default="intake")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    comparison: Mapped["TenderComparison"] = relationship(back_populates="quotes")
    documents: Mapped[list["TenderDocument"]] = relationship(back_populates="quote")

    __table_args__ = (
        _values_check("gst_treatment", GST_TREATMENTS, "tender_quotes"),
        _values_check("contract_type", CONTRACT_TYPES, "tender_quotes"),
        _values_check("stage", QUOTE_STAGES, "tender_quotes"),
        Index("ix_tender_quotes_comparison_id", "comparison_id"),
    )


class TenderDocument(Base):
    __tablename__ = "tender_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tender_quotes.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type: Mapped[str | None] = mapped_column(String(64))
    classification_confidence: Mapped[float | None] = mapped_column(Numeric)
    ocr_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    page_count: Mapped[int | None] = mapped_column(Integer)
    ingest_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="pending"
    )
    content_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    quote: Mapped["TenderQuote"] = relationship(back_populates="documents")
    pages: Mapped[list["TenderPage"]] = relationship(back_populates="document")

    __table_args__ = (
        _values_check("doc_type", DOC_TYPES, "tender_documents"),
        _values_check("ingest_status", INGEST_STATUSES, "tender_documents"),
        UniqueConstraint(
            "quote_id", "content_hash", name="uq_tender_documents_quote_id_content_hash"
        ),
        Index("ix_tender_documents_quote_id", "quote_id"),
    )


class TenderPage(Base):
    __tablename__ = "tender_pages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tender_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped["TenderDocument"] = relationship(back_populates="pages")

    __table_args__ = (
        UniqueConstraint(
            "document_id", "page_no", name="uq_tender_pages_document_id_page_no"
        ),
    )


class TenderLineItem(Base):
    __tablename__ = "tender_line_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tender_quotes.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tender_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox: Mapped[dict | None] = mapped_column(JSONB)
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    section_path: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    qty: Mapped[float | None] = mapped_column(Numeric)
    unit: Mapped[str | None] = mapped_column(String(64))
    rate_cents: Mapped[int | None] = mapped_column(BigInteger)
    amount_cents: Mapped[int | None] = mapped_column(BigInteger)
    item_status: Mapped[str] = mapped_column(String(32), nullable=False)
    allowance_cents: Mapped[int | None] = mapped_column(BigInteger)
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric)
    embedding = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        _values_check("item_status", LINE_ITEM_STATUSES, "tender_line_items"),
        Index("ix_tender_line_items_quote_id", "quote_id"),
        Index("ix_tender_line_items_document_id", "document_id"),
    )


class TaxonomyCell(Base):
    __tablename__ = "taxonomy_cells"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    parent_code: Mapped[str | None] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    grp: Mapped[str] = mapped_column(String(64), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    applicability: Mapped[dict | None] = mapped_column(JSONB)
    bundling_parents: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    region_tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    build_type_tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    benchmark_key: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (_values_check("stage", TAXONOMY_STAGES, "taxonomy_cells"),)


class TaxonomySynonym(Base):
    __tablename__ = "taxonomy_synonyms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cell_code: Mapped[str] = mapped_column(
        String(32), ForeignKey("taxonomy_cells.code", ondelete="CASCADE"), nullable=False
    )
    phrase: Mapped[str] = mapped_column(Text, nullable=False)
    phrase_norm: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="seed")
    confidence: Mapped[float | None] = mapped_column(Numeric)
    # FK to tender_corrections.id is added in migration 009 (the corrections
    # table is created after this one in the chain).
    correction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "tender_corrections.id",
            ondelete="SET NULL",
            name="fk_taxonomy_synonyms_correction_id_tender_corrections",
            use_alter=True,
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        _values_check("source", SYNONYM_SOURCES, "taxonomy_synonyms"),
        UniqueConstraint(
            "cell_code", "phrase_norm", name="uq_taxonomy_synonyms_cell_code_phrase_norm"
        ),
    )


class ExpectationRule(Base):
    __tablename__ = "expectation_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rule_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    cell_code: Mapped[str] = mapped_column(
        String(32), ForeignKey("taxonomy_cells.code", ondelete="CASCADE"), nullable=False
    )
    predicate: Mapped[dict] = mapped_column(JSONB, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    region_tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    build_type_tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (_values_check("severity", RULE_SEVERITIES, "expectation_rules"),)


class Benchmark(Base):
    __tablename__ = "benchmarks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    benchmark_key: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False)
    build_type: Mapped[str] = mapped_column(String(32), nullable=False)
    spec_level: Mapped[str] = mapped_column(String(32), nullable=False)
    metric: Mapped[str] = mapped_column(String(32), nullable=False)
    p25: Mapped[float | None] = mapped_column(Numeric)
    p50: Mapped[float | None] = mapped_column(Numeric)
    p75: Mapped[float | None] = mapped_column(Numeric)
    unit: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    provenance: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    effective_date: Mapped[date | None] = mapped_column(Date)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("benchmarks.id", ondelete="SET NULL")
    )

    __table_args__ = (
        _values_check("metric", BENCHMARK_METRICS, "benchmarks"),
        _values_check("source", BENCHMARK_SOURCES, "benchmarks"),
        _values_check("confidence", BENCHMARK_CONFIDENCES, "benchmarks"),
        Index("ix_benchmarks_benchmark_key", "benchmark_key"),
    )


class TenderMapping(Base):
    __tablename__ = "tender_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    line_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tender_line_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    cell_code: Mapped[str] = mapped_column(
        String(32), ForeignKey("taxonomy_cells.code", ondelete="CASCADE"), nullable=False
    )
    allocation_fraction: Mapped[float] = mapped_column(
        Numeric, nullable=False, default=1.0
    )
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric)
    adjudication: Mapped[dict | None] = mapped_column(JSONB)
    qa_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="needs_review"
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        _values_check("tier", MAPPING_TIERS, "tender_mappings"),
        _values_check("qa_state", QA_STATES, "tender_mappings"),
        Index("ix_tender_mappings_line_item_id", "line_item_id"),
    )


class TenderCellStatus(Base):
    __tablename__ = "tender_cell_status"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comparison_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tender_comparisons.id", ondelete="CASCADE"),
        nullable=False,
    )
    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tender_quotes.id", ondelete="CASCADE"),
        nullable=False,
    )
    cell_code: Mapped[str] = mapped_column(
        String(32), ForeignKey("taxonomy_cells.code", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_cents: Mapped[int | None] = mapped_column(BigInteger)
    bundled_into_cell: Mapped[str | None] = mapped_column(String(32))
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Numeric)
    qa_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="needs_review"
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        _values_check("status", CELL_STATUSES, "tender_cell_status"),
        _values_check("qa_state", QA_STATES, "tender_cell_status"),
        UniqueConstraint(
            "comparison_id",
            "quote_id",
            "cell_code",
            name="uq_tender_cell_status_comparison_quote_cell",
        ),
    )


class TenderFlag(Base):
    __tablename__ = "tender_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comparison_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tender_comparisons.id", ondelete="CASCADE"),
        nullable=False,
    )
    quote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tender_quotes.id", ondelete="CASCADE")
    )
    cell_code: Mapped[str | None] = mapped_column(String(32))
    flag_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    headline: Mapped[str] = mapped_column(String(512), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    include_in_report: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    qa_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="needs_review"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        _values_check("flag_type", FLAG_TYPES, "tender_flags"),
        _values_check("severity", FLAG_SEVERITIES, "tender_flags"),
        _values_check("qa_state", FLAG_QA_STATES, "tender_flags"),
        Index("ix_tender_flags_comparison_id", "comparison_id"),
    )


class TenderCorrection(Base):
    __tablename__ = "tender_corrections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    field: Mapped[str] = mapped_column(String(128), nullable=False)
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)
    reviewer: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_tender_corrections_entity_id", "entity_id"),)


class TenderReport(Base):
    __tablename__ = "tender_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comparison_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tender_comparisons.id", ondelete="CASCADE"),
        nullable=False,
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    html_path: Mapped[str | None] = mapped_column(String(1024))
    pdf_path: Mapped[str | None] = mapped_column(String(1024))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_tender_reports_comparison_id", "comparison_id"),)


class TenderJob(Base):
    __tablename__ = "tender_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    comparison_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tender_comparisons.id", ondelete="CASCADE")
    )
    quote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tender_quotes.id", ondelete="CASCADE")
    )
    payload: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(255))
    last_error: Mapped[str | None] = mapped_column(Text)
    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        _values_check("status", JOB_STATUSES, "tender_jobs"),
        Index("ix_tender_jobs_status_run_after", "status", "run_after"),
    )


class GoldenDocument(Base):
    __tablename__ = "golden_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    doc_meta: Mapped[dict | None] = mapped_column(JSONB)
    anonymised: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        _values_check("source", GOLDEN_SOURCES, "golden_documents"),
        _values_check("difficulty", GOLDEN_DIFFICULTIES, "golden_documents"),
    )


class GoldenAnnotation(Base):
    __tablename__ = "golden_annotations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    golden_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("golden_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    annotation: Mapped[dict] = mapped_column(JSONB, nullable=False)
    annotator: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    git_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_versions: Mapped[dict | None] = mapped_column(JSONB)
    models: Mapped[dict | None] = mapped_column(JSONB)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary: Mapped[dict | None] = mapped_column(JSONB)


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    eval_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False
    )
    golden_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("golden_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False)

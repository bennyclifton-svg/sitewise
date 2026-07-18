"""A4: project-scoped extract content-hash cache."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

from tender.llm.client import LLMExtractionResponse
from tender.models import (
    TenderComparison,
    TenderDocument,
    TenderExtractCache,
    TenderFlag,
    TenderJob,
    TenderLineItem,
    TenderPage,
    TenderQuote,
)
from tender.schemas import ProjectContext
from tender.services import extract_cache, extraction_handler, telemetry
from tests.conftest import run_async

PROJECT_ID = uuid.uuid4()
COMPARISON_ID = uuid.uuid4()
QUOTE_ID = uuid.uuid4()
DOCUMENT_ID = uuid.uuid4()
CONTENT_HASH = "abc123hash"

PAYLOAD = {
    "line_items": [
        {
            "page_no": 1,
            "description_raw": "Slab and footings",
            "item_status": "included",
            "amount_cents": 4_500_000,
            "extraction_confidence": 0.95,
        }
    ],
    "page_subtotals": [],
    "quote_total_cents": 4_500_000,
}


class _ScalarResult:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def first(self) -> Any | None:
        return self._values[0] if self._values else None

    def all(self) -> list[Any]:
        return self._values


class _ExecuteResult:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def scalar_one(self) -> Any:
        return self._values[0]

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._values)


class _Session:
    def __init__(
        self,
        *,
        document: TenderDocument,
        quote: TenderQuote,
        comparison: TenderComparison,
        pages: list[TenderPage],
        context: dict,
    ) -> None:
        self.document = document
        self.quote = quote
        self.comparison = comparison
        self.pages = pages
        self.line_items: list[TenderLineItem] = []
        self.flags: list[TenderFlag] = []
        self.jobs: list[TenderJob] = []
        self.added_cache: list[TenderExtractCache] = []
        self.execute_values: list[list[Any]] = [[context], pages]
        self.flush_count = 0

    async def get(self, model: type, item_id: uuid.UUID) -> Any:
        if model is TenderDocument and item_id == self.document.id:
            return self.document
        if model is TenderQuote and item_id == self.quote.id:
            return self.quote
        if model is TenderComparison and item_id == self.comparison.id:
            return self.comparison
        return None

    async def execute(self, statement: Any) -> _ExecuteResult:
        if getattr(statement, "is_delete", False):
            self.line_items = [
                item for item in self.line_items if item.document_id != self.document.id
            ]
            return _ExecuteResult([])
        return _ExecuteResult(self.execute_values.pop(0))

    def add(self, obj: Any) -> None:
        if isinstance(obj, TenderLineItem):
            self.line_items.append(obj)
        elif isinstance(obj, TenderFlag):
            self.flags.append(obj)
        elif isinstance(obj, TenderJob):
            self.jobs.append(obj)
        elif isinstance(obj, TenderExtractCache):
            self.added_cache.append(obj)

    async def flush(self) -> None:
        self.flush_count += 1


class _CountingLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def extract(self, document_pages, schema, context):
        self.calls += 1
        return LLMExtractionResponse(
            data=PAYLOAD,
            model="test-model",
            prompt_version="0.1.0",
        )

    async def adjudicate(self, *args, **kwargs):
        raise NotImplementedError


def _context() -> dict:
    return ProjectContext(
        state="NSW",
        region="metro",
        build_type="new_build",
        storeys=1,
        spec_level="mid",
    ).model_dump(mode="json")


def _fixtures() -> tuple[TenderDocument, _Session]:
    document = TenderDocument(
        id=DOCUMENT_ID,
        quote_id=QUOTE_ID,
        storage_path="quote.pdf",
        original_filename="quote.pdf",
        mime_type="application/pdf",
        ingest_status="ingested",
        doc_type="quote_letter",
        page_count=1,
        content_hash=CONTENT_HASH,
    )
    quote = TenderQuote(
        id=QUOTE_ID,
        comparison_id=COMPARISON_ID,
        builder_name="Acme",
        stated_total_cents=4_500_000,
    )
    comparison = TenderComparison(
        id=COMPARISON_ID,
        project_id=PROJECT_ID,
        created_by=uuid.uuid4(),
        context=_context(),
    )
    page = TenderPage(
        document_id=document.id,
        page_no=1,
        image_path="page-0001.png",
        text_content="Slab and footings $45,000",
    )
    session = _Session(
        document=document,
        quote=quote,
        comparison=comparison,
        pages=[page],
        context=_context(),
    )
    return document, session


def _job(document: TenderDocument) -> SimpleNamespace:
    return SimpleNamespace(
        kind="extract_line_items",
        comparison_id=COMPARISON_ID,
        quote_id=document.quote_id,
        payload={"document_id": str(document.id)},
    )


def test_extractor_version_matches_prompt_version() -> None:
    from tender.llm.openai_client import PROMPT_VERSION

    assert extract_cache.EXTRACTOR_VERSION == PROMPT_VERSION


def test_extract_cache_miss_calls_llm_and_stores_payload(monkeypatch) -> None:
    document, session = _fixtures()
    llm = _CountingLLM()
    stored: list[dict[str, Any]] = []

    async def _get(*args, **kwargs):
        return None

    async def _put(session_arg, **kwargs):
        stored.append(kwargs)
        session_arg.add(
            TenderExtractCache(
                project_id=kwargs["project_id"],
                content_hash=kwargs["content_hash"],
                extractor_version=kwargs["extractor_version"],
                payload=kwargs["payload"],
                model=kwargs.get("model"),
            )
        )

    monkeypatch.setattr(extraction_handler.extract_cache, "get_cached_extract", _get)
    monkeypatch.setattr(extraction_handler.extract_cache, "put_cached_extract", _put)

    run_async(
        extraction_handler.extract_line_items_job(session, _job(document), llm_client=llm)
    )

    assert llm.calls == 1
    assert len(session.line_items) == 1
    assert session.line_items[0].description_raw == "Slab and footings"
    assert len(stored) == 1
    assert stored[0]["project_id"] == PROJECT_ID
    assert stored[0]["content_hash"] == CONTENT_HASH
    assert stored[0]["extractor_version"] == extract_cache.EXTRACTOR_VERSION
    assert len(session.added_cache) == 1
    assert session.jobs[0].kind == "embed_items"


def test_extract_cache_hit_skips_llm_and_materializes_items(monkeypatch) -> None:
    document, session = _fixtures()
    llm = _CountingLLM()
    cache_row = TenderExtractCache(
        project_id=PROJECT_ID,
        content_hash=CONTENT_HASH,
        extractor_version=extract_cache.EXTRACTOR_VERSION,
        payload={
            "line_items": [
                {
                    "page_no": 1,
                    "description_raw": "Cached slab",
                    "item_status": "included",
                    "amount_cents": 1_000_000,
                    "extraction_confidence": 0.9,
                }
            ],
            "page_subtotals": [],
            "quote_total_cents": 1_000_000,
        },
        model="cached-model",
    )
    put_calls: list[Any] = []

    async def _get(*args, **kwargs):
        return cache_row

    async def _put(*args, **kwargs):
        put_calls.append(kwargs)

    monkeypatch.setattr(extraction_handler.extract_cache, "get_cached_extract", _get)
    monkeypatch.setattr(extraction_handler.extract_cache, "put_cached_extract", _put)

    usage = telemetry.begin_stage_usage()
    try:
        run_async(
            extraction_handler.extract_line_items_job(
                session, _job(document), llm_client=llm
            )
        )
    finally:
        telemetry.end_stage_usage()

    assert llm.calls == 0
    assert put_calls == []
    assert len(session.line_items) == 1
    assert session.line_items[0].description_raw == "Cached slab"
    assert session.line_items[0].amount_cents == 1_000_000
    assert usage.cache_hits == 1
    assert session.jobs[0].kind == "embed_items"

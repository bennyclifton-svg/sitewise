from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import fitz

from tender.llm.client import LLMAdjudicationResponse, LLMExtractionResponse
from tender.models import TenderDocument, TenderFlag, TenderJob, TenderLineItem, TenderPage, TenderQuote
from tender.schemas import ProjectContext
from tender.services.classification import classify_document
from tender.services.extraction_handler import extract_line_items_job
from tender.services.ingestion import ingest_document
from tender.services.pdf import PageExtract
from tests.conftest import run_async


COMPARISON_ID = uuid.uuid4()
QUOTE_ID = uuid.uuid4()
DOCUMENT_ID = uuid.uuid4()


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
    def __init__(self, *, document: TenderDocument, quote: TenderQuote, context: dict) -> None:
        self.document = document
        self.quote = quote
        self.context = context
        self.pages: list[TenderPage] = []
        self.line_items: list[TenderLineItem] = []
        self.flags: list[TenderFlag] = []
        self.jobs: list[TenderJob] = []
        self.execute_values: list[list[Any]] = []

    async def get(self, model: type, item_id: uuid.UUID) -> Any:
        if model is TenderDocument and item_id == self.document.id:
            return self.document
        if model is TenderQuote and item_id == self.quote.id:
            return self.quote
        return None

    async def execute(self, statement: Any) -> _ExecuteResult:
        if getattr(statement, "is_delete", False):
            self.line_items = [
                item for item in self.line_items if item.document_id != self.document.id
            ]
            return _ExecuteResult([])
        return _ExecuteResult(self.execute_values.pop(0))

    def add(self, obj: Any) -> None:
        if isinstance(obj, TenderPage):
            self.pages.append(obj)
        elif isinstance(obj, TenderLineItem):
            self.line_items.append(obj)
        elif isinstance(obj, TenderFlag):
            self.flags.append(obj)
        elif isinstance(obj, TenderJob):
            self.jobs.append(obj)

    async def flush(self) -> None:
        return None


class _StubLLM:
    async def adjudicate(
        self,
        question,
        choices,
        evidence,
        context,
        *,
        prompt_version,
        model_key,
    ):
        return LLMAdjudicationResponse(
            choice="quote_letter",
            confidence=0.95,
            rationale="quote",
            model="test-model",
            prompt_version=prompt_version,
        )

    async def extract(self, document_pages, schema, context):
        return LLMExtractionResponse(
            data={
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
            },
            model="test-model",
            prompt_version="0.1.0",
        )


def _text_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (72, 72),
        "Quotation\nFooting $1,000\nSlab and drainage allowance included",
    )
    data = doc.tobytes()
    doc.close()
    return data


def _context() -> dict:
    return ProjectContext(
        state="NSW",
        region="metro",
        build_type="new_build",
        storeys=1,
        spec_level="mid",
    ).model_dump(mode="json")


def _job(kind: str, document: TenderDocument) -> SimpleNamespace:
    return SimpleNamespace(
        kind=kind,
        comparison_id=COMPARISON_ID,
        quote_id=document.quote_id,
        payload={"document_id": str(document.id)},
    )


def test_front_half_handlers_enqueue_next_stage() -> None:
    document = TenderDocument(
        id=DOCUMENT_ID,
        quote_id=QUOTE_ID,
        storage_path="quote.pdf",
        original_filename="quote.pdf",
        mime_type="application/pdf",
        ingest_status="pending",
        content_hash="hash-a",
    )
    quote = TenderQuote(
        id=QUOTE_ID,
        comparison_id=COMPARISON_ID,
        builder_name="Acme",
        stated_total_cents=4_500_000,
    )
    session = _Session(document=document, quote=quote, context=_context())
    llm = _StubLLM()

    session.execute_values = [[], []]
    run_async(
        ingest_document(
            session,
            _job("ingest_document", document),
            downloader=lambda *, storage_key: _text_pdf(),
            uploader=lambda *, storage_key, content, filename: storage_key,
            extractor=lambda pdf_bytes: [
                PageExtract(
                    page_no=1,
                    text="Quotation\nFooting $1,000\nSlab and drainage allowance included",
                )
            ],
        )
    )
    classify_job = session.jobs.pop(0)
    assert classify_job.kind == "classify_document"

    session.execute_values = [[page.text_content for page in session.pages], [session.context]]
    run_async(classify_document(session, classify_job, llm_client=llm))
    extract_job = session.jobs.pop(0)
    assert extract_job.kind == "extract_line_items"

    session.execute_values = [[session.context], session.pages]
    run_async(extract_line_items_job(session, extract_job, llm_client=llm))
    embed_job = session.jobs.pop(0)
    assert embed_job.kind == "embed_items"
    assert len(session.line_items) == 1

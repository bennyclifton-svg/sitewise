from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

from tender.llm.client import LLMExtractionResponse
from tender.models import TenderDocument, TenderFlag, TenderJob, TenderLineItem, TenderPage, TenderQuote
from tender.schemas import ProjectContext
from tender.services import extraction_handler
from tests.conftest import run_async


COMPARISON_ID = uuid.uuid4()
QUOTE_ID = uuid.uuid4()
DOCUMENT_ID = uuid.uuid4()


class _ScalarResult:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

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
        pages: list[TenderPage],
        context: dict,
        line_items: list[TenderLineItem] | None = None,
    ) -> None:
        self.document = document
        self.quote = quote
        self.pages = pages
        self.line_items = line_items or []
        self.flags: list[TenderFlag] = []
        self.jobs: list[TenderJob] = []
        self.execute_values: list[list[Any]] = [[context], pages]
        self.flush_count = 0

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
        if isinstance(obj, TenderLineItem):
            self.line_items.append(obj)
        elif isinstance(obj, TenderFlag):
            self.flags.append(obj)
        elif isinstance(obj, TenderJob):
            self.jobs.append(obj)

    async def flush(self) -> None:
        self.flush_count += 1


class _StubLLM:
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


def _document() -> TenderDocument:
    return TenderDocument(
        id=DOCUMENT_ID,
        quote_id=QUOTE_ID,
        storage_path="quote.pdf",
        original_filename="quote.pdf",
        mime_type="application/pdf",
        ingest_status="ingested",
        doc_type="quote_letter",
        page_count=1,
    )


def _quote() -> TenderQuote:
    return TenderQuote(
        id=QUOTE_ID,
        comparison_id=COMPARISON_ID,
        builder_name="Acme",
        stated_total_cents=4_500_000,
    )


def _job(document: TenderDocument) -> SimpleNamespace:
    return SimpleNamespace(
        kind="extract_line_items",
        comparison_id=COMPARISON_ID,
        quote_id=document.quote_id,
        payload={"document_id": str(document.id)},
    )


def test_extract_persists_line_items_and_replaces_prior_rows() -> None:
    document = _document()
    quote = _quote()
    prior = TenderLineItem(
        quote_id=QUOTE_ID,
        document_id=document.id,
        page_no=1,
        description_raw="Old row",
        item_status="included",
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
        pages=[page],
        context=_context(),
        line_items=[prior],
    )

    run_async(
        extraction_handler.extract_line_items_job(
            session, _job(document), llm_client=_StubLLM()
        )
    )

    assert len(session.line_items) == 1
    item = session.line_items[0]
    assert item.description_raw == "Slab and footings"
    assert item.amount_cents == 4_500_000
    assert item.item_status == "included"
    assert float(item.extraction_confidence) == 0.95
    assert session.flags == []
    assert quote.stage == "embed_items"
    assert session.jobs[0].kind == "embed_items"
    assert session.jobs[0].payload == {"document_id": str(document.id)}

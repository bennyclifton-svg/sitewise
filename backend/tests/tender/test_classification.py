from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from tender.llm.client import LLMAdjudicationResponse
from tender.models import TenderDocument, TenderJob, TenderQuote
from tender.schemas import ProjectContext
from tender.services import classification
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
        context: dict,
        page_texts: list[str],
    ) -> None:
        self.document = document
        self.quote = quote
        self.execute_values = [page_texts, [context]]
        self.jobs: list[TenderJob] = []
        self.flush_count = 0

    async def get(self, model: type, item_id: uuid.UUID) -> Any:
        if model is TenderDocument and item_id == self.document.id:
            return self.document
        if model is TenderQuote and item_id == self.quote.id:
            return self.quote
        return None

    async def execute(self, _statement: Any) -> _ExecuteResult:
        return _ExecuteResult(self.execute_values.pop(0))

    def add(self, obj: Any) -> None:
        if isinstance(obj, TenderJob):
            self.jobs.append(obj)

    async def flush(self) -> None:
        self.flush_count += 1


class _StubLLM:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

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
        self.calls.append(
            {
                "question": question,
                "choices": choices,
                "evidence": evidence,
                "context": context,
                "prompt_version": prompt_version,
                "model_key": model_key,
            }
        )
        return LLMAdjudicationResponse(
            choice="quote_letter",
            confidence=0.95,
            rationale="Looks like a quote",
            model="test-model",
            prompt_version=prompt_version,
        )

    async def extract(self, *args, **kwargs):
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
        original_filename="builder-quote.pdf",
        mime_type="application/pdf",
        ingest_status="ingested",
        page_count=3,
    )


def _quote() -> TenderQuote:
    return TenderQuote(id=QUOTE_ID, comparison_id=COMPARISON_ID, builder_name="Acme")


def _job(document: TenderDocument) -> SimpleNamespace:
    return SimpleNamespace(
        kind="classify_document",
        comparison_id=COMPARISON_ID,
        quote_id=document.quote_id,
        payload={"document_id": str(document.id)},
    )


def test_classify_writes_doc_type_and_confidence() -> None:
    document = _document()
    quote = _quote()
    session = _Session(
        document=document,
        quote=quote,
        context=_context(),
        page_texts=["page 1 body", "page 2 body", "page 3 body"],
    )
    llm = _StubLLM()

    run_async(classification.classify_document(session, _job(document), llm_client=llm))

    assert document.doc_type == "quote_letter"
    assert float(document.classification_confidence) == pytest.approx(0.95)
    assert quote.stage == "extract_line_items"
    assert session.jobs[0].kind == "extract_line_items"
    assert session.jobs[0].payload == {"document_id": str(document.id)}
    call = llm.calls[0]
    assert call["evidence"]["filename"] == "builder-quote.pdf"
    assert call["evidence"]["first_pages_text"] == ["page 1 body", "page 2 body"]
    assert "page 3 body" not in str(call["evidence"])
    assert call["model_key"] == "tender_model_adjudicate_small"
    assert call["prompt_version"] == "0.1.0"

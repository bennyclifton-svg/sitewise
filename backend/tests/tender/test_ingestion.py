from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import fitz

from tender.models import TenderDocument, TenderJob, TenderPage, TenderQuote
from tender.services import ingestion
from tender.services.ingestion import OfficeConversionError
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

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._values)


class _Session:
    def __init__(
        self,
        *,
        document: TenderDocument,
        quote: TenderQuote,
        execute_values: list[list[Any]],
        pages: list[TenderPage] | None = None,
    ) -> None:
        self.document = document
        self.quote = quote
        self.execute_values = execute_values
        self.pages = pages or []
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
        if isinstance(obj, TenderPage):
            self.pages.append(obj)
        elif isinstance(obj, TenderJob):
            self.jobs.append(obj)

    async def flush(self) -> None:
        self.flush_count += 1


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


def _image_only_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.draw_rect(fitz.Rect(50, 50, 500, 700), fill=(0.8, 0.8, 0.8))
    data = doc.tobytes()
    doc.close()
    return data


def _quote() -> TenderQuote:
    return TenderQuote(id=QUOTE_ID, comparison_id=COMPARISON_ID, builder_name="Acme")


def _document(
    *,
    mime_type: str = "application/pdf",
    filename: str = "quote.pdf",
    content_hash: str = "hash-a",
) -> TenderDocument:
    return TenderDocument(
        id=DOCUMENT_ID,
        quote_id=QUOTE_ID,
        storage_path="quotes/quote.pdf",
        original_filename=filename,
        mime_type=mime_type,
        ingest_status="pending",
        content_hash=content_hash,
    )


def _job(document: TenderDocument) -> SimpleNamespace:
    return SimpleNamespace(
        kind="ingest_document",
        comparison_id=COMPARISON_ID,
        quote_id=document.quote_id,
        payload={"document_id": str(document.id)},
    )


def _fake_extractor(text: str = "Quotation\nFooting $1,000\nSlab and drainage allowance included"):
    def _extract(pdf_bytes: bytes) -> list[PageExtract]:
        return [PageExtract(page_no=1, text=text)]
    return _extract


def test_ingest_persists_pages_and_marks_ingested() -> None:
    pdf_bytes = _text_pdf()
    document = _document()
    quote = _quote()
    session = _Session(document=document, quote=quote, execute_values=[[], []])
    uploaded: list[str] = []

    run_async(
        ingestion.ingest_document(
            session,
            _job(document),
            downloader=lambda *, storage_key: pdf_bytes,
            uploader=lambda *, storage_key, content, filename: uploaded.append(storage_key)
            or storage_key,
            extractor=_fake_extractor(),
        )
    )

    assert document.ingest_status == "ingested"
    assert document.page_count == 1
    assert document.ocr_applied is False
    assert quote.stage == "classify_document"
    assert len(session.pages) == 1
    assert "Slab and drainage allowance included" in session.pages[0].text_content
    assert len(uploaded) == 1
    assert session.jobs[0].kind == "classify_document"
    assert session.jobs[0].payload == {"document_id": str(document.id)}
    assert session.flush_count >= 2


def test_unsupported_format_short_circuits() -> None:
    document = _document(mime_type="text/plain", filename="quote.txt")
    quote = _quote()
    session = _Session(document=document, quote=quote, execute_values=[[]])

    run_async(
        ingestion.ingest_document(
            session,
            _job(document),
            downloader=lambda *, storage_key: b"junk",
            uploader=lambda **kwargs: "ignored",
            extractor=_fake_extractor(),
        )
    )

    assert document.ingest_status == "unsupported_format"
    assert session.pages == []
    assert session.jobs == []


def test_resume_skips_already_persisted_pages() -> None:
    pdf_bytes = _text_pdf()
    document = _document()
    quote = _quote()
    existing_page = TenderPage(
        document_id=document.id,
        page_no=1,
        image_path="existing.png",
        text_content="existing",
    )
    session = _Session(
        document=document,
        quote=quote,
        execute_values=[[], [1]],
        pages=[existing_page],
    )
    uploaded: list[str] = []

    run_async(
        ingestion.ingest_document(
            session,
            _job(document),
            downloader=lambda *, storage_key: pdf_bytes,
            uploader=lambda *, storage_key, content, filename: uploaded.append(storage_key)
            or storage_key,
            extractor=_fake_extractor(),
        )
    )

    assert uploaded == []
    assert len(session.pages) == 1
    assert document.ingest_status == "ingested"


def test_duplicate_hash_short_circuits() -> None:
    document = _document(content_hash="dup")
    quote = _quote()
    session = _Session(
        document=document,
        quote=quote,
        execute_values=[[uuid.uuid4()]],
    )

    run_async(
        ingestion.ingest_document(
            session,
            _job(document),
            downloader=lambda *, storage_key: _text_pdf(),
            uploader=lambda **kwargs: "ignored",
            extractor=_fake_extractor(),
        )
    )

    assert document.ingest_status == "duplicate"
    assert session.pages == []
    assert session.jobs == []


def test_xlsx_document_converts_to_pdf_before_ingest() -> None:
    pdf_bytes = _text_pdf()
    document = _document(
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="quote.xlsx",
    )
    quote = _quote()
    session = _Session(document=document, quote=quote, execute_values=[[], []])
    converter_calls: list[bytes] = []

    run_async(
        ingestion.ingest_document(
            session,
            _job(document),
            downloader=lambda *, storage_key: b"xlsx-bytes",
            uploader=lambda *, storage_key, content, filename: storage_key,
            extractor=_fake_extractor(),
            converter=lambda *, source_bytes, filename, mime_type: converter_calls.append(
                source_bytes
            )
            or pdf_bytes,
        )
    )

    assert converter_calls == [b"xlsx-bytes"]
    assert document.ingest_status == "ingested"
    assert document.page_count == 1
    assert len(session.pages) == 1
    assert session.jobs[0].kind == "classify_document"


def test_unconvertible_office_document_resolves_to_unsupported_format() -> None:
    document = _document(
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="quote.docx",
    )
    quote = _quote()
    session = _Session(document=document, quote=quote, execute_values=[[]])

    def fail_conversion(*, source_bytes, filename, mime_type):
        raise OfficeConversionError("LibreOffice failed")

    run_async(
        ingestion.ingest_document(
            session,
            _job(document),
            downloader=lambda *, storage_key: b"docx-bytes",
            uploader=lambda **kwargs: "ignored",
            extractor=_fake_extractor(),
            converter=fail_conversion,
        )
    )

    assert document.ingest_status == "unsupported_format"
    assert session.pages == []
    assert session.jobs == []

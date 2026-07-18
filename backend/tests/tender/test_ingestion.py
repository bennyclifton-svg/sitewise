from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import fitz
import httpx
import pytest

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
        self.commit_count = 0
        # Pages durable at the last commit — what survives a worker rollback.
        self.committed_pages: list[TenderPage] = []

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

    async def commit(self) -> None:
        self.commit_count += 1
        self.committed_pages = list(self.pages)


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


def _multi_page_pdf(page_count: int) -> bytes:
    doc = fitz.open()
    for index in range(page_count):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 72), f"Page {index + 1}")
    data = doc.tobytes()
    doc.close()
    return data


def _fake_extractor_pages(page_count: int):
    def _extract(pdf_bytes: bytes) -> list[PageExtract]:
        return [
            PageExtract(page_no=index + 1, text=f"Page {index + 1}")
            for index in range(page_count)
        ]
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


def test_page_uploads_commit_incrementally_so_a_retry_can_resume() -> None:
    """A failure on page 3 must not discard pages 1-2.

    The worker rolls the session back when a handler raises, so pages that were
    merely flushed are lost and the retry restarts from page 1 — re-uploading
    the whole document straight back into the same failure window. Committing
    per page is what makes the existing resume path reachable.
    """

    pdf_bytes = _multi_page_pdf(3)
    document = _document()
    quote = _quote()
    session = _Session(document=document, quote=quote, execute_values=[[], []])
    uploaded: list[str] = []

    def _flaky_uploader(*, storage_key, content, filename):
        if len(uploaded) == 2:
            raise httpx.RemoteProtocolError("Server disconnected")
        uploaded.append(storage_key)
        return storage_key

    with pytest.raises(httpx.RemoteProtocolError):
        run_async(
            ingestion.ingest_document(
                session,
                _job(document),
                downloader=lambda *, storage_key: pdf_bytes,
                uploader=_flaky_uploader,
                extractor=_fake_extractor_pages(3),
            )
        )

    assert len(uploaded) == 2
    assert [page.page_no for page in session.committed_pages] == [1, 2]
    assert document.ingest_status == "pending", "document stays retryable"


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


def test_warm_project_hash_clones_pages_without_odl() -> None:
    """A4: re-compare of an already-ingested project hash skips ODL/PNG."""
    from tender.models import TenderComparison

    project_id = uuid.uuid4()
    prior_id = uuid.uuid4()
    document = _document(content_hash="warm-hash")
    quote = _quote()
    comparison = TenderComparison(
        id=COMPARISON_ID,
        project_id=project_id,
        created_by=uuid.uuid4(),
        context={"state": "NSW", "region": "metro", "build_type": "renovation", "storeys": 1, "spec_level": "mid"},
    )
    prior_doc = TenderDocument(
        id=prior_id,
        quote_id=uuid.uuid4(),
        storage_path="prior.pdf",
        original_filename="prior.pdf",
        mime_type="application/pdf",
        ingest_status="ingested",
        content_hash="warm-hash",
        page_count=1,
        ocr_applied=False,
    )
    prior_page = TenderPage(
        document_id=prior_id,
        page_no=1,
        image_path="tender/comparisons/old/pages/page-0001.png",
        text_content="warm page text",
    )

    class _WarmSession(_Session):
        async def get(self, model: type, item_id: uuid.UUID) -> Any:
            if model is TenderDocument and item_id == prior_id:
                return prior_doc
            if model is TenderComparison and item_id == COMPARISON_ID:
                return comparison
            return await super().get(model, item_id)

    session = _WarmSession(
        document=document,
        quote=quote,
        # same-quote dup miss, project warm prior hit, prior pages
        execute_values=[[], [prior_id], [prior_page]],
    )
    download_calls: list[str] = []
    extract_calls: list[bytes] = []
    upload_calls: list[str] = []

    run_async(
        ingestion.ingest_document(
            session,
            _job(document),
            downloader=lambda *, storage_key: download_calls.append(storage_key) or b"",
            uploader=lambda *, storage_key, content, filename: upload_calls.append(storage_key)
            or storage_key,
            extractor=lambda pdf_bytes: extract_calls.append(pdf_bytes) or [],
        )
    )

    assert document.ingest_status == "ingested"
    assert document.page_count == 1
    assert download_calls == []
    assert extract_calls == []
    assert upload_calls == []
    assert len(session.pages) == 1
    assert session.pages[0].document_id == document.id
    assert session.pages[0].image_path == prior_page.image_path
    assert session.pages[0].text_content == "warm page text"
    assert quote.stage == "classify_document"
    assert session.jobs[0].kind == "classify_document"


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

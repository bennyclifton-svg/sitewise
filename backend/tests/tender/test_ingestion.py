import hashlib
import struct
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import fitz
import pytest
from app.config import settings
from tender.models import TenderDocument, TenderJob, TenderQuote
from tender.services import ingestion
from tests.conftest import run_async

COMPARISON_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
QUOTE_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DOCUMENT_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _png_size(png: bytes) -> tuple[int, int]:
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", png[16:24])
    return width, height


def _document(**overrides) -> TenderDocument:
    defaults = dict(
        id=DOCUMENT_ID,
        quote_id=QUOTE_ID,
        storage_path="tender/comparison/quote/quote.pdf",
        original_filename="quote.pdf",
        mime_type="application/pdf",
        ocr_applied=False,
        ingest_status="pending",
    )
    defaults.update(overrides)
    return TenderDocument(**defaults)


def _quote() -> TenderQuote:
    return TenderQuote(
        id=QUOTE_ID, comparison_id=COMPARISON_ID, builder_name="Acme Builders"
    )


def _job(document: TenderDocument) -> TenderJob:
    return TenderJob(
        id=uuid.uuid4(),
        kind="ingest_document",
        quote_id=document.quote_id,
        payload={"document_id": str(document.id)},
        status="running",
        attempts=0,
    )


def _page_nos_result(page_nos: list[int]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = page_nos
    return result


def _session(document: TenderDocument, existing_pages: list[int]) -> AsyncMock:
    session = AsyncMock()
    session.get = AsyncMock(side_effect=[document, _quote()])
    session.scalar = AsyncMock(return_value=None)  # no duplicate by default
    session.execute = AsyncMock(return_value=_page_nos_result(existing_pages))
    session.add = MagicMock()
    return session


def test_text_density_flags_image_only_page_not_text_page(
    text_pdf_bytes: bytes, image_only_pdf_bytes: bytes
) -> None:
    with fitz.open(stream=text_pdf_bytes, filetype="pdf") as doc:
        text_density = ingestion.page_text_density(doc[0])
    with fitz.open(stream=image_only_pdf_bytes, filetype="pdf") as doc:
        image_density = ingestion.page_text_density(doc[0])

    threshold = settings.tender_ocr_text_density_threshold
    assert text_density > threshold
    assert image_density < threshold


def test_render_page_png_at_150_dpi_pixel_size(text_pdf_bytes: bytes) -> None:
    with fitz.open(stream=text_pdf_bytes, filetype="pdf") as doc:
        png = ingestion.render_page_png(doc[0], dpi=150)

    width, height = _png_size(png)
    # 612 x 792 pt page at 150 DPI -> 612/72*150 = 1275, 792/72*150 = 1650.
    assert width == 1275
    assert height == 1650


def test_ingest_renders_and_persists_every_page(text_pdf_bytes: bytes) -> None:
    document = _document()
    session = _session(document, existing_pages=[])

    async def _run() -> None:
        with (
            patch.object(
                ingestion, "download_project_file", return_value=text_pdf_bytes
            ),
            patch.object(ingestion, "upload_project_file") as mock_upload,
        ):
            await ingestion.ingest_document(session, _job(document))

        assert document.ingest_status == "ingested"
        assert document.page_count == 2
        assert document.ocr_applied is False
        assert document.content_hash == hashlib.sha256(text_pdf_bytes).hexdigest()

        assert mock_upload.call_count == 2
        first_key = mock_upload.call_args_list[0].kwargs["storage_key"]
        assert first_key == (
            f"tender/{COMPARISON_ID}/{DOCUMENT_ID}/pages/page-0001.png"
        )
        width, height = _png_size(mock_upload.call_args_list[0].kwargs["content"])
        assert (width, height) == (1275, 1650)

        added_pages = [call.args[0] for call in session.add.call_args_list]
        assert [page.page_no for page in added_pages] == [1, 2]
        assert all("plasterboard" in page.text_content for page in added_pages)
        # one commit per page checkpoint + the final document commit
        assert session.commit.await_count == 3

    run_async(_run())


def test_ingest_resumes_from_existing_page_checkpoint(text_pdf_bytes: bytes) -> None:
    document = _document()
    session = _session(document, existing_pages=[1])

    async def _run() -> None:
        with (
            patch.object(
                ingestion, "download_project_file", return_value=text_pdf_bytes
            ),
            patch.object(ingestion, "upload_project_file") as mock_upload,
        ):
            await ingestion.ingest_document(session, _job(document))

        assert document.ingest_status == "ingested"
        assert mock_upload.call_count == 1
        only_key = mock_upload.call_args.kwargs["storage_key"]
        assert only_key.endswith("page-0002.png")
        added_pages = [call.args[0] for call in session.add.call_args_list]
        assert [page.page_no for page in added_pages] == [2]

    run_async(_run())


def test_ingest_duplicate_hash_short_circuits(text_pdf_bytes: bytes) -> None:
    document = _document()
    session = _session(document, existing_pages=[])
    session.scalar = AsyncMock(return_value=uuid.uuid4())  # another doc, same hash

    async def _run() -> None:
        with (
            patch.object(
                ingestion, "download_project_file", return_value=text_pdf_bytes
            ),
            patch.object(ingestion, "upload_project_file") as mock_upload,
        ):
            await ingestion.ingest_document(session, _job(document))

        assert document.ingest_status == "duplicate"
        mock_upload.assert_not_called()
        session.add.assert_not_called()

    run_async(_run())


def test_ingest_non_pdf_marked_unsupported_format() -> None:
    document = _document(
        original_filename="quote.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    session = _session(document, existing_pages=[])

    async def _run() -> None:
        with (
            patch.object(
                ingestion, "download_project_file", return_value=b"PK\x03\x04 not a pdf"
            ),
            patch.object(ingestion, "upload_project_file") as mock_upload,
        ):
            await ingestion.ingest_document(session, _job(document))

        assert document.ingest_status == "unsupported_format"
        mock_upload.assert_not_called()

    run_async(_run())


def test_ingest_image_only_pdf_with_ocr_disabled_keeps_empty_text(
    image_only_pdf_bytes: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "tender_ocr_enabled", False)
    document = _document()
    session = _session(document, existing_pages=[])

    async def _run() -> None:
        with (
            patch.object(
                ingestion, "download_project_file", return_value=image_only_pdf_bytes
            ),
            patch.object(ingestion, "upload_project_file") as mock_upload,
        ):
            await ingestion.ingest_document(session, _job(document))

        assert document.ingest_status == "ingested"
        assert document.ocr_applied is False
        assert mock_upload.call_count == 2
        added_pages = [call.args[0] for call in session.add.call_args_list]
        assert all(page.text_content == "" for page in added_pages)
        assert all(page.ocr_confidence is None for page in added_pages)

    run_async(_run())

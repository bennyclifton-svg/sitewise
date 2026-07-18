"""Document ingestion stage for the Tender Comparison Module."""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from tender.models import (
    TenderComparison,
    TenderDocument,
    TenderJob,
    TenderPage,
    TenderQuote,
)
from tender.services import jobs
from tender.services.pdf import PageExtract, extract_pages, render_page_png


@dataclass(frozen=True)
class _PreparedPage:
    page_no: int
    png_bytes: bytes
    text: str


Downloader = Callable[..., bytes]
Uploader = Callable[..., str]
Extractor = Callable[[bytes], list[PageExtract]]
Converter = Callable[..., bytes]


class OfficeConversionError(RuntimeError):
    pass


async def ingest_document(
    session: AsyncSession,
    job: TenderJob,
    *,
    deps=None,
    downloader: Downloader | None = None,
    uploader: Uploader | None = None,
    extractor: Extractor | None = None,
    converter: Converter | None = None,
) -> None:
    downloader = downloader or _default_downloader
    uploader = uploader or _default_uploader
    extractor = extractor or _default_extractor
    converter = converter or _default_office_converter

    document_id = uuid.UUID(job.payload["document_id"])
    document = await session.get(TenderDocument, document_id)
    if document is None:
        raise ValueError(f"ingest_document: document {document_id} not found")

    duplicate_id = await _duplicate_document_id(session, document)
    if duplicate_id is not None:
        document.ingest_status = "duplicate"
        await session.flush()
        return

    if not _is_pdf(document) and not _is_convertible_office(document):
        document.ingest_status = "unsupported_format"
        await session.flush()
        return

    if await _reuse_project_pages(session, job, document):
        return

    source_bytes = await asyncio.to_thread(downloader, storage_key=document.storage_path)
    if _is_pdf(document):
        pdf_bytes = source_bytes
    else:
        try:
            pdf_bytes = await asyncio.to_thread(
                converter,
                source_bytes=source_bytes,
                filename=document.original_filename,
                mime_type=document.mime_type,
            )
        except OfficeConversionError:
            document.ingest_status = "unsupported_format"
            await session.flush()
            return

    extracted_pages = await asyncio.to_thread(extractor, pdf_bytes)
    existing_page_nos = await _existing_page_numbers(session, document.id)

    prepared_pages: list[_PreparedPage] = []
    for page in extracted_pages:
        if page.page_no in existing_page_nos:
            continue

        png_bytes = render_page_png(
            pdf_bytes, page_no=page.page_no, dpi=settings.tender_page_render_dpi
        )
        prepared_pages.append(
            _PreparedPage(
                page_no=page.page_no,
                png_bytes=png_bytes,
                text=page.text,
            )
        )

    # Commit each page as it lands. The worker rolls the session back when a
    # handler raises, so flushed-but-uncommitted pages would be lost and the
    # retry would restart from page one — re-uploading a whole document into
    # the same failure window. Committing here is what makes the
    # ``_existing_page_numbers`` resume path above reachable.
    for page in prepared_pages:
        image_path = _page_storage_key(job, document, page.page_no)
        uploaded_path = await asyncio.to_thread(
            uploader,
            storage_key=image_path,
            content=page.png_bytes,
            filename=f"page-{page.page_no:04d}.png",
        )
        session.add(
            TenderPage(
                document_id=document.id,
                page_no=page.page_no,
                image_path=uploaded_path,
                text_content=page.text,
                ocr_confidence=None,
            )
        )
        await session.commit()

    document.page_count = len(extracted_pages)
    document.ocr_applied = False
    document.ingest_status = "ingested"

    quote = await session.get(TenderQuote, document.quote_id)
    if quote is not None:
        quote.stage = "classify_document"

    await jobs.enqueue(
        session,
        kind="classify_document",
        comparison_id=job.comparison_id,
        quote_id=document.quote_id,
        payload={"document_id": str(document.id)},
    )
    await session.flush()


async def _duplicate_document_id(
    session: AsyncSession, document: TenderDocument
) -> uuid.UUID | None:
    if not document.content_hash:
        return None

    result = await session.execute(
        select(TenderDocument.id)
        .where(
            TenderDocument.quote_id == document.quote_id,
            TenderDocument.content_hash == document.content_hash,
            TenderDocument.id != document.id,
            TenderDocument.ingest_status == "ingested",
        )
        .limit(1)
    )
    return result.scalars().first()


async def _reuse_project_pages(
    session: AsyncSession,
    job: TenderJob,
    document: TenderDocument,
) -> bool:
    """Clone pages from a prior ingested doc with the same project content hash.

    Skips ODL + PNG re-render on warm re-compare. Returns True when reuse applied.
    """
    if not document.content_hash:
        return False

    comparison = await session.get(TenderComparison, job.comparison_id)
    if comparison is None:
        return False

    prior_id = await _prior_ingested_document_id(
        session,
        project_id=comparison.project_id,
        content_hash=document.content_hash,
        exclude_id=document.id,
    )
    if prior_id is None:
        return False

    prior = await session.get(TenderDocument, prior_id)
    if prior is None:
        return False

    pages_result = await session.execute(
        select(TenderPage)
        .where(TenderPage.document_id == prior.id)
        .order_by(TenderPage.page_no)
    )
    prior_pages = list(pages_result.scalars().all())
    if not prior_pages:
        return False

    for page in prior_pages:
        session.add(
            TenderPage(
                document_id=document.id,
                page_no=page.page_no,
                image_path=page.image_path,
                text_content=page.text_content,
                ocr_confidence=page.ocr_confidence,
            )
        )

    document.page_count = prior.page_count or len(prior_pages)
    document.ocr_applied = prior.ocr_applied
    document.ingest_status = "ingested"

    quote = await session.get(TenderQuote, document.quote_id)
    if quote is not None:
        quote.stage = "classify_document"

    await jobs.enqueue(
        session,
        kind="classify_document",
        comparison_id=job.comparison_id,
        quote_id=document.quote_id,
        payload={"document_id": str(document.id)},
    )
    await session.flush()
    return True


async def _prior_ingested_document_id(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    content_hash: str,
    exclude_id: uuid.UUID,
) -> uuid.UUID | None:
    result = await session.execute(
        select(TenderDocument.id)
        .join(TenderQuote, TenderDocument.quote_id == TenderQuote.id)
        .join(TenderComparison, TenderQuote.comparison_id == TenderComparison.id)
        .where(
            TenderComparison.project_id == project_id,
            TenderDocument.content_hash == content_hash,
            TenderDocument.ingest_status == "ingested",
            TenderDocument.id != exclude_id,
        )
        .limit(1)
    )
    return result.scalars().first()


async def _existing_page_numbers(
    session: AsyncSession, document_id: uuid.UUID
) -> set[int]:
    result = await session.execute(
        select(TenderPage.page_no)
        .where(TenderPage.document_id == document_id)
        .order_by(TenderPage.page_no)
    )
    return set(result.scalars().all())


def _is_pdf(document: TenderDocument) -> bool:
    return document.mime_type.lower() == "application/pdf" or document.original_filename.lower().endswith(
        ".pdf"
    )


def _is_convertible_office(document: TenderDocument) -> bool:
    mime_type = document.mime_type.lower()
    suffix = Path(document.original_filename).suffix.lower()
    return mime_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    } or suffix in {".docx", ".xlsx"}


def _page_storage_key(job: TenderJob, document: TenderDocument, page_no: int) -> str:
    return (
        f"tender/comparisons/{job.comparison_id}/quotes/{document.quote_id}/"
        f"documents/{document.id}/pages/page-{page_no:04d}.png"
    )


def _default_downloader(*, storage_key: str) -> bytes:
    from app.storage.project_files import download_project_file

    return download_project_file(storage_key=storage_key)


def _default_uploader(*, storage_key: str, content: bytes, filename: str) -> str:
    from app.storage.project_files import upload_project_file

    return upload_project_file(storage_key=storage_key, content=content, filename=filename)


def _default_extractor(pdf_bytes: bytes) -> list[PageExtract]:
    return extract_pages(
        pdf_bytes,
        hybrid=settings.tender_odl_hybrid_enabled,
        hybrid_url=settings.tender_odl_hybrid_url,
        hybrid_mode=settings.tender_odl_hybrid_mode,
        hybrid_fallback=settings.tender_odl_hybrid_fallback,
    )


def _default_office_converter(
    *,
    source_bytes: bytes,
    filename: str,
    mime_type: str,
) -> bytes:
    source_name = Path(filename).name or f"source{_office_suffix_for_mime(mime_type)}"
    if Path(source_name).suffix.lower() not in {".docx", ".xlsx"}:
        source_name = f"{source_name}{_office_suffix_for_mime(mime_type)}"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        source_path = tmp_path / source_name
        source_path.write_bytes(source_bytes)
        try:
            subprocess.run(
                [
                    "soffice",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(tmp_path),
                    str(source_path),
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise OfficeConversionError("LibreOffice conversion failed") from exc

        output_path = source_path.with_suffix(".pdf")
        if not output_path.exists():
            candidates = list(tmp_path.glob("*.pdf"))
            if not candidates:
                raise OfficeConversionError("LibreOffice produced no PDF")
            output_path = candidates[0]
        return output_path.read_bytes()


def _office_suffix_for_mime(mime_type: str) -> str:
    if mime_type.lower() == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        return ".xlsx"
    return ".docx"

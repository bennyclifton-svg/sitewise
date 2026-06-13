"""Document ingestion stage (PRD §7.4 / §9.1).

Idempotent and checkpointed per page: every page row is committed as it is
persisted, keyed by ``UNIQUE (document_id, page_no)``, so a retry after a
crash resumes at the first missing page instead of restarting.

OCR detection (text density) always runs. Applying OCR shells out to
``ocrmypdf`` and needs Tesseract + Ghostscript on the host; when
``TENDER_OCR_ENABLED`` is false or the binaries are missing, low-text pages
keep ``text_content=''`` and a warning is logged.
"""

from __future__ import annotations

import hashlib
import asyncio
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from statistics import fmean

import fitz
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.storage.project_files import download_project_file, upload_project_file
from tender.models import TenderDocument, TenderJob, TenderPage, TenderQuote

logger = structlog.get_logger(__name__)

_OCR_TIMEOUT_SECONDS = 600


def page_text_density(page: fitz.Page) -> float:
    """Extracted characters per 1000 pt² of page area.

    A digital text page lands around 2–8; a scanned page with only OCR-noise
    or no text sits near zero. The default threshold (0.05) tolerates ~25
    stray characters on a letter/A4 page before treating it as digital.
    """

    area = page.rect.width * page.rect.height
    if area <= 0:
        return 0.0
    characters = len(page.get_text().strip())
    return characters / (area / 1000)


def render_page_png(page: fitz.Page, *, dpi: int) -> bytes:
    return page.get_pixmap(dpi=dpi).tobytes("png")


def _looks_like_pdf(document: TenderDocument, content: bytes) -> bool:
    return (
        document.mime_type == "application/pdf"
        or document.original_filename.lower().endswith(".pdf")
        or content[:5] == b"%PDF-"
    )


def apply_ocr(content: bytes) -> bytes:
    """Run ``ocrmypdf --skip-text`` over the document; returns the OCR'd bytes.

    Raises ``OcrUnavailableError`` when ocrmypdf/Tesseract are not installed.
    """

    if shutil.which("ocrmypdf") is None:
        raise OcrUnavailableError("ocrmypdf is not on PATH")

    with tempfile.TemporaryDirectory(prefix="tender-ocr-") as workdir:
        source = Path(workdir) / "source.pdf"
        target = Path(workdir) / "ocr.pdf"
        source.write_bytes(content)
        subprocess.run(
            ["ocrmypdf", "--skip-text", str(source), str(target)],
            check=True,
            capture_output=True,
            timeout=_OCR_TIMEOUT_SECONDS,
        )
        return target.read_bytes()


class OcrUnavailableError(RuntimeError):
    pass


def ocr_page_confidences(
    pdf: fitz.Document, page_numbers: list[int], *, dpi: int
) -> dict[int, float]:
    """Mean Tesseract word confidence (0–1) per page, via TSV output.

    Returns an empty dict when the tesseract binary is unavailable — the
    escape hatch then simply never fires.
    """

    if shutil.which("tesseract") is None:
        logger.warning("tender_ocr_no_tesseract_for_confidence")
        return {}

    confidences: dict[int, float] = {}
    with tempfile.TemporaryDirectory(prefix="tender-ocr-conf-") as workdir:
        for page_no in page_numbers:
            image = Path(workdir) / f"page-{page_no}.png"
            image.write_bytes(render_page_png(pdf[page_no - 1], dpi=dpi))
            result = subprocess.run(
                ["tesseract", str(image), "stdout", "tsv"],
                check=True,
                capture_output=True,
                timeout=_OCR_TIMEOUT_SECONDS,
            )
            word_confidences = []
            for line in result.stdout.decode("utf-8", errors="replace").splitlines()[1:]:
                fields = line.split("\t")
                if len(fields) >= 12 and fields[11].strip():
                    confidence = float(fields[10])
                    if confidence >= 0:
                        word_confidences.append(confidence / 100)
            if word_confidences:
                confidences[page_no] = fmean(word_confidences)
    return confidences


async def _existing_page_numbers(
    session: AsyncSession, document_id: uuid.UUID
) -> set[int]:
    result = await session.execute(
        select(TenderPage.page_no).where(TenderPage.document_id == document_id)
    )
    return set(result.scalars().all())


async def ingest_document(session: AsyncSession, job: TenderJob) -> None:
    document_id = uuid.UUID(str(job.payload["document_id"]))
    document = await session.get(TenderDocument, document_id)
    if document is None:
        raise ValueError(f"tender document {document_id} not found")
    quote = await session.get(TenderQuote, document.quote_id)
    if quote is None:
        raise ValueError(f"tender quote {document.quote_id} not found")

    content = await asyncio.to_thread(download_project_file, storage_key=document.storage_path)
    content_hash = hashlib.sha256(content).hexdigest()
    document.content_hash = content_hash

    duplicate_id = await session.scalar(
        select(TenderDocument.id)
        .where(
            TenderDocument.quote_id == document.quote_id,
            TenderDocument.content_hash == content_hash,
            TenderDocument.id != document.id,
        )
        .limit(1)
    )
    if duplicate_id is not None:
        document.ingest_status = "duplicate"
        await session.commit()
        logger.info(
            "tender_ingest_duplicate",
            document_id=str(document.id),
            duplicate_of=str(duplicate_id),
        )
        return

    if not _looks_like_pdf(document, content):
        # XLSX/DOCX conversion lands in M2; never silently dropped.
        document.ingest_status = "unsupported_format"
        await session.commit()
        logger.warning(
            "tender_ingest_unsupported_format",
            document_id=str(document.id),
            filename=document.original_filename,
            mime_type=document.mime_type,
        )
        return

    pdf = fitz.open(stream=content, filetype="pdf")
    try:
        threshold = settings.tender_ocr_text_density_threshold
        ocr_candidates = [
            page_no
            for page_no, page in enumerate(pdf, start=1)
            if page_text_density(page) < threshold
        ]

        ocr_applied = False
        page_confidences: dict[int, float] = {}
        if ocr_candidates and settings.tender_ocr_enabled:
            try:
                ocr_content = apply_ocr(content)
            except (OcrUnavailableError, subprocess.SubprocessError) as exc:
                logger.warning(
                    "tender_ingest_ocr_failed",
                    document_id=str(document.id),
                    error=str(exc),
                )
            else:
                pdf.close()
                pdf = fitz.open(stream=ocr_content, filetype="pdf")
                ocr_applied = True
                page_confidences = ocr_page_confidences(
                    pdf, ocr_candidates, dpi=settings.tender_page_render_dpi
                )
        elif ocr_candidates:
            logger.warning(
                "tender_ingest_ocr_disabled",
                document_id=str(document.id),
                low_text_pages=ocr_candidates,
            )

        if page_confidences:
            mean_confidence = fmean(page_confidences.values())
            if mean_confidence < settings.tender_ocr_min_confidence:
                # §7.4 escape hatch: don't emit junk pages.
                document.ocr_applied = True
                document.ingest_status = "manual_transcription_required"
                await session.commit()
                logger.warning(
                    "tender_ingest_manual_transcription_required",
                    document_id=str(document.id),
                    mean_confidence=mean_confidence,
                )
                return

        existing_pages = await _existing_page_numbers(session, document.id)
        for page_no, page in enumerate(pdf, start=1):
            if page_no in existing_pages:
                continue
            image_key = (
                f"tender/{quote.comparison_id}/{document.id}/pages/page-{page_no:04d}.png"
            )
            await asyncio.to_thread(
                upload_project_file,
                storage_key=image_key,
                content=render_page_png(page, dpi=settings.tender_page_render_dpi),
                filename=f"page-{page_no:04d}.png",
            )
            session.add(
                TenderPage(
                    document_id=document.id,
                    page_no=page_no,
                    image_path=image_key,
                    text_content=page.get_text().strip(),
                    ocr_confidence=page_confidences.get(page_no),
                )
            )
            # Per-page checkpoint: a retry resumes at the first missing page.
            await session.commit()

        document.page_count = pdf.page_count
        document.ocr_applied = ocr_applied
        document.ingest_status = "ingested"
        await session.commit()
        logger.info(
            "tender_ingest_done",
            document_id=str(document.id),
            page_count=pdf.page_count,
            ocr_applied=ocr_applied,
        )
    finally:
        pdf.close()

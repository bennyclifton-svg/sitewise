from pathlib import Path

import structlog

from app.config import settings
from app.document_intake.odl_pdf import PdfDocumentExtract, extract_pdf_document
from ingest.extractors.base import ExtractedDocument, PageText
from ingest.extractors.pdf_drawing import extract_pdf_title_block_text
from ingest.extractors.pdf_text import extract_pdf_text
from ingest.title_block import extract_pdf_title_block_fields, render_title_block_preview

logger = structlog.get_logger(__name__)

_TEXT_LAYER_FALLBACK_MIN_CHARS = 500
_ODL_MIN_TEXT_LAYER_RATIO = 0.6
# OpenDataLoader runs as a Java subprocess. It dies transiently (observed: exit
# 130 in 0.7s, where the same bytes then parse fine), so one crash must not cost
# the whole document.
_ODL_ATTEMPTS = 2


def _run_odl(path: Path):
    last_error: Exception | None = None
    for attempt in range(1, _ODL_ATTEMPTS + 1):
        try:
            return extract_pdf_document(
                path.read_bytes(),
                hybrid=settings.tender_odl_hybrid_enabled,
                hybrid_url=settings.tender_odl_hybrid_url,
                hybrid_mode=settings.tender_odl_hybrid_mode,
                hybrid_fallback=settings.tender_odl_hybrid_fallback,
            ), None
        except Exception as exc:
            last_error = exc
            logger.warning(
                "pdf_odl_attempt_failed",
                path=str(path),
                attempt=attempt,
                attempts=_ODL_ATTEMPTS,
                error_type=type(exc).__name__,
            )
    return None, last_error


def _text_layer_only(path: Path, odl_error: Exception) -> ExtractedDocument:
    """Salvage a document whose ODL extraction failed outright."""
    text_layer = _text_layer_extract(path)
    if text_layer is None or not text_layer.normalized_content.strip():
        raise odl_error
    logger.warning(
        "pdf_odl_failed_using_text_layer",
        path=str(path),
        text_layer_chars=len(text_layer.normalized_content.strip()),
        error_type=type(odl_error).__name__,
    )
    return ExtractedDocument(
        normalized_content=text_layer.normalized_content,
        page_count=text_layer.page_count,
        pages=text_layer.pages,
        drawing_identity=text_layer.drawing_identity,
        extraction_metadata={
            "pdf_extractor": "pdf_odl",
            "pdf_extraction_source": "text_layer_after_odl_failure",
            "odl_hybrid_requested": settings.tender_odl_hybrid_enabled,
            "odl_character_count": 0,
            "text_layer_character_count": len(text_layer.normalized_content.strip()),
            "odl_error": type(odl_error).__name__,
        },
    )


def extract_pdf_odl(path: Path) -> ExtractedDocument:
    document, odl_error = _run_odl(path)
    if document is None:
        assert odl_error is not None
        return _with_title_block(path, _text_layer_only(path, odl_error))

    extracted = _document_from_odl(document)
    text_layer = _text_layer_extract(path)
    selected = extracted
    if text_layer is not None and _should_use_text_layer(extracted, text_layer):
        metadata = _extraction_metadata(
            source="text_layer_fallback",
            odl=extracted,
            text_layer=text_layer,
            odl_document=document,
        )
        logger.warning(
            "pdf_odl_text_layer_fallback",
            path=str(path),
            odl_chars=metadata["odl_character_count"],
            text_layer_chars=metadata["text_layer_character_count"],
        )
        selected = ExtractedDocument(
            normalized_content=text_layer.normalized_content,
            page_count=text_layer.page_count,
            pages=text_layer.pages,
            drawing_identity=text_layer.drawing_identity,
            extraction_metadata=metadata,
        )
    else:
        selected = ExtractedDocument(
            normalized_content=extracted.normalized_content,
            page_count=extracted.page_count,
            pages=extracted.pages,
            drawing_identity=extracted.drawing_identity,
            extraction_metadata=_extraction_metadata(
            source="odl",
            odl=extracted,
            text_layer=text_layer,
            odl_document=document,
            ),
        )

    return _with_title_block(path, selected)


def _with_title_block(path: Path, selected: ExtractedDocument) -> ExtractedDocument:
    """Append the sheet's title block, identity first.

    The geometry-read identity leads the section because a title block's text
    order cannot be trusted: CAD exports emit labels and values in separate
    groups, so downstream line pairing would otherwise read label -> label.
    """
    try:
        title_block = extract_pdf_title_block_text(path)
    except Exception as exc:
        logger.warning(
            "pdf_title_block_extract_failed",
            path=str(path),
            error_type=type(exc).__name__,
        )
        title_block = ""

    identity = ""
    try:
        identity = render_title_block_preview(extract_pdf_title_block_fields(path)) or ""
    except Exception as exc:
        logger.warning(
            "pdf_title_block_fields_failed",
            path=str(path),
            error_type=type(exc).__name__,
        )

    section = "\n\n".join(part for part in (identity, title_block) if part)
    if not section:
        return selected

    return ExtractedDocument(
        normalized_content=f"{selected.normalized_content}\n\n## Title block\n\n{section}",
        page_count=selected.page_count,
        pages=selected.pages,
        drawing_identity=selected.drawing_identity,
        extraction_metadata={
            **(selected.extraction_metadata or {}),
            "pdf_title_block_extracted": True,
            "pdf_title_block_identity_read": bool(identity),
        },
    )


def _document_from_odl(document: PdfDocumentExtract) -> ExtractedDocument:
    page_texts = [
        PageText(page_number=page.page_no, text=page.text.strip())
        for page in document.pages
        if page.text.strip()
    ]
    parts = [
        f"## Page {page.page_number}\n\n{page.text}"
        for page in page_texts
    ]
    return ExtractedDocument(
        normalized_content="\n\n".join(parts).strip(),
        page_count=len(document.pages),
        pages=page_texts,
    )


def _text_layer_extract(path: Path) -> ExtractedDocument | None:
    try:
        return extract_pdf_text(path)
    except Exception as exc:
        logger.warning(
            "pdf_text_layer_fallback_failed",
            path=str(path),
            error_type=type(exc).__name__,
        )
        return None


def _should_use_text_layer(
    odl: ExtractedDocument,
    text_layer: ExtractedDocument,
) -> bool:
    odl_chars = len(odl.normalized_content.strip())
    text_layer_chars = len(text_layer.normalized_content.strip())
    if text_layer_chars == 0:
        return False
    if odl_chars == 0:
        return True
    if text_layer_chars < _TEXT_LAYER_FALLBACK_MIN_CHARS:
        return False
    return odl_chars / text_layer_chars < _ODL_MIN_TEXT_LAYER_RATIO


def _extraction_metadata(
    *,
    source: str,
    odl: ExtractedDocument,
    text_layer: ExtractedDocument | None,
    odl_document: PdfDocumentExtract,
) -> dict[str, object]:
    return {
        "pdf_extractor": "pdf_odl",
        "pdf_extraction_source": source,
        "odl_hybrid_requested": settings.tender_odl_hybrid_enabled,
        "odl_hybrid_mode": odl_document.hybrid_mode,
        "odl_hybrid_backend_available": odl_document.hybrid_backend_available,
        "odl_character_count": len(odl.normalized_content.strip()),
        "text_layer_character_count": (
            len(text_layer.normalized_content.strip()) if text_layer is not None else None
        ),
    }

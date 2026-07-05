from pathlib import Path

import structlog

from app.config import settings
from app.document_intake.odl_pdf import PdfDocumentExtract, extract_pdf_document
from ingest.extractors.base import ExtractedDocument, PageText
from ingest.extractors.pdf_text import extract_pdf_text

logger = structlog.get_logger(__name__)

_TEXT_LAYER_FALLBACK_MIN_CHARS = 500
_ODL_MIN_TEXT_LAYER_RATIO = 0.6


def extract_pdf_odl(path: Path) -> ExtractedDocument:
    document = extract_pdf_document(
        path.read_bytes(),
        hybrid=settings.tender_odl_hybrid_enabled,
        hybrid_url=settings.tender_odl_hybrid_url,
        hybrid_mode=settings.tender_odl_hybrid_mode,
        hybrid_fallback=settings.tender_odl_hybrid_fallback,
    )
    extracted = _document_from_odl(document)
    text_layer = _text_layer_extract(path)
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
        return ExtractedDocument(
            normalized_content=text_layer.normalized_content,
            page_count=text_layer.page_count,
            pages=text_layer.pages,
            drawing_identity=text_layer.drawing_identity,
            extraction_metadata=metadata,
        )
    return ExtractedDocument(
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
    except Exception:
        logger.exception("pdf_text_layer_fallback_failed", path=str(path))
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

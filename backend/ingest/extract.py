import structlog

from ingest.extractors.base import ExtractedDocument
from ingest.sanitize import sanitize_text
from ingest.extractors.docx import extract_docx
from ingest.extractors.dwg import extract_dwg
from ingest.extractors.markdown import extract_markdown
from ingest.extractors.pdf_drawing import extract_pdf_drawing
from ingest.extractors.pdf_odl import extract_pdf_odl
from ingest.extractors.pdf_text import extract_pdf_text
from ingest.types import IngestPlan

logger = structlog.get_logger(__name__)

_EXTRACTORS = {
    "markdown": extract_markdown,
    "docx": extract_docx,
    "pdf_text": extract_pdf_text,
    "pdf_odl": extract_pdf_odl,
    "pdf_drawing": extract_pdf_drawing,
    "dwg": extract_dwg,
}


def extract_document(plan: IngestPlan) -> ExtractedDocument | None:
    extractor_name = plan.extractor
    if extractor_name == "unsupported" or extractor_name == "register_stub":
        logger.warning("extract_skipped", relative_path=plan.entry.relative_path, extractor=extractor_name)
        return None

    extractor = _EXTRACTORS.get(extractor_name)
    if extractor is None:
        logger.warning("extract_unknown", relative_path=plan.entry.relative_path, extractor=extractor_name)
        return None

    extracted = extractor(plan.entry.absolute_path)
    cleaned = sanitize_text(extracted.normalized_content).strip()
    if not cleaned:
        logger.warning("extract_empty", relative_path=plan.entry.relative_path)
        return None
    return ExtractedDocument(
        normalized_content=cleaned,
        page_count=extracted.page_count,
        pages=extracted.pages,
        drawing_identity=extracted.drawing_identity,
        extraction_metadata=extracted.extraction_metadata,
    )

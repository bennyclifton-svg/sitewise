from ingest.types import Classification, IngestPlan, ManifestEntry, ProjectContext

USEFUL_TEXT_MIN_CHARS = 200


def has_useful_text(text: str | None) -> bool:
    """D3: the single definition of 'worth indexing'. Do not fork this."""
    return bool(text) and len(text.strip()) >= USEFUL_TEXT_MIN_CHARS


def _extractor_for(classification: Classification, extension: str) -> str:
    if extension == ".pdf":
        return "pdf_odl"
    if classification.document_class == "drawing":
        if extension == ".dwg":
            return "dwg"
        if extension == ".md":
            return "markdown"
        return "register_stub"
    if extension == ".docx":
        return "docx"
    if extension == ".rtf":
        return "rtf"
    if extension == ".md":
        return "markdown"
    return "unsupported"


def _chunker_for(classification: Classification) -> str:
    if classification.document_class == "specification":
        return "specification"
    if classification.document_class == "drawing":
        return "register"      # bounded chunker for title-block + notes
    return "prose"


def should_persist_chunks(plan: IngestPlan, *, extracted_text: str | None) -> bool:
    """Persist chunks when there is useful text. Class never decides this (D3)."""
    if plan.extractor == "unsupported":
        return False
    return has_useful_text(extracted_text)


def build_ingest_plan(entry: ManifestEntry, context: ProjectContext, classification: Classification) -> IngestPlan:
    return IngestPlan(
        entry=entry,
        context=context,
        classification=classification,
        extractor=_extractor_for(classification, entry.extension),
        chunker=_chunker_for(classification),
    )

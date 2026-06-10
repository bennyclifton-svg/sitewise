from ingest.types import Classification, IngestPlan, ManifestEntry, ProjectContext


def _extractor_for(classification: Classification, extension: str) -> str:
    if classification.document_class == "doctrine" or classification.document_class == "reference_guide":
        return "markdown" if extension == ".md" else "pdf_text"
    if classification.document_class == "drawing":
        if extension == ".dwg":
            return "dwg"
        if extension == ".pdf":
            return "pdf_drawing"
        return "register_stub"
    if extension == ".docx":
        return "docx"
    if extension == ".md":
        return "markdown"
    if extension == ".pdf":
        return "pdf_text"
    return "unsupported"


def _chunker_for(classification: Classification) -> str:
    if classification.ingest_mode == "register_only":
        return "register"
    if classification.document_class == "specification":
        return "specification"
    return "prose"


def should_persist_chunks(plan: IngestPlan) -> bool:
    document_class = plan.classification.document_class
    ingest_mode = plan.classification.ingest_mode
    if ingest_mode == "register_only":
        return False
    if document_class in {"doctrine", "reference_guide"}:
        return False
    return True


def build_ingest_plan(entry: ManifestEntry, context: ProjectContext, classification: Classification) -> IngestPlan:
    return IngestPlan(
        entry=entry,
        context=context,
        classification=classification,
        extractor=_extractor_for(classification, entry.extension),
        chunker=_chunker_for(classification),
    )

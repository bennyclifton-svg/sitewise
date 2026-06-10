from ingest.chunkers.base import TextChunk
from ingest.sanitize import sanitize_text
from ingest.chunkers.prose import chunk_prose
from ingest.chunkers.register import chunk_register
from ingest.chunkers.specification import chunk_specification
from ingest.extractors.base import ExtractedDocument
from ingest.types import IngestPlan

_CHUNKERS = {
    "prose": chunk_prose,
    "specification": chunk_specification,
    "register": chunk_register,
}


def chunk_document(
    extracted: ExtractedDocument,
    plan: IngestPlan,
) -> list[TextChunk]:
    chunker = _CHUNKERS.get(plan.chunker, chunk_prose)
    extension = plan.entry.extension.lstrip(".") or "text"
    chunks = chunker(
        extracted.normalized_content,
        source_format=extension,
        relative_path=plan.entry.relative_path,
    )
    return [
        TextChunk(
            chunk_index=chunk.chunk_index,
            content=sanitize_text(chunk.content),
            page_or_section=chunk.page_or_section,
            token_count=chunk.token_count,
            chunk_metadata=chunk.chunk_metadata,
        )
        for chunk in chunks
        if sanitize_text(chunk.content).strip()
    ]

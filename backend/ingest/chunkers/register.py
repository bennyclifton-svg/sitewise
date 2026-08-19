from ingest.chunkers.base import TextChunk
from ingest.chunkers.prose import _split_oversized


def chunk_register(text: str, *, source_format: str, relative_path: str) -> list[TextChunk]:
    content = text.strip()
    if not content:
        return []
    chunks = _split_oversized(content, "register")
    return [
        TextChunk(
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            page_or_section=chunk.page_or_section,
            token_count=chunk.token_count,
            chunk_metadata={
                "source_format": source_format,
                "relative_path": relative_path,
                **(chunk.chunk_metadata or {}),
            },
        )
        for chunk in chunks
    ]

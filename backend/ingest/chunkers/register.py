from ingest.chunkers.base import TextChunk
from ingest.chunkers.prose import count_tokens


def chunk_register(text: str, *, source_format: str, relative_path: str) -> list[TextChunk]:
    content = text.strip()
    if not content:
        return []
    return [
        TextChunk(
            chunk_index=0,
            content=content,
            page_or_section="register",
            token_count=count_tokens(content),
            chunk_metadata={"source_format": source_format, "relative_path": relative_path},
        )
    ]

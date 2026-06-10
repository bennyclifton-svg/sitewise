import re

from ingest.chunkers.base import TextChunk
from ingest.chunkers.prose import TARGET_TOKENS, _split_oversized, count_tokens

_TRADE_SECTION_RE = re.compile(r"(?:^|\n)(\d{4}\s+[A-Z][^\n]{3,80})\n", re.MULTILINE)


def chunk_specification(text: str, *, source_format: str, relative_path: str) -> list[TextChunk]:
    del relative_path
    if not text.strip():
        return []

    matches = list(_TRADE_SECTION_RE.finditer(text))
    if len(matches) < 2:
        return [
            TextChunk(
                chunk_index=index,
                content=piece.content,
                page_or_section=piece.page_or_section,
                token_count=piece.token_count,
                chunk_metadata={**(piece.chunk_metadata or {}), "source_format": source_format},
            )
            for index, piece in enumerate(_split_oversized(text.strip(), "Specification"))
        ]

    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        label = match.group(1).strip()
        start = match.start(1)
        end = matches[index + 1].start(1) if index + 1 < len(matches) else len(text)
        sections.append((label, text[start:end].strip()))

    chunks: list[TextChunk] = []
    chunk_index = 0
    for label, body in sections:
        if count_tokens(body) <= TARGET_TOKENS:
            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    content=body,
                    page_or_section=label,
                    token_count=count_tokens(body),
                    chunk_metadata={"source_format": source_format},
                )
            )
            chunk_index += 1
            continue
        for piece in _split_oversized(body, label):
            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    content=piece.content,
                    page_or_section=piece.page_or_section,
                    token_count=piece.token_count,
                    chunk_metadata={**(piece.chunk_metadata or {}), "source_format": source_format},
                )
            )
            chunk_index += 1

    return chunks

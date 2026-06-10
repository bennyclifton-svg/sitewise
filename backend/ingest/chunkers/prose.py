import re

from ingest.chunkers.base import TextChunk

TARGET_TOKENS = 600
OVERLAP_TOKENS = 80

_HEADER_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
_TOKEN_RE = re.compile(r"\w+|[^\w\s]|\s+")


def _encode(text: str) -> list[str]:
    # Keep ingestion and tests offline even when tiktoken has not cached cl100k_base.
    return _TOKEN_RE.findall(text)


def _decode(tokens: list[str]) -> str:
    return "".join(tokens)


def count_tokens(text: str) -> int:
    return len(_encode(text))


def _split_oversized(text: str, section_label: str | None) -> list[TextChunk]:
    tokens = _encode(text)
    if len(tokens) <= TARGET_TOKENS:
        return [
            TextChunk(
                chunk_index=0,
                content=text.strip(),
                page_or_section=section_label,
                token_count=len(tokens),
            )
        ]

    chunks: list[TextChunk] = []
    start = 0
    chunk_index = 0
    while start < len(tokens):
        end = min(start + TARGET_TOKENS, len(tokens))
        piece = _decode(tokens[start:end]).strip()
        if piece:
            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    content=piece,
                    page_or_section=section_label,
                    token_count=count_tokens(piece),
                    chunk_metadata={"char_start": start, "char_end": end},
                )
            )
            chunk_index += 1
        if end >= len(tokens):
            break
        start = max(end - OVERLAP_TOKENS, start + 1)

    return chunks


def chunk_prose(text: str, *, source_format: str, relative_path: str) -> list[TextChunk]:
    del relative_path
    if not text.strip():
        return []

    sections: list[tuple[str | None, str]] = []
    matches = list(_HEADER_RE.finditer(text))
    if not matches:
        sections.append((None, text))
    else:
        if matches[0].start() > 0:
            sections.append((None, text[: matches[0].start()]))
        for index, match in enumerate(matches):
            label = match.group(2).strip()
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            sections.append((label, text[start:end]))

    chunks: list[TextChunk] = []
    chunk_index = 0
    for label, body in sections:
        for piece in _split_oversized(body.strip(), label):
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

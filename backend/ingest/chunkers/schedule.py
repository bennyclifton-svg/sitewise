import re

from ingest.chunkers.base import TextChunk
from ingest.chunkers.prose import TARGET_TOKENS, _split_oversized, count_tokens

_TABLE_ROW_RE = re.compile(r"^\s*\|.+\|\s*$")
_NUMBERED_ROW_RE = re.compile(r"^\s*\d+[\.)]\s+\S")


def chunk_schedule(text: str, *, source_format: str, relative_path: str) -> list[TextChunk]:
    content = text.strip()
    if not content:
        return []
    rows = _schedule_rows(content)
    if len(rows) >= 2:
        chunks: list[TextChunk] = []
        for index, (label, body) in enumerate(rows):
            if count_tokens(body) <= TARGET_TOKENS:
                chunks.append(
                    TextChunk(
                        chunk_index=index,
                        content=body,
                        page_or_section=label,
                        token_count=count_tokens(body),
                        chunk_metadata={
                            "source_format": source_format,
                            "relative_path": relative_path,
                        },
                    )
                )
                continue
            for piece in _split_oversized(body, label):
                chunks.append(
                    TextChunk(
                        chunk_index=len(chunks),
                        content=piece.content,
                        page_or_section=piece.page_or_section,
                        token_count=piece.token_count,
                        chunk_metadata={
                            "source_format": source_format,
                            "relative_path": relative_path,
                            **(piece.chunk_metadata or {}),
                        },
                    )
                )
        return chunks
    pieces = _split_oversized(content, "schedule")
    return [
        TextChunk(
            chunk_index=index,
            content=piece.content,
            page_or_section=piece.page_or_section,
            token_count=piece.token_count,
            chunk_metadata={
                "source_format": source_format,
                "relative_path": relative_path,
                **(piece.chunk_metadata or {}),
            },
        )
        for index, piece in enumerate(pieces)
    ]


def _schedule_rows(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    table_rows = [line.strip() for line in lines if _TABLE_ROW_RE.match(line)]
    data_rows = [row for row in table_rows if not _is_table_separator(row)]
    if len(data_rows) >= 3:
        body_rows = data_rows[1:]
        return [
            (f"row {index + 1}", row)
            for index, row in enumerate(body_rows)
            if row.strip("|").strip()
        ]
    numbered = [line.strip() for line in lines if _NUMBERED_ROW_RE.match(line)]
    if len(numbered) >= 2:
        return [(f"row {index + 1}", line) for index, line in enumerate(numbered)]
    return []


def _is_table_separator(row: str) -> bool:
    cells = [cell.strip() for cell in row.strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells)

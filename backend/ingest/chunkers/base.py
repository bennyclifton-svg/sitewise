from dataclasses import dataclass

from ingest.types import IngestPlan


@dataclass(frozen=True, slots=True)
class TextChunk:
    chunk_index: int
    content: str
    page_or_section: str | None = None
    token_count: int | None = None
    chunk_metadata: dict | None = None


def chunk_not_implemented(plan: IngestPlan) -> list[TextChunk]:
    msg = (
        f"Chunker '{plan.chunker}' is not implemented yet "
        f"for {plan.entry.relative_path}"
    )
    raise NotImplementedError(msg)

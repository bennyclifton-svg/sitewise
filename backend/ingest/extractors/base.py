from dataclasses import dataclass, field

from ingest.drawing_parse import DrawingIdentity


@dataclass(frozen=True, slots=True)
class PageText:
    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    normalized_content: str
    page_count: int | None = None
    pages: list[PageText] = field(default_factory=list)
    drawing_identity: DrawingIdentity | None = None

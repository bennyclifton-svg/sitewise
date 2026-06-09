import html
import re
import uuid

import structlog

from app.assistant.outputs import Citation, GroundedAnswer
from app.retrieval.schemas import SourcePassage

logger = structlog.get_logger(__name__)


class GroundingError(Exception):
    """Raised when an assistant answer fails citation grounding checks."""


def _normalize_text(text: str) -> str:
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text.strip().lower())


def _passage_search_text(passage: SourcePassage) -> str:
    parts = [
        passage.content,
        passage.project,
        passage.filename,
        passage.relative_path,
        passage.page_or_section or "",
        passage.source_type or "",
        passage.document_class,
    ]
    if passage.document_metadata:
        for value in passage.document_metadata.values():
            if isinstance(value, str):
                parts.append(value)
    return _normalize_text(" ".join(parts))


def _strip_excerpt_ellipsis(excerpt: str) -> str:
    trimmed = excerpt.strip()
    trimmed = re.sub(r"\.{3,}$", "", trimmed)
    trimmed = re.sub(r"…$", "", trimmed)
    return trimmed.strip()


def excerpt_matches_passage(excerpt: str, passage: SourcePassage) -> bool:
    cleaned = _strip_excerpt_ellipsis(excerpt)
    normalized_excerpt = _normalize_text(cleaned)
    if not normalized_excerpt:
        return True

    searchable = _passage_search_text(passage)
    if normalized_excerpt in searchable:
        return True

    if len(normalized_excerpt) >= 24:
        prefix = normalized_excerpt[: min(120, len(normalized_excerpt))]
        if prefix in searchable:
            return True

    return False


def _excerpt_from_passage(passage: SourcePassage, hint: str | None = None) -> str:
    content = passage.content.strip()
    if hint:
        cleaned_hint = _strip_excerpt_ellipsis(hint)
        normalized_hint = _normalize_text(cleaned_hint)
        normalized_content = _normalize_text(content)
        if normalized_hint:
            index = normalized_content.find(normalized_hint[: min(80, len(normalized_hint))])
            if index >= 0:
                # Map back approximately — use raw content slice from proportional position
                start = max(0, int(index / max(len(normalized_content), 1) * len(content)) - 20)
                return content[start : start + 300].strip()
    return content[:300].strip()


def repair_citations(
    answer: GroundedAnswer,
    passages: dict[uuid.UUID, SourcePassage],
) -> GroundedAnswer:
    repaired: list[Citation] = []
    for citation in answer.citations:
        passage = passages.get(citation.chunk_id)
        if passage is None:
            repaired.append(citation)
            continue

        excerpt = citation.excerpt
        if not excerpt_matches_passage(excerpt, passage):
            excerpt = _excerpt_from_passage(passage, hint=excerpt)
            logger.info(
                "citation_excerpt_repaired",
                chunk_id=str(citation.chunk_id),
            )

        repaired.append(
            citation.model_copy(
                update={
                    "document_id": passage.document_id,
                    "excerpt": excerpt,
                    "filename": passage.filename,
                    "project": passage.project,
                    "phase": passage.phase,
                    "source_type": passage.source_type,
                    "page_or_section": passage.page_or_section,
                }
            )
        )

    return answer.model_copy(update={"citations": repaired})


class GroundingValidator:
    def __init__(self) -> None:
        self._passages: dict[uuid.UUID, SourcePassage] = {}

    @property
    def passages(self) -> dict[uuid.UUID, SourcePassage]:
        return dict(self._passages)

    def register(self, passages: list[SourcePassage]) -> None:
        for passage in passages:
            self._passages[passage.chunk_id] = passage

    def validate(self, answer: GroundedAnswer) -> GroundedAnswer:
        answer = repair_citations(answer, self._passages)

        if answer.workflow_deferred:
            return self._attach_cited_passages(answer)

        if not answer.evidence_sufficient:
            if answer.citations:
                self._validate_citations(answer.citations)
            return self._attach_cited_passages(answer)

        if not answer.citations:
            msg = "Answer claims sufficient evidence but includes no citations"
            raise GroundingError(msg)

        self._validate_citations(answer.citations)
        return self._attach_cited_passages(answer)

    def _validate_citations(self, citations: list[Citation]) -> None:
        for citation in citations:
            passage = self._passages.get(citation.chunk_id)
            if passage is None:
                msg = f"Citation chunk_id {citation.chunk_id} was not retrieved during this turn"
                raise GroundingError(msg)

            if citation.document_id != passage.document_id:
                msg = f"Citation document_id mismatch for chunk {citation.chunk_id}"
                raise GroundingError(msg)

            if not excerpt_matches_passage(citation.excerpt, passage):
                msg = f"Citation excerpt not found in retrieved passage for chunk {citation.chunk_id}"
                raise GroundingError(msg)

    def _attach_cited_passages(self, answer: GroundedAnswer) -> GroundedAnswer:
        cited = [
            self._passages[citation.chunk_id]
            for citation in answer.citations
            if citation.chunk_id in self._passages
        ]
        return answer.model_copy(update={"cited_passages": cited})

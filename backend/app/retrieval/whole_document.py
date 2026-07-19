import time

import structlog
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.source_document import SourceDocument
from app.retrieval.query_text import lexical_query_text
from app.retrieval.schemas import SourcePassage
from app.sitewise.markdown_sections import doctrine_core_content

logger = structlog.get_logger(__name__)

_DOCTRINE_BOOST = 10


def _query_terms(query: str) -> list[str]:
    lexical = lexical_query_text(query)
    return [term for term in lexical.lower().split() if term]


def _platform_scope_filter():
    scope_expr = SourceDocument.document_metadata["knowledge_scope"].astext
    return and_(
        SourceDocument.project_id.is_(None),
        scope_expr == "platform",
    )


def score_platform_document(
    *,
    relative_path: str,
    filename: str,
    content: str,
    source_type: str | None,
    terms: list[str],
) -> int:
    if not terms:
        return _DOCTRINE_BOOST if source_type == "doctrine" else 0
    haystack = f"{relative_path} {filename} {content}".lower()
    score = sum(1 for term in terms if term in haystack)
    if source_type == "doctrine":
        score += _DOCTRINE_BOOST
    return score


def _document_columns(*, content_chars: int | None = None):
    content = SourceDocument.normalized_content
    if content_chars is not None:
        content = func.left(SourceDocument.normalized_content, content_chars).label(
            "normalized_content"
        )
    return (
        SourceDocument.id,
        SourceDocument.filename,
        SourceDocument.relative_path,
        SourceDocument.project,
        SourceDocument.project_id,
        SourceDocument.phase,
        SourceDocument.source_type,
        SourceDocument.document_class,
        SourceDocument.document_metadata,
        content,
    )


def _searchable_text():
    return func.lower(
        SourceDocument.relative_path
        + " "
        + SourceDocument.filename
        + " "
        + func.coalesce(SourceDocument.normalized_content, "")
    )


def _term_match_filter(terms: list[str]):
    searchable = _searchable_text()
    return or_(*(searchable.contains(term) for term in terms))


def _row_to_passage(row, *, max_chars: int, terms: list[str]) -> SourcePassage:
    score = score_platform_document(
        relative_path=row.relative_path,
        filename=row.filename,
        content=row.normalized_content,
        source_type=row.source_type,
        terms=terms,
    )
    return SourcePassage(
        chunk_id=row.id,
        document_id=row.id,
        chunk_index=0,
        content=row.normalized_content,
        page_or_section=None,
        project=row.project,
        project_id=row.project_id,
        phase=row.phase,
        source_type=row.source_type,
        document_class=row.document_class,
        filename=row.filename,
        relative_path=row.relative_path,
        document_metadata=row.document_metadata,
        chunk_metadata={"whole_document": True},
        score=float(score),
    )


def doctrine_passage_content(full_text: str, *, max_chars: int) -> tuple[str, bool]:
    """Content served for the always-loaded doctrine passage.

    Assembles the doctrine core (preamble + cross-cutting rules) so every
    platform turn sees the disciplines rather than the accidental first
    max_chars of the file. Falls back to legacy truncation when the heading
    structure is not recognised. Returns (content, is_core).
    """
    core = doctrine_core_content(
        full_text, max_chars=settings.doctrine_core_content_chars
    )
    if core is None:
        return full_text[:max_chars], False
    return core, True


async def _load_doctrine_document(
    session: AsyncSession,
    *,
    max_chars: int,
    terms: list[str],
):
    stmt = (
        select(*_document_columns(content_chars=None))
        .where(_platform_scope_filter(), SourceDocument.source_type == "doctrine")
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return None
    passage = _row_to_passage(row, max_chars=max_chars, terms=terms)
    content, is_core = doctrine_passage_content(
        row.normalized_content or "", max_chars=max_chars
    )
    return passage.model_copy(
        update={
            "content": content,
            "chunk_metadata": {"whole_document": True, "doctrine_core": is_core},
        }
    )


async def _load_matching_seed_documents(
    session: AsyncSession,
    *,
    terms: list[str],
    limit: int,
    exclude_ids: set,
    max_chars: int,
) -> list[SourcePassage]:
    if limit <= 0:
        return []

    filters = [
        _platform_scope_filter(),
        SourceDocument.source_type == "reference",
    ]
    if terms:
        filters.append(_term_match_filter(terms))
    if exclude_ids:
        filters.append(SourceDocument.id.not_in(exclude_ids))

    stmt = (
        select(*_document_columns(content_chars=max_chars))
        .where(*filters)
        .order_by(SourceDocument.relative_path.asc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [
        _row_to_passage(row, max_chars=max_chars, terms=terms)
        for row in result.all()
    ]


async def load_platform_whole_documents(
    session: AsyncSession,
    query: str,
    *,
    limit: int | None = None,
    content_chars: int | None = None,
) -> list[SourcePassage]:
    total_start = time.perf_counter()
    doc_limit = limit or settings.whole_document_passage_limit
    max_chars = content_chars or settings.whole_document_content_chars
    terms = _query_terms(query)
    seed_limit = max(doc_limit - 1, 0)

    doctrine_passage = await _load_doctrine_document(
        session, max_chars=max_chars, terms=terms
    )
    exclude_ids = {doctrine_passage.document_id} if doctrine_passage else set()
    seed_passages = await _load_matching_seed_documents(
        session,
        terms=terms,
        limit=seed_limit,
        exclude_ids=exclude_ids,
        max_chars=max_chars,
    )

    passages: list[SourcePassage] = []
    if doctrine_passage is not None:
        passages.append(doctrine_passage)

    passages.extend(seed_passages)

    if len(passages) < doc_limit and terms:
        extra = await _load_matching_seed_documents(
            session,
            terms=[],
            limit=doc_limit - len(passages),
            exclude_ids=exclude_ids | {p.document_id for p in passages},
            max_chars=max_chars,
        )
        passages.extend(extra)

    passages.sort(
        key=lambda passage: (-passage.score, passage.relative_path),
    )
    passages = passages[:doc_limit]

    logger.info(
        "whole_document_load_complete",
        selected_count=len(passages),
        query_term_count=len(terms),
        elapsed_ms=int((time.perf_counter() - total_start) * 1000),
    )
    return passages


async def load_platform_documents_by_paths(
    session: AsyncSession,
    relative_paths: list[str],
    *,
    content_chars: int | None = None,
) -> tuple[list[SourcePassage], list[str]]:
    """Load platform documents by exact relative_path, preserving caller order."""
    if not relative_paths:
        return [], []

    max_chars = content_chars or settings.whole_document_content_chars
    stmt = (
        select(*_document_columns(content_chars=max_chars))
        .where(
            _platform_scope_filter(),
            SourceDocument.relative_path.in_(relative_paths),
        )
    )
    result = await session.execute(stmt)
    by_path = {
        row.relative_path: _row_to_passage(row, max_chars=max_chars, terms=[])
        for row in result.all()
    }

    passages: list[SourcePassage] = []
    missing: list[str] = []
    for path in relative_paths:
        passage = by_path.get(path)
        if passage is None:
            missing.append(path)
            continue
        passages.append(passage)

    logger.info(
        "whole_document_load_by_paths_complete",
        requested_count=len(relative_paths),
        loaded_count=len(passages),
        missing_count=len(missing),
    )
    return passages, missing

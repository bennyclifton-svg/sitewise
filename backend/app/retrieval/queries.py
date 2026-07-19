import uuid

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.document_chunk import DocumentChunk
from app.database.source_document import SourceDocument
from app.retrieval.query_text import lexical_query_text
from app.retrieval.schemas import ChunkSearchHit, RetrievalFilters


def apply_document_filters(
    stmt: Select,
    filters: RetrievalFilters | None,
) -> Select:
    if filters is None:
        return stmt

    if filters.active_project_id is not None:
        if filters.cross_project:
            authorized_ids = filters.authorized_project_ids or (filters.active_project_id,)
            scope_conditions = [SourceDocument.project_id.in_(authorized_ids)]
        else:
            scope_conditions = [SourceDocument.project_id == filters.active_project_id]
        if filters.include_platform_knowledge:
            scope_conditions.append(
                (SourceDocument.project_id.is_(None))
                & (SourceDocument.document_metadata["knowledge_scope"].astext == "platform")
            )
        stmt = stmt.where(or_(*scope_conditions))

    if filters.project_id is not None:
        stmt = stmt.where(SourceDocument.project_id == filters.project_id)
    if filters.platform_knowledge_only:
        stmt = stmt.where(
            SourceDocument.project_id.is_(None),
            SourceDocument.document_metadata["knowledge_scope"].astext == "platform",
        )
    if filters.phase is not None:
        stmt = stmt.where(SourceDocument.phase == filters.phase)
    if filters.source_type is not None:
        stmt = stmt.where(SourceDocument.source_type == filters.source_type)
    if filters.document_class is not None:
        stmt = stmt.where(SourceDocument.document_class == filters.document_class)
    if filters.procurement_stage is not None:
        stmt = stmt.where(
            SourceDocument.document_metadata["procurement_stage"].astext
            == filters.procurement_stage
        )
    if filters.tenderer_id is not None:
        stmt = stmt.where(
            SourceDocument.document_metadata["tenderer_id"].astext
            == filters.tenderer_id
        )
    return stmt


def _row_to_hit(row, *, raw_score: float | None) -> ChunkSearchHit:
    return ChunkSearchHit(
        chunk_id=row.id,
        document_id=row.document_id,
        chunk_index=row.chunk_index,
        content=row.content,
        page_or_section=row.page_or_section,
        chunk_metadata=row.chunk_metadata,
        project=row.project,
        project_id=row.project_id,
        phase=row.phase,
        source_type=row.source_type,
        document_class=row.document_class,
        filename=row.filename,
        relative_path=row.relative_path,
        document_metadata=row.document_metadata,
        raw_score=raw_score,
    )


async def semantic_search(
    session: AsyncSession,
    query_embedding: list[float],
    *,
    filters: RetrievalFilters | None = None,
    limit: int = 20,
) -> list[ChunkSearchHit]:
    distance = DocumentChunk.embedding.cosine_distance(query_embedding).label(
        "distance"
    )
    stmt = (
        select(
            DocumentChunk.id,
            DocumentChunk.document_id,
            DocumentChunk.chunk_index,
            DocumentChunk.page_or_section,
            DocumentChunk.content,
            DocumentChunk.chunk_metadata,
            SourceDocument.project,
            SourceDocument.project_id,
            SourceDocument.phase,
            SourceDocument.source_type,
            SourceDocument.document_class,
            SourceDocument.filename,
            SourceDocument.relative_path,
            SourceDocument.document_metadata,
            distance,
        )
        .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )
    stmt = apply_document_filters(stmt, filters)

    result = await session.execute(stmt)
    return [
        _row_to_hit(row, raw_score=1.0 - float(row.distance)) for row in result.all()
    ]


async def fulltext_search(
    session: AsyncSession,
    query_text: str,
    *,
    filters: RetrievalFilters | None = None,
    limit: int = 20,
) -> list[ChunkSearchHit]:
    normalized = query_text.strip()
    if not normalized:
        return []

    lexical_text = lexical_query_text(normalized)
    ts_query = func.plainto_tsquery("english", lexical_text)
    rank = func.ts_rank(DocumentChunk.search_vector, ts_query).label("rank")
    stmt = (
        select(
            DocumentChunk.id,
            DocumentChunk.document_id,
            DocumentChunk.chunk_index,
            DocumentChunk.page_or_section,
            DocumentChunk.content,
            DocumentChunk.chunk_metadata,
            SourceDocument.project,
            SourceDocument.project_id,
            SourceDocument.phase,
            SourceDocument.source_type,
            SourceDocument.document_class,
            SourceDocument.filename,
            SourceDocument.relative_path,
            SourceDocument.document_metadata,
            rank,
        )
        .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
        .where(DocumentChunk.search_vector.op("@@")(ts_query))
        .order_by(rank.desc())
        .limit(limit)
    )
    stmt = apply_document_filters(stmt, filters)

    result = await session.execute(stmt)
    return [_row_to_hit(row, raw_score=float(row.rank)) for row in result.all()]


async def fetch_neighbouring_chunks(
    session: AsyncSession,
    document_id: uuid.UUID,
    chunk_index: int,
    *,
    before: int = 1,
    after: int = 1,
) -> list[DocumentChunk]:
    if before < 1 and after < 1:
        return []

    min_index = max(0, chunk_index - before)
    max_index = chunk_index + after
    stmt = (
        select(DocumentChunk)
        .where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.chunk_index >= min_index,
            DocumentChunk.chunk_index <= max_index,
            DocumentChunk.chunk_index != chunk_index,
        )
        .order_by(DocumentChunk.chunk_index.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def fetch_neighbouring_chunks_batch(
    session: AsyncSession,
    hits: list[ChunkSearchHit],
    *,
    filters: RetrievalFilters | None = None,
    before: int = 1,
    after: int = 1,
) -> dict[uuid.UUID, list[DocumentChunk]]:
    if not hits or (before < 1 and after < 1):
        return {hit.chunk_id: [] for hit in hits}

    ranges = [
        and_(
            DocumentChunk.document_id == hit.document_id,
            DocumentChunk.chunk_index >= max(0, hit.chunk_index - before),
            DocumentChunk.chunk_index <= hit.chunk_index + after,
        )
        for hit in hits
    ]
    stmt = (
        select(DocumentChunk)
        .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
        .where(or_(*ranges))
        .order_by(DocumentChunk.document_id.asc(), DocumentChunk.chunk_index.asc())
    )
    rows = list(
        (await session.execute(apply_document_filters(stmt, filters))).scalars().all()
    )
    return {
        hit.chunk_id: [
            row
            for row in rows
            if row.document_id == hit.document_id
            and max(0, hit.chunk_index - before) <= row.chunk_index <= hit.chunk_index + after
            and row.chunk_index != hit.chunk_index
        ]
        for hit in hits
    }


def hits_by_id(hits: list[ChunkSearchHit]) -> dict[uuid.UUID, ChunkSearchHit]:
    return {hit.chunk_id: hit for hit in hits}


async def fetch_chunk_by_id(
    session: AsyncSession,
    chunk_id: uuid.UUID,
    *,
    filters: RetrievalFilters | None = None,
) -> ChunkSearchHit | None:
    stmt = (
        select(
            DocumentChunk.id,
            DocumentChunk.document_id,
            DocumentChunk.chunk_index,
            DocumentChunk.page_or_section,
            DocumentChunk.content,
            DocumentChunk.chunk_metadata,
            SourceDocument.project,
            SourceDocument.project_id,
            SourceDocument.phase,
            SourceDocument.source_type,
            SourceDocument.document_class,
            SourceDocument.filename,
            SourceDocument.relative_path,
            SourceDocument.document_metadata,
        )
        .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
        .where(DocumentChunk.id == chunk_id)
    )
    stmt = apply_document_filters(stmt, filters)
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return None
    return _row_to_hit(row, raw_score=None)

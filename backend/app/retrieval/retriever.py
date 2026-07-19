import time
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.retrieval.embedding import embed_query
from app.retrieval import fusion, queries
from app.retrieval.schemas import NeighbourChunk, RetrievalFilters, SourcePassage

logger = structlog.get_logger(__name__)


class DocumentRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def retrieve(
        self,
        query: str,
        *,
        filters: RetrievalFilters | None = None,
        limit: int | None = None,
        include_neighbours: bool = True,
    ) -> list[SourcePassage]:
        normalized = query.strip()
        if not normalized:
            return []

        total_start = time.perf_counter()
        embedding_start = time.perf_counter()
        query_embedding = await embed_query(normalized)
        embedding_ms = int((time.perf_counter() - embedding_start) * 1000)
        if query_embedding is None:
            return []

        semantic_start = time.perf_counter()
        semantic_hits = await queries.semantic_search(
            self._session,
            query_embedding,
            filters=filters,
            limit=settings.retrieval_semantic_limit,
        )
        semantic_ms = int((time.perf_counter() - semantic_start) * 1000)

        lexical_start = time.perf_counter()
        lexical_hits = await queries.fulltext_search(
            self._session,
            normalized,
            filters=filters,
            limit=settings.retrieval_fts_limit,
        )
        lexical_ms = int((time.perf_counter() - lexical_start) * 1000)

        fusion_start = time.perf_counter()
        fused = fusion.reciprocal_rank_fusion(
            [
                [hit.chunk_id for hit in semantic_hits],
                [hit.chunk_id for hit in lexical_hits],
            ],
            k=settings.retrieval_rrf_k,
        )
        fusion_ms = int((time.perf_counter() - fusion_start) * 1000)

        final_limit = limit or settings.retrieval_final_limit
        top_ids = [chunk_id for chunk_id, _score in fused[:final_limit]]
        if not top_ids:
            return []

        hit_lookup = queries.hits_by_id(semantic_hits + lexical_hits)
        passages: list[SourcePassage] = []
        neighbours_ms = 0
        for chunk_id, score in fused[:final_limit]:
            hit = hit_lookup.get(chunk_id)
            if hit is None:
                continue

            neighbours: list[NeighbourChunk] = []
            if include_neighbours:
                neighbours_start = time.perf_counter()
                neighbour_rows = await queries.fetch_neighbouring_chunks(
                    self._session,
                    hit.document_id,
                    hit.chunk_index,
                    before=settings.retrieval_neighbour_before,
                    after=settings.retrieval_neighbour_after,
                )
                neighbours_ms += int((time.perf_counter() - neighbours_start) * 1000)
                neighbours = [
                    NeighbourChunk(
                        chunk_id=row.id,
                        chunk_index=row.chunk_index,
                        content=row.content,
                        page_or_section=row.page_or_section,
                    )
                    for row in neighbour_rows
                ]

            passages.append(
                SourcePassage(
                    chunk_id=hit.chunk_id,
                    document_id=hit.document_id,
                    chunk_index=hit.chunk_index,
                    content=hit.content,
                    page_or_section=hit.page_or_section,
                    project=hit.project,
                    project_id=hit.project_id,
                    phase=hit.phase,
                    source_type=hit.source_type,
                    document_class=hit.document_class,
                    filename=hit.filename,
                    relative_path=hit.relative_path,
                    document_metadata=hit.document_metadata,
                    chunk_metadata=hit.chunk_metadata,
                    score=score,
                    neighbours=neighbours,
                )
            )

        logger.info(
            "retrieval_complete",
            query_length=len(normalized),
            semantic_count=len(semantic_hits),
            lexical_count=len(lexical_hits),
            result_count=len(passages),
            filters=filters.model_dump(exclude_none=True) if filters else {},
            timings_ms={
                "embedding": embedding_ms,
                "semantic": semantic_ms,
                "lexical": lexical_ms,
                "fusion": fusion_ms,
                "neighbours": neighbours_ms,
                "total": int((time.perf_counter() - total_start) * 1000),
            },
        )
        return passages

    async def read_chunk(
        self, chunk_id: uuid.UUID, *, filters: RetrievalFilters | None = None
    ) -> SourcePassage | None:
        total_start = time.perf_counter()
        hit = await queries.fetch_chunk_by_id(self._session, chunk_id, filters=filters)
        if hit is None:
            return None

        neighbours_start = time.perf_counter()
        neighbours = await queries.fetch_neighbouring_chunks(
            self._session,
            hit.document_id,
            hit.chunk_index,
            before=settings.retrieval_neighbour_before,
            after=settings.retrieval_neighbour_after,
        )
        logger.info(
            "chunk_read_complete",
            chunk_id=str(chunk_id),
            neighbour_count=len(neighbours),
            timings_ms={
                "neighbours": int((time.perf_counter() - neighbours_start) * 1000),
                "total": int((time.perf_counter() - total_start) * 1000),
            },
        )
        return SourcePassage(
            chunk_id=hit.chunk_id,
            document_id=hit.document_id,
            chunk_index=hit.chunk_index,
            content=hit.content,
            page_or_section=hit.page_or_section,
            project=hit.project,
            project_id=hit.project_id,
            phase=hit.phase,
            source_type=hit.source_type,
            document_class=hit.document_class,
            filename=hit.filename,
            relative_path=hit.relative_path,
            document_metadata=hit.document_metadata,
            chunk_metadata=hit.chunk_metadata,
            score=1.0,
            neighbours=[
                NeighbourChunk(
                    chunk_id=n.id,
                    chunk_index=n.chunk_index,
                    content=n.content,
                    page_or_section=n.page_or_section,
                )
                for n in neighbours
            ],
        )

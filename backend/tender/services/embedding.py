from __future__ import annotations

import argparse
import asyncio
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from tender.models import TaxonomySynonym, TenderJob, TenderLineItem, TenderQuote
from tender.seeds.load import normalize_phrase
from tender.services import jobs
from tender.services.telemetry import note_openai_response

MAX_EMBED_BATCH_SIZE = 256


class EmbeddingClient(Protocol):
    async def embed_texts(self, texts: list[str], *, model: str) -> list[list[float]]:
        ...


@dataclass
class EmbeddingTarget:
    id: str | uuid.UUID
    text: str
    embedding: list[float] | None = None


class OpenAIEmbeddingClient:
    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)

    async def embed_texts(self, texts: list[str], *, model: str) -> list[list[float]]:
        response = await self.client.embeddings.create(
            model=model,
            input=texts,
            dimensions=settings.tender_embedding_dimensions,
        )
        note_openai_response(response)
        return [list(item.embedding) for item in response.data]


def worker_handlers() -> Mapping[str, Callable[[AsyncSession, TenderJob], object]]:
    return {"embed_items": embed_items}


async def embed_items(
    session: AsyncSession,
    job: TenderJob,
    *,
    embedder: EmbeddingClient | None = None,
) -> None:
    await embed_line_items(session, quote_id=job.quote_id, embedder=embedder)
    if job.quote_id is None:
        return
    quote = await session.get(TenderQuote, job.quote_id)
    if quote is not None:
        quote.stage = "map_items"
    await jobs.enqueue(
        session,
        kind="map_items",
        comparison_id=job.comparison_id,
        quote_id=job.quote_id,
        payload={"reason": "embedding_complete"},
    )


async def embed_line_items(
    session: AsyncSession,
    *,
    quote_id: uuid.UUID | None = None,
    embedder: EmbeddingClient | None = None,
    batch_size: int = MAX_EMBED_BATCH_SIZE,
) -> int:
    embedder = embedder or OpenAIEmbeddingClient()
    total = 0
    while True:
        statement = select(TenderLineItem).where(TenderLineItem.embedding.is_(None))
        if quote_id is not None:
            statement = statement.where(TenderLineItem.quote_id == quote_id)
        result = await session.execute(statement.order_by(TenderLineItem.created_at).limit(batch_size))
        items = list(result.scalars())
        if not items:
            return total

        by_id = {item.id: item for item in items}
        total += await embed_targets(
            [
                EmbeddingTarget(
                    id=item.id,
                    text=item.description_raw,
                    embedding=item.embedding,
                )
                for item in items
            ],
            embedder=embedder,
            write_embedding=lambda item_id, vector: setattr(by_id[item_id], "embedding", vector),
            model=settings.tender_embed_model,
            dimensions=settings.tender_embedding_dimensions,
            batch_size=batch_size,
        )
        await session.flush()


async def embed_taxonomy_synonyms(
    session: AsyncSession,
    *,
    embedder: EmbeddingClient | None = None,
    batch_size: int = MAX_EMBED_BATCH_SIZE,
) -> int:
    embedder = embedder or OpenAIEmbeddingClient()
    total = 0
    while True:
        result = await session.execute(
            select(TaxonomySynonym)
            .where(TaxonomySynonym.embedding.is_(None))
            .order_by(TaxonomySynonym.created_at)
            .limit(batch_size)
        )
        synonyms = list(result.scalars())
        if not synonyms:
            return total

        by_id = {synonym.id: synonym for synonym in synonyms}
        total += await embed_targets(
            [
                EmbeddingTarget(
                    id=synonym.id,
                    text=synonym.phrase_norm,
                    embedding=synonym.embedding,
                )
                for synonym in synonyms
            ],
            embedder=embedder,
            write_embedding=lambda synonym_id, vector: setattr(
                by_id[synonym_id], "embedding", vector
            ),
            model=settings.tender_embed_model,
            dimensions=settings.tender_embedding_dimensions,
            batch_size=batch_size,
        )
        await session.flush()


async def embed_targets(
    targets: Sequence[EmbeddingTarget],
    *,
    embedder: EmbeddingClient,
    write_embedding: Callable[[str | uuid.UUID, list[float]], None],
    model: str,
    dimensions: int,
    batch_size: int = MAX_EMBED_BATCH_SIZE,
) -> int:
    missing = [target for target in targets if target.embedding is None]
    total = 0
    for start in range(0, len(missing), min(batch_size, MAX_EMBED_BATCH_SIZE)):
        batch = missing[start : start + min(batch_size, MAX_EMBED_BATCH_SIZE)]
        texts = [normalize_phrase(target.text) for target in batch]
        vectors = await embedder.embed_texts(texts, model=model)
        if len(vectors) != len(batch):
            raise ValueError("embedding response count did not match request count")
        for target, vector in zip(batch, vectors, strict=True):
            assert_embedding_dimensions(vector, dimensions)
            write_embedding(target.id, vector)
            total += 1
    return total


def assert_embedding_dimensions(vector: Sequence[float], dimensions: int) -> None:
    if len(vector) != dimensions:
        raise ValueError(f"embedding must have {dimensions} dimensions")


async def _run_embed_synonyms() -> int:
    from app.database.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        count = await embed_taxonomy_synonyms(session)
        await session.commit()
    return count


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill TCM synonym embeddings.")
    parser.parse_args(argv)
    count = asyncio.run(_run_embed_synonyms())
    print(f"Embedded {count} taxonomy synonym rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from functools import lru_cache

import structlog
from openai import AsyncOpenAI

from app.config import settings

logger = structlog.get_logger(__name__)


@lru_cache
def get_embedding_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def embed_query(text: str) -> list[float] | None:
    normalized = text.strip()
    if not normalized:
        return None

    response = await get_embedding_client().embeddings.create(
        model=settings.openai_embedding_model,
        input=[normalized],
        dimensions=settings.openai_embedding_dimensions,
    )
    if not response.data:
        return None

    vector = response.data[0].embedding
    if len(vector) != settings.openai_embedding_dimensions:
        msg = (
            f"Expected {settings.openai_embedding_dimensions} dimensions, "
            f"got {len(vector)}"
        )
        raise ValueError(msg)

    logger.debug("query_embedding_complete", query_length=len(normalized))
    return vector

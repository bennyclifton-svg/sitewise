import structlog
from openai import OpenAI

from app.config import settings

logger = structlog.get_logger(__name__)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    client = OpenAI(api_key=settings.openai_api_key)
    embeddings: list[list[float]] = []
    batch_size = settings.ingest_embedding_batch_size

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=batch,
            dimensions=settings.openai_embedding_dimensions,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        batch_embeddings = [item.embedding for item in ordered]
        for vector in batch_embeddings:
            if len(vector) != settings.openai_embedding_dimensions:
                msg = (
                    f"Expected {settings.openai_embedding_dimensions} dimensions, "
                    f"got {len(vector)}"
                )
                raise ValueError(msg)
        embeddings.extend(batch_embeddings)
        logger.debug("embed_batch_complete", count=len(batch))

    return embeddings

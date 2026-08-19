from collections.abc import Sequence

import structlog
from openai import OpenAI

from app.config import settings
from ingest.chunkers.prose import count_tokens

logger = structlog.get_logger(__name__)

EMBED_MAX_TOKENS = 8191


class EmbedInputTooLarge(ValueError):
    def __init__(self, relative_path: str, token_count: int) -> None:
        self.relative_path = relative_path
        self.token_count = token_count
        super().__init__(
            f"embedding input too large for {relative_path}: {token_count} tokens"
        )


def embed_texts(
    texts: list[str],
    *,
    relative_paths: Sequence[str] | None = None,
) -> list[list[float]]:
    if not texts:
        return []

    paths = list(relative_paths or [])
    for index, text in enumerate(texts):
        token_count = count_tokens(text)
        if token_count > EMBED_MAX_TOKENS:
            path = paths[index] if index < len(paths) else f"chunk[{index}]"
            logger.error(
                "embed_input_too_large",
                relative_path=path,
                token_count=token_count,
            )
            raise EmbedInputTooLarge(path, token_count)

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

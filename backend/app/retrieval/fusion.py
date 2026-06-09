import uuid
from collections import defaultdict


def reciprocal_rank_fusion(
    ranked_lists: list[list[uuid.UUID]],
    *,
    k: int = 60,
) -> list[tuple[uuid.UUID, float]]:
    """Fuse multiple ranked chunk-id lists with Reciprocal Rank Fusion."""
    if not ranked_lists:
        return []

    scores: dict[uuid.UUID, float] = defaultdict(float)
    for ranked_list in ranked_lists:
        for rank, chunk_id in enumerate(ranked_list, start=1):
            scores[chunk_id] += 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda item: item[1], reverse=True)

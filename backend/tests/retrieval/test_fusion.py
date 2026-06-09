import uuid

from app.retrieval.fusion import reciprocal_rank_fusion


def test_rrf_boosts_chunks_in_both_lists() -> None:
    shared = uuid.uuid4()
    only_semantic = uuid.uuid4()
    only_lexical = uuid.uuid4()

    fused = reciprocal_rank_fusion(
        [
            [shared, only_semantic],
            [shared, only_lexical],
        ],
        k=60,
    )

    assert fused[0][0] == shared
    assert fused[0][1] > fused[1][1]
    assert fused[0][1] > fused[2][1]


def test_rrf_respects_rank_within_list() -> None:
    first = uuid.uuid4()
    second = uuid.uuid4()

    fused = reciprocal_rank_fusion([[first, second]], k=60)

    assert fused[0][0] == first
    assert fused[1][0] == second
    assert fused[0][1] > fused[1][1]


def test_rrf_empty_input() -> None:
    assert reciprocal_rank_fusion([]) == []


def test_rrf_accumulates_duplicate_ranks_in_same_list() -> None:
    chunk_id = uuid.uuid4()
    fused = reciprocal_rank_fusion([[chunk_id, chunk_id]], k=60)

    assert len(fused) == 1
    assert fused[0][0] == chunk_id
    assert fused[0][1] == (1.0 / (60 + 1)) + (1.0 / (60 + 2))

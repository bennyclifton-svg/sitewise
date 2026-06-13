from __future__ import annotations

from tender.services import embedding
from tests.conftest import run_async


def test_embed_targets_normalizes_text_and_skips_existing_vectors() -> None:
    targets = [
        embedding.EmbeddingTarget(id="item-1", text="  Retaining   WALLS  "),
        embedding.EmbeddingTarget(id="item-2", text="Site costs", embedding=[0.1] * 3),
    ]
    embedder = FakeEmbedder(dimensions=3)
    written: dict[str, list[float]] = {}

    async def _run() -> None:
        first = await embedding.embed_targets(
            targets,
            embedder=embedder,
            write_embedding=lambda item_id, vector: written.__setitem__(item_id, vector),
            model="embed-test",
            dimensions=3,
        )
        targets[0].embedding = written["item-1"]
        second = await embedding.embed_targets(
            targets,
            embedder=embedder,
            write_embedding=lambda item_id, vector: written.__setitem__(item_id, vector),
            model="embed-test",
            dimensions=3,
        )
        assert first == 1
        assert second == 0

    run_async(_run())

    assert embedder.calls == [(["retaining walls"], "embed-test")]
    assert written == {"item-1": [1.0, 0.0, 0.0]}


def test_embed_targets_batches_at_256() -> None:
    targets = [embedding.EmbeddingTarget(id=f"item-{index}", text=f"Item {index}") for index in range(257)]
    embedder = FakeEmbedder(dimensions=3)

    async def _run() -> None:
        embedded = await embedding.embed_targets(
            targets,
            embedder=embedder,
            write_embedding=lambda item_id, vector: None,
            model="embed-test",
            dimensions=3,
        )
        assert embedded == 257

    run_async(_run())

    assert [len(texts) for texts, _model in embedder.calls] == [256, 1]


def test_embed_targets_rejects_wrong_dimension() -> None:
    targets = [embedding.EmbeddingTarget(id="item-1", text="Kitchen joinery")]
    embedder = FakeEmbedder(dimensions=2)

    async def _run() -> None:
        try:
            await embedding.embed_targets(
                targets,
                embedder=embedder,
                write_embedding=lambda item_id, vector: None,
                model="embed-test",
                dimensions=3,
            )
        except ValueError as exc:
            assert "3 dimensions" in str(exc)
            return
        raise AssertionError("wrong-dimension embedding was accepted")

    run_async(_run())


def test_worker_registers_embed_items_handler() -> None:
    assert "embed_items" in embedding.worker_handlers()


class FakeEmbedder:
    def __init__(self, *, dimensions: int) -> None:
        self.dimensions = dimensions
        self.calls: list[tuple[list[str], str]] = []

    async def embed_texts(self, texts: list[str], *, model: str) -> list[list[float]]:
        self.calls.append((texts, model))
        return [[1.0] + [0.0] * (self.dimensions - 1) for _text in texts]

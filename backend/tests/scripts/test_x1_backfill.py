import uuid
from types import SimpleNamespace

from scripts import x1_backfill as backfill


class _Session:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class _Factory:
    def __call__(self) -> _Session:
        return _Session()


def test_backfill_twice_produces_identical_chunk_counts(monkeypatch) -> None:
    doc = SimpleNamespace(
        id=uuid.uuid4(),
        normalized_content=("cost plan line item total " * 20),
        ingest_mode="register_only",
        document_class="report",
        filename="Cost Plan.pdf",
        relative_path="projects/demo/Cost Plan.pdf",
        project="demo",
        phase="delivery",
        source_type="project_evidence",
        project_id=uuid.uuid4(),
    )
    chunks: dict[uuid.UUID, list] = {doc.id: []}

    def load_candidates(session, *, limit=None):
        del session, limit
        return [doc]

    def delete_document_chunks(session, doc_id):
        del session
        chunks[doc_id] = []

    def upsert_chunks(session, plan, doc_id, new_chunks, embeddings):
        del session, plan, embeddings
        chunks.setdefault(doc_id, []).extend(new_chunks)

    def embed_fn(texts: list[str]) -> list[list[float]]:
        return [[0.0] * 8 for _ in texts]

    monkeypatch.setattr(backfill, "load_candidates", load_candidates)
    monkeypatch.setattr(backfill, "delete_document_chunks", delete_document_chunks)
    monkeypatch.setattr(backfill, "upsert_chunks", upsert_chunks)

    factory = _Factory()
    backfill.run(
        apply=True,
        session_factory=factory,
        embed_fn=embed_fn,
        capture_rollback_log=False,
    )
    n = len(chunks[doc.id])
    assert n > 0

    backfill.run(
        apply=True,
        session_factory=factory,
        embed_fn=embed_fn,
        capture_rollback_log=False,
    )
    assert len(chunks[doc.id]) == n
    assert doc.ingest_mode == "full_text"

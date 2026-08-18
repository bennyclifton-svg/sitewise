"""User classification override (X1 Stage 5). Fast unit tests; no live database."""

from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from ingest.classify import classify_entry
from ingest.types import Classification, ManifestEntry
from tests.conftest import run_async

from app.database.source_document import SourceDocument
from app.projects.classification_override import (
    DocumentClassificationNotFound,
    classification_from_override,
    lookup_override,
    set_document_classification,
)

PROJECT_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PROJECT_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DOC_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
ACTOR_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
CONTENT_HASH = "a" * 64


def _entry(filename: str = "Heritage Impact Statement.pdf") -> ManifestEntry:
    return ManifestEntry(
        absolute_path=Path(filename),
        relative_path=f"04-projects/demo/_inbox/{filename}",
        project="demo",
        filename=filename,
        extension=".pdf",
        size_bytes=100,
    )


def _document(**overrides: object) -> SourceDocument:
    values = {
        "id": DOC_ID,
        "project_id": PROJECT_A,
        "project": "demo",
        "phase": "delivery",
        "document_class": "report",
        "ingest_mode": "full_text",
        "document_metadata": {
            "basis": "filename",
            "confidence": "0.85",
            "subject": "heritage",
        },
        "content_hash": CONTENT_HASH,
        "source_type": "project_evidence",
        "filename": "Heritage Impact Statement.pdf",
        "relative_path": "04-projects/demo/_inbox/Heritage Impact Statement.pdf",
        "normalized_content": "x" * 200,
    }
    values.update(overrides)
    return SourceDocument(**values)


class _ExecuteResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _Session:
    def __init__(
        self,
        *,
        document: SourceDocument | None = None,
        override: object = None,
        project: object = None,
    ) -> None:
        self.document = document
        self.override = override
        self.project = project
        self.added: list[object] = []

    async def get(self, model: type, ident: uuid.UUID) -> object | None:
        name = getattr(model, "__name__", "")
        if name == "SourceDocument" and self.document is not None:
            return self.document if ident == self.document.id else None
        if name == "Project" and self.project is not None:
            project_id = getattr(self.project, "id", None)
            return self.project if ident == project_id else None
        return None

    async def execute(self, _statement: object) -> _ExecuteResult:
        return _ExecuteResult(self.override)

    def add(self, obj: object) -> None:
        self.added.append(obj)
        self.override = obj

    async def flush(self) -> None:
        return None


def test_classify_entry_stage_a_override_outranks_filename() -> None:
    override = Classification(
        document_class="certificate",
        document_subject="planning",
        ingest_mode="full_text",
        document_metadata={"basis": "user", "confidence": "1.00", "subject": "planning"},
        confidence=1.0,
        basis="user",
    )
    classification = classify_entry(_entry(), override=override)
    assert classification.document_class == "certificate"
    assert classification.document_subject == "planning"
    assert classification.basis == "user"
    assert classification.confidence == 1.0


def test_filename_without_override_still_classifies_heritage_statement() -> None:
    classification = classify_entry(_entry())
    assert classification.document_class == "report"
    assert classification.basis != "user"


def test_override_survives_reingest() -> None:
    """Re-classify the identical file; Stage A still returns the user correction."""
    row = SimpleNamespace(
        document_class="certificate",
        document_subject="planning",
    )
    override = classification_from_override(row)
    classification = classify_entry(_entry(), override=override)
    assert classification.document_class == "certificate"
    assert classification.document_metadata["basis"] == "user"
    assert classification.document_metadata["confidence"] == "1.0"
    assert classification.basis == "user"
    assert classification.confidence == 1.0


def test_override_survives_file_move() -> None:
    stored = SimpleNamespace(
        project_id=PROJECT_A,
        content_hash=CONTENT_HASH,
        relative_path="04-projects/demo/_inbox/Heritage Impact Statement.pdf",
        key_basis="content_hash",
        document_class="certificate",
        document_subject="planning",
    )
    session = _Session(override=stored)

    async def _run() -> None:
        found = await lookup_override(
            session,
            project_id=PROJECT_A,
            content_hash=CONTENT_HASH,
            relative_path="04-projects/demo/05-statutory/Heritage Impact Statement.pdf",
        )
        assert found is stored

    run_async(_run())


def test_path_keyed_override_does_not_survive_move() -> None:
    """Known limitation: key_basis=relative_path breaks when the file is moved."""
    session = _Session(override=None)

    async def _run() -> None:
        found = await lookup_override(
            session,
            project_id=PROJECT_A,
            content_hash=None,
            relative_path="04-projects/demo/05-statutory/moved.pdf",
        )
        assert found is None

    run_async(_run())


def test_null_content_hash_uses_relative_path_key() -> None:
    document = _document(content_hash=None)
    session = _Session(document=document, project=SimpleNamespace(id=PROJECT_A))

    async def _run() -> None:
        with (
            patch(
                "app.projects.classification_override.publish_project_event",
                new=AsyncMock(),
            ),
            patch(
                "app.projects.classification_override.upsert_consultant_fact_from_document",
            ),
        ):
            updated = await set_document_classification(
                session,
                project_id=PROJECT_A,
                document_id=DOC_ID,
                document_class="certificate",
                document_subject="planning",
                actor_id=ACTOR_ID,
                reason="planning certificate",
            )

        assert updated.document_class == "certificate"
        assert len(session.added) == 1
        override = session.added[0]
        assert override.key_basis == "relative_path"
        assert override.relative_path == document.relative_path
        assert override.content_hash is None

    run_async(_run())


def test_set_document_classification_tenant_guard() -> None:
    document = _document(project_id=PROJECT_A)
    session = _Session(document=document)

    async def _run() -> None:
        try:
            await set_document_classification(
                session,
                project_id=PROJECT_B,
                document_id=DOC_ID,
                document_class="certificate",
                document_subject=None,
                actor_id=ACTOR_ID,
            )
        except DocumentClassificationNotFound:
            return
        raise AssertionError("expected DocumentClassificationNotFound")

    run_async(_run())


def test_set_document_classification_applies_user_basis() -> None:
    document = _document()
    session = _Session(document=document, project=SimpleNamespace(id=PROJECT_A))

    async def _run() -> None:
        with (
            patch(
                "app.projects.classification_override.publish_project_event",
                new=AsyncMock(),
            ) as publish,
            patch(
                "app.projects.classification_override.upsert_consultant_fact_from_document",
            ),
        ):
            updated = await set_document_classification(
                session,
                project_id=PROJECT_A,
                document_id=DOC_ID,
                document_class="certificate",
                document_subject="planning",
                actor_id=ACTOR_ID,
            )

        assert updated.document_class == "certificate"
        assert updated.document_metadata["basis"] == "user"
        assert updated.document_metadata["confidence"] == "1.0"
        assert updated.document_metadata["subject"] == "planning"
        assert len(session.added) == 1
        override = session.added[0]
        assert override.key_basis == "content_hash"
        assert override.content_hash == CONTENT_HASH
        publish.assert_awaited()

    run_async(_run())

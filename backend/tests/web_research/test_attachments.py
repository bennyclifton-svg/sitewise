from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.web_research.attachments import (
    find_official_attachment,
    official_relative_path,
    persist_official_attachment,
    web_source_from_attachment,
)
from app.web_research.service import WebSource
from tests.conftest import run_async

PROJECT_ID = uuid.uuid4()
_URL = "https://legislation.nsw.gov.au/view/whole/html/inforce/current/act-1979-203"


def _source(**overrides) -> WebSource:
    values = dict(
        url=_URL,
        title="Environmental Planning and Assessment Act 1979",
        publisher="NSW Government",
        jurisdiction="NSW",
        authority_class="official_legislation",
        source_type="web_legislation",
        version_status="current",
        effective_date="1 July 2026",
        section="4.15",
        excerpt="A consent authority is to take into consideration the relevant matters.",
        content_hash="a" * 64,
        retrieved_at="2026-08-16T00:00:00+00:00",
    )
    values.update(overrides)
    return WebSource(**values)


class _Result:
    def __init__(self, value) -> None:
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Session:
    def __init__(self, existing=None) -> None:
        self.existing = existing
        self.added: list[object] = []

    async def execute(self, _stmt):
        return _Result(self.existing)

    def add(self, obj) -> None:
        self.added.append(obj)
        self.existing = obj

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()


def test_official_relative_path_uses_instrument_id() -> None:
    assert official_relative_path(_URL) == "official/act-1979-203"


def test_official_relative_path_slugs_a_council_pdf() -> None:
    assert official_relative_path(
        "https://www.innerwest.nsw.gov.au/ArticleDocuments/123/DCP-2022.pdf"
    ) == "official/dcp-2022.pdf"


def test_persist_official_attachment_writes_reference_not_evidence() -> None:
    session = _Session()
    source = _source()

    document = run_async(
        persist_official_attachment(
            session,
            project_id=PROJECT_ID,
            project_slug="newtown-extension",
            source=source,
            text=source.excerpt,
        )
    )

    assert document.source_type == "reference"
    assert document.document_class == "statutory_instrument"
    assert document.document_metadata["knowledge_scope"] == "official"
    assert document.document_metadata["official_url"] == _URL
    assert document.relative_path == "official/act-1979-203"
    assert document.normalized_content == source.excerpt
    assert document.project_id == PROJECT_ID
    assert session.added == [document]


def test_official_attachment_writes_no_document_type() -> None:
    session = _Session()
    source = _source()

    document = run_async(
        persist_official_attachment(
            session,
            project_id=PROJECT_ID,
            project_slug="newtown-extension",
            source=source,
            text=source.excerpt,
        )
    )

    assert getattr(document, "document_type", None) not in {
        "planning_instrument",
        "reference_guide",
        "doctrine",
        "tender_submission",
    }


def test_persist_official_attachment_replaces_same_url_and_keeps_previous_hash() -> None:
    existing = SimpleNamespace(
        id=uuid.uuid4(),
        content_hash="b" * 64,
        document_metadata={"knowledge_scope": "official"},
        normalized_content="old",
        filename="old",
        source_type="project_evidence",
        document_class="unknown",
        relative_path="official/act-1979-203",
        project_id=PROJECT_ID,
        project="newtown-extension",
        phase="reference",
        document_type="planning_instrument",
        ingest_mode="full_text",
    )
    session = _Session(existing=existing)
    source = _source(content_hash="c" * 64)

    document = run_async(
        persist_official_attachment(
            session,
            project_id=PROJECT_ID,
            project_slug="newtown-extension",
            source=source,
            text="new text",
        )
    )

    assert document is existing
    assert document.content_hash == "c" * 64
    assert document.document_metadata["previous_content_hash"] == "b" * 64
    assert document.source_type == "reference"
    assert document.normalized_content == "new text"
    assert session.added == []


def test_find_official_attachment_returns_fresh_snapshot() -> None:
    retrieved = datetime.now(UTC).isoformat()
    existing = SimpleNamespace(
        document_metadata={"retrieved_at": retrieved, "knowledge_scope": "official"},
        content_hash="a" * 64,
        normalized_content="stored text",
        filename="Environmental Planning and Assessment Act 1979",
    )
    session = _Session(existing=existing)

    found = run_async(
        find_official_attachment(session, project_id=PROJECT_ID, url=_URL)
    )

    assert found is existing


def test_find_official_attachment_ignores_stale_snapshot() -> None:
    stale = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    existing = SimpleNamespace(
        document_metadata={"retrieved_at": stale, "knowledge_scope": "official"},
    )
    session = _Session(existing=existing)

    found = run_async(
        find_official_attachment(session, project_id=PROJECT_ID, url=_URL)
    )

    assert found is None


def test_web_source_from_attachment_rehydrates_provenance() -> None:
    document = SimpleNamespace(
        filename="Environmental Planning and Assessment Act 1979",
        normalized_content="4.15 Evaluation\nA consent authority is to take into consideration.",
        content_hash="a" * 64,
        document_metadata={
            "official_url": _URL,
            "publisher": "NSW Government",
            "jurisdiction": "NSW",
            "authority_class": "official_legislation",
            "source_type": "web_legislation",
            "version_status": "current",
            "effective_date": "1 July 2026",
            "retrieved_at": "2026-08-16T00:00:00+00:00",
        },
    )

    source = web_source_from_attachment(document, section_hint="4.15")

    assert source.url == _URL
    assert source.title == "Environmental Planning and Assessment Act 1979"
    assert source.authority_class == "official_legislation"
    assert "4.15 Evaluation" in source.excerpt
    assert source.content_hash == "a" * 64

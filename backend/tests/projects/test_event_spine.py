"""Project-verb spine (X1 Stage 13). Fast unit tests; no live database."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.dialects.postgresql import Insert as PGInsert
from sqlalchemy.dialects.postgresql import dialect as postgresql_dialect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import Select

from app.database.activity_event import ActivityEvent
from app.database.source_document import SourceDocument
from app.projects.event_spine import (
    PROJECT_VERBS,
    ProjectVerb,
    list_project_verbs,
    maybe_record_document_revised,
    record_project_verb,
    revision_sort_key,
    verb_dedup_key,
)
from tests.conftest import run_async

PROJECT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
REFERENCE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")

_CARD_VERBS = frozenset(
    {
        "document.received",
        "document.extracted",
        "document.classified",
        "document.reclassified",
        "document.filed",
        "document.revised",
        "invoice.received",
        "invoice.needs_review",
        "invoice.approved",
        "invoice.rejected",
        "invoice.posted",
        "invoice.duplicate",
        "invoice.conflict",
        "email.received",
        "email.linked",
        "email.action_detected",
        "project_signal.detected",
    }
)


def _params(statement) -> dict:
    return dict(statement.compile().params)


class VerbSession:
    """Simulates INSERT ... ON CONFLICT DO NOTHING RETURNING id."""

    def __init__(self, *, existing_revisions: list[str] | None = None) -> None:
        self.keys: set[tuple[uuid.UUID, str]] = set()
        self.rows: list[dict] = []
        self.statements: list = []
        self.existing_revisions = existing_revisions or []

    async def execute(self, statement):
        self.statements.append(statement)
        if isinstance(statement, Select):
            rows = [
                SimpleNamespace(
                    document_metadata={
                        "drawing_number": "S203",
                        "revision": revision,
                    }
                )
                for revision in self.existing_revisions
            ]
            return SimpleNamespace(all=lambda: rows, scalars=lambda: SimpleNamespace(all=lambda: []))

        params = _params(statement)
        key = (params["project_id"], params["deduplication_key"])
        if key in self.keys:
            return SimpleNamespace(scalar_one_or_none=lambda: None)
        self.keys.add(key)
        self.rows.append(params)
        return SimpleNamespace(scalar_one_or_none=lambda: params["id"])


def _record(
    session: VerbSession,
    *,
    verb: ProjectVerb = "document.received",
    extra: str = "hash-1",
    message: str = "Received file",
    metadata: dict | None = None,
    reference_id: uuid.UUID = REFERENCE_ID,
):
    return record_project_verb(
        session,
        project_id=PROJECT_ID,
        verb=verb,
        reference_type="source_document",
        reference_id=reference_id,
        message=message,
        deduplication_key=verb_dedup_key(
            verb,
            reference_type="source_document",
            reference_id=reference_id,
            extra=extra,
        ),
        metadata=metadata,
    )


def test_unknown_verb_raises() -> None:
    session = VerbSession()
    with pytest.raises(ValueError, match="unknown project verb"):
        run_async(
            record_project_verb(
                session,
                project_id=PROJECT_ID,
                verb="document.invented",  # type: ignore[arg-type]
                reference_type="source_document",
                reference_id=REFERENCE_ID,
                message="nope",
                deduplication_key="x",
            )
        )
    assert session.statements == []


def test_duplicate_dedup_key_is_noop() -> None:
    session = VerbSession()
    first = run_async(_record(session))
    second = run_async(_record(session))

    assert first is not None
    assert first.source == "document.received"
    assert first.step == "document.received"
    assert first.status == "complete"
    assert first.run_id is not None
    assert second is None
    assert len(session.rows) == 1
    compiled = str(session.statements[0].compile(dialect=postgresql_dialect()))
    assert "ON CONFLICT" in compiled
    assert "DO NOTHING" in compiled
    assert "deduplication_key" in compiled
    assert isinstance(session.statements[0], PGInsert)


def test_duplicate_dedup_key_does_not_log_an_error() -> None:
    session = VerbSession()
    with (
        patch("app.projects.event_spine.log.error") as spine_error,
        patch("app.database.activity_events.log.error") as swallowed,
    ):
        run_async(_record(session))
        run_async(_record(session))

    assert spine_error.call_count == 0
    assert swallowed.call_count == 0


def test_insert_failure_raises_rather_than_being_swallowed() -> None:
    class BoomSession:
        async def execute(self, statement):
            raise IntegrityError("fk_activity_events_project_id", {}, Exception())

    with (
        patch("app.projects.event_spine.log.error") as spine_error,
        patch("app.database.activity_events.log.error") as swallowed,
        pytest.raises(IntegrityError),
    ):
        run_async(_record(BoomSession()))

    assert spine_error.call_count == 0
    assert swallowed.call_count == 0


def test_metadata_allowlist_drops_canonical_payloads() -> None:
    session = VerbSession()
    event = run_async(
        _record(
            session,
            metadata={
                "filename": "S203.pdf",
                "document_class": "drawing",
                "normalized_content": "SECRET BODY",
                "machine_extraction": {"total": "100"},
                "body": "do not persist",
                "content_hash": "abc",
            },
            message="x" * 600,
        )
    )
    assert event is not None
    assert event.event_metadata == {
        "filename": "S203.pdf",
        "document_class": "drawing",
        "content_hash": "abc",
    }
    assert "normalized_content" not in event.event_metadata
    assert "machine_extraction" not in event.event_metadata
    assert "body" not in event.event_metadata
    assert len(event.message) == 500


def test_project_verbs_is_closed_and_covers_the_card() -> None:
    assert PROJECT_VERBS == frozenset(ProjectVerb.__args__)  # type: ignore[attr-defined]
    assert _CARD_VERBS <= PROJECT_VERBS
    assert "project_signal.dismissed" in PROJECT_VERBS
    assert "document_ingest" not in PROJECT_VERBS
    assert "sort_files" not in PROJECT_VERBS


def test_list_project_verbs_excludes_workflow_trace_sources() -> None:
    verb_event = ActivityEvent(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        run_id=uuid.uuid4(),
        source="document.received",
        step="document.received",
        status="complete",
        message="Received",
        event_metadata={},
    )
    session = VerbSession()

    async def execute(statement):
        session.statements.append(statement)
        compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
        assert "document_ingest" not in compiled
        assert "sort_files" not in compiled
        assert "GROUP BY" not in compiled.upper()
        assert "document.received" in compiled
        assert "invoice.approved" in compiled
        assert "email.received" in compiled
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [verb_event]))

    session.execute = execute  # type: ignore[method-assign]
    rows = run_async(list_project_verbs(session, project_id=PROJECT_ID))
    assert rows == [verb_event]
    compiled = str(session.statements[0].compile())
    assert "created_at" in compiled.lower()


def test_later_drawing_revision_emits_document_revised() -> None:
    document = SourceDocument(
        id=REFERENCE_ID,
        project_id=PROJECT_ID,
        project="demo",
        phase="delivery",
        document_class="drawing",
        filename="S203.pdf",
        relative_path="03-design/structural/S203.pdf",
        normalized_content="x" * 200,
        document_metadata={"drawing_number": "S203", "revision": "C"},
    )
    session = VerbSession(existing_revisions=["B"])
    event = run_async(maybe_record_document_revised(session, document=document))
    assert event is not None
    assert event.source == "document.revised"
    assert event.event_metadata["previous_revision"] == "B"
    assert event.event_metadata["revision"] == "C"
    assert event.event_metadata["drawing_number"] == "S203"
    again = run_async(maybe_record_document_revised(session, document=document))
    assert again is None
    assert len(session.rows) == 1


def test_earlier_revision_arriving_late_emits_nothing() -> None:
    document = SourceDocument(
        id=REFERENCE_ID,
        project_id=PROJECT_ID,
        project="demo",
        phase="delivery",
        document_class="drawing",
        filename="S203-B.pdf",
        relative_path="03-design/structural/S203-B.pdf",
        normalized_content="x" * 200,
        document_metadata={"drawing_number": "S203", "revision": "B"},
    )
    session = VerbSession(existing_revisions=["C"])
    event = run_async(maybe_record_document_revised(session, document=document))
    assert event is None
    assert session.rows == []


def test_numeric_revision_10_supersedes_9() -> None:
    assert revision_sort_key("Rev 10") > revision_sort_key("Rev 9")
    assert revision_sort_key("C") > revision_sort_key("B")
    document = SourceDocument(
        id=REFERENCE_ID,
        project_id=PROJECT_ID,
        project="demo",
        phase="delivery",
        document_class="drawing",
        filename="S203.pdf",
        relative_path="03-design/structural/S203.pdf",
        normalized_content="x" * 200,
        document_metadata={"drawing_number": "S203", "revision": "Rev 10"},
    )
    session = VerbSession(existing_revisions=["Rev 9"])
    event = run_async(maybe_record_document_revised(session, document=document))
    assert event is not None
    assert event.event_metadata["revision"] == "Rev 10"
    assert event.event_metadata["previous_revision"] == "Rev 9"


def test_inbox_upload_emits_document_received() -> None:
    from app.database.project import Project
    from app.inbox.service import InboxUploadItem, upload_inbox_files
    from ingest.hashing import bytes_content_hash

    project = Project(
        id=PROJECT_ID,
        owner_user_id=uuid.uuid4(),
        slug="demo",
        title="Demo",
        workspace_path="04-projects/demo",
        phase="procurement",
        status="active",
        project_metadata={},
        created_at=datetime(2026, 8, 19, tzinfo=UTC),
        updated_at=datetime(2026, 8, 19, tzinfo=UTC),
    )
    content = b"# Brief\n\nProject context for ingest."
    file_id = uuid.uuid4()
    snapshot = SimpleNamespace(
        content_fingerprint="a" * 64,
        profile=SimpleNamespace(profile_revision=1),
        decisions=SimpleNamespace(set_revision=1),
    )
    verb = AsyncMock()
    session = AsyncMock()

    async def _run() -> None:
        with (
            patch(
                "app.inbox.service.get_workspace_file_by_path",
                new=AsyncMock(return_value=None),
            ),
            patch("app.inbox.service.upload_project_file"),
            patch(
                "app.inbox.service.lock_project",
                new=AsyncMock(return_value=project),
            ),
            patch(
                "app.inbox.service.start_workflow_run",
                new=AsyncMock(return_value=(SimpleNamespace(id=uuid.uuid4()), True)),
            ),
            patch(
                "app.inbox.service.upsert_workspace_file",
                new=AsyncMock(
                    return_value=SimpleNamespace(
                        id=file_id,
                        filename="brief.md",
                        content_hash=bytes_content_hash(content),
                    )
                ),
            ),
            patch("app.inbox.service.record_project_verb", new=verb),
            patch("app.inbox.service.record_activity_events", new=AsyncMock()),
        ):
            await upload_inbox_files(
                session,
                project=project,
                items=[InboxUploadItem(filename="brief.md", content=content)],
                user_id=uuid.uuid4(),
                snapshot=snapshot,
            )

        verb.assert_awaited()
        kwargs = verb.await_args.kwargs
        assert kwargs["verb"] == "document.received"
        assert kwargs["reference_type"] == "workspace_file"
        assert kwargs["reference_id"] == file_id
        assert kwargs["metadata"]["content_hash"] == bytes_content_hash(content)
        assert kwargs["metadata"]["filename"] == "brief.md"

    run_async(_run())


def test_successful_ingest_emits_extracted_and_classified() -> None:
    from app.workflows.document_ingest import ingest_project_document

    workspace_file_id = uuid.uuid4()
    source_document_id = uuid.uuid4()
    record = SimpleNamespace(
        id=workspace_file_id,
        project_id=PROJECT_ID,
        filename="brief.md",
        workspace_path="04-projects/demo/_inbox/brief.md",
        storage_key="demo/_inbox/brief.md",
        ingest_status="queued",
        ingest_error=None,
        source_document_id=None,
        content_hash="abc123",
    )
    document = SimpleNamespace(
        id=source_document_id,
        document_metadata={"subject": "heritage", "revision": "P1"},
        normalized_content="x" * 200,
        relative_path="04-projects/demo/_inbox/brief.md",
        document_class="report",
        filename="brief.md",
        content_hash="abc123",
        project_id=PROJECT_ID,
    )
    session = AsyncMock()
    session.get = AsyncMock(side_effect=lambda model, ident: record if ident == workspace_file_id else document)
    verb = AsyncMock()
    project = SimpleNamespace(
        id=PROJECT_ID,
        slug="demo",
        phase="procurement",
        workspace_path="04-projects/demo",
    )

    async def _run() -> None:
        with (
            patch(
                "app.workflows.document_ingest.download_project_file",
                return_value=b"# Brief",
            ),
            patch(
                "app.workflows.document_ingest.ingest_hosted_file",
                return_value=True,
            ),
            patch(
                "app.workflows.document_ingest.source_document_id_for_path",
                return_value=source_document_id,
            ),
            patch(
                "app.workflows.document_ingest.record_activity_events",
                new=AsyncMock(),
            ),
            patch(
                "app.workflows.document_ingest.record_project_verb",
                new=verb,
            ),
            patch(
                "app.workflows.document_ingest.maybe_record_document_revised",
                new=AsyncMock(),
            ),
            patch(
                "app.workflows.document_ingest.safe_bootstrap_identity_from_document",
                new=AsyncMock(),
            ),
            patch(
                "app.workflows.document_ingest.file_single_document",
                new=AsyncMock(return_value=None),
            ),
            patch("app.workflows.document_ingest.upsert_consultant_fact_from_document"),
        ):
            await ingest_project_document(
                session,
                project=project,
                run_id=uuid.uuid4(),
                workspace_file_id=workspace_file_id,
            )

        verbs = [call.kwargs["verb"] for call in verb.await_args_list]
        assert verbs == ["document.extracted", "document.classified"]
        extracted, classified = verb.await_args_list
        assert extracted.kwargs["metadata"]["content_hash"] == "abc123"
        assert classified.kwargs["metadata"]["document_class"] == "report"
        assert classified.kwargs["deduplication_key"].endswith("abc123:report:heritage")

    run_async(_run())


def test_unchanged_reingest_does_not_emit_again() -> None:
    from app.workflows.document_ingest import ingest_project_document

    workspace_file_id = uuid.uuid4()
    record = SimpleNamespace(
        id=workspace_file_id,
        project_id=PROJECT_ID,
        filename="brief.md",
        workspace_path="04-projects/demo/_inbox/brief.md",
        storage_key="demo/_inbox/brief.md",
        ingest_status="queued",
        ingest_error=None,
        source_document_id=None,
        content_hash="abc123",
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=record)
    verb = AsyncMock()
    project = SimpleNamespace(
        id=PROJECT_ID,
        slug="demo",
        phase="procurement",
        workspace_path="04-projects/demo",
    )

    async def _run() -> None:
        with (
            patch(
                "app.workflows.document_ingest.download_project_file",
                return_value=b"# Brief",
            ),
            patch(
                "app.workflows.document_ingest.ingest_hosted_file",
                return_value=False,
            ),
            patch(
                "app.workflows.document_ingest.source_document_id_for_path",
                return_value=uuid.uuid4(),
            ),
            patch(
                "app.workflows.document_ingest.record_activity_events",
                new=AsyncMock(),
            ),
            patch(
                "app.workflows.document_ingest.record_project_verb",
                new=verb,
            ),
            patch(
                "app.workflows.document_ingest.maybe_record_document_revised",
                new=AsyncMock(),
            ),
        ):
            await ingest_project_document(
                session,
                project=project,
                run_id=uuid.uuid4(),
                workspace_file_id=workspace_file_id,
            )

        verb.assert_not_awaited()

    run_async(_run())


def test_approve_twice_does_not_duplicate_invoice_approved_event() -> None:
    from app.cost_plan.invoice_service import _record_invoice_event

    invoice_id = uuid.uuid4()
    invoice = SimpleNamespace(id=invoice_id, invoice_number="INV-009")
    session = VerbSession()
    session.get = AsyncMock(return_value=invoice)  # type: ignore[method-assign]

    async def _run() -> None:
        await _record_invoice_event(
            session,
            project_id=PROJECT_ID,
            invoice_id=invoice_id,
            source="invoice.approved",
            message="Invoice approved",
        )
        await _record_invoice_event(
            session,
            project_id=PROJECT_ID,
            invoice_id=invoice_id,
            source="invoice.approved",
            message="Invoice approved",
        )

    run_async(_run())
    assert len(session.rows) == 1
    assert session.rows[0]["source"] == "invoice.approved"


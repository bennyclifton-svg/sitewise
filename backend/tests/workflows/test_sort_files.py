import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.database.workspace_file import WorkspaceFile
from app.intake.sort_service import (
    SortFilesResult,
    _move_workspace_file,
    _resolve_destination_filename,
    sort_inbox_files,
)
from app.workflows.sort_files import run_sort_files_workflow
from tests.conftest import run_async


@pytest.fixture(autouse=True)
def _silent_sort_verbs() -> None:
    with patch(
        "app.intake.sort_service.record_project_verb",
        new_callable=AsyncMock,
    ):
        yield


USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _project(**overrides):
    from app.database.project import Project

    values = {
        "id": PROJECT_ID,
        "owner_user_id": USER_ID,
        "slug": "greenfield-demo",
        "title": "Greenfield Demo",
        "workspace_path": "04-projects/greenfield-demo",
        "phase": "brief-planning",
        "archetype": "renovation",
        "user_role": "architect-pm",
        "state": "NSW",
        "status": "active",
        "project_metadata": None,
        "created_at": datetime(2026, 6, 7, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 6, 7, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return Project(**values)


def _workspace_file(**overrides) -> WorkspaceFile:
    values = {
        "id": uuid.uuid4(),
        "project_id": PROJECT_ID,
        "workspace_path": "04-projects/greenfield-demo/_inbox/ARCHITECTURE/CC-A-010.pdf",
        "filename": "CC-A-010.pdf",
        "storage_bucket": "project-files",
        "storage_key": f"{PROJECT_ID}/04-projects/greenfield-demo/_inbox/ARCHITECTURE/CC-A-010.pdf",
        "content_hash": "abc123",
        "size_bytes": 1200,
        "ingest_status": "ingested",
        "ingest_error": None,
        "source_document_id": None,
        "created_at": datetime(2026, 6, 7, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 6, 7, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return WorkspaceFile(**values)


def test_sort_files_blocks_when_overlay_gate_fails() -> None:
    result = run_async(
        run_sort_files_workflow(
            AsyncMock(),
            user_id=USER_ID,
            project=_project(archetype="TBC"),
            thread_id=None,
        )
    )

    assert result.status == "blocked"
    assert result.gate.ready is False
    assert result.draft is None


def test_sort_inbox_skips_manifest_and_leaves_unresolved() -> None:
    session = AsyncMock()
    inbox_files = [
        _workspace_file(
            workspace_path="04-projects/greenfield-demo/_inbox/intake_manifest_v01.md",
            filename="intake_manifest_v01.md",
        ),
        _workspace_file(
            workspace_path="04-projects/greenfield-demo/_inbox/notes.txt",
            filename="notes.txt",
        ),
    ]

    with patch(
        "app.intake.sort_service.list_workspace_files_under_prefix",
        new=AsyncMock(return_value=inbox_files),
    ):
        result = run_async(sort_inbox_files(session, project=_project()))

    assert result.counts.skipped == 1
    assert result.counts.needs_review == 1
    assert result.counts.moved == 0
    assert "intake_manifest_v" in result.manifest_markdown


def test_sort_inbox_skips_files_that_are_still_ingesting() -> None:
    session = AsyncMock()
    queued = _workspace_file(ingest_status="queued")

    with (
        patch(
            "app.intake.sort_service.list_workspace_files_under_prefix",
            new=AsyncMock(return_value=[queued]),
        ),
        patch("app.intake.sort_service._move_workspace_file", new=AsyncMock()) as move,
    ):
        result = run_async(sort_inbox_files(session, project=_project()))

    assert result.counts.waiting == 1
    assert result.counts.inspected == 0
    assert result.records[0].outcome == "waiting"
    assert result.records[0].reason == "Ingestion is still in progress"
    move.assert_not_awaited()


def test_files_still_ingesting_report_waiting_not_skipped() -> None:
    session = AsyncMock()
    queued = _workspace_file(
        ingest_status="queued",
        filename="still-ingesting.pdf",
        workspace_path="04-projects/greenfield-demo/_inbox/still-ingesting.pdf",
    )

    with patch(
        "app.intake.sort_service.list_workspace_files_under_prefix",
        new=AsyncMock(return_value=[queued]),
    ):
        result = run_async(sort_inbox_files(session, project=_project()))

    record = next(r for r in result.records if r.filename == "still-ingesting.pdf")
    assert record.outcome == "waiting"
    assert result.counts.waiting == 1
    assert result.counts.skipped == 0


def test_failed_ingest_reports_failed_not_skipped() -> None:
    session = AsyncMock()
    failed = _workspace_file(
        ingest_status="failed",
        filename="broken.pdf",
        workspace_path="04-projects/greenfield-demo/_inbox/broken.pdf",
    )

    with patch(
        "app.intake.sort_service.list_workspace_files_under_prefix",
        new=AsyncMock(return_value=[failed]),
    ):
        result = run_async(sort_inbox_files(session, project=_project()))

    assert result.records[0].outcome == "failed"
    assert result.counts.failed == 1
    assert result.counts.skipped == 0


def test_low_confidence_reports_needs_review() -> None:
    session = AsyncMock()
    doc_id = uuid.uuid4()
    source = _workspace_file(
        source_document_id=doc_id,
        ingest_status="ingested",
        filename="scan.pdf",
        workspace_path="04-projects/greenfield-demo/_inbox/scan.pdf",
    )
    document = SimpleNamespace(
        document_class="unknown",
        ingest_mode="full_text",
        document_metadata={"confidence": "0.40", "basis": "filename", "subject": "none"},
        relative_path=source.workspace_path,
    )
    session.get = AsyncMock(return_value=document)

    with (
        patch(
            "app.intake.sort_service.list_workspace_files_under_prefix",
            new=AsyncMock(return_value=[source]),
        ),
        patch("app.intake.sort_service._move_workspace_file", new=AsyncMock()) as move,
    ):
        result = run_async(sort_inbox_files(session, project=_project()))

    assert result.records[0].outcome == "needs-review"
    assert result.counts.needs_review == 1
    assert result.counts.moved == 0
    move.assert_not_awaited()


def test_weak_filename_guess_reports_needs_review() -> None:
    from ingest.classify import classify_entry
    from ingest.types import ManifestEntry
    from pathlib import Path

    classification = classify_entry(
        ManifestEntry(
            absolute_path=Path("Statement.pdf"),
            relative_path="04-projects/greenfield-demo/_inbox/Statement.pdf",
            project="greenfield-demo",
            filename="Statement.pdf",
            extension=".pdf",
            size_bytes=100,
        )
    )
    session = AsyncMock()
    doc_id = uuid.uuid4()
    source = _workspace_file(
        source_document_id=doc_id,
        ingest_status="ingested",
        filename="Statement.pdf",
        workspace_path="04-projects/greenfield-demo/_inbox/Statement.pdf",
    )
    document = SimpleNamespace(
        document_class=classification.document_class,
        ingest_mode="full_text",
        document_metadata={
            "confidence": f"{classification.confidence:.2f}",
            "basis": classification.basis,
            "subject": classification.document_subject,
        },
        relative_path=source.workspace_path,
    )
    session.get = AsyncMock(return_value=document)

    with (
        patch(
            "app.intake.sort_service.list_workspace_files_under_prefix",
            new=AsyncMock(return_value=[source]),
        ),
        patch("app.intake.sort_service._move_workspace_file", new=AsyncMock()) as move,
    ):
        result = run_async(sort_inbox_files(session, project=_project()))

    assert classification.confidence < 0.65
    assert result.records[0].outcome == "needs-review"
    assert result.counts.needs_review == 1
    move.assert_not_awaited()


def test_sort_does_not_download_files(monkeypatch) -> None:
    session = AsyncMock()
    source = _workspace_file()
    calls: list[object] = []

    def capture_download(**kwargs):
        calls.append(kwargs)
        return b""

    monkeypatch.setattr(
        "app.intake.sort_service.download_project_file", capture_download
    )

    with (
        patch(
            "app.intake.sort_service.list_workspace_files_under_prefix",
            new=AsyncMock(return_value=[source]),
        ),
        patch(
            "app.intake.sort_service.get_workspace_file_by_path",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.intake.sort_service._resolve_destination_filename",
            new=AsyncMock(return_value="CC-A-010.pdf"),
        ),
        patch("app.intake.sort_service._move_workspace_file", new=AsyncMock()),
        patch(
            "app.intake.sort_service.source_document_id_for_path",
            return_value=None,
        ),
    ):
        run_async(sort_inbox_files(session, project=_project()))

    assert calls == []


def test_sort_twice_is_a_no_op() -> None:
    session = AsyncMock()
    source = _workspace_file()
    destinations: dict[str, WorkspaceFile] = {}

    async def fake_get_by_path(session_obj, *, project_id, workspace_path):
        return destinations.get(workspace_path)

    async def fake_move(session_obj, *, project, record, destination_workspace_path, destination_filename):
        moved_record = _workspace_file(
            workspace_path=destination_workspace_path,
            filename=destination_filename,
            content_hash=record.content_hash,
        )
        destinations[destination_workspace_path] = moved_record
        return moved_record

    with (
        patch(
            "app.intake.sort_service.list_workspace_files_under_prefix",
            new=AsyncMock(return_value=[source]),
        ),
        patch(
            "app.intake.sort_service.get_workspace_file_by_path",
            side_effect=fake_get_by_path,
        ),
        patch(
            "app.intake.sort_service._resolve_destination_filename",
            new=AsyncMock(return_value="CC-A-010.pdf"),
        ),
        patch(
            "app.intake.sort_service._move_workspace_file",
            new=AsyncMock(side_effect=fake_move),
        ),
        patch(
            "app.intake.sort_service.source_document_id_for_path",
            return_value=None,
        ),
    ):
        first = run_async(sort_inbox_files(session, project=_project()))
        second = run_async(sort_inbox_files(session, project=_project()))

    assert first.counts.moved == 1
    assert second.counts.moved == 0
    assert second.counts.already_filed == first.counts.moved


def test_sort_inbox_refuses_when_destination_hash_differs() -> None:
    session = AsyncMock()
    source = _workspace_file()
    destination = _workspace_file(
        workspace_path="04-projects/greenfield-demo/03-design/architect/CC-A-010.pdf",
        filename="CC-A-010.pdf",
        content_hash="different",
    )

    async def fake_get_by_path(session_obj, *, project_id, workspace_path):
        if workspace_path.endswith("/03-design/architect/CC-A-010.pdf"):
            return destination
        return None

    with (
        patch(
            "app.intake.sort_service.list_workspace_files_under_prefix",
            new=AsyncMock(return_value=[source]),
        ),
        patch(
            "app.intake.sort_service.get_workspace_file_by_path",
            side_effect=fake_get_by_path,
        ),
        patch(
            "app.intake.sort_service._resolve_destination_filename",
            new=AsyncMock(return_value="CC-A-010.pdf"),
        ),
    ):
        result = run_async(sort_inbox_files(session, project=_project()))

    assert result.counts.refused == 1
    assert result.records[0].outcome == "refused"


def test_sort_inbox_refuses_when_move_fails() -> None:
    session = AsyncMock()
    source = _workspace_file()
    canary = "ch03-sort-storage-token-xxxxxxxxxxxxxxxxxxxxxxxx"

    with (
        patch(
            "app.intake.sort_service.list_workspace_files_under_prefix",
            new=AsyncMock(return_value=[source]),
        ),
        patch(
            "app.intake.sort_service.get_workspace_file_by_path",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.intake.sort_service._resolve_destination_filename",
            new=AsyncMock(return_value="CC-A-010.pdf"),
        ),
        patch(
            "app.intake.sort_service._move_workspace_file",
            new=AsyncMock(side_effect=RuntimeError(canary)),
        ),
        patch("app.intake.sort_service.log.error") as log_error,
    ):
        result = run_async(sort_inbox_files(session, project=_project()))

    assert result.counts.refused == 1
    assert result.records[0].outcome == "refused"
    assert result.records[0].reason == "Project storage could not move the file."
    assert result.warnings == ["A project file could not be moved in storage."]
    assert canary not in str(result)
    assert canary not in result.manifest_markdown
    assert log_error.call_args.kwargs["error_type"] == "RuntimeError"
    assert canary not in str(log_error.call_args)


def test_sort_inbox_moves_confident_match() -> None:
    session = AsyncMock()
    source = _workspace_file()
    moved_record = _workspace_file(
        workspace_path="04-projects/greenfield-demo/03-design/architect/CC-A-010 - SITE PLAN.pdf",
        filename="CC-A-010 - SITE PLAN.pdf",
    )

    with (
        patch(
            "app.intake.sort_service.list_workspace_files_under_prefix",
            new=AsyncMock(return_value=[source]),
        ),
        patch(
            "app.intake.sort_service.get_workspace_file_by_path",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.intake.sort_service._resolve_destination_filename",
            new=AsyncMock(return_value="CC-A-010 - SITE PLAN.pdf"),
        ),
        patch(
            "app.intake.sort_service._move_workspace_file",
            new=AsyncMock(return_value=moved_record),
        ),
        patch(
            "app.intake.sort_service.source_document_id_for_path",
            return_value=None,
        ),
    ):
        result = run_async(sort_inbox_files(session, project=_project()))

    assert result.counts.moved == 1
    assert result.records[0].destination_path.endswith("/03-design/architect/CC-A-010 - SITE PLAN.pdf")


def test_successful_file_move_emits_document_filed() -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    doc_id = uuid.uuid4()
    source = _workspace_file(source_document_id=doc_id)
    moved_record = _workspace_file(
        workspace_path="04-projects/greenfield-demo/03-design/architect/CC-A-010 - SITE PLAN.pdf",
        filename="CC-A-010 - SITE PLAN.pdf",
        source_document_id=doc_id,
    )
    verb = AsyncMock()

    with (
        patch(
            "app.intake.sort_service.list_workspace_files_under_prefix",
            new=AsyncMock(return_value=[source]),
        ),
        patch(
            "app.intake.sort_service.get_workspace_file_by_path",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.intake.sort_service._resolve_destination_filename",
            new=AsyncMock(return_value="CC-A-010 - SITE PLAN.pdf"),
        ),
        patch(
            "app.intake.sort_service._move_workspace_file",
            new=AsyncMock(return_value=moved_record),
        ),
        patch(
            "app.intake.sort_service.source_document_id_for_path",
            return_value=doc_id,
        ),
        patch(
            "app.intake.sort_service.record_project_verb",
            new=verb,
        ),
    ):
        result = run_async(sort_inbox_files(session, project=_project()))

    assert result.counts.moved == 1
    verb.assert_awaited()
    kwargs = verb.await_args.kwargs
    assert kwargs["verb"] == "document.filed"
    assert kwargs["reference_id"] == doc_id
    assert kwargs["deduplication_key"].endswith(
        result.records[0].destination_path
    )


def test_sort_inbox_moves_chen_authority_pack() -> None:
    session = AsyncMock()
    planning = _workspace_file(
        workspace_path="04-projects/greenfield-demo/_inbox/09-planning-pathway-memo-harrison-clarke.md",
        filename="09-planning-pathway-memo-harrison-clarke.md",
        storage_key=f"{PROJECT_ID}/planning.md",
        content_hash="planning",
    )
    certifier = _workspace_file(
        workspace_path="04-projects/greenfield-demo/_inbox/12-certifier-appointment-chen-residence.md",
        filename="12-certifier-appointment-chen-residence.md",
        storage_key=f"{PROJECT_ID}/certifier.md",
        content_hash="certifier",
    )
    previews = {
        planning.storage_key: b"# PLANNING PATHWAY MEMO\n\nPursue DA + CC pathway.",
        certifier.storage_key: b"Subject: Principal certifier appointed\n\nCertifier engagement on file.",
    }

    async def fake_resolve_destination_filename(**kwargs):
        return kwargs["filename"]

    with (
        patch(
            "app.intake.sort_service.list_workspace_files_under_prefix",
            new=AsyncMock(return_value=[planning, certifier]),
        ),
        patch(
            "app.intake.sort_service.download_project_file",
            side_effect=lambda *, storage_key: previews[storage_key],
        ),
        patch(
            "app.intake.sort_service.get_workspace_file_by_path",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.intake.sort_service._resolve_destination_filename",
            new=AsyncMock(side_effect=fake_resolve_destination_filename),
        ),
        patch("app.intake.sort_service._move_workspace_file", new=AsyncMock()),
        patch(
            "app.intake.sort_service.source_document_id_for_path",
            return_value=None,
        ),
    ):
        result = run_async(sort_inbox_files(session, project=_project()))

    assert result.counts.moved == 2
    assert result.counts.unresolved == 0
    assert all(record.outcome == "moved" for record in result.records)
    assert all(
        record.destination_path is not None
        and "/04-planning-and-authorities/" in record.destination_path
        for record in result.records
    )


def test_move_workspace_file_updates_existing_source_document_path() -> None:
    session = AsyncMock()
    source_document_id = uuid.uuid4()
    source = _workspace_file(source_document_id=source_document_id)
    moved_record = _workspace_file(
        workspace_path="04-projects/greenfield-demo/03-design/architect/CC-A-010.pdf",
        filename="CC-A-010.pdf",
        source_document_id=source_document_id,
    )
    document = SimpleNamespace(
        id=source_document_id,
        document_class="drawing",
        filename="CC-A-010.pdf",
        relative_path=source.workspace_path,
        document_metadata={"drawing_number": "CC-A-010", "basis": "filename"},
    )
    session.get = AsyncMock(return_value=document)

    with (
        patch("app.intake.sort_service.download_project_file", return_value=b"content"),
        patch("app.intake.sort_service.upload_project_file"),
        patch("app.intake.sort_service.delete_project_files"),
        patch(
            "app.intake.sort_service.upsert_workspace_file",
            new=AsyncMock(return_value=moved_record),
        ),
    ):
        result = run_async(
            _move_workspace_file(
                session,
                project=_project(),
                record=source,
                destination_workspace_path=moved_record.workspace_path,
                destination_filename=moved_record.filename,
            )
        )

    assert result == moved_record
    assert document.relative_path == moved_record.workspace_path
    assert document.filename == moved_record.filename
    assert document.document_class == "drawing"
    session.delete.assert_awaited_once_with(source)
    session.flush.assert_awaited_once()


def test_split_schedule_identity_controls_sorted_filename() -> None:
    result = run_async(
        _resolve_destination_filename(
            source_path="04-projects/greenfield-demo/_inbox/sheet.pdf",
            destination_folder="03-design/landscape-architect",
            filename="Landscape Design - 03 Landscape [D].pdf",
            project=_project(),
            preview_snippet="Drawing Title DETAILS\nRevision D",
            document_metadata={
                "split_from": "Landscape Design [D].pdf",
                "split_method": "drawing_schedule_v1",
                "document_number": "LPCC 23 - 226 / 3",
                "title": "Section & Details",
                "revision": "D",
            },
        )
    )

    assert result == "LPCC 23 - 226 - 3 - Section & Details Rev D.pdf"


def test_filed_document_keeps_the_classification_that_routed_it() -> None:
    session = AsyncMock()
    source_document_id = uuid.uuid4()
    source = _workspace_file(source_document_id=source_document_id)
    moved_record = _workspace_file(
        workspace_path="04-projects/greenfield-demo/01-cost/Invoice 0043.pdf",
        filename="Invoice 0043.pdf",
        source_document_id=source_document_id,
    )
    document = SimpleNamespace(
        id=source_document_id,
        document_class="commercial",
        filename="Invoice 0043.pdf",
        relative_path=source.workspace_path,
        document_metadata={"commercial_type": "invoice", "basis": "filename"},
    )
    session.get = AsyncMock(return_value=document)

    with (
        patch("app.intake.sort_service.download_project_file", return_value=b"content"),
        patch("app.intake.sort_service.upload_project_file"),
        patch("app.intake.sort_service.delete_project_files"),
        patch(
            "app.intake.sort_service.upsert_workspace_file",
            new=AsyncMock(return_value=moved_record),
        ),
    ):
        run_async(
            _move_workspace_file(
                session,
                project=_project(),
                record=source,
                destination_workspace_path=moved_record.workspace_path,
                destination_filename=moved_record.filename,
            )
        )

    assert document.document_class == "commercial"
    assert document.document_metadata["commercial_type"] == "invoice"
    assert document.relative_path == moved_record.workspace_path


def test_move_does_not_reextract_or_reembed() -> None:
    import app.intake.sort_service as sort_service

    assert not hasattr(sort_service, "ingest_hosted_file")
    session = AsyncMock()
    source = _workspace_file(source_document_id=uuid.uuid4())
    moved_record = _workspace_file(
        workspace_path="04-projects/greenfield-demo/03-design/architect/CC-A-010.pdf",
        filename="CC-A-010.pdf",
        source_document_id=source.source_document_id,
    )
    document = SimpleNamespace(
        id=source.source_document_id,
        document_class="drawing",
        filename=source.filename,
        relative_path=source.workspace_path,
        document_metadata={},
    )
    session.get = AsyncMock(return_value=document)

    with (
        patch("app.intake.sort_service.download_project_file", return_value=b"content"),
        patch("app.intake.sort_service.upload_project_file"),
        patch("app.intake.sort_service.delete_project_files"),
        patch(
            "app.intake.sort_service.upsert_workspace_file",
            new=AsyncMock(return_value=moved_record),
        ),
    ):
        run_async(
            _move_workspace_file(
                session,
                project=_project(),
                record=source,
                destination_workspace_path=moved_record.workspace_path,
                destination_filename=moved_record.filename,
            )
        )

    session.get.assert_awaited()


def test_move_workspace_file_deletes_source_blob_only_after_commit() -> None:
    session = AsyncMock()
    new_source_document_id = uuid.uuid4()
    source = _workspace_file()
    moved_record = _workspace_file(
        workspace_path="04-projects/greenfield-demo/03-design/architect/CC-A-010.pdf",
        filename="CC-A-010.pdf",
        source_document_id=new_source_document_id,
    )

    with (
        patch("app.intake.sort_service.download_project_file", return_value=b"content"),
        patch("app.intake.sort_service.upload_project_file") as upload,
        patch("app.intake.sort_service.delete_project_files") as delete_source,
        patch(
            "app.intake.sort_service.upsert_workspace_file",
            new=AsyncMock(return_value=moved_record),
        ),
    ):
        result = run_async(
            _move_workspace_file(
                session,
                project=_project(),
                record=source,
                destination_workspace_path=moved_record.workspace_path,
                destination_filename=moved_record.filename,
            )
        )

    assert result == moved_record
    upload.assert_called_once()
    session.commit.assert_awaited_once()
    delete_source.assert_called_once_with(storage_keys=[source.storage_key])


def test_move_workspace_file_keeps_source_blob_when_commit_fails() -> None:
    session = AsyncMock()
    session.commit.side_effect = RuntimeError("deadlock detected")
    source = _workspace_file()
    moved_record = _workspace_file(
        workspace_path="04-projects/greenfield-demo/03-design/architect/CC-A-010.pdf",
        filename="CC-A-010.pdf",
    )

    with (
        patch("app.intake.sort_service.download_project_file", return_value=b"content"),
        patch("app.intake.sort_service.upload_project_file"),
        patch("app.intake.sort_service.delete_project_files") as delete_source,
        patch(
            "app.intake.sort_service.upsert_workspace_file",
            new=AsyncMock(return_value=moved_record),
        ),
    ):
        with pytest.raises(RuntimeError, match="deadlock detected"):
            run_async(
                _move_workspace_file(
                    session,
                    project=_project(),
                    record=source,
                    destination_workspace_path=moved_record.workspace_path,
                    destination_filename=moved_record.filename,
                )
            )

    delete_source.assert_not_called()


@pytest.mark.parametrize(
    ("unresolved", "refused", "expected_status"),
    [
        (0, 0, "complete"),
        (1, 0, "needs_review"),
        (0, 1, "needs_review"),
    ],
)
def test_run_sort_files_workflow_reports_reviewable_outcomes(
    unresolved: int,
    refused: int,
    expected_status: str,
) -> None:
    session = AsyncMock()
    sort_result = SortFilesResult()
    sort_result.counts.inspected = 2
    sort_result.counts.moved = 1
    sort_result.counts.unresolved = unresolved
    sort_result.counts.refused = refused
    sort_result.manifest_version = 2
    sort_result.manifest_workspace_path = (
        "04-projects/greenfield-demo/_inbox/intake_manifest_v02.md"
    )
    sort_result.manifest_markdown = "# Intake manifest v02\n"

    draft = MagicMock()
    draft.id = uuid.uuid4()
    draft.version = 2
    draft.project_id = PROJECT_ID
    draft.workflow_type = "sort_files"
    draft.status = "draft"
    draft.title = "Intake manifest v02"
    draft.workspace_path = sort_result.manifest_workspace_path
    draft.author_user_id = USER_ID
    draft.content_markdown = sort_result.manifest_markdown
    draft.model = None
    draft.runtime = "clerk-sitewise-sort-files"
    draft.provenance_metadata = {}
    draft.created_at = datetime(2026, 6, 7, tzinfo=timezone.utc)
    draft.updated_at = datetime(2026, 6, 7, tzinfo=timezone.utc)

    with (
        patch(
            "app.workflows.sort_files.sort_inbox_files",
            new=AsyncMock(return_value=sort_result),
        ),
        patch(
            "app.workflows.sort_files.next_draft_version",
            new=AsyncMock(return_value=2),
        ),
            patch(
                "app.workflows.sort_files.create_draft_artifact",
                new=AsyncMock(return_value=draft),
            ),
            patch(
                "app.projects.artefact_revisions.set_export_result_for_path",
                new=AsyncMock(return_value=None),
            ),
        ):
        result = run_async(
            run_sort_files_workflow(
                session,
                user_id=USER_ID,
                project=_project(),
                thread_id=None,
            )
        )

    assert result.status == expected_status
    assert result.trace[-1].status == expected_status
    assert result.draft is not None
    assert result.draft.version == 2
    session.commit.assert_awaited()


def test_sort_reads_drawing_identity_from_the_title_block_not_the_filename() -> None:
    # E02-EL~1.PDF is a Windows 8.3 alias: identity is persisted at ingest (D2).
    session = AsyncMock()
    doc_id = uuid.uuid4()
    drawing = _workspace_file(
        workspace_path="04-projects/greenfield-demo/_inbox/ELEC/E02-EL~1.PDF",
        filename="E02-EL~1.PDF",
        storage_key=f"{PROJECT_ID}/elec.pdf",
        content_hash="elec",
        source_document_id=doc_id,
    )
    document = SimpleNamespace(
        document_class="drawing",
        ingest_mode="register_only",
        relative_path=drawing.workspace_path,
        document_metadata={
            "confidence": "0.95",
            "basis": "structural",
            "subject": "services",
            "document_number": "E02",
            "title": "LEVEL L0 GROUND - LIGHTING LAYOUT",
            "revision": "C1",
            "split_method": "title_block_v1",
        },
    )
    session.get = AsyncMock(return_value=document)

    with (
        patch(
            "app.intake.sort_service.list_workspace_files_under_prefix",
            new=AsyncMock(return_value=[drawing]),
        ),
        patch(
            "app.intake.sort_service.get_workspace_file_by_path",
            new=AsyncMock(return_value=None),
        ),
        patch("app.intake.sort_service._move_workspace_file", new=AsyncMock()),
        patch(
            "app.intake.sort_service.source_document_id_for_path",
            return_value=None,
        ),
    ):
        result = run_async(sort_inbox_files(session, project=_project()))

    assert result.counts.moved == 1
    record = result.records[0]
    assert record.document_number == "E02"
    assert record.title == "LEVEL L0 GROUND - LIGHTING LAYOUT"
    assert record.revision == "C1"
    assert record.destination_filename.lower() == (
        "e02 - level l0 ground - lighting layout rev c1.pdf"
    )

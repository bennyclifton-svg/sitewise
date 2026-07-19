import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.database.workspace_file import WorkspaceFile
from app.intake.sort_service import SortFilesResult, _move_workspace_file, sort_inbox_files
from app.workflows.sort_files import run_sort_files_workflow
from tests.conftest import run_async

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
    assert result.counts.unresolved == 1
    assert result.counts.moved == 0
    assert "intake_manifest_v" in result.manifest_markdown


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
            new=AsyncMock(side_effect=RuntimeError("storage unavailable")),
        ),
    ):
        result = run_async(sort_inbox_files(session, project=_project()))

    assert result.counts.refused == 1
    assert result.records[0].outcome == "refused"
    assert "Move failed" in (result.records[0].reason or "")
    assert result.warnings


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
    ):
        result = run_async(sort_inbox_files(session, project=_project()))

    assert result.counts.moved == 1
    assert result.records[0].destination_path.endswith("/03-design/architect/CC-A-010 - SITE PLAN.pdf")


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


def test_move_workspace_file_purges_old_source_document_id() -> None:
    session = AsyncMock()
    old_source_document_id = uuid.uuid4()
    new_source_document_id = uuid.uuid4()
    source = _workspace_file(source_document_id=old_source_document_id)
    moved_record = _workspace_file(
        workspace_path="04-projects/greenfield-demo/03-design/architect/CC-A-010.pdf",
        filename="CC-A-010.pdf",
        source_document_id=new_source_document_id,
    )

    with (
        patch("app.intake.sort_service.download_project_file", return_value=b"content"),
        patch("app.intake.sort_service.move_project_file"),
        patch("app.intake.sort_service._purge_source_document") as purge,
        patch("app.intake.sort_service.ingest_hosted_file", return_value=True),
        patch(
            "app.intake.sort_service.source_document_id_for_path",
            return_value=new_source_document_id,
        ),
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
    purge.assert_called_once_with(source.workspace_path, PROJECT_ID, old_source_document_id)
    session.delete.assert_awaited_once_with(source)
    session.flush.assert_awaited_once()


def test_run_sort_files_workflow_persists_manifest_draft() -> None:
    session = AsyncMock()
    sort_result = SortFilesResult()
    sort_result.counts.inspected = 2
    sort_result.counts.moved = 1
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

    assert result.status == "complete"
    assert result.draft is not None
    assert result.draft.version == 2
    session.commit.assert_awaited()

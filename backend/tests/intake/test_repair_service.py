import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import fitz

from app.database.project import Project
from app.database.workspace_file import WorkspaceFile
from app.intake.repair_service import (
    FileRepairPreview,
    FileRepairPreviewResult,
    apply_existing_file_repairs,
    preview_existing_file_repairs,
)
from tests.conftest import run_async

PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _project() -> Project:
    now = datetime(2026, 7, 26, tzinfo=timezone.utc)
    return Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="industrial",
        title="Industrial",
        workspace_path="04-projects/industrial",
        phase="design",
        archetype="warehouse",
        user_role="architect-pm",
        state="NSW",
        status="active",
        project_metadata={},
        created_at=now,
        updated_at=now,
    )


def _legacy_hydraulic_file() -> WorkspaceFile:
    now = datetime(2026, 7, 25, tzinfo=timezone.utc)
    return WorkspaceFile(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        workspace_path="04-projects/industrial/03-design/architect/HY-SK~1.PDF",
        filename="HY-SK~1.PDF",
        storage_bucket="project-files",
        storage_key=f"{PROJECT_ID}/legacy-hydraulic.pdf",
        content_hash="abc123",
        size_bytes=1200,
        ingest_status="ingested",
        ingest_error=None,
        source_document_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
    )


def _hydraulic_sheet_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page(width=1191, height=842)
    page.insert_text((700, 700), "Drawing Title:", fontsize=8)
    page.insert_text((780, 700), "HYDRAULIC ROOF DRAINAGE PLAN", fontsize=8)
    page.insert_text((700, 720), "Drawing No:", fontsize=8)
    page.insert_text((780, 720), "HY-SK-06", fontsize=8)
    page.insert_text((700, 740), "Rev:", fontsize=8)
    page.insert_text((780, 740), "P1", fontsize=8)
    data = document.tobytes()
    document.close()
    return data


def test_preview_existing_file_repairs_proposes_folder_and_filename_without_mutating():
    session = AsyncMock()
    legacy = _legacy_hydraulic_file()

    with (
        patch(
            "app.intake.repair_service.list_workspace_files_for_project",
            new=AsyncMock(return_value=[legacy]),
        ),
        patch(
            "app.intake.sort_service.download_project_file",
            return_value=_hydraulic_sheet_pdf(),
        ),
        patch(
            "app.intake.repair_service.get_workspace_file_by_path",
            new=AsyncMock(return_value=None),
        ),
    ):
        result = run_async(
            preview_existing_file_repairs(session, project=_project())
        )

    assert result.inspected == 1
    assert result.changes == 1
    row = result.rows[0]
    assert row.status == "change"
    assert row.current_path.endswith("/03-design/architect/HY-SK~1.PDF")
    assert row.proposed_path.endswith(
        "/03-design/hydraulic/HY-SK-06 - HYDRAULIC ROOF DRAINAGE PLAN Rev P1.PDF"
    )
    assert row.document_number == "HY-SK-06"
    assert row.revision == "P1"
    assert set(row.changes) == {"folder", "filename", "metadata"}
    session.delete.assert_not_awaited()
    session.commit.assert_not_awaited()


def test_apply_existing_file_repairs_rechecks_and_moves_only_approved_changes():
    session = AsyncMock()
    legacy = _legacy_hydraulic_file()
    proposal = FileRepairPreview(
        status="change",
        current_path=legacy.workspace_path,
        current_filename=legacy.filename,
        proposed_path=(
            "04-projects/industrial/03-design/hydraulic/"
            "HY-SK-06 - HYDRAULIC ROOF DRAINAGE PLAN Rev P1.PDF"
        ),
        proposed_filename="HY-SK-06 - HYDRAULIC ROOF DRAINAGE PLAN Rev P1.PDF",
        document_number="HY-SK-06",
        title="HYDRAULIC ROOF DRAINAGE PLAN",
        revision="P1",
        category="Hydraulic",
        confidence="high",
        changes=("folder", "filename", "metadata"),
    )
    preview = FileRepairPreviewResult(inspected=1, changes=1, rows=[proposal])

    with (
        patch(
            "app.intake.repair_service.preview_existing_file_repairs",
            new=AsyncMock(return_value=preview),
        ),
        patch(
            "app.intake.repair_service.get_workspace_file_by_path",
            new=AsyncMock(return_value=legacy),
        ),
        patch(
            "app.intake.repair_service._move_workspace_file",
            new=AsyncMock(return_value=legacy),
            create=True,
        ) as move,
        patch(
            "app.intake.repair_service.record_activity_events",
            new=AsyncMock(),
        ) as record_activity,
    ):
        result = run_async(
            apply_existing_file_repairs(
                session,
                project=_project(),
                workspace_paths={legacy.workspace_path},
            )
        )

    assert result.applied == 1
    assert result.failed == 0
    move.assert_awaited_once()
    record_activity.assert_awaited_once()
    assert record_activity.await_args.kwargs["source"] == "document_repair"
    assert record_activity.await_args.kwargs["events"][0].status == "complete"
    session.commit.assert_awaited_once()

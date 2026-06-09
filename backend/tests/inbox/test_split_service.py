import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import fitz

from app.database.project import Project
from tests.conftest import run_async


def _make_pdf(pages):
    doc = fitz.open()
    for width, height, text in pages:
        page = doc.new_page(width=width, height=height)
        if text:
            page.insert_text((72, 72), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def _project():
    return Project(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        owner_user_id=uuid.uuid4(), slug="demo", title="Demo",
        workspace_path="04-projects/demo", phase="procurement",
        archetype="small-commercial", user_role="architect-pm", state="NSW",
        status="active", project_metadata={},
        created_at=datetime(2026, 6, 7, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 7, tzinfo=timezone.utc),
    )


def test_analyze_stages_pdf_and_returns_proposal():
    from app.inbox.split_service import analyze_pdf_upload

    data = _make_pdf([(1191, 842, "SITE PLAN SHEET: 2 OF 20 SCALE: 1:200")] * 4)

    async def _run():
        with patch("app.inbox.split_service.upload_project_file") as mock_upload:
            result = await analyze_pdf_upload(
                project=_project(), filename="L18 CC Plans.pdf", content=data,
            )
        mock_upload.assert_called_once()
        assert result.is_drawing_set is True
        assert result.page_count == 4
        assert len(result.pages) == 4
        assert result.staging_id

    run_async(_run())


def test_split_staged_pdf_ingests_each_sheet_and_deletes_staging():
    from app.inbox.service import InboxUploadOutcome
    from app.inbox.split_service import split_staged_pdf

    data = _make_pdf([
        (1191, 842, "SITE PLAN SHEET: 2 OF 20"),
        (1191, 842, "ELEVATIONS SHEET: 5 OF 20"),
    ])
    project = _project()
    session = AsyncMock()

    async def fake_upload(session, *, project, items):
        return [
            InboxUploadOutcome(
                id=uuid.uuid4(), filename=item.filename,
                workspace_path=f"{project.workspace_path}/_inbox/{item.filename}",
                content_hash="h", size_bytes=len(item.content),
                ingest_status="ingested", message="ok",
            )
            for item in items
        ]

    async def _run():
        with (
            patch("app.inbox.split_service.download_project_file", return_value=data),
            patch("app.inbox.split_service.upload_inbox_files", side_effect=fake_upload) as mock_ingest,
            patch("app.inbox.split_service.delete_project_file") as mock_delete,
            patch("app.inbox.split_service._attach_split_provenance", new=AsyncMock()),
        ):
            outcomes = await split_staged_pdf(
                session, project=project, staging_id="abc123",
                source_filename="L18 CC Plans.pdf",
            )
        assert len(outcomes) == 2
        mock_ingest.assert_called_once()
        mock_delete.assert_called_once()  # staging removed

    run_async(_run())


def test_split_staged_pdf_keeps_staging_when_all_fail():
    from app.inbox.service import InboxUploadOutcome
    from app.inbox.split_service import split_staged_pdf

    data = _make_pdf([(1191, 842, "SITE PLAN SHEET: 2 OF 20")])
    project = _project()

    async def fake_upload(session, *, project, items):
        return [
            InboxUploadOutcome(
                id=uuid.uuid4(), filename=i.filename, workspace_path="w",
                content_hash="h", size_bytes=1, ingest_status="failed", message="boom",
            ) for i in items
        ]

    async def _run():
        with (
            patch("app.inbox.split_service.download_project_file", return_value=data),
            patch("app.inbox.split_service.upload_inbox_files", side_effect=fake_upload),
            patch("app.inbox.split_service.delete_project_file") as mock_delete,
            patch("app.inbox.split_service._attach_split_provenance", new=AsyncMock()),
        ):
            await split_staged_pdf(
                AsyncMock(), project=project, staging_id="abc123",
                source_filename="x.pdf",
            )
        mock_delete.assert_not_called()  # staging retained for retry

    run_async(_run())

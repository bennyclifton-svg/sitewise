"""Auto-sort and consultant-fact promotion after hosted ingest."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.database.project import Project
from app.database.source_document import SourceDocument
from app.database.workspace_file import WorkspaceFile
from app.workflows.document_ingest import ingest_project_document
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DOC_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
FILE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _project() -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="petersham",
        title="Petersham",
        workspace_path="04-projects/petersham",
        phase="brief-planning",
        status="active",
        project_metadata={},
        created_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
        updated_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
    )


def test_ingest_auto_sorts_confident_inbox_drawing_and_promotes_firm() -> None:
    project = _project()
    record = WorkspaceFile(
        id=FILE_ID,
        project_id=PROJECT_ID,
        workspace_path="04-projects/petersham/_inbox/H-001-COVER-Layout1.pdf",
        filename="H-001-COVER-Layout1.pdf",
        storage_bucket="project-files",
        storage_key=f"{PROJECT_ID}/04-projects/petersham/_inbox/H-001-COVER-Layout1.pdf",
        content_hash="abc",
        size_bytes=100,
        ingest_status="queued",
        source_document_id=None,
    )
    document = SourceDocument(
        id=DOC_ID,
        project_id=PROJECT_ID,
        project="petersham",
        phase="brief-planning",
        document_class="drawing",
        filename="H-001-COVER-Layout1.pdf",
        relative_path="04-projects/petersham/_inbox/H-001-COVER-Layout1.pdf",
        normalized_content=(
            "HYDRAULIC SERVICES\n"
            "Hydraulic Services drawings issued by TDL Engineering Consulting Pty Ltd\n"
        ),
        document_metadata={
            "discipline": "Hydraulic",
            "issuing_firm": "TDL Engineering Consulting Pty Ltd",
            "confidence": "0.95",
            "basis": "filename",
            "subject": "none",
        },
    )

    session = AsyncMock()
    session.get = AsyncMock(side_effect=[record, document, document])
    session.commit = AsyncMock()

    with (
        patch(
            "app.workflows.document_ingest.download_project_file",
            return_value=b"%PDF",
        ),
        patch(
            "app.workflows.document_ingest.ingest_hosted_file",
            return_value=True,
        ),
        patch(
            "app.workflows.document_ingest.source_document_id_for_path",
            return_value=DOC_ID,
        ),
        patch(
            "app.workflows.document_ingest.safe_bootstrap_identity_from_document",
            new_callable=AsyncMock,
        ),
        patch(
            "app.workflows.document_ingest.file_single_document",
            new_callable=AsyncMock,
            return_value=(
                "04-projects/petersham/03-design/hydraulic/H-001 COVER.pdf"
            ),
        ) as file_mock,
        patch(
            "app.database.activity_events.record_activity_events",
            new_callable=AsyncMock,
        ),
        patch(
            "app.workflows.document_ingest.record_project_verb",
            new_callable=AsyncMock,
        ),
        patch(
            "app.workflows.document_ingest.maybe_record_document_revised",
            new_callable=AsyncMock,
        ),
    ):
        result = run_async(
            ingest_project_document(
                session,
                project=project,
                run_id=uuid.uuid4(),
                workspace_file_id=FILE_ID,
            )
        )

    assert result.ingest_status == "ingested"
    file_mock.assert_awaited_once()
    from app.projects.project_knowledge import list_shared_project_objects

    facts = list_shared_project_objects(project, kind="consultant")
    assert len(facts) == 1
    assert facts[0].value["firm"] == "TDL Engineering Consulting Pty Ltd"


def test_file_single_document_is_noop_when_not_in_inbox() -> None:
    from app.intake.sort_service import file_single_document

    project = _project()
    document = SourceDocument(
        id=DOC_ID,
        project_id=PROJECT_ID,
        project="petersham",
        phase="brief-planning",
        document_class="drawing",
        filename="H-001 COVER.pdf",
        relative_path="04-projects/petersham/03-design/hydraulic/H-001 COVER.pdf",
        normalized_content="x" * 200,
        document_metadata={"confidence": "0.92", "basis": "filename", "subject": "none"},
    )

    with patch(
        "app.intake.sort_service.sort_inbox_files", new_callable=AsyncMock
    ) as sort_mock:
        result = run_async(
            file_single_document(AsyncMock(), project=project, document=document)
        )

    assert result is None
    sort_mock.assert_not_awaited()


def test_file_single_document_skips_low_confidence() -> None:
    from app.intake.sort_service import file_single_document

    project = _project()
    document = SourceDocument(
        id=DOC_ID,
        project_id=PROJECT_ID,
        project="petersham",
        phase="brief-planning",
        document_class="unknown",
        filename="scan.pdf",
        relative_path="04-projects/petersham/_inbox/scan.pdf",
        normalized_content="x" * 200,
        document_metadata={"confidence": "0.40", "basis": "default", "subject": "none"},
    )

    with patch(
        "app.intake.sort_service.sort_inbox_files", new_callable=AsyncMock
    ) as sort_mock:
        result = run_async(
            file_single_document(AsyncMock(), project=project, document=document)
        )

    assert result is None
    sort_mock.assert_not_awaited()

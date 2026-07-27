import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.workflows.document_ingest import ingest_project_document
from tests.conftest import run_async


def test_document_ingest_leaves_file_in_inbox_until_sort_is_explicit() -> None:
    project_id = uuid.uuid4()
    workspace_file_id = uuid.uuid4()
    source_document_id = uuid.uuid4()
    workspace_path = "04-projects/demo/_inbox/brief.md"
    record = SimpleNamespace(
        id=workspace_file_id,
        project_id=project_id,
        filename="brief.md",
        workspace_path=workspace_path,
        storage_key="demo/_inbox/brief.md",
        ingest_status="queued",
        ingest_error=None,
        source_document_id=None,
    )
    source_document = SimpleNamespace(document_metadata={"revision": "P1"})
    session = AsyncMock()
    session.get = AsyncMock(side_effect=[record, source_document])
    project = SimpleNamespace(id=project_id, slug="demo", phase="procurement")

    async def _run() -> None:
        with (
            patch(
                "app.workflows.document_ingest.download_project_file",
                return_value=b"# Brief\n\nProject context.",
            ) as download,
            patch(
                "app.workflows.document_ingest.ingest_hosted_file", return_value=True
            ) as ingest,
            patch(
                "app.workflows.document_ingest.source_document_id_for_path",
                return_value=source_document_id,
            ),
            patch(
                "app.workflows.document_ingest.record_activity_events",
                new=AsyncMock(),
            ) as record_activity,
        ):
            result = await ingest_project_document(
                session,
                project=project,
                run_id=uuid.uuid4(),
                workspace_file_id=workspace_file_id,
                document_metadata={"split_from": "drawing-set.pdf", "sheet_index": 1},
            )

        download.assert_called_once_with(storage_key=record.storage_key)
        ingest.assert_called_once()
        assert ingest.call_args.kwargs["workspace_path"] == workspace_path
        assert record.workspace_path == workspace_path
        assert record.ingest_status == "ingested"
        assert record.source_document_id == source_document_id
        assert result.ingest_status == "ingested"
        assert source_document.document_metadata == {
            "revision": "P1",
            "split_from": "drawing-set.pdf",
            "sheet_index": 1,
        }
        record_activity.assert_awaited_once()

    run_async(_run())

import itertools
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
        content_hash="abc123",
    )
    source_document = SimpleNamespace(
        id=source_document_id,
        document_metadata={"revision": "P1"},
        normalized_content="",
        relative_path=workspace_path,
        document_class="report",
        filename="brief.md",
        content_hash="abc123",
        project_id=project_id,
    )
    session = AsyncMock()
    # The workspace-file record loads first; every subsequent session.get
    # (source-document lookups for metadata merge and identity bootstrap)
    # resolves to the same source document.
    session.get = AsyncMock(
        side_effect=itertools.chain([record], itertools.repeat(source_document))
    )
    # Auto-sort queries the inbox listing via session.execute(...).scalars().all();
    # an empty inbox listing means nothing moves, so the file stays put.
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=execute_result)
    project = SimpleNamespace(
        id=project_id,
        slug="demo",
        phase="procurement",
        workspace_path="04-projects/demo",
    )

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
            patch(
                "app.workflows.document_ingest.record_project_verb",
                new=AsyncMock(),
            ),
            patch(
                "app.workflows.document_ingest.maybe_record_document_revised",
                new=AsyncMock(),
            ),
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


def test_document_ingest_failure_does_not_persist_provider_error() -> None:
    project_id = uuid.uuid4()
    workspace_file_id = uuid.uuid4()
    provider_detail = "provider-document-secret-" + ("x" * 24)
    record = SimpleNamespace(
        id=workspace_file_id,
        project_id=project_id,
        filename="brief.pdf",
        workspace_path="04-projects/demo/_inbox/brief.pdf",
        storage_key="demo/_inbox/brief.pdf",
        ingest_status="queued",
        ingest_error=None,
        source_document_id=None,
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=record)
    project = SimpleNamespace(
        id=project_id,
        slug="demo",
        phase="procurement",
        workspace_path="04-projects/demo",
    )

    async def _run() -> None:
        with (
            patch(
                "app.workflows.document_ingest.download_project_file",
                side_effect=RuntimeError(provider_detail),
            ),
            patch(
                "app.workflows.document_ingest.record_activity_events",
                new=AsyncMock(),
            ) as record_activity,
        ):
            with pytest.raises(RuntimeError, match="provider-document-secret"):
                await ingest_project_document(
                    session,
                    project=project,
                    run_id=uuid.uuid4(),
                    workspace_file_id=workspace_file_id,
                )

        assert record.ingest_status == "failed"
        assert record.ingest_error == (
            "Document ingestion failed. Retry the file or contact support "
            "if it continues."
        )
        event = record_activity.await_args.kwargs["events"][-1]
        assert event.metadata["error_type"] == "RuntimeError"
        assert "error" not in event.metadata
        assert provider_detail not in str(event)

    run_async(_run())

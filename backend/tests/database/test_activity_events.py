import uuid
from types import SimpleNamespace

from app.database.activity_events import activity_run_status, record_activity_events
from app.schemas.projects import WorkflowTraceEvent
from tests.conftest import run_async


PROJECT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
RUN_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


class FakeSession:
    def __init__(self) -> None:
        self.rows = []
        self.flushed = False

    def add_all(self, rows) -> None:
        self.rows.extend(rows)

    async def flush(self) -> None:
        self.flushed = True


class BrokenSession:
    def add_all(self, rows) -> None:
        _ = rows
        raise RuntimeError("activity table unavailable")


def test_record_activity_events_adds_rows() -> None:
    session = FakeSession()

    run_async(
        record_activity_events(
            session,
            project_id=PROJECT_ID,
            source="document_ingest",
            run_id=RUN_ID,
            reference_type="workspace_file",
            reference_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            events=[
                WorkflowTraceEvent(
                    step="store",
                    status="complete",
                    message="Stored file.",
                    metadata={"filename": "quote.pdf"},
                ),
                WorkflowTraceEvent(
                    step="persist",
                    status="complete",
                    message="Persisted document.",
                    metadata={"chunk_count": 4},
                ),
            ],
        )
    )

    assert session.flushed is True
    assert len(session.rows) == 2
    assert session.rows[0].project_id == PROJECT_ID
    assert session.rows[0].source == "document_ingest"
    assert session.rows[0].event_metadata == {"filename": "quote.pdf"}
    assert session.rows[1].step == "persist"


def test_record_activity_events_swallows_failures() -> None:
    run_async(
        record_activity_events(
            BrokenSession(),
            project_id=PROJECT_ID,
            source="document_ingest",
            run_id=RUN_ID,
            events=[
                WorkflowTraceEvent(
                    step="store",
                    status="complete",
                    message="Stored file.",
                )
            ],
        )
    )


def test_activity_run_status_is_derived_from_latest_event() -> None:
    running = [
        SimpleNamespace(status="complete"),
        SimpleNamespace(status="running"),
    ]
    complete = [
        SimpleNamespace(status="running"),
        SimpleNamespace(status="complete"),
    ]
    failed = [
        SimpleNamespace(status="complete"),
        SimpleNamespace(status="failed"),
    ]

    assert activity_run_status(running) == "running"
    assert activity_run_status(complete) == "complete"
    assert activity_run_status(failed) == "failed"

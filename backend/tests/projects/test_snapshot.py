import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.database.project import Project
from app.database.project_decision import ProjectDecision
from app.auth.dependencies import CurrentUser
from app.api.projects import get_project_snapshot_view
from app.projects.snapshot import ProjectSnapshotNotFound, get_project_snapshot


PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
OWNER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


class _Result:
    def __init__(self, *, value=None, rows=None):
        self.value = value
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.rows


def _project() -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=OWNER_ID,
        slug="demo",
        title="Demo",
        workspace_path="04-projects/demo",
        phase="procurement",
        building_class="class-1",
        work_type="renovation",
        user_role="architect-pm",
        state="NSW",
        profile_revision=2,
        decision_set_revision=4,
        status="active",
        project_metadata={
            "taxonomy": {
                "site_address": "10 Test Street",
                "budget": "$1.2m",
            }
        },
    )


def _decision() -> ProjectDecision:
    return ProjectDecision(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        decision_id="procurement-route",
        section="Procurement",
        label="Procurement route",
        options=[{"value": "traditional", "label": "Traditional"}],
        selected="traditional",
        source="user",
        revision=3,
        locked=True,
        evidence_conflict=False,
        provenance={},
        workflow_type="create_pmp",
    )


def _session(*, content_hash: str = "abc") -> AsyncMock:
    evidence = SimpleNamespace(
        id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        relative_path="brief.md",
        content_hash=content_hash,
        document_metadata={},
        total_count=1,
    )
    failure = SimpleNamespace(
        workspace_path="inbox/broken.pdf",
        ingest_error="parse failed",
        total_count=1,
    )
    session = AsyncMock()
    session.execute.side_effect = [
        _Result(value=_project()),
        _Result(rows=[_decision()]),
        _Result(rows=[]),
        _Result(rows=[evidence]),
        _Result(rows=[failure]),
    ]
    return session


def test_snapshot_fingerprint_ignores_generation_time_and_exposes_missing_inputs() -> None:
    first_time = datetime(2026, 7, 19, 1, 0, tzinfo=UTC)
    first = asyncio.run(
        get_project_snapshot(
            _session(),
            project_id=PROJECT_ID,
            owner_user_id=OWNER_ID,
            generated_at=first_time,
        )
    )
    second = asyncio.run(
        get_project_snapshot(
            _session(),
            project_id=PROJECT_ID,
            owner_user_id=OWNER_ID,
            generated_at=first_time + timedelta(minutes=5),
        )
    )

    assert first.content_fingerprint == second.content_fingerprint
    assert first.generated_at != second.generated_at
    assert first.identity.client.status == "needs_input"
    assert first.confirmed_inputs["timeframe"].status == "needs_input"
    assert first.confirmed_inputs["procurement_route"].value == "traditional"
    assert first.evidence.active_count == 1
    assert first.evidence.ingest_failure_count == 1
    assert first.evidence.selection_status == "not_persisted"


def test_snapshot_fingerprint_changes_with_evidence_content() -> None:
    before = asyncio.run(
        get_project_snapshot(
            _session(content_hash="abc"),
            project_id=PROJECT_ID,
            owner_user_id=OWNER_ID,
        )
    )
    after = asyncio.run(
        get_project_snapshot(
            _session(content_hash="def"),
            project_id=PROJECT_ID,
            owner_user_id=OWNER_ID,
        )
    )
    assert before.evidence.fingerprint != after.evidence.fingerprint
    assert before.content_fingerprint != after.content_fingerprint


def test_snapshot_not_found_covers_cross_tenant_lookup() -> None:
    session = AsyncMock()
    session.execute.return_value = _Result(value=None)
    with pytest.raises(ProjectSnapshotNotFound):
        asyncio.run(
            get_project_snapshot(
                session,
                project_id=PROJECT_ID,
                owner_user_id=uuid.uuid4(),
            )
        )


def test_manual_snapshot_endpoint_uses_owner_scoped_reader() -> None:
    snapshot = asyncio.run(
        get_project_snapshot(
            _session(),
            project_id=PROJECT_ID,
            owner_user_id=OWNER_ID,
        )
    )
    read = AsyncMock(return_value=snapshot)
    user = CurrentUser(id=OWNER_ID, email="owner@example.com")

    with patch("app.api.projects.get_project_snapshot", new=read):
        result = asyncio.run(
            get_project_snapshot_view(
                project_id=PROJECT_ID,
                user=user,
                session=AsyncMock(),
            )
        )

    assert result.content_fingerprint == snapshot.content_fingerprint
    assert read.await_args.kwargs["owner_user_id"] == OWNER_ID

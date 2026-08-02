import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.database.procurement_request import ProcurementRequest
from app.procurement import requests as service
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


class _Result:
    def __init__(self, scalar=None, rows=None) -> None:
        self.scalar = scalar
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return self.rows


class _Session:
    def __init__(self, *results: _Result) -> None:
        self.results = list(results)
        self.added = []

    def add(self, value) -> None:
        self.added.append(value)

    async def execute(self, _statement):
        return self.results.pop(0)

    async def flush(self) -> None:
        return None

    async def refresh(self, _value) -> None:
        return None


def _request(**overrides) -> ProcurementRequest:
    values = {
        "id": uuid.uuid4(),
        "project_id": PROJECT_ID,
        "created_by_user_id": USER_ID,
        "kind": "trade_rfq",
        "target_name": "Electrical Services",
        "target_slug": "electrical_services",
        "status": "draft",
        "current_draft_artifact_id": None,
        "issued_at": None,
        "closed_at": None,
        "revision": 1,
        "created_at": datetime(2026, 8, 2, tzinfo=UTC),
        "updated_at": datetime(2026, 8, 2, tzinfo=UTC),
    }
    values.update(overrides)
    return ProcurementRequest(**values)


def _draft(**overrides):
    values = {
        "id": DRAFT_ID,
        "project_id": PROJECT_ID,
        "workflow_type": "trade_rfq_electrical_services",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_request_model_declares_lifecycle_and_project_indexes() -> None:
    constraints = {
        constraint.name for constraint in ProcurementRequest.__table__.constraints
    }
    indexes = {index.name for index in ProcurementRequest.__table__.indexes}

    assert {
        "ck_procurement_requests_kind",
        "ck_procurement_requests_status",
        "ck_procurement_requests_revision",
    } <= constraints
    assert {
        "ix_procurement_requests_project_updated",
        "ix_procurement_requests_project_status",
        "ix_procurement_requests_current_draft",
    } <= indexes


def test_migration_has_fks_rls_and_authenticated_grants() -> None:
    source = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "038_procurement_requests.py"
    ).read_text(encoding="utf-8")

    assert 'ForeignKey("projects.id", ondelete="CASCADE")' in source
    assert 'ForeignKey("users.id", ondelete="RESTRICT")' in source
    assert 'ForeignKey("draft_artifacts.id", ondelete="RESTRICT")' in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "procurement_requests_owner_policy" in source
    assert (
        "GRANT SELECT, INSERT, UPDATE ON procurement_requests TO authenticated"
        in source
    )


def test_create_normalises_target_and_starts_at_draft_revision_one() -> None:
    session = _Session()

    request = run_async(
        service.create_procurement_request(
            session,
            project_id=PROJECT_ID,
            created_by_user_id=USER_ID,
            kind="trade_rfq",
            target_name="  Electrical   Services ",
        )
    )

    assert request.target_name == "Electrical Services"
    assert request.target_slug == "electrical_services"
    assert request.status == "draft"
    assert request.revision == 1
    assert session.added == [request]


def test_request_status_transitions_record_issue_and_close_times() -> None:
    session = _Session()
    request = _request()

    issued = run_async(
        service.transition_procurement_request(
            session, request=request, status="issued", expected_revision=1
        )
    )
    closed = run_async(
        service.transition_procurement_request(
            session, request=issued, status="closed", expected_revision=2
        )
    )

    assert issued.issued_at is not None
    assert closed.closed_at is not None
    assert closed.revision == 3


@pytest.mark.parametrize(
    ("current", "next_status"),
    [("draft", "closed"), ("issued", "draft"), ("closed", "cancelled")],
)
def test_request_rejects_invalid_status_transitions(current, next_status) -> None:
    with pytest.raises(service.ProcurementRequestStateConflict):
        run_async(
            service.transition_procurement_request(
                _Session(),
                request=_request(status=current),
                status=next_status,
                expected_revision=1,
            )
        )


def test_request_rejects_stale_revision() -> None:
    with pytest.raises(service.ProcurementRequestRevisionConflict):
        run_async(
            service.transition_procurement_request(
                _Session(),
                request=_request(revision=3),
                status="issued",
                expected_revision=2,
            )
        )


def test_attach_rejects_a_draft_from_another_project() -> None:
    with pytest.raises(
        service.ProcurementRequestDraftConflict, match="does not belong"
    ):
        run_async(
            service.attach_current_draft(
                _Session(),
                request=_request(),
                draft=_draft(project_id=uuid.uuid4()),
            )
        )


def test_attach_generated_draft_reuses_matching_open_request() -> None:
    request = _request()
    session = _Session(_Result(request))

    attached = run_async(
        service.attach_generated_draft(
            session,
            project_id=PROJECT_ID,
            created_by_user_id=USER_ID,
            draft=_draft(),
            target_name="Electrical Services",
            kind="trade_rfq",
        )
    )

    assert attached is request
    assert request.current_draft_artifact_id == DRAFT_ID
    assert request.revision == 2


def test_attach_generated_draft_creates_one_when_no_open_request_exists() -> None:
    session = _Session(_Result())

    request = run_async(
        service.attach_generated_draft(
            session,
            project_id=PROJECT_ID,
            created_by_user_id=USER_ID,
            draft=_draft(),
            target_name="Electrical Services",
            kind="trade_rfq",
        )
    )

    assert request.current_draft_artifact_id == DRAFT_ID
    assert request.revision == 2
    assert session.added == [request]


def test_list_returns_current_request_rows_in_service_order() -> None:
    latest = _request(target_name="Electrical", target_slug="electrical")
    older = _request(target_name="Hydraulic", target_slug="hydraulic")
    session = _Session(_Result(rows=[latest, older]))

    rows = run_async(service.list_procurement_requests(session, project_id=PROJECT_ID))

    assert rows == [latest, older]

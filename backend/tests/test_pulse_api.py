"""Project-scoped Pulse feed and dismiss API (X1 Stage 14.3)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.project import Project
from app.database.session import get_db
from app.main import fastapi_app as app
from app.projects.pulse import PulseFeed, PulseItem

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER = uuid.UUID("22222222-2222-2222-2222-222222222222")
PROJECT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
INVOICE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def _project(*, owner: uuid.UUID = USER_ID) -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=owner,
        slug="demo",
        title="Demo Project",
        workspace_path="04-projects/demo",
        phase="procurement",
        archetype="small-commercial",
        user_role="architect-pm",
        state="NSW",
        status="active",
        project_metadata={},
    )


def _feed(*items: PulseItem) -> PulseFeed:
    return PulseFeed(
        attention=list(items),
        other=[],
        attention_count=len(items),
        generated_at=NOW,
        since=NOW,
    )


def _invoice_card(*, review_state: str = "ready_for_review") -> PulseItem:
    return PulseItem(
        id=f"invoice_review_required:cost_invoice:{INVOICE_ID}:{review_state}",
        kind="attention",
        signal_type="invoice_review_required",
        title="Builder invoice 009 needs review",
        body="Builder invoice 009 needs review",
        domain="COMMERCIAL",
        evidence=[],
        actions=["review_invoice", "dismiss"],
        created_at=NOW,
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def client(mock_session: AsyncMock) -> TestClient:
    current_user = CurrentUser(id=USER_ID, email="user@example.com")

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_pulse_on_another_project_returns_404(client: TestClient) -> None:
    with (
        patch("app.api.pulse.get_project", new=AsyncMock(return_value=_project(owner=OTHER_USER))),
        patch("app.api.pulse.require_active_entitlement", new=AsyncMock()),
        patch("app.api.pulse.build_pulse_feed", new=AsyncMock()) as build,
    ):
        response = client.get(f"/projects/{PROJECT_ID}/pulse")

    assert response.status_code == 404
    assert response.status_code != 403
    build.assert_not_called()


def test_dismiss_is_idempotent_and_drops_the_card(client: TestClient) -> None:
    card = _invoice_card()
    with (
        patch("app.api.pulse.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.pulse.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.pulse.record_project_verb",
            new=AsyncMock(side_effect=[object(), None]),
        ) as record,
        patch(
            "app.api.pulse.build_pulse_feed",
            new=AsyncMock(side_effect=[_feed(), _feed()]),
        ),
    ):
        first = client.post(
            f"/projects/{PROJECT_ID}/pulse/dismiss",
            json={"subject_key": card.id},
        )
        second = client.post(
            f"/projects/{PROJECT_ID}/pulse/dismiss",
            json={"subject_key": card.id},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["attention"] == []
    assert second.json()["attention"] == []
    assert record.call_count == 2
    assert record.call_args.kwargs["deduplication_key"] == (
        f"project_signal.dismissed:pulse:{card.id}"
    )


def test_dismiss_does_not_change_invoice_review_state(client: TestClient) -> None:
    card = _invoice_card()
    with (
        patch("app.api.pulse.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.pulse.require_active_entitlement", new=AsyncMock()),
        patch("app.api.pulse.record_project_verb", new=AsyncMock()),
        patch("app.api.pulse.build_pulse_feed", new=AsyncMock(return_value=_feed())),
        patch("app.cost_plan.invoice_service.decide_invoice") as decide,
        patch("app.cost_plan.invoice_service.transition_review_state") as transition,
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/pulse/dismiss",
            json={"subject_key": card.id},
        )

    assert response.status_code == 200
    decide.assert_not_called()
    transition.assert_not_called()


def test_dismiss_unknown_signal_type_returns_422(client: TestClient) -> None:
    with (
        patch("app.api.pulse.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.pulse.require_active_entitlement", new=AsyncMock()),
        patch("app.api.pulse.record_project_verb", new=AsyncMock()) as record,
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/pulse/dismiss",
            json={"subject_key": "programme_risk:source_document:abc"},
        )

    assert response.status_code == 422
    record.assert_not_called()


def test_dismiss_subject_key_is_in_the_body_not_the_path(client: TestClient) -> None:
    card = _invoice_card()
    with (
        patch("app.api.pulse.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.pulse.require_active_entitlement", new=AsyncMock()),
        patch("app.api.pulse.record_project_verb", new=AsyncMock()),
        patch("app.api.pulse.build_pulse_feed", new=AsyncMock(return_value=_feed())),
    ):
        missing = client.post(f"/projects/{PROJECT_ID}/pulse/{card.id}/dismiss")
        ok = client.post(
            f"/projects/{PROJECT_ID}/pulse/dismiss",
            json={"subject_key": card.id},
        )

    assert missing.status_code == 404
    assert ok.status_code == 200


def test_pulse_since_query_is_passed_to_builder(client: TestClient) -> None:
    since = datetime(2026, 8, 18, 0, 0, tzinfo=UTC)
    with (
        patch("app.api.pulse.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.pulse.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.pulse.build_pulse_feed",
            new=AsyncMock(return_value=_feed()),
        ) as build,
    ):
        response = client.get(
            f"/projects/{PROJECT_ID}/pulse",
            params={"since": since.isoformat()},
        )

    assert response.status_code == 200
    build.assert_called_once()
    assert build.call_args.kwargs["since"] == since

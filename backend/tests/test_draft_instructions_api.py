import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.database.session import get_db
from app.main import fastapi_app as app
from app.projects.artefact_revisions import ArtefactRevisionConflict
from app.projects.draft_instructions_service import (
    AllInstructionsFailedError,
    ApplyResult,
    FailedInstruction,
    StaleAnchorError,
)

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
NOW = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)

ENDPOINT = f"/projects/{PROJECT_ID}/drafts/{DRAFT_ID}/apply-instructions"

BODY = {
    "expected_base_version": 3,
    "instructions": [
        {
            "anchor_start": 40,
            "anchor_end": 66,
            "quoted_text": "single-stage invited tender",
            "instruction": "make it two-stage",
        }
    ],
}


def _project(owner_id: uuid.UUID = USER_ID) -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=owner_id,
        slug="chen-residence",
        title="Chen Residence",
        workspace_path="04-projects/chen-residence",
        phase="brief-planning",
        archetype="new-dwelling",
        user_role="architect-pm",
        state="NSW",
        status="active",
        project_metadata=None,
        created_at=NOW,
        updated_at=NOW,
    )


def _draft(version: int = 4) -> DraftArtifact:
    return DraftArtifact(
        id=DRAFT_ID,
        project_id=PROJECT_ID,
        workflow_type="create_pmp",
        version=version,
        status="draft",
        title="Project Management Plan",
        workspace_path="04-projects/chen-residence/00-brief-pmp/PMP.md",
        author_user_id=USER_ID,
        content_markdown="# Project Management Plan\n\n## Procurement posture\n\nBody.\n",
        model="gpt-5.6",
        runtime="clerk-sitewise",
        provenance_metadata={"changed_ranges": [{"start": 10, "end": 20}]},
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


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


@pytest.fixture(autouse=True)
def _stub_common(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.api.projects.get_project", AsyncMock(return_value=_project())
    )
    monkeypatch.setattr(
        "app.api.projects.require_active_entitlement", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.api.projects.get_draft_artifact", AsyncMock(return_value=_draft())
    )


def _stub_apply(monkeypatch: pytest.MonkeyPatch, mock: AsyncMock) -> None:
    monkeypatch.setattr("app.api.projects.apply_draft_instructions", mock)


def test_apply_instructions_returns_the_new_version(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_apply(
        monkeypatch,
        AsyncMock(
            return_value=ApplyResult(revision=_draft(version=4), applied_count=1, failed=[])
        ),
    )

    response = client.post(ENDPOINT, json=BODY)

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft"]["version"] == 4
    assert payload["applied_count"] == 1
    assert payload["failed"] == []


def test_apply_instructions_reports_partial_failures(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_apply(
        monkeypatch,
        AsyncMock(
            return_value=ApplyResult(
                revision=_draft(),
                applied_count=1,
                failed=[FailedInstruction(index=0, reason="selection is outside any section")],
            )
        ),
    )

    response = client.post(ENDPOINT, json=BODY)

    assert response.status_code == 200
    assert response.json()["failed"] == [
        {"index": 0, "reason": "selection is outside any section"}
    ]


def test_apply_instructions_rejects_a_draft_from_another_project(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    foreign = _draft()
    foreign.project_id = uuid.uuid4()
    monkeypatch.setattr(
        "app.api.projects.get_draft_artifact", AsyncMock(return_value=foreign)
    )
    apply_mock = AsyncMock()
    _stub_apply(monkeypatch, apply_mock)

    response = client.post(ENDPOINT, json=BODY)

    assert response.status_code == 404
    apply_mock.assert_not_awaited()


def test_apply_instructions_rejects_a_project_owned_by_another_user(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_require_project_owner` answers 403 for a foreign project, 404 for a missing one."""
    monkeypatch.setattr(
        "app.api.projects.get_project", AsyncMock(return_value=_project(OTHER_USER_ID))
    )
    apply_mock = AsyncMock()
    _stub_apply(monkeypatch, apply_mock)

    response = client.post(ENDPOINT, json=BODY)

    assert response.status_code == 403
    apply_mock.assert_not_awaited()


def test_apply_instructions_missing_project_is_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.projects.get_project", AsyncMock(return_value=None))
    apply_mock = AsyncMock()
    _stub_apply(monkeypatch, apply_mock)

    assert client.post(ENDPOINT, json=BODY).status_code == 404
    apply_mock.assert_not_awaited()


def test_apply_instructions_missing_draft_is_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.projects.get_draft_artifact", AsyncMock(return_value=None))
    _stub_apply(monkeypatch, AsyncMock())

    assert client.post(ENDPOINT, json=BODY).status_code == 404


def test_stale_anchor_is_409(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_apply(
        monkeypatch,
        AsyncMock(side_effect=StaleAnchorError("Instruction 1 no longer matches the draft")),
    )

    response = client.post(ENDPOINT, json=BODY)

    assert response.status_code == 409
    assert "no longer matches" in response.json()["detail"]


def test_revision_conflict_is_409_and_names_the_current_version(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_apply(
        monkeypatch,
        AsyncMock(
            side_effect=ArtefactRevisionConflict(
                "Expected create_pmp v3, current version is v5"
            )
        ),
    )

    response = client.post(ENDPOINT, json=BODY)

    assert response.status_code == 409
    assert "v5" in response.json()["detail"]


def test_all_instructions_failed_is_422(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_apply(
        monkeypatch,
        AsyncMock(
            side_effect=AllInstructionsFailedError(
                [FailedInstruction(index=0, reason="heading line was modified")]
            )
        ),
    )

    response = client.post(ENDPOINT, json=BODY)

    assert response.status_code == 422
    assert "heading line was modified" in response.json()["detail"]


def test_too_many_instructions_is_rejected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    apply_mock = AsyncMock()
    _stub_apply(monkeypatch, apply_mock)
    body = {
        "expected_base_version": 3,
        "instructions": [BODY["instructions"][0]] * 21,
    }

    assert client.post(ENDPOINT, json=body).status_code == 422
    apply_mock.assert_not_awaited()


def test_empty_instruction_list_is_rejected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    apply_mock = AsyncMock()
    _stub_apply(monkeypatch, apply_mock)

    response = client.post(
        ENDPOINT, json={"expected_base_version": 3, "instructions": []}
    )

    assert response.status_code == 422
    apply_mock.assert_not_awaited()


def test_unexpected_error_returns_a_diagnosable_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bare 500 with no detail renders as 'Request failed with status 500'."""
    _stub_apply(monkeypatch, AsyncMock(side_effect=RuntimeError("boom")))

    response = client.post(ENDPOINT, json=BODY)

    assert response.status_code == 500
    assert response.json()["detail"] == "Could not apply changes: RuntimeError: boom"


def test_response_serialization_error_returns_a_diagnosable_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Response validation belongs inside the endpoint's protected boundary."""
    invalid_revision = _draft()
    invalid_revision.updated_at = None
    _stub_apply(
        monkeypatch,
        AsyncMock(
            return_value=ApplyResult(
                revision=invalid_revision,
                applied_count=1,
                failed=[],
            )
        ),
    )

    response = client.post(ENDPOINT, json=BODY)

    assert response.status_code == 500
    assert "ValidationError" in response.json()["detail"]

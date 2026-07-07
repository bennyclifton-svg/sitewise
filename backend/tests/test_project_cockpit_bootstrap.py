import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.project import Project
from app.database.session import get_db
from app.main import fastapi_app as app
from app.schemas.projects import EvidencePreview, PlatformKnowledgeStatus

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
EVIDENCE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
NOW = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)


def _project() -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="demo",
        title="Demo Project",
        workspace_path="04-projects/demo",
        phase="procurement",
        archetype="small-commercial",
        user_role="architect-pm",
        state="NSW",
        status="active",
        project_metadata={},
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


def _draft_summary() -> dict:
    return {
        "id": DRAFT_ID,
        "project_id": PROJECT_ID,
        "workflow_type": "create_pmp",
        "version": 7,
        "status": "draft",
        "title": "PMP Draft",
        "workspace_path": "04-projects/demo/00-brief-pmp/PMP.md",
        "author_user_id": USER_ID,
        "model": "gpt-4o-mini",
        "runtime": "clerk-sitewise",
        "created_at": NOW,
        "updated_at": NOW,
    }


@contextmanager
def _consultant_procurement_bootstrap_patches():
    with (
        patch(
            "app.api.projects.get_latest_consultant_procurement_draft_summaries",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "app.api.projects._ensure_consultant_procurement_workspace_files",
            new=AsyncMock(
                side_effect=lambda _session, *, project, workspace_files, consultant_draft_summaries: workspace_files
            ),
        ),
    ):
        yield


def test_cockpit_bootstrap_returns_lightweight_first_paint_payload(
    client: TestClient,
) -> None:
    evidence = EvidencePreview(
        id=EVIDENCE_ID,
        title="Architect Engagement",
        filename="engagement.md",
        relative_path="04-projects/demo/02-consultant/architect/engagement.md",
        source_type="project_evidence",
        document_class="project_evidence",
        excerpt="Architect engagement excerpt.",
    )

    with (
        patch("app.api.projects.ensure_user_exists", new=AsyncMock()),
        patch("app.api.projects.ensure_default_project_catalog", new=AsyncMock()),
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.list_projects", new=AsyncMock(return_value=[_project()])),
        patch(
            "app.api.projects.list_workspace_files_for_project",
            new=AsyncMock(
                return_value=[
                    SimpleNamespace(
                        workspace_path="04-projects/demo/02-consultant/architect/engagement.md"
                    )
                ]
            ),
        ),
        patch("app.api.projects._list_project_evidence_previews", new=AsyncMock(return_value=[evidence])),
        patch(
            "app.api.projects._platform_knowledge_status",
            new=AsyncMock(return_value=PlatformKnowledgeStatus(available=False, buckets=[])),
        ),
        patch(
            "app.api.projects.get_latest_draft_artifact_summaries",
            new=AsyncMock(return_value={"create_pmp": _draft_summary()}),
        ),
        patch(
            "app.api.projects._ensure_pmp_workspace_file",
            new=AsyncMock(side_effect=lambda _session, *, project, workspace_files, draft_summaries: workspace_files),
        ),
        patch(
            "app.api.projects._ensure_cost_plan_workspace_file",
            new=AsyncMock(side_effect=lambda _session, *, project, workspace_files, draft_summaries: workspace_files),
        ),
        _consultant_procurement_bootstrap_patches(),
    ):
        response = client.get(f"/projects/{PROJECT_ID}/cockpit-bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["id"] == str(PROJECT_ID)
    assert payload["projects"][0]["id"] == str(PROJECT_ID)
    assert payload["workspace_tree"]["tree"]
    assert payload["evidence"][0]["id"] == str(EVIDENCE_ID)
    assert payload["evidence"][0]["content"] is None
    assert payload["latest_drafts"]["create_pmp"]["id"] == str(DRAFT_ID)
    assert "content_markdown" not in payload["latest_drafts"]["create_pmp"]
    assert "provenance_metadata" not in payload["latest_drafts"]["create_pmp"]
    assert payload["latest_drafts"]["create_cost_plan"] is None
    assert payload["latest_drafts"]["sort_files"] is None
    assert "total" in payload["timings_ms"]


def test_cockpit_bootstrap_includes_canonical_pmp_path_for_legacy_draft(
    client: TestClient,
) -> None:
    legacy_draft = {
        **_draft_summary(),
        "workspace_path": "04-projects/demo/00-brief-pmp/PMP-draft-v07.md",
    }

    with (
        patch("app.api.projects.ensure_user_exists", new=AsyncMock()),
        patch("app.api.projects.ensure_default_project_catalog", new=AsyncMock()),
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.list_projects", new=AsyncMock(return_value=[_project()])),
        patch(
            "app.api.projects.list_workspace_files_for_project",
            new=AsyncMock(return_value=[]),
        ),
        patch("app.api.projects._list_project_evidence_previews", new=AsyncMock(return_value=[])),
        patch(
            "app.api.projects._platform_knowledge_status",
            new=AsyncMock(return_value=PlatformKnowledgeStatus(available=False, buckets=[])),
        ),
        patch(
            "app.api.projects.get_latest_draft_artifact_summaries",
            new=AsyncMock(return_value={"create_pmp": legacy_draft}),
        ),
        patch(
            "app.api.projects._ensure_pmp_workspace_file",
            new=AsyncMock(side_effect=lambda _session, *, project, workspace_files, draft_summaries: workspace_files),
        ),
        patch(
            "app.api.projects._ensure_cost_plan_workspace_file",
            new=AsyncMock(side_effect=lambda _session, *, project, workspace_files, draft_summaries: workspace_files),
        ),
        _consultant_procurement_bootstrap_patches(),
    ):
        response = client.get(f"/projects/{PROJECT_ID}/cockpit-bootstrap")

    assert response.status_code == 200
    tree = response.json()["workspace_tree"]["tree"]
    brief_node = next(node for node in tree if node["name"] == "00-brief-pmp")
    file_names = [child["name"] for child in brief_node["children"] if child["kind"] == "file"]
    assert "PMP.md" in file_names


def test_cockpit_bootstrap_includes_cost_plan_markdown_for_existing_draft(
    client: TestClient,
) -> None:
    cost_plan_draft = {
        **_draft_summary(),
        "workflow_type": "create_cost_plan",
        "title": "Cost Plan Draft",
        "workspace_path": "04-projects/demo/01-cost/cost_plan_v01.md",
        "version": 1,
    }

    with (
        patch("app.api.projects.ensure_user_exists", new=AsyncMock()),
        patch("app.api.projects.ensure_default_project_catalog", new=AsyncMock()),
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.list_projects", new=AsyncMock(return_value=[_project()])),
        patch(
            "app.api.projects.list_workspace_files_for_project",
            new=AsyncMock(
                return_value=[
                    SimpleNamespace(
                        workspace_path="04-projects/demo/01-cost/Cost_Plan_v01.draft.xlsx"
                    )
                ]
            ),
        ),
        patch("app.api.projects._list_project_evidence_previews", new=AsyncMock(return_value=[])),
        patch(
            "app.api.projects._platform_knowledge_status",
            new=AsyncMock(return_value=PlatformKnowledgeStatus(available=False, buckets=[])),
        ),
        patch(
            "app.api.projects.get_latest_draft_artifact_summaries",
            new=AsyncMock(return_value={"create_cost_plan": cost_plan_draft}),
        ),
        patch(
            "app.api.projects._ensure_pmp_workspace_file",
            new=AsyncMock(side_effect=lambda _session, *, project, workspace_files, draft_summaries: workspace_files),
        ),
        patch(
            "app.api.projects._ensure_cost_plan_workspace_file",
            new=AsyncMock(side_effect=lambda _session, *, project, workspace_files, draft_summaries: workspace_files),
        ),
        _consultant_procurement_bootstrap_patches(),
    ):
        response = client.get(f"/projects/{PROJECT_ID}/cockpit-bootstrap")

    assert response.status_code == 200
    tree = response.json()["workspace_tree"]["tree"]
    cost_node = next(node for node in tree if node["name"] == "01-cost")
    file_names = [child["name"] for child in cost_node["children"] if child["kind"] == "file"]
    assert "cost_plan_v01.md" in file_names
    assert "Cost_Plan_v01.draft.xlsx" in file_names


def test_cockpit_bootstrap_includes_consultant_procurement_drafts(
    client: TestClient,
) -> None:
    consultant_draft_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    consultant_draft = {
        "id": consultant_draft_id,
        "project_id": PROJECT_ID,
        "workflow_type": "consultant_procurement_structural_engineer",
        "version": 1,
        "status": "draft",
        "title": "Request for Fee Proposal - Structural engineer",
        "workspace_path": (
            "04-projects/demo/02-consultant/"
            "consultant_procurement_structural_engineer_v01.draft.md"
        ),
        "author_user_id": USER_ID,
        "model": None,
        "runtime": "clerk-consultant-procurement",
        "created_at": NOW,
        "updated_at": NOW,
    }

    with (
        patch("app.api.projects.ensure_user_exists", new=AsyncMock()),
        patch("app.api.projects.ensure_default_project_catalog", new=AsyncMock()),
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.list_projects", new=AsyncMock(return_value=[_project()])),
        patch(
            "app.api.projects.list_workspace_files_for_project",
            new=AsyncMock(return_value=[]),
        ),
        patch("app.api.projects._list_project_evidence_previews", new=AsyncMock(return_value=[])),
        patch(
            "app.api.projects._platform_knowledge_status",
            new=AsyncMock(return_value=PlatformKnowledgeStatus(available=False, buckets=[])),
        ),
        patch(
            "app.api.projects.get_latest_draft_artifact_summaries",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "app.api.projects.get_latest_consultant_procurement_draft_summaries",
            new=AsyncMock(
                return_value={"consultant_procurement_structural_engineer": consultant_draft}
            ),
        ),
        patch(
            "app.api.projects._ensure_pmp_workspace_file",
            new=AsyncMock(side_effect=lambda _session, *, project, workspace_files, draft_summaries: workspace_files),
        ),
        patch(
            "app.api.projects._ensure_cost_plan_workspace_file",
            new=AsyncMock(side_effect=lambda _session, *, project, workspace_files, draft_summaries: workspace_files),
        ),
        patch(
            "app.api.projects._ensure_consultant_procurement_workspace_files",
            new=AsyncMock(side_effect=lambda _session, *, project, workspace_files, consultant_draft_summaries: workspace_files),
        ),
    ):
        response = client.get(f"/projects/{PROJECT_ID}/cockpit-bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["latest_drafts"]["consultant_procurement_structural_engineer"]["id"] == str(
        consultant_draft_id
    )
    tree = payload["workspace_tree"]["tree"]
    consultant_node = next(node for node in tree if node["name"] == "02-consultant")
    file_names = [child["name"] for child in consultant_node["children"] if child["kind"] == "file"]
    assert "consultant_procurement_structural_engineer_v01.draft.md" in file_names


def test_project_activity_returns_grouped_runs(
    client: TestClient,
    mock_session: AsyncMock,
) -> None:
    run_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    event_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    draft_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    run = SimpleNamespace(
        run_id=run_id,
        source="document_ingest",
        reference_type="draft_artifact",
        reference_id=draft_id,
        status="complete",
        created_at=NOW,
        updated_at=NOW,
        events=[
            SimpleNamespace(
                id=event_id,
                step="store",
                status="complete",
                message="Stored file in the project workspace.",
                event_metadata={"filename": "quote.pdf"},
                created_at=NOW,
            )
        ],
    )
    mock_session.execute.return_value = SimpleNamespace(
        all=lambda: [
            SimpleNamespace(
                id=draft_id,
                provenance_metadata={
                    "seed_consulted": [" seed/setup-and-commission-guide.md "],
                    "evidence_refs": ["project_evidence:demo/brief.pdf#chunk=1"],
                    "context_refs": ["doctrine:docs/clerk-brief.md"],
                },
            )
        ]
    )

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch(
            "app.api.projects.list_project_activity_runs",
            new=AsyncMock(return_value=[run]),
        ),
    ):
        response = client.get(f"/projects/{PROJECT_ID}/activity")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runs"][0]["run_id"] == str(run_id)
    assert payload["runs"][0]["source"] == "document_ingest"
    assert payload["runs"][0]["events"][0]["metadata"] == {"filename": "quote.pdf"}
    assert payload["runs"][0]["references"] == {
        "seed_consulted": ["seed/setup-and-commission-guide.md"],
        "evidence_refs": ["project_evidence:demo/brief.pdf#chunk=1"],
        "context_refs": ["doctrine:docs/clerk-brief.md"],
    }
    assert payload["newest_created_at"] == NOW.isoformat().replace("+00:00", "Z")


def test_project_activity_delete_removes_selected_runs(client: TestClient) -> None:
    run_ids = [
        uuid.UUID("99999999-9999-9999-9999-999999999999"),
        uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
    ]
    delete_runs = AsyncMock(return_value=5)

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.delete_project_activity_runs", new=delete_runs),
    ):
        response = client.request(
            "DELETE",
            f"/projects/{PROJECT_ID}/activity",
            json={"run_ids": [str(run_id) for run_id in run_ids]},
        )

    assert response.status_code == 200
    assert response.json() == {"deleted": 5}
    delete_runs.assert_awaited_once_with(
        ANY,
        project_id=PROJECT_ID,
        run_ids=run_ids,
    )

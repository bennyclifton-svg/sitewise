import re
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.workflows import procurement_request as engine
from app.workflows.contractor_procurement import draft_contractor_eoi_artifact
from tests.conftest import run_async
from tests.workflows.test_consultant_procurement import (
    DRAFT_ID,
    USER_ID,
    _Session,
    _StubRetriever,
    _passage,
    _project,
)


def _install(monkeypatch, *, retriever: _StubRetriever, version: int = 1) -> None:
    monkeypatch.setattr(engine, "DocumentRetriever", lambda session: retriever)
    monkeypatch.setattr(
        engine,
        "next_draft_version",
        AsyncMock(return_value=version),
    )

    async def _create_draft(session, **kwargs):
        match = re.search(r"_v(\d+)\.draft\.md$", kwargs["workspace_path"])
        draft_version = int(match.group(1)) if match else version
        return SimpleNamespace(
            id=DRAFT_ID,
            project_id=kwargs["project_id"],
            workflow_type=kwargs["workflow_type"],
            version=draft_version,
            status="draft",
            title=kwargs["title"],
            workspace_path=kwargs["workspace_path"],
            author_user_id=kwargs["author_user_id"],
            content_markdown=kwargs["content_markdown"],
            model=kwargs["model"],
            runtime=kwargs["runtime"],
            provenance_metadata=kwargs["provenance_metadata"],
        )

    monkeypatch.setattr(
        engine,
        "create_draft_artifact",
        AsyncMock(side_effect=_create_draft),
    )
    monkeypatch.setattr(
        engine,
        "_sync_draft_workspace",
        AsyncMock(side_effect=lambda session, **kwargs: kwargs["draft"].workspace_path),
    )


def test_eoi_is_unpriced_and_not_an_offer(monkeypatch) -> None:
    _install(monkeypatch, retriever=_StubRetriever())

    result = run_async(
        draft_contractor_eoi_artifact(
            _Session(),
            project=_project(),
            user_id=USER_ID,
            package="Main Works",
        )
    )

    markdown = result.draft.content_markdown
    assert result.draft.title == "Expression of Interest - Main Works"
    assert result.draft.workflow_type == "contractor_eoi_main_works"
    assert result.draft.workspace_path.endswith(
        "/02-procurement/contractor_eoi_main_works_v01.draft.md"
    )
    for banned in ("fee proposal", "lump-sum fee", "hourly rate", "disbursement"):
        assert banned not in markdown.lower()
    assert "Expression of Interest" in markdown
    assert "not an offer" in markdown.lower() or "client is not bound" in markdown.lower()
    assert "returnable" in markdown.lower() or "company profile" in markdown.lower()


def test_eoi_never_renders_a_budget_figure(monkeypatch) -> None:
    retriever = _StubRetriever(
        project_passages={
            "project brief": [
                _passage(
                    filename="cost-plan.md",
                    path="04-projects/walsh-renovation/01-cost/cost-plan.md",
                    content="Current construction budget is $920,000.",
                )
            ]
        }
    )
    _install(monkeypatch, retriever=retriever)

    result = run_async(
        draft_contractor_eoi_artifact(
            _Session(),
            project=_project(),
            user_id=USER_ID,
            package="Main Works",
        )
    )

    assert "$" not in result.draft.content_markdown
    assert "TBC by client" in result.draft.content_markdown


def test_eoi_includes_required_head_contractor_guidance(monkeypatch) -> None:
    _install(monkeypatch, retriever=_StubRetriever())
    project = _project()
    project.archetype = "renovation"
    project.building_class = "residential"
    project.work_type = "refurb"
    project.user_role = "architect-pm"

    result = run_async(
        draft_contractor_eoi_artifact(
            _Session(),
            project=project,
            user_id=USER_ID,
        )
    )

    assert "Platform guidance: none found" not in result.draft.content_markdown
    assert any(
        item["path"] == "seed/as-standards-reference.md"
        for item in result.source_trace["platform_knowledge"]
    )

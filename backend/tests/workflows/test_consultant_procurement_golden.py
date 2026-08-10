from pathlib import Path
from types import SimpleNamespace

from tests.workflows.test_consultant_procurement import (
    _Session,
    _StubRetriever,
    _cost_plan_markdown,
    _install,
    _passage,
    _run,
)

FIXTURE = Path(__file__).parent / "fixtures" / "consultant_rfp_structural_v01.md"
TOWN_PLANNER_FIXTURE = (
    Path(__file__).parent / "fixtures" / "consultant_rfp_town_planner_v01.md"
)


def _deterministic_retriever() -> _StubRetriever:
    return _StubRetriever(
        project_passages={
            "project brief": [
                _passage(
                    filename="project-brief.pdf",
                    path="04-projects/walsh-renovation/00-brief/project-brief.pdf",
                    content="Owner wants a two-storey renovation.",
                )
            ],
        },
    )


def test_consultant_rfp_matches_golden(monkeypatch) -> None:
    retriever = _deterministic_retriever()
    cost_plan = SimpleNamespace(
        workspace_path="04-projects/walsh-renovation/01-cost/cost_plan_v01.md",
        content_markdown=_cost_plan_markdown(),
    )
    _install(monkeypatch, retriever=retriever, cost_plan=cost_plan)
    result = _run(session=_Session(), discipline="structural engineer")

    if not FIXTURE.exists():
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(result.draft.content_markdown, encoding="utf-8")

    assert result.draft.content_markdown == FIXTURE.read_text(encoding="utf-8")
    assert result.draft.workflow_type == "consultant_procurement_structural_engineer"
    assert result.draft.title == "Request for Proposal - Structural engineer"


def test_town_planner_rfp_matches_golden(monkeypatch) -> None:
    retriever = _deterministic_retriever()
    cost_plan = SimpleNamespace(
        workspace_path="04-projects/walsh-renovation/01-cost/cost_plan_v01.md",
        content_markdown=_cost_plan_markdown(),
    )
    _install(monkeypatch, retriever=retriever, cost_plan=cost_plan)
    result = _run(session=_Session(), discipline="town planner")

    assert result.draft.content_markdown == TOWN_PLANNER_FIXTURE.read_text(
        encoding="utf-8"
    )
    assert result.draft.workflow_type == "consultant_procurement_town_planner"
    assert result.draft.title == "Request for Proposal - Town planner"

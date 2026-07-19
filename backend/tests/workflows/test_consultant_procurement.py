import re
import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from app.workflows import consultant_procurement as workflow
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


class _Session:
    def __init__(self) -> None:
        self.commit = AsyncMock()


class _StubRetriever:
    def __init__(
        self,
        *,
        project_passages: dict[str, list[Any]] | None = None,
        platform_passages: list[Any] | None = None,
    ) -> None:
        self.project_passages = project_passages or {}
        self.platform_passages = platform_passages or []
        self.calls: list[dict[str, Any]] = []

    async def retrieve(self, query: str, **kwargs: Any) -> list[Any]:
        self.calls.append({"query": query, **kwargs})
        filters = kwargs["filters"]
        if filters.platform_knowledge_only:
            return self.platform_passages
        for key, passages in self.project_passages.items():
            if key in query.lower():
                return passages
        return []


def _project() -> SimpleNamespace:
    return SimpleNamespace(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="demo",
        title="Walsh Renovation",
        workspace_path="04-projects/walsh-renovation",
        phase="procurement",
        state="NSW",
    )


def _passage(
    *,
    filename: str,
    path: str,
    content: str,
    source_type: str = "project_evidence",
    metadata: dict[str, Any] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        document_id=uuid.uuid4(),
        chunk_id=uuid.uuid4(),
        filename=filename,
        relative_path=path,
        page_or_section="p1",
        content=content,
        score=0.1,
        source_type=source_type,
        document_metadata=metadata or {},
    )


def _cost_plan_markdown() -> str:
    return """# Cost plan

## Cost breakdown by category

| Cost Code | Category | Cost Items | Budget | Status | Basis |
| --- | --- | --- | --- | --- | --- |
| 6 | Consultants | Structural engineer | TBC | Assumption | Not yet appointed |
| 10 | Consultants | BASIX / energy assessor | TBC | Assumption | Not yet appointed |
| 12 | Construction | Building works | $920,000 | Assumption | Benchmark |
| | | **Subtotal - Consultants** | TBC | | |
| | | **Subtotal - Construction** | $920,000 | | |
"""


def _install(
    monkeypatch,
    *,
    retriever: _StubRetriever,
    version: int = 1,
    cost_plan: Any = None,
) -> tuple[AsyncMock, AsyncMock]:
    monkeypatch.setattr(workflow, "DocumentRetriever", lambda session: retriever)
    monkeypatch.setattr(
        workflow,
        "next_draft_version",
        AsyncMock(return_value=version),
    )
    monkeypatch.setattr(
        workflow,
        "get_latest_draft_artifact",
        AsyncMock(return_value=cost_plan),
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

    create_draft = AsyncMock(side_effect=_create_draft)
    monkeypatch.setattr(workflow, "create_draft_artifact", create_draft)
    sync_workspace = AsyncMock(side_effect=lambda session, **kwargs: kwargs["draft"].workspace_path)
    monkeypatch.setattr(workflow, "sync_consultant_procurement_draft_workspace", sync_workspace)
    return create_draft, sync_workspace


def _run(
    *,
    session: _Session,
    discipline: str,
    max_pages: int = 1,
    instructions: str | None = None,
):
    return run_async(
        workflow.draft_consultant_procurement_artifact(
            session,
            project=_project(),
            user_id=USER_ID,
            discipline=discipline,
            max_pages=max_pages,
            instructions=instructions,
        )
    )


def test_structural_engineer_happy_path_creates_rfp_draft(monkeypatch) -> None:
    retriever = _StubRetriever(
        project_passages={
            "project brief": [
                _passage(
                    filename="project-brief.pdf",
                    path="04-projects/walsh-renovation/00-brief/project-brief.pdf",
                    content="Owner wants a two-storey renovation.",
                )
            ],
            "planning pathway": [
                _passage(
                    filename="planning-pathway.pdf",
                    path="04-projects/walsh-renovation/02-planning/pathway.pdf",
                    content="DA pathway with council approval.",
                )
            ],
            "design drawings": [
                _passage(
                    filename="structural-markups.pdf",
                    path="04-projects/walsh-renovation/03-design/markups.pdf",
                    content="Structural scope needs beams and footing advice.",
                )
            ],
        },
        platform_passages=[
            _passage(
                filename="consultant-procurement.md",
                path="seed/consultant-procurement.md",
                content="Consultant RFPs should request scope, deliverables, exclusions, and fee basis.",
                source_type="reference",
                metadata={"frontmatter": {"title": "Consultant procurement guide"}},
            )
        ],
    )
    cost_plan = SimpleNamespace(
        workspace_path="04-projects/walsh-renovation/01-cost/cost_plan_v01.md",
        content_markdown=_cost_plan_markdown(),
    )
    create_draft, sync_workspace = _install(monkeypatch, retriever=retriever, cost_plan=cost_plan)
    session = _Session()

    result = _run(session=session, discipline="structural engineer")

    assert result.draft.title == "Request for Fee Proposal - Structural engineer"
    assert result.draft.workspace_path == (
        "04-projects/walsh-renovation/02-consultant/"
        "consultant_procurement_structural_engineer_v01.draft.md"
    )
    assert "# Request for Fee Proposal - Structural engineer" in result.draft.content_markdown
    assert "client-issued request for fee proposal" in result.draft.content_markdown
    assert result.source_trace["project_documents"]
    assert result.source_trace["platform_knowledge"][0]["path"] == (
        "seed/consultant-procurement.md"
    )
    assert result.source_trace["forecast"]["used"] is True
    assert result.source_trace["forecast"]["status"] == "Judgement"
    assert create_draft.await_args.kwargs["runtime"] == "clerk-consultant-procurement"
    sync_workspace.assert_awaited_once()
    assert sync_workspace.await_args.kwargs["markdown"] == result.draft.content_markdown
    session.commit.assert_awaited_once()


def test_basix_alias_happy_path_uses_basix_scope_and_path(monkeypatch) -> None:
    retriever = _StubRetriever()
    cost_plan = SimpleNamespace(
        workspace_path="04-projects/walsh-renovation/01-cost/cost_plan_v01.md",
        content_markdown=_cost_plan_markdown(),
    )
    _install(monkeypatch, retriever=retriever, cost_plan=cost_plan)
    session = _Session()

    result = _run(session=session, discipline="BASIX assessor")

    assert result.discipline == "BASIX / energy assessor"
    assert result.draft.workspace_path.endswith(
        "/consultant_procurement_basix_energy_assessor_v01.draft.md"
    )
    assert "BASIX / energy assessment fee proposal" in result.draft.content_markdown
    assert result.source_trace["forecast"]["used"] is True


def test_auto_versioning_path_names_use_next_workflow_version(monkeypatch) -> None:
    retriever = _StubRetriever()
    _install(monkeypatch, retriever=retriever, version=12, cost_plan=None)
    session = _Session()

    result = _run(session=session, discipline="traffic consultant")

    assert result.draft.version == 12
    assert result.draft.workspace_path.endswith(
        "/consultant_procurement_traffic_consultant_v12.draft.md"
    )


def test_no_evidence_still_creates_draft_with_assumptions(monkeypatch) -> None:
    retriever = _StubRetriever()
    _install(monkeypatch, retriever=retriever, cost_plan=None)
    session = _Session()

    result = _run(session=session, discipline="arborist")

    assert "No project evidence was found" in result.draft.content_markdown
    assert "Project brief or owner scope brief." in result.source_trace["missing_inputs"]
    assert result.source_trace["forecast"] == {
        "used": False,
        "reason": "No benchmark rule for this discipline.",
    }


def test_forecast_values_are_labelled_as_judgement_allowances(monkeypatch) -> None:
    retriever = _StubRetriever()
    cost_plan = SimpleNamespace(
        workspace_path="04-projects/walsh-renovation/01-cost/cost_plan_v01.md",
        content_markdown=_cost_plan_markdown(),
    )
    _install(monkeypatch, retriever=retriever, cost_plan=cost_plan)
    session = _Session()

    result = _run(session=session, discipline="structural engineer")

    assert "$16,500 ex GST judgement allowance" in result.draft.content_markdown
    assert "not a received fee proposal" in result.draft.content_markdown
    forecast = result.source_trace["forecast"]
    assert forecast["status"] == "Judgement"
    assert forecast["basis"] == "Benchmark allowance - consultant fee forecast"


def test_fee_proposals_excluded_from_inputs_and_reconciled(monkeypatch) -> None:
    retriever = _StubRetriever(
        project_passages={
            "project brief": [
                _passage(
                    filename="03-owner-project-brief-walsh-house.md",
                    path="04-projects/walsh-renovation/00-brief/03-owner-project-brief-walsh-house.md",
                    content="Owner brief: renovation and first-floor addition.",
                )
            ],
            "cost plan": [
                _passage(
                    filename="p02-01-fee-proposal-southline-structural.md",
                    path="04-projects/walsh-renovation/_inbox/p02-01-fee-proposal-southline-structural.md",
                    content="# FEE PROPOSAL - STRUCTURAL ENGINEERING. Total professional fee $20,150.",
                )
            ],
        }
    )
    cost_plan = SimpleNamespace(
        workspace_path="04-projects/walsh-renovation/01-cost/cost_plan_v01.md",
        content_markdown=_cost_plan_markdown(),
    )
    _install(monkeypatch, retriever=retriever, cost_plan=cost_plan)
    session = _Session()

    result = _run(session=session, discipline="structural engineer")

    md = result.draft.content_markdown
    # Leakage guard: the competing structural fee proposal is not circulated.
    assert "p02-01-fee-proposal-southline-structural.md" not in md
    # Reconciliation: the parametric benchmark no longer overrides real evidence silently.
    assert "received Structural engineer fee proposal is on file" in md
    assert "$20,150 ex GST" in md
    assert "reconcile the internal benchmark against it" in md
    forecast = result.source_trace["forecast"]
    assert forecast["received_proposal_on_file"] is True
    assert forecast["received_proposal_amount"] == 20150


def test_platform_guidance_resolved_from_catalog_when_semantic_search_empty(monkeypatch) -> None:
    retriever = _StubRetriever()  # no platform passages returned by semantic search
    _install(monkeypatch, retriever=retriever, cost_plan=None)
    session = _Session()
    project = SimpleNamespace(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="demo",
        title="Walsh Renovation",
        workspace_path="04-projects/walsh-renovation",
        phase="procurement",
        state="NSW",
        archetype="renovation",
        user_role="architect-pm",
        building_class=None,
        work_type=None,
    )

    result = run_async(
        workflow.draft_consultant_procurement_artifact(
            session,
            project=project,
            user_id=USER_ID,
            discipline="structural engineer",
        )
    )

    knowledge_paths = [k["path"] for k in result.source_trace["platform_knowledge"]]
    assert "seed/procurement-quoting-guide.md" in knowledge_paths
    assert "Platform guidance: none found" not in result.draft.content_markdown


def test_source_documents_are_referenced_not_written_over(monkeypatch) -> None:
    source_path = "04-projects/walsh-renovation/02-consultant/existing-email.pdf"
    retriever = _StubRetriever(
        project_passages={
            "correspondence": [
                _passage(
                    filename="existing-email.pdf",
                    path=source_path,
                    content="Previous structural consultant correspondence.",
                )
            ]
        }
    )
    create_draft, _sync_workspace = _install(monkeypatch, retriever=retriever, cost_plan=None)
    session = _Session()

    result = _run(session=session, discipline="structural engineer")

    generated_path = create_draft.await_args.kwargs["workspace_path"]
    assert generated_path != source_path
    assert generated_path.endswith(
        "/consultant_procurement_structural_engineer_v01.draft.md"
    )
    assert result.source_trace["project_documents"][0]["relative_path"] == source_path

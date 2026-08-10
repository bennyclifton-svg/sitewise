import re
import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.workflows import consultant_procurement as workflow
from app.workflows import procurement_request
from app.workflows.consultant_procurement import (
    NonConsultantDiscipline,
    normalise_discipline,
    run_validated_rfp_narrative,
)
from app.sitewise.rfp_renderer import build_rfp_citation_index
from app.workflows.create_pmp import WorkflowValidationError
from app.workflows.rfp_narrative import RfpNarrativeOutput
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


def _project(**overrides: Any) -> SimpleNamespace:
    values = {
        "id": PROJECT_ID,
        "owner_user_id": USER_ID,
        "slug": "demo",
        "title": "Walsh Renovation",
        "workspace_path": "04-projects/walsh-renovation",
        "phase": "procurement",
        "state": "NSW",
        "building_class": "residential",
        "work_type": "refurb",
        "user_role": "architect-pm",
        "profile_revision": 1,
        "project_metadata": {},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


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
        procurement_request,
        "load_sections",
        AsyncMock(return_value=None),
    )
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
    monkeypatch.setattr(
        workflow,
        "load_procurement_document_register",
        AsyncMock(return_value=[]),
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
    sync_workspace = AsyncMock(
        side_effect=lambda session, **kwargs: kwargs["draft"].workspace_path
    )
    monkeypatch.setattr(
        workflow, "sync_consultant_procurement_draft_workspace", sync_workspace
    )

    async def _narrative(**kwargs: Any) -> RfpNarrativeOutput:
        evidence = kwargs["project_evidence"]
        if not evidence:
            return RfpNarrativeOutput(
                background="Confirm the project brief, approval pathway, and current design status before issue.",
            )
        citation_index = kwargs["citation_index"]
        path = evidence[0]["relative_path"]
        token = citation_index.token_for(path)
        return RfpNarrativeOutput(
            background=f"The current project evidence defines the consultant briefing basis. {token}",
            requested_services=[
                f"Tailor the requested services to the evidenced project spaces and systems. {token}"
            ],
        )

    monkeypatch.setattr(workflow, "run_rfp_narrative_model", _narrative)
    return create_draft, sync_workspace


def _run(
    *,
    session: _Session,
    discipline: str,
    max_pages: int = 1,
    instructions: str | None = None,
    project: Any | None = None,
):
    return run_async(
        workflow.draft_consultant_procurement_artifact(
            session,
            project=project or _project(),
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
    create_draft, sync_workspace = _install(
        monkeypatch, retriever=retriever, cost_plan=cost_plan
    )
    session = _Session()

    result = _run(session=session, discipline="structural engineer")

    assert result.draft.title == "Request for Proposal - Structural engineer"
    assert result.draft.workspace_path == (
        "04-projects/walsh-renovation/02-consultant/"
        "consultant_procurement_structural_engineer_v01.draft.md"
    )
    assert (
        "# Request for Proposal - Structural engineer" in result.draft.content_markdown
    )
    assert "## Proposal particulars" in result.draft.content_markdown
    assert "| Field | Project detail | Source |" not in result.draft.content_markdown
    assert "| Project |" in result.draft.content_markdown
    primary, trace = result.draft.content_markdown.split("## Trace & QA", maxsplit=1)
    assert "client-issued Request for Proposal" not in primary
    assert "client-issued Request for Proposal" in trace
    assert "Confirm" not in primary
    assert any(
        "client-issued Request for Proposal" in item
        for item in result.source_trace["assumptions"]
    )
    assert "| Document number | Title | Rev | Category |" in (
        result.draft.content_markdown
    )
    assert "## Citation key" not in result.draft.content_markdown
    assert "[1]" in result.draft.content_markdown
    assert "| Site / address | TBC | Confirm |" not in result.draft.content_markdown
    assert "| Client | TBC | Confirm |" not in result.draft.content_markdown
    assert result.source_trace["project_documents"]
    assert result.source_trace["platform_knowledge"][0]["path"] == (
        "seed/procurement-tendering-guide.md"
    )
    assert any(
        item["path"] == "seed/consultant-procurement.md"
        for item in result.source_trace["platform_knowledge"]
    )
    assert result.source_trace["forecast"]["used"] is True
    assert result.source_trace["forecast"]["status"] == "Judgement"
    assert result.source_trace["forecast"]["construction_budget"] == 920_000
    assert "| Budget | $920,000 ex GST |  |" in (result.draft.content_markdown)
    assert create_draft.await_args.kwargs["runtime"] == "clerk-consultant-procurement"
    assert result.draft.provenance_metadata["seed_consulted"] == [
        "seed/procurement-tendering-guide.md",
        "seed/cost-management-principles.md",
        "seed/procurement-quoting-guide.md",
        "seed/consultant-procurement.md",
    ]
    assert result.draft.provenance_metadata["evidence_refs"] == [
        "04-projects/walsh-renovation/00-brief/project-brief.pdf",
        "04-projects/walsh-renovation/02-planning/pathway.pdf",
        "04-projects/walsh-renovation/03-design/markups.pdf",
    ]
    assert result.draft.provenance_metadata["context_refs"] == [
        "seed/procurement-tendering-guide.md",
        "seed/cost-management-principles.md",
        "seed/procurement-quoting-guide.md",
        "seed/consultant-procurement.md",
    ]
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


def test_rfp_information_register_uses_document_repository_metadata(
    monkeypatch,
) -> None:
    retriever = _StubRetriever(
        project_passages={
            "project brief": [
                _passage(
                    filename="420 - 57 GREENBANK Section Rev P3.pdf",
                    path="04-projects/greenbank/03-design/structural/420-section.pdf",
                    content="Structural engineer details are required for the frame and slab.",
                    metadata={
                        "document_number": "420",
                        "title": "STRUCTURAL ENG. DETAILS",
                        "revision": "P3",
                        "discipline": "Structural",
                    },
                )
            ]
        }
    )
    _install(monkeypatch, retriever=retriever, cost_plan=None)

    result = _run(session=_Session(), discipline="structural engineer")

    assert (
        "| 420 | STRUCTURAL ENG. DETAILS | P3 | Structural |"
        in result.draft.content_markdown
    )
    assert "1. Tailor the requested services" in result.draft.content_markdown
    assert "Provide a concise return brief" in result.draft.content_markdown


def test_rfp_prefers_user_adopted_cost_plan_budget_over_partial_trade_total(
    monkeypatch,
) -> None:
    cost_plan = SimpleNamespace(
        workspace_path="04-projects/greenbank/01-cost/cost_plan_v03.md",
        content_markdown="""# Greenbank Cost Plan

## Cost breakdown by category

| Cost code | Category | Cost item | Budget | Status | Basis |
| --- | --- | --- | ---: | --- | --- |
| 6 | Consultants | Structural engineer | $12,000 | proposed | Planning allowance |
| 12 | Construction | Building work | $360,000 | proposed | Planning allowance |
| 21 | PC allowances | Owner selections | $40,000 | proposed | Planning allowance |

## Assumptions

- **adopted_construction_budget_ex_gst:** $400,000.00 supplied by the user.
""",
    )
    _install(monkeypatch, retriever=_StubRetriever(), cost_plan=cost_plan)

    result = _run(session=_Session(), discipline="structural engineer")

    assert result.source_trace["forecast"]["construction_budget"] == 400_000
    assert "| Budget | $400,000 ex GST |  |" in (result.draft.content_markdown)


@pytest.mark.parametrize(
    "discipline",
    [
        "Mechanical engineer",
        "Mechanical services",
        "Mechanical consultant",
        "HVAC engineer",
        "Services Engineer (Mechanical)",
    ],
)
def test_mechanical_phrasings_use_shared_technical_profile(
    discipline: str,
) -> None:
    profile = normalise_discipline(discipline)

    assert profile.name == "Mechanical Services Engineer"
    assert profile.slug == "mechanical_engineer"
    assert profile.knowledge_paths == ("seed/mechanical-services-guide.md",)
    assert "ventilation" in profile.knowledge_query_terms
    assert any("commissioning" in item.lower() for item in profile.deliverables)


def test_mechanical_rfp_consults_technical_guide_and_targeted_evidence(
    monkeypatch,
) -> None:
    retriever = _StubRetriever()
    _install(monkeypatch, retriever=retriever, cost_plan=None)

    result = _run(
        session=_Session(),
        discipline="mechanical engineer",
        max_pages=3,
        project=_project(building_class="mixed", work_type="new"),
    )

    knowledge = result.source_trace["platform_knowledge"]
    mechanical = next(
        item
        for item in knowledge
        if item["path"] == "seed/mechanical-services-guide.md"
    )
    assert mechanical["source_type"] == "discipline-guidance"
    assert (
        "cross-lifecycle mechanical-services guidance" in mechanical["snippet"].lower()
    )
    assert (
        "seed/mechanical-services-guide.md"
        in result.draft.provenance_metadata["seed_consulted"]
    )
    assert "Establish the mechanical design basis" in result.draft.content_markdown
    assert "Commissioning plan and records" in result.draft.content_markdown
    assert any(
        "car park ventilation smoke control" in call["query"]
        for call in retriever.calls
    )
    platform_call = next(
        call for call in retriever.calls if call["filters"].platform_knowledge_only
    )
    assert "HVAC ventilation exhaust controls commissioning" in platform_call["query"]


def test_mechanical_rfp_uses_evidence_tailored_requested_services(monkeypatch) -> None:
    retriever = _StubRetriever(
        project_passages={
            "project brief": [
                _passage(
                    filename="design-brief.pdf",
                    path="04-projects/industrial/00-brief/design-brief.pdf",
                    content=(
                        "The 2,135 m² warehouse includes offices, wet-area amenities, "
                        "MHE charging ventilation and smoke clearance."
                    ),
                )
            ]
        }
    )
    _install(monkeypatch, retriever=retriever, cost_plan=None)

    result = _run(
        session=_Session(),
        discipline="mechanical engineer",
        project=_project(
            title="Industrial",
            building_class="industrial",
            work_type="extend",
            project_metadata={
                "taxonomy": {
                    "subclasses": ["warehouse"],
                    "scale": {"gfa_sqm": 2135, "office_percent": 9.3},
                }
            },
        ),
    )

    requested = result.draft.content_markdown.split(
        "## Services and deliverables", maxsplit=1
    )[1].split("## Programme and submission", maxsplit=1)[0]
    assert (
        "Tailor the requested services to the evidenced project spaces and systems. [1]"
        in requested
    )
    assert "dwellings, common areas, car parking" not in requested


def test_hydraulic_profile_uses_discipline_guide_and_fitout_controls() -> None:
    profile = normalise_discipline("hydraulic engineer")

    assert profile.knowledge_paths == ("seed/hydraulic-services-guide.md",)
    assert "sanitary drainage" in profile.knowledge_query_terms
    assert any("landlord" in item.lower() for item in profile.requested_services)
    assert any("design-basis" in item.lower() for item in profile.deliverables)


@pytest.mark.parametrize(
    ("discipline", "expected_name", "expected_path"),
    [
        (
            "electrical engineer",
            "Electrical Services Engineer",
            "seed/electrical-services-guide.md",
        ),
        (
            "fire engineer",
            "Fire engineer",
            "seed/fire-life-safety-guide.md",
        ),
        (
            "ESD consultant",
            "Sustainability Consultant",
            "seed/non-residential-sustainability-energy-guide.md",
        ),
        (
            "ICT consultant",
            "ICT / AV / Security Consultant",
            "seed/ict-av-security-guide.md",
        ),
    ],
)
def test_new_discipline_profiles_route_to_deep_guidance(
    discipline: str,
    expected_name: str,
    expected_path: str,
) -> None:
    profile = normalise_discipline(discipline)

    assert profile.name == expected_name
    assert profile.knowledge_paths == (expected_path,)
    assert any("fee breakdown" in item.lower() for item in profile.deliverables)


def test_commercial_fitout_filters_semantic_guidance_to_project_taxonomy(
    monkeypatch,
) -> None:
    retriever = _StubRetriever(
        platform_passages=[
            _passage(
                filename="nsw-industrial-warehouse-cost-breakdown-reference.md",
                path="skills/reference/nsw-industrial-warehouse-cost-breakdown-reference.md",
                content="Industrial warehouse cost taxonomy.",
                source_type="reference",
            ),
            _passage(
                filename="procurement-quoting-guide.md",
                path="seed/procurement-quoting-guide.md",
                content="Residential procurement guidance.",
                source_type="reference",
            ),
            _passage(
                filename="mechanical-services-guide.md",
                path="seed/mechanical-services-guide.md",
                content="Mechanical services consultant guidance.",
                source_type="reference",
            ),
            _passage(
                filename="nsw-commercial-fitout-cost-breakdown-reference.md",
                path="skills/reference/nsw-commercial-fitout-cost-breakdown-reference.md",
                content="Commercial fit-out consultant fee stages.",
                source_type="reference",
            ),
        ]
    )
    _install(monkeypatch, retriever=retriever, cost_plan=None)

    result = _run(
        session=_Session(),
        discipline="hydraulic engineer",
        project=_project(
            title="Meridian Chambers Fit-Out",
            building_class="commercial",
            work_type="refurb",
            user_role="d-and-c",
            project_metadata={"taxonomy": {"subclasses": ["office"]}},
        ),
    )

    paths = {item["path"] for item in result.source_trace["platform_knowledge"]}
    assert "skills/reference/nsw-commercial-fitout-cost-breakdown-reference.md" in paths
    assert "seed/hydraulic-services-guide.md" in paths
    assert (
        "skills/reference/nsw-industrial-warehouse-cost-breakdown-reference.md"
        not in paths
    )
    assert "seed/procurement-quoting-guide.md" not in paths
    assert "seed/procurement-tendering-guide.md" in paths
    assert "seed/cost-management-principles.md" in paths
    assert "seed/mechanical-services-guide.md" not in paths


def test_auto_versioning_path_names_use_next_workflow_version(monkeypatch) -> None:
    retriever = _StubRetriever()
    _install(monkeypatch, retriever=retriever, version=12, cost_plan=None)
    session = _Session()

    result = _run(session=session, discipline="traffic consultant")

    assert result.draft.version == 12
    assert result.draft.workspace_path.endswith(
        "/consultant_procurement_traffic_consultant_v12.draft.md"
    )


def test_rfp_includes_confirmed_site_address_and_client(monkeypatch) -> None:
    retriever = _StubRetriever()
    _install(monkeypatch, retriever=retriever, cost_plan=None)
    session = _Session()
    project = _project(
        project_metadata={
            "taxonomy": {
                "site_address": "82 Queen Street, Petersham NSW 2049",
                "client": "Walsh Family",
            }
        }
    )

    result = _run(session=session, discipline="structural engineer", project=project)

    assert "| Site / address | 82 Queen Street, Petersham NSW 2049" in (
        result.draft.content_markdown
    )
    assert "| Client | Walsh Family" in result.draft.content_markdown
    assert "Confirmed site address." not in result.source_trace["missing_inputs"]


def test_rfp_falls_back_to_evidence_address_when_profile_empty(monkeypatch) -> None:
    retriever = _StubRetriever(
        project_passages={
            "project brief": [
                _passage(
                    filename="project-brief.pdf",
                    path="04-projects/walsh-renovation/00-brief/project-brief.pdf",
                    content=(
                        "Project brief for proposed new dwelling at "
                        "14 Wattle Grove, Lindfield NSW 2070 for the owners "
                        "Jane and John Walsh."
                    ),
                )
            ],
        }
    )
    _install(monkeypatch, retriever=retriever, cost_plan=None)
    session = _Session()

    result = _run(session=session, discipline="structural engineer")

    assert "| Site / address | 14 Wattle Grove, Lindfield NSW 2070" in (
        result.draft.content_markdown
    )


def test_no_evidence_still_creates_draft_with_assumptions(monkeypatch) -> None:
    retriever = _StubRetriever()
    _install(monkeypatch, retriever=retriever, cost_plan=None)
    session = _Session()

    result = _run(session=session, discipline="arborist")

    primary, trace = result.draft.content_markdown.split("## Trace & QA", maxsplit=1)
    assert "TBC" not in primary
    assert "No project evidence was found" in trace
    assert (
        "Project brief or owner scope brief." in result.source_trace["missing_inputs"]
    )
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

    forecast = result.source_trace["forecast"]
    assert forecast["status"] == "Judgement"
    assert forecast["basis"] == "Benchmark allowance - consultant fee forecast"
    assert "$16,500 ex GST judgement allowance" in forecast["label"]
    assert "not a received fee proposal" in forecast["label"]
    assert "judgement allowance" not in result.draft.content_markdown


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
    # Reconciliation remains available internally without leaking competitor
    # pricing or benchmark commentary into the issued RFP.
    assert "received consultant fee proposal is on file" not in md
    assert "$20,150 ex GST" not in md
    forecast = result.source_trace["forecast"]
    assert forecast["received_proposal_on_file"] is True
    assert forecast["received_proposal_amount"] == 20150


def test_other_discipline_fee_proposal_can_supply_project_scope(monkeypatch) -> None:
    retriever = _StubRetriever(
        project_passages={
            "project brief": [
                _passage(
                    filename="04-fee-proposal-form-function-studio.md",
                    path="04-projects/fitout/_inbox/04-fee-proposal-form-function-studio.md",
                    content=(
                        "Architect and project management fee proposal for Meridian "
                        "Chambers Fit-Out, including a kitchenette, breakout area and "
                        "Level 4 mezzanine."
                    ),
                )
            ]
        }
    )
    _install(monkeypatch, retriever=retriever, cost_plan=None)

    result = _run(
        session=_Session(),
        discipline="hydraulic engineer",
        project=_project(building_class="commercial", work_type="refurb"),
    )

    assert (
        "04-fee-proposal-form-function-studio.md"
        in (result.draft.provenance_metadata["evidence_refs"])[0]
    )


def test_evidenced_programme_replaces_summary_tbc(monkeypatch) -> None:
    retriever = _StubRetriever(
        project_passages={
            "project brief": [
                _passage(
                    filename="engagement-letter.md",
                    path="04-projects/fitout/00-brief/engagement-letter.md",
                    content="Target possession is 1 November 2026.",
                )
            ]
        }
    )
    _install(monkeypatch, retriever=retriever, cost_plan=None)

    async def _programme_narrative(**kwargs: Any) -> RfpNarrativeOutput:
        return RfpNarrativeOutput(
            background="The current programme is evidenced. [1]",
            requested_services=["Provide staged hydraulic services. [1]"],
            programme=["Target possession is 1 November 2026. [1]"],
        )

    monkeypatch.setattr(workflow, "run_rfp_narrative_model", _programme_narrative)
    result = _run(
        session=_Session(),
        discipline="hydraulic engineer",
        project=_project(building_class="commercial", work_type="refurb"),
    )

    assert "- Target possession is 1 November 2026. [1]" in (
        result.draft.content_markdown
    )


def test_platform_guidance_resolved_from_catalog_when_semantic_search_empty(
    monkeypatch,
) -> None:
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


def test_required_seed_content_is_loaded_into_rfp_context(monkeypatch) -> None:
    retriever = _StubRetriever()
    _install(monkeypatch, retriever=retriever, cost_plan=None)
    full_seed = "# Procurement guidance\n\nUse staged fees and explicit exclusions."
    monkeypatch.setattr(
        procurement_request,
        "load_sections",
        AsyncMock(
            return_value=SimpleNamespace(
                passage=_passage(
                    filename="procurement-quoting-guide.md",
                    path="seed/procurement-quoting-guide.md",
                    content=full_seed,
                    source_type="reference",
                )
            )
        ),
    )
    project = _project(archetype="renovation")
    seen_platform_knowledge: list[dict[str, Any]] = []

    async def _capture_narrative(**kwargs: Any) -> RfpNarrativeOutput:
        seen_platform_knowledge.extend(kwargs["platform_knowledge"])
        return RfpNarrativeOutput(
            background="Confirm the project context before issue."
        )

    monkeypatch.setattr(workflow, "run_rfp_narrative_model", _capture_narrative)

    result = _run(
        session=_Session(),
        discipline="town planner",
        project=project,
    )

    seed = next(
        item
        for item in result.source_trace["platform_knowledge"]
        if item["path"] == "seed/procurement-quoting-guide.md"
    )
    assert seed["snippet"] == full_seed
    assert any(item["snippet"] == full_seed for item in seen_platform_knowledge)
    assert (
        "seed/procurement-quoting-guide.md"
        in result.draft.provenance_metadata["seed_consulted"]
    )


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
    create_draft, _sync_workspace = _install(
        monkeypatch, retriever=retriever, cost_plan=None
    )
    session = _Session()

    result = _run(session=session, discipline="structural engineer")

    generated_path = create_draft.await_args.kwargs["workspace_path"]
    assert generated_path != source_path
    assert generated_path.endswith(
        "/consultant_procurement_structural_engineer_v01.draft.md"
    )
    assert result.source_trace["project_documents"][0]["relative_path"] == source_path


@pytest.mark.parametrize(
    "discipline",
    [
        "main contractor",
        "main_contractor",
        "main works",
        "head contractor",
        "principal contractor",
        "builder",
        "design and construct",
        "subcontractor",
        "sub contractor",
        "trade contractor",
        "trade package",
    ],
)
def test_contractor_disciplines_are_rejected(discipline: str) -> None:
    with pytest.raises(NonConsultantDiscipline):
        normalise_discipline(discipline)


@pytest.mark.parametrize(
    ("discipline", "name", "slug"),
    [
        ("town planner", "Town planner", "town_planner"),
        ("heritage consultant", "Heritage consultant", "heritage_consultant"),
        ("fire engineer", "Fire engineer", "fire_engineer"),
        ("acoustic consultant", "Acoustic consultant", "acoustic_consultant"),
    ],
)
def test_known_consultant_profiles_do_not_use_generic_fallback(
    discipline: str, name: str, slug: str
) -> None:
    profile = normalise_discipline(discipline)

    assert profile.name == name
    assert profile.slug == slug


def test_structural_profile_is_contract_ready_and_uses_discipline_specific_closeout() -> (
    None
):
    profile = normalise_discipline("structural engineer")

    assert len(profile.requested_services) == 7
    assert any(
        "new-to-existing interface" in item for item in profile.requested_services
    )
    assert any("completion statements" in item for item in profile.requested_services)
    assert not any(
        "commissioning" in item.lower() for item in profile.requested_services
    )


def test_unknown_consultant_still_falls_through() -> None:
    profile = normalise_discipline("facade consultant")
    assert profile.name == "facade consultant"
    assert profile.slug == "facade_consultant"


@pytest.mark.parametrize(
    "discipline",
    [
        "Town planning",
        "Town planning consultant",
        "Planning consultant",
    ],
)
def test_town_planning_phrasings_alias_to_town_planner(discipline: str) -> None:
    """A discipline phrased as "town planning" (not "town planner") must resolve
    to the same curated profile/slug, not spin up a second, generically-templated
    workflow lineage. Regression for Walsh Two producing both
    consultant_procurement_town_planner_* and consultant_procurement_town_planning_*
    drafts for what should be a single discipline.
    """
    profile = normalise_discipline(discipline)

    assert profile.name == "Town planner"
    assert profile.slug == "town_planner"
    assert profile.requested_services
    assert profile.benchmark_terms


@pytest.mark.parametrize(
    "discipline",
    [
        "Building certifier",
        "Building certifier / PCA",
        "Building certifier/PCA",
        "Principal certifying authority",
    ],
)
def test_building_certifier_phrasings_alias_to_certifier(discipline: str) -> None:
    """Same class of bug as town planning/town planner: a user (or the chat
    agent parsing their words) is far more likely to say "building certifier"
    or "building certifier / PCA" than the bare canonical "certifier", and
    without an alias that phrasing falls through to the generic fallback
    profile instead of the curated certifier one.
    """
    profile = normalise_discipline(discipline)

    assert profile.name == "Certifier"
    assert profile.slug == "certifier"
    assert profile.requested_services
    assert profile.benchmark_terms


def _rfp_evidence() -> list[dict[str, str]]:
    return [
        {"relative_path": "docs/brief.pdf", "snippet": "Project brief."},
        {"relative_path": "docs/site-plan.pdf", "snippet": "Site plan."},
        {"relative_path": "docs/survey.pdf", "snippet": "Survey."},
    ]


def test_rfp_narrative_retries_after_invalid_citation(monkeypatch) -> None:
    evidence = _rfp_evidence()
    citation_index = build_rfp_citation_index(evidence)
    invalid = RfpNarrativeOutput(
        background="The project brief identifies the scope. [99]",
        requested_services=["Provide project-specific planning services. [1]"],
    )
    valid = RfpNarrativeOutput(
        background="The project brief identifies the scope. [1]",
        requested_services=["Provide project-specific planning services. [1]"],
    )
    run_narrative = AsyncMock(side_effect=[invalid, valid])
    monkeypatch.setattr(workflow, "run_rfp_narrative_model", run_narrative)

    output = run_async(
        run_validated_rfp_narrative(
            project=_project(),
            target=normalise_discipline("town planner"),
            project_evidence=evidence,
            platform_knowledge=[],
            citation_index=citation_index,
        )
    )

    assert output == valid
    assert run_narrative.await_count == 2
    assert "[99]" in run_narrative.await_args_list[1].kwargs["validation_feedback"]


def test_rfp_narrative_reraises_after_three_invalid_attempts(monkeypatch) -> None:
    evidence = _rfp_evidence()
    citation_index = build_rfp_citation_index(evidence)
    invalid = RfpNarrativeOutput(
        background="The project brief identifies the scope. [99]",
        requested_services=["Provide project-specific planning services. [1]"],
    )
    run_narrative = AsyncMock(return_value=invalid)
    monkeypatch.setattr(workflow, "run_rfp_narrative_model", run_narrative)

    with pytest.raises(WorkflowValidationError, match=r"\[99\]"):
        run_async(
            run_validated_rfp_narrative(
                project=_project(),
                target=normalise_discipline("town planner"),
                project_evidence=evidence,
                platform_knowledge=[],
                citation_index=citation_index,
            )
        )

    assert run_narrative.await_count == 3


def test_rfp_draft_retries_invalid_narrative_before_persisting(monkeypatch) -> None:
    retriever = _StubRetriever(
        project_passages={
            "project brief": [
                _passage(
                    filename="project-brief.pdf",
                    path="04-projects/walsh-renovation/00-brief/project-brief.pdf",
                    content="Owner wants a two-storey renovation.",
                )
            ]
        }
    )
    _install(monkeypatch, retriever=retriever, cost_plan=None)
    invalid = RfpNarrativeOutput(
        background="The project brief defines the scope. [99]",
        requested_services=["Provide project-specific planning services. [1]"],
    )
    valid = RfpNarrativeOutput(
        background="The project brief defines the scope. [1]",
        requested_services=["Provide project-specific planning services. [1]"],
    )
    run_narrative = AsyncMock(side_effect=[invalid, valid])
    monkeypatch.setattr(workflow, "run_rfp_narrative_model", run_narrative)

    result = _run(session=_Session(), discipline="town planner")

    assert "[99]" not in result.draft.content_markdown
    assert "The project brief defines the scope. [1]" in result.draft.content_markdown
    assert run_narrative.await_count == 2

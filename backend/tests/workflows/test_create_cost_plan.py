import asyncio
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.database.project import Project
from app.cost_plan.import_legacy import parse_legacy_draft
from app.retrieval.schemas import SourcePassage
from app.sitewise.cost_plan_evidence_validation import (
    claim_first_violations,
    cost_plan_evidence_grounded_violations,
    ensure_evidence_grounded_cost_plan_scaffold,
)
from app.sitewise.cost_plan_sources import required_section_headings
from app.cost_plan.schemas import CostItemInput
from app.workflows.create_cost_plan import (
    CostPlanDraftOutput,
    render_typed_cost_plan_markdown,
    retrieve_create_cost_plan_sources,
    run_create_cost_plan_workflow,
    sync_cost_plan_revision_artifacts,
    validate_cost_plan_output,
)
from app.workflows.create_pmp import WorkflowValidationError, normalize_pmp_markdown
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
WALSH_FIXTURE_DIR = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "synthetic-mobilisation-evidence"
    / "walsh-renovation"
)


def _project(**overrides) -> Project:
    values = {
        "id": PROJECT_ID,
        "owner_user_id": USER_ID,
        "slug": "greenfield-demo",
        "title": "Greenfield Demo",
        "workspace_path": "04-projects/greenfield-demo",
        "phase": "brief-planning",
        "archetype": "renovation",
        "user_role": "architect-pm",
        "state": "NSW",
        "status": "active",
        "project_metadata": None,
        "created_at": datetime(2026, 6, 7, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 6, 7, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return Project(**values)


def _valid_seed_consulted() -> list[str]:
    return [
        "seed/renovation-guide.md",
        "seed/role-architect-pm.md",
        "seed/cost-management-principles.md",
        "skills/reference/nsw-residential-cost-breakdown-reference.md",
    ]


def _walsh_source_texts() -> list[str]:
    return [
        path.read_text(encoding="utf-8")
        for path in sorted(WALSH_FIXTURE_DIR.glob("[0-9]*.md"))
    ]


def _cost_breakdown_section() -> str:
    return """## Budget reconciliation and cost breakdown

| Cost Code | Category | Cost Items | Budget | Status | Basis |
| --- | --- | --- | --- | --- | --- |
| 1 | Fees and charges | Planning fees | 12000 | Assumption | Benchmark |
| 2 | Fees and charges | Certifier fees | 8000 | Assumption | Benchmark |
| 3 | Consultants | Architect PM | 148500 | Assumption | Fee proposal |
| 4 | Construction | Preliminaries | 45000 | Assumption | HIA schedule |
| 5 | Construction | Siteworks | 38000 | Assumption | Benchmark |
| 6 | Construction | Footings and slab | 92000 | Assumption | Benchmark |
| 7 | Construction | Framing | 78000 | Assumption | Benchmark |
| 8 | Contingency / allowances | Construction contingency | 55000 | Assumption | 7% construction |
| | | **Grand total (ex GST)** | 466500 | Assumption | |
"""


def _valid_cost_plan_markdown() -> str:
    greenfield_terms = (
        "Fees and charges and Consultants groups with construction contingency 5-10%. "
        "All figures exclude GST. Latent conditions remain an assumption. "
        "Recommendation: owner confirm working budget by 2026-07-01."
    )
    sections = {
        "Project name and location": (
            "## Project name and location\n\n"
            "Greenfield Demo — Assumption: 1 Example Street, Sydney NSW 2000. "
            f"{greenfield_terms}"
        ),
        "Source evidence used": (
            "## Source evidence used\n\n"
            "Doctrine and seeds only — no project cost evidence yet."
        ),
        "Budget reconciliation and control decision": (
            "## Budget reconciliation and control decision\n\n"
            "| Figure | Source | Amount (ex GST) | Adopted? |\n"
            "| --- | --- | --- | --- |\n"
            "| Working budget | Assumption | TBC | Qualified |\n"
        ),
        "Total approved or indicative budget": (
            "## Total approved or indicative budget\n\n"
            "Indicative total project cost (ex GST): **Assumption $466,500**."
        ),
        "GST basis": (
            "## GST basis\n\n"
            "All workbook figures exclude GST. Owner-facing communication may use inc GST."
        ),
        "Cost breakdown by category": _cost_breakdown_section(),
        "Known locked contract and appointment values": (
            "## Known locked contract and appointment values\n\n"
            "Assumption: none locked yet."
        ),
        "Allowances and contingency": (
            "## Allowances and contingency\n\n"
            "Construction contingency 7% on construction cost only — Assumption."
        ),
        "PM fee treatment": (
            "## PM fee treatment\n\n"
            "Architect-PM fee inside total project budget — Assumption."
        ),
        "Assumptions and exclusions": (
            "## Assumptions and exclusions\n\n"
            "- Benchmark construction rates — verify before commitment."
        ),
        "Risks and review questions": (
            "## Risks and review questions\n\n"
            "| Risk | Impact | Owner | Next action | Due |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| Latent conditions | High | Owner | Geotech | 2026-07-01 |\n"
            "| Budget not evidenced | High | Owner | Confirm ceiling | 2026-07-01 |\n"
            "| Planning pathway | Medium | PM | Test CDC vs DA | 2026-07-01 |\n"
            "| Trade pricing | Medium | Builder | Tender | 2026-07-01 |\n"
            "| Contingency adequacy | Medium | Owner | Review at lockup | 2026-07-01 |\n"
        ),
        "Authority, compliance and procurement gates": (
            "## Authority, compliance and procurement gates\n\n"
            "| Gate | Status | Cost impact |\n"
            "| --- | --- | --- |\n"
            "| Geotechnical | Assumption | Medium–High |\n"
        ),
        "Recommended next steps": (
            "## Recommended next steps\n\n"
            "1. Owner to confirm working budget ceiling by 2026-07-01."
        ),
        "Internal audit layer": (
            "## Internal audit layer\n\n"
            "- **Facts**\n- Platform-seeded scaffold only.\n"
            "- **Assumptions**\n- All construction lines are benchmark.\n"
            "- **Judgements**\n- Contingency at 7% pending scope lock.\n"
            "- **Recommendations**\n- Confirm budget by 2026-07-01.\n"
            "- **Recommendations**\n- Commission geotech before slab pricing.\n"
            "- **Recommendations**\n- Review markdown before workbook export.\n"
        ),
    }
    sections.update(
        {
            "Cost plan summary and control decision": (
                "## Cost plan summary and control decision\n\n"
                "Greenfield Demo - Assumption: 1 Example Street, Sydney NSW 2000. "
                f"{greenfield_terms}"
            ),
            "Budget reconciliation and cost breakdown": _cost_breakdown_section(),
            "Commitments, allowances and exclusions": (
                "## Commitments, allowances and exclusions\n\n"
                "- Benchmark construction rates - verify before commitment."
            ),
            "Risks, delivery gates and next actions": (
                "## Risks, delivery gates and next actions\n\n"
                "| Risk | Owner | Next action |\n"
                "| --- | --- | --- |\n"
                "| Budget not evidenced | Owner | Confirm ceiling by 2026-07-01 |"
            ),
            "Source evidence and audit trail": (
                "## Source evidence and audit trail\n\n"
                "### Citation key\n\nDoctrine and seeds only.\n\n"
                "- **Facts**\n- Platform-seeded scaffold only.\n"
                "- **Assumptions**\n- All construction lines are benchmark."
            ),
        }
    )
    body = "\n\n".join(sections[heading] for heading in required_section_headings())
    return f"# Project Cost Plan\n\n{body}"


def _valid_evidence_grounded_cost_plan_markdown() -> str:
    markdown = _valid_cost_plan_markdown()
    return _replace_section(
        markdown,
        "Source evidence and audit trail",
        """## Source evidence and audit trail

### Citation key

[1] claim-03.md - May 2026
[2] fee-proposal.md - on file

| Cost-plan area | Evidence status | Ref |
| --- | --- | --- |
| Construction breakdown | Grounded | [1] |
| PM fee | Partial | [2] |

- **Facts**
- Progress claim #3 includes trade schedule with preliminaries, slab, frame rows.
- Architect fee proposal on file at $148,500 ex GST.
- **Assumptions**
- Owner budget ceiling not evidenced.
- **Judgements**
- Adopt claim schedule for construction breakdown pending reconciliation.
- **Recommendations**
- Reconcile claim total to contract sum by 2026-07-01.
""",
    )
    source_section = """## Source evidence used

Evidence on file: progress claim #3 (May 2026); architect fee proposal.

| Section | Evidence status | Ref |
| --- | --- | --- |
| Construction breakdown | Grounded | progress claim |
| PM fee | Partial | fee proposal |
| Budget ceiling | Not evidenced | — |
"""
    audit = """## Internal audit layer

- **Facts**
- Progress claim #3 includes trade schedule with preliminaries, slab, frame rows.
- Architect fee proposal on file at $148,500 ex GST.
- **Assumptions**
- Owner budget ceiling not evidenced.
- **Judgements**
- Adopt claim schedule for construction breakdown pending reconciliation.
- **Recommendations**
- Owner to confirm budget ceiling by 2026-07-01.
- **Recommendations**
- Reconcile claim total to contract sum by 2026-07-01.
- **Recommendations**
- Review markdown before workbook export by 2026-07-01.
"""
    return _replace_section(
        _replace_section(markdown, "Source evidence used", source_section),
        "Internal audit layer",
        audit,
    )


def _replace_section(markdown: str, heading: str, replacement: str) -> str:
    target = heading.strip().lower()
    lines = markdown.splitlines()
    output: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip().lower()
        if stripped.startswith("## ") and stripped[3:].strip() == target:
            output.extend(replacement.rstrip().splitlines())
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("## "):
                index += 1
            continue
        output.append(line)
        index += 1
    return "\n".join(output)


def _passage(*, project: str, source_type: str, relative_path: str) -> SourcePassage:
    return SourcePassage(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        content="Cost plan budget contingency claims variations.",
        project=project,
        phase="reference",
        source_type=source_type,
        document_class="reference_guide" if source_type == "reference" else source_type,
        filename=relative_path.split("/")[-1],
        relative_path=relative_path,
        document_metadata={"knowledge_scope": "platform"}
        if source_type == "reference"
        else None,
        chunk_metadata={"whole_document": True},
        score=1.0,
    )


def _sample_typed_items(
    *,
    fee: str | None = "148500",
    contingency: str | None = "120000",
    construction_budget: str | None = "1850000",
) -> list[CostItemInput]:
    from decimal import Decimal

    items = [
        CostItemInput(
            item_key="scaffold:1",
            cost_code="1",
            category="Fees and charges",
            item="Architect / PM fee",
            budget=None if fee is None else Decimal(fee),
            forecast=Decimal(fee or "0"),
            basis="Engagement letter",
            status="confirmed",
        ),
        CostItemInput(
            item_key="scaffold:12",
            cost_code="12",
            category="Construction",
            item="Preliminaries",
            budget=(
                None
                if construction_budget is None
                else Decimal(construction_budget) * Decimal("8") / Decimal("100")
            ),
            forecast=Decimal("0"),
            basis="Benchmark % of ceiling",
            status="proposed",
        ),
        CostItemInput(
            item_key="scaffold:13",
            cost_code="13",
            category="Construction",
            item="Siteworks and demolition",
            budget=(
                None
                if construction_budget is None
                else Decimal(construction_budget) * Decimal("92") / Decimal("100")
            ),
            forecast=Decimal("0"),
            basis="Benchmark % of ceiling",
            status="proposed",
        ),
        CostItemInput(
            item_key="scaffold:25",
            cost_code="25",
            category="Contingency / allowances",
            item="Owner-held contingency",
            budget=None if contingency is None else Decimal(contingency),
            forecast=Decimal(contingency or "0"),
            basis="Owner brief",
            status="confirmed",
        ),
    ]
    return items


def _typed_output(
    *,
    draft_mode: str = "platform_seeded",
    items: list[CostItemInput] | None = None,
    seed_consulted: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    omit_table: bool = False,
) -> CostPlanDraftOutput:
    typed_items = items if items is not None else _sample_typed_items()
    markdown = (
        "# Project Cost Plan\n\nNo table.\n"
        if omit_table
        else render_typed_cost_plan_markdown("Project Cost Plan", typed_items)
    )
    output = CostPlanDraftOutput(
        title="Project Cost Plan",
        markdown=markdown,
        seed_consulted=seed_consulted
        if seed_consulted is not None
        else _valid_seed_consulted(),
        evidence_refs=(
            []
            if draft_mode == "platform_seeded"
            else (
                evidence_refs
                if evidence_refs is not None
                else [
                    "project_evidence:greenfield-demo/07-construction/"
                    "05-progress-claims/claim-03.md#chunk=1"
                ]
            )
        ),
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    output._cost_items = typed_items
    return output


def test_create_cost_plan_blocks_when_overlay_gate_fails() -> None:
    result = run_async(
        run_create_cost_plan_workflow(
            AsyncMock(),
            user_id=USER_ID,
            project=_project(archetype="TBC"),
            thread_id=None,
        )
    )

    assert result.status == "blocked"
    assert result.gate.ready is False
    assert result.draft is None


def test_create_cost_plan_fails_when_platform_and_project_sources_missing() -> None:
    with (
        patch(
            "app.workflows.create_cost_plan.load_cost_project_evidence_documents",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.list_cost_evidence_paths",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.load_platform_documents_by_paths",
            new=AsyncMock(return_value=([], [])),
        ),
    ):
        result = run_async(
            run_create_cost_plan_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=_project(),
                thread_id=None,
            )
        )

    assert result.status == "failed"
    assert "doctrine and seed" in (result.message or "")


def test_create_cost_plan_greenfield_from_platform_documents() -> None:
    output = _typed_output(draft_mode="platform_seeded")
    draft = AsyncMock()
    draft.id = uuid.uuid4()
    draft.project_id = PROJECT_ID
    draft.workflow_type = "create_cost_plan"
    draft.version = 1
    draft.status = "draft"
    draft.title = output.title
    draft.workspace_path = "04-projects/greenfield-demo/01-cost/cost_plan_v01.md"
    draft.author_user_id = USER_ID
    draft.content_markdown = output.markdown
    draft.model = "gpt-5.6-terra"
    draft.runtime = "clerk-sitewise-create-cost-plan-typed"
    draft.provenance_metadata = {}
    draft.created_at = datetime(2026, 6, 7, tzinfo=timezone.utc)
    draft.updated_at = datetime(2026, 6, 7, tzinfo=timezone.utc)
    workbook_metadata = {
        "file_name": "Cost_Plan_v01.draft.xlsx",
        "workspace_path": "04-projects/greenfield-demo/01-cost/Cost_Plan_v01.draft.xlsx",
        "version": 1,
        "content_hash": "abc123",
        "size_bytes": 1234,
        "row_count": 8,
        "cost_item_lookup_count": 8,
        "warnings": [],
        "generated_at": "2026-06-07T00:00:00+00:00",
    }

    platform_passage = _passage(
        project="seed",
        source_type="reference",
        relative_path="seed/cost-management-principles.md",
    )
    typed_import = replace(parse_legacy_draft(draft), typed_version_id=draft.id)

    with (
        patch(
            "app.workflows.create_cost_plan.load_cost_project_evidence_documents",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.list_cost_evidence_paths",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.load_platform_documents_by_paths",
            new=AsyncMock(return_value=([platform_passage], [])),
        ),
        patch(
            "app.workflows.create_cost_plan.run_create_cost_plan_typed",
            new=AsyncMock(return_value=output),
        ),
        patch(
            "app.workflows.create_cost_plan._next_version_hint",
            new=AsyncMock(return_value=1),
        ),
        patch(
            "app.workflows.create_cost_plan.create_draft_artifact",
            new=AsyncMock(return_value=draft),
        ) as create_draft,
        patch(
            "app.workflows.create_cost_plan.import_legacy_draft",
            new=AsyncMock(return_value=typed_import),
        ),
        patch(
            "app.workflows.create_cost_plan.sync_cost_plan_draft_workspace",
            new=AsyncMock(return_value=draft.workspace_path),
        ) as sync_markdown,
        patch(
            "app.workflows.create_cost_plan.save_cost_plan_workbook_artifact",
            new=AsyncMock(return_value=workbook_metadata),
        ) as save_workbook,
    ):
        result = run_async(
            run_create_cost_plan_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=_project(),
                thread_id=None,
            )
        )

    assert result.status == "complete"
    assert result.draft is not None
    create_draft.assert_awaited_once()
    sync_markdown.assert_not_awaited()
    save_workbook.assert_awaited_once()
    assert (
        create_draft.await_args.kwargs["provenance_metadata"]["draft_mode"]
        == "platform_seeded"
    )
    assert create_draft.await_args.kwargs["provenance_metadata"]["compiler"] == "typed"
    assert create_draft.await_args.kwargs["workspace_path"].endswith(
        "01-cost/cost_plan_v01.md"
    )
    assert (
        result.draft.provenance_metadata["workbook"]["file_name"]
        == "Cost_Plan_v01.draft.xlsx"
    )


def test_validate_cost_plan_output_accepts_platform_seeded() -> None:
    validate_cost_plan_output(
        _typed_output(draft_mode="platform_seeded"),
        "platform_seeded",
        archetype="renovation",
    )


def test_validate_cost_plan_output_fails_when_mandatory_seed_missing() -> None:
    output = _typed_output(
        draft_mode="platform_seeded",
        seed_consulted=["seed/role-architect-pm.md"],
    )
    with pytest.raises(WorkflowValidationError, match="mandatory seeds"):
        validate_cost_plan_output(
            output,
            "platform_seeded",
            archetype="renovation",
        )


def test_validate_cost_plan_output_fails_when_typed_table_missing() -> None:
    output = _typed_output(draft_mode="platform_seeded", omit_table=True)
    with pytest.raises(WorkflowValidationError, match="typed cost table"):
        validate_cost_plan_output(
            output,
            "platform_seeded",
            archetype="renovation",
        )


def test_validate_cost_plan_output_fails_when_typed_rows_missing() -> None:
    output = _typed_output(draft_mode="platform_seeded")
    output._cost_items = []
    with pytest.raises(WorkflowValidationError, match="typed cost rows"):
        validate_cost_plan_output(
            output,
            "platform_seeded",
            archetype="renovation",
        )


def test_validate_cost_plan_evidence_grounded_accepts_valid_draft() -> None:
    validate_cost_plan_output(
        _typed_output(draft_mode="evidence_grounded"),
        "evidence_grounded",
        archetype="renovation",
    )


def test_validate_cost_plan_output_rejects_draft_that_omits_evidenced_walsh_figures() -> (
    None
):
    output = _typed_output(
        draft_mode="evidence_grounded",
        items=_sample_typed_items(fee=None, contingency=None, construction_budget=None),
        evidence_refs=[
            "project_evidence:walsh-reno/00-brief-pmp/03-owner-project-brief-walsh-house.md#chunk=1",
            "project_evidence:walsh-reno/02-consultant/architect/02-fee-proposal-atelier-north.md#chunk=1",
        ],
    )

    with pytest.raises(WorkflowValidationError, match="evidenced"):
        validate_cost_plan_output(
            output,
            "evidence_grounded",
            archetype="renovation",
            source_texts=_walsh_source_texts(),
        )


def test_claim_first_violations_detects_collapsed_construction() -> None:
    collapsed = _valid_cost_plan_markdown().replace(
        _cost_breakdown_section(),
        """## Budget reconciliation and cost breakdown

| Cost Code | Category | Cost Items | Budget | Status | Basis |
| --- | --- | --- | --- | --- | --- |
| 1 | Construction | Construction contract | 450000 | Grounded | Claim total |
""",
    )
    source_texts = [
        "Preliminaries 45000\nSiteworks 38000\nFootings and slab 92000\n"
        "Framing 78000\nExternal envelope 65000"
    ]
    violations = claim_first_violations(
        collapsed,
        [
            "project_evidence:greenfield-demo/07-construction/05-progress-claims/"
            "claim-03.md#chunk=1"
        ],
        source_texts=source_texts,
    )
    assert violations
    assert "claim-first" in violations[0].lower()


def test_cost_plan_evidence_grounded_violations_empty_without_refs() -> None:
    assert cost_plan_evidence_grounded_violations(_valid_cost_plan_markdown(), []) == []


def test_ensure_evidence_grounded_cost_plan_scaffold_injects_missing_map_and_facts() -> (
    None
):
    markdown = _valid_cost_plan_markdown()
    refs = ["project_evidence:demo/01-cost/budget.md#chunk=0"]
    violations_before = cost_plan_evidence_grounded_violations(markdown, refs)
    assert any("evidence map" in issue for issue in violations_before)

    repaired = ensure_evidence_grounded_cost_plan_scaffold(markdown, refs)
    violations_after = cost_plan_evidence_grounded_violations(repaired, refs)
    assert not any("evidence map" in issue for issue in violations_after)
    assert not any("Facts" in issue for issue in violations_after)
    assert "Citation key" in repaired
    assert "| Cost-plan area | Evidence status | Ref |" in repaired
    assert "- **Facts**" in repaired


def test_ensure_evidence_grounded_cost_plan_scaffold_normalizes_audit_headings() -> (
    None
):
    markdown = _replace_section(
        _valid_cost_plan_markdown(),
        "Source evidence and audit trail",
        "## Source evidence and audit trail\n\n### Facts\n- Claim schedule on file.\n",
    )
    refs = ["project_evidence:demo/01-cost/budget.md#chunk=0"]
    repaired = ensure_evidence_grounded_cost_plan_scaffold(markdown, refs)
    assert "### Facts" not in repaired
    assert "- **Facts**" in repaired


def test_retrieve_create_cost_plan_sources_platform_seeded_when_no_project_evidence() -> (
    None
):
    platform_passage = _passage(
        project="seed",
        source_type="reference",
        relative_path="seed/cost-management-principles.md",
    )
    with (
        patch(
            "app.workflows.create_cost_plan.load_platform_documents_by_paths",
            new=AsyncMock(return_value=([platform_passage], [])),
        ),
        patch(
            "app.workflows.create_cost_plan.list_cost_evidence_paths",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ) as retrieve,
        patch(
            "app.workflows.create_cost_plan.load_cost_project_evidence_documents",
            new=AsyncMock(return_value=[]),
        ),
    ):
        passages, project_count, _, draft_mode, missing = run_async(
            retrieve_create_cost_plan_sources(AsyncMock(), project=_project())
        )

    retrieve.assert_awaited_once()

    assert project_count == 0
    assert draft_mode == "platform_seeded"
    assert missing == []
    assert passages == [platform_passage]


def test_retrieve_create_cost_plan_skips_semantic_for_complete_context() -> None:
    platform_passage = _passage(
        project="seed",
        source_type="reference",
        relative_path="seed/cost-management-principles.md",
    )
    selection = SimpleNamespace(required_paths=())
    context = SimpleNamespace(critical_unknowns=lambda: [])

    with (
        patch(
            "app.workflows.create_cost_plan.select_seed_knowledge",
            return_value=selection,
        ),
        patch(
            "app.workflows.create_cost_plan.load_platform_documents_by_paths",
            new=AsyncMock(return_value=([platform_passage], [])),
        ),
        patch(
            "app.workflows.create_cost_plan.list_cost_evidence_paths",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.load_cost_project_evidence_documents",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ) as semantic_retrieve,
    ):
        passages, project_count, _, draft_mode, _ = run_async(
            retrieve_create_cost_plan_sources(
                AsyncMock(),
                project=_project(),
                generation_context=context,
            )
        )

    semantic_retrieve.assert_not_awaited()
    assert passages == [platform_passage]
    assert project_count == 0
    assert draft_mode == "platform_seeded"


def test_retrieve_create_cost_plan_sources_uses_session_sequentially() -> None:
    """AsyncSession forbids concurrent awaits; gather on one session is illegal."""
    in_flight = 0
    max_in_flight = 0

    async def _load_platform(_session, _paths, *, content_chars):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.02)
        in_flight -= 1
        return ([], [])

    async def _list_markers(_session, *, project_id):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.02)
        in_flight -= 1
        return []

    with (
        patch(
            "app.workflows.create_cost_plan.load_platform_documents_by_paths",
            new=AsyncMock(side_effect=_load_platform),
        ),
        patch(
            "app.workflows.create_cost_plan.list_cost_evidence_paths",
            new=AsyncMock(side_effect=_list_markers),
        ),
        patch(
            "app.workflows.create_cost_plan.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.load_cost_project_evidence_documents",
            new=AsyncMock(return_value=[]),
        ),
    ):
        run_async(retrieve_create_cost_plan_sources(AsyncMock(), project=_project()))

    assert max_in_flight == 1


def test_retrieve_create_cost_plan_sources_uses_taxonomy_when_archetype_empty() -> None:
    platform_passage = _passage(
        project="seed",
        source_type="reference",
        relative_path="seed/cost-management-principles.md",
    )
    loaded_paths: list[str] = []

    async def _load_platform_documents(_session, paths, *, content_chars):
        loaded_paths.extend(paths)
        return [platform_passage], []

    with (
        patch(
            "app.workflows.create_cost_plan.load_platform_documents_by_paths",
            new=AsyncMock(side_effect=_load_platform_documents),
        ),
        patch(
            "app.workflows.create_cost_plan.list_cost_evidence_paths",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.load_cost_project_evidence_documents",
            new=AsyncMock(return_value=[]),
        ),
    ):
        passages, project_count, _, draft_mode, missing = run_async(
            retrieve_create_cost_plan_sources(
                AsyncMock(),
                project=_project(
                    archetype="",
                    building_class="residential",
                    work_type="refurb",
                    project_metadata={"taxonomy": {"subclasses": ["house"]}},
                ),
            )
        )

    assert project_count == 0
    assert draft_mode == "platform_seeded"
    assert missing == []
    assert passages == [platform_passage]
    assert "seed/cost-management-principles.md" in loaded_paths
    assert "seed/role-architect-pm.md" in loaded_paths
    assert (
        "skills/reference/nsw-residential-cost-breakdown-reference.md" in loaded_paths
    )


def test_retrieve_create_cost_plan_sources_skips_semantic_when_markers_suffice() -> (
    None
):
    platform_passage = _passage(
        project="seed",
        source_type="reference",
        relative_path="seed/cost-management-principles.md",
    )
    evidence_passage = _passage(
        project="demo",
        source_type="project_evidence",
        relative_path="01-cost/budget.md",
    )
    marker_paths = [
        "01-cost/budget.md",
        "07-construction/05-progress-claims/claim-01.md",
        "07-construction/06-variations/var-01.md",
    ]
    with (
        patch(
            "app.workflows.create_cost_plan.load_platform_documents_by_paths",
            new=AsyncMock(return_value=([platform_passage], [])),
        ),
        patch(
            "app.workflows.create_cost_plan.list_cost_evidence_paths",
            new=AsyncMock(return_value=marker_paths),
        ),
        patch(
            "app.workflows.create_cost_plan.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ) as retrieve,
        patch(
            "app.workflows.create_cost_plan.load_cost_project_evidence_documents",
            new=AsyncMock(return_value=[evidence_passage]),
        ),
    ):
        _, project_count, _, draft_mode, _ = run_async(
            retrieve_create_cost_plan_sources(AsyncMock(), project=_project())
        )

    retrieve.assert_not_awaited()
    assert project_count == 1
    assert draft_mode == "evidence_grounded"


def test_normalize_cost_plan_markdown_strips_bullet_prefixed_table_rows() -> None:
    raw = "## Section\n\n- | Col | Val |\n  | --- | --- |\n  | A | 1 |\n"
    normalized = normalize_pmp_markdown(raw)
    assert "- | Col |" not in normalized
    assert "| Col | Val |" in normalized


def test_revision_sync_exports_only_the_workbook_from_typed_state() -> None:
    session = AsyncMock()
    draft = SimpleNamespace(content_markdown="# Cost Plan", provenance_metadata={})
    typed_state = object()
    workbook_metadata = {"row_count": 25}
    with (
        patch(
            "app.workflows.create_cost_plan.sync_cost_plan_draft_workspace",
            new=AsyncMock(return_value="cost_plan_v02.md"),
        ) as sync_markdown,
        patch(
            "app.workflows.create_cost_plan.save_cost_plan_workbook_artifact",
            new=AsyncMock(return_value=workbook_metadata),
        ) as save_workbook,
    ):
        result = run_async(
            sync_cost_plan_revision_artifacts(
                session,
                project=_project(),
                draft=draft,
                typed_state=typed_state,
            )
        )

    assert result == workbook_metadata
    sync_markdown.assert_not_awaited()
    assert save_workbook.await_args.kwargs["typed_state"] is typed_state


def test_typed_compiler_allocates_stated_budget_and_names_actron() -> None:
    from decimal import Decimal

    from app.sitewise.cost_plan_evidence import extract_cost_plan_evidence_pack
    from app.workflows.create_cost_plan import (
        apply_indicative_budget_allocation,
        render_typed_cost_plan_markdown,
        _typed_cost_items,
    )

    project = _project(
        archetype=None,
        building_class="commercial",
        work_type="refurb",
        project_metadata={
            "taxonomy": {
                "subclasses": ["office"],
                "work_scope": ["mechanical_hvac"],
                "budget": "around $180k",
                "assets": [
                    {
                        "type": "Split ducted AC",
                        "count": 2,
                        "location": "service centre and western office",
                        "make_model": "Pioneer",
                        "action": "replace",
                        "replacement_spec": "Actron 30kW split ducted",
                        "notes": "R22 refrigerant; beyond economical repair",
                    }
                ],
            }
        },
    )
    pack = extract_cost_plan_evidence_pack([], [])
    items = _typed_cost_items(project, pack)
    allocated, stated, forecast = apply_indicative_budget_allocation(
        project, items, pack
    )

    assert stated == Decimal("180000.00")
    assert forecast is not None
    assert forecast.construction_envelope_total == Decimal("180000.00")
    envelope = [
        item
        for item in allocated
        if item.category.lower() in {"construction", "pc allowances"}
    ]
    assert envelope
    assert all(item.budget is not None and item.budget > 0 for item in envelope)
    assert any("Actron" in item.item for item in allocated)
    assert any("Pioneer" in item.item for item in allocated)

    markdown = render_typed_cost_plan_markdown(
        "Project Cost Plan",
        allocated,
        stated_budget=stated,
        forecast=forecast,
    )
    assert "ex GST" in markdown
    assert "indicative allocation" in markdown.lower()
    assert "$180,000" in markdown
    assert "Actron" in markdown


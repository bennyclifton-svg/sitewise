import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.database.project import Project
from app.retrieval.schemas import SourcePassage
from app.sitewise.cost_plan_evidence_validation import (
    claim_first_violations,
    cost_plan_evidence_grounded_violations,
    ensure_evidence_grounded_cost_plan_scaffold,
)
from app.sitewise.cost_plan_sources import required_section_headings
from app.workflows.create_cost_plan import (
    CostPlanDraftOutput,
    retrieve_create_cost_plan_sources,
    run_create_cost_plan_workflow,
    validate_cost_plan_output,
)
from app.workflows.create_pmp import WorkflowValidationError, normalize_pmp_markdown
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


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


def _cost_breakdown_section() -> str:
    return """## Cost breakdown by category

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
        "All figures exclude GST. Recommendation: owner confirm working budget by 2026-07-01."
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
    body = "\n\n".join(sections[heading] for heading in required_section_headings("architect-pm"))
    return f"# Project Cost Plan\n\n{body}"


def _valid_evidence_grounded_cost_plan_markdown() -> str:
    markdown = _valid_cost_plan_markdown()
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
        document_metadata={"knowledge_scope": "platform"} if source_type == "reference" else None,
        chunk_metadata={"whole_document": True},
        score=1.0,
    )


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
    output = CostPlanDraftOutput(
        title="Project Cost Plan",
        markdown=_valid_cost_plan_markdown(),
        seed_consulted=_valid_seed_consulted(),
        evidence_refs=[],
        context_refs=["doctrine:docs/clerk-brief.md", "reference:seed/cost-management-principles.md"],
    )
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
    draft.model = "gpt-4o-mini"
    draft.runtime = "clerk-sitewise-create-cost-plan"
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
            "app.workflows.create_cost_plan.run_create_cost_plan_model",
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
    sync_markdown.assert_awaited_once()
    save_workbook.assert_awaited_once()
    assert create_draft.await_args.kwargs["provenance_metadata"]["draft_mode"] == "platform_seeded"
    assert create_draft.await_args.kwargs["workspace_path"].endswith("01-cost/cost_plan_v01.md")
    assert result.draft.provenance_metadata["workbook"]["file_name"] == "Cost_Plan_v01.draft.xlsx"


def test_validate_cost_plan_output_accepts_platform_seeded() -> None:
    output = CostPlanDraftOutput(
        title="Project Cost Plan",
        markdown=_valid_cost_plan_markdown(),
        seed_consulted=_valid_seed_consulted(),
        evidence_refs=[],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    validate_cost_plan_output(
        output,
        "platform_seeded",
        archetype="renovation",
        user_role="architect-pm",
    )


def test_validate_cost_plan_output_fails_when_mandatory_seed_missing() -> None:
    output = CostPlanDraftOutput(
        title="Project Cost Plan",
        markdown=_valid_cost_plan_markdown(),
        seed_consulted=["seed/role-architect-pm.md"],
        evidence_refs=[],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    with pytest.raises(WorkflowValidationError, match="mandatory seeds"):
        validate_cost_plan_output(
            output,
            "platform_seeded",
            archetype="renovation",
            user_role="architect-pm",
        )


def test_validate_cost_plan_output_fails_when_section_missing() -> None:
    markdown = _valid_cost_plan_markdown().replace("## GST basis", "## GST")
    output = CostPlanDraftOutput(
        title="Project Cost Plan",
        markdown=markdown,
        seed_consulted=_valid_seed_consulted(),
        evidence_refs=[],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    with pytest.raises(WorkflowValidationError, match="missing required sections"):
        validate_cost_plan_output(
            output,
            "platform_seeded",
            archetype="renovation",
            user_role="architect-pm",
        )


def test_validate_cost_plan_output_fails_when_greenfield_markers_missing() -> None:
    thin = "\n\n".join(
        f"## {heading}\n\nShort generic paragraph."
        for heading in required_section_headings("architect-pm")
    )
    output = CostPlanDraftOutput(
        title="Project Cost Plan",
        markdown=f"# Project Cost Plan\n\n{thin}",
        seed_consulted=_valid_seed_consulted(),
        evidence_refs=[],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    with pytest.raises(WorkflowValidationError, match="depth markers"):
        validate_cost_plan_output(
            output,
            "platform_seeded",
            archetype="renovation",
            user_role="architect-pm",
        )


def test_validate_cost_plan_evidence_grounded_requires_evidence_map() -> None:
    output = CostPlanDraftOutput(
        title="Project Cost Plan",
        markdown=_valid_cost_plan_markdown(),
        seed_consulted=_valid_seed_consulted(),
        evidence_refs=["project_evidence:greenfield-demo/01-cost/claim.md#chunk=1"],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    with pytest.raises(WorkflowValidationError, match="evidence map"):
        validate_cost_plan_output(
            output,
            "evidence_grounded",
            archetype="renovation",
            user_role="architect-pm",
        )


def test_validate_cost_plan_evidence_grounded_accepts_valid_draft() -> None:
    output = CostPlanDraftOutput(
        title="Project Cost Plan",
        markdown=_valid_evidence_grounded_cost_plan_markdown(),
        seed_consulted=_valid_seed_consulted(),
        evidence_refs=[
            "project_evidence:greenfield-demo/07-construction/05-progress-claims/"
            "claim-03.md#chunk=1"
        ],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    validate_cost_plan_output(
        output,
        "evidence_grounded",
        archetype="renovation",
        user_role="architect-pm",
    )


def test_claim_first_violations_detects_collapsed_construction() -> None:
    collapsed = _valid_cost_plan_markdown().replace(
        _cost_breakdown_section(),
        """## Cost breakdown by category

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


def test_ensure_evidence_grounded_cost_plan_scaffold_injects_missing_map_and_facts() -> None:
    markdown = _valid_cost_plan_markdown()
    refs = ["project_evidence:demo/01-cost/budget.md#chunk=0"]
    violations_before = cost_plan_evidence_grounded_violations(markdown, refs)
    assert any("evidence map" in issue for issue in violations_before)

    repaired = ensure_evidence_grounded_cost_plan_scaffold(markdown, refs)
    violations_after = cost_plan_evidence_grounded_violations(repaired, refs)
    assert not any("evidence map" in issue for issue in violations_after)
    assert not any("Facts" in issue for issue in violations_after)
    assert "Evidence on file:" in repaired
    assert "| Section | Evidence status | Ref |" in repaired
    assert "- **Facts**" in repaired


def test_ensure_evidence_grounded_cost_plan_scaffold_normalizes_audit_headings() -> None:
    markdown = _replace_section(
        _valid_cost_plan_markdown(),
        "Internal audit layer",
        "## Internal audit layer\n\n### Facts\n- Claim schedule on file.\n",
    )
    refs = ["project_evidence:demo/01-cost/budget.md#chunk=0"]
    repaired = ensure_evidence_grounded_cost_plan_scaffold(markdown, refs)
    assert "### Facts" not in repaired
    assert "- **Facts**" in repaired


def test_retrieve_create_cost_plan_sources_platform_seeded_when_no_project_evidence() -> None:
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


def test_retrieve_create_cost_plan_sources_supplements_with_semantic_search() -> None:
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

    retrieve.assert_awaited_once()
    assert project_count == 1
    assert draft_mode == "evidence_grounded"


def test_normalize_cost_plan_markdown_strips_bullet_prefixed_table_rows() -> None:
    raw = "## Section\n\n- | Col | Val |\n  | --- | --- |\n  | A | 1 |\n"
    normalized = normalize_pmp_markdown(raw)
    assert "- | Col |" not in normalized
    assert "| Col | Val |" in normalized

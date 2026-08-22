import asyncio
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.cost_plan.consultant_appointment import (
    APPOINTED_STATUS,
    apply_appointment_to_consultant_facts,
    apply_appointment_to_cost_items,
    apply_appointment_to_pmp_markdown,
    appoint_consultant,
    extract_fee_proposal,
    match_cost_plan_item,
)
from app.cost_plan.schemas import CostItemInput, CostPlanState, DependencySnapshot
from app.database.project import Project
from app.database.source_document import SourceDocument
from app.projects.consultant_facts import map_discipline_to_register_label
from app.projects.project_knowledge import (
    list_shared_project_objects,
    upsert_shared_project_object,
)
from app.schemas.project_snapshot import ProjectSnapshot
from app.sitewise.consultant_register import apply_consultant_register_facts

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DOCUMENT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")

NEWTOWN_TOWN_PLANNER = (
    Path(__file__).resolve().parents[3]
    / "docs/demo-corpus/newtown/02-fee-proposals/town-planning"
    / "verity-urban-planning-vup-2504-41gs.md"
)
NEWTOWN_ARCHITECT = (
    Path(__file__).resolve().parents[3]
    / "docs/demo-corpus/newtown/02-fee-proposals/architectural-services"
    / "bower-lane-architecture-bla-p2603.md"
)


def _item(
    key: str,
    label: str,
    *,
    category: str = "Consultants",
    code: str = "6",
    budget: str | None = "8000",
    committed: str = "0",
) -> CostItemInput:
    return CostItemInput(
        item_key=key,
        cost_code=code,
        category=category,
        item=label,
        budget=Decimal(budget) if budget is not None else None,
        committed=Decimal(committed),
        forecast=Decimal(budget or "0"),
        basis="Not yet appointed",
        status="proposed",
    )


def test_map_discipline_uses_classified_fee_proposal_labels() -> None:
    assert map_discipline_to_register_label("Town Planning") == "Town Planner"
    assert map_discipline_to_register_label("Architectural Services") == "Architect"
    assert map_discipline_to_register_label("Structural Engineering") == "Structural"
    assert map_discipline_to_register_label("Civil") == "Civil"
    assert map_discipline_to_register_label("Certification") == "Certifier"


def test_looks_like_fee_proposal_prefers_commercial_type() -> None:
    from app.cost_plan.consultant_appointment import _looks_like_fee_proposal

    classified = SourceDocument(
        filename="notes.md",
        relative_path="02-consultant/structural/notes.md",
        document_metadata={"commercial_type": "fee_proposal"},
        normalized_content="",
        project="demo",
        phase="procurement",
        document_class="commercial",
    )
    report_named_quote = SourceDocument(
        filename="quote-looking-report.pdf",
        relative_path="01-reports/quote-looking-report.pdf",
        document_metadata={},
        normalized_content="",
        project="demo",
        phase="brief-planning",
        document_class="report",
    )
    unknown_named = SourceDocument(
        filename="Acme Fee Proposal.pdf",
        relative_path="_inbox/Acme Fee Proposal.pdf",
        document_metadata={},
        normalized_content="",
        project="demo",
        phase="procurement",
        document_class="unknown",
    )
    assert _looks_like_fee_proposal(classified) is True
    assert _looks_like_fee_proposal(report_named_quote) is False
    assert _looks_like_fee_proposal(unknown_named) is True


def test_extract_fee_proposal_reads_newtown_town_planner() -> None:
    content = NEWTOWN_TOWN_PLANNER.read_text(encoding="utf-8")
    document = SourceDocument(
        filename="verity-urban-planning-vup-2504-41gs.md",
        relative_path="02-fee-proposals/town-planning/verity-urban-planning-vup-2504-41gs.md",
        document_metadata={
            "discipline": "Town Planning",
            "issuing_firm": "Verity Urban Planning",
        },
        normalized_content=content,
        project="newtown",
        phase="procurement",
        document_class="fee_proposal",
    )

    proposal = extract_fee_proposal(document)

    assert proposal.discipline == "Town Planner"
    assert proposal.firm == "Verity Urban Planning"
    assert proposal.fee_ex_gst == Decimal("9900.00")
    assert proposal.proposal_reference == "VUP-2504-41GS"


def test_extract_fee_proposal_reads_newtown_architect() -> None:
    content = NEWTOWN_ARCHITECT.read_text(encoding="utf-8")
    document = SourceDocument(
        filename="bower-lane-architecture-bla-p2603.md",
        relative_path="02-fee-proposals/architectural-services/bower-lane.md",
        document_metadata={
            "discipline": "Architectural",
            "issuing_firm": "Bower Lane Architecture",
        },
        normalized_content=content,
        project="newtown",
        phase="procurement",
        document_class="fee_proposal",
    )

    proposal = extract_fee_proposal(document)

    assert proposal.discipline == "Architect"
    assert proposal.firm == "Bower Lane Architecture"
    assert proposal.fee_ex_gst == Decimal("82000.00")
    assert proposal.proposal_reference == "BLA-P2603"


def test_nominated_fee_overrides_extracted_total() -> None:
    document = SourceDocument(
        filename="verity.md",
        relative_path="verity.md",
        document_metadata={"discipline": "Town Planning", "issuing_firm": "Verity"},
        normalized_content="Professional fees excl GST | $9,900.00",
        project="newtown",
        phase="procurement",
        document_class="fee_proposal",
    )

    proposal = extract_fee_proposal(document, nominated_fee_ex_gst=Decimal("12000"))

    assert proposal.fee_ex_gst == Decimal("12000")
    assert proposal.fee_source == "nominated"


def test_match_cost_plan_item_uses_discipline_not_schema_hunt() -> None:
    items = [
        _item("struct", "Structural engineer"),
        _item("pm", "Architect / PM fee", category="Fees and charges", code="1"),
        _item("council", "Planning, certification and authority fees", category="Fees and charges", code="2"),
    ]

    assert match_cost_plan_item(items, "Town Planner") is None
    assert match_cost_plan_item(items, "Architect").item_key == "pm"
    assert match_cost_plan_item(items, "Structural Engineer").item_key == "struct"


def test_apply_appointment_sets_approved_contract_and_adds_missing_row() -> None:
    items = [
        _item("struct", "Structural engineer"),
        _item("pm", "Architect / PM fee", category="Fees and charges", code="1"),
    ]

    updated, changed_key = apply_appointment_to_cost_items(
        items,
        discipline="Town Planner",
        firm="Verity Urban Planning",
        fee_ex_gst=Decimal("9900.00"),
        basis="Appointed (Verity Urban Planning); fee proposal VUP-2504-41GS",
    )

    town = next(item for item in updated if item.item_key == changed_key)
    assert town.item == "Town Planner"
    assert town.category == "Consultants"
    assert town.committed == Decimal("9900.00")
    assert town.forecast == Decimal("9900.00")
    assert town.status == "confirmed"
    assert "Appointed" in town.basis


def test_apply_appointment_updates_existing_structural_row() -> None:
    items = [_item("struct", "Structural engineer", budget="8000")]

    updated, changed_key = apply_appointment_to_cost_items(
        items,
        discipline="Structural Engineer",
        firm="Ardent Structural",
        fee_ex_gst=Decimal("11500.00"),
        basis="Appointed (Ardent Structural); fee proposal AS-P26118",
    )

    row = next(item for item in updated if item.item_key == changed_key)
    assert row.item_key == "struct"
    assert row.budget == Decimal("8000")
    assert row.committed == Decimal("11500.00")
    assert row.forecast == Decimal("11500.00")


def test_pmp_consultants_register_records_appointed_fee() -> None:
    project = Project(project_metadata={})
    apply_appointment_to_consultant_facts(
        project,
        discipline="Town Planner",
        firm="Verity Urban Planning",
        fee_ex_gst=Decimal("9900.00"),
        evidence_path="02-fee-proposals/town-planning/verity.md",
    )
    facts = list_shared_project_objects(project, kind="consultant")
    assert facts[0].value["status"] == APPOINTED_STATUS
    assert facts[0].value["fee"] == "$9,900.00 ex GST"

    markdown = """## Consultants
| Discipline | Firm | Fee | Status | Citation |
|---|---|---|---|---|
| Architect | TBC |  | Assumption / Not evidenced | — |
| Town Planner | TBC |  | Assumption / Not evidenced | — |

## Next
"""
    patched = apply_appointment_to_pmp_markdown(markdown, project=project)
    assert (
        "| Town Planner | Verity Urban Planning | $9,900.00 ex GST | "
        f"{APPOINTED_STATUS} |"
    ) in patched


def test_apply_consultant_register_facts_overwrites_fee_when_appointed() -> None:
    project = Project(project_metadata={})
    apply_appointment_to_consultant_facts(
        project,
        discipline="Structural Engineer",
        firm="Ardent Structural",
        fee_ex_gst=Decimal("11500.00"),
        evidence_path="ardent.md",
    )
    markdown = """## Consultants
| Discipline | Firm | Fee | Status | Citation |
|---|---|---|---|---|
| Structural Engineer | TBC |  | Assumption / Not evidenced | — |
"""
    patched = apply_consultant_register_facts(markdown, project=project)
    assert "$11,500.00 ex GST" in patched
    assert APPOINTED_STATUS in patched
    assert "Ardent Structural" in patched


def test_appoint_consultant_writes_approved_contract_without_schema_hunt() -> None:
    project = Project(id=PROJECT_ID, owner_user_id=USER_ID, project_metadata={})
    document = SourceDocument(
        id=DOCUMENT_ID,
        project_id=PROJECT_ID,
        filename="verity-urban-planning-vup-2504-41gs.md",
        relative_path="02-fee-proposals/town-planning/verity.md",
        document_metadata={
            "discipline": "Town Planning",
            "issuing_firm": "Verity Urban Planning",
        },
        normalized_content=NEWTOWN_TOWN_PLANNER.read_text(encoding="utf-8"),
        project="newtown",
        phase="procurement",
        document_class="fee_proposal",
    )
    base = CostPlanState(
        project_id=PROJECT_ID,
        version=1,
        dependency_snapshot=DependencySnapshot(
            profile_revision=1,
            evidence_fingerprint="evidence",
            decision_set_revision=1,
            runtime_version="test",
        ),
        items=[_item("struct", "Structural engineer")],
    )
    published: list[CostItemInput] = []
    upsert_kwargs: dict = {}
    snapshot = ProjectSnapshot.model_validate(
        {
            "generated_at": datetime.now(UTC),
            "content_fingerprint": "snapshot-v2",
            "identity": {
                "project_id": PROJECT_ID,
                "title": "House",
                "slug": "house",
                "workspace_path": "projects/house",
                "phase": "design",
                "status": "active",
                "site_address": {"status": "needs_input"},
                "client": {"status": "needs_input"},
            },
            "profile": {
                "project_id": PROJECT_ID,
                "profile_revision": 2,
                "building_class": "residential",
                "work_type": "extend",
                "subclasses": ["house"],
                "scale": {},
                "complexity": {},
                "work_scope": [],
                "user_role": "architect-pm",
                "state": "NSW",
            },
            "decisions": {"set_revision": 3, "items": []},
            "evidence": {
                "fingerprint": "evidence-after-fee-proposals",
                "active_count": 3,
                "fingerprint_complete": True,
                "ingest_failure_count": 0,
                "ingest_failures": [],
            },
            "confirmed_inputs": {},
            "open_profile_proposals": [],
        }
    )

    async def upsert(*args, item, **kwargs):
        published.append(item)
        upsert_kwargs.update(kwargs)
        return SimpleNamespace(state=base.model_copy(update={"version": 2}))

    async def write_fact(*args, project, kind, object_id, update, source, **kwargs):
        return upsert_shared_project_object(
            project,
            kind=kind,
            object_id=object_id,
            update=update,
            source=source,
        )

    pmp = SimpleNamespace(
        id=uuid.uuid4(),
        version=3,
        content_markdown="""## Consultants
| Discipline | Firm | Fee | Status | Citation |
|---|---|---|---|---|
| Town Planner | TBC |  | Assumption / Not evidenced | — |
""",
    )
    revised = SimpleNamespace(version=4)

    session = MagicMock()
    session.get = AsyncMock(return_value=document)

    with (
        patch(
            "app.cost_plan.consultant_appointment.get_cost_plan",
            new=AsyncMock(return_value=base),
        ),
        patch(
            "app.cost_plan.consultant_appointment.get_project_snapshot",
            new=AsyncMock(return_value=snapshot),
        ),
        patch(
            "app.cost_plan.consultant_appointment.upsert_cost_item",
            new=AsyncMock(side_effect=upsert),
        ),
        patch(
            "app.cost_plan.consultant_appointment.schedule_cost_plan_workbook_rebuild"
        ),
        patch(
            "app.cost_plan.consultant_appointment.write_shared_project_object",
            new=AsyncMock(side_effect=write_fact),
        ),
        patch(
            "app.cost_plan.consultant_appointment.get_latest_draft_artifact",
            new=AsyncMock(return_value=pmp),
        ),
            patch(
                "app.cost_plan.consultant_appointment.revise_workflow_artefact",
                new=AsyncMock(return_value=revised),
            ) as revise,
            patch(
                "app.cost_plan.consultant_appointment.record_consultant_appointment",
                new=AsyncMock(return_value=True),
            ),
        ):
        result = asyncio.run(
            appoint_consultant(
                session,
                project=project,
                author_user_id=USER_ID,
                source_document_id=DOCUMENT_ID,
            )
        )

    assert result.discipline == "Town Planner"
    assert result.firm == "Verity Urban Planning"
    assert result.approved_contract == Decimal("9900.00")
    assert result.cost_plan_version == 2
    assert result.pmp_updated is True
    assert result.pmp_version == 4
    assert published[0].committed == Decimal("9900.00")
    assert published[0].item == "Town Planner"
    assert upsert_kwargs.get("current_snapshot") is None
    rebased = upsert_kwargs.get("dependency_snapshot")
    assert rebased is not None
    assert rebased.evidence_fingerprint == "evidence-after-fee-proposals"
    assert "Approved Contract" not in revise.await_args.kwargs["content_markdown"]
    assert "Verity Urban Planning" in revise.await_args.kwargs["content_markdown"]
    assert "$9,900.00 ex GST" in revise.await_args.kwargs["content_markdown"]

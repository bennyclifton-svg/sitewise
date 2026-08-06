from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path

from app.cost_plan.evidence_reconciliation import (
    CostEvidenceDocument,
    build_cost_evidence_reconciliation,
)
from app.cost_plan.schemas import CostItemInput, CostPlanState, DependencySnapshot


REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_ROOT = (
    REPO_ROOT
    / "data"
    / "synthetic-mobilisation-evidence"
    / "kavanagh-residence-cost-files"
)
FIXTURE_ROOT = Path(__file__).with_name("fixtures")
PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _item(
    cost_code: str,
    category: str,
    item: str,
    budget: str,
) -> CostItemInput:
    return CostItemInput(
        item_key=cost_code,
        cost_code=cost_code,
        category=category,
        item=item,
        budget=budget,
        forecast=budget,
        basis="Planning allowance - not a quotation",
    )


def _cost_plan() -> CostPlanState:
    return CostPlanState(
        project_id=PROJECT_ID,
        version=2,
        dependency_snapshot=DependencySnapshot(
            profile_revision=3,
            evidence_fingerprint="before-upload",
            decision_set_revision=1,
            runtime_version="test",
        ),
        items=[
            _item("1", "Fees and charges", "Planning fees", "12500"),
            _item("2", "Fees and charges", "Certifier fees", "12500"),
            _item("3", "Consultants", "Architect / PM", "12500"),
            _item("4", "Consultants", "Structural engineer", "22000"),
            _item("5", "Consultants", "Surveyor", "8500"),
            _item("6", "Construction", "Preliminaries", "179000"),
            _item("7", "Construction", "Siteworks", "89500"),
            _item("8", "Construction", "Footings and slab", "89500"),
            _item("9", "Construction", "Framing", "89500"),
            _item("10", "Construction", "External envelope", "304000"),
            _item("11", "Construction", "Partitions and doors", "196500"),
            _item("12", "Construction", "Kitchen and bathrooms", "107000"),
            _item("13", "Construction", "Building services", "179000"),
            _item(
                "14",
                "Contingency / allowances",
                "Construction contingency",
                "92550",
            ),
        ],
    )


def _documents() -> list[CostEvidenceDocument]:
    names = [
        "01-fee-proposal-quoin-architecture.md",
        "02-fee-proposal-catenary-structures.md",
        "03-fee-proposal-flowline-hydraulics.md",
        "04-fee-proposal-vertex-cost-advisory.md",
        "05-building-proposal-ironbark-main-works.md",
    ]
    return [
        CostEvidenceDocument(
            id=uuid.uuid5(PROJECT_ID, name),
            filename=name,
            relative_path=f"04-projects/kavanagh/_inbox/{name}",
            content=(EVIDENCE_ROOT / name).read_text(encoding="utf-8"),
        )
        for name in names
    ]


def test_latest_cost_evidence_replaces_allowances_with_received_proposals() -> None:
    result = build_cost_evidence_reconciliation(_cost_plan(), _documents())

    by_item = {item.item: item for item in result.proposed_items}
    assert by_item["Architect / PM"].budget == Decimal("96000.00")
    assert by_item["Structural engineer"].budget == Decimal("41800.00")
    assert by_item["Hydraulic / wastewater"].budget == Decimal("32500.00")
    assert by_item["Quantity surveyor / cost advisory"].budget == Decimal("45000.00")

    construction = [
        item for item in result.proposed_items if item.category == "Construction"
    ]
    assert sum((item.budget or Decimal("0")) for item in construction) == Decimal(
        "1234000.00"
    )
    assert all(item.forecast == item.budget for item in result.proposed_items)
    assert all(item.status == "proposed" for item in result.proposed_items)
    assert all(item.source_refs for item in result.proposed_items)
    assert result.issues == ()
    assert {proposal.kind for proposal in result.received_proposals} == {
        "architecture",
        "structural",
        "hydraulic",
        "cost_advisory",
        "main_works",
    }


def test_multiple_main_works_proposals_are_not_silently_selected() -> None:
    documents = _documents()
    main_works = documents[-1]
    documents.append(
        CostEvidenceDocument(
            id=uuid.uuid4(),
            filename="competing-main-works.md",
            relative_path="04-projects/kavanagh/_inbox/competing-main-works.md",
            content=main_works.content.replace(
                "Ironbark Main Works Pty Ltd", "Competing Main Works Pty Ltd"
            ).replace("IMW-KAV-T-026", "CMP-KAV-T-001"),
        )
    )

    result = build_cost_evidence_reconciliation(_cost_plan(), documents)

    assert not any(item.category == "Construction" for item in result.proposed_items)
    assert any(
        "multiple main works proposals" in issue.lower() for issue in result.issues
    )


def test_contract_price_schedule_preserves_every_priced_source_row() -> None:
    filename = "ANX V CONTACT PRICE SCHEDULE [B].pdf"
    document_id = uuid.uuid5(PROJECT_ID, filename)
    document = CostEvidenceDocument(
        id=document_id,
        filename=filename,
        relative_path=f"04-projects/demo/_inbox/{filename}",
        content=(FIXTURE_ROOT / "large_contract_price_schedule.md").read_text(
            encoding="utf-8"
        ),
    )

    result = build_cost_evidence_reconciliation(_cost_plan(), [document])

    assert result.issues == ()
    assert len(result.received_proposals) == 1
    proposal = result.received_proposals[0]
    assert proposal.kind == "main_works"
    assert proposal.total_ex_gst == Decimal("5870686.00")
    assert len(proposal.line_items) == 37

    construction = [
        item for item in result.proposed_items if item.category == "Construction"
    ]
    assert len(construction) == 37
    assert sum((item.budget or Decimal("0")) for item in construction) == Decimal(
        "5870686.00"
    )
    assert construction[0].cost_code == "1.01"
    assert construction[0].item == "Preliminaries"
    assert construction[-1].cost_code == "2.37"
    assert all(
        item.source_refs[0]["document_id"] == str(document_id)
        for item in construction
    )

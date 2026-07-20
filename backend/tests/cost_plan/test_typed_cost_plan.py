from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from openpyxl import load_workbook
from pydantic import ValidationError

from app.cost_plan.calculations import CostPlanCalculationError, calculate_totals
from app.cost_plan.dependencies import (
    DEFAULT_EDGES,
    DependencyCycleError,
    stale_reasons,
    validate_acyclic,
)
from app.cost_plan.import_legacy import parse_legacy_draft
from app.cost_plan.renderer import render_cost_plan_markdown
from app.cost_plan.schemas import CostItemInput, CostPlanState, DependencySnapshot
from app.cost_plan.service import refresh_cost_plan, upsert_cost_item
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.mcp_bridge.tender_cost_handoff import map_tender_handoff
from app.projects.workflow_capabilities import (
    APPROVED_TENDER_HANDOFF,
    CREATE_COST_PLAN,
    EDIT_COST_PLAN,
    REFRESH_COST_PLAN,
    workflow_capabilities,
)
from app.schemas.project_snapshot import ProjectSnapshot
from app.sitewise.cost_plan_workbook import build_typed_cost_plan_workbook
from tender.schemas import ApprovedTenderCostHandoff, ApprovedTenderCostItem
from tests.conftest import run_async

PROJECT_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
DRAFT_ID = uuid.UUID("30000000-0000-0000-0000-000000000001")


def _dependencies() -> DependencySnapshot:
    return DependencySnapshot(
        profile_revision=2,
        evidence_fingerprint="evidence-v2",
        decision_set_revision=3,
        runtime_version="test-runtime-v1",
    )


def _item(**updates) -> CostItemInput:
    values = {
        "item_key": "demolition",
        "cost_code": "01-100",
        "category": "Enabling works",
        "item": "Demolition",
        "budget": Decimal("80000.00"),
        "committed": Decimal("10000.00"),
        "forecast": Decimal("85000.00"),
        "paid": Decimal("5000.00"),
        "allowance_type": "ps",
        "basis": "Builder scope and QS allowance",
        "source_refs": [{"document_id": "doc-1", "hash": "abc"}],
        "confidence": Decimal("0.9"),
    }
    values.update(updates)
    return CostItemInput(**values)


def _state(**updates) -> CostPlanState:
    values = {
        "project_id": PROJECT_ID,
        "version": 1,
        "contingency_percent": Decimal("5"),
        "escalation_percent": Decimal("2.5"),
        "gst_treatment": "exclusive",
        "assumptions": {"pricing_date": "2026-07-19"},
        "dependency_snapshot": _dependencies(),
        "items": [_item()],
    }
    values.update(updates)
    return CostPlanState(**values)


def _snapshot() -> ProjectSnapshot:
    return ProjectSnapshot.model_validate(
        {
            "generated_at": datetime.now(UTC),
            "content_fingerprint": "snapshot-v2",
            "identity": {
                "project_id": PROJECT_ID,
                "title": "House",
                "slug": "house",
                "workspace_path": "projects/house",
                "phase": "construction",
                "status": "active",
                "site_address": {"status": "needs_input"},
                "client": {"status": "needs_input"},
            },
            "profile": {
                "project_id": PROJECT_ID,
                "profile_revision": 2,
                "building_class": "residential",
                "work_type": "refurb",
                "subclasses": ["house"],
                "scale": {},
                "complexity": {},
                "work_scope": [],
                "user_role": "architect-pm",
                "state": "NSW",
            },
            "decisions": {"set_revision": 3, "items": []},
            "evidence": {
                "fingerprint": "evidence-v2",
                "active_count": 1,
                "fingerprint_complete": True,
                "ingest_failure_count": 0,
                "ingest_failures": [],
            },
            "confirmed_inputs": {},
            "open_profile_proposals": [],
        }
    )


@pytest.mark.parametrize(
    ("gst_treatment", "gst", "exclusive", "inclusive"),
    [
        ("exclusive", "887.91", "8879.06", "9766.97"),
        ("inclusive", "807.19", "8071.87", "8879.06"),
        ("not_applicable", "0.00", "8879.06", "8879.06"),
    ],
)
def test_decimal_arithmetic_is_exact_across_gst_rules(
    gst_treatment: str, gst: str, exclusive: str, inclusive: str
) -> None:
    item = _item(
        budget=None,
        quantity=Decimal("3"),
        unit="m2",
        rate=Decimal("2750"),
        committed=Decimal("8000"),
        forecast=Decimal("9000"),
        paid=Decimal("0"),
    )
    totals = calculate_totals(
        [item],
        contingency_percent=Decimal("5"),
        escalation_percent=Decimal("2.5"),
        gst_treatment=gst_treatment,
    )
    assert totals.budget == Decimal("8250.00")
    assert totals.variance == Decimal("-750.00")
    assert totals.allowances == Decimal("8250.00")
    assert totals.gst == Decimal(gst)
    assert totals.total_excluding_gst == Decimal(exclusive)
    assert totals.total_including_gst == Decimal(inclusive)


def test_float_and_incomplete_unit_rate_inputs_are_rejected() -> None:
    with pytest.raises(ValidationError, match="must not be supplied as float"):
        _item(budget=80_000.0)
    with pytest.raises(ValidationError, match="must be supplied together"):
        _item(budget=None, quantity="10", unit="m2")
    with pytest.raises(CostPlanCalculationError, match="does not equal"):
        calculate_totals(
            [_item(budget="99", quantity="2", unit="ea", rate="10")],
            contingency_percent=Decimal("0"),
            escalation_percent=Decimal("0"),
            gst_treatment="exclusive",
        )


def test_markdown_and_workbook_render_the_same_typed_rows_and_totals() -> None:
    state = _state()
    markdown = render_cost_plan_markdown(state)
    workbook = build_typed_cost_plan_workbook(project_title="House", state=state)
    loaded = load_workbook(BytesIO(workbook.content), data_only=False)
    summary = loaded["Summary"]

    assert "| 01-100 | Enabling works | Demolition | $80,000.00 |" in markdown
    assert "Total including GST: **$94,710.00**" in markdown
    assert summary["A5"].value == "01-100"
    assert summary["C5"].value == "Demolition"
    assert Decimal(summary["D5"].value) == Decimal("80000.00")
    assert workbook.row_count == 1


def test_legacy_import_never_invents_invalid_rows_and_reports_reconciliation() -> None:
    draft = DraftArtifact(
        id=DRAFT_ID,
        project_id=PROJECT_ID,
        workflow_type="create_cost_plan",
        version=4,
        status="accepted",
        title="Accepted Cost Plan",
        workspace_path="cost.md",
        author_user_id=USER_ID,
        content_markdown="""# Cost Plan

| Cost code | Category | Cost item | Budget | Basis |
|---|---|---|---:|---|
| 01 | Enabling | Demolition | $80,000 | Quote |
| | Structure | Framing | $100,000 | Estimate |
| 03 | Services | Electrical | TBC | Estimate |
| | | Grand total | $200,000 | |
""",
        runtime="legacy",
    )
    result = parse_legacy_draft(draft)
    assert [item.cost_code for item in result.items] == ["01"]
    assert result.parsed_budget_total == Decimal("80000.00")
    assert result.source_budget_total == Decimal("200000")
    assert len(result.warnings) == 3
    assert all(item.item_key != "2" for item in result.items)


def test_dependency_graph_and_stale_reasons_are_deterministic() -> None:
    validate_acyclic(DEFAULT_EDGES)
    with pytest.raises(DependencyCycleError):
        validate_acyclic((*DEFAULT_EDGES, ("project_plan", "cost_plan")))

    recorded = _dependencies()
    current = _snapshot().model_copy(deep=True)
    current.profile.profile_revision = 3
    current.evidence.fingerprint = "evidence-v3"
    current.decisions.set_revision = 4
    assert stale_reasons(
        recorded,
        current,
        current_upstream_versions={"report": 2},
        tender_approved_after_cost_plan=True,
    ) == [
        "profile_changed",
        "evidence_added_removed_or_revised",
        "decision_changed",
        "tender_approved_after_cost_plan",
    ]


def test_capability_matrix_publishes_all_typed_cost_actions() -> None:
    matrix = workflow_capabilities(_snapshot())
    for name in (
        CREATE_COST_PLAN,
        REFRESH_COST_PLAN,
        EDIT_COST_PLAN,
        APPROVED_TENDER_HANDOFF,
    ):
        capability = matrix.capabilities[name]
        assert capability.status == "supported"
        assert capability.reference_coverage
    assert matrix.capabilities[APPROVED_TENDER_HANDOFF].required_confirmations == [
        "approved_frozen_qs_passed_tender",
        "selected_quote_and_package",
        "confirm_apply_as_proposal",
    ]


def test_tender_handoff_maps_financial_qualifiers_without_ranking() -> None:
    quote_id = uuid.uuid4()
    handoff = ApprovedTenderCostHandoff(
        project_id=PROJECT_ID,
        comparison_id=uuid.uuid4(),
        report_id=uuid.uuid4(),
        report_version=2,
        report_frozen=True,
        mandatory_qa_resolved=True,
        qs_gate_passed=True,
        operator_approved_by=USER_ID,
        selected_quote_id=quote_id,
        package_scope="Main works",
        comparison_version="comparison-hash",
        quote_version="quote-hash",
        source_documents=[{"document_id": "doc", "content_hash": "hash"}],
        mapped_items=[
            ApprovedTenderCostItem(
                item_key="tender-01",
                cost_code="01",
                category="Works",
                item="Main works",
                amount_cents=12_345_678,
                source_refs=[{"document_id": "doc"}],
            )
        ],
        stated_total_cents=12_500_000,
        comparable_total_cents=12_345_678,
        gst_treatment="inclusive",
        exclusions=["Landscaping"],
        qualifications=["Subject to final design"],
        idempotency_key="tender-cost:stable",
    )
    proposal = map_tender_handoff(handoff)
    assert proposal.selected_option_id == quote_id
    assert proposal.items[0].budget == Decimal("123456.78")
    assert proposal.financial_qualifiers["exclusions"] == ["Landscaping"]
    assert "rank" not in str(proposal.model_dump()).lower()


def test_row_upsert_changes_only_the_named_item() -> None:
    base = _state(
        items=[
            _item(),
            _item(
                item_key="structure",
                cost_code="02-100",
                item="Structure",
                allowance_type="none",
            ),
        ]
    )
    replacement = _item(budget="90000")
    published = base.model_copy(
        update={"version": 2, "items": [replacement, base.items[1]]}
    )
    project = Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="house",
        title="House",
        workspace_path="projects/house",
    )
    with (
        patch(
            "app.cost_plan.service._base_for_mutation",
            new=AsyncMock(return_value=base),
        ),
        patch(
            "app.cost_plan.service._publish_state",
            new=AsyncMock(return_value=published),
        ) as publish_state,
    ):
        result = run_async(
            upsert_cost_item(
                AsyncMock(),
                project=project,
                author_user_id=USER_ID,
                expected_base_version=1,
                item=replacement,
            )
        )
    state_sent = publish_state.await_args.kwargs["state"]
    assert result.changed_item_keys == ["demolition"]
    assert [item.item_key for item in state_sent.items] == ["demolition", "structure"]
    assert state_sent.items[1] == base.items[1]


def test_refresh_preserves_locked_and_manual_rows_as_explicit_conflicts() -> None:
    locked = _item(locked=True, status="manual")
    base = _state(items=[locked])
    proposal = _item(budget="90000", locked=False, status="proposed")
    project = Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="house",
        title="House",
        workspace_path="projects/house",
    )
    published = base.model_copy(update={"version": 2})
    with (
        patch(
            "app.cost_plan.service._base_for_mutation",
            new=AsyncMock(return_value=base),
        ),
        patch(
            "app.cost_plan.service._publish_state",
            new=AsyncMock(return_value=published),
        ) as publish_state,
    ):
        result = run_async(
            refresh_cost_plan(
                AsyncMock(),
                project=project,
                author_user_id=USER_ID,
                expected_base_version=1,
                current_snapshot=_snapshot(),
                proposed_items=[proposal],
                dependency_snapshot=_dependencies(),
            )
        )
    state_sent = publish_state.await_args.kwargs["state"]
    assert state_sent.items == [locked]
    assert result.changed_item_keys == []
    assert result.conflicts == ["demolition"]
    assert result.state.status == "proposed"

from datetime import date

import pytest

from app.sitewise.cost_plan_evidence import extract_cost_plan_evidence_pack
from app.workflows.cost_plan_narrative import (
    CostPlanNarrativeOutput,
    validate_cost_plan_narrative_output,
)
from app.workflows.create_pmp import WorkflowValidationError
from app.workflows.pmp_narrative import RiskRow
from tests.sitewise.test_cost_plan_evidence import _read


def _full_chen_pack():
    texts = [
        _read("01-engagement-letter-harrison-clarke-studio.md"),
        _read("02-fee-proposal-harrison-clarke-studio.md"),
        _read("03-owner-project-brief-chen-residence.md"),
        _read("09-planning-pathway-memo-harrison-clarke.md"),
        _read("06-geotechnical-report-terratech.md"),
        _read("11-master-programme-chen-residence.md"),
        _read("12-certifier-appointment-chen-residence.md"),
    ]
    return extract_cost_plan_evidence_pack(texts, [])


def test_validate_cost_plan_narrative_rejects_fee_exceeding_ceiling_misread() -> None:
    pack = _full_chen_pack()
    output = CostPlanNarrativeOutput(
        judgements=[
            "Architect fees at $148,500 exceed the construction ceiling.",
            "DA + CC pathway is adopted.",
        ],
        recommendations=[
            "Prepare tender docs by 2026-07-05.",
            "Monitor programme to September 2026 by 2026-07-05.",
            "Declare Linden conflict by 2026-07-05.",
        ],
        risk_rows=[
            RiskRow(risk="A", owner="Owner", status="Open", next_action="Act", due_date="2026-07-05"),
            RiskRow(risk="B", owner="Owner", status="Open", next_action="Act", due_date="2026-07-05"),
            RiskRow(risk="C", owner="Owner", status="Open", next_action="Act", due_date="2026-07-05"),
            RiskRow(risk="D", owner="Owner", status="Open", next_action="Act", due_date="2026-07-05"),
            RiskRow(risk="E", owner="Owner", status="Open", next_action="Act", due_date="2026-07-05"),
        ],
        next_steps=[
            "Step one by 2026-07-05.",
            "Step two by 2026-07-05.",
            "Step three by 2026-07-05.",
        ],
    )

    with pytest.raises(WorkflowValidationError, match="not exceeding it"):
        validate_cost_plan_narrative_output(output, pack, run_date=date(2026, 6, 8))


def test_validate_cost_plan_narrative_rejects_geotech_commission_when_on_file() -> None:
    pack = _full_chen_pack()
    output = CostPlanNarrativeOutput(
        judgements=[
            "Tender must reconcile to the $1,850,000 ceiling.",
            "Geotechnical report is on file for footing design.",
        ],
        recommendations=[
            "Engage a geotechnical consultant by 2026-07-05.",
            "Prepare tender docs by 2026-07-05.",
            "Declare Linden conflict by 2026-07-05.",
        ],
        risk_rows=[
            RiskRow(risk="A", owner="Owner", status="Open", next_action="Act", due_date="2026-07-05"),
            RiskRow(risk="B", owner="Owner", status="Open", next_action="Act", due_date="2026-07-05"),
            RiskRow(risk="C", owner="Owner", status="Open", next_action="Act", due_date="2026-07-05"),
            RiskRow(risk="D", owner="Owner", status="Open", next_action="Act", due_date="2026-07-05"),
            RiskRow(risk="E", owner="Owner", status="Open", next_action="Act", due_date="2026-07-05"),
        ],
        next_steps=[
            "Step one by 2026-07-05.",
            "Step two by 2026-07-05.",
            "Step three by 2026-07-05.",
        ],
    )

    with pytest.raises(WorkflowValidationError, match="geotechnical"):
        validate_cost_plan_narrative_output(output, pack, run_date=date(2026, 6, 8))


def test_validator_rejects_generic_risk_owner() -> None:
    pack = _full_chen_pack()
    output = CostPlanNarrativeOutput(
        judgements=[
            "Tender must reconcile to the $1,850,000 ceiling.",
            "DA + CC pathway is adopted.",
        ],
        recommendations=[
            "Prepare tender docs by 2026-07-05.",
            "Confirm planning pathway by 2026-07-05.",
            "Declare Linden conflict by 2026-07-05.",
        ],
        risk_rows=[
            RiskRow(
                risk="A",
                owner="Project Team",
                status="Open",
                next_action="Act by 2026-07-05",
                due_date="2026-07-05",
            ),
            RiskRow(
                risk="B",
                owner="Project Team",
                status="Open",
                next_action="Act by 2026-07-05",
                due_date="2026-07-05",
            ),
            RiskRow(
                risk="C",
                owner="Project Team",
                status="Open",
                next_action="Act by 2026-07-05",
                due_date="2026-07-05",
            ),
            RiskRow(
                risk="D",
                owner="Project Team",
                status="Open",
                next_action="Act by 2026-07-05",
                due_date="2026-07-05",
            ),
            RiskRow(
                risk="E",
                owner="Project Team",
                status="Open",
                next_action="Act by 2026-07-05",
                due_date="2026-07-05",
            ),
        ],
        next_steps=[
            "Step one by 2026-07-05.",
            "Step two by 2026-07-05.",
            "Step three by 2026-07-05.",
        ],
    )

    with pytest.raises(WorkflowValidationError, match="generic"):
        validate_cost_plan_narrative_output(output, pack, run_date=date(2026, 6, 8))

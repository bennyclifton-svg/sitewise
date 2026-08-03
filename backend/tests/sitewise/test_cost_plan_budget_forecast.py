from decimal import Decimal

import pytest

from app.sitewise.cost_plan_budget_forecast import (
    AdoptedBudgetForecastError,
    build_adopted_budget_forecast,
)


GREENBANK_COST_PLAN = """# Greenbank Cost Plan

## Cost breakdown by category

| Cost Code | Category | Cost Items | Budget | Status | Basis |
| --- | --- | --- | --- | --- | --- |
| 1 | Fees and charges | Architect-PM architect / PM fee | TBC | Approved | Engagement letter |
| 2 | Fees and charges | DA and CC authority fees | TBC | Assumption | Benchmark |
| 3 | Fees and charges | BASIX certificate fee | TBC | Assumption | Benchmark |
| 4 | Fees and charges | Sydney Water / infrastructure | TBC | Assumption | Benchmark |
| 5 | Fees and charges | Levies and statutory | TBC | Assumption | Benchmark |
| 6 | Consultants | Structural engineer | TBC | Assumption | Not yet appointed |
| 7 | Consultants | Geotechnical engineer | TBC | Assumption | Not yet appointed |
| 8 | Consultants | Surveyor | TBC | Assumption | Not yet appointed |
| 9 | Consultants | Hydraulic / wastewater | TBC | Assumption | Not yet appointed |
| 10 | Consultants | BASIX / energy assessor | TBC | Assumption | Not yet appointed |
| 11 | Consultants | Principal certifier | TBC | Assumption | Not yet appointed |
| 12 | Construction | Investigations, surveys and opening-up | TBC | Assumption | Pending pricing |
| 13 | Construction | Preliminaries, protection and temporary works | TBC | Assumption | Pending pricing |
| 14 | Construction | Hazardous-material controls and demolition | TBC | Assumption | Pending pricing |
| 15 | Construction | Existing-structure repair and new structural work | TBC | Assumption | Pending pricing |
| 16 | Construction | Envelope, roofing and old-to-new weatherproofing | TBC | Assumption | Pending pricing |
| 17 | Construction | Partitions, linings, doors and joinery | TBC | Assumption | Pending pricing |
| 18 | Construction | Kitchen, bathrooms and fittings | TBC | Assumption | Pending pricing |
| 19 | Construction | Building-services alterations and upgrades | TBC | Assumption | Pending pricing |
| 20 | Construction | Finishes, external works and making good | TBC | Assumption | Pending pricing |
| 21 | PC allowances | Kitchen joinery PC | TBC | Assumption | Selection pending |
| 22 | PC allowances | Wet area / sanitary PC | TBC | Assumption | Selection pending |
| 23 | PC allowances | Floor coverings PC | TBC | Assumption | Selection pending |
| 24 | PC allowances | Lighting fittings PC | TBC | Assumption | Selection pending |
| 25 | Contingency / allowances | Owner-held contingency | TBC | Assumption | 5-10% construction |
"""


def test_greenbank_adopted_budget_populates_all_25_rows_and_reconciles() -> None:
    forecast = build_adopted_budget_forecast(
        GREENBANK_COST_PLAN,
        construction_budget=Decimal("300000"),
        work_type="extend",
        source_ref="chat:user-instruction",
    )

    assert [item.cost_code for item in forecast.items] == [
        str(index) for index in range(1, 26)
    ]
    assert all(item.budget is not None and item.budget > 0 for item in forecast.items)
    assert forecast.construction_envelope_total == Decimal("300000.00")
    assert forecast.category_totals["Construction"] == Decimal("270000.00")
    assert forecast.category_totals["PC allowances"] == Decimal("30000.00")
    assert forecast.category_totals["Contingency / allowances"] == Decimal("30000.00")
    assert forecast.category_totals["Fees and charges"] == Decimal("36000.00")
    assert forecast.category_totals["Consultants"] == Decimal("33500.00")
    assert forecast.total_excluding_gst == Decimal("399500.00")
    assert forecast.contingency_percent == Decimal("10")
    assert all(item.forecast == item.budget for item in forecast.items)
    assert all(
        item.source_refs
        == [{"ref": "chat:user-instruction", "type": "user_provided_assumption"}]
        for item in forecast.items
    )


def test_adopted_budget_preserves_confirmed_prices_and_allocates_the_remainder() -> (
    None
):
    markdown = GREENBANK_COST_PLAN.replace(
        "| 13 | Construction | Preliminaries, protection and temporary works | TBC | Assumption | Pending pricing |",
        "| 13 | Construction | Preliminaries, protection and temporary works | $40,000 | Approved | Builder quote |",
    )

    forecast = build_adopted_budget_forecast(
        markdown,
        construction_budget=Decimal("300000"),
        work_type="extend",
    )

    preliminaries = next(item for item in forecast.items if item.cost_code == "13")
    assert preliminaries.budget == Decimal("40000.00")
    assert preliminaries.committed == Decimal("40000.00")
    assert preliminaries.status == "confirmed"
    assert preliminaries.locked is True
    assert forecast.construction_envelope_total == Decimal("300000.00")


def test_adopted_budget_preserves_manual_kitchen_pc_allowance() -> None:
    markdown = GREENBANK_COST_PLAN.replace(
        "| 25 | Contingency / allowances | Owner-held contingency | TBC | Assumption | 5-10% construction |",
        "\n".join(
            (
                "| 25 | Contingency / allowances | Owner-held contingency | TBC | Assumption | 5-10% construction |",
                "| 26 | PC allowances | Kitchen — including engineered stone benchtops | $33,000 | Manual | User-adopted planning allowance |",
            )
        ),
    )

    forecast = build_adopted_budget_forecast(
        markdown,
        construction_budget=Decimal("555555"),
        work_type="extend",
    )

    kitchen = next(
        item
        for item in forecast.items
        if item.item == "Kitchen — including engineered stone benchtops"
    )
    assert kitchen.budget == Decimal("33000.00")
    assert kitchen.status == "manual"
    assert kitchen.locked is True
    assert forecast.construction_envelope_total == Decimal("555555.00")


def test_adopted_budget_rejects_a_plan_without_cost_rows() -> None:
    with pytest.raises(AdoptedBudgetForecastError, match="cost item rows"):
        build_adopted_budget_forecast(
            "# Empty Cost Plan",
            construction_budget=Decimal("300000"),
            work_type="extend",
        )

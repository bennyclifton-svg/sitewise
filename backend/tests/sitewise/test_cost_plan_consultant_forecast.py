from app.sitewise.cost_plan_consultant_forecast import (
    forecast_consultant_fees_for_markdown,
)
from app.sitewise.cost_plan_workbook import parse_cost_breakdown


def _markdown(*, certifier_row: str | None = None, construction_rows: bool = True) -> str:
    construction = (
        "\n".join(
            [
                "| 12 | Construction | Preliminaries | $73,600 | Assumption | Benchmark % of ceiling |",
                "| 13 | Construction | Siteworks and demolition | $64,400 | Assumption | Benchmark % of ceiling |",
                "| 14 | Construction | Footings and slab | $110,400 | Assumption | Benchmark % of ceiling |",
                "| 15 | Construction | Framing and roof | $165,600 | Assumption | Benchmark % of ceiling |",
                "| 16 | Construction | External envelope and lockup | $138,000 | Assumption | Benchmark % of ceiling |",
                "| 17 | Construction | Internal linings and joinery | $128,800 | Assumption | Benchmark % of ceiling |",
                "| 18 | Construction | Kitchen and bathrooms | $82,800 | Assumption | Benchmark % of ceiling |",
                "| 19 | Construction | Building services | $92,000 | Assumption | Benchmark % of ceiling |",
                "| 20 | Construction | Finishes and external works | $64,400 | Assumption | Benchmark % of ceiling |",
            ]
        )
        if construction_rows
        else ""
    )
    certifier = (
        certifier_row
        or "| 11 | Consultants | Principal certifier | TBC | Assumption | Not yet appointed |"
    )
    construction_subtotal = "$920,000" if construction_rows else "TBC"
    grand_total = "$1,101,500" if construction_rows else "$181,500"
    return f"""# Cost plan

## Cost breakdown by category

| Cost Code | Category | Cost Items | Budget | Status | Basis |
| --- | --- | --- | --- | --- | --- |
| 1 | Fees and charges | Atelier North Pty Ltd architect / PM fee | $96,500 | Approved | Engagement letter |
| 2 | Fees and charges | DA and CC authority fees | TBC | Assumption | Benchmark |
| 6 | Consultants | Structural engineer | TBC | Assumption | Not yet appointed |
| 7 | Consultants | Geotechnical engineer | TBC | Assumption | Not yet appointed |
| 8 | Consultants | Surveyor | TBC | Assumption | Not yet appointed |
| 9 | Consultants | Hydraulic / wastewater | TBC | Assumption | Not yet appointed |
| 10 | Consultants | BASIX / energy assessor | TBC | Assumption | Not yet appointed |
{certifier}
{construction}
| 25 | Contingency / allowances | Owner-held contingency | $85,000 | Evidenced | 10% owner-held |
| | | **Subtotal - Fees and charges** | $96,500 | | |
| | | **Subtotal - Consultants** | TBC | | |
| | | **Subtotal - Construction** | {construction_subtotal} | | |
| | | **Subtotal - Contingency / allowances** | $85,000 | | |
| | | **Grand total (ex GST)** | {grand_total} | Assumption | Sum of itemised subtotals |

## Known locked contract and appointment values

| Supplier | Scope | Amount (ex GST) | Date | Evidence |
| --- | --- | --- | --- | --- |
| Atelier North Pty Ltd | Architect / PM | $96,500 | 2026-03-01 | Engagement letter |
"""


def _line(markdown: str, label: str):
    lines, warnings = parse_cost_breakdown(markdown)
    assert warnings == []
    return next(line for line in lines if line.cost_item == label)


def test_forecast_applies_missing_consultant_benchmarks_and_totals() -> None:
    result = forecast_consultant_fees_for_markdown(_markdown())

    assert result.construction_base == 920_000
    assert result.known_professional_fee_total == 96_500
    assert result.missing_consultant_forecast_total == 47_000
    assert result.consultant_subtotal == 47_000
    assert _line(result.updated_markdown, "Atelier North Pty Ltd architect / PM fee").budget == 96_500
    assert _line(result.updated_markdown, "Structural engineer").budget == 16_500
    assert _line(result.updated_markdown, "Geotechnical engineer").budget == 5_000
    assert _line(result.updated_markdown, "Surveyor").budget == 6_500
    assert _line(result.updated_markdown, "Hydraulic / wastewater").budget == 8_000
    assert _line(result.updated_markdown, "BASIX / energy assessor").budget == 3_000
    assert _line(result.updated_markdown, "Principal certifier").budget == 8_000
    assert "|  |  | **Subtotal - Consultants** | $47,000 |  |  |" in result.updated_markdown
    assert "|  |  | **Grand total (ex GST)** | $1,148,500 | Judgement |" in result.updated_markdown
    assert "## Consultant fee forecast basis" in result.updated_markdown


def test_forecast_keeps_known_certifier_fee() -> None:
    result = forecast_consultant_fees_for_markdown(
        _markdown(
            certifier_row=(
                "| 11 | Consultants | Principal certifier | $6,800 | Grounded | "
                "Appointed (Certify NSW); owner-direct fee |"
            )
        )
    )

    assert result.missing_consultant_forecast_total == 39_000
    assert result.consultant_subtotal == 45_800
    assert _line(result.updated_markdown, "Principal certifier").budget == 6_800
    assert "|  |  | **Subtotal - Consultants** | $45,800 |  |  |" in result.updated_markdown


def test_forecast_warns_on_stale_architect_pm_misallocation() -> None:
    markdown = _markdown().replace(
        "| 1 | Fees and charges | Atelier North Pty Ltd architect / PM fee | $96,500 |",
        "| 1 | Fees and charges | Atelier North Pty Ltd architect / PM fee | $980,000 |",
    )

    result = forecast_consultant_fees_for_markdown(markdown)

    assert any("Architect / PM fee row appears unusually high" in item for item in result.warnings)


def test_forecast_falls_back_when_construction_base_missing() -> None:
    result = forecast_consultant_fees_for_markdown(_markdown(construction_rows=False))

    assert result.construction_base is None
    assert result.missing_consultant_forecast_total == 51_000
    assert any("Construction base was not found" in item for item in result.warnings)

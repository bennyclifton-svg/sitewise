from __future__ import annotations

from decimal import Decimal

from app.cost_plan.calculations import calculate_totals, resolved_budget
from app.cost_plan.schemas import CostPlanState


def _currency(value: Decimal) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def render_cost_plan_markdown(state: CostPlanState) -> str:
    totals = calculate_totals(
        state.items,
        contingency_percent=state.contingency_percent,
        escalation_percent=state.escalation_percent,
        gst_treatment=state.gst_treatment,
    )
    rows = [
        "| Cost code | Category | Cost item | Budget | Committed | Forecast | Paid | Allowance | Status | Basis | Sources |",
        "|---|---|---|---:|---:|---:|---:|---|---|---|---|",
    ]
    for item in state.items:
        refs = ", ".join(
            str(ref.get("ref") or ref.get("id") or ref.get("path") or "source")
            for ref in item.source_refs
        )
        rows.append(
            "| "
            + " | ".join(
                (
                    item.cost_code,
                    item.category,
                    item.item,
                    _currency(resolved_budget(item)),
                    _currency(item.committed),
                    _currency(item.forecast),
                    _currency(item.paid),
                    item.allowance_type.upper(),
                    item.status,
                    item.basis.replace("|", "\\|"),
                    refs.replace("|", "\\|"),
                )
            )
            + " |"
        )

    assumptions = [
        f"- **{key}:** {value}" for key, value in sorted(state.assumptions.items())
    ]
    summary = [
        f"- Budget: **{_currency(totals.budget)}**",
        f"- Committed: **{_currency(totals.committed)}**",
        f"- Forecast: **{_currency(totals.forecast)}**",
        f"- Paid: **{_currency(totals.paid)}**",
        f"- Variance: **{_currency(totals.variance)}**",
        f"- Allowances: **{_currency(totals.allowances)}**",
        f"- Contingency ({state.contingency_percent}%): **{_currency(totals.contingency)}**",
        f"- Escalation ({state.escalation_percent}%): **{_currency(totals.escalation)}**",
        f"- GST ({state.gst_treatment}): **{_currency(totals.gst)}**",
        f"- Total excluding GST: **{_currency(totals.total_excluding_gst)}**",
        f"- Total including GST: **{_currency(totals.total_including_gst)}**",
    ]
    narrative = str(state.narrative.get("markdown", "")).strip()
    sections = [
        f"# Cost Plan v{state.version}",
        "## Cost breakdown by category",
        "\n".join(rows),
        "## Deterministic totals",
        "\n".join(summary),
        "## Assumptions",
        "\n".join(assumptions) if assumptions else "- None recorded.",
    ]
    if narrative:
        sections.extend(("## Narrative", narrative))
    return "\n\n".join(sections).rstrip() + "\n"

"""Canonical Procurement Strategy export content."""

from __future__ import annotations

import csv
from io import StringIO

from app.schemas.projects import ProcurementStrategyView


_STATUS_LABELS = {
    "not_started": "Not started",
    "researching": "Researching",
    "shortlisting": "Shortlisting",
    "request_drafted": "Request drafted",
    "issued": "Issued",
    "responses_received": "Submitted",
    "evaluating": "Recommendation",
    "awarded": "Contract",
    "cancelled": "Cancelled",
}


def procurement_strategy_export_rows(
    strategy: ProcurementStrategyView,
) -> list[list[str]]:
    headers = [
        "Discipline",
        *[f"Firm {slot}" for slot in range(1, strategy.tenderer_column_count + 1)],
        "Status",
    ]
    rows = [headers]
    for row in strategy.rows:
        candidates = {candidate.slot: candidate.company_name for candidate in row.candidates}
        rows.append(
            [
                row.discipline_label,
                *[candidates.get(slot, "") for slot in range(1, strategy.tenderer_column_count + 1)],
                _STATUS_LABELS[row.status],
            ]
        )
    return rows


def procurement_strategy_export_markdown(strategy: ProcurementStrategyView) -> str:
    rows = procurement_strategy_export_rows(strategy)
    header, *body = rows
    return "\n".join(
        [
            "# Procurement Strategy",
            "",
            _markdown_row(header),
            _markdown_row(["---"] * len(header)),
            *[_markdown_row(row) for row in body],
        ]
    )


def procurement_strategy_export_csv(strategy: ProcurementStrategyView) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(procurement_strategy_export_rows(strategy))
    return output.getvalue()


def _markdown_row(values: list[str]) -> str:
    return "| " + " | ".join(_markdown_cell(value) for value in values) + " |"


def _markdown_cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")

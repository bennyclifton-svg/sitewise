from __future__ import annotations

import re
from dataclasses import dataclass

from app.sitewise.cost_plan_workbook import CostPlanLine, parse_cost_breakdown

MONEY_ROUNDING = 500
FORECAST_BASIS = "Benchmark allowance - consultant fee forecast"
FORECAST_STATUS = "Judgement"
FORECAST_SECTION_HEADING = "Consultant fee forecast basis"


@dataclass(frozen=True, slots=True)
class ConsultantBenchmark:
    rate: float
    minimum: int
    maximum: int


@dataclass(frozen=True, slots=True)
class ConsultantForecastRow:
    cost_code: str
    cost_item: str
    current_budget: float | None
    forecast_budget: int | None
    status: str
    basis: str
    action: str

    def to_payload(self) -> dict:
        return {
            "cost_code": self.cost_code,
            "cost_item": self.cost_item,
            "current_budget": self.current_budget,
            "forecast_budget": self.forecast_budget,
            "status": self.status,
            "basis": self.basis,
            "action": self.action,
        }


@dataclass(frozen=True, slots=True)
class ConsultantForecastResult:
    source_path: str | None
    construction_base: int | None
    known_professional_fee_total: int
    missing_consultant_forecast_total: int
    consultant_subtotal: int
    rows: tuple[ConsultantForecastRow, ...]
    warnings: tuple[str, ...]
    updated_markdown: str

    def to_payload(self, *, include_markdown: bool = False) -> dict:
        payload = {
            "source_path": self.source_path,
            "construction_base": self.construction_base,
            "known_professional_fee_total": self.known_professional_fee_total,
            "missing_consultant_forecast_total": self.missing_consultant_forecast_total,
            "consultant_subtotal": self.consultant_subtotal,
            "rows": [row.to_payload() for row in self.rows],
            "warnings": list(self.warnings),
        }
        if include_markdown:
            payload["updated_markdown"] = self.updated_markdown
        return payload


BENCHMARKS: dict[str, ConsultantBenchmark] = {
    "structural engineer": ConsultantBenchmark(0.018, 12_000, 24_000),
    "geotechnical engineer": ConsultantBenchmark(0.0055, 4_000, 7_500),
    "surveyor": ConsultantBenchmark(0.007, 5_000, 9_000),
    "hydraulic / wastewater": ConsultantBenchmark(0.0085, 5_000, 12_000),
    "basix / energy assessor": ConsultantBenchmark(0.0035, 2_000, 5_000),
    "principal certifier": ConsultantBenchmark(0.0085, 5_500, 10_000),
}
PROTECTED_STATUSES = {
    "approved",
    "contracted",
    "evidenced",
    "fact",
    "grounded",
    "locked",
}
ARCHITECT_PM_WARNING_THRESHOLD = 250_000


def forecast_consultant_fees_for_markdown(
    markdown: str,
    *,
    source_path: str | None = None,
) -> ConsultantForecastResult:
    """Apply deterministic consultant fee benchmark rows to a cost-plan draft."""
    cost_lines, parse_warnings = parse_cost_breakdown(markdown)
    warnings = list(parse_warnings)
    construction_base = _construction_base(markdown, cost_lines)
    if construction_base is None:
        warnings.append(
            "Construction base was not found; consultant allowances use midpoint fallback values."
        )

    consultant_rows = [
        line for line in cost_lines if _normalise_category(line.category) == "consultants"
    ]
    known_professional_fee_total = sum(
        _money_to_int(line.budget)
        for line in cost_lines
        if _is_known_professional_fee(line)
    )

    forecast_by_code: dict[str, int] = {}
    result_rows: list[ConsultantForecastRow] = []
    known_consultant_total = 0
    missing_forecast_total = 0
    for line in consultant_rows:
        key = _benchmark_key(line.cost_item)
        is_protected = _is_protected_status(line.status)
        current_budget = _money_to_int(line.budget)
        if is_protected:
            if current_budget is not None:
                known_consultant_total += current_budget
            result_rows.append(
                ConsultantForecastRow(
                    cost_code=line.cost_code,
                    cost_item=line.cost_item,
                    current_budget=line.budget,
                    forecast_budget=current_budget,
                    status=line.status,
                    basis=line.basis,
                    action="kept_known",
                )
            )
            continue

        if key is None:
            result_rows.append(
                ConsultantForecastRow(
                    cost_code=line.cost_code,
                    cost_item=line.cost_item,
                    current_budget=line.budget,
                    forecast_budget=current_budget,
                    status=line.status,
                    basis=line.basis,
                    action="no_benchmark",
                )
            )
            if current_budget is None:
                warnings.append(f"No consultant benchmark rule matched '{line.cost_item}'.")
            else:
                known_consultant_total += current_budget
            continue

        forecast_budget = _benchmark_amount(BENCHMARKS[key], construction_base)
        forecast_by_code[line.cost_code] = forecast_budget
        missing_forecast_total += forecast_budget
        result_rows.append(
            ConsultantForecastRow(
                cost_code=line.cost_code,
                cost_item=line.cost_item,
                current_budget=line.budget,
                forecast_budget=forecast_budget,
                status=FORECAST_STATUS,
                basis=FORECAST_BASIS,
                action="forecasted",
            )
        )

    _append_stale_value_warnings(cost_lines, warnings)
    updated_markdown = _rewrite_cost_breakdown(markdown, forecast_by_code)
    updated_markdown = _upsert_forecast_basis_section(
        updated_markdown,
        construction_base=construction_base,
        missing_forecast_total=missing_forecast_total,
    )
    return ConsultantForecastResult(
        source_path=source_path,
        construction_base=construction_base,
        known_professional_fee_total=known_professional_fee_total,
        missing_consultant_forecast_total=missing_forecast_total,
        consultant_subtotal=known_consultant_total + missing_forecast_total,
        rows=tuple(result_rows),
        warnings=tuple(dict.fromkeys(warnings)),
        updated_markdown=updated_markdown,
    )


def _construction_base(markdown: str, lines: list[CostPlanLine]) -> int | None:
    construction_total = sum(
        _money_to_int(line.budget) or 0
        for line in lines
        if _normalise_category(line.category) == "construction"
    )
    if construction_total:
        return construction_total
    subtotal = _table_label_amount(markdown, "subtotal", "construction")
    if subtotal is not None:
        return subtotal

    patterns = (
        r"Construction cost-control reference:\*\*\s*\$([\d,]+)",
        r"Owner working construction ceiling\s*\|[^|\n]*\|\s*\$([\d,]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, markdown, flags=re.IGNORECASE)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def _rewrite_cost_breakdown(markdown: str, forecast_by_code: dict[str, int]) -> str:
    if not forecast_by_code:
        return markdown
    lines = markdown.splitlines()
    bounds = _section_bounds(lines, "Cost breakdown by category")
    if bounds is None:
        return markdown
    start, end = bounds
    table_indices = _table_indices(lines, start + 1, end)
    if not table_indices:
        return markdown

    header = _split_row(lines[table_indices[0]])
    indexes = _header_indexes(header)
    required = {"cost code", "category", "cost items", "budget", "status", "basis"}
    if not required.issubset(indexes):
        return markdown

    for index in table_indices[2:]:
        cells = _split_row(lines[index])
        _pad_cells(cells, len(header))
        label = _clean_cell(cells[indexes["cost items"]]).lower()
        code = _clean_cell(cells[indexes["cost code"]])
        category = _normalise_category(cells[indexes["category"]])
        if code in forecast_by_code and category == "consultants":
            cells[indexes["budget"]] = _format_money(forecast_by_code[code])
            cells[indexes["status"]] = FORECAST_STATUS
            cells[indexes["basis"]] = FORECAST_BASIS
            lines[index] = _join_row(cells)
        elif "subtotal" in label and "consultants" in label:
            cells[indexes["budget"]] = _format_money(_consultant_subtotal(lines, table_indices, indexes))
            lines[index] = _join_row(cells)

    grand_total = _subtotal_sum(lines, table_indices, indexes)
    if grand_total is not None:
        for index in table_indices[2:]:
            cells = _split_row(lines[index])
            _pad_cells(cells, len(header))
            label = _clean_cell(cells[indexes["cost items"]]).lower()
            if "grand total" in label:
                cells[indexes["budget"]] = _format_money(grand_total)
                cells[indexes["status"]] = "Judgement"
                cells[indexes["basis"]] = "Sum of itemised subtotals including consultant fee forecast"
                lines[index] = _join_row(cells)
                break
    return "\n".join(lines)


def _consultant_subtotal(
    lines: list[str],
    table_indices: list[int],
    indexes: dict[str, int],
) -> int:
    total = 0
    for index in table_indices[2:]:
        cells = _split_row(lines[index])
        if len(cells) <= max(indexes.values()):
            continue
        if _normalise_category(cells[indexes["category"]]) != "consultants":
            continue
        total += _parse_money(cells[indexes["budget"]]) or 0
    return total


def _subtotal_sum(
    lines: list[str],
    table_indices: list[int],
    indexes: dict[str, int],
) -> int | None:
    total = 0
    found = False
    for index in table_indices[2:]:
        cells = _split_row(lines[index])
        if len(cells) <= max(indexes.values()):
            continue
        label = _clean_cell(cells[indexes["cost items"]]).lower()
        if "subtotal" not in label:
            continue
        amount = _parse_money(cells[indexes["budget"]])
        if amount is not None:
            total += amount
            found = True
    return total if found else None


def _upsert_forecast_basis_section(
    markdown: str,
    *,
    construction_base: int | None,
    missing_forecast_total: int,
) -> str:
    base = _format_money(construction_base) if construction_base is not None else "fallback midpoints"
    section = "\n".join(
        [
            f"## {FORECAST_SECTION_HEADING}",
            "",
            (
                f"- Consultant rows marked **{FORECAST_STATUS}** are benchmark allowances, "
                "not received fee proposals or invoices."
            ),
            f"- Construction base used: {base}.",
            f"- Missing consultant fee forecast total: {_format_money(missing_forecast_total)} ex GST.",
        ]
    )
    lines = markdown.splitlines()
    bounds = _section_bounds(lines, FORECAST_SECTION_HEADING)
    if bounds is not None:
        start, end = bounds
        next_lines = lines[:start] + section.splitlines() + lines[end:]
        return "\n".join(next_lines)

    breakdown_bounds = _section_bounds(lines, "Cost breakdown by category")
    if breakdown_bounds is None:
        return markdown.rstrip() + "\n\n" + section
    _start, end = breakdown_bounds
    next_lines = lines[:end] + ["", *section.splitlines()] + lines[end:]
    return "\n".join(next_lines)


def _append_stale_value_warnings(lines: list[CostPlanLine], warnings: list[str]) -> None:
    for line in lines:
        label = line.cost_item.lower()
        amount = _money_to_int(line.budget)
        if amount is None:
            continue
        if "architect" in label and "pm fee" in label and amount >= ARCHITECT_PM_WARNING_THRESHOLD:
            warnings.append(
                "Architect / PM fee row appears unusually high; check whether the construction budget was misallocated."
            )


def _benchmark_key(label: str) -> str | None:
    normalised = _normalise_label(label)
    if "structural" in normalised:
        return "structural engineer"
    if "geotechnical" in normalised or "geotech" in normalised:
        return "geotechnical engineer"
    if "surveyor" in normalised or "survey" in normalised:
        return "surveyor"
    if "hydraulic" in normalised or "wastewater" in normalised:
        return "hydraulic / wastewater"
    if "basix" in normalised or "energy" in normalised or "nathers" in normalised:
        return "basix / energy assessor"
    if "certifier" in normalised or "pca" in normalised:
        return "principal certifier"
    return None


def _benchmark_amount(benchmark: ConsultantBenchmark, construction_base: int | None) -> int:
    if construction_base is None:
        raw = (benchmark.minimum + benchmark.maximum) / 2
    else:
        raw = construction_base * benchmark.rate
    clamped = min(max(raw, benchmark.minimum), benchmark.maximum)
    return _round_money(clamped)


def _is_known_professional_fee(line: CostPlanLine) -> bool:
    label = line.cost_item.lower()
    amount = _money_to_int(line.budget)
    return amount is not None and "architect" in label and ("pm" in label or "architect" in label)


def _is_protected_status(status: str) -> bool:
    lower = status.strip().lower()
    return any(token in lower for token in PROTECTED_STATUSES)


def _section_bounds(lines: list[str], heading: str) -> tuple[int, int] | None:
    target = heading.strip().lower()
    start = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("## "):
            continue
        current = stripped[3:].strip().lower()
        if current == target:
            start = index
            continue
        if start is not None:
            return start, index
    if start is None:
        return None
    return start, len(lines)


def _table_indices(lines: list[str], start: int, end: int) -> list[int]:
    table_start = None
    for index in range(start, end):
        if _is_table_line(lines[index]):
            cells = _split_row(lines[index])
            headers = set(_header_indexes(cells))
            if {"cost code", "category", "cost items", "budget"}.issubset(headers):
                table_start = index
                break
    if table_start is None:
        return []

    indices = []
    for index in range(table_start, end):
        if not _is_table_line(lines[index]):
            break
        indices.append(index)
    return indices


def _header_indexes(cells: list[str]) -> dict[str, int]:
    return {_normalise_header(cell): index for index, cell in enumerate(cells)}


def _table_label_amount(markdown: str, *label_parts: str) -> int | None:
    lower_parts = [part.lower() for part in label_parts]
    for line in markdown.splitlines():
        if not _is_table_line(line):
            continue
        cells = _split_row(line)
        label = " ".join(_clean_cell(cell).lower() for cell in cells[:3])
        if all(part in label for part in lower_parts):
            for cell in cells[3:]:
                amount = _parse_money(cell)
                if amount is not None:
                    return amount
    return None


def _split_row(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _join_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _pad_cells(cells: list[str], length: int) -> None:
    while len(cells) < length:
        cells.append("")


def _normalise_header(value: str) -> str:
    value = _clean_cell(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    aliases = {"cost item": "cost items", "item": "cost items", "amount": "budget"}
    return aliases.get(value, value)


def _normalise_category(value: str) -> str:
    cleaned = _clean_cell(value).lower()
    if "consult" in cleaned:
        return "consultants"
    if "construct" in cleaned:
        return "construction"
    if "fee" in cleaned or "charge" in cleaned:
        return "fees and charges"
    return cleaned


def _normalise_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean_cell(value).lower()).strip()


def _clean_cell(value: str) -> str:
    cleaned = re.sub(r"(\*\*|__|`)", "", value)
    cleaned = cleaned.replace("&amp;", "&")
    return " ".join(cleaned.split())


def _parse_money(value: str) -> int | None:
    cleaned = _clean_cell(value).lower()
    if not cleaned or "tbc" in cleaned or cleaned in {"-", "--", "n/a", "na"}:
        return None
    match = re.search(r"\$?\s*(\d[\d,]*(?:\.\d+)?)", cleaned)
    if not match:
        return None
    return round(float(match.group(1).replace(",", "")))


def _money_to_int(value: float | None) -> int | None:
    if value is None:
        return None
    return round(value)


def _round_money(value: float) -> int:
    return int(round(value / MONEY_ROUNDING) * MONEY_ROUNDING)


def _format_money(value: int | None) -> str:
    if value is None:
        return "TBC"
    return f"${value:,.0f}"

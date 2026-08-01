from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP

from app.cost_plan.calculations import money
from app.cost_plan.schemas import CostItemInput
from app.sitewise.cost_plan_consultant_forecast import consultant_fee_allowance
from app.sitewise.cost_plan_workbook import CostPlanLine, parse_cost_breakdown

ALLOCATION_QUANTUM = Decimal("500")
USER_ASSUMPTION_REF = "user_instruction"
PROTECTED_STATUS_TOKENS = frozenset(
    {"approved", "contracted", "evidenced", "fact", "grounded", "locked"}
)


class AdoptedBudgetForecastError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AdoptedBudgetForecast:
    construction_budget: Decimal
    construction_envelope_total: Decimal
    contingency_percent: Decimal
    category_totals: dict[str, Decimal]
    total_excluding_gst: Decimal
    items: tuple[CostItemInput, ...]
    assumptions: dict[str, str]
    warnings: tuple[str, ...]

    def to_payload(self) -> dict:
        return {
            "construction_budget_ex_gst": f"{self.construction_budget:.2f}",
            "construction_envelope_total": f"{self.construction_envelope_total:.2f}",
            "contingency_percent": f"{self.contingency_percent:g}",
            "category_totals": {
                key: f"{value:.2f}" for key, value in self.category_totals.items()
            },
            "total_excluding_gst": f"{self.total_excluding_gst:.2f}",
            "row_count": len(self.items),
            "assumptions": dict(self.assumptions),
            "warnings": list(self.warnings),
        }


def build_adopted_budget_forecast(
    markdown: str,
    *,
    construction_budget: Decimal,
    work_type: str | None,
    source_ref: str | None = None,
) -> AdoptedBudgetForecast:
    """Populate an existing cost-plan schedule from a user-adopted budget.

    Construction and PC rows reconcile exactly to ``construction_budget``.
    Owner-side fees, consultants, and contingency are calculated separately and
    remain clearly labelled planning allowances rather than project evidence.
    """
    adopted_budget = money(Decimal(construction_budget))
    if adopted_budget <= 0:
        raise AdoptedBudgetForecastError(
            "construction budget must be greater than zero"
        )

    lines, parse_warnings = parse_cost_breakdown(markdown)
    if not lines:
        raise AdoptedBudgetForecastError(
            "Cost Plan does not contain cost item rows to allocate."
        )

    envelope_indexes = [
        index for index, line in enumerate(lines) if _is_construction_envelope(line)
    ]
    if not envelope_indexes:
        raise AdoptedBudgetForecastError(
            "Cost Plan does not contain Construction or PC allowance rows."
        )

    allocated_envelope = _allocate_construction_envelope(
        lines,
        envelope_indexes=envelope_indexes,
        construction_budget=adopted_budget,
    )
    contingency_percent = _contingency_percent(work_type)
    reference = source_ref or USER_ASSUMPTION_REF
    items: list[CostItemInput] = []
    seen_keys: set[str] = set()
    for index, line in enumerate(lines):
        protected = _is_protected(line)
        if index in allocated_envelope:
            budget = allocated_envelope[index]
        elif protected:
            budget = money(Decimal(str(line.budget)))
        elif _category_key(line.category) == "fees and charges":
            budget = _fee_allowance(line.cost_item, adopted_budget)
        elif _category_key(line.category) == "consultants":
            allowance = consultant_fee_allowance(line.cost_item, adopted_budget)
            budget = money(
                Decimal(allowance or _generic_consultant_allowance(adopted_budget))
            )
        elif _is_contingency(line):
            budget = money(adopted_budget * contingency_percent / Decimal("100"))
        else:
            budget = _round_allowance(
                _clamp(
                    adopted_budget * Decimal("0.01"), Decimal("500"), Decimal("15000")
                )
            )

        item_key = _unique_item_key(line, index=index, seen=seen_keys)
        allowance_type = _allowance_type(line)
        source_refs = (
            [{"ref": reference, "type": "user_provided_assumption"}]
            if not protected
            else [{"ref": "current_cost_plan", "type": "confirmed_cost"}]
        )
        committed = (
            money(Decimal(str(line.approved_contract or line.budget)))
            if protected
            else Decimal("0")
        )
        items.append(
            CostItemInput(
                item_key=item_key,
                cost_code=line.cost_code,
                category=line.category,
                item=line.cost_item,
                budget=budget,
                committed=committed,
                forecast=budget,
                paid=Decimal("0"),
                allowance_type=allowance_type,
                basis=line.basis
                if protected
                else _planning_basis(
                    line,
                    construction_budget=adopted_budget,
                    contingency_percent=contingency_percent,
                ),
                source_refs=source_refs,
                confidence=Decimal("0.35") if not protected else None,
                status="confirmed" if protected else "proposed",
                locked=protected,
            )
        )

    category_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for item in items:
        category_totals[item.category] += item.budget or Decimal("0")
    category_totals = {key: money(value) for key, value in category_totals.items()}
    envelope_total = money(
        sum(
            (
                item.budget or Decimal("0")
                for item in items
                if _is_construction_envelope_item(item)
            ),
            Decimal("0"),
        )
    )
    if envelope_total != adopted_budget:
        raise AdoptedBudgetForecastError(
            "allocated Construction and PC allowances do not reconcile to the adopted budget"
        )
    total = money(sum((item.budget or Decimal("0") for item in items), Decimal("0")))
    assumptions = {
        "adopted_construction_budget_ex_gst": (
            f"${adopted_budget:,.2f} supplied by the user."
        ),
        "construction_envelope_basis": (
            "Construction and PC allowance rows together reconcile exactly to the "
            "user-adopted construction budget."
        ),
        "planning_allowance_status": (
            "Unconfirmed figures are early planning allowances, not quotations, "
            "contracts, invoices, or project evidence."
        ),
        "owner_contingency_basis": (
            f"{contingency_percent:g}% of construction, held outside the adopted "
            "construction envelope."
        ),
    }
    return AdoptedBudgetForecast(
        construction_budget=adopted_budget,
        construction_envelope_total=envelope_total,
        contingency_percent=contingency_percent,
        category_totals=category_totals,
        total_excluding_gst=total,
        items=tuple(items),
        assumptions=assumptions,
        warnings=tuple(parse_warnings),
    )


def _allocate_construction_envelope(
    lines: list[CostPlanLine],
    *,
    envelope_indexes: list[int],
    construction_budget: Decimal,
) -> dict[int, Decimal]:
    protected = {
        index: money(Decimal(str(lines[index].budget)))
        for index in envelope_indexes
        if _is_protected(lines[index])
    }
    protected_total = sum(protected.values(), Decimal("0"))
    if protected_total > construction_budget:
        raise AdoptedBudgetForecastError(
            "confirmed Construction and PC costs exceed the adopted construction budget"
        )
    forecast_indexes = [index for index in envelope_indexes if index not in protected]
    remaining = money(construction_budget - protected_total)
    if not forecast_indexes:
        if remaining != 0:
            raise AdoptedBudgetForecastError(
                "confirmed Construction and PC costs do not reconcile to the adopted budget"
            )
        return protected

    weights = {index: _construction_weight(lines[index]) for index in forecast_indexes}
    allocated = _allocate_weighted(remaining, weights)
    return {**protected, **allocated}


def _allocate_weighted(
    total: Decimal,
    weights: dict[int, Decimal],
) -> dict[int, Decimal]:
    weight_total = sum(weights.values(), Decimal("0"))
    if weight_total <= 0:
        raise AdoptedBudgetForecastError("construction allocation weights are invalid")
    raw = {index: total * weight / weight_total for index, weight in weights.items()}
    allocated = {
        index: (amount / ALLOCATION_QUANTUM).to_integral_value(rounding=ROUND_FLOOR)
        * ALLOCATION_QUANTUM
        for index, amount in raw.items()
    }
    residual = money(total - sum(allocated.values(), Decimal("0")))
    ranked = sorted(
        weights,
        key=lambda index: (raw[index] - allocated[index], weights[index], -index),
        reverse=True,
    )
    for index in ranked:
        if residual < ALLOCATION_QUANTUM:
            break
        allocated[index] += ALLOCATION_QUANTUM
        residual -= ALLOCATION_QUANTUM
    if residual:
        allocated[ranked[0]] += residual
    return {index: money(value) for index, value in allocated.items()}


def _construction_weight(line: CostPlanLine) -> Decimal:
    label = _label_key(line.cost_item)
    rules = (
        (("investigation", "opening up", "survey"), Decimal("3")),
        (("preliminar", "temporary work", "protection"), Decimal("10")),
        (("hazard", "demolition"), Decimal("8")),
        (("existing structure", "structural work", "foundation"), Decimal("18")),
        (("envelope", "roof", "weatherproof"), Decimal("17")),
        (("partition", "lining", "door", "joinery"), Decimal("11")),
        (("kitchen", "bathroom", "fitting"), Decimal("6")),
        (("service", "electrical", "hydraulic", "mechanical"), Decimal("10")),
        (("finish", "external work", "making good"), Decimal("7")),
    )
    if _category_key(line.category) == "pc allowances":
        if "kitchen" in label or "joinery" in label:
            return Decimal("4")
        if "wet" in label or "sanitary" in label:
            return Decimal("3")
        if "floor" in label or "lighting" in label:
            return Decimal("1.5")
        return Decimal("2")
    for tokens, weight in rules:
        if any(token in label for token in tokens):
            return weight
    return Decimal("5")


def _fee_allowance(label: str, construction_budget: Decimal) -> Decimal:
    normalised = _label_key(label)
    if (
        "architect" in normalised
        or "project management" in normalised
        or "pm fee" in normalised
    ):
        return _round_allowance(
            _clamp(
                construction_budget * Decimal("0.10"),
                Decimal("15000"),
                Decimal("60000"),
            )
        )
    if "da" in normalised or "cc" in normalised or "authority fee" in normalised:
        return _round_allowance(
            _clamp(
                construction_budget * Decimal("0.012"),
                Decimal("2000"),
                Decimal("15000"),
            )
        )
    if "basix" in normalised or "certificate" in normalised:
        return Decimal("500.00")
    if "water" in normalised or "infrastructure" in normalised:
        return Decimal("1000.00")
    if "levy" in normalised or "statutory" in normalised:
        return _round_allowance(
            _clamp(
                construction_budget * Decimal("0.003"),
                Decimal("1000"),
                Decimal("20000"),
            )
        )
    return _round_allowance(
        _clamp(construction_budget * Decimal("0.01"), Decimal("1000"), Decimal("15000"))
    )


def _generic_consultant_allowance(construction_budget: Decimal) -> int:
    return int(
        _round_allowance(
            _clamp(
                construction_budget * Decimal("0.01"), Decimal("2000"), Decimal("15000")
            )
        )
    )


def _round_allowance(value: Decimal) -> Decimal:
    rounded = (value / ALLOCATION_QUANTUM).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ) * ALLOCATION_QUANTUM
    return money(max(rounded, ALLOCATION_QUANTUM))


def _clamp(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    return min(max(value, minimum), maximum)


def _contingency_percent(work_type: str | None) -> Decimal:
    return (
        Decimal("10")
        if (work_type or "").lower()
        in {
            "refurb",
            "extend",
            "remediation",
        }
        else Decimal("7.5")
    )


def _planning_basis(
    line: CostPlanLine,
    *,
    construction_budget: Decimal,
    contingency_percent: Decimal,
) -> str:
    if _is_construction_envelope(line):
        return (
            "Planning allowance - allocated from the user-adopted "
            f"${construction_budget:,.2f} construction budget (ex GST)"
        )
    if _is_contingency(line):
        return (
            f"Planning allowance - {contingency_percent:g}% owner contingency "
            "held outside the construction envelope"
        )
    return (
        "Planning allowance - deterministic early-stage benchmark against the "
        "user-adopted construction budget; not a quotation"
    )


def _is_construction_envelope(line: CostPlanLine) -> bool:
    return _category_key(line.category) in {"construction", "pc allowances"}


def _is_construction_envelope_item(item: CostItemInput) -> bool:
    return _category_key(item.category) in {"construction", "pc allowances"}


def _is_contingency(line: CostPlanLine) -> bool:
    return "contingency" in _category_key(line.category) or "contingency" in _label_key(
        line.cost_item
    )


def _is_protected(line: CostPlanLine) -> bool:
    if line.budget is None:
        return False
    status = _label_key(line.status)
    return any(token in status for token in PROTECTED_STATUS_TOKENS)


def _allowance_type(line: CostPlanLine) -> str:
    category = _category_key(line.category)
    if category == "pc allowances":
        return "pc"
    if _is_contingency(line):
        return "contingency"
    return "none"


def _unique_item_key(line: CostPlanLine, *, index: int, seen: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", line.cost_code.lower()).strip("-")
    if not base:
        base = f"row-{index + 1}"
    candidate = base
    suffix = 2
    while candidate in seen:
        candidate = f"{base}-{suffix}"
        suffix += 1
    seen.add(candidate)
    return candidate


def _category_key(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _label_key(value: str) -> str:
    return _category_key(value)

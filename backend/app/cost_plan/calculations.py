from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.cost_plan.schemas import CostItemInput, CostPlanTotals, GstTreatment

MONEY_QUANTUM = Decimal("0.01")
RATE_QUANTUM = Decimal("0.0001")
GST_RATE = Decimal("0.10")


class CostPlanCalculationError(ValueError):
    pass


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def optional_budget(item: CostItemInput) -> Decimal | None:
    if item.quantity is not None:
        calculated = money(item.quantity * item.rate)  # type: ignore[operator]
        if item.budget is not None and money(item.budget) != calculated:
            raise CostPlanCalculationError(
                f"{item.item_key}: budget does not equal quantity multiplied by rate"
            )
        return calculated
    if item.budget is None:
        return None
    return money(item.budget)


def resolved_budget(item: CostItemInput) -> Decimal:
    """Sum known amounts internally; callers must preserve unpriced totals."""
    return optional_budget(item) or Decimal("0.00")


def calculate_totals(
    items: list[CostItemInput],
    *,
    contingency_percent: Decimal,
    escalation_percent: Decimal,
    gst_treatment: GstTreatment,
) -> CostPlanTotals:
    if contingency_percent < 0 or escalation_percent < 0:
        raise CostPlanCalculationError("percentages cannot be negative")

    has_unpriced_items = any(optional_budget(item) is None for item in items)
    has_unpriced_allowances = any(
        optional_budget(item) is None and item.allowance_type in {"pc", "ps", "contingency"}
        for item in items
    )
    budgets = [resolved_budget(item) for item in items]
    budget = money(sum(budgets, Decimal("0")))
    committed = money(sum((item.committed for item in items), Decimal("0")))
    forecast = money(sum((item.forecast for item in items), Decimal("0")))
    paid = money(sum((item.paid for item in items), Decimal("0")))
    allowances = money(
        sum(
            (
                resolved_budget(item)
                for item in items
                if item.allowance_type in {"pc", "ps", "contingency"}
            ),
            Decimal("0"),
        )
    )
    contingency = money(budget * contingency_percent / Decimal("100"))
    escalation = money((budget + contingency) * escalation_percent / Decimal("100"))
    subtotal = money(budget + contingency + escalation)
    if gst_treatment == "exclusive":
        excluding = subtotal
        gst = money(excluding * GST_RATE)
        including = money(excluding + gst)
    elif gst_treatment == "inclusive":
        including = subtotal
        excluding = money(including / (Decimal("1") + GST_RATE))
        gst = money(including - excluding)
    else:
        excluding = subtotal
        gst = Decimal("0.00")
        including = subtotal

    return CostPlanTotals(
        budget=None if has_unpriced_items else budget,
        committed=committed,
        forecast=forecast,
        paid=paid,
        variance=None if has_unpriced_items else money(budget - forecast),
        allowances=None if has_unpriced_allowances else allowances,
        contingency=None if has_unpriced_items else contingency,
        escalation=None if has_unpriced_items else escalation,
        gst=None if has_unpriced_items else gst,
        total_excluding_gst=None if has_unpriced_items else excluding,
        total_including_gst=None if has_unpriced_items else including,
    )

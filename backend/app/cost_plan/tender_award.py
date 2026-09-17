"""Reconcile extracted tender lines before writing an awarded contract."""
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.cost_plan.schemas import CostPlanOperation, CostPlanState


class AwardedTenderLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_key: str = Field(min_length=1)
    description: str = Field(min_length=1)
    amount_ex_gst: Decimal = Field(ge=0, max_digits=16, decimal_places=2)
    source_location: str = Field(min_length=1)

    @field_validator("amount_ex_gst", mode="before")
    @classmethod
    def decimal_string(cls, value: object) -> object:
        if not isinstance(value, str):
            raise ValueError("Tender amounts must be decimal strings")
        return value


def awarded_tender_operations(
    state: CostPlanState,
    *,
    lines: list[AwardedTenderLine],
    contract_total_ex_gst: str,
    contractor: str,
    source: dict,
) -> list[CostPlanOperation]:
    try:
        total = Decimal(contract_total_ex_gst)
        valid = total.is_finite() and 0 < total < Decimal("1e14") and total == total.quantize(Decimal("0.01"))
    except InvalidOperation:
        valid = False
    if not valid:
        raise ValueError("Contract total must be a positive ex-GST amount in cents")
    if not lines or len(lines) > 200:
        raise ValueError("Provide between 1 and 200 tender lines")
    actual = sum((line.amount_ex_gst for line in lines), Decimal("0"))
    if actual != total:
        raise ValueError(
            f"Mapped tender lines total {actual:.2f} ex GST; contract total is "
            f"{total:.2f}. Resolve missing items, margin or GST before saving."
        )
    items = {item.item_key: item for item in state.items}
    grouped: dict[str, list[AwardedTenderLine]] = {}
    seen: set[tuple[str, str]] = set()
    for line in lines:
        identity = (line.source_location.strip(), line.description.strip())
        if identity in seen:
            raise ValueError("A tender source line was mapped more than once")
        seen.add(identity)
        if line.item_key not in items:
            raise ValueError(f"Unknown Cost Plan item: {line.item_key}")
        grouped.setdefault(line.item_key, []).append(line)
    if len(grouped) > 50:
        raise ValueError("An award can update at most 50 Cost Plan rows")
    operations = []
    for key, mapped in grouped.items():
        item = items[key]
        amount = sum((line.amount_ex_gst for line in mapped), Decimal("0"))
        values = {
            "committed": str(amount),
            "forecast": str(max(amount, item.paid)),
            "basis": f"Awarded to {contractor}: " + "; ".join(line.description for line in mapped),
            "source_refs": [*(ref for ref in item.source_refs if not (
                ref.get("kind") == "awarded_tender"
                and ref.get("source_document_id") == source.get("source_document_id")
            )), {
                **source, "kind": "awarded_tender", "contractor": contractor,
                "contract_total_ex_gst": str(total),
                "lines": [line.model_dump(mode="json") for line in mapped],
            }],
        }
        operations.append(CostPlanOperation(
            operation="UPDATE", target_type="cost_item", target_id=key, values=values,
        ))
    return operations

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Money = Decimal
GstTreatment = Literal["exclusive", "inclusive", "not_applicable"]
AllowanceType = Literal["none", "pc", "ps", "contingency"]


def _decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, float):
        raise ValueError(f"{field} must not be supplied as float")
    try:
        return Decimal(value)  # type: ignore[arg-type]
    except Exception as exc:
        raise ValueError(f"{field} must be a decimal-compatible value") from exc


class CostItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_key: str = Field(min_length=1, max_length=255)
    cost_code: str = Field(min_length=1, max_length=128)
    category: str = Field(min_length=1, max_length=255)
    item: str = Field(min_length=1, max_length=512)
    budget: Money | None = None
    committed: Money = Decimal("0")
    forecast: Money = Decimal("0")
    paid: Money = Decimal("0")
    allowance_type: AllowanceType = "none"
    quantity: Decimal | None = None
    unit: str | None = None
    rate: Decimal | None = None
    basis: str = Field(min_length=1)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    status: Literal["proposed", "confirmed", "manual"] = "proposed"
    locked: bool = False

    @field_validator(
        "budget",
        "committed",
        "forecast",
        "paid",
        "quantity",
        "rate",
        "confidence",
        mode="before",
    )
    @classmethod
    def decimals_only(cls, value: object, info) -> object:
        if value is None:
            return None
        return _decimal(value, field=info.field_name)

    @model_validator(mode="after")
    def validate_unit_rate(self) -> "CostItemInput":
        unit_values = (self.quantity, self.unit, self.rate)
        if any(value is not None for value in unit_values) and not all(
            value is not None for value in unit_values
        ):
            raise ValueError("quantity, unit, and rate must be supplied together")
        if self.budget is None and self.quantity is None:
            raise ValueError("budget or complete quantity/unit/rate input is required")
        if self.paid > self.forecast and self.forecast != 0:
            raise ValueError("paid cannot exceed forecast")
        return self


class CostPlanTotals(BaseModel):
    budget: Money
    committed: Money
    forecast: Money
    paid: Money
    variance: Money
    allowances: Money
    contingency: Money
    escalation: Money
    gst: Money
    total_excluding_gst: Money
    total_including_gst: Money


class DependencySnapshot(BaseModel):
    profile_revision: int = Field(ge=1)
    evidence_fingerprint: str = Field(min_length=1)
    decision_set_revision: int = Field(ge=1)
    upstream_artefacts: list[dict[str, Any]] = Field(default_factory=list)
    model_version: str | None = None
    prompt_version: str | None = None
    runtime_version: str = Field(min_length=1)


class CostPlanState(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    project_id: uuid.UUID
    artefact_revision_id: uuid.UUID | None = None
    version: int = Field(ge=1)
    status: Literal["proposed", "accepted", "superseded"] = "proposed"
    contingency_percent: Decimal = Field(default=Decimal("0"), ge=0)
    escalation_percent: Decimal = Field(default=Decimal("0"), ge=0)
    gst_treatment: GstTreatment = "exclusive"
    assumptions: dict[str, str] = Field(default_factory=dict)
    narrative: dict[str, Any] = Field(default_factory=dict)
    dependency_snapshot: DependencySnapshot
    items: list[CostItemInput]
    totals: CostPlanTotals | None = None

    @field_validator("contingency_percent", "escalation_percent", mode="before")
    @classmethod
    def percentage_decimals_only(cls, value: object, info) -> Decimal:
        return _decimal(value, field=info.field_name)


class ExternalCostProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: uuid.UUID
    source_type: str = Field(min_length=1)
    source_id: uuid.UUID
    source_version: int = Field(ge=1)
    selected_option_id: uuid.UUID
    package_scope: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1, max_length=255)
    items: list[CostItemInput] = Field(min_length=1)
    financial_qualifiers: dict[str, Any]
    source_versions: dict[str, Any]


class CostPlanMutationResult(BaseModel):
    state: CostPlanState
    changed_item_keys: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)

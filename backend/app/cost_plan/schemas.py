from __future__ import annotations

import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Money = Decimal
GstTreatment = Literal["exclusive", "inclusive", "not_applicable"]
AllowanceType = Literal["none", "pc", "ps", "contingency"]
InvoiceGstTreatment = Literal["taxable", "gst_free", "derived"]
InvoiceMappingMethod = Literal[
    "exact",
    "related_reference",
    "keyword",
    "model",
    "manual",
    "remembered",
    "unidentified",
]


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
    display_order: int = Field(default=0, ge=0)
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


class CostPlanOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["ADD", "UPDATE", "DELETE", "MOVE", "DUPLICATE"]
    target_type: Literal["cost_item", "cost_category"]
    target_id: str | None = Field(default=None, max_length=255)
    values: dict[str, Any] = Field(default_factory=dict)
    reference_id: str | None = Field(default=None, max_length=255)
    placement: Literal["before", "after"] | None = None

    @model_validator(mode="after")
    def validate_operation(self) -> "CostPlanOperation":
        if self.operation != "ADD" and not self.target_id:
            raise ValueError(f"{self.operation} requires target_id")
        if self.operation == "MOVE" and (
            not self.reference_id or self.placement is None
        ):
            raise ValueError("MOVE requires reference_id and placement")
        if self.operation in {"ADD", "UPDATE"} and not self.values:
            raise ValueError(f"{self.operation} requires values")
        return self


class CostPlanDelta(BaseModel):
    version: int
    changed_items: list[CostItemInput] = Field(default_factory=list)
    deleted_item_keys: list[str] = Field(default_factory=list)
    totals: CostPlanTotals
    workbook_status: Literal["pending", "ready"] = "pending"


class CostPlanBatchMutationResult(BaseModel):
    state: CostPlanState
    delta: CostPlanDelta


class CostPlanDeletionBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "invoice",
        "commitment",
        "variation",
        "forecast",
        "procurement",
    ]
    id: str | None = None
    label: str = Field(min_length=1, max_length=512)
    reference_id: str | None = None


class InvoiceLineInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=2000)
    amount_ex_gst: Money
    gst_treatment: InvoiceGstTreatment = "taxable"
    source_locators: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("amount_ex_gst", mode="before")
    @classmethod
    def amount_decimal_only(cls, value: object) -> Decimal:
        return _decimal(value, field="amount_ex_gst")

    @model_validator(mode="after")
    def positive_amount(self) -> "InvoiceLineInput":
        if self.amount_ex_gst <= 0:
            raise ValueError("amount_ex_gst must be greater than zero")
        return self


class ExtractedInvoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_name: str = Field(min_length=1, max_length=512)
    supplier_abn: str | None = Field(default=None, max_length=32)
    invoice_number: str = Field(min_length=1, max_length=128)
    invoice_date: date
    due_date: date | None = None
    po_number: str | None = Field(default=None, max_length=128)
    related_reference: str | None = Field(default=None, max_length=255)
    subtotal_ex_gst: Money
    gst: Money
    total_including_gst: Money
    currency: Literal["AUD"] = "AUD"
    lines: list[InvoiceLineInput] = Field(min_length=1)
    provenance: dict[str, Any] = Field(default_factory=dict)

    @field_validator("subtotal_ex_gst", "gst", "total_including_gst", mode="before")
    @classmethod
    def invoice_decimal_only(cls, value: object, info) -> Decimal:
        return _decimal(value, field=info.field_name)

    @model_validator(mode="after")
    def reconcile_totals(self) -> "ExtractedInvoice":
        line_total = sum(
            (line.amount_ex_gst for line in self.lines), Decimal("0")
        ).quantize(Decimal("0.01"))
        subtotal = self.subtotal_ex_gst.quantize(Decimal("0.01"))
        gst = self.gst.quantize(Decimal("0.01"))
        inclusive = self.total_including_gst.quantize(Decimal("0.01"))
        if subtotal <= 0 or gst < 0 or inclusive <= 0:
            raise ValueError(
                "invoice totals must be positive and GST cannot be negative"
            )
        if line_total != subtotal:
            raise ValueError(
                f"invoice line total {line_total} does not equal subtotal {subtotal}"
            )
        if subtotal + gst != inclusive:
            raise ValueError(
                f"subtotal plus GST {subtotal + gst} does not equal total {inclusive}"
            )
        taxable_total = sum(
            (
                line.amount_ex_gst
                for line in self.lines
                if line.gst_treatment != "gst_free"
            ),
            Decimal("0"),
        )
        expected_gst = (taxable_total * Decimal("0.10")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        if gst != expected_gst:
            raise ValueError(
                f"GST {gst} does not equal 10% of taxable lines {expected_gst}"
            )
        if self.due_date is not None and self.due_date < self.invoice_date:
            raise ValueError("due_date cannot be before invoice_date")
        return self

    @property
    def billing_month(self) -> date:
        return self.invoice_date.replace(day=1)


class InvoiceAllocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_number: int = Field(ge=1)
    description: str = Field(min_length=1, max_length=2000)
    amount_ex_gst: Money
    gst_treatment: InvoiceGstTreatment
    cost_item_key: str | None = Field(default=None, max_length=255)
    cost_item_label: str = Field(default="Unidentified", min_length=1, max_length=512)
    mapping_method: InvoiceMappingMethod = "unidentified"
    mapping_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    review_status: Literal["mapped", "needs_review"] = "needs_review"
    source_locators: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("amount_ex_gst", "mapping_confidence", mode="before")
    @classmethod
    def allocation_decimal_only(cls, value: object, info) -> object:
        if value is None:
            return None
        return _decimal(value, field=info.field_name)

    @model_validator(mode="after")
    def validate_mapping_state(self) -> "InvoiceAllocationInput":
        if self.amount_ex_gst <= 0:
            raise ValueError("amount_ex_gst must be greater than zero")
        if self.review_status == "mapped" and not self.cost_item_key:
            raise ValueError("mapped allocations require cost_item_key")
        if self.review_status == "needs_review" and self.cost_item_key is not None:
            raise ValueError("review allocations must not select cost_item_key")
        return self


class InvoiceRegisterRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allocation_id: uuid.UUID
    invoice_date: date
    company: str
    po_number: str | None = None
    invoice_number: str
    description: str
    cost_item: str
    amount_ex_gst: Money
    billing_month: date
    paid: bool = False

    @field_validator("amount_ex_gst", mode="before")
    @classmethod
    def register_amount_decimal_only(cls, value: object) -> Decimal:
        return _decimal(value, field="amount_ex_gst")


class InvoiceCostItemOption(BaseModel):
    item_key: str
    cost_code: str
    category: str
    item: str
    budget: Money | None = None


class InvoiceLedgerRow(BaseModel):
    allocation_id: uuid.UUID
    invoice_id: uuid.UUID
    invoice_revision: int = Field(ge=1)
    invoice_date: date
    company: str
    po_number: str | None = None
    invoice_number: str
    description: str
    cost_item_key: str | None = None
    cost_item_label: str
    amount_ex_gst: Money
    billing_month: date
    paid: bool
    review_status: Literal["mapped", "needs_review"]
    mapping_method: InvoiceMappingMethod


class InvoiceLedgerResponse(BaseModel):
    cost_plan_version: int = Field(ge=1)
    workbook_path: str
    rows: list[InvoiceLedgerRow]
    cost_items: list[InvoiceCostItemOption]


class InvoiceFieldsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    expected_cost_plan_version: int = Field(ge=1)
    paid: bool | None = None
    billing_month: date | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> "InvoiceFieldsUpdate":
        if self.paid is None and self.billing_month is None:
            raise ValueError("paid or billing_month is required")
        if self.billing_month is not None and self.billing_month.day != 1:
            raise ValueError("billing_month must be the first day of a month")
        return self


class InvoiceAllocationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    expected_cost_plan_version: int = Field(ge=1)
    cost_item_key: str = Field(min_length=1, max_length=255)

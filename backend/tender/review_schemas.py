"""Source facts and a compact, source-referenced procurement review."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FactKind = Literal[
    "total",
    "subtotal",
    "component",
    "allowance",
    "rate",
    "option",
    "included",
    "excluded",
    "owner_supply",
    "qualification",
    "programme",
    "insurance",
    "validity",
    "pricing_basis",
]
IssueKind = Literal[
    "scope",
    "basis",
    "allowance",
    "exclusion",
    "programme",
    "insurance",
    "validity",
    "conflict",
]


class SourceFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_no: int = Field(ge=1)
    label: str = Field(min_length=1, max_length=100)
    excerpt: str = Field(min_length=1, max_length=450)
    kind: FactKind
    amount_printed: str | None = Field(default=None, max_length=80)
    currency: str = Field(default="AUD", pattern=r"^[A-Z]{3}$")
    tax_basis: Literal["inc", "ex", "unknown"] = "unknown"
    parent_label: str | None = Field(default=None, max_length=100)
    is_rollup: bool = False
    # Preserve a printed date; date arithmetic belongs to the review service.
    valid_until: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    issued_on: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    validity_days: int | None = Field(default=None, ge=1, le=3660)


class PageCoverage(BaseModel):
    page_no: int = Field(ge=1)
    readable: bool
    blank: bool


class ReviewExtraction(BaseModel):
    coverage: list[PageCoverage] = Field(min_length=1, max_length=4)
    facts: list[SourceFact] = Field(default_factory=list, max_length=600)


class ReviewFinding(BaseModel):
    issue: IssueKind
    fact_ids: list[str] = Field(min_length=1, max_length=4)


class ReviewMatrixCell(BaseModel):
    quote_id: str
    fact_ids: list[str] = Field(default_factory=list, max_length=12)


class ReviewMatrixRow(BaseModel):
    label: str = Field(min_length=1, max_length=70)
    cells: list[ReviewMatrixCell] = Field(min_length=1, max_length=4)


class ReviewSelection(BaseModel):
    conclusion: Literal[
        "preferred_for_clarification", "clarification_required", "single_quote"
    ]
    preferred_quote_id: str | None = None
    recommendation_fact_ids: list[str] = Field(default_factory=list, max_length=4)
    findings: list[ReviewFinding] = Field(min_length=1, max_length=4)
    matrix: list[ReviewMatrixRow] = Field(default_factory=list, max_length=24)

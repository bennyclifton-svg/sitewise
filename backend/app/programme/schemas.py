from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ActivityKind = Literal["stage", "activity", "milestone"]
ProgrammeScale = Literal["week", "month", "quarter"]
ProgrammeStatus = Literal["proposed", "accepted", "superseded"]
MAX_PROGRAMME_OPERATIONS = 80


class ProgrammeActivityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_key: str = Field(min_length=1, max_length=255)
    kind: ActivityKind
    parent_key: str | None = Field(default=None, max_length=255)
    name: str = Field(min_length=1, max_length=512)
    display_order: int = Field(default=0, ge=0)
    start_date: date
    duration_days: int = Field(ge=0)
    finish_date: date | None = None
    predecessor_key: str | None = Field(default=None, max_length=255)
    lag_days: int = 0
    assumption: bool = True
    notes: str = ""

    @model_validator(mode="after")
    def validate_kind_rules(self) -> "ProgrammeActivityInput":
        if self.kind == "milestone" and self.duration_days != 0:
            raise ValueError("milestone duration_days must be 0")
        if self.kind == "stage" and self.parent_key:
            raise ValueError("stage cannot have parent_key")
        if self.kind in {"activity", "milestone"} and not self.parent_key:
            raise ValueError(f"{self.kind} requires parent_key")
        return self


_ACTIVITY_VALUE_FIELDS = frozenset(ProgrammeActivityInput.model_fields)
_VALUE_ALIASES = {"description": "notes"}
_DROP_VALUE_KEYS = frozenset({"end_date", "phase", "status", "wbs", "percent_complete"})
_OPERATION_FIELDS = frozenset(
    {"operation", "target_type", "target_id", "values", "reference_id", "placement"}
)


def normalize_activity_values(raw: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, value in raw.items():
        if key in _DROP_VALUE_KEYS:
            continue
        mapped = _VALUE_ALIASES.get(key, key)
        if mapped in _ACTIVITY_VALUE_FIELDS and mapped not in values:
            values[mapped] = value
    return values


class ProgrammeOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["ADD", "UPDATE", "DELETE", "MOVE"]
    target_type: ActivityKind
    target_id: str | None = Field(default=None, max_length=255)
    values: dict[str, Any] = Field(default_factory=dict)
    reference_id: str | None = Field(default=None, max_length=255)
    placement: Literal["before", "after"] | None = None

    @model_validator(mode="before")
    @classmethod
    def coerce_llm_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        incoming = dict(data)
        target = incoming.pop("target", None)
        if isinstance(target, dict):
            incoming.setdefault(
                "target_type",
                target.get("type") or target.get("kind") or target.get("target_type"),
            )
            target_id = target.get("id") or target.get("target_id")
            if target_id:
                incoming.setdefault("target_id", target_id)
        values = dict(incoming.get("values") or {})
        for key in _ACTIVITY_VALUE_FIELDS | _VALUE_ALIASES.keys() | _DROP_VALUE_KEYS:
            if key in incoming:
                values.setdefault(key, incoming.pop(key))
        if "kind" in values and "target_type" not in incoming:
            incoming["target_type"] = values["kind"]
        if values:
            incoming["values"] = normalize_activity_values(values)
        return {key: value for key, value in incoming.items() if key in _OPERATION_FIELDS}

    @model_validator(mode="after")
    def validate_operation(self) -> "ProgrammeOperation":
        if self.operation != "ADD" and not self.target_id:
            raise ValueError(f"{self.operation} requires target_id")
        if self.operation == "MOVE" and (
            not self.reference_id or self.placement is None
        ):
            raise ValueError("MOVE requires reference_id and placement")
        if self.operation in {"ADD", "UPDATE"} and not self.values:
            raise ValueError(f"{self.operation} requires values")
        return self


class ProgrammeState(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    project_id: uuid.UUID
    version: int = Field(ge=1)
    status: ProgrammeStatus = "proposed"
    view_scale: ProgrammeScale = "month"
    pmp_embed_visible: bool = True
    activities: list[ProgrammeActivityInput] = Field(default_factory=list)


class ProgrammeViewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    view_scale: ProgrammeScale | None = None
    pmp_embed_visible: bool | None = None

    @model_validator(mode="after")
    def require_one_field(self) -> "ProgrammeViewUpdate":
        if self.view_scale is None and self.pmp_embed_visible is None:
            raise ValueError("view_scale or pmp_embed_visible is required")
        return self


class ProgrammeOperationsBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operations: list[ProgrammeOperation] = Field(min_length=1)

    @model_validator(mode="after")
    def limit_batch(self) -> "ProgrammeOperationsBatch":
        if len(self.operations) > MAX_PROGRAMME_OPERATIONS:
            raise ValueError(
                f"at most {MAX_PROGRAMME_OPERATIONS} operations can be applied"
            )
        return self

from __future__ import annotations

import uuid
from collections.abc import MutableMapping
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.database.project import Project
from app.schemas.project_snapshot import ProjectSnapshot, SnapshotValue
from app.schemas.projects import ProjectSubclassSelection
from app.sitewise.consultant_register import consultant_appointment_rows
from app.sitewise.taxonomy import (
    derive_risk_flags,
    complexity_dimensions_for,
    scale_fields_for,
    work_scope_items_for,
    work_scope_options_for,
)


class FieldState(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    EXPLICITLY_EXCLUDED = "explicitly_excluded"
    NOT_APPLICABLE = "not_applicable"


class ContextField(BaseModel):
    key: str
    label: str
    value: Any | None = None
    state: FieldState
    source: str | None = None


class GenerationContextRisk(BaseModel):
    key: str
    severity: str
    title: str
    description: str
    source: Literal["taxonomy"] = "taxonomy"


class ProjectGenerationContext(BaseModel):
    schema_version: Literal[1] = 1
    project_id: uuid.UUID
    context_version: int = Field(ge=1)
    identity: dict[str, ContextField]
    taxonomy: dict[str, ContextField]
    scale: dict[str, ContextField]
    complexity: dict[str, ContextField]
    scope: dict[str, ContextField]
    commercial: dict[str, ContextField]
    programme: dict[str, ContextField]
    approvals: dict[str, ContextField]
    stakeholders: dict[str, ContextField]
    derived_risks: list[GenerationContextRisk]

    def critical_unknowns(self) -> list[ContextField]:
        groups = (
            self.identity,
            self.taxonomy,
            self.commercial,
            self.programme,
            self.approvals,
        )
        return [
            field
            for group in groups
            for field in group.values()
            if field.state == FieldState.UNKNOWN
        ]


GenerationContextCache = MutableMapping[
    tuple[uuid.UUID, int], ProjectGenerationContext
]


def resolve_project_generation_context(
    snapshot: ProjectSnapshot,
    *,
    cache: GenerationContextCache | None = None,
    project: Project | None = None,
) -> ProjectGenerationContext:
    """Resolve the canonical, profiler-aware context for one project revision."""
    key = (snapshot.identity.project_id, snapshot.context_version)
    # Skip cache when project-backed consultant facts are requested — those can
    # change without a snapshot fingerprint bump in the same request.
    if cache is not None and project is None and key in cache:
        return cache[key]

    profile = snapshot.profile
    subclasses = _subclass_values(profile.subclasses)
    selected_scope = tuple(profile.work_scope)
    identity = {
        "title": _field(
            snapshot,
            path="identity.title",
            label="Project title",
            value=snapshot.identity.title,
            source="project",
        ),
        "site_address": _snapshot_field(
            snapshot,
            path="identity.site_address",
            key="site_address",
            label="Site address",
            value=snapshot.identity.site_address,
        ),
        "client": _snapshot_field(
            snapshot,
            path="identity.client",
            key="client",
            label="Client / owners",
            value=snapshot.identity.client,
        ),
    }
    taxonomy = {
        "building_class": _field(
            snapshot,
            path="taxonomy.building_class",
            label="Building class",
            value=profile.building_class,
            source="project_profile",
        ),
        "subclasses": _field(
            snapshot,
            path="taxonomy.subclasses",
            label="Building subclasses",
            value=list(subclasses),
            source="project_profile",
        ),
        "work_type": _field(
            snapshot,
            path="taxonomy.work_type",
            label="Work type",
            value=profile.work_type,
            source="project_profile",
        ),
        "state": _field(
            snapshot,
            path="taxonomy.state",
            label="State",
            value=profile.state,
            source="project_profile",
        ),
        "user_role": _field(
            snapshot,
            path="taxonomy.user_role",
            label="User role",
            value=profile.user_role,
            source="project_profile",
        ),
    }

    applicable_scale = {
        field.key: field
        for subclass in subclasses
        for field in scale_fields_for(profile.building_class or "", subclass)
    }
    scale = {
        key: _field(
            snapshot,
            path=f"scale.{key}",
            label=field.label,
            value=profile.scale.get(key),
            source="project_profile",
        )
        for key, field in applicable_scale.items()
    }
    dimensions = complexity_dimensions_for(
        profile.building_class or "", subclasses
    )
    complexity = {
        dimension.key: _field(
            snapshot,
            path=f"complexity.{dimension.key}",
            label=dimension.label,
            value=profile.complexity.get(dimension.key),
            source="project_profile",
        )
        for dimension in dimensions
    }
    scope = {
        item.value: _field(
            snapshot,
            path=f"scope.{item.value}",
            label=item.label,
            value=True if item.value in selected_scope else None,
            source="project_profile",
        )
        for item in work_scope_options_for(profile.work_type)
    }

    budget = snapshot.confirmed_inputs.get("budget")
    procurement = snapshot.confirmed_inputs.get("procurement_route")
    timeframe = snapshot.confirmed_inputs.get("timeframe")
    commercial = {
        "budget": _snapshot_field(
            snapshot,
            path="commercial.budget",
            key="budget",
            label="Project budget",
            value=budget,
        ),
        "procurement_route": _snapshot_field(
            snapshot,
            path="commercial.procurement_route",
            key="procurement_route",
            label="Procurement route",
            value=procurement,
        ),
    }
    programme = {
        "phase": _field(
            snapshot,
            path="programme.phase",
            label="Project phase",
            value=snapshot.identity.phase,
            source="project",
        ),
        "timeframe": _snapshot_field(
            snapshot,
            path="programme.timeframe",
            key="timeframe",
            label="Project timeframe",
            value=timeframe,
        ),
    }
    planning = complexity.get("planning")
    approvals = {
        "planning_pathway": planning.model_copy(
            update={"key": "planning_pathway", "label": "Planning pathway"}
        )
        if planning is not None
        else _field(
            snapshot,
            path="approvals.planning_pathway",
            label="Planning pathway",
            value=None,
            source=None,
        ),
    }

    selected_items = work_scope_items_for(profile.work_type, selected_scope)
    consultants = sorted(
        {
            consultant
            for item in selected_items
            for consultant in item.consultants
            if consultant
        },
        key=str.casefold,
    )
    appointments = consultant_appointment_rows(project) if project is not None else []
    stakeholders = {
        "client": identity["client"].model_copy(
            update={"key": "client", "label": "Client / owners"}
        ),
        "consultants": _field(
            snapshot,
            path="stakeholders.consultants",
            label="Required consultants",
            value=consultants,
            source="taxonomy" if consultants else None,
        ),
        "consultant_appointments": _field(
            snapshot,
            path="stakeholders.consultant_appointments",
            label="Evidence-derived consultant firms",
            value=appointments,
            source="evidence" if appointments else None,
        ),
    }
    known_complexity = {
        key: str(field.value)
        for key, field in complexity.items()
        if field.state == FieldState.KNOWN and field.value is not None
    }
    derived_risks = [
        GenerationContextRisk(
            key=risk.value,
            severity=risk.severity,
            title=risk.title,
            description=risk.description,
        )
        for risk in derive_risk_flags(known_complexity, list(selected_scope))
    ]
    context = ProjectGenerationContext(
        project_id=snapshot.identity.project_id,
        context_version=snapshot.context_version,
        identity=identity,
        taxonomy=taxonomy,
        scale=scale,
        complexity=complexity,
        scope=scope,
        commercial=commercial,
        programme=programme,
        approvals=approvals,
        stakeholders=stakeholders,
        derived_risks=derived_risks,
    )
    if cache is not None and project is None:
        cache[key] = context
    return context


def format_generation_context(context: ProjectGenerationContext) -> str:
    """Render a compact prompt block without discarding relevant unknowns."""
    lines = [
        "Canonical project generation context:",
        f"- context_version: {context.context_version}",
    ]
    for group_name in (
        "identity",
        "taxonomy",
        "scale",
        "complexity",
        "scope",
        "commercial",
        "programme",
        "approvals",
        "stakeholders",
    ):
        group = getattr(context, group_name)
        if not group:
            continue
        lines.append(f"- {group_name}:")
        for field in group.values():
            lines.append(
                f"  - {field.key}: {_display_value(field)} [{field.state.value}]"
            )
    if context.derived_risks:
        lines.append(
            "- derived_risks: "
            + ", ".join(risk.key for risk in context.derived_risks)
        )
    return "\n".join(lines)


def _snapshot_field(
    snapshot: ProjectSnapshot,
    *,
    path: str,
    key: str,
    label: str,
    value: SnapshotValue | None,
) -> ContextField:
    return _field(
        snapshot,
        path=path,
        key=key,
        label=label,
        value=value.value if value is not None else None,
        source=value.source if value is not None else None,
    )


def _field(
    snapshot: ProjectSnapshot,
    *,
    path: str,
    label: str,
    value: Any,
    source: str | None,
    key: str | None = None,
) -> ContextField:
    override = snapshot.field_states.get(path)
    state = (
        FieldState(override)
        if override is not None
        else FieldState.KNOWN
        if _has_value(value)
        else FieldState.UNKNOWN
    )
    return ContextField(
        key=key or path.rsplit(".", maxsplit=1)[-1],
        label=label,
        value=value if state == FieldState.KNOWN else None,
        state=state,
        source=source if state == FieldState.KNOWN else "project_profile_state"
        if override is not None
        else None,
    )


def _has_value(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _subclass_values(
    values: list[str | ProjectSubclassSelection],
) -> tuple[str, ...]:
    return tuple(
        item if isinstance(item, str) else item.value
        for item in values
        if (item if isinstance(item, str) else item.value)
    )


def _display_value(field: ContextField) -> str:
    if field.state == FieldState.UNKNOWN:
        return "UNKNOWN"
    if field.state == FieldState.EXPLICITLY_EXCLUDED:
        return "EXPLICITLY EXCLUDED"
    if field.state == FieldState.NOT_APPLICABLE:
        return "NOT APPLICABLE"
    if isinstance(field.value, list):
        return ", ".join(str(item) for item in field.value) or "none"
    return str(field.value)

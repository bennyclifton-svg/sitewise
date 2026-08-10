from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.projects.generation_context import (
    ContextField,
    FieldState,
    GenerationContextRisk,
    ProjectGenerationContext,
)
from app.sitewise.taxonomy import section_weights_for


class ArtefactContextBase(BaseModel):
    schema_version: Literal[1] = 1
    project_id: uuid.UUID
    context_version: int = Field(ge=1)
    critical_unknowns: list[ContextField]


class PmpContext(ArtefactContextBase):
    artefact_type: Literal["pmp"] = "pmp"
    identity: dict[str, ContextField]
    taxonomy: dict[str, ContextField]
    scope: dict[str, ContextField]
    scale: dict[str, ContextField]
    complexity: dict[str, ContextField]
    commercial: dict[str, ContextField]
    programme: dict[str, ContextField]
    approvals: dict[str, ContextField]
    stakeholders: dict[str, ContextField]
    derived_risks: list[GenerationContextRisk]
    section_weights: dict[str, float]
    user_provided_fields: dict[str, Any]

    @property
    def risk_flag_values(self) -> tuple[str, ...]:
        return tuple(risk.key for risk in self.derived_risks)


class CostPlanContext(ArtefactContextBase):
    artefact_type: Literal["cost_plan"] = "cost_plan"
    identity: dict[str, ContextField]
    taxonomy: dict[str, ContextField]
    scope: dict[str, ContextField]
    scale: dict[str, ContextField]
    complexity: dict[str, ContextField]
    commercial: dict[str, ContextField]
    programme: dict[str, ContextField]
    procurement: dict[str, ContextField]
    known_exclusions: dict[str, ContextField]


class RfpContext(ArtefactContextBase):
    artefact_type: Literal["rfp"] = "rfp"
    discipline: str = Field(min_length=1)
    identity: dict[str, ContextField]
    taxonomy: dict[str, ContextField]
    scope: dict[str, ContextField]
    scale: dict[str, ContextField]
    complexity: dict[str, ContextField]
    programme: dict[str, ContextField]
    procurement: dict[str, ContextField]
    approvals: dict[str, ContextField]
    stakeholders: dict[str, ContextField]
    derived_risks: list[GenerationContextRisk]
    section_weights: dict[str, float]


class RftContext(ArtefactContextBase):
    artefact_type: Literal["rft"] = "rft"
    package: str = Field(min_length=1)
    identity: dict[str, ContextField]
    taxonomy: dict[str, ContextField]
    scope: dict[str, ContextField]
    scale: dict[str, ContextField]
    complexity: dict[str, ContextField]
    programme: dict[str, ContextField]
    procurement: dict[str, ContextField]
    approvals: dict[str, ContextField]
    known_exclusions: dict[str, ContextField]


ProcurementArtefactContext = RfpContext | RftContext
ArtefactContext = PmpContext | CostPlanContext | ProcurementArtefactContext


def build_pmp_context(project_context: ProjectGenerationContext) -> PmpContext:
    selected_scope = selected_scope_values(project_context.scope)
    risk_flags = [risk.key for risk in project_context.derived_risks]
    complexity = _without(
        project_context.complexity,
        "planning",
        "procurement_route",
    )
    return PmpContext(
        project_id=project_context.project_id,
        context_version=project_context.context_version,
        identity=project_context.identity,
        taxonomy=project_context.taxonomy,
        scope=project_context.scope,
        scale=project_context.scale,
        complexity=complexity,
        commercial=project_context.commercial,
        programme=project_context.programme,
        approvals=project_context.approvals,
        stakeholders=project_context.stakeholders,
        derived_risks=project_context.derived_risks,
        section_weights=_section_weights(project_context, selected_scope, risk_flags),
        user_provided_fields=_pmp_user_fields(project_context),
        critical_unknowns=_critical_unknowns(
            project_context.identity,
            project_context.taxonomy,
            project_context.scale,
            complexity,
            project_context.commercial,
            project_context.programme,
            project_context.approvals,
            project_context.stakeholders,
        ),
    )


def build_cost_plan_context(
    project_context: ProjectGenerationContext,
) -> CostPlanContext:
    identity = _select(project_context.identity, "title", "site_address")
    taxonomy = _select(
        project_context.taxonomy,
        "building_class",
        "subclasses",
        "work_type",
        "state",
    )
    procurement = _procurement_fields(project_context)
    commercial = _select(project_context.commercial, "budget")
    complexity = _without(project_context.complexity, "procurement_route")
    return CostPlanContext(
        project_id=project_context.project_id,
        context_version=project_context.context_version,
        identity=identity,
        taxonomy=taxonomy,
        scope=project_context.scope,
        scale=project_context.scale,
        complexity=complexity,
        commercial=commercial,
        programme=project_context.programme,
        procurement=procurement,
        known_exclusions=_known_exclusions(project_context.scope),
        critical_unknowns=_critical_unknowns(
            identity,
            taxonomy,
            project_context.scale,
            complexity,
            commercial,
            project_context.programme,
            procurement,
        ),
    )


def build_rfp_context(
    project_context: ProjectGenerationContext,
    discipline: str,
) -> RfpContext:
    target = _required_target(discipline, label="discipline")
    identity = _select(project_context.identity, "title", "site_address", "client")
    taxonomy = _select(
        project_context.taxonomy,
        "building_class",
        "subclasses",
        "work_type",
        "state",
    )
    procurement = _procurement_fields(project_context)
    selected_scope = selected_scope_values(project_context.scope)
    risk_flags = [risk.key for risk in project_context.derived_risks]
    complexity = _without(
        project_context.complexity,
        "planning",
        "procurement_route",
    )
    return RfpContext(
        project_id=project_context.project_id,
        context_version=project_context.context_version,
        discipline=target,
        identity=identity,
        taxonomy=taxonomy,
        scope=project_context.scope,
        scale=project_context.scale,
        complexity=complexity,
        programme=project_context.programme,
        procurement=procurement,
        approvals=project_context.approvals,
        stakeholders=project_context.stakeholders,
        derived_risks=project_context.derived_risks,
        section_weights=_section_weights(project_context, selected_scope, risk_flags),
        critical_unknowns=_critical_unknowns(
            identity,
            taxonomy,
            project_context.scale,
            project_context.scope,
            complexity,
            project_context.programme,
            procurement,
            project_context.approvals,
            project_context.stakeholders,
        ),
    )


def build_rft_context(
    project_context: ProjectGenerationContext,
    package: str,
) -> RftContext:
    target = _required_target(package, label="package")
    identity = _select(project_context.identity, "title", "site_address")
    taxonomy = _select(
        project_context.taxonomy,
        "building_class",
        "subclasses",
        "work_type",
        "state",
    )
    procurement = _procurement_fields(project_context)
    complexity = _without(
        project_context.complexity,
        "planning",
        "procurement_route",
    )
    return RftContext(
        project_id=project_context.project_id,
        context_version=project_context.context_version,
        package=target,
        identity=identity,
        taxonomy=taxonomy,
        scope=project_context.scope,
        scale=project_context.scale,
        complexity=complexity,
        programme=project_context.programme,
        procurement=procurement,
        approvals=project_context.approvals,
        known_exclusions=_known_exclusions(project_context.scope),
        critical_unknowns=_critical_unknowns(
            identity,
            taxonomy,
            project_context.scale,
            project_context.scope,
            complexity,
            project_context.programme,
            procurement,
            project_context.approvals,
        ),
    )


def format_artefact_context(context: ArtefactContext) -> str:
    lines = [
        f"{_context_label(context)} project context lens:",
        f"- context_version: {context.context_version}",
    ]
    if isinstance(context, RfpContext):
        lines.append(f"- consultant_discipline: {context.discipline}")
    elif isinstance(context, RftContext):
        lines.append(f"- trade_package: {context.package}")

    for group_name in _prompt_groups(context):
        group = getattr(context, group_name)
        if not group:
            continue
        lines.append(f"- {group_name}:")
        for field in group.values():
            lines.append(
                f"  - {field.key}: {_display_value(field)} [{field.state.value}]"
            )
    if isinstance(context, (PmpContext, RfpContext)) and context.derived_risks:
        lines.append(
            "- derived_risks: "
            + ", ".join(risk.key for risk in context.derived_risks)
        )
    if context.critical_unknowns:
        lines.append(
            "- critical_unknown_information: "
            + ", ".join(field.key for field in context.critical_unknowns)
        )
    return "\n".join(lines)


def known_context_values(fields: dict[str, ContextField]) -> dict[str, Any]:
    return {
        key: field.value
        for key, field in fields.items()
        if field.state == FieldState.KNOWN and field.value is not None
    }


def selected_scope_values(fields: dict[str, ContextField]) -> tuple[str, ...]:
    return tuple(
        key
        for key, field in fields.items()
        if field.state == FieldState.KNOWN and field.value is True
    )


def _prompt_groups(context: ArtefactContext) -> tuple[str, ...]:
    if isinstance(context, PmpContext):
        return (
            "identity",
            "taxonomy",
            "scale",
            "complexity",
            "scope",
            "commercial",
            "programme",
            "approvals",
            "stakeholders",
        )
    if isinstance(context, CostPlanContext):
        return (
            "identity",
            "taxonomy",
            "scale",
            "complexity",
            "scope",
            "commercial",
            "programme",
            "procurement",
            "known_exclusions",
        )
    if isinstance(context, RfpContext):
        return (
            "identity",
            "taxonomy",
            "scale",
            "complexity",
            "scope",
            "programme",
            "procurement",
            "approvals",
            "stakeholders",
        )
    return (
        "identity",
        "taxonomy",
        "scale",
        "complexity",
        "scope",
        "programme",
        "procurement",
        "approvals",
        "known_exclusions",
    )


def _context_label(context: ArtefactContext) -> str:
    if isinstance(context, PmpContext):
        return "PMP"
    if isinstance(context, CostPlanContext):
        return "Cost Plan"
    if isinstance(context, RfpContext):
        return "RFP"
    return "RFT"


def _select(
    fields: dict[str, ContextField], *keys: str
) -> dict[str, ContextField]:
    return {key: fields[key] for key in keys if key in fields}


def _without(
    fields: dict[str, ContextField], *keys: str
) -> dict[str, ContextField]:
    excluded = set(keys)
    return {key: field for key, field in fields.items() if key not in excluded}


def _known_exclusions(
    fields: dict[str, ContextField],
) -> dict[str, ContextField]:
    return {
        key: field
        for key, field in fields.items()
        if field.state == FieldState.EXPLICITLY_EXCLUDED
    }


def _procurement_fields(
    context: ProjectGenerationContext,
) -> dict[str, ContextField]:
    confirmed = context.commercial.get("procurement_route")
    profile = context.complexity.get("procurement_route")
    if confirmed is not None and confirmed.state == FieldState.KNOWN:
        return {"procurement_route": confirmed}
    if profile is not None:
        return {"procurement_route": profile}
    return {"procurement_route": confirmed} if confirmed is not None else {}


def _critical_unknowns(
    *groups: dict[str, ContextField],
) -> list[ContextField]:
    unknowns: list[ContextField] = []
    seen: set[str] = set()
    for group in groups:
        for field in group.values():
            if field.state != FieldState.UNKNOWN or field.key in seen:
                continue
            seen.add(field.key)
            unknowns.append(field)
    return unknowns


def _section_weights(
    context: ProjectGenerationContext,
    selected_scope: tuple[str, ...],
    risk_flags: list[str],
) -> dict[str, float]:
    return section_weights_for(
        building_class=_known_string(context.taxonomy, "building_class"),
        work_type=_known_string(context.taxonomy, "work_type"),
        work_scope=list(selected_scope),
        risk_flags=risk_flags,
    )


def _pmp_user_fields(context: ProjectGenerationContext) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for group in (
        context.identity,
        context.commercial,
        context.programme,
        context.approvals,
    ):
        fields.update(known_context_values(group))
    state = context.taxonomy.get("state")
    if state is not None and state.state == FieldState.KNOWN:
        fields["state"] = state.value
    return fields


def _known_string(fields: dict[str, ContextField], key: str) -> str | None:
    field = fields.get(key)
    if field is None or field.state != FieldState.KNOWN or field.value is None:
        return None
    return str(field.value)


def _required_target(value: str, *, label: str) -> str:
    target = value.strip()
    if not target:
        raise ValueError(f"{label} is required")
    return target


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

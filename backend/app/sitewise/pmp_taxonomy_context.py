"""Helpers for turning project taxonomy metadata into PMP generation context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.sitewise.archetype_bridge import effective_taxonomy
from app.sitewise.taxonomy import (
    RiskFlag,
    derive_risk_flags,
    risk_flag_definitions,
    section_weights_for,
)


@dataclass(frozen=True, slots=True)
class PmpTaxonomyContext:
    building_class: str
    work_type: str | None
    subclasses: tuple[str, ...]
    scale: dict[str, Any]
    complexity: dict[str, str]
    work_scope: tuple[str, ...]
    risk_flags: tuple[RiskFlag, ...]
    section_weights: dict[str, float]
    user_provided_fields: dict[str, Any]

    @property
    def risk_flag_values(self) -> tuple[str, ...]:
        return tuple(flag.value for flag in self.risk_flags)


def project_has_taxonomy(project: object | None) -> bool:
    if project is None:
        return False
    return getattr(project, "building_class", None) is not None


def pmp_taxonomy_context(project: object) -> PmpTaxonomyContext | None:
    if getattr(project, "building_class", None) is None:
        return None
    taxonomy = effective_taxonomy(project)
    if taxonomy.building_class is None:
        return None

    metadata = getattr(project, "project_metadata", None)
    taxonomy_metadata = _taxonomy_metadata(metadata)
    scale = _clean_mapping(taxonomy_metadata.get("scale"))
    complexity = {
        key: str(value)
        for key, value in _clean_mapping(taxonomy_metadata.get("complexity")).items()
        if isinstance(value, str) and value.strip()
    }
    work_scope = _string_tuple(taxonomy_metadata.get("work_scope"))
    manual_risk_flags = _string_tuple(taxonomy_metadata.get("risk_flags"))
    derived_flags = derive_risk_flags(complexity, list(work_scope))
    risk_flags = _merge_risk_flags(derived_flags, manual_risk_flags)
    weights = section_weights_for(
        building_class=taxonomy.building_class,
        work_type=taxonomy.work_type,
        work_scope=list(work_scope),
        risk_flags=[flag.value for flag in risk_flags],
    )
    return PmpTaxonomyContext(
        building_class=taxonomy.building_class,
        work_type=taxonomy.work_type,
        subclasses=taxonomy.subclasses,
        scale=scale,
        complexity=complexity,
        work_scope=work_scope,
        risk_flags=tuple(risk_flags),
        section_weights=weights,
        user_provided_fields=_user_provided_fields(project, taxonomy_metadata),
    )


def _taxonomy_metadata(metadata: object) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return {}
    taxonomy = metadata.get("taxonomy")
    return taxonomy if isinstance(taxonomy, dict) else {}


def _clean_mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): item
        for key, item in value.items()
        if isinstance(key, str) and item not in (None, "", [], {})
    }


def _string_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        stripped = value.strip()
        return (stripped,) if stripped else ()
    if not isinstance(value, list):
        return ()
    values: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            values.append(item.strip())
        elif isinstance(item, dict):
            raw = item.get("value")
            if isinstance(raw, str) and raw.strip():
                values.append(raw.strip())
    return tuple(values)


def _merge_risk_flags(
    derived: list[RiskFlag],
    manual_values: tuple[str, ...],
) -> list[RiskFlag]:
    definitions = risk_flag_definitions()
    merged: list[RiskFlag] = []
    seen: set[str] = set()
    for flag in derived:
        if flag.value in seen:
            continue
        seen.add(flag.value)
        merged.append(flag)
    for value in manual_values:
        if value in seen or value not in definitions:
            continue
        seen.add(value)
        merged.append(definitions[value])
    return merged


def _user_provided_fields(project: object, taxonomy_metadata: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "title": getattr(project, "title", None),
        "workspace_path": getattr(project, "workspace_path", None),
        "state": getattr(project, "state", None),
        "phase": getattr(project, "phase", None),
    }
    for key in (
        "site_address",
        "client",
        "budget",
        "timeframe",
        "procurement_route",
        "brief",
        "notes",
    ):
        value = taxonomy_metadata.get(key)
        if value not in (None, "", [], {}):
            fields[key] = value
    return {key: value for key, value in fields.items() if value not in (None, "", [], {})}

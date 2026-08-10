"""Explicit project-change dependencies for targeted artefact refreshes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from app.database.project import Project


DirtyCategory = Literal[
    "scope_dirty",
    "programme_dirty",
    "cost_dirty",
    "consultants_dirty",
    "ffe_dirty",
    "approvals_dirty",
    "design_dirty",
    "procurement_dirty",
]


@dataclass(frozen=True, slots=True)
class AffectedArtefact:
    artefact_type: Literal["pmp", "rfp", "rft", "cost_plan", "consultant_register"]
    selector: str | None
    blocks: tuple[str, ...]


_PROFILE_DIRTY: dict[str, tuple[DirtyCategory, ...]] = {
    "building_class": ("scope_dirty", "design_dirty", "cost_dirty"),
    "work_type": ("scope_dirty", "design_dirty", "cost_dirty", "procurement_dirty"),
    "subclasses": ("scope_dirty", "design_dirty", "cost_dirty"),
    "scale": ("scope_dirty", "cost_dirty", "programme_dirty"),
    "complexity": ("design_dirty", "approvals_dirty", "programme_dirty"),
    "work_scope": ("scope_dirty", "design_dirty", "cost_dirty", "procurement_dirty"),
    "state": ("approvals_dirty",),
    "client": ("consultants_dirty",),
    "site_address": ("scope_dirty", "approvals_dirty"),
}

_DIRTY_DEPENDENCIES: dict[DirtyCategory, tuple[AffectedArtefact, ...]] = {
    "scope_dirty": (
        AffectedArtefact("pmp", None, ("project_summary", "scope")),
        AffectedArtefact("rfp", "*", ("background", "requested_services")),
        AffectedArtefact("rft", "*", ("background", "scope")),
    ),
    "programme_dirty": (
        AffectedArtefact("pmp", None, ("programme", "risks")),
        AffectedArtefact("rfp", "*", ("programme",)),
        AffectedArtefact("rft", "*", ("programme",)),
    ),
    "cost_dirty": (
        AffectedArtefact("cost_plan", None, ("items", "totals")),
        AffectedArtefact("pmp", None, ("cost_planning",)),
    ),
    "consultants_dirty": (
        AffectedArtefact("pmp", None, ("consultants",)),
        AffectedArtefact("rfp", "affected_discipline", ("requested_services",)),
        AffectedArtefact("consultant_register", None, ("consultants",)),
        AffectedArtefact("cost_plan", None, ("consultant_fees",)),
    ),
    "ffe_dirty": (
        AffectedArtefact("pmp", None, ("ffe",)),
        AffectedArtefact("rft", "affected_package", ("scope", "materials")),
        AffectedArtefact("cost_plan", None, ("finishes", "ffe")),
    ),
    "approvals_dirty": (
        AffectedArtefact("pmp", None, ("planning_and_compliance", "risks")),
        AffectedArtefact("rfp", "affected_discipline", ("requested_services",)),
    ),
    "design_dirty": (
        AffectedArtefact("pmp", None, ("design_management", "risks")),
        AffectedArtefact("rfp", "*", ("interfaces", "requested_services")),
        AffectedArtefact("rft", "*", ("interfaces", "design_responsibility")),
    ),
    "procurement_dirty": (
        AffectedArtefact("pmp", None, ("procurement_and_delivery",)),
        AffectedArtefact("rfp", "*", ("submission_requirements",)),
        AffectedArtefact("rft", "*", ("submission_requirements",)),
    ),
}


def dirty_categories_for_profile_fields(
    fields: Iterable[str],
) -> tuple[DirtyCategory, ...]:
    dirty: list[DirtyCategory] = []
    for field in fields:
        dirty.extend(_PROFILE_DIRTY.get(field, ()))
    return tuple(dict.fromkeys(dirty))


def affected_artefacts(
    dirty_categories: Iterable[DirtyCategory],
) -> tuple[AffectedArtefact, ...]:
    affected: list[AffectedArtefact] = []
    seen: set[tuple[str, str | None, tuple[str, ...]]] = set()
    for category in dirty_categories:
        for dependency in _DIRTY_DEPENDENCIES[category]:
            key = (
                dependency.artefact_type,
                dependency.selector,
                dependency.blocks,
            )
            if key not in seen:
                seen.add(key)
                affected.append(dependency)
    return tuple(affected)


def mark_project_dirty(project: Project, categories: Iterable[DirtyCategory]) -> None:
    additions = tuple(categories)
    if not additions:
        return
    metadata = dict(project.project_metadata or {})
    existing = metadata.get("dirty_categories")
    current = (
        [value for value in existing if isinstance(value, str)]
        if isinstance(existing, list)
        else []
    )
    metadata["dirty_categories"] = list(dict.fromkeys([*current, *additions]))
    metadata["affected_artefacts"] = [
        {
            "artefact_type": item.artefact_type,
            "selector": item.selector,
            "blocks": list(item.blocks),
        }
        for item in affected_artefacts(metadata["dirty_categories"])
    ]
    project.project_metadata = metadata


def clear_project_dirty(project: Project, categories: Iterable[DirtyCategory]) -> None:
    removing = set(categories)
    metadata = dict(project.project_metadata or {})
    current = metadata.get("dirty_categories")
    remaining = (
        [value for value in current if isinstance(value, str) and value not in removing]
        if isinstance(current, list)
        else []
    )
    if remaining:
        metadata["dirty_categories"] = remaining
        metadata["affected_artefacts"] = [
            {
                "artefact_type": item.artefact_type,
                "selector": item.selector,
                "blocks": list(item.blocks),
            }
            for item in affected_artefacts(remaining)
        ]
    else:
        metadata.pop("dirty_categories", None)
        metadata.pop("affected_artefacts", None)
    project.project_metadata = metadata

"""Compatibility bridge from legacy archetypes to PMP 2.0 taxonomy."""

from __future__ import annotations

from typing import NamedTuple


class EffectiveTaxonomy(NamedTuple):
    building_class: str | None
    work_type: str | None
    subclasses: tuple[str, ...]


_LEGACY_ARCHETYPES: dict[str, EffectiveTaxonomy] = {
    "new-dwelling": EffectiveTaxonomy("residential", "new", ("house",)),
    "renovation": EffectiveTaxonomy("residential", "refurb", ("house",)),
    "multi-dwelling": EffectiveTaxonomy("residential", "new", ("townhouses",)),
    "ancillary": EffectiveTaxonomy("residential", "extend", ("other",)),
    "small-commercial": EffectiveTaxonomy("commercial", None, ("other",)),
}


def effective_taxonomy(project) -> EffectiveTaxonomy:
    building_class = getattr(project, "building_class", None)
    work_type = getattr(project, "work_type", None)
    if building_class is not None or work_type is not None:
        subclasses = _metadata_subclasses(
            getattr(project, "project_metadata", None)
        )
        legacy = _LEGACY_ARCHETYPES.get(getattr(project, "archetype", None))
        if (
            not subclasses
            and legacy is not None
            and legacy.building_class == building_class
        ):
            subclasses = legacy.subclasses
        return EffectiveTaxonomy(
            building_class,
            work_type,
            subclasses,
        )

    archetype = getattr(project, "archetype", None)
    if archetype in _LEGACY_ARCHETYPES:
        return _LEGACY_ARCHETYPES[archetype]
    return EffectiveTaxonomy(None, None, ())


def effective_work_scopes(project) -> tuple[str, ...]:
    """Return confirmed work-scope values stored with the project taxonomy."""
    return _metadata_string_values(
        getattr(project, "project_metadata", None),
        "work_scope",
    )


def _metadata_subclasses(metadata: dict | None) -> tuple[str, ...]:
    return _metadata_string_values(metadata, "subclasses")


def _metadata_string_values(
    metadata: dict | None,
    key: str,
) -> tuple[str, ...]:
    if not isinstance(metadata, dict):
        return ()
    taxonomy = metadata.get("taxonomy")
    if not isinstance(taxonomy, dict):
        return ()
    raw_values = taxonomy.get(key)
    if not isinstance(raw_values, list):
        return ()
    values: list[str] = []
    for item in raw_values:
        if isinstance(item, str) and item.strip():
            values.append(item)
        elif isinstance(item, dict):
            value = item.get("value")
            if isinstance(value, str) and value.strip():
                values.append(value)
    return tuple(values)

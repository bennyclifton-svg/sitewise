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
    """Resolve PMP 2.0 taxonomy, with legacy archetypes as test-fixture fallback."""
    building_class = getattr(project, "building_class", None)
    work_type = getattr(project, "work_type", None)
    if building_class is not None or work_type is not None:
        return EffectiveTaxonomy(
            building_class,
            work_type,
            _metadata_subclasses(getattr(project, "project_metadata", None)),
        )

    archetype = getattr(project, "archetype", None)
    if archetype in _LEGACY_ARCHETYPES:
        return _LEGACY_ARCHETYPES[archetype]
    return EffectiveTaxonomy(None, None, ())


def _metadata_subclasses(metadata: dict | None) -> tuple[str, ...]:
    if not isinstance(metadata, dict):
        return ()
    taxonomy = metadata.get("taxonomy")
    if not isinstance(taxonomy, dict):
        return ()
    subclasses = taxonomy.get("subclasses")
    if not isinstance(subclasses, list):
        return ()
    return tuple(item for item in subclasses if isinstance(item, str) and item.strip())

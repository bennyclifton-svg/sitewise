"""Cached seed-knowledge routing shared by generated artefact workflows."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.generation_context import (
    FieldState,
    ProjectGenerationContext,
)
from app.retrieval.schemas import SourcePassage
from app.schemas.projects import WorkflowTraceEvent
from app.sitewise.archetype_bridge import effective_taxonomy, effective_work_scopes
from app.sitewise.knowledge_catalog import (
    DOCTRINE_PATH,
    CatalogEntry,
    applicable_platform_paths,
    file_catalog,
    load_sections,
    select_required_paths,
)

ArtefactType = Literal["pmp", "cost_plan", "rfp", "rft"]

REPO_ROOT = Path(__file__).resolve().parents[3]
_SECTION_ROUTE_MAP_PATHS: dict[ArtefactType, Path] = {
    "pmp": REPO_ROOT / "data" / "taxonomy" / "pmp-section-seed-map.json",
}
_DEFAULT_WORKFLOWS: dict[ArtefactType, str] = {
    "pmp": "create-pmp",
    "cost_plan": "create-cost-plan",
    "rfp": "consultant-procurement",
    "rft": "trade-procurement",
}


class SeedRoutingError(ValueError):
    """Raised when seed metadata or a section route is invalid."""


@dataclass(frozen=True, slots=True)
class SeedSectionRoute:
    artefact_section: str
    path: str
    section_id: str
    required: bool

    @property
    def ref(self) -> str:
        return f"{self.path}#{self.section_id}"


@dataclass(frozen=True, slots=True)
class SeedKnowledgeSelection:
    artefact_type: ArtefactType
    workflow: str
    seed_version: str
    required_paths: tuple[str, ...]
    workflow_paths: tuple[str, ...]
    target_paths: tuple[str, ...]
    applicable_paths: tuple[str, ...]
    section_routes: tuple[SeedSectionRoute, ...]

    @property
    def guidance_paths(self) -> tuple[str, ...]:
        """Return ordered workflow and target guidance, excluding base overlays."""
        return _dedupe((*self.target_paths, *self.workflow_paths))

    @property
    def section_refs(self) -> tuple[str, ...]:
        return tuple(route.ref for route in self.section_routes)


@dataclass(frozen=True, slots=True)
class LoadedSeedKnowledge:
    passages: list[SourcePassage]
    missing_required_refs: list[str]
    optional_warnings: list[str]
    trace_events: list[WorkflowTraceEvent]


@dataclass(frozen=True, slots=True)
class _RoutingContext:
    archetype: str | None
    building_class: str | None
    work_type: str | None
    subclasses: tuple[str, ...]
    work_scopes: tuple[str, ...]
    complexity: tuple[str, ...]
    risk_flags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _SeedRoutingIndex:
    version: str
    entries_by_path: dict[str, CatalogEntry]
    section_maps: dict[ArtefactType, dict[str, Any]]


def select_seed_knowledge(
    artefact_type: ArtefactType,
    project_context: ProjectGenerationContext,
    *,
    section: str | None = None,
    discipline: str | None = None,
    package: str | None = None,
    required_paths: Sequence[str] = (),
    workflow: str | None = None,
) -> SeedKnowledgeSelection:
    """Select cached seed routes from canonical project context."""
    return _select(
        artefact_type,
        _context_from_generation_context(project_context),
        section=section,
        discipline=discipline,
        package=package,
        required_paths=required_paths,
        workflow=workflow,
    )


def select_seed_knowledge_for_project(
    artefact_type: ArtefactType,
    project: object,
    *,
    section: str | None = None,
    discipline: str | None = None,
    package: str | None = None,
    required_paths: Sequence[str] = (),
    workflow: str | None = None,
) -> SeedKnowledgeSelection:
    """Route legacy project-shaped callers through the same cached selector."""
    taxonomy = effective_taxonomy(project)
    return _select(
        artefact_type,
        _RoutingContext(
            archetype=_optional_text(getattr(project, "archetype", None)),
            building_class=taxonomy.building_class,
            work_type=taxonomy.work_type,
            subclasses=taxonomy.subclasses,
            work_scopes=effective_work_scopes(project),
            complexity=_project_metadata_values(project, "complexity"),
            risk_flags=_project_metadata_values(project, "risk_flags"),
        ),
        section=section,
        discipline=discipline,
        package=package,
        required_paths=required_paths,
        workflow=workflow,
    )


def select_seed_knowledge_for_taxonomy(
    artefact_type: ArtefactType,
    *,
    archetype: str | None,
    building_class: str | None = None,
    work_type: str | None = None,
    subclasses: Sequence[str] | None = None,
    work_scopes: Sequence[str] | None = None,
    complexity: Sequence[str] | None = None,
    risk_flags: Sequence[str] | None = None,
    section: str | None = None,
    discipline: str | None = None,
    package: str | None = None,
    required_paths: Sequence[str] = (),
    workflow: str | None = None,
) -> SeedKnowledgeSelection:
    """Route explicit taxonomy inputs through the shared cached selector."""
    return _select(
        artefact_type,
        _RoutingContext(
            archetype=_optional_text(archetype),
            building_class=_optional_text(building_class),
            work_type=_optional_text(work_type),
            subclasses=_normalised_values(subclasses),
            work_scopes=_normalised_values(work_scopes),
            complexity=_normalised_values(complexity),
            risk_flags=_normalised_values(risk_flags),
        ),
        section=section,
        discipline=discipline,
        package=package,
        required_paths=required_paths,
        workflow=workflow,
    )


async def load_seed_knowledge(
    session: AsyncSession,
    selection: SeedKnowledgeSelection,
    *,
    max_chars: int,
) -> LoadedSeedKnowledge:
    """Load the section-level passages in a resolved seed route plan."""
    passages: list[SourcePassage] = []
    missing_required: list[str] = []
    optional_warnings: list[str] = []

    for route in selection.section_routes:
        loaded = await load_sections(
            session,
            route.path,
            [route.section_id],
            max_chars=max_chars,
        )
        if loaded is None or loaded.passage is None:
            if route.required:
                missing_required.append(route.ref)
            else:
                optional_warnings.append(route.ref)
            continue
        metadata = dict(loaded.passage.chunk_metadata or {})
        metadata["artefact_section"] = route.artefact_section
        if selection.artefact_type == "pmp":
            metadata["pmp_section"] = route.artefact_section
        metadata["seed_section_refs"] = [route.ref]
        metadata["required"] = route.required
        passages.append(loaded.passage.model_copy(update={"chunk_metadata": metadata}))

    trace_events: list[WorkflowTraceEvent] = []
    label = selection.artefact_type.upper().replace("_", " ")
    if passages:
        trace_events.append(
            WorkflowTraceEvent(
                step="seed_routing",
                status="complete",
                message=f"Loaded {label} seed sections.",
                metadata={
                    "seed_version": selection.seed_version,
                    "refs": [
                        ref
                        for passage in passages
                        for ref in (passage.chunk_metadata or {}).get(
                            "seed_section_refs", []
                        )
                    ],
                },
            )
        )
    if optional_warnings:
        trace_events.append(
            WorkflowTraceEvent(
                step="seed_routing",
                status="warning",
                message=f"Optional {label} seed sections were not available.",
                metadata={"missing_refs": optional_warnings},
            )
        )
    if missing_required:
        trace_events.append(
            WorkflowTraceEvent(
                step="seed_routing",
                status="blocked",
                message=f"Required {label} seed sections were not available.",
                metadata={"missing_refs": missing_required},
            )
        )
    return LoadedSeedKnowledge(
        passages=passages,
        missing_required_refs=missing_required,
        optional_warnings=optional_warnings,
        trace_events=trace_events,
    )


def seed_routing_cache_info() -> Any:
    """Expose cache statistics for diagnostics and regression tests."""
    return _select_cached.cache_info()


def clear_seed_routing_caches() -> None:
    """Clear metadata, index, and route caches after seed files change in-process."""
    _seed_routing_index.cache_clear()
    _select_cached.cache_clear()


def _select(
    artefact_type: ArtefactType,
    context: _RoutingContext,
    *,
    section: str | None,
    discipline: str | None,
    package: str | None,
    required_paths: Sequence[str],
    workflow: str | None,
) -> SeedKnowledgeSelection:
    index = _seed_routing_index()
    return _select_cached(
        artefact_type,
        workflow or _DEFAULT_WORKFLOWS[artefact_type],
        context,
        _optional_text(section),
        _optional_text(discipline),
        _optional_text(package),
        _normalised_values(required_paths),
        index.version,
    )


@lru_cache(maxsize=512)
def _select_cached(
    artefact_type: ArtefactType,
    workflow: str,
    context: _RoutingContext,
    section: str | None,
    discipline: str | None,
    package: str | None,
    extra_required_paths: tuple[str, ...],
    seed_version: str,
) -> SeedKnowledgeSelection:
    index = _seed_routing_index()
    if seed_version != index.version:
        raise SeedRoutingError("Seed routing index changed during selection")
    try:
        required = tuple(
            select_required_paths(
                workflow=workflow,
                archetype=context.archetype or "",
                building_class=context.building_class,
                work_type=context.work_type,
                subclasses=context.subclasses,
                work_scopes=context.work_scopes,
            )
        )
    except ValueError:
        if artefact_type in {"pmp", "cost_plan"}:
            raise
        required = ()
    workflow_paths = tuple(
        path
        for path in required
        if path != DOCTRINE_PATH
        and (entry := index.entries_by_path.get(path)) is not None
        and workflow in entry.required_by
    )
    target_paths = _dedupe(
        (
            *extra_required_paths,
            *_target_paths(
                index,
                discipline=discipline,
                package=package,
            ),
        )
    )
    guidance_paths = _dedupe((*target_paths, *workflow_paths))
    _validate_paths(guidance_paths, index=index)
    applicable = applicable_platform_paths(
        archetype=context.archetype,
        building_class=context.building_class,
        work_type=context.work_type,
        subclasses=context.subclasses,
        work_scopes=context.work_scopes,
        include_required=False,
    )
    applicable.update(guidance_paths)
    routes = _resolve_section_routes(
        artefact_type,
        context=context,
        selected_paths=set(required),
        requested_section=section,
        index=index,
    )
    return SeedKnowledgeSelection(
        artefact_type=artefact_type,
        workflow=workflow,
        seed_version=seed_version,
        required_paths=required,
        workflow_paths=workflow_paths,
        target_paths=target_paths,
        applicable_paths=tuple(sorted(applicable)),
        section_routes=routes,
    )


@lru_cache(maxsize=1)
def _seed_routing_index() -> _SeedRoutingIndex:
    entries = file_catalog()
    section_maps = {
        artefact_type: json.loads(path.read_text(encoding="utf-8"))
        for artefact_type, path in _SECTION_ROUTE_MAP_PATHS.items()
    }
    fingerprint = {
        "catalog": [asdict(entry) for entry in entries],
        "section_maps": section_maps,
    }
    version = hashlib.sha256(
        json.dumps(fingerprint, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    return _SeedRoutingIndex(
        version=version,
        entries_by_path={entry.path: entry for entry in entries},
        section_maps=section_maps,
    )


def _context_from_generation_context(
    context: ProjectGenerationContext,
) -> _RoutingContext:
    return _RoutingContext(
        archetype=None,
        building_class=_known_text(context, "taxonomy", "building_class"),
        work_type=_known_text(context, "taxonomy", "work_type"),
        subclasses=_known_values(context, "taxonomy", "subclasses"),
        work_scopes=tuple(
            key
            for key, field in context.scope.items()
            if field.state == FieldState.KNOWN and field.value is True
        ),
        complexity=tuple(
            sorted(
                f"{key}:{_route_value(field.value)}"
                for key, field in context.complexity.items()
                if field.state == FieldState.KNOWN and field.value is not None
            )
        ),
        risk_flags=tuple(sorted(risk.key for risk in context.derived_risks)),
    )


def _known_text(
    context: ProjectGenerationContext,
    group: str,
    key: str,
) -> str | None:
    field = getattr(context, group).get(key)
    if field is None or field.state != FieldState.KNOWN or field.value is None:
        return None
    return _optional_text(field.value)


def _known_values(
    context: ProjectGenerationContext,
    group: str,
    key: str,
) -> tuple[str, ...]:
    field = getattr(context, group).get(key)
    if field is None or field.state != FieldState.KNOWN:
        return ()
    value = field.value
    if not isinstance(value, (list, tuple, set)):
        value = (value,)
    return _normalised_values(value)


def _resolve_section_routes(
    artefact_type: ArtefactType,
    *,
    context: _RoutingContext,
    selected_paths: set[str],
    requested_section: str | None,
    index: _SeedRoutingIndex,
) -> tuple[SeedSectionRoute, ...]:
    route_map = index.section_maps.get(artefact_type)
    if route_map is None:
        return ()
    sections = route_map.get("sections", {})
    routes: list[SeedSectionRoute] = []
    for artefact_section, config in sections.items():
        if requested_section is not None and artefact_section != requested_section:
            continue
        if not isinstance(config, dict):
            continue
        routes.extend(
            _section_route_items(
                artefact_section=artefact_section,
                items=list(config.get("required", [])),
                required=True,
                context=context,
            )
        )
        routes.extend(
            _section_route_items(
                artefact_section=artefact_section,
                items=list(config.get("optional", [])),
                required=False,
                context=context,
            )
        )
    usable = _validate_section_routes(
        routes, selected_paths=selected_paths, index=index
    )
    return tuple(usable)


def _section_route_items(
    *,
    artefact_section: str,
    items: list[dict[str, object]],
    required: bool,
    context: _RoutingContext,
) -> list[SeedSectionRoute]:
    routes: list[SeedSectionRoute] = []
    for item in items:
        when = item.get("when", {})
        if isinstance(when, dict) and not _matches_when(when, context=context):
            continue
        path = str(item["path"])
        routes.extend(
            SeedSectionRoute(
                artefact_section=artefact_section,
                path=path,
                section_id=section_id,
                required=required,
            )
            for section_id in _as_tuple(item.get("section_ids"))
        )
    return routes


def _matches_when(when: dict[str, object], *, context: _RoutingContext) -> bool:
    axes: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "building_class",
            (context.building_class,) if context.building_class else (),
        ),
        ("work_type", (context.work_type,) if context.work_type else ()),
        ("subclasses", context.subclasses),
        ("work_scope", context.work_scopes),
        ("complexity", context.complexity),
        ("risk_flags", context.risk_flags),
    )
    return all(
        key not in when or _matches_list(values, when[key])
        for key, values in axes
    )


def _matches_list(values: tuple[str, ...], expected: object) -> bool:
    wanted = _as_tuple(expected)
    if not wanted or "any" in wanted or "all" in wanted:
        return True
    return any(value in wanted for value in values)


def _validate_section_routes(
    routes: list[SeedSectionRoute],
    *,
    selected_paths: set[str],
    index: _SeedRoutingIndex,
) -> list[SeedSectionRoute]:
    """Drop routes the catalog cannot supply; raise only on authoring errors.

    Unknown files and unknown section ids are authoring mistakes in the section
    map and stay fatal — tests catch them before deploy. A *required* route
    whose file the catalog did not select is different: the section map and the
    seed frontmatter are separate files that evolve independently, and their
    disagreement is evaluated at runtime against live project taxonomy. Raising
    there kills the workflow for a project whose only fault is an unusual
    class/work-type pairing, so the route is dropped instead and generation
    continues with the seeds that are genuinely available.
    """
    errors: list[str] = []
    usable: list[SeedSectionRoute] = []
    for route in routes:
        entry = index.entries_by_path.get(route.path)
        if entry is None:
            errors.append(f"unknown file {route.path}")
            continue
        if route.section_id not in entry.sections:
            errors.append(f"unknown section {route.ref}")
            continue
        if (
            route.required
            and route.path not in selected_paths
            and not _is_cross_cutting(entry)
        ):
            continue
        usable.append(route)
    if errors:
        raise SeedRoutingError("; ".join(errors))
    return usable


def _validate_paths(paths: Sequence[str], *, index: _SeedRoutingIndex) -> None:
    unknown = [path for path in paths if path not in index.entries_by_path]
    if unknown:
        raise SeedRoutingError(
            "Unknown seed guidance path(s): " + ", ".join(sorted(unknown))
        )


def _target_paths(
    index: _SeedRoutingIndex,
    *,
    discipline: str | None,
    package: str | None,
) -> tuple[str, ...]:
    targets = tuple(
        _route_value(target)
        for target in (discipline, package)
        if target is not None
    )
    if not targets:
        return ()
    paths: list[str] = []
    for entry in index.entries_by_path.values():
        terms = {
            _route_value(entry.loaded_by),
            _route_value(entry.path.rsplit("/", maxsplit=1)[-1].removesuffix(".md")),
            *(_route_value(topic) for topic in entry.topics),
        }
        if any(target in terms for target in targets):
            paths.append(entry.path)
    return tuple(paths)


def _is_cross_cutting(entry: CatalogEntry) -> bool:
    return entry.path == DOCTRINE_PATH or entry.tier == "topic"


def _as_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return (str(value),)


def _normalised_values(values: Sequence[object] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _route_value(value: object) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", str(value).casefold()))


def _dedupe(paths: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(paths))


def _project_metadata_values(project: object, key: str) -> tuple[str, ...]:
    metadata = getattr(project, "project_metadata", None)
    if not isinstance(metadata, dict):
        return ()
    taxonomy = metadata.get("taxonomy")
    raw = taxonomy.get(key) if isinstance(taxonomy, dict) else metadata.get(key)
    if isinstance(raw, dict):
        return tuple(
            sorted(f"{name}:{_route_value(value)}" for name, value in raw.items())
        )
    if isinstance(raw, str):
        return (raw,) if raw.strip() else ()
    if not isinstance(raw, list):
        return ()
    values: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            values.append(item)
        elif isinstance(item, dict):
            value = item.get("value")
            if isinstance(value, str) and value.strip():
                values.append(value)
    return tuple(values)

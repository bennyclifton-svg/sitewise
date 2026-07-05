"""Section-level seed routing for PMP generation.

Frontmatter selects the seed files that apply to a project. This module uses a
declarative map to choose the sections of those files that each PMP section may
draw from.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.retrieval.schemas import SourcePassage
from app.schemas.projects import WorkflowTraceEvent
from app.sitewise.knowledge_catalog import (
    DOCTRINE_PATH,
    CatalogEntry,
    file_catalog,
    load_sections,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTE_MAP_PATH = REPO_ROOT / "data" / "taxonomy" / "pmp-section-seed-map.json"


class PmpSeedRoutingError(ValueError):
    """Raised when the declarative route map references invalid knowledge."""


@dataclass(frozen=True)
class PmpSeedSectionRoute:
    pmp_section: str
    path: str
    section_id: str
    required: bool

    @property
    def ref(self) -> str:
        return f"{self.path}#{self.section_id}"


@dataclass(frozen=True)
class PmpSeedRoutePlan:
    required: tuple[PmpSeedSectionRoute, ...]
    optional: tuple[PmpSeedSectionRoute, ...]

    @property
    def all_routes(self) -> tuple[PmpSeedSectionRoute, ...]:
        return (*self.required, *self.optional)

    @property
    def refs(self) -> tuple[str, ...]:
        return tuple(route.ref for route in self.all_routes)


@dataclass(frozen=True)
class LoadedPmpSeedSections:
    passages: list[SourcePassage]
    missing_required_refs: list[str]
    optional_warnings: list[str]
    trace_events: list[WorkflowTraceEvent]


@lru_cache(maxsize=1)
def _route_map() -> dict[str, Any]:
    return json.loads(ROUTE_MAP_PATH.read_text(encoding="utf-8"))


def _entry_by_path() -> dict[str, CatalogEntry]:
    return {entry.path: entry for entry in file_catalog()}


def _is_cross_cutting(entry: CatalogEntry) -> bool:
    return entry.path == DOCTRINE_PATH or entry.tier == "topic"


def _as_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return (str(value),)


def _matches_list(values: tuple[str, ...], expected: object) -> bool:
    wanted = _as_tuple(expected)
    if not wanted:
        return True
    if "any" in wanted or "all" in wanted:
        return True
    return any(value in wanted for value in values)


def _matches_when(
    when: dict[str, object],
    *,
    building_class: str | None,
    work_type: str | None,
    subclasses: tuple[str, ...],
    work_scope: tuple[str, ...],
    risk_flags: tuple[str, ...],
) -> bool:
    if "building_class" in when and not _matches_list(
        (building_class,) if building_class else (), when["building_class"]
    ):
        return False
    if "work_type" in when and not _matches_list(
        (work_type,) if work_type else (), when["work_type"]
    ):
        return False
    if "subclasses" in when and not _matches_list(subclasses, when["subclasses"]):
        return False
    if "work_scope" in when and not _matches_list(work_scope, when["work_scope"]):
        return False
    if "risk_flags" in when and not _matches_list(risk_flags, when["risk_flags"]):
        return False
    return True


def _route_items(
    *,
    pmp_section: str,
    items: list[dict[str, object]],
    required: bool,
    building_class: str | None,
    work_type: str | None,
    subclasses: tuple[str, ...],
    work_scope: tuple[str, ...],
    risk_flags: tuple[str, ...],
) -> list[PmpSeedSectionRoute]:
    routes: list[PmpSeedSectionRoute] = []
    for item in items:
        when = item.get("when", {})
        if isinstance(when, dict) and not _matches_when(
            when,
            building_class=building_class,
            work_type=work_type,
            subclasses=subclasses,
            work_scope=work_scope,
            risk_flags=risk_flags,
        ):
            continue
        path = str(item["path"])
        for section_id in _as_tuple(item.get("section_ids")):
            routes.append(
                PmpSeedSectionRoute(
                    pmp_section=pmp_section,
                    path=path,
                    section_id=section_id,
                    required=required,
                )
            )
    return routes


def _validate_routes(
    routes: list[PmpSeedSectionRoute],
    *,
    selected_paths: set[str],
) -> None:
    entries = _entry_by_path()
    errors: list[str] = []
    for route in routes:
        entry = entries.get(route.path)
        if entry is None:
            errors.append(f"unknown file {route.path}")
            continue
        if route.section_id not in entry.sections:
            errors.append(f"unknown section {route.ref}")
        if route.required and route.path not in selected_paths and not _is_cross_cutting(entry):
            errors.append(f"required route file is not selected: {route.path}")
    if errors:
        raise PmpSeedRoutingError("; ".join(errors))


def resolve_seed_routes(
    *,
    selected_paths: list[str],
    building_class: str | None,
    work_type: str | None,
    subclasses: tuple[str, ...] = (),
    work_scope: tuple[str, ...] = (),
    risk_flags: tuple[str, ...] = (),
) -> PmpSeedRoutePlan:
    """Resolve and validate the seed sections for the project's PMP inputs."""
    sections = _route_map().get("sections", {})
    required: list[PmpSeedSectionRoute] = []
    optional: list[PmpSeedSectionRoute] = []
    for pmp_section, config in sections.items():
        if not isinstance(config, dict):
            continue
        required.extend(
            _route_items(
                pmp_section=pmp_section,
                items=list(config.get("required", [])),
                required=True,
                building_class=building_class,
                work_type=work_type,
                subclasses=subclasses,
                work_scope=work_scope,
                risk_flags=risk_flags,
            )
        )
        optional.extend(
            _route_items(
                pmp_section=pmp_section,
                items=list(config.get("optional", [])),
                required=False,
                building_class=building_class,
                work_type=work_type,
                subclasses=subclasses,
                work_scope=work_scope,
                risk_flags=risk_flags,
            )
        )
    _validate_routes([*required, *optional], selected_paths=set(selected_paths))
    return PmpSeedRoutePlan(required=tuple(required), optional=tuple(optional))


async def load_pmp_seed_sections(
    session: AsyncSession,
    *,
    selected_paths: list[str],
    building_class: str | None,
    work_type: str | None,
    subclasses: tuple[str, ...] = (),
    work_scope: tuple[str, ...] = (),
    risk_flags: tuple[str, ...] = (),
    max_chars: int,
) -> LoadedPmpSeedSections:
    plan = resolve_seed_routes(
        selected_paths=selected_paths,
        building_class=building_class,
        work_type=work_type,
        subclasses=subclasses,
        work_scope=work_scope,
        risk_flags=risk_flags,
    )
    passages: list[SourcePassage] = []
    missing_required: list[str] = []
    optional_warnings: list[str] = []

    for route in plan.all_routes:
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
        metadata["pmp_section"] = route.pmp_section
        metadata["seed_section_refs"] = [route.ref]
        metadata["required"] = route.required
        passages.append(loaded.passage.model_copy(update={"chunk_metadata": metadata}))

    trace_events: list[WorkflowTraceEvent] = []
    if passages:
        trace_events.append(
            WorkflowTraceEvent(
                step="seed_routing",
                status="complete",
                message="Loaded PMP seed sections.",
                metadata={
                    "refs": [
                        ref
                        for passage in passages
                        for ref in (passage.chunk_metadata or {}).get(
                            "seed_section_refs", []
                        )
                    ]
                },
            )
        )
    if optional_warnings:
        trace_events.append(
            WorkflowTraceEvent(
                step="seed_routing",
                status="warning",
                message="Optional PMP seed sections were not available.",
                metadata={"missing_refs": optional_warnings},
            )
        )
    if missing_required:
        trace_events.append(
            WorkflowTraceEvent(
                step="seed_routing",
                status="blocked",
                message="Required PMP seed sections were not available.",
                metadata={"missing_refs": missing_required},
            )
        )
    return LoadedPmpSeedSections(
        passages=passages,
        missing_required_refs=missing_required,
        optional_warnings=optional_warnings,
        trace_events=trace_events,
    )

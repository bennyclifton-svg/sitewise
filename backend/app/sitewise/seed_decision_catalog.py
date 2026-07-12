"""Parse structured ``decision-catalog`` fences from platform seed markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import yaml

_FENCE_RE = re.compile(r"^(```|~~~)([^\s]*)")


@dataclass(frozen=True, slots=True)
class SeedDecisionSpec:
    id: str
    section: str
    label: str
    options: tuple[dict[str, str], ...]
    default_hint: str | None = None
    archetypes: tuple[str, ...] = ()
    classes: tuple[str, ...] = ()
    work_types: tuple[str, ...] = ()
    shared: bool = True
    cost_only: bool = False


@dataclass(frozen=True, slots=True)
class _CatalogFence:
    body: str


def _iter_catalog_fences(markdown: str) -> Iterator[_CatalogFence]:
    lines = markdown.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        match = _FENCE_RE.match(lines[index])
        if match is None:
            index += 1
            continue
        fence = match.group(1)
        info = match.group(2)
        index += 1
        body_lines: list[str] = []
        while index < len(lines) and not lines[index].strip().startswith(fence):
            body_lines.append(lines[index])
            index += 1
        if index < len(lines):
            index += 1
        if info == "decision-catalog":
            yield _CatalogFence(body="".join(body_lines))


def _normalise_options(raw_options: object) -> tuple[dict[str, str], ...]:
    if not isinstance(raw_options, list):
        return ()
    options: list[dict[str, str]] = []
    for item in raw_options:
        if not isinstance(item, dict):
            continue
        value = item.get("value") or item.get("id")
        label = item.get("label") or item.get("title")
        if not isinstance(value, str) or not value.strip():
            continue
        options.append(
            {
                "value": value.strip(),
                "label": str(label).strip() if label else value.strip(),
            }
        )
    return tuple(options)


def _string_tuple(raw: object) -> tuple[str, ...]:
    if isinstance(raw, str) and raw.strip():
        return (raw.strip(),)
    if not isinstance(raw, list):
        return ()
    values: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            values.append(item.strip())
    return tuple(values)


def _spec_from_entry(entry: dict[str, Any]) -> SeedDecisionSpec | None:
    decision_id = entry.get("id")
    label = entry.get("label")
    section = entry.get("section")
    if not isinstance(decision_id, str) or not decision_id.strip():
        return None
    if not isinstance(label, str) or not label.strip():
        return None
    if not isinstance(section, str) or not section.strip():
        return None
    options = _normalise_options(entry.get("options"))
    if not options:
        return None
    applies_to = entry.get("applies_to")
    archetypes: tuple[str, ...] = ()
    classes: tuple[str, ...] = ()
    work_types: tuple[str, ...] = ()
    if isinstance(applies_to, dict):
        archetypes = _string_tuple(applies_to.get("archetypes"))
        classes = _string_tuple(applies_to.get("classes"))
        work_types = _string_tuple(applies_to.get("work_types"))
    default_hint = entry.get("default_hint")
    return SeedDecisionSpec(
        id=decision_id.strip(),
        section=section.strip(),
        label=label.strip(),
        options=options,
        default_hint=(
            default_hint.strip()
            if isinstance(default_hint, str) and default_hint.strip()
            else None
        ),
        archetypes=archetypes,
        classes=classes,
        work_types=work_types,
        shared=bool(entry.get("shared", True)),
        cost_only=bool(entry.get("cost_only", False)),
    )


def extract_decision_catalogs(markdown: str) -> list[SeedDecisionSpec]:
    specs: list[SeedDecisionSpec] = []
    seen: set[str] = set()
    for block in _iter_catalog_fences(markdown):
        try:
            payload = yaml.safe_load(block.body)
        except yaml.YAMLError:
            continue
        if not isinstance(payload, list):
            continue
        for item in payload:
            if not isinstance(item, dict):
                continue
            spec = _spec_from_entry(item)
            if spec is None or spec.id in seen:
                continue
            seen.add(spec.id)
            specs.append(spec)
    return specs


def load_decision_catalogs_from_seed_text(markdown: str) -> list[SeedDecisionSpec]:
    return extract_decision_catalogs(markdown)


def seed_directory() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "seed"


def load_all_seed_decision_catalogs(
    seed_dir: Path | None = None,
) -> list[SeedDecisionSpec]:
    directory = seed_dir or seed_directory()
    if not directory.is_dir():
        return []
    specs: list[SeedDecisionSpec] = []
    seen: set[str] = set()
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for spec in extract_decision_catalogs(text):
            if spec.id in seen:
                continue
            seen.add(spec.id)
            specs.append(spec)
    return specs


def filter_decisions_for_project(
    specs: list[SeedDecisionSpec] | tuple[SeedDecisionSpec, ...],
    *,
    archetype: str | None = None,
    building_class: str | None = None,
    work_type: str | None = None,
    include_cost_only: bool = False,
) -> list[SeedDecisionSpec]:
    filtered: list[SeedDecisionSpec] = []
    for spec in specs:
        if spec.cost_only and not include_cost_only:
            continue
        if spec.archetypes and archetype and archetype not in spec.archetypes:
            continue
        if spec.classes and building_class and building_class not in spec.classes:
            continue
        if spec.work_types and work_type and work_type not in spec.work_types:
            continue
        filtered.append(spec)
    return filtered

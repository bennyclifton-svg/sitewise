"""Frontmatter-driven platform knowledge catalog."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.source_document import SourceDocument
from app.retrieval.schemas import SourcePassage
from app.retrieval.whole_document import (
    _document_columns,
    _platform_scope_filter,
    _row_to_passage,
)
from app.sitewise.markdown_sections import (
    assemble_sections,
    list_section_ids,
    split_sections,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCTRINE_PATH = "docs/clerk-brief.md"

_KNOWLEDGE_SOURCES: tuple[tuple[str, Path], ...] = (
    ("seed", REPO_ROOT / "data" / "seed"),
    ("skills/reference", REPO_ROOT / "data" / "skills" / "reference"),
)
WORKFLOWS: tuple[str, ...] = ("create-pmp", "create-cost-plan", "consultant-procurement")


@dataclass(frozen=True)
class CatalogEntry:
    path: str
    title: str
    tier: str | None
    loaded_by: str | None
    topics: tuple[str, ...]
    summary: str
    applies_to_roles: tuple[str, ...] | None
    applies_to_archetypes: tuple[str, ...] | None
    applies_to_classes: tuple[str, ...] | None
    applies_to_work_types: tuple[str, ...] | None
    required_by: dict[str, int]
    doctrine_anchors: tuple[str, ...]
    sections: tuple[str, ...]


def _parse_list(value: str) -> list[str]:
    inner = value.strip()[1:-1].strip()
    if not inner:
        return []
    return [item.strip().strip("\"'") for item in inner.split(",")]


def _parse_dict(value: str) -> dict[str, int | str]:
    inner = value.strip()[1:-1].strip()
    if not inner:
        return {}
    parsed: dict[str, int | str] = {}
    for item in inner.split(","):
        if ":" not in item:
            continue
        key, raw = item.split(":", 1)
        text = raw.strip().strip("\"'")
        parsed[key.strip().strip("\"'")] = int(text) if text.isdigit() else text
    return parsed


def parse_frontmatter(content: str) -> dict[str, object]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return {}

    data: dict[str, object] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, raw = line.split(":", 1)
        value = raw.strip()
        if value.startswith("[") and value.endswith("]"):
            data[key.strip()] = _parse_list(value)
        elif value.startswith("{") and value.endswith("}"):
            data[key.strip()] = _parse_dict(value)
        else:
            data[key.strip()] = value.strip("\"'")
    return data


def _string_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return ()


def _optional_string_tuple(value: object) -> tuple[str, ...] | None:
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return None


def _required_by(value: object) -> dict[str, int]:
    if isinstance(value, dict):
        result: dict[str, int] = {}
        for key, rank in value.items():
            try:
                result[str(key)] = int(rank)
            except (TypeError, ValueError):
                continue
        return result
    if isinstance(value, list):
        return {str(item): index + 1 for index, item in enumerate(value)}
    return {}


def _entry_from_file(path: Path, corpus_path: str) -> CatalogEntry:
    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter = parse_frontmatter(text)
    sections = split_sections(text)
    first_h1 = next((section for section in sections if section.level == 1), None)
    return CatalogEntry(
        path=corpus_path,
        title=first_h1.heading if first_h1 else path.stem,
        tier=str(frontmatter["tier"]) if "tier" in frontmatter else None,
        loaded_by=str(frontmatter["loaded_by"]) if "loaded_by" in frontmatter else None,
        topics=_string_tuple(frontmatter.get("topics")),
        summary=str(frontmatter.get("summary", "")),
        applies_to_roles=_optional_string_tuple(frontmatter.get("applies_to_roles")),
        applies_to_archetypes=_optional_string_tuple(
            frontmatter.get("applies_to_archetypes")
        ),
        applies_to_classes=_optional_string_tuple(frontmatter.get("applies_to_classes")),
        applies_to_work_types=_optional_string_tuple(
            frontmatter.get("applies_to_work_types")
        ),
        required_by=_required_by(frontmatter.get("required_by")),
        doctrine_anchors=_string_tuple(frontmatter.get("doctrine_anchors")),
        sections=tuple(section.section_id for section in sections),
    )


@lru_cache(maxsize=1)
def file_catalog() -> tuple[CatalogEntry, ...]:
    entries: list[CatalogEntry] = []
    doctrine_file = REPO_ROOT / DOCTRINE_PATH
    if doctrine_file.exists():
        entries.append(_entry_from_file(doctrine_file, DOCTRINE_PATH))
    for prefix, directory in _KNOWLEDGE_SOURCES:
        if not directory.exists():
            continue
        for file in sorted(directory.glob("*.md")):
            if file.name != "README.md":
                entries.append(_entry_from_file(file, f"{prefix}/{file.name}"))
    return tuple(entries)


def _applies(
    entry: CatalogEntry,
    *,
    archetype: str | None,
    user_role: str,
) -> bool:
    if entry.applies_to_archetypes is None and entry.applies_to_classes is not None:
        return False
    if (
        entry.applies_to_archetypes is not None
        and archetype not in entry.applies_to_archetypes
    ):
        return False
    if entry.applies_to_roles is not None and user_role not in entry.applies_to_roles:
        return False
    return True


def _matches_axis(filters: tuple[str, ...] | None, value: str | None) -> bool:
    if filters is None or value is None:
        return True
    return value in filters or "any" in filters or "all" in filters


def _applies_to_taxonomy(
    entry: CatalogEntry,
    *,
    building_class: str | None,
    work_type: str | None,
    user_role: str,
) -> bool:
    if entry.applies_to_roles is not None and user_role not in entry.applies_to_roles:
        return False
    return _matches_axis(
        entry.applies_to_classes, building_class
    ) and _matches_axis(entry.applies_to_work_types, work_type)


def _role_entry(entries: tuple[CatalogEntry, ...], user_role: str) -> CatalogEntry | None:
    return next(
        (
            entry
            for entry in entries
            if entry.tier == "role-overlay"
            and entry.loaded_by == f"user_role: {user_role}"
        ),
        None,
    )


def _dedupe(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def catalog_entry_for_path(path: str) -> CatalogEntry | None:
    return next((entry for entry in file_catalog() if entry.path == path), None)


def _topic_match(entry: CatalogEntry, topics: list[str] | None) -> bool:
    wanted_topics = {topic.strip().lower() for topic in topics or [] if topic.strip()}
    if not wanted_topics:
        return True
    return bool(wanted_topics.intersection(topic.lower() for topic in entry.topics))


def applicable_entries(
    *,
    archetype: str | None = None,
    user_role: str | None = None,
    building_class: str | None = None,
    work_type: str | None = None,
    topics: list[str] | None = None,
) -> tuple[CatalogEntry, ...]:
    entries: list[CatalogEntry] = []
    for entry in file_catalog():
        if not _topic_match(entry, topics):
            continue
        if building_class is not None and user_role is not None:
            if entry.tier == "archetype":
                continue
            if (
                entry.tier == "role-overlay"
                and entry.loaded_by != f"user_role: {user_role}"
            ):
                continue
            if not _applies_to_taxonomy(
                entry,
                building_class=building_class,
                work_type=work_type,
                user_role=user_role,
            ):
                continue
        elif user_role is not None:
            if (
                entry.tier == "archetype"
                and entry.loaded_by != f"archetype: {archetype}"
            ):
                continue
            if (
                entry.tier == "role-overlay"
                and entry.loaded_by != f"user_role: {user_role}"
            ):
                continue
            if not _applies(entry, archetype=archetype, user_role=user_role):
                continue
        entries.append(entry)
    return tuple(entries)


def required_paths_by_workflow(
    *,
    archetype: str | None,
    user_role: str,
    building_class: str | None = None,
    work_type: str | None = None,
    workflows: tuple[str, ...] = WORKFLOWS,
) -> dict[str, list[str]]:
    return {
        workflow: select_required_paths(
            workflow=workflow,
            archetype=archetype,
            user_role=user_role,
            building_class=building_class,
            work_type=work_type,
        )
        for workflow in workflows
    }


def required_workflows_for_path(required: dict[str, list[str]], path: str) -> list[str]:
    return [workflow for workflow, paths in required.items() if path in paths]


def applicable_platform_paths(
    *,
    archetype: str | None,
    user_role: str,
    building_class: str | None = None,
    work_type: str | None = None,
    topics: list[str] | None = None,
    include_required: bool = True,
) -> set[str]:
    paths = {
        entry.path
        for entry in applicable_entries(
            archetype=archetype,
            user_role=user_role,
            building_class=building_class,
            work_type=work_type,
            topics=topics,
        )
    }
    if include_required:
        for required_paths in required_paths_by_workflow(
            archetype=archetype,
            user_role=user_role,
            building_class=building_class,
            work_type=work_type,
        ).values():
            paths.update(required_paths)
    return paths


def select_required_paths(
    *,
    workflow: str,
    archetype: str,
    user_role: str,
    building_class: str | None = None,
    work_type: str | None = None,
) -> list[str]:
    entries = file_catalog()
    if building_class is not None:
        role_entry = _role_entry(entries, user_role)
        if role_entry is None:
            msg = (
                "Unsupported taxonomy overlay combination: "
                f"building_class={building_class!r}, work_type={work_type!r}, "
                f"user_role={user_role!r}"
            )
            raise ValueError(msg)
        ranked_paths: list[tuple[int, str]] = [(0, DOCTRINE_PATH), (2, role_entry.path)]
        ranked_paths.extend(
            (entry.required_by[workflow], entry.path)
            for entry in entries
            if workflow in entry.required_by
            and _applies_to_taxonomy(
                entry,
                building_class=building_class,
                work_type=work_type,
                user_role=user_role,
            )
        )
        return _dedupe([path for _, path in sorted(ranked_paths)])

    archetype_entry = next(
        (
            entry
            for entry in entries
            if entry.tier == "archetype"
            and entry.loaded_by == f"archetype: {archetype}"
        ),
        None,
    )
    role_entry = _role_entry(entries, user_role)
    if archetype_entry is None or role_entry is None:
        msg = (
            f"Unsupported overlay combination: archetype={archetype!r}, "
            f"user_role={user_role!r}"
        )
        raise ValueError(msg)

    workflow_entries = sorted(
        (
            entry
            for entry in entries
            if workflow in entry.required_by
            and _applies(entry, archetype=archetype, user_role=user_role)
        ),
        key=lambda entry: entry.required_by[workflow],
    )
    return _dedupe(
        [
            DOCTRINE_PATH,
            archetype_entry.path,
            role_entry.path,
            *(entry.path for entry in workflow_entries),
        ]
    )


async def ingested_platform_paths(session: AsyncSession) -> set[str]:
    stmt = select(SourceDocument.relative_path).where(_platform_scope_filter())
    result = await session.execute(stmt)
    return {row[0] for row in result.all()}


async def list_platform_knowledge(
    session: AsyncSession,
    *,
    archetype: str | None = None,
    user_role: str | None = None,
    building_class: str | None = None,
    work_type: str | None = None,
    topics: list[str] | None = None,
) -> list[dict]:
    ingested = await ingested_platform_paths(session)
    listing: list[dict] = []
    for entry in applicable_entries(
        archetype=archetype,
        user_role=user_role,
        building_class=building_class,
        work_type=work_type,
        topics=topics,
    ):
        listing.append(
            {
                "path": entry.path,
                "title": entry.title,
                "tier": entry.tier,
                "topics": list(entry.topics),
                "summary": entry.summary,
                "applies_to_classes": list(entry.applies_to_classes or []),
                "applies_to_work_types": list(entry.applies_to_work_types or []),
                "sections": list(entry.sections),
                "related_doctrine_sections": list(entry.doctrine_anchors),
                "ingested": entry.path in ingested,
            }
        )
    return listing


@dataclass(frozen=True)
class LoadedKnowledge:
    passage: SourcePassage | None
    missing_sections: list[str]
    available_sections: list[str]


async def load_sections(
    session: AsyncSession,
    path: str,
    section_ids: list[str] | None,
    *,
    max_chars: int,
) -> LoadedKnowledge | None:
    stmt = (
        select(*_document_columns(content_chars=None))
        .where(_platform_scope_filter(), SourceDocument.relative_path == path)
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return None

    full_text = row.normalized_content or ""
    available = list_section_ids(full_text)
    requested = [section.strip() for section in section_ids or [] if section.strip()]
    passage = _row_to_passage(row, max_chars=max_chars, terms=[])
    if not requested:
        return LoadedKnowledge(
            passage=passage.model_copy(update={"content": full_text[:max_chars]}),
            missing_sections=[],
            available_sections=available,
        )

    assembled = assemble_sections(full_text, requested, max_chars=max_chars)
    if assembled is None:
        return LoadedKnowledge(
            passage=None,
            missing_sections=[section for section in requested if section not in available],
            available_sections=available,
        )
    return LoadedKnowledge(
        passage=passage.model_copy(
            update={
                "content": assembled,
                "chunk_metadata": {
                    "whole_document": True,
                    "section_ids": requested,
                },
            }
        ),
        missing_sections=[],
        available_sections=available,
    )

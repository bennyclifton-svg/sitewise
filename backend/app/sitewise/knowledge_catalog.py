"""Platform knowledge catalog: metadata-driven seed selection and section loading.

One disclosure model for both runtimes. Selection metadata is the YAML
frontmatter on the checked-in knowledge files (data/seed/*.md,
data/skills/reference/*, docs/clerk-brief.md) — the same files the ingest
pipeline persists to the corpus, read from the repo checkout the way
tender.seeds.load reads data/tender/. Deterministic Python over declarative
metadata; no LLM in seed selection.

The file catalog answers "what exists and when does it apply"; the database
answers "what is actually ingested and servable". select_required_paths must
stay output-identical to pmp_sources/cost_plan_sources.required_platform_paths
— guarded by tests/sitewise/test_catalog_parity.py.
"""

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
from ingest.frontmatter import parse_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[3]

DOCTRINE_PATH = "docs/clerk-brief.md"

# Corpus relative_path prefix -> repo directory, matching ingest corpus roots.
_KNOWLEDGE_SOURCES: tuple[tuple[str, Path], ...] = (
    ("seed", REPO_ROOT / "data" / "seed"),
    ("skills/reference", REPO_ROOT / "data" / "skills" / "reference"),
)


@dataclass(frozen=True)
class CatalogEntry:
    path: str  # corpus relative_path, e.g. "seed/new-dwelling-guide.md"
    title: str
    tier: str | None
    loaded_by: str | None
    topics: tuple[str, ...]
    summary: str
    applies_to_roles: tuple[str, ...] | None
    applies_to_archetypes: tuple[str, ...] | None
    required_by: dict[str, int]
    doctrine_anchors: tuple[str, ...]
    sections: tuple[str, ...]


def _string_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return ()


def _optional_string_tuple(value: object) -> tuple[str, ...] | None:
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return None


def _required_by(value: object) -> dict[str, int]:
    """Accept the ordered-map form ({workflow: rank}) and the legacy list form."""
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
        applies_to_archetypes=_optional_string_tuple(frontmatter.get("applies_to_archetypes")),
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
            if file.name == "README.md":
                continue
            entries.append(_entry_from_file(file, f"{prefix}/{file.name}"))
    return tuple(entries)


def _applies(entry: CatalogEntry, *, archetype: str, user_role: str) -> bool:
    if entry.applies_to_archetypes is not None and archetype not in entry.applies_to_archetypes:
        return False
    if entry.applies_to_roles is not None and user_role not in entry.applies_to_roles:
        return False
    return True


def select_required_paths(*, workflow: str, archetype: str, user_role: str) -> list[str]:
    """Mandatory doctrine + overlay + workflow seed paths, in load order.

    Output-identical to the hand-coded lists this replaces; the parity test
    covers every archetype x role combination for both workflows.
    """
    entries = file_catalog()
    archetype_entry = next(
        (
            entry
            for entry in entries
            if entry.tier == "archetype" and entry.loaded_by == f"archetype: {archetype}"
        ),
        None,
    )
    role_entry = next(
        (
            entry
            for entry in entries
            if entry.tier == "role-overlay" and entry.loaded_by == f"user_role: {user_role}"
        ),
        None,
    )
    if archetype_entry is None or role_entry is None:
        msg = f"Unsupported overlay combination: archetype={archetype!r}, user_role={user_role!r}"
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

    paths = [
        DOCTRINE_PATH,
        archetype_entry.path,
        role_entry.path,
        *(entry.path for entry in workflow_entries),
    ]
    seen: set[str] = set()
    ordered: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


async def ingested_platform_paths(session: AsyncSession) -> set[str]:
    stmt = select(SourceDocument.relative_path).where(_platform_scope_filter())
    result = await session.execute(stmt)
    return {row[0] for row in result.all()}


async def list_platform_knowledge(
    session: AsyncSession,
    *,
    archetype: str | None = None,
    user_role: str | None = None,
    topics: list[str] | None = None,
) -> list[dict]:
    """Catalog listing for agents: metadata and section IDs, never content.

    Entries are filtered to the declared overlays (an archetype guide for a
    different archetype is noise, not knowledge) and optionally by topic.
    `ingested=False` marks entries not yet servable from the corpus.
    """
    ingested = await ingested_platform_paths(session)
    wanted_topics = {topic.strip().lower() for topic in topics or [] if topic.strip()}

    listing: list[dict] = []
    for entry in file_catalog():
        if entry.tier == "archetype" and archetype is not None:
            if entry.loaded_by != f"archetype: {archetype}":
                continue
        if entry.tier == "role-overlay" and user_role is not None:
            if entry.loaded_by != f"user_role: {user_role}":
                continue
        if archetype is not None and user_role is not None:
            if not _applies(entry, archetype=archetype, user_role=user_role):
                continue
        if wanted_topics and not wanted_topics.intersection(
            topic.lower() for topic in entry.topics
        ):
            continue
        listing.append(
            {
                "path": entry.path,
                "title": entry.title,
                "tier": entry.tier,
                "topics": list(entry.topics),
                "summary": entry.summary,
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
    """Load a platform document whole (capped) or as targeted sections.

    Returns None when the document is not in the corpus. When any requested
    section ID is unknown, no content is served — the available section IDs
    come back instead so the caller can correct itself.
    """
    stmt = (
        select(*_document_columns(content_chars=None))
        .where(
            _platform_scope_filter(),
            SourceDocument.relative_path == path,
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return None

    full_text = row.normalized_content or ""
    available = list_section_ids(full_text)

    requested = [ref.strip() for ref in section_ids or [] if ref.strip()]
    if not requested:
        passage = _row_to_passage(row, max_chars=max_chars, terms=[])
        capped = SourcePassage(
            **{**passage.model_dump(), "content": full_text[:max_chars]}
        )
        return LoadedKnowledge(passage=capped, missing_sections=[], available_sections=available)

    assembled = assemble_sections(full_text, requested, max_chars=max_chars)
    if assembled is None:
        missing = [ref for ref in requested if ref not in available]
        return LoadedKnowledge(
            passage=None, missing_sections=missing, available_sections=available
        )

    passage = _row_to_passage(row, max_chars=max_chars, terms=[])
    section_passage = SourcePassage(
        **{
            **passage.model_dump(),
            "content": assembled,
            "chunk_metadata": {"whole_document": True, "section_ids": requested},
        }
    )
    return LoadedKnowledge(
        passage=section_passage, missing_sections=[], available_sections=available
    )

"""Deterministic heading splitter for platform knowledge documents.

Splits doctrine and seed markdown into addressable sections so callers can
load a targeted slice instead of the whole document. The doctrine's heading
structure (# preamble, ## 00-brief-pmp … ## 09-handover-dlp, # Cross-cutting
rules with ## §-anchors) is a tested contract — see tests/sitewise.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,2})\s+(.+?)\s*$")
_FENCE_RE = re.compile(r"^(```|~~~)")
_SLUG_KEEP_RE = re.compile(r"[^a-z0-9§]+")


@dataclass(frozen=True)
class MarkdownSection:
    section_id: str
    heading: str
    level: int
    parent_id: str | None
    start: int
    end: int
    content: str


def slugify_heading(heading: str) -> str:
    slug = _SLUG_KEEP_RE.sub("-", heading.lower())
    return slug.strip("-")


def _frontmatter_end(lines: list[str]) -> int:
    """Return the line index just past a leading frontmatter block, else 0."""
    if not lines or lines[0].strip() != "---":
        return 0
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return index + 1
    return 0


def split_sections(text: str, *, max_level: int = 2) -> list[MarkdownSection]:
    """Split markdown into heading-bounded sections (levels 1..max_level).

    Section content includes the heading line. A level-1 section spans until
    the next level-1 heading (so it contains its level-2 children); a level-2
    section spans until the next heading of level 1 or 2. Headings inside
    fenced code blocks are ignored. Section IDs are heading slugs; on a slug
    collision the ID is qualified as "<parent-slug>/<slug>".
    """
    lines = text.splitlines(keepends=True)
    skip_lines = _frontmatter_end(lines)

    # (level, heading, char_offset) for each real heading
    headings: list[tuple[int, str, int]] = []
    offset = 0
    in_fence = False
    for index, line in enumerate(lines):
        if index >= skip_lines:
            if _FENCE_RE.match(line):
                in_fence = not in_fence
            elif not in_fence:
                match = _HEADING_RE.match(line)
                if match and len(match.group(1)) <= max_level:
                    headings.append((len(match.group(1)), match.group(2), offset))
        offset += len(line)
    total = offset

    sections: list[MarkdownSection] = []
    seen_ids: set[str] = set()
    parent_slug: str | None = None
    parent_id: str | None = None
    for position, (level, heading, start) in enumerate(headings):
        end = total
        for next_level, _, next_start in headings[position + 1 :]:
            if next_level <= level:
                end = next_start
                break

        slug = slugify_heading(heading)
        if level == 1:
            parent_slug = slug
            parent_id = None
        section_id = slug
        if section_id in seen_ids and level > 1 and parent_slug:
            section_id = f"{parent_slug}/{slug}"
        seen_ids.add(section_id)

        sections.append(
            MarkdownSection(
                section_id=section_id,
                heading=heading,
                level=level,
                parent_id=parent_id if level > 1 else None,
                start=start,
                end=end,
                content=text[start:end],
            )
        )
        if level == 1:
            parent_id = section_id
    return sections


def section_by_id(sections: list[MarkdownSection], ref: str) -> MarkdownSection | None:
    """Look up a section by exact ID, or by bare slug when unambiguous."""
    for section in sections:
        if section.section_id == ref:
            return section
    suffix_matches = [
        section for section in sections if section.section_id.rsplit("/", 1)[-1] == ref
    ]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    return None


def assemble_sections(
    text: str,
    section_ids: list[str],
    *,
    max_chars: int | None = None,
) -> str | None:
    """Concatenate the requested sections in document order.

    Returns None when any requested section is missing, so callers can fall
    back to whole-document behaviour rather than silently serving a subset.
    """
    sections = split_sections(text)
    resolved: list[MarkdownSection] = []
    for ref in section_ids:
        section = section_by_id(sections, ref)
        if section is None:
            return None
        resolved.append(section)

    resolved.sort(key=lambda section: section.start)
    deduped: list[MarkdownSection] = []
    for section in resolved:
        if deduped and section.start < deduped[-1].end:
            continue  # nested or duplicate span already covered
        deduped.append(section)

    assembled = "".join(section.content for section in deduped).strip()
    if max_chars is not None:
        assembled = assembled[:max_chars]
    return assembled


def list_section_ids(text: str) -> list[str]:
    return [section.section_id for section in split_sections(text)]


CROSS_CUTTING_SECTION_ID = "cross-cutting-rules"


def doctrine_core_content(text: str, *, max_chars: int | None = None) -> str | None:
    """Assemble the always-loaded doctrine core.

    Core = the preamble (first level-1 section: authority stack, project-lead
    role, core principle) plus the entire Cross-cutting rules block. The ten
    stage sections (00-brief-pmp … 09-handover-dlp) and sub-roles stay
    on-demand. Returns None when the doctrine's heading structure is not
    recognised, so callers can fall back to truncated whole-document loading.
    """
    sections = split_sections(text)
    preamble = next((section for section in sections if section.level == 1), None)
    cross_cutting = section_by_id(sections, CROSS_CUTTING_SECTION_ID)
    if preamble is None or cross_cutting is None or preamble.start >= cross_cutting.start:
        return None
    assembled = (preamble.content + cross_cutting.content).strip()
    if max_chars is not None:
        assembled = assembled[:max_chars]
    return assembled

"""Length validation for the primary 2-4 page PMP view."""

from __future__ import annotations

import json
import re

from app.sitewise.markdown_sections import split_sections
from app.sitewise.section_contracts import (
    PMP_SECTION_HEADINGS,
    heading_for_section_id,
    section_id_for_heading,
)

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")
_FENCE_RE = re.compile(r"^\s*(```|~~~)\s*([A-Za-z0-9_-]*)")
_LINK_RE = re.compile(r"!?\[([^\]]+)\]\([^)]+\)")
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def pmp_word_count(markdown: str) -> int:
    """Count words as rendered in the primary PMP view."""
    return _count_words(_primary_markdown(markdown))


def length_violations(
    markdown: str,
    *,
    weights: dict[str, float],
    min_words: int,
    max_words: int,
) -> list[str]:
    """Return actionable length feedback for the PMP retry loop."""
    total = pmp_word_count(markdown)
    violations: list[str] = []
    hard_max = int(max_words * 1.05)
    if total > hard_max:
        overshoot = total - max_words
        violations.append(
            f"Draft is {total} words, maximum {max_words} (5% tolerance {hard_max}) "
            f"- condense by about {overshoot} words."
        )
    if total < min_words:
        section = _highest_weighted_section(weights)
        violations.append(
            f"Draft is {total} words, minimum {min_words} - deepen "
            f"{_display_section(section)} with project-specific content."
        )

    for heading, section_words in _section_word_counts(markdown):
        section_id = _section_id_for_heading_any(heading)
        if section_id is None or section_id not in weights:
            continue
        target = int(weights[section_id] * max_words)
        limit = int(weights[section_id] * max_words * 1.5)
        if target <= 0 or section_words <= limit:
            continue
        violations.append(
            f"{heading} is {section_words} words, budget ~{target} - condense."
        )
    return violations


def _primary_markdown(markdown: str) -> str:
    return _replace_decision_fences(_drop_collapsed_blocks(_drop_annexure_sections(markdown)))


def _drop_annexure_sections(markdown: str) -> str:
    lines = markdown.splitlines()
    kept: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip().lower()
        if stripped.startswith("## "):
            heading = stripped[3:].strip()
            skipping = heading.startswith("annexure") or heading.startswith("appendix")
        if not skipping:
            kept.append(line)
    return "\n".join(kept)


def _drop_collapsed_blocks(markdown: str) -> str:
    lines = markdown.splitlines()
    kept: list[str] = []
    in_details = False
    for line in lines:
        lower = line.strip().lower()
        if lower.startswith("<details"):
            in_details = True
            continue
        if in_details:
            if lower.startswith("</details"):
                in_details = False
            continue
        kept.append(line)
    return "\n".join(kept)


def _replace_decision_fences(markdown: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    index = 0
    while index < len(lines):
        match = _FENCE_RE.match(lines[index])
        if match is None:
            output.append(lines[index])
            index += 1
            continue
        fence = match.group(1)
        info = match.group(2)
        index += 1
        body: list[str] = []
        while index < len(lines) and not lines[index].strip().startswith(fence):
            body.append(lines[index])
            index += 1
        if index < len(lines):
            index += 1
        if info == "pmp-decision":
            output.append(_selected_decision_label("\n".join(body)))
        else:
            output.extend(body)
    return "\n".join(output)


def _selected_decision_label(payload_text: str) -> str:
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return ""
    selected = payload.get("selected") or payload.get("selected_option")
    options = payload.get("options")
    if not isinstance(options, list):
        return str(selected or "")
    for option in options:
        if not isinstance(option, dict):
            continue
        if option.get("id") == selected or option.get("value") == selected:
            label = option.get("label") or option.get("title")
            return str(label or selected or "")
    return str(selected or "")


def _count_words(markdown: str) -> int:
    text = _LINK_RE.sub(r"\1", markdown)
    text = _HTML_TAG_RE.sub(" ", text)
    text = text.replace("|", " ")
    text = re.sub(r"[#>*_`~\[\]():,.;!?/\\{}=+-]", " ", text)
    return len(_WORD_RE.findall(text))


def _section_word_counts(markdown: str) -> list[tuple[str, int]]:
    sections = [section for section in split_sections(_primary_markdown(markdown)) if section.level == 2]
    return [(section.heading, _count_words(section.content)) for section in sections]


def _highest_weighted_section(weights: dict[str, float]) -> str:
    candidates = [(section, weight) for section, weight in weights.items() if section != "snapshot"]
    if not candidates:
        candidates = list(weights.items())
    return max(candidates, key=lambda item: item[1])[0]


def _display_section(section_id: str) -> str:
    return PMP_SECTION_HEADINGS.get(section_id, section_id)


def _section_id_for_heading_any(heading: str) -> str | None:
    direct = section_id_for_heading(heading, work_type=None)
    if direct is not None:
        return direct
    advisory = section_id_for_heading(heading, work_type="advisory")
    if advisory is not None:
        return advisory
    normalized = heading.strip().lower()
    for section_id in PMP_SECTION_HEADINGS:
        if heading_for_section_id(section_id, work_type=None).lower() == normalized:
            return section_id
    return None

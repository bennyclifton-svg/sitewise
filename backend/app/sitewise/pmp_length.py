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
FINAL_LENGTH_TOLERANCE = 1.15


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


def within_final_length_tolerance(markdown: str, *, max_words: int) -> bool:
    """Return true for a small final overrun after the model retry loop."""
    return pmp_word_count(markdown) <= int(max_words * FINAL_LENGTH_TOLERANCE)


def condense_primary_markdown_to_word_band(
    markdown: str,
    *,
    weights: dict[str, float],
    min_words: int,
    max_words: int,
) -> str:
    """Deterministically compact an overlong primary PMP without changing annexures."""
    hard_max = int(max_words * 1.05)
    if pmp_word_count(markdown) <= hard_max:
        return markdown

    target_sections = _oversized_section_ids(markdown, weights, max_words)
    if not target_sections:
        target_sections = {section for section in weights if section != "snapshot"}

    passes = [
        (target_sections, 14, 18),
        (target_sections, 10, 14),
        (set(weights), 10, 14),
        (set(weights), 8, 11),
    ]
    compacted = markdown
    for sections, table_words, line_words in passes:
        compacted = _condense_sections(
            compacted,
            target_sections=sections,
            table_cell_words=table_words,
            line_words=line_words,
        )
        if pmp_word_count(compacted) <= hard_max:
            return compacted
        if pmp_word_count(compacted) < min_words:
            return compacted
    return compacted


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


def _oversized_section_ids(
    markdown: str,
    weights: dict[str, float],
    max_words: int,
) -> set[str]:
    oversized: set[str] = set()
    for heading, section_words in _section_word_counts(markdown):
        section_id = _section_id_for_heading_any(heading)
        if section_id is None or section_id not in weights:
            continue
        limit = int(weights[section_id] * max_words * 1.5)
        if section_words > limit:
            oversized.add(section_id)
    return oversized


def _condense_sections(
    markdown: str,
    *,
    target_sections: set[str],
    table_cell_words: int,
    line_words: int,
) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    current_section: str | None = None
    in_fence = False
    for line in lines:
        fence = _FENCE_RE.match(line)
        if fence:
            in_fence = not in_fence
            output.append(line)
            continue

        if not in_fence and line.startswith("## "):
            current_section = _section_id_for_heading_any(line[3:].strip())
            output.append(line)
            continue

        if in_fence or current_section not in target_sections:
            output.append(line)
            continue

        if _is_table_separator(line):
            output.append(line)
        elif _is_table_row(line):
            output.append(_condense_table_row(line, table_cell_words))
        else:
            output.append(_condense_markdown_line(line, line_words))
    return "\n".join(output)


def _is_table_row(line: str) -> bool:
    return line.lstrip().startswith("|") and line.rstrip().endswith("|")


def _is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if not _is_table_row(stripped):
        return False
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    return all(cell and set(cell) <= {"-", ":"} for cell in cells)


def _condense_table_row(line: str, word_limit: int) -> str:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    compacted = [_truncate_text(cell, word_limit) for cell in cells]
    return "| " + " | ".join(compacted) + " |"


def _condense_markdown_line(line: str, word_limit: int) -> str:
    if not line.strip() or line.lstrip().startswith("#"):
        return line
    match = re.match(r"^(\s*(?:[-*+]|\d+[.)])\s+)(.+)$", line)
    if match:
        return match.group(1) + _truncate_text(match.group(2), word_limit)
    return _truncate_text(line, word_limit)


def _truncate_text(text: str, word_limit: int) -> str:
    if len(_WORD_RE.findall(text)) <= word_limit:
        return text
    kept: list[str] = []
    words = 0
    for token in text.split():
        token_words = len(_WORD_RE.findall(token))
        if token_words and words + token_words > word_limit:
            break
        kept.append(token)
        words += token_words
    compacted = " ".join(kept).rstrip(" ,;:-")
    if compacted.endswith((".", "!", "?", ")")):
        return compacted
    return compacted + "."


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

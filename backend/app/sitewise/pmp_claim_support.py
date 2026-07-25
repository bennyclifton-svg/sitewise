"""Conservative lexical support checks for cited PMP claims."""

from __future__ import annotations

import re
from collections.abc import Sequence

_CITATION_RE = re.compile(r"\[(\d+)\]")
_KEY_LINE_RE = re.compile(r"^\s*(?:[-*]\s*)?\[(\d+)\]\s+(.+?)\s*$")
_WORD_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", re.IGNORECASE)
_NUMBER_WORDS = frozenset(
    {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"}
)
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "project",
        "status",
        "the",
        "to",
        "with",
    }
)


def citation_claim_support_violations(
    markdown: str,
    *,
    source_texts: Sequence[str],
    source_labels: Sequence[str],
) -> list[str]:
    """Reject only clearly unsupported claims attached to a mapped citation.

    This is deliberately conservative: it does not try to prove every
    paraphrase. It catches citations where a concrete, content-rich claim has
    almost no lexical relationship to the cited document.
    """
    if not source_texts or not source_labels:
        return []
    citation_sources = _citation_source_map(markdown, source_texts, source_labels)
    if not citation_sources:
        return []

    body = _before_citation_key(markdown)
    violations: list[str] = []
    for line in body.splitlines():
        refs = _CITATION_RE.findall(line)
        if not refs:
            continue
        claim = _CITATION_RE.sub("", line)
        claim_tokens = _meaningful_tokens(claim)
        if len(claim_tokens) < 4:
            continue
        source = "\n".join(citation_sources.get(ref, "") for ref in refs)
        if not source:
            continue
        source_tokens = set(_meaningful_tokens(source))
        overlap = set(claim_tokens) & source_tokens
        concrete = any(token.isdigit() or token in _NUMBER_WORDS for token in claim_tokens)
        minimum_overlap = 2 if concrete else 3
        if len(overlap) >= minimum_overlap:
            continue
        excerpt = " ".join(claim.split()).strip(" |-")
        violations.append(
            "Cited claim is not supported by the mapped source text: "
            f"{excerpt[:180]}"
        )
    return _dedupe(violations)


def exclusion_citation_violations(markdown: str) -> list[str]:
    """Require evidence for exclusions presented as current project facts."""
    brief = _markdown_section(markdown, "Brief")
    if not brief:
        return []
    collecting = False
    violations: list[str] = []
    for line in brief.splitlines():
        stripped = line.strip()
        lowered = stripped.casefold()
        if stripped.startswith("### "):
            collecting = "exclusion" in lowered
            continue
        if not stripped:
            continue
        first_cell = stripped.strip("|").split("|", 1)[0].strip().casefold()
        exclusion_row = first_cell in {"exclusion", "exclusions"}
        if not collecting and not exclusion_row:
            continue
        if stripped.startswith("#"):
            collecting = False
            continue
        if _is_table_header_or_rule(stripped):
            continue
        if _CITATION_RE.search(stripped):
            continue
        if "user provided" in lowered:
            continue
        if any(
            marker in lowered
            for marker in (
                "assumption",
                "not evidenced",
                "unverified",
                "design-development gap",
                "design development gap",
            )
        ) and not re.search(
            r"\b(?:are|is|remain|confirmed)\s+excluded?\b",
            lowered,
        ):
            continue
        content = stripped.strip("|- ")
        if len(_meaningful_tokens(content)) < 2:
            continue
        violations.append(
            "Brief exclusion stated without a supporting citation or explicit "
            f"unverified status: {content[:180]}"
        )
    return _dedupe(violations)


def _citation_source_map(
    markdown: str,
    source_texts: Sequence[str],
    source_labels: Sequence[str],
) -> dict[str, str]:
    labels = list(source_labels[: len(source_texts)])
    labels.extend(
        f"evidence document {index + 1}"
        for index in range(len(labels), len(source_texts))
    )
    normalized = [(_normalize_label(label), text) for label, text in zip(labels, source_texts, strict=True)]
    key = _citation_key(markdown)
    output: dict[str, str] = {}
    for line in key.splitlines():
        match = _KEY_LINE_RE.match(line)
        if not match:
            continue
        number, description = match.groups()
        description_key = _normalize_label(description)
        matches = [
            text
            for label, text in normalized
            if label and (label in description_key or description_key.startswith(label))
        ]
        if matches:
            output[number] = "\n".join(matches)
    return output


def _citation_key(markdown: str) -> str:
    collecting = False
    lines: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip().casefold()
        if stripped.startswith("## "):
            collecting = stripped[3:].strip() == "citation key"
            continue
        if collecting:
            lines.append(line)
    return "\n".join(lines)


def _before_citation_key(markdown: str) -> str:
    lines: list[str] = []
    for line in markdown.splitlines():
        if line.strip().casefold() == "## citation key":
            break
        lines.append(line)
    return "\n".join(lines)


def _markdown_section(markdown: str, heading: str) -> str:
    target = heading.casefold()
    lines: list[str] = []
    collecting = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            collecting = stripped[3:].strip().casefold() == target
            continue
        if collecting:
            lines.append(line)
    return "\n".join(lines)


def _normalize_label(value: str) -> str:
    value = value.split("—", 1)[0].split(" - ", 1)[0]
    value = value.replace("\\", "/").rsplit("/", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _meaningful_tokens(value: str) -> list[str]:
    return [
        token
        for token in (match.group(0).casefold() for match in _WORD_RE.finditer(value))
        if token not in _STOPWORDS and len(token) > 1
    ]


def _is_table_header_or_rule(line: str) -> bool:
    cells = [cell.strip().casefold() for cell in line.strip("|").split("|")]
    if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
        return True
    return any(cell in {"item", "exclusion", "position", "status"} for cell in cells)


def _dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))

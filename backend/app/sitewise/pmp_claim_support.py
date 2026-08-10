"""Conservative lexical support checks for cited PMP claims."""

from __future__ import annotations

import re
from collections.abc import Sequence

_CITATION_RE = re.compile(r"\[(\d+)\]")
_KEY_LINE_RE = re.compile(r"^\s*(?:[-*]\s*)?\[(\d+)\]\s+(.+?)\s*$")
_WORD_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", re.IGNORECASE)
_REGISTER_ROW_RE = re.compile(r"(?:^\s*\**\s*|\|\s*)([RA]\d{2})\b")
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
_PROVENANCE_MARKERS = (
    "assumption",
    "user provided",
    "not evidenced",
    "unverified",
    "design-development gap",
    "design development gap",
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

    Provenance-labelled lines (Assumption / User provided / Not evidenced),
    forward action/risk register rows, and evidence-status meta rows are out of
    scope — those are not grounded evidence claims.
    """
    if not source_texts or not source_labels:
        return []
    citation_sources = _citation_source_map(markdown, source_texts, source_labels)
    if not citation_sources:
        return []
    citation_labels = _citation_label_map(markdown, source_labels, source_texts)

    body = _before_citation_key(markdown)
    violations: list[str] = []
    for line in body.splitlines():
        refs = _CITATION_RE.findall(line)
        if not refs:
            continue
        claim = _CITATION_RE.sub("", line)
        if _is_exempt_claim(claim):
            continue
        claim_tokens = _meaningful_tokens(claim)
        if len(claim_tokens) < 4:
            continue
        source = "\n".join(citation_sources.get(ref, "") for ref in refs)
        if not source:
            continue
        source_tokens = set(_meaningful_tokens(source))
        overlap = set(claim_tokens) & source_tokens
        # Comma-insensitive numeric support: "$1,234,000" vs "$1234000".
        overlap.update(_numeric_overlap(claim, source))
        concrete = any(
            token.isdigit() or token in _NUMBER_WORDS for token in claim_tokens
        ) or bool(_numeric_runs(claim))
        minimum_overlap = 2 if concrete else 3
        if len(overlap) >= minimum_overlap:
            continue
        # If another loaded project document clearly supports the claim, the
        # citation is pointed at the wrong file — do not hard-block Create PMP.
        if _corpus_supports_claim(
            claim,
            claim_tokens,
            source_texts=source_texts,
            minimum_overlap=minimum_overlap,
            concrete=concrete,
        ):
            continue
        excerpt = " ".join(claim.split()).strip(" |-")
        mapped = ", ".join(
            citation_labels.get(ref, f"[{ref}]") for ref in refs if ref in citation_sources
        )
        violations.append(
            "Cited claim is not supported by the mapped source text"
            + (f" ({mapped})" if mapped else "")
            + f": {excerpt[:180]}"
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


def _is_exempt_claim(claim: str) -> bool:
    lowered = claim.casefold()
    if any(marker in lowered for marker in _PROVENANCE_MARKERS):
        return True
    if _REGISTER_ROW_RE.search(claim):
        return True
    first_cell = claim.strip().strip("|").split("|", 1)[0].strip().casefold()
    if first_cell in {"evidence status", "section", "citation", "ref"}:
        return True
    return False


def _corpus_supports_claim(
    claim: str,
    claim_tokens: list[str],
    *,
    source_texts: Sequence[str],
    minimum_overlap: int,
    concrete: bool,
) -> bool:
    claim_token_set = set(claim_tokens)
    for source in source_texts:
        if not source.strip():
            continue
        overlap = claim_token_set & set(_meaningful_tokens(source))
        overlap.update(_numeric_overlap(claim, source))
        if len(overlap) >= minimum_overlap:
            return True
        if concrete and len(overlap) >= 2:
            return True
    return False


def _numeric_runs(value: str) -> set[str]:
    """Digit runs of length >= 3 with commas/spaces stripped from the source span."""
    compact = re.sub(r"[,\s]", "", value)
    return {match.group(0) for match in re.finditer(r"\d{3,}", compact)}


def _numeric_overlap(claim: str, source: str) -> set[str]:
    return _numeric_runs(claim) & _numeric_runs(source)


def _citation_source_map(
    markdown: str,
    source_texts: Sequence[str],
    source_labels: Sequence[str],
) -> dict[str, str]:
    labeled = _labeled_sources(source_texts, source_labels)
    key = _citation_key(markdown)
    output: dict[str, str] = {}
    for line in key.splitlines():
        match = _KEY_LINE_RE.match(line)
        if not match:
            continue
        number, description = match.groups()
        matches = _match_sources(description, labeled)
        if matches:
            output[number] = "\n".join(text for _label, text in matches)
    return output


def _citation_label_map(
    markdown: str,
    source_labels: Sequence[str],
    source_texts: Sequence[str],
) -> dict[str, str]:
    labeled = _labeled_sources(source_texts, source_labels)
    key = _citation_key(markdown)
    output: dict[str, str] = {}
    for line in key.splitlines():
        match = _KEY_LINE_RE.match(line)
        if not match:
            continue
        number, description = match.groups()
        matches = _match_sources(description, labeled)
        if matches:
            output[number] = ", ".join(label for label, _text in matches)
    return output


def _labeled_sources(
    source_texts: Sequence[str],
    source_labels: Sequence[str],
) -> list[tuple[str, str, str]]:
    labels = list(source_labels[: len(source_texts)])
    labels.extend(
        f"evidence document {index + 1}"
        for index in range(len(labels), len(source_texts))
    )
    return [
        (label, _normalize_label(label), text)
        for label, text in zip(labels, source_texts, strict=True)
    ]


def _match_sources(
    description: str,
    labeled: Sequence[tuple[str, str, str]],
) -> list[tuple[str, str]]:
    description_key = _normalize_label(description)
    if not description_key:
        return []
    exact = [
        (label, text)
        for label, normalized, text in labeled
        if normalized and normalized == description_key
    ]
    if exact:
        return exact
    # Prefer the longest label match so short stems cannot steal a citation.
    partial = [
        (len(normalized), label, text)
        for label, normalized, text in labeled
        if normalized
        and (
            normalized in description_key
            or description_key in normalized
            or description_key.startswith(normalized)
        )
    ]
    if not partial:
        return []
    partial.sort(reverse=True)
    best_len = partial[0][0]
    return [(label, text) for length, label, text in partial if length == best_len]


def _citation_key(markdown: str) -> str:
    sections: list[str] = []
    collecting = False
    current: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip().casefold()
        if stripped.startswith("## "):
            if collecting:
                sections.append("\n".join(current))
            collecting = stripped[3:].strip() == "citation key"
            current = []
            continue
        if collecting:
            current.append(line)
    if collecting:
        sections.append("\n".join(current))
    # Prefer the final Citation key when a draft accidentally emits more than one.
    return sections[-1] if sections else ""


def _before_citation_key(markdown: str) -> str:
    lines: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip().casefold()
        if stripped.startswith("## ") and stripped[3:].strip() == "citation key":
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
    # Drop fragment / query suffixes from evidence-ref style paths.
    value = value.split("#", 1)[0].split("?", 1)[0]
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

"""High-signal evidence digest and conflict ledger for PMP generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from collections.abc import Sequence

_SPACE_RE = re.compile(r"\s+")
_UNIT_RE = re.compile(r"\bunit\s+(\d+[a-z]?)\b", re.IGNORECASE)
_AREA_AFTER_RE = re.compile(
    r"\b(gfa|gla|nla|gross floor area|gross lettable area|net lettable area)"
    r"\b[^\d]{0,45}(\d[\d,]*(?:\.\d+)?)\s*(?:m2|m²|sqm)\b",
    re.IGNORECASE,
)
_AREA_BEFORE_RE = re.compile(
    r"\b(\d[\d,]*(?:\.\d+)?)\s*(?:m2|m²|sqm)\b[^\n.]{0,45}"
    r"\b(gfa|gla|nla|gross floor area|gross lettable area|net lettable area)\b",
    re.IGNORECASE,
)
_AREA_VALUE_RE = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*(?:m2|m²|sqm|square metres?)\b",
    re.IGNORECASE,
)
_CONCRETE_RE = re.compile(
    r"(?:\d|\$|\bmust\b|\bshall\b|\brequired\b|\bnot permitted\b|\bexcluded?\b|"
    r"\bnon[- ]?compli|\bperformance solution\b|\bapproval\b|\bconsent\b)",
    re.IGNORECASE,
)

_PRIORITY_TERMS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (
        8,
        (
            "performance solution",
            "non-compliance",
            "noncompliance",
            "not compliant",
            "condition of consent",
            "deferred commencement",
            "clause 4.6",
            "occupation certificate",
        ),
    ),
    (
        6,
        (
            "development application",
            "construction certificate",
            "complying development",
            "approval pathway",
            "planning pathway",
            "exclusion",
            "excluded",
            "out of scope",
            "owner supplied",
            "tenant scope",
            "landlord scope",
        ),
    ),
    (
        5,
        (
            "gross floor area",
            "gross lettable area",
            "gfa",
            "gla",
            "nla",
            "unit ",
            "warehouse",
            "mezzanine",
            "office",
            "programme",
            "practical completion",
            "procurement",
            "contract",
            "budget",
            "cost plan",
        ),
    ),
    (
        3,
        (
            "must",
            "shall",
            "required",
            "recommend",
            "risk",
            "interface",
            "appointment",
            "consultant",
            "authority",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class EvidenceConflict:
    subject: str
    values: tuple[str, ...]
    sources: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceLedger:
    critical_facts: tuple[tuple[str, str], ...]
    conflicts: tuple[EvidenceConflict, ...]


def build_document_digest(text: str, *, max_chars: int = 4_500) -> str:
    """Keep document identity plus high-consequence spans from the full file.

    The old implementation took only the first 8,000 characters. Reports often
    place conclusions, exclusions and performance solutions near the end, so
    that approach was both expensive and lossy.
    """
    clean = text.strip()
    if len(clean) <= max_chars:
        return clean

    lines = [line.strip() for line in clean.splitlines() if line.strip()]
    if not lines:
        return clean[:max_chars]

    selected: list[tuple[int, int, str]] = []
    head_budget = min(1_600, max_chars // 2)
    head = clean[:head_budget].rsplit("\n", 1)[0].strip()
    if head:
        selected.append((100, -1, head))

    for index, line in enumerate(lines):
        normalized = _normalize(line)
        if len(normalized) < 12:
            continue
        if any(
            marker in normalized
            for marker in ("area schedule", "scope exclusions", "service exclusions")
        ):
            window = "\n".join(lines[index : index + 8])
            selected.append((7, index, _trim_span(window, 900)))
        score = _priority_score(normalized)
        if score and (_CONCRETE_RE.search(normalized) or score >= 6):
            selected.append((score, index, _trim_span(line, 420)))

    tail = clean[-700:].split("\n", 1)[-1].strip()
    if tail:
        selected.append((2, len(lines) + 1, tail))

    # Highest consequence first, while retaining source line order within a tier.
    selected.sort(key=lambda item: (-item[0], item[1]))
    output: list[str] = []
    seen: set[str] = set()
    used = 0
    for _score, _index, span in selected:
        key = _normalize(span)
        if not key or key in seen:
            continue
        addition = len(span) + (2 if output else 0)
        if used + addition > max_chars:
            continue
        output.append(span)
        seen.add(key)
        used += addition
    return "\n\n".join(output)


def build_evidence_ledger(
    source_texts: Sequence[str],
    source_labels: Sequence[str],
    *,
    max_facts: int = 24,
) -> EvidenceLedger:
    labels = _parallel_labels(source_texts, source_labels)
    candidates: list[tuple[int, str, str]] = []
    for text, label in zip(source_texts, labels, strict=True):
        for line in text.splitlines():
            span = _trim_span(line.strip(), 360)
            normalized = _normalize(span)
            if len(normalized) < 18:
                continue
            score = _priority_score(normalized)
            if score >= 5 and (_CONCRETE_RE.search(normalized) or score >= 8):
                candidates.append((score, label, span))

    candidates.sort(key=lambda item: -item[0])
    facts: list[tuple[str, str]] = []
    seen: set[str] = set()
    per_source: dict[str, int] = {}
    source_topics: set[tuple[str, str]] = set()
    for _score, label, span in candidates:
        key = _normalize(span)
        if key in seen:
            continue
        if per_source.get(label, 0) >= 3:
            continue
        topic = _fact_topic(key)
        if topic and (label, topic) in source_topics:
            continue
        facts.append((label, span))
        seen.add(key)
        per_source[label] = per_source.get(label, 0) + 1
        if topic:
            source_topics.add((label, topic))
        if len(facts) >= max_facts:
            break

    return EvidenceLedger(
        critical_facts=tuple(facts),
        conflicts=tuple(
            _identity_conflicts(source_texts, labels)
            + _area_conflicts(source_texts, labels)
        ),
    )


def format_evidence_ledger(ledger: EvidenceLedger) -> str:
    lines = [
        "Evidence authority and priority rules:",
        "- Statutory approvals and current authority records govern compliance status.",
        "- Within the same document family, the current approved revision governs an older revision.",
        "- Current project briefs and design reports govern their own subject matter; user-locked "
        "decisions govern choices but cannot override statutory facts.",
        "- Platform knowledge is guidance only and must not be cited as project evidence.",
        "- Do not silently resolve a conflict by document date alone when the sources have different authority.",
    ]
    if ledger.conflicts:
        lines.extend(
            [
                "",
                "Critical source conflicts — state both values in the relevant control "
                "section detail cell and cite the sources; do not write Conflict or "
                "requiring resolution as status labels (citation colour signals disagreement):",
            ]
        )
        for conflict in ledger.conflicts:
            pairs = "; ".join(
                f"{value} ({source})"
                for value, source in zip(conflict.values, conflict.sources, strict=True)
            )
            lines.append(f"- {conflict.subject}: {pairs}")
    if ledger.critical_facts:
        lines.extend(
            [
                "",
                "High-consequence source spans (quote or faithfully paraphrase; never combine "
                "tokens from separate spans into a new fact):",
            ]
        )
        lines.extend(f"- {label}: {span}" for label, span in ledger.critical_facts)
    return "\n".join(lines)


def conflict_summary_violations(
    markdown: str,
    ledger: EvidenceLedger,
) -> list[str]:
    """Require every curated conflict value somewhere in the issued draft body."""
    if not ledger.conflicts:
        return []
    normalized = _normalize_comparison(markdown)
    violations: list[str] = []
    for conflict in ledger.conflicts:
        missing = [
            value
            for value in conflict.values
            if _conflict_anchor(value) not in normalized
        ]
        if missing:
            violations.append(
                f"Draft does not surface {conflict.subject}: " + ", ".join(missing)
            )
    return violations


def _identity_conflicts(
    texts: Sequence[str], labels: Sequence[str]
) -> list[EvidenceConflict]:
    values: dict[str, str] = {}
    for _text, label, value in _identity_sources(texts, labels):
        values.setdefault(value.casefold(), label)
    if len(values) < 2:
        return []
    ordered = sorted(values.items())
    return [
        EvidenceConflict(
            subject="Project/unit identity conflict",
            values=tuple(
                f"Unit {key.removeprefix('unit ')}".upper().replace("UNIT ", "Unit ")
                for key, _ in ordered
            ),
            sources=tuple(source for _, source in ordered),
        )
    ]


def _area_conflicts(
    texts: Sequence[str], labels: Sequence[str]
) -> list[EvidenceConflict]:
    values: dict[str, tuple[str, str]] = {}
    for text, label, _unit in _identity_sources(texts, labels):
        area = _primary_project_area(text)
        if area is None:
            continue
        value, qualifier = area
        values.setdefault(value, (label, qualifier))
    if len(values) < 2:
        return []
    ordered = sorted(values.items())
    return [
        EvidenceConflict(
            subject="Total project area conflict",
            values=tuple(
                f"{value} m2{f' {qualifier}' if qualifier else ''}"
                for value, (_source, qualifier) in ordered
            ),
            sources=tuple(source for _value, (source, _qualifier) in ordered),
        )
    ]


def _identity_sources(
    texts: Sequence[str],
    labels: Sequence[str],
) -> list[tuple[str, str, str]]:
    output: list[tuple[str, str, str]] = []
    for text, label in zip(texts, labels, strict=True):
        label_key = label.casefold()
        head = text[:4_000].casefold()
        identity_bearing = any(
            marker in label_key
            for marker in (
                "brief",
                "site plan",
                "development application",
                "da report",
                "statement of environmental",
            )
        ) or any(
            marker in head
            for marker in (
                "report for development application",
                "support of the development application",
            )
        )
        if not identity_bearing:
            continue
        match = _UNIT_RE.search(text[:6_000])
        if match:
            output.append((text, label, f"Unit {match.group(1).upper()}"))
    return output


def _primary_project_area(text: str) -> tuple[str, str] | None:
    folded = text.casefold()
    schedule_start = folded.find("area schedule")
    if schedule_start >= 0:
        schedule_end = folded.find("all building areas", schedule_start)
        if schedule_end < 0:
            schedule_end = schedule_start + 800
        values = _AREA_VALUE_RE.findall(text[schedule_start:schedule_end])
        if values:
            qualifier = "GLA" if "gross lettable area" in folded else ""
            return _canonical_number(values[-1]), qualifier

    total_patterns = (
        re.compile(
            r"(?:unit\s*\w+\s*)?(?:warehouse\s*&\s*office\s*)?total\s*gfa"
            r"\s*(\d[\d,]*(?:\.\d+)?)\s*(?:m2|m²|sqm)",
            re.IGNORECASE,
        ),
        re.compile(
            r"made up of\s+(\d[\d,]*(?:\.\d+)?)\s+square metres?"
            r"\s+of total (?:warehouse|building) space",
            re.IGNORECASE,
        ),
    )
    for pattern in total_patterns:
        match = pattern.search(text)
        if match:
            return _canonical_number(match.group(1)), "total area"

    metric_values: list[tuple[str, str]] = []
    for metric, value in _AREA_AFTER_RE.findall(text):
        metric_values.append((_canonical_number(value), _canonical_metric(metric)))
    for value, metric in _AREA_BEFORE_RE.findall(text):
        metric_values.append((_canonical_number(value), _canonical_metric(metric)))
    unique = list(dict.fromkeys(metric_values))
    return unique[0] if len(unique) == 1 else None


def _priority_score(normalized: str) -> int:
    return max(
        (
            score
            for score, terms in _PRIORITY_TERMS
            if any(term in normalized for term in terms)
        ),
        default=0,
    )


def _fact_topic(normalized: str) -> str:
    for topic in (
        "clause 4.6",
        "performance solution",
        "non-compliance",
        "noncompliance",
        "condition of consent",
        "development application",
        "construction certificate",
        "exclusion",
        "out of scope",
        "gross floor area",
        "gross lettable area",
        "programme",
        "procurement",
        "budget",
    ):
        if topic in normalized:
            return topic
    return ""


def _parallel_labels(texts: Sequence[str], labels: Sequence[str]) -> list[str]:
    output = list(labels[: len(texts)])
    output.extend(f"evidence document {index + 1}" for index in range(len(output), len(texts)))
    return output


def _trim_span(span: str, limit: int) -> str:
    value = _SPACE_RE.sub(" ", span).strip(" |-")
    if len(value) <= limit:
        return value
    return value[:limit].rsplit(" ", 1)[0] + "…"


def _normalize(value: str) -> str:
    return _SPACE_RE.sub(" ", value.casefold()).strip()


def _canonical_metric(value: str) -> str:
    folded = value.casefold()
    if folded in {"gfa", "gross floor area"}:
        return "GFA"
    if folded in {"gla", "gross lettable area"}:
        return "GLA"
    return "NLA"


def _canonical_number(value: str) -> str:
    number = value.replace(",", "")
    return number.rstrip("0").rstrip(".") if "." in number else number


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


def _normalize_comparison(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _conflict_anchor(value: str) -> str:
    unit = _UNIT_RE.search(value)
    if unit:
        return _normalize_comparison(f"Unit {unit.group(1)}")
    number = re.search(r"\d[\d,]*(?:\.\d+)?", value)
    if number:
        return _normalize_comparison(number.group(0))
    return _normalize_comparison(value)

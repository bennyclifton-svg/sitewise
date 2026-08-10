"""Deterministic cross-section checks for concurrently generated narrative."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, replace
from datetime import date
from itertools import combinations
import re
import unicodedata

from app.projects.generation_brief import (
    ArtefactGenerationBrief,
    verify_generation_brief_integrity,
)


@dataclass(frozen=True, slots=True)
class ConsistencySection:
    """One generated section and its homogeneous scope or risk collections."""

    key: str
    text: tuple[str, ...] = ()
    scope_items: tuple[str, ...] = ()
    risk_items: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConsistencyIssue:
    code: str
    section_keys: tuple[str, ...]
    message: str


@dataclass(frozen=True, slots=True)
class SemanticCandidate:
    id: str
    kind: str
    section_keys: tuple[str, ...]
    excerpts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConsistencyReport:
    deterministic_issues: tuple[ConsistencyIssue, ...] = ()
    semantic_candidates: tuple[SemanticCandidate, ...] = ()
    semantic_conflicts: tuple[str, ...] = ()
    ai_call_count: int = 0

    @property
    def is_consistent(self) -> bool:
        candidates_resolved = not self.semantic_candidates or self.ai_call_count == 1
        return (
            not self.deterministic_issues
            and not self.semantic_conflicts
            and candidates_resolved
        )


ConsistencyResolver = Callable[
    [ArtefactGenerationBrief, tuple[SemanticCandidate, ...]],
    Awaitable[set[str] | Sequence[str]],
]

_PROJECT_CLAIM = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*)?project(?:\s+name)?(?:\*\*)?\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)
_PROJECT_PROSE_CLAIM = re.compile(
    r"\bproject(?:\s+name)?\s+(?:is|called|named)\s+['\"]?([^.;\n]+?)"
    r"['\"]?(?=[.;]|$)",
    re.IGNORECASE,
)
_CONSULTANT_CLAIM = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*)?consultant(?:\s+(?:discipline|name))?"
    r"(?:\*\*)?\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)
_CONSULTANT_PROSE_CLAIM = re.compile(
    r"\bconsultant(?:\s+(?:discipline|name))?\s+"
    r"(?:is|will be|is to be)\s+['\"]?([^.;\n]+?)['\"]?(?=[.;]|$)",
    re.IGNORECASE,
)
_PROCUREMENT_CLAIM = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*)?procurement(?:\s+(?:route|model|basis))?"
    r"(?:\*\*)?\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)
_PROCUREMENT_ALIASES: dict[str, tuple[str, ...]] = {
    "traditional": ("traditional lump sum", "traditional", "lump sum"),
    "design_construct": (
        "design and construct",
        "design construct",
        "d and c",
        "d c",
    ),
    "construction_management": ("construction management",),
    "managing_contractor": ("managing contractor",),
}
_PROCUREMENT_PROSE_ALIASES: dict[str, tuple[str, ...]] = {
    "traditional": ("traditional procurement", "traditional delivery"),
    "design_construct": (
        "design and construct",
        "design construct",
        "d and c",
        "d c",
    ),
    "construction_management": ("construction management",),
    "managing_contractor": ("managing contractor",),
}
_ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_DUE_DATE = re.compile(
    r"\b(?:by|due(?:\s+date)?(?:\s*(?:is|:))?)\s+(\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)
_EXPLICIT_MILESTONE_DATE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*)?(?P<label>[a-z][a-z0-9 /&-]{1,80}?)"
    r"(?:\*\*)?\s*:\s*(?P<date>\d{4}-\d{2}-\d{2})\s*[.]?\s*$",
    re.IGNORECASE,
)
_DUPLICATE_STOP_WORDS = frozenset(
    {"a", "an", "and", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}
)
MAX_SEMANTIC_CANDIDATES = 12


def check_generation_consistency(
    brief: ArtefactGenerationBrief,
    sections: Sequence[ConsistencySection],
    *,
    run_date: date | None = None,
) -> ConsistencyReport:
    """Return deterministic conflicts and bounded semantic candidates."""
    verify_generation_brief_integrity(brief)
    issues: list[ConsistencyIssue] = []
    project_name = _known_context_value(brief, "identity", "title")
    if isinstance(project_name, str) and project_name.strip():
        expected = _normalize_claim(project_name)
        for section in sections:
            for line in section.text:
                match = _PROJECT_CLAIM.match(line)
                claim = (
                    match.group(1)
                    if match is not None
                    else _matched_claim(_PROJECT_PROSE_CLAIM, line)
                )
                if claim is not None and _normalize_claim(claim) != expected:
                    issues.append(
                        ConsistencyIssue(
                            code="project_name_conflict",
                            section_keys=(section.key,),
                            message=(
                                f"Section {section.key!r} labels the project as "
                                f"{claim.strip()!r}; expected {project_name!r}."
                            ),
                        )
                    )
    consultants = _canonical_consultants(brief)
    if consultants:
        expected_consultants = {_normalize_claim(value) for value in consultants}
        for section in sections:
            for line in section.text:
                match = _CONSULTANT_CLAIM.match(line)
                claim = (
                    match.group(1)
                    if match is not None
                    else _matched_claim(_CONSULTANT_PROSE_CLAIM, line)
                )
                if (
                    claim is not None
                    and _normalize_claim(claim) not in expected_consultants
                ):
                    issues.append(
                        ConsistencyIssue(
                            code="consultant_name_conflict",
                            section_keys=(section.key,),
                            message=(
                                f"Section {section.key!r} labels the consultant as "
                                f"{claim.strip()!r}; expected one of "
                                f"{', '.join(consultants)}."
                            ),
                        )
                    )
    procurement_route = _known_context_value(
        brief, "procurement", "procurement_route"
    ) or _known_context_value(brief, "commercial", "procurement_route")
    if isinstance(procurement_route, str) and procurement_route.strip():
        expected_groups = _procurement_groups(procurement_route)
        expected_value = _normalize_claim(procurement_route)
        for section in sections:
            for line in section.text:
                match = _PROCUREMENT_CLAIM.match(line)
                claim = match.group(1).strip() if match is not None else None
                claim_groups = (
                    _procurement_groups(claim)
                    if claim is not None
                    else _procurement_groups_in_prose(line)
                )
                if not claim_groups:
                    continue
                agrees = (
                    bool(expected_groups)
                    and claim_groups == expected_groups
                    or not expected_groups
                    and _normalize_claim(claim) == expected_value
                )
                if not agrees:
                    issues.append(
                        ConsistencyIssue(
                            code="procurement_terminology_conflict",
                            section_keys=(section.key,),
                            message=(
                                f"Section {section.key!r} labels the procurement route as "
                                f"{(claim or line).strip()!r}; expected {procurement_route!r}."
                            ),
                        )
                    )
    for section in sections:
        for value in _section_values(section):
            for token in _ISO_DATE.findall(value):
                try:
                    date.fromisoformat(token)
                except ValueError:
                    issues.append(
                        ConsistencyIssue(
                            code="invalid_date",
                            section_keys=(section.key,),
                            message=(
                                f"Section {section.key!r} contains invalid ISO date "
                                f"{token!r}."
                            ),
                        )
                    )
            if run_date is not None:
                for token in _DUE_DATE.findall(value):
                    try:
                        due = date.fromisoformat(token)
                    except ValueError:
                        continue
                    if due < run_date:
                        issues.append(
                            ConsistencyIssue(
                                code="date_before_generation",
                                section_keys=(section.key,),
                                message=(
                                    f"Section {section.key!r} contains due date {token!r} "
                                    f"before generation date {run_date.isoformat()}."
                                ),
                            )
                        )
    milestone_claims: dict[str, tuple[date, str]] = {
        key: (value, "shared generation brief")
        for key, value in _brief_milestone_dates(brief).items()
    }
    for section in sections:
        for value in _section_values(section):
            claim = _milestone_date_claim(value)
            if claim is None:
                continue
            milestone, claimed_date = claim
            previous = milestone_claims.get(milestone)
            if previous is not None and previous[0] != claimed_date:
                issues.append(
                    ConsistencyIssue(
                        code="milestone_date_conflict",
                        section_keys=(previous[1], section.key),
                        message=(
                            f"Milestone {milestone!r} is dated {previous[0].isoformat()} "
                            f"in section {previous[1]!r} and {claimed_date.isoformat()} "
                            f"in section {section.key!r}."
                        ),
                    )
                )
                continue
            milestone_claims[milestone] = (claimed_date, section.key)
    issues.extend(
        _exact_duplicate_issues(sections, attribute="scope_items", kind="scope")
    )
    issues.extend(
        _exact_duplicate_issues(sections, attribute="risk_items", kind="risk")
    )
    semantic_candidates: list[SemanticCandidate] = []
    for attribute, kind in (("scope_items", "scope"), ("risk_items", "risk")):
        near_issues, near_candidates = _near_duplicate_results(
            sections,
            attribute=attribute,
            kind=kind,
            candidate_limit=MAX_SEMANTIC_CANDIDATES - len(semantic_candidates),
        )
        issues.extend(near_issues)
        semantic_candidates.extend(near_candidates)
    return ConsistencyReport(
        deterministic_issues=tuple(issues),
        semantic_candidates=tuple(semantic_candidates),
    )


async def run_generation_consistency_gate(
    brief: ArtefactGenerationBrief,
    sections: Sequence[ConsistencySection],
    *,
    run_date: date | None = None,
    resolver: ConsistencyResolver | None = None,
) -> ConsistencyReport:
    """Check combined sections and resolve only genuinely ambiguous candidates."""
    report = check_generation_consistency(brief, sections, run_date=run_date)
    if (
        report.deterministic_issues
        or not report.semantic_candidates
        or resolver is None
    ):
        return report
    resolved = set(await resolver(brief, report.semantic_candidates))
    conflicts = tuple(
        candidate.id
        for candidate in report.semantic_candidates
        if candidate.id in resolved
    )
    return replace(report, semantic_conflicts=conflicts, ai_call_count=1)


def format_consistency_failures(report: ConsistencyReport) -> str:
    """Format only blocking conflicts for an existing workflow validation error."""
    messages = [issue.message for issue in report.deterministic_issues]
    conflict_ids = set(report.semantic_conflicts)
    for candidate in report.semantic_candidates:
        if candidate.id not in conflict_ids:
            continue
        messages.append(
            "AI consistency review confirmed "
            f"{candidate.kind.replace('_', ' ')} between sections "
            f"{', '.join(candidate.section_keys)}: " + " <> ".join(candidate.excerpts)
        )
    if not messages and report.semantic_candidates and report.ai_call_count == 0:
        messages.append("Semantic consistency candidates were not resolved.")
    return "; ".join(messages)


def _known_context_value(
    brief: ArtefactGenerationBrief,
    group_name: str,
    field_name: str,
) -> object | None:
    group = getattr(brief.context, group_name, None)
    if not isinstance(group, dict):
        return None
    field = group.get(field_name)
    if field is None:
        return None
    state = getattr(field, "state", None)
    if getattr(state, "value", state) != "known":
        return None
    return getattr(field, "value", None)


def _normalize_claim(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().replace("&", " and ")
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


def _matched_claim(pattern: re.Pattern[str], value: str) -> str | None:
    match = pattern.search(value)
    return match.group(1).strip(" \t'\"") if match is not None else None


def _canonical_consultants(brief: ArtefactGenerationBrief) -> tuple[str, ...]:
    values: list[str] = []
    discipline = getattr(brief.context, "discipline", None)
    if isinstance(discipline, str) and discipline.strip():
        values.append(discipline.strip())
    configured = _known_context_value(brief, "stakeholders", "consultants")
    if isinstance(configured, str) and configured.strip():
        values.append(configured.strip())
    elif isinstance(configured, (list, tuple)):
        values.extend(
            item.strip()
            for item in configured
            if isinstance(item, str) and item.strip()
        )
    return tuple(dict.fromkeys(values))


def _procurement_groups(value: str) -> frozenset[str]:
    normalized = f" {_normalize_claim(value)} "
    return frozenset(
        group
        for group, aliases in _PROCUREMENT_ALIASES.items()
        if any(f" {alias} " in normalized for alias in aliases)
    )


def _procurement_groups_in_prose(value: str) -> frozenset[str]:
    normalized = f" {_normalize_claim(value)} "
    return frozenset(
        group
        for group, aliases in _PROCUREMENT_PROSE_ALIASES.items()
        if any(f" {alias} " in normalized for alias in aliases)
    )


def _section_values(section: ConsistencySection) -> tuple[str, ...]:
    return (*section.text, *section.scope_items, *section.risk_items)


def _milestone_date_claim(value: str) -> tuple[str, date] | None:
    match = _EXPLICIT_MILESTONE_DATE.match(value)
    if match is None:
        return None
    milestone = _milestone_key(match.group("label"))
    if milestone is None:
        return None
    try:
        claimed_date = date.fromisoformat(match.group("date"))
    except ValueError:
        return None
    return milestone, claimed_date


def _milestone_key(label: str) -> str | None:
    normalized = _normalize_claim(label)
    normalized = re.sub(r"\s+(?:date|target)$", "", normalized)
    if "da lodgement" in normalized:
        return "da_lodgement"
    if "cdc lodgement" in normalized:
        return "cdc_lodgement"
    if any(
        term in normalized
        for term in ("tender close", "rfp close", "rft close", "rfq close")
    ):
        return "tender_close"
    if "response" in normalized and any(
        term in normalized for term in ("due", "close", "date")
    ):
        return "response_due"
    if "construction start" in normalized:
        return "construction_start"
    if "practical completion" in normalized:
        return "practical_completion"
    return None


def _brief_milestone_dates(
    brief: ArtefactGenerationBrief,
) -> dict[str, date]:
    programme = getattr(brief.context, "programme", None)
    if not isinstance(programme, dict):
        return {}
    dates: dict[str, date] = {}
    for key, field in programme.items():
        state = getattr(field, "state", None)
        if getattr(state, "value", state) != "known":
            continue
        value = getattr(field, "value", None)
        milestone = _milestone_key(
            f"{key} {getattr(field, 'label', '')} {value if isinstance(value, str) else ''}"
        )
        if milestone is None:
            continue
        if isinstance(value, date):
            dates[milestone] = value
            continue
        if isinstance(value, str):
            match = _ISO_DATE.search(value)
            if match is not None:
                try:
                    dates[milestone] = date.fromisoformat(match.group(0))
                except ValueError:
                    continue
    return dates


def _exact_duplicate_issues(
    sections: Sequence[ConsistencySection],
    *,
    attribute: str,
    kind: str,
) -> list[ConsistencyIssue]:
    issues: list[ConsistencyIssue] = []
    seen: dict[tuple[str, ...], tuple[str, str]] = {}
    for section in sections:
        for item in getattr(section, attribute):
            tokens = _content_tokens(item)
            if not tokens:
                continue
            previous = seen.get(tokens)
            if previous is None:
                seen[tokens] = (section.key, item)
                continue
            issues.append(
                ConsistencyIssue(
                    code=f"duplicate_{kind}",
                    section_keys=(previous[0], section.key),
                    message=(
                        f"Sections {previous[0]!r} and {section.key!r} contain duplicate "
                        f"{kind} items: {previous[1]!r} and {item!r}."
                    ),
                )
            )
    return issues


def _content_tokens(value: str) -> tuple[str, ...]:
    without_citations = re.sub(r"\[\d+\]", " ", value)
    without_marker = re.sub(r"^\s*(?:[-*]\s+|\d+[.)]\s*)", "", without_citations)
    return tuple(
        re.findall(
            r"[a-z0-9]+", unicodedata.normalize("NFKC", without_marker).casefold()
        )
    )


def _near_duplicate_results(
    sections: Sequence[ConsistencySection],
    *,
    attribute: str,
    kind: str,
    candidate_limit: int,
) -> tuple[list[ConsistencyIssue], list[SemanticCandidate]]:
    records = [
        (section_index, item_index, section.key, item, _content_tokens(item))
        for section_index, section in enumerate(sections)
        for item_index, item in enumerate(getattr(section, attribute))
    ]
    issues: list[ConsistencyIssue] = []
    candidates: list[SemanticCandidate] = []
    for left, right in combinations(records, 2):
        if not left[4] or left[4] == right[4]:
            continue
        left_tokens = set(left[4]) - _DUPLICATE_STOP_WORDS
        right_tokens = set(right[4]) - _DUPLICATE_STOP_WORDS
        union = left_tokens | right_tokens
        if len(union) < 5:
            continue
        similarity = len(left_tokens & right_tokens) / len(union)
        if similarity < 0.65:
            continue
        if similarity >= 0.9:
            issues.append(
                ConsistencyIssue(
                    code=f"duplicate_{kind}",
                    section_keys=(left[2], right[2]),
                    message=(
                        f"Sections {left[2]!r} and {right[2]!r} contain near-duplicate "
                        f"{kind} items: {left[3]!r} and {right[3]!r}."
                    ),
                )
            )
            continue
        if len(candidates) < candidate_limit:
            candidates.append(
                SemanticCandidate(
                    id=f"{kind}:{left[0]}:{left[1]}:{right[0]}:{right[1]}",
                    kind=f"possible_duplicate_{kind}",
                    section_keys=(left[2], right[2]),
                    excerpts=(left[3], right[3]),
                )
            )
    return issues, candidates


__all__ = [
    "ConsistencyIssue",
    "ConsistencyReport",
    "ConsistencyResolver",
    "ConsistencySection",
    "SemanticCandidate",
    "check_generation_consistency",
    "format_consistency_failures",
    "run_generation_consistency_gate",
]

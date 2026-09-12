from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

PROFILE_MUTATION_SCOPE = "profile_mutation"
PROCUREMENT_STRATEGY_MUTATION_SCOPE = "procurement_strategy_mutation"
PROFILE_ENRICHMENT_REASON = "profile_enrichment_authority"
PROFILE_SETUP_REASON = "profile_setup_from_brief"
PROFILE_SCOPE_POPULATE_REASON = "profile_scope_populate"

_DIRECT_IMPERATIVE = re.compile(r"\b(?:set(?!\s+up)|change|make)\b", re.IGNORECASE)
_SAVE_IMPERATIVE = re.compile(r"\b(?:update|save)\b", re.IGNORECASE)
_PROFILE_CONTEXT = re.compile(
    r"\b(?:profile|classification|project setup|project (?:to|as)|scale)\b",
    re.IGNORECASE,
)
_EVIDENCE_ASSERTION = re.compile(
    r"\b(?:report|document|drawing|email|quote|proposal|assessment)\b.{0,30}"
    r"\b(?:says?|states?|notes?|indicates?|suggests?|shows?)\b",
    re.IGNORECASE,
)
_HEDGE = re.compile(r"\b(?:may|might|possibly|probably|appears? to|could be)\b", re.IGNORECASE)
_PROFILE_PROPOSAL_CONFIRMATION = re.compile(
    r"\b(?:confirm|accept|approve)\b", re.IGNORECASE
)
_PROFILE_ENRICHMENT_VERBS = (
    "update",
    "complete",
    "fill",
    "populate",
    "enrich",
    "check",
    "review",
    "correct",
    "fix",
    "audit",
)
_PROFILE_SETUP_REQUEST = re.compile(
    r"^(?:(?:please|can you|could you|would you)\s+)*"
    r"(?:set\s+up|setup|establish)\b.*\bprofile\b",
    re.IGNORECASE,
)
_SCOPE_POPULATE_RE = re.compile(
    r"("
    r"\b(?:populate|fill|tick|check|select|set)\b.{0,60}\b"
    r"(?:scope\s+items?|work\s+scope|scope\s+checkboxes?)\b"
    r"|"
    r"\b(?:scope\s+items?|work\s+scope|scope\s+checkboxes?)\b.{0,60}\b"
    r"(?:populate|fill|tick|check|select)\b"
    r")",
    re.IGNORECASE | re.DOTALL,
)
_PROCUREMENT_STRATEGY_CONTEXT = re.compile(
    r"\b(?:procurement\s+strategy|tenderer(?:s)?|quote\s+candidate(?:s)?|"
    r"(?:procurement|tenderer)\s+(?:table|grid)|this\s+table)\b",
    re.IGNORECASE,
)
_PROCUREMENT_STRATEGY_WRITE = re.compile(
    r"\b(?:add|apply|clear|delete|fill|lock|move|populate|refresh|remove|save|"
    r"set|shortlist|unlock|update)\b",
    re.IGNORECASE,
)
_PROCUREMENT_CANDIDATE_RESEARCH = re.compile(
    r"\b(?:find|identify|look\s+up|research|source)\b",
    re.IGNORECASE,
)
_PROCUREMENT_CANDIDATE_PARTICIPANT = re.compile(
    r"\b(?:architects?|certifiers?|consultants?|contractors?|engineers?|firms?|"
    r"planners?|suppliers?|surveyors?|tenderers?|trades?)\b",
    re.IGNORECASE,
)

_BUILDING_CLASSES = {
    "residential": "residential",
    "commercial": "commercial",
    "industrial": "industrial",
    "institution": "institution",
    "mixed use": "mixed",
    "mixed-use": "mixed",
    "mixed": "mixed",
    "infrastructure": "infrastructure",
    "distribution centre": "industrial",
    "distribution center": "industrial",
    "warehouse": "industrial",
}
_WORK_TYPES = {
    "new build": "new",
    "new": "new",
    "refurbishment": "refurb",
    "refurbish": "refurb",
    "refurb": "refurb",
    "extension": "extend",
    "addition": "extend",
    "extend": "extend",
    "fit-out": "refurb",
    "fitout": "refurb",
    "fit out": "refurb",
    "remediation": "remediation",
    "rectification": "remediation",
    "advisory": "advisory",
    "technical due diligence": "advisory",
    "due diligence": "advisory",
    "before settlement": "advisory",
}
_STATES = {
    "new south wales": "NSW",
    "victoria": "VIC",
    "queensland": "QLD",
    "south australia": "SA",
    "western australia": "WA",
    "tasmania": "TAS",
    "northern territory": "NT",
    "australian capital territory": "ACT",
    "nsw": "NSW",
    "vic": "VIC",
    "qld": "QLD",
    "sa": "SA",
    "wa": "WA",
    "tas": "TAS",
    "nt": "NT",
    "act": "ACT",
}
_SUBCLASSES = {
    "townhouses": "townhouses",
    "townhouse": "townhouses",
    "apartments": "apartments",
    "apartment": "apartments",
    "house": "house",
    "class 1a": "house",
    "class1a": "house",
    "distribution centre": "logistics_ecommerce",
    "distribution center": "logistics_ecommerce",
    "logistics": "logistics_ecommerce",
    "warehouse": "warehouse",
    "office": "office",
}
_STOREY_WORDS = {
    "single": 1,
    "one": 1,
    "1": 1,
    "two": 2,
    "2": 2,
    "three": 3,
    "3": 3,
    "four": 4,
    "4": 4,
}
_STOREYS_RE = re.compile(
    r"\b("
    + "|".join(re.escape(word) for word in sorted(_STOREY_WORDS, key=len, reverse=True))
    + r")[\s-]*(?:storey|storeys|story|stories)\b",
    re.IGNORECASE,
)
_GFA_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(?:m(?:2|²)|sqm|m\^2)\b(?!\s*(?:site|lot))(?:\s*gfa)?"
    r"|\bgfa\b[^\d]{0,12}(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_SITE_AREA_RE = re.compile(
    r"\b(?:site(?:\s+area)?|lot)\b[^\d]{0,16}(\d+(?:\.\d+)?)"
    r"|"
    r"\b(\d+(?:\.\d+)?)\s*(?:m(?:2|²)|sqm|m\^2)\b\s*(?:site(?:\s+area)?|lot)\b",
    re.IGNORECASE,
)
_BEDROOMS_RE = re.compile(r"\b(\d+)\s*(?:bedrooms?|beds?)\b", re.IGNORECASE)
_DOCK_RE = re.compile(
    r"\b(\d+)\s*(?:loading\s+docks?|dock\s+doors?)\b"
    r"|\b(?:new\s+|own\s+new\s+)?loading\s+dock\b",
    re.IGNORECASE,
)
_GARAGE_COUNT_WORDS = {
    "single": 1,
    "double": 2,
    "triple": 3,
    "two": 2,
    "three": 3,
}
_GARAGE_RE = re.compile(
    r"\b(\d+)\s*(?:garage(?:/car)?\s*spaces?|garage\s*spaces?|car\s*spaces?|garages?)\b"
    r"|\b(?:no|zero)\s+garage\b"
    r"|\b(single|double|triple|two|three)[\s-]+garage\b",
    re.IGNORECASE,
)
_COMPLEXITY_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("planning", "da", re.compile(r"\b(?:planning\s+by\s+)?\bda\b|\bdevelopment\s+application\b", re.I)),
    ("planning", "cdc", re.compile(r"\bcdc\b|\bcomplying\s+development\b", re.I)),
    (
        "procurement_route",
        "design_construct",
        re.compile(
            r"\bdesign\s+(?:and|&)\s+construct\b|\bd\s*&\s*c\b|\bdesign\s+and\s+construct\b",
            re.I,
        ),
    ),
    ("contamination_level", "nil", re.compile(r"\bno\s+contamination\b|\bclean\s+site\b", re.I)),
    (
        "environmental_sensitivity",
        "standard",
        re.compile(r"\bno\s+environmental\s+constraints?\b", re.I),
    ),
    ("flood_exposure", "not_flood_prone", re.compile(r"\bno\s+flood(?:\s+exposure)?\b", re.I)),
    ("heritage_status", "none", re.compile(r"\bno\s+heritage\b", re.I)),
    (
        "bushfire_exposure",
        "not_bushfire_prone",
        re.compile(r"\bno\s+bush\s*-?\s*fires?\b", re.I),
    ),
    ("access_constraints", "unrestricted", re.compile(r"\bno\s+access\s+constraints?\b", re.I)),
)
_SITE_ADDRESS_RE = re.compile(
    r"\b(?:set|change|update|save)\b.{0,80}?\b(?:project\s+|site\s+)?address\b"
    r".{0,40}?\b(?:to|as)\s*:?\s*[\"'“‘]?(.+?)[\"'”’]?\s*$",
    re.IGNORECASE,
)
_CLIENT_RE = re.compile(
    r"\b(?:set|change|update|save)\b.{0,80}?\b(?:client|owners?|owner names?)\b"
    r".{0,40}?\b(?:to|as)\s*:?\s*[\"'“‘]?(.+?)[\"'”’]?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class MutationIntent:
    user_message_hash: str
    scopes: tuple[str, ...]
    profile_patch: Mapping[str, Any]
    requires_confirmation: bool
    reason: str

    def as_turn_payload(self) -> dict[str, Any]:
        return {
            "user_message_hash": self.user_message_hash,
            "scopes": list(self.scopes),
            "profile_patch": dict(self.profile_patch),
            "requires_confirmation": self.requires_confirmation,
            "reason": self.reason,
        }


def hash_user_message(user_text: str) -> str:
    return hashlib.sha256(user_text.encode("utf-8")).hexdigest()


def materialize_profile_patch(
    intent: MutationIntent,
    *,
    current_scale: Mapping[str, Any] | None = None,
) -> MutationIntent:
    """Merge partial scale updates onto the current profile scale for binding."""
    patch = dict(intent.profile_patch)
    requested_scale = patch.get("scale")
    if isinstance(requested_scale, Mapping):
        merged = dict(current_scale or {})
        merged.update(dict(requested_scale))
        patch["scale"] = merged
    return MutationIntent(
        user_message_hash=intent.user_message_hash,
        scopes=intent.scopes,
        profile_patch=MappingProxyType(patch),
        requires_confirmation=intent.requires_confirmation,
        reason=intent.reason,
    )


def is_profile_setup_text(user_text: str) -> bool:
    """True when the user asks to establish the Project Profile from a brief."""
    normalized = " ".join(user_text.lower().split())
    return bool(_PROFILE_SETUP_REQUEST.search(normalized))


def is_work_scope_populate_text(user_text: str) -> bool:
    """True when the user asks to tick Project Profile work-scope checkboxes."""
    return bool(_SCOPE_POPULATE_RE.search(user_text or ""))


def is_profile_enrichment_text(user_text: str) -> bool:
    """True when the user asks for a best-effort profile fill without exact values."""
    normalized = " ".join(user_text.lower().split())
    return "profile" in normalized and (
        bool(_PROFILE_SETUP_REQUEST.search(normalized))
        or any(
            re.search(rf"\b{verb}\b", normalized)
            for verb in _PROFILE_ENRICHMENT_VERBS
        )
    )


def classify_mutation_intent(user_text: str) -> MutationIntent:
    message_hash = hash_user_message(user_text)
    procurement_scope = _has_procurement_strategy_mutation(user_text)
    targets = _profile_targets(user_text)
    imperative = bool(_DIRECT_IMPERATIVE.search(user_text)) or bool(
        _SAVE_IMPERATIVE.search(user_text) and _PROFILE_CONTEXT.search(user_text)
    )
    evidence_assertion = bool(_EVIDENCE_ASSERTION.search(user_text))
    quoted_instruction = _is_quoted_instruction(user_text)
    hedged = bool(_HEDGE.search(user_text))
    clean_spoken = (
        not evidence_assertion and not quoted_instruction and not hedged
    )
    if is_work_scope_populate_text(user_text) and not quoted_instruction:
        scopes = [PROFILE_MUTATION_SCOPE]
        if procurement_scope:
            scopes.append(PROCUREMENT_STRATEGY_MUTATION_SCOPE)
        return MutationIntent(
            user_message_hash=message_hash,
            scopes=tuple(scopes),
            profile_patch=MappingProxyType({}),
            requires_confirmation=False,
            reason=PROFILE_SCOPE_POPULATE_REASON,
        )
    if is_profile_setup_text(user_text) and clean_spoken and targets:
        scopes = [PROFILE_MUTATION_SCOPE]
        if procurement_scope:
            scopes.append(PROCUREMENT_STRATEGY_MUTATION_SCOPE)
        return MutationIntent(
            user_message_hash=message_hash,
            scopes=tuple(scopes),
            profile_patch=MappingProxyType(targets),
            requires_confirmation=False,
            reason=PROFILE_SETUP_REASON,
        )
    explicit = imperative and bool(targets) and clean_spoken
    if explicit:
        scopes = [PROFILE_MUTATION_SCOPE]
        if procurement_scope:
            scopes.append(PROCUREMENT_STRATEGY_MUTATION_SCOPE)
        return MutationIntent(
            user_message_hash=message_hash,
            scopes=tuple(scopes),
            profile_patch=MappingProxyType(targets),
            requires_confirmation=False,
            reason="explicit_profile_imperative",
        )
    if is_profile_enrichment_text(user_text) and clean_spoken:
        scopes = [PROFILE_MUTATION_SCOPE]
        if procurement_scope:
            scopes.append(PROCUREMENT_STRATEGY_MUTATION_SCOPE)
        return MutationIntent(
            user_message_hash=message_hash,
            scopes=tuple(scopes),
            profile_patch=MappingProxyType({}),
            requires_confirmation=False,
            reason=PROFILE_ENRICHMENT_REASON,
        )
    requires_confirmation = bool(targets) and (evidence_assertion or hedged or imperative)
    reason = (
        "evidence_or_quoted_profile_claim"
        if evidence_assertion or quoted_instruction
        else "ambiguous_profile_request" if requires_confirmation else "no_profile_mutation"
    )
    return MutationIntent(
        user_message_hash=message_hash,
        scopes=(PROCUREMENT_STRATEGY_MUTATION_SCOPE,) if procurement_scope else (),
        profile_patch=MappingProxyType(targets),
        requires_confirmation=requires_confirmation,
        reason=("explicit_procurement_strategy_imperative" if procurement_scope else reason),
    )


def _has_procurement_strategy_mutation(user_text: str) -> bool:
    if _is_quoted_instruction(user_text) or _EVIDENCE_ASSERTION.search(user_text):
        return False
    table_write = bool(
        _PROCUREMENT_STRATEGY_CONTEXT.search(user_text)
        and _PROCUREMENT_STRATEGY_WRITE.search(user_text)
    )
    researched_candidate_write = bool(
        _PROCUREMENT_CANDIDATE_RESEARCH.search(user_text)
        and _PROCUREMENT_CANDIDATE_PARTICIPANT.search(user_text)
        and _PROCUREMENT_STRATEGY_WRITE.search(user_text)
    )
    return table_write or researched_candidate_write


def is_profile_proposal_confirmation(user_text: str) -> bool:
    """Return whether the user explicitly confirms a profile proposal."""
    normalized = " ".join(user_text.lower().split())
    if not _PROFILE_PROPOSAL_CONFIRMATION.search(normalized):
        return False
    return any(
        phrase in normalized
        for phrase in ("profile", "site address", "client", "owner")
    )


def _profile_targets(text: str) -> dict[str, Any]:
    address = _match_site_address(text)
    client = _match_client(text)
    working = text
    if address:
        working = working.replace(address, " ")
    if client:
        working = working.replace(client, " ")
    lowered = " ".join(working.lower().replace("_", " ").split())
    targets: dict[str, Any] = {}
    _match_alias(targets, "building_class", lowered, _BUILDING_CLASSES)
    _match_alias(targets, "work_type", lowered, _WORK_TYPES)
    _match_alias(targets, "state", lowered, _STATES)
    subclass = _match_subclass(lowered)
    if subclass is not None:
        targets["subclasses"] = [subclass]
    scale = _match_scale(lowered)
    if scale:
        targets["scale"] = scale
    complexity = _match_complexity(working)
    if complexity:
        targets["complexity"] = complexity
    if address is not None:
        targets["site_address"] = address
    if client is not None:
        targets["client"] = client
    narrative = _match_scope_narrative(lowered, subclasses=targets.get("subclasses"))
    if narrative:
        targets["scope_narrative"] = narrative
    return targets


_SCOPE_NARRATIVE_CUES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bunique\s+tenancy\b", re.I), "Unique tenancy"),
    (re.compile(r"\bits\s+it\b|\bown\s+(?:it|ict)\b|\bict\b", re.I), "Own IT fit-out"),
    (re.compile(r"\bloading\s+dock\b", re.I), "New loading dock"),
    (re.compile(r"\bmezzanine\b", re.I), "Mezzanine"),
    (re.compile(r"\bamenities\b", re.I), "Amenities"),
)


def _match_scope_narrative(
    text: str,
    *,
    subclasses: list[str] | None,
) -> list[str]:
    """Bespoke leftover lines that checkboxes and scale cannot hold."""
    lines: list[str] = []
    for pattern, line in _SCOPE_NARRATIVE_CUES:
        if pattern.search(text):
            lines.append(line)
    if (
        re.search(r"\boffice\b", text)
        and subclasses != ["office"]
        and "New office" not in lines
    ):
        lines.append("New office")
    return lines


def _match_site_address(text: str) -> str | None:
    match = _SITE_ADDRESS_RE.search(" ".join(text.strip().split()))
    if not match:
        return None
    value = match.group(1).strip(" .")
    return value or None


def _match_client(text: str) -> str | None:
    match = _CLIENT_RE.search(" ".join(text.strip().split()))
    if not match:
        return None
    value = match.group(1).strip(" .")
    return value or None


def _match_alias(
    targets: dict[str, Any],
    field: str,
    text: str,
    aliases: dict[str, str],
) -> None:
    for alias in sorted(aliases, key=len, reverse=True):
        if re.search(rf"(?<![\w-]){re.escape(alias)}(?![\w-])", text):
            targets[field] = aliases[alias]
            return


def _match_subclass(text: str) -> str | None:
    if "warehouse" in text:
        return "warehouse"
    if "townhouse" in text:
        return "townhouses"
    if "apartment" in text:
        return "apartments"
    if (
        re.search(r"\bhouse\b", text)
        or re.search(r"\bclass\s*1a\b", text)
        or re.search(r"\bhome\b(?!\s+(?:office|studio|based))", text)
    ):
        return "house"
    for alias in sorted(_SUBCLASSES, key=len, reverse=True):
        if re.search(rf"(?<![\w-]){re.escape(alias)}(?![\w-])", text):
            return _SUBCLASSES[alias]
    return None


def _match_scale(text: str) -> dict[str, int]:
    scale: dict[str, int] = {}
    storeys = _STOREYS_RE.search(text)
    if storeys:
        scale["storeys"] = _STOREY_WORDS[storeys.group(1).lower()]
    gfa = _GFA_RE.search(text)
    if gfa:
        raw = gfa.group(1) or gfa.group(2)
        scale["gfa_sqm"] = int(float(raw))
    site = _SITE_AREA_RE.search(text)
    if site:
        raw = site.group(1) or site.group(2)
        scale["site_sqm"] = int(float(raw))
    bedrooms = _BEDROOMS_RE.search(text)
    if bedrooms:
        scale["bedrooms"] = int(bedrooms.group(1))
    garage = _GARAGE_RE.search(text)
    if garage:
        if garage.group(1) is not None:
            scale["garage_spaces"] = int(garage.group(1))
        elif garage.group(2) is not None:
            scale["garage_spaces"] = _GARAGE_COUNT_WORDS[garage.group(2).lower()]
        else:
            scale["garage_spaces"] = 0
    dock = _DOCK_RE.search(text)
    if dock:
        scale["dock_doors"] = int(dock.group(1)) if dock.group(1) else 1
    return scale


def _match_complexity(text: str) -> dict[str, str]:
    complexity: dict[str, str] = {}
    for key, value, pattern in _COMPLEXITY_PATTERNS:
        if key in complexity:
            continue
        if pattern.search(text):
            complexity[key] = value
    return complexity


def _is_quoted_instruction(text: str) -> bool:
    stripped = text.strip()
    quote_pairs = (("\"", "\""), ("'", "'"), ("“", "”"), ("‘", "’"))
    return any(
        stripped.startswith(start)
        and stripped.endswith(end)
        and len(stripped) > len(start) + len(end)
        for start, end in quote_pairs
    )

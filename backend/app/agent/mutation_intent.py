from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

PROFILE_MUTATION_SCOPE = "profile_mutation"

_DIRECT_IMPERATIVE = re.compile(r"\b(?:set|change|make)\b", re.IGNORECASE)
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

_BUILDING_CLASSES = {
    "residential": "residential",
    "commercial": "commercial",
    "industrial": "industrial",
    "institution": "institution",
    "mixed use": "mixed",
    "mixed-use": "mixed",
    "mixed": "mixed",
    "infrastructure": "infrastructure",
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
    "remediation": "remediation",
    "rectification": "remediation",
    "advisory": "advisory",
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
_ROLES = {
    "owner builder": "owner-builder",
    "owner-builder": "owner-builder",
    "architect project manager": "architect-pm",
    "architect pm": "architect-pm",
    "architect/pm": "architect-pm",
    "architect-pm": "architect-pm",
    "design and construct": "d-and-c",
    "d&c": "d-and-c",
    "builder": "builder",
}
_SUBCLASSES = {
    "townhouses": "townhouses",
    "townhouse": "townhouses",
    "apartments": "apartments",
    "apartment": "apartments",
    "house": "house",
    "class 1a": "house",
    "class1a": "house",
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
    r"\b(\d+(?:\.\d+)?)\s*(?:m(?:2|²)|sqm|m\^2)\b(?:\s*gfa)?|\bgfa\b[^\d]{0,12}(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_BEDROOMS_RE = re.compile(r"\b(\d+)\s*(?:bedrooms?|beds?)\b", re.IGNORECASE)
_GARAGE_RE = re.compile(
    r"\b(\d+)\s*(?:garage(?:/car)?\s*spaces?|garage\s*spaces?|car\s*spaces?|garages?)\b"
    r"|\b(?:no|zero)\s+garage\b",
    re.IGNORECASE,
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


def classify_mutation_intent(user_text: str) -> MutationIntent:
    message_hash = hash_user_message(user_text)
    targets = _profile_targets(user_text)
    imperative = bool(_DIRECT_IMPERATIVE.search(user_text)) or bool(
        _SAVE_IMPERATIVE.search(user_text) and _PROFILE_CONTEXT.search(user_text)
    )
    evidence_assertion = bool(_EVIDENCE_ASSERTION.search(user_text))
    quoted_instruction = _is_quoted_instruction(user_text)
    hedged = bool(_HEDGE.search(user_text))
    explicit = (
        imperative
        and bool(targets)
        and not evidence_assertion
        and not quoted_instruction
        and not hedged
    )
    if explicit:
        return MutationIntent(
            user_message_hash=message_hash,
            scopes=(PROFILE_MUTATION_SCOPE,),
            profile_patch=MappingProxyType(targets),
            requires_confirmation=False,
            reason="explicit_profile_imperative",
        )
    requires_confirmation = bool(targets) and (evidence_assertion or hedged or imperative)
    reason = (
        "evidence_or_quoted_profile_claim"
        if evidence_assertion or quoted_instruction
        else "ambiguous_profile_request" if requires_confirmation else "no_profile_mutation"
    )
    return MutationIntent(
        user_message_hash=message_hash,
        scopes=(),
        profile_patch=MappingProxyType(targets),
        requires_confirmation=requires_confirmation,
        reason=reason,
    )


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
    _match_alias(targets, "user_role", lowered, _ROLES)
    subclass = _match_subclass(lowered)
    if subclass is not None:
        targets["subclasses"] = [subclass]
    scale = _match_scale(lowered)
    if scale:
        targets["scale"] = scale
    if address is not None:
        targets["site_address"] = address
    if client is not None:
        targets["client"] = client
    return targets


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
    if "townhouse" in text:
        return "townhouses"
    if "apartment" in text:
        return "apartments"
    if re.search(r"\bhouse\b", text) or re.search(r"\bclass\s*1a\b", text):
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
    bedrooms = _BEDROOMS_RE.search(text)
    if bedrooms:
        scale["bedrooms"] = int(bedrooms.group(1))
    garage = _GARAGE_RE.search(text)
    if garage:
        if garage.group(1) is None:
            scale["garage_spaces"] = 0
        else:
            scale["garage_spaces"] = int(garage.group(1))
    return scale


def _is_quoted_instruction(text: str) -> bool:
    stripped = text.strip()
    quote_pairs = (("\"", "\""), ("'", "'"), ("“", "”"), ("‘", "’"))
    return any(
        stripped.startswith(start)
        and stripped.endswith(end)
        and len(stripped) > len(start) + len(end)
        for start, end in quote_pairs
    )

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
    r"\b(?:profile|classification|project setup|project (?:to|as))\b", re.IGNORECASE
)
_EVIDENCE_ASSERTION = re.compile(
    r"\b(?:report|document|drawing|email|quote|proposal|assessment)\b.{0,30}"
    r"\b(?:says?|states?|notes?|indicates?|suggests?|shows?)\b",
    re.IGNORECASE,
)
_HEDGE = re.compile(r"\b(?:may|might|possibly|probably|appears? to|could be)\b", re.IGNORECASE)

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
    "architect-pm": "architect-pm",
    "design and construct": "d-and-c",
    "d&c": "d-and-c",
    "builder": "builder",
}


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


def _profile_targets(text: str) -> dict[str, str]:
    lowered = " ".join(text.lower().replace("_", " ").split())
    targets: dict[str, str] = {}
    _match_alias(targets, "building_class", lowered, _BUILDING_CLASSES)
    _match_alias(targets, "work_type", lowered, _WORK_TYPES)
    _match_alias(targets, "state", lowered, _STATES)
    _match_alias(targets, "user_role", lowered, _ROLES)
    return targets


def _match_alias(
    targets: dict[str, str],
    field: str,
    text: str,
    aliases: dict[str, str],
) -> None:
    for alias in sorted(aliases, key=len, reverse=True):
        if re.search(rf"(?<![\w-]){re.escape(alias)}(?![\w-])", text):
            targets[field] = aliases[alias]
            return


def _is_quoted_instruction(text: str) -> bool:
    stripped = text.strip()
    quote_pairs = (("\"", "\""), ("'", "'"), ("“", "”"), ("‘", "’"))
    return any(
        stripped.startswith(start)
        and stripped.endswith(end)
        and len(stripped) > len(start) + len(end)
        for start, end in quote_pairs
    )

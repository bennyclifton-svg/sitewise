"""Deterministic confidence scoring for ingest-time identity bootstrap."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.projects.identity import identity_from_evidence_texts

IdentityField = Literal["site_address", "client"]
IdentityAction = Literal["auto_apply", "propose", "skip"]

AUTO_APPLY_THRESHOLD = 0.85
PROPOSE_THRESHOLD = 0.5

_STRONG_ADDRESS_PATTERNS = (
    re.compile(
        r"\*\*Project:\*\*\s*.+?[—-]\s*(\d+\s+.+?(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)"
        r"(?:\s+\d{4})?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"Re:[^\n]*?(\d+\s+.+?(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)(?:\s+\d{4})?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"proposed new dwelling at\s+(\d+\s+.+?(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)"
        r"(?:\s+\d{4})?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d+\s+[A-Za-z][\w\s\-']+?(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|"
        r"Place|Pl|Drive|Dr|Court|Ct|Parade|Pde|Way|Terrace|Tce)\b[^,\n]*,?\s*"
        r"[A-Za-z][\w\s\-']+?\s*(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)(?:\s+\d{4})?)",
        re.IGNORECASE,
    ),
)

_CLIENT_LINE_PATTERN = re.compile(
    r"(?:^\*\*Client:\*\*|^Client:)\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
_PREPARED_FOR_PATTERN = re.compile(
    r"(?:prepared for|for the owners?)\s+([A-Z][\w\s&'.-]{2,80})",
    re.IGNORECASE,
)
_TO_OWNERS_PATTERN = re.compile(r"^\*\*To:\*\*\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_AMBIGUOUS_CLIENT_PATTERN = re.compile(
    r"\bfor\b",
    re.IGNORECASE,
)
_COMPANY_HINT_PATTERN = re.compile(
    r"\b(?:pty|ltd|limited|architects?|consultants?|partners?|atelier|group)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class IdentityFieldDecision:
    field: IdentityField
    value: str | None
    confidence: float
    action: IdentityAction


def score_identity_from_text(text: str) -> list[IdentityFieldDecision]:
    cleaned = text.strip() if isinstance(text, str) else ""
    if not cleaned:
        return [
            IdentityFieldDecision("site_address", None, 0.0, "skip"),
            IdentityFieldDecision("client", None, 0.0, "skip"),
        ]
    extracted = identity_from_evidence_texts([cleaned])
    address = extracted.get("site_address")
    client = extracted.get("client")
    # Prefer explicit Client: line when extractors miss it.
    if not client:
        client_match = _CLIENT_LINE_PATTERN.search(cleaned)
        if client_match:
            client = " ".join(client_match.group(1).split())
    return [
        _decide_address(cleaned, address if isinstance(address, str) else None),
        _decide_client(cleaned, client if isinstance(client, str) else None),
    ]


def _decide_address(text: str, value: str | None) -> IdentityFieldDecision:
    if not value:
        return IdentityFieldDecision("site_address", None, 0.0, "skip")
    confidence = 0.6
    for pattern in _STRONG_ADDRESS_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        matched = " ".join(match.group(1).split())
        if _addresses_align(matched, value):
            confidence = 0.9
            break
    return IdentityFieldDecision(
        "site_address",
        value,
        confidence,
        _action_for(confidence),
    )


def _decide_client(text: str, value: str | None) -> IdentityFieldDecision:
    if not value:
        return IdentityFieldDecision("client", None, 0.0, "skip")
    if _is_ambiguous_client(value):
        return IdentityFieldDecision("client", value, 0.55, "propose")
    confidence = 0.55
    if _TO_OWNERS_PATTERN.search(text) or _PREPARED_FOR_PATTERN.search(text):
        confidence = 0.9
    else:
        client_match = _CLIENT_LINE_PATTERN.search(text)
        if client_match:
            matched = " ".join(client_match.group(1).split())
            if matched.lower() == value.lower() and not _is_ambiguous_client(matched):
                confidence = 0.9
            elif matched.lower() == value.lower():
                confidence = 0.55
    return IdentityFieldDecision(
        "client",
        value,
        confidence,
        _action_for(confidence),
    )


def _is_ambiguous_client(value: str) -> bool:
    if _AMBIGUOUS_CLIENT_PATTERN.search(value) and _COMPANY_HINT_PATTERN.search(value):
        return True
    if re.search(r"\bfor\b", value, re.IGNORECASE) and "," not in value:
        # "Atelier North for David & Emma Walsh"
        parts = re.split(r"\bfor\b", value, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
            return True
    return False


def _action_for(confidence: float) -> IdentityAction:
    if confidence >= AUTO_APPLY_THRESHOLD:
        return "auto_apply"
    if confidence >= PROPOSE_THRESHOLD:
        return "propose"
    return "skip"


def _addresses_align(left: str, right: str) -> bool:
    def tokens(value: str) -> set[str]:
        return {part.lower() for part in re.findall(r"[A-Za-z0-9]+", value)}

    left_tokens = tokens(left)
    right_tokens = tokens(right)
    if not left_tokens or not right_tokens:
        return False
    overlap = left_tokens & right_tokens
    return len(overlap) >= min(3, len(left_tokens), len(right_tokens))

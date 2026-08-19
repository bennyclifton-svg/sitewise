"""Deterministic email message categories and action candidates.

Message labels are interpretation metadata. They are never DocumentClass
values. No model fallback (Stage E).
"""

from __future__ import annotations

import re
from typing import Literal, get_args

from pydantic import BaseModel, Field

from app.email.models import ProjectEmail

MessageCategory = Literal[
    "action_required",
    "decision_required",
    "design_change",
    "rfi",
    "instruction",
    "programme_change",
    "document_transmittal",
    "approval",
    "invoice_notice",
    "fee_proposal",
    "tender_submission",
    "meeting",
    "information_only",
    "unknown",
]

EmailActionType = Literal[
    "reply_required",
    "decision_required",
    "commit_date",
    "cost_signal",
    "document_transmittal",
]

MESSAGE_CATEGORIES: frozenset[str] = frozenset(get_args(MessageCategory))
EMAIL_ACTION_TYPES: frozenset[str] = frozenset(get_args(EmailActionType))
EMAIL_BODY_DOCUMENT_CLASS = "correspondence"
ACTION_EXCERPT_MAX = 280

_CATEGORY_RULES: tuple[tuple[re.Pattern[str], MessageCategory], ...] = (
    (re.compile(r"\bRFI\b|request for information", re.I), "rfi"),
    (re.compile(r"\bsite instruction\b|\bSI\s*\d", re.I), "instruction"),
    (re.compile(r"\btransmittal\b|\bIFC\b", re.I), "document_transmittal"),
    (re.compile(r"\btax invoice\b|\binvoice no\.?\b|\binvoice number\b", re.I), "invoice_notice"),
    (re.compile(r"\bfee proposal\b|\bfee estimate\b", re.I), "fee_proposal"),
    (re.compile(r"\btender submission\b|\blump sum tender\b", re.I), "tender_submission"),
    (re.compile(r"\bdesign change\b|\brevised drawings?\b", re.I), "design_change"),
    (re.compile(r"\bextension of time\b|\bEOT\b|\bprogramme change\b", re.I), "programme_change"),
    (
        re.compile(
            r"\bnotice of determination\b|\bCDC (?:approved|issued)\b|"
            r"\bconstruction certificate\b",
            re.I,
        ),
        "approval",
    ),
    (re.compile(r"\bminutes\b|\bmeeting (?:notes|agenda)\b", re.I), "meeting"),
    (
        re.compile(r"\bplease decide\b|\bdecision required\b|\bfor your decision\b", re.I),
        "decision_required",
    ),
    (
        re.compile(r"\bplease advise\b|\bplease confirm\b|\baction required\b", re.I),
        "action_required",
    ),
    (re.compile(r"\bfor your information\b|\bFYI\b", re.I), "information_only"),
)

_INSTRUCTION_FALLBACK = re.compile(r"\binstruction\b", re.I)

_ACTION_RULES: tuple[tuple[EmailActionType, re.Pattern[str], float], ...] = (
    (
        "reply_required",
        re.compile(r"\bRFI\b|please advise|please confirm|action required", re.I),
        0.85,
    ),
    (
        "decision_required",
        re.compile(r"please decide|decision required|for your decision", re.I),
        0.85,
    ),
    (
        "commit_date",
        re.compile(
            r"\bwe will\b.{0,80}\b(?:monday|tuesday|wednesday|thursday|friday|"
            r"saturday|sunday|\d{1,2}\s+\w+)\b",
            re.I | re.S,
        ),
        0.80,
    ),
    (
        "cost_signal",
        re.compile(
            r"(?:variation|\bVO\b|additional cost).{0,40}\$[\d,]+|"
            r"\$[\d,]+.{0,40}(?:variation|\bVO\b|additional cost)",
            re.I | re.S,
        ),
        0.85,
    ),
    ("document_transmittal", re.compile(r"\btransmittal\b|\bIFC\b", re.I), 0.85),
)


class EmailActionCandidate(BaseModel):
    type: EmailActionType
    excerpt: str = Field(max_length=ACTION_EXCERPT_MAX)
    locator: str
    confidence: float


def classify_message_category(email: ProjectEmail) -> MessageCategory:
    """Closed 14-value label for the message. Never a source-document class."""
    blob = f"{email.subject}\n{email.body_text}"
    for pattern, category in _CATEGORY_RULES:
        if pattern.search(blob):
            return category
    if _INSTRUCTION_FALLBACK.search(blob):
        return "instruction"
    if (email.subject or "").strip() or (email.body_text or "").strip():
        return "information_only"
    return "unknown"


def detect_action_candidates(email: ProjectEmail) -> list[EmailActionCandidate]:
    """Quote raw body/subject. Do not rewrite. Do not mutate canonical rows."""
    found: list[EmailActionCandidate] = []
    seen: set[EmailActionType] = set()
    for source, text in (
        ("subject", email.subject or ""),
        ("body", email.body_text or ""),
    ):
        for action_type, pattern, confidence in _ACTION_RULES:
            if action_type in seen:
                continue
            match = pattern.search(text)
            if match is None:
                continue
            seen.add(action_type)
            found.append(
                EmailActionCandidate(
                    type=action_type,
                    excerpt=_excerpt(text, match.start(), match.end()),
                    locator=source if source == "subject" else f"body:{match.start()}",
                    confidence=confidence,
                )
            )
    return found


def _excerpt(text: str, start: int, end: int) -> str:
    window = 80
    lo = max(0, start - window)
    hi = min(len(text), end + window)
    snippet = " ".join(text[lo:hi].split())
    if len(snippet) <= ACTION_EXCERPT_MAX:
        return snippet
    return snippet[: ACTION_EXCERPT_MAX - 1].rstrip() + "…"

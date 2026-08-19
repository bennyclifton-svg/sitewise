"""Score email-to-project matches in Python. An LLM may not pick project_id."""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel

from app.email.models import ProjectEmail
from ingest.router import REVIEW_CONFIDENCE_MIN

MatchBasis = Literal["alias", "user", "thread", "domain", "subject", "contact", "default"]
MATCH_REVIEW_CONFIDENCE_MIN = REVIEW_CONFIDENCE_MIN

USER_CONFIDENCE = 1.0
ALIAS_CONFIDENCE = 1.0
THREAD_CONFIDENCE = 0.95
CONTACT_CONFIDENCE = 0.90
DOMAIN_CONFIDENCE = 0.85
SUBJECT_STRONG_CONFIDENCE = 0.90
SUBJECT_PHRASE_CONFIDENCE = 0.85
SUBJECT_MULTI_CONFIDENCE = 0.75
SUBJECT_WEAK_CONFIDENCE = 0.55
DEFAULT_CONFIDENCE = 0.0

_STOPWORDS = frozenset(
    {
        "re",
        "fw",
        "fwd",
        "the",
        "and",
        "for",
        "from",
        "with",
        "project",
        "nsw",
        "pty",
        "ltd",
        "limited",
        "australia",
        "street",
        "road",
        "avenue",
        "drive",
        "lane",
        "court",
        "place",
        "unit",
        "level",
        "hello",
        "hi",
        "update",
        "meeting",
        "notes",
        "lunch",
        "tomorrow",
    }
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_MIN_TOKEN_LEN = 4


class ProjectMatch(BaseModel):
    project_id: uuid.UUID | None
    confidence: float
    basis: MatchBasis


class ProjectMatchCandidate(BaseModel):
    project_id: uuid.UUID
    slug: str
    title: str
    code: str | None = None
    site_address: str | None = None
    client_name: str | None = None
    email_domains: tuple[str, ...] = ()
    stored_addresses: tuple[str, ...] = ()
    alias_hit: bool = False


def match_project(
    *,
    email: ProjectEmail,
    candidates: Sequence[ProjectMatchCandidate],
    prior_thread_project_id: uuid.UUID | None,
    user_override: ProjectMatch | None,
) -> ProjectMatch:
    """Priority: user > alias > thread > scored domain/subject/contact > default."""
    if user_override is not None:
        return ProjectMatch(
            project_id=user_override.project_id,
            confidence=USER_CONFIDENCE,
            basis="user",
        )
    alias_hit = next((c for c in candidates if c.alias_hit), None)
    if alias_hit is not None:
        return ProjectMatch(
            project_id=alias_hit.project_id,
            confidence=ALIAS_CONFIDENCE,
            basis="alias",
        )
    if prior_thread_project_id is not None:
        return ProjectMatch(
            project_id=prior_thread_project_id,
            confidence=THREAD_CONFIDENCE,
            basis="thread",
        )
    best: ProjectMatch | None = None
    for candidate in candidates:
        scored = _score_candidate(email, candidate)
        if scored is None:
            continue
        if best is None or _is_better(scored, best):
            best = scored
    if best is None:
        return ProjectMatch(
            project_id=None,
            confidence=DEFAULT_CONFIDENCE,
            basis="default",
        )
    return best


def _is_better(candidate: ProjectMatch, current: ProjectMatch) -> bool:
    if candidate.confidence > current.confidence:
        return True
    if candidate.confidence < current.confidence:
        return False
    rank = {"contact": 3, "domain": 2, "subject": 1}
    return rank.get(candidate.basis, 0) > rank.get(current.basis, 0)


def _score_candidate(
    email: ProjectEmail, candidate: ProjectMatchCandidate
) -> ProjectMatch | None:
    contact = _contact_match(email, candidate)
    domain = _domain_match(email, candidate)
    subject = _subject_match(email, candidate)
    scored = [item for item in (contact, domain, subject) if item is not None]
    if not scored:
        return None
    winner = scored[0]
    for item in scored[1:]:
        if _is_better(item, winner):
            winner = item
    return winner


def _contact_match(
    email: ProjectEmail, candidate: ProjectMatchCandidate
) -> ProjectMatch | None:
    sender = (email.from_address or "").strip().lower()
    if not sender:
        return None
    stored = {addr.strip().lower() for addr in candidate.stored_addresses if addr}
    if sender not in stored:
        return None
    return ProjectMatch(
        project_id=candidate.project_id,
        confidence=CONTACT_CONFIDENCE,
        basis="contact",
    )


def _domain_match(
    email: ProjectEmail, candidate: ProjectMatchCandidate
) -> ProjectMatch | None:
    sender_domain = _sender_domain(email.from_address)
    if sender_domain is None:
        return None
    stored = {
        domain.strip().lower().lstrip("@")
        for domain in candidate.email_domains
        if domain and domain.strip()
    }
    if sender_domain not in stored:
        return None
    return ProjectMatch(
        project_id=candidate.project_id,
        confidence=DOMAIN_CONFIDENCE,
        basis="domain",
    )


def _subject_match(
    email: ProjectEmail, candidate: ProjectMatchCandidate
) -> ProjectMatch | None:
    subject = email.subject or ""
    if candidate.code and _contains_phrase(subject, candidate.code):
        return ProjectMatch(
            project_id=candidate.project_id,
            confidence=SUBJECT_STRONG_CONFIDENCE,
            basis="subject",
        )
    if candidate.slug and _contains_phrase(subject, candidate.slug.replace("-", " ")):
        return ProjectMatch(
            project_id=candidate.project_id,
            confidence=SUBJECT_STRONG_CONFIDENCE,
            basis="subject",
        )
    if candidate.title and _contains_phrase(subject, candidate.title):
        return ProjectMatch(
            project_id=candidate.project_id,
            confidence=SUBJECT_PHRASE_CONFIDENCE,
            basis="subject",
        )
    subject_tokens = _tokens(subject)
    field_tokens = _tokens(
        " ".join(
            part
            for part in (candidate.title, candidate.site_address, candidate.client_name)
            if part
        )
    )
    overlap = subject_tokens & field_tokens
    if not overlap:
        return None
    if len(overlap) >= 2 or any(len(token) >= 8 for token in overlap):
        return ProjectMatch(
            project_id=candidate.project_id,
            confidence=SUBJECT_MULTI_CONFIDENCE,
            basis="subject",
        )
    return ProjectMatch(
        project_id=candidate.project_id,
        confidence=SUBJECT_WEAK_CONFIDENCE,
        basis="subject",
    )


def _sender_domain(address: str | None) -> str | None:
    if not address or "@" not in address:
        return None
    domain = address.rsplit("@", 1)[-1].strip().lower()
    return domain or None


def _contains_phrase(haystack: str, needle: str) -> bool:
    phrase = needle.strip()
    if len(phrase) < 3:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])"
    return re.search(pattern, haystack.lower()) is not None


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(text.lower())
        if token not in _STOPWORDS and len(token) >= _MIN_TOKEN_LEN
    }


def thread_key(email: ProjectEmail) -> str:
    """Group by provider thread id, else In-Reply-To / References / Message-ID."""
    if email.provider_thread_id:
        return f"provider:{email.provider}:{email.provider_thread_id}"
    in_reply_to = _header(email, "in-reply-to")
    if in_reply_to:
        return f"msgid:{_first_message_id(in_reply_to)}"
    references = _header(email, "references")
    if references:
        return f"msgid:{_first_message_id(references)}"
    if email.internet_message_id:
        return f"msgid:{_first_message_id(email.internet_message_id)}"
    return f"solo:{email.id}"


def _header(email: ProjectEmail, name: str) -> str | None:
    headers = email.headers if isinstance(email.headers, dict) else {}
    for key, value in headers.items():
        if key.lower() == name and isinstance(value, str) and value.strip():
            return value
    return None


def _first_message_id(raw: str) -> str:
    return raw.split()[0].strip()

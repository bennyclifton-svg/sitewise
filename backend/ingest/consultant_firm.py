"""Extract issuing consultant firms from certificate/cover-sheet text."""

from __future__ import annotations

import re

_CLIENT_NOISE = re.compile(
    r"(?i)\b(?:"
    r"joins?\s+win|j\s*&\s*cg\s+con|jw\s+building|client|owner|builder|"
    r"principal|contractor|for\s+construction|a\.?d\.?\s*envirotech|"
    r"chen\s+total|mckenzie\s+group"
    r")\b"
)

_PREFERRED_FIRMS = (
    "Fire Safety Studio Pty Ltd",
    "Acoustic Logic Pty Ltd",
    "Roda Architects Pty Ltd",
    "Vista Access Architects Pty Ltd",
    "TDL Engineering Consulting Pty Ltd",
    "Zait Engineering Solutions Pty Ltd",
    "Sulphurcrest Enterprises Pty Ltd",
)

_PHRASE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?is)(?:drawings?\s+issued\s+by|prepared\s+by|issued\s+by|"
        r"property\s+of|copyright(?:\s+are)?\s+the\s+property\s+of|"
        r"on\s+behalf\s+of)\s+"
        r"([A-Z][A-Za-z0-9&./' -]{2,80}?"
        r"(?:Pty\.?\s*Ltd\.?|Limited|Architects|Consulting(?:\s+Pty\.?\s*Ltd\.?)?))"
    ),
    re.compile(
        r"(?is)\b([A-Z][A-Za-z0-9&./' -]{2,80}?"
        r"(?:Pty\.?\s*Ltd\.?|Limited))\b"
    ),
)

_COPYRIGHT_UPPER = re.compile(
    r"(?is)(?:copyright|property)\s+(?:are\s+)?(?:the\s+)?property\s+of\s+"
    r"([A-Z0-9][A-Z0-9&./' -]{2,80}?(?:PTY\.?\s*LTD\.?|LIMITED))"
)


def _clean_firm(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" -:–—,;")
    cleaned = re.sub(r"(?i)^copyright\s+", "", cleaned).strip()
    cleaned = re.sub(r"\.+$", ".", cleaned) if cleaned.endswith("..") else cleaned
    # Title-case all-caps copyright lines without destroying Pty Ltd.
    if cleaned.isupper():
        parts: list[str] = []
        for token in cleaned.split(" "):
            upper = token.upper().rstrip(".")
            if upper == "PTY":
                parts.append("Pty.")
            elif upper == "LTD":
                parts.append("Ltd")
            elif upper in {"AND", "&"}:
                parts.append(token if token == "&" else "and")
            else:
                parts.append(token.title())
        cleaned = " ".join(parts)
    cleaned = re.sub(r"(?i)\bpty\.?\s*ltd\.?", "Pty Ltd", cleaned)
    cleaned = re.sub(r"(?i)\bconsulting$", "Consulting", cleaned)
    return cleaned.strip(" -:–—,;.")


_FIRM_NOISE_RE = re.compile(
    r"(?i)^(?:phone|tel|fax|email|www\.|http|mobile|abn|acn)\b|"
    r"\b(?:phone|tel|fax)\s*:|"
    r"\d{4}\s*\d{4}"
)


def _looks_like_client(firm: str) -> bool:
    return bool(_CLIENT_NOISE.search(firm))


def is_noise_firm_candidate(firm: str) -> bool:
    return bool(_FIRM_NOISE_RE.search(firm))


def extract_issuing_firm_from_text(text: str) -> str | None:
    """Return the best issuing-firm candidate from free text, or None."""
    if not text or not text.strip():
        return None

    # Prefer known project-consultant names when the full string is present.
    for preferred in _PREFERRED_FIRMS:
        if preferred.casefold() in text.casefold():
            return preferred

    scored: list[tuple[int, str]] = []
    for index, match in enumerate(_COPYRIGHT_UPPER.finditer(text)):
        firm = _clean_firm(match.group(1))
        if firm and not _looks_like_client(firm) and not is_noise_firm_candidate(firm):
            scored.append((0 + index, firm))

    for pattern_rank, pattern in enumerate(_PHRASE_PATTERNS):
        for index, match in enumerate(pattern.finditer(text)):
            firm = _clean_firm(match.group(1))
            if not firm or _looks_like_client(firm) or is_noise_firm_candidate(firm):
                continue
            # Prefer explicit phrasing ("issued by" / "property of") over bare Pty Ltd.
            score = (pattern_rank * 10) + index
            if "issued by" in match.group(0).lower() or "prepared by" in match.group(0).lower():
                score -= 5
            if "property of" in match.group(0).lower():
                score -= 4
            scored.append((score, firm))

    if not scored:
        return None
    scored.sort(key=lambda item: item[0])
    return scored[0][1]

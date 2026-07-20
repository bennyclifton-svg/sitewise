"""Deterministic per-page currency census. Invariant I1's measuring stick."""

from __future__ import annotations

import re
from dataclasses import dataclass

from tender.schemas import currency_to_cents

CURRENCY_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d{2})?)")
GROUPING_RE = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})?$")
CONTEXT_BLOCKLIST = re.compile(
    r"(ABN|ACN|Ph|Phone|Mobile|Fax|Lic|Reg)\s*:?\s*$", re.IGNORECASE
)


def despace_letter_spaced_text(text: str) -> str:
    """Collapse letter/digit spacing seen in some PDF text extractions."""
    out = text or ""
    out = re.sub(r"(?<=\d)\s+(?=[\d,.])", "", out)
    out = re.sub(r"(?<=[$,.])\s+(?=\d)", "", out)
    prev = None
    while prev != out:
        prev = out
        out = re.sub(
            r"(?<![A-Za-z0-9])([A-Za-z0-9])(?:\s+([A-Za-z0-9]))+(?![A-Za-z0-9])",
            lambda m: m.group(0).replace(" ", ""),
            out,
        )
    return out


@dataclass(frozen=True)
class CensusToken:
    page_no: int
    raw: str
    cents: int
    context: str
    suspect_format: bool


def census_page(text: str, page_no: int) -> list[CensusToken]:
    out: list[CensusToken] = []
    for match in CURRENCY_RE.finditer(text or ""):
        before = text[max(0, match.start() - 40) : match.start()]
        if CONTEXT_BLOCKLIST.search(before):
            continue
        digits = match.group(1)
        cents = currency_to_cents(digits)
        if cents is None:
            continue
        out.append(
            CensusToken(
                page_no=page_no,
                raw=match.group(0).strip(),
                cents=cents,
                context=text[max(0, match.start() - 40) : match.end() + 40],
                suspect_format=not GROUPING_RE.fullmatch(digits),
            )
        )
    return out

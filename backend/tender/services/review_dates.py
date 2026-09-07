"""Interpret printed dates in Python; never rely on model-generated date arithmetic."""

from __future__ import annotations

import re
from datetime import date

from tender.review_schemas import ReviewExtraction

_MONTHS = {
    name: index
    for index, name in enumerate(
        "jan feb mar apr may jun jul aug sep oct nov dec".split(), 1
    )
}
_DATES = re.compile(
    r"\b(?:(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})|(?P<day2>\d{1,2})[./-](?P<month2>\d{1,2})[./-](?P<year2>\d{4})|(?P<month3>[A-Za-z]{3,9})\s+(?P<day3>\d{1,2})(?:st|nd|rd|th)?[,]?\s+(?P<year3>\d{4})|(?P<day4>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month4>[A-Za-z]{3,9})[,]?\s+(?P<year4>\d{4}))\b"
)


def printed_dates(text: str) -> list[str]:
    dates = []
    for match in _DATES.finditer(text):
        for suffix in ("", "2", "3", "4"):
            if match[f"year{suffix}"]:
                month = match[f"month{suffix}"]
                month = (
                    int(month) if month.isdigit() else _MONTHS.get(month[:3].lower(), 0)
                )
                try:
                    dates.append(
                        date(
                            int(match[f"year{suffix}"]),
                            month,
                            int(match[f"day{suffix}"]),
                        ).isoformat()
                    )
                except ValueError:
                    pass
                break
    return list(dict.fromkeys(dates))


def normalize_source_dates(
    result: ReviewExtraction, pages: dict[int, str], opening_page: str
) -> None:
    opening_dates = printed_dates(opening_page)
    for fact in result.facts:
        source_dates = (
            printed_dates(pages.get(fact.page_no, ""))
            + printed_dates(fact.excerpt)
            + opening_dates
        )
        if fact.valid_until not in source_dates:
            fact.valid_until = None
        if fact.issued_on not in source_dates:
            fact.issued_on = (
                opening_dates[0]
                if len(opening_dates) == 1 and fact.kind == "validity"
                else None
            )
        if fact.validity_days:
            days = re.search(r"\b(\d+)\s+days?\b", fact.excerpt, re.IGNORECASE)
            fact.validity_days = int(days[1]) if days else None

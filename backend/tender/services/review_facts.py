"""Deterministic source validation, money parsing and commercial reconciliation."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from tender.review_schemas import ReviewExtraction, ReviewSelection
from tender.services.census import census_page

_MONEY = re.compile(r"(?P<sign>-?)(?P<value>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?)$")


def parse_printed_money(value: str | None) -> int | None:
    if value is None:
        return None
    text = value.strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    text = re.sub(r"\b(?:AUD|USD|NZD|GBP|EUR)\b|A\$|US\$|NZ\$|[$£€]", "", text).strip()
    match = _MONEY.fullmatch(text)
    if match is None:
        return None
    amount = Decimal(match["value"].replace(",", "")) * 100
    return int(amount) * (-1 if negative or match["sign"] else 1)


def _normal(value: str) -> str:
    return " ".join(value.split()).casefold()


def validate_extraction(
    result: ReviewExtraction, pages: dict[int, str], image_pages: set[int]
) -> None:
    covered = [page.page_no for page in result.coverage]
    if len(covered) != len(set(covered)) or set(covered) != set(pages):
        raise ValueError(
            f"Incomplete page coverage in extraction: expected original pages {sorted(pages)}, received {covered}"
        )
    if any(not page.readable for page in result.coverage):
        raise ValueError("A submission page is unreadable; upload a clearer copy")
    for fact in result.facts:
        if fact.page_no not in pages:
            raise ValueError("Extraction cited a page outside the document window")
        if fact.page_no not in image_pages and _normal(fact.excerpt) not in _normal(
            pages[fact.page_no]
        ):
            raise ValueError("Extraction excerpt does not match the cited source page")
        if fact.amount_printed and _normal(fact.amount_printed) not in _normal(
            fact.excerpt
        ):
            raise ValueError("Printed amount is missing from its source excerpt")
        if fact.valid_until:
            date.fromisoformat(fact.valid_until)
        if fact.issued_on:
            date.fromisoformat(fact.issued_on)


def missing_amounts(
    result: ReviewExtraction, pages: dict[int, str]
) -> list[dict[str, Any]]:
    captured = Counter(
        (fact.page_no, parse_printed_money(fact.amount_printed))
        for fact in result.facts
        if fact.amount_printed
    )
    unresolved = Counter(
        (fact.page_no, _normal(fact.amount_printed))
        for fact in result.facts
        if fact.amount_printed and parse_printed_money(fact.amount_printed) is None
    )
    missing = []
    for number, text in pages.items():
        for token in census_page(text, number):
            raw_key = (number, _normal(token.raw))
            if unresolved[raw_key]:
                unresolved[raw_key] -= 1
                continue
            key = (number, token.cents)
            if captured[key]:
                captured[key] -= 1
            else:
                missing.append(
                    {
                        "page_no": number,
                        "raw": token.raw,
                        "context": token.context,
                        "cents": token.cents,
                    }
                )
    return missing


def numbered_facts(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts = []
    for document_index, document in enumerate(documents, 1):
        for index, fact in enumerate(document["facts"]):
            value = dict(fact)
            value.update(
                id=f"f{document_index}:{index}",
                document_id=document["id"],
                quote_id=document["quote_id"],
                amount_cents=parse_printed_money(fact.get("amount_printed")),
            )
            if _normal(value["label"]) in {"gst", "tax", "tax (gst)"}:
                value["kind"] = "pricing_basis"
            if value["kind"] == "pricing_basis" and re.fullmatch(
                r"\d+(?:\.\d+)?%", (value.get("amount_printed") or "").strip()
            ):
                value["amount_printed"] = None
                value["amount_cents"] = None
            facts.append(value)
    return facts


def _inclusive(
    fact: dict[str, Any], facts: list[dict[str, Any]] | None = None
) -> int | None:
    amount = fact.get("amount_cents")
    if amount is None:
        return None
    if fact["tax_basis"] == "inc":
        return amount
    if fact["tax_basis"] == "ex" and fact["currency"] == "AUD":
        quoted_tax = [
            item["amount_cents"]
            for item in facts or []
            if fact.get("page_no") is not None
            and item["document_id"] == fact["document_id"]
            and item["page_no"] == fact["page_no"]
            and item["currency"] == fact["currency"]
            and _normal(item["label"]) in {"gst", "tax (gst)"}
            and _normal(item.get("parent_label") or "") == _normal(fact["label"])
            and item.get("amount_cents") is not None
        ]
        if len(quoted_tax) == 1:
            return amount + quoted_tax[0]
        return int(
            (Decimal(amount) * Decimal("1.1")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
    return None


def _declared_summary_spans(facts, totals):
    # Source wording can establish a summary even when the reader misses rollup flags.
    priced_pages = Counter(
        (fact["document_id"], fact["page_no"])
        for fact in facts
        if fact["kind"] == "component" and fact.get("amount_cents") is not None
    )
    starts = {}
    for fact in facts:
        if fact["kind"] != "pricing_basis":
            continue
        key = (fact["document_id"], fact["page_no"])
        if (
            re.search(r"\bcategory totals\b", fact.get("excerpt", ""), re.I)
            and priced_pages[key] >= 2
        ):
            starts.setdefault(key[0], set()).add(key[1])
    spans = {}
    for document_id, pages in starts.items():
        if len(pages) != 1:
            continue
        start = next(iter(pages))
        ends = [
            fact["page_no"]
            for fact in totals
            if fact["document_id"] == document_id and fact["page_no"] >= start
        ]
        if ends:
            spans[document_id] = (start, min(ends))
    return spans


def reconcile_submission(
    facts: list[dict[str, Any]], *, review_date: date
) -> dict[str, Any]:
    totals = [
        fact
        for fact in facts
        if fact["kind"] == "total" and fact.get("amount_cents") is not None
    ]
    # Different documents can repeat the same offer inclusive/exclusive of GST.
    # Conflicting offers stay visible; their amounts are never added together.
    currencies = {fact["currency"] for fact in totals}
    inclusive = [_inclusive(fact, facts) for fact in totals]
    if (
        totals
        and all(amount is not None for amount in inclusive)
        and len(currencies) == 1
    ):
        conflicting = max(inclusive) - min(inclusive) > 1
    else:
        conflicting = (
            len(
                {
                    (fact["amount_cents"], fact["tax_basis"], fact["currency"])
                    for fact in totals
                }
            )
            > 1
        )
    chosen = next(
        (fact for fact in totals if fact["tax_basis"] == "inc"),
        totals[0] if totals else None,
    )
    expired = []
    issued = next(
        (
            date.fromisoformat(fact["issued_on"])
            for fact in facts
            if fact.get("issued_on")
        ),
        None,
    )
    for fact in facts:
        expiry = (
            date.fromisoformat(fact["valid_until"]) if fact.get("valid_until") else None
        )
        if expiry is None and fact.get("validity_days") and issued:
            expiry = issued + timedelta(days=fact["validity_days"])
        if expiry and expiry < review_date:
            expired.append(fact["id"])
    malformed = [
        fact["id"]
        for fact in facts
        if fact.get("amount_printed") and fact.get("amount_cents") is None
    ]
    components = []
    seen = set()
    labels = {
        _normal(fact["label"])
        for fact in facts
        if fact["kind"] == "component" and fact.get("amount_cents") is not None
    }
    rollups = [
        fact
        for fact in facts
        if fact["kind"] == "component"
        and fact.get("is_rollup")
        and not fact.get("parent_label")
    ]
    component_source = facts
    spans = {}
    if len(rollups) > 1:
        # Summary schedules can continue onto the next page beside the closing
        # total. Include those last rows even when they have no detail to roll up.
        for fact in rollups:
            start, end = spans.get(
                fact["document_id"], (fact["page_no"], fact["page_no"])
            )
            spans[fact["document_id"]] = (
                min(start, fact["page_no"]),
                max(end, fact["page_no"]),
            )
        for fact in totals:
            if fact["document_id"] in spans:
                start, end = spans[fact["document_id"]]
                if fact["page_no"] == end + 1:
                    spans[fact["document_id"]] = (start, fact["page_no"])
    spans.update(_declared_summary_spans(facts, totals))
    if spans:
        component_source = [
            fact
            for fact in facts
            if fact["document_id"] not in spans
            or spans[fact["document_id"]][0]
            <= fact["page_no"]
            <= spans[fact["document_id"]][1]
        ]
    for fact in component_source:
        if fact["kind"] != "component" or fact.get("amount_cents") is None:
            continue
        if fact.get("parent_label") and _normal(fact["parent_label"]) in labels:
            continue
        key = (
            _normal(fact["label"]),
            fact["amount_cents"],
            fact["tax_basis"],
            fact["currency"],
        )
        if key not in seen:
            components.append(fact)
            seen.add(key)
    bases = {(fact["tax_basis"], fact["currency"]) for fact in components}
    component_sum = (
        sum(fact["amount_cents"] for fact in components) if len(bases) == 1 else None
    )
    residual = None
    uplift = None
    reconciliation_total = chosen["amount_cents"] if chosen else None
    if (
        chosen
        and chosen["tax_basis"] == "inc"
        and bases == {("ex", "AUD")}
        and chosen["currency"] == "AUD"
    ):
        matching_ex = next(
            (fact["amount_cents"] for fact in totals if fact["tax_basis"] == "ex"), None
        )
        reconciliation_total = (
            matching_ex
            if matching_ex is not None
            else int(
                (Decimal(chosen["amount_cents"]) / Decimal("1.1")).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
        )
    compatible = chosen and (
        bases == {(chosen["tax_basis"], chosen["currency"])}
        or (
            chosen["tax_basis"] == "inc"
            and chosen["currency"] == "AUD"
            and bases == {("ex", "AUD")}
        )
    )
    if component_sum and compatible and not conflicting:
        residual = reconciliation_total - component_sum
        if abs(residual) <= 1:
            residual = 0
        uplift = str(
            (Decimal(residual) / Decimal(component_sum) * 100).quantize(Decimal("0.01"))
        )
    return {
        "headline_cents": chosen["amount_cents"] if chosen else None,
        "headline_basis": chosen["tax_basis"] if chosen else "unknown",
        "currency": chosen["currency"] if chosen else "AUD",
        "headline_fact_ids": [fact["id"] for fact in totals],
        "conflicting_totals": conflicting,
        "expired_fact_ids": expired,
        "malformed_fact_ids": malformed,
        "component_sum_cents": component_sum,
        "component_fact_ids": [fact["id"] for fact in components],
        "residual_cents": residual,
        "apparent_uplift_percent": uplift,
        "reconciliation_total_cents": reconciliation_total,
    }


def validate_selection(
    selection: ReviewSelection,
    facts: list[dict[str, Any]],
    quote_ids: list[str],
    profile: str,
) -> None:
    by_id = {fact["id"]: fact for fact in facts}
    if len(quote_ids) == 1 and (
        selection.conclusion != "single_quote" or selection.preferred_quote_id
    ):
        raise ValueError("A single quote cannot receive a relative recommendation")
    if len(quote_ids) > 1 and selection.conclusion == "single_quote":
        raise ValueError("A comparison must account for every submitted firm")
    if selection.conclusion == "preferred_for_clarification":
        if (
            selection.preferred_quote_id not in quote_ids
            or not selection.recommendation_fact_ids
        ):
            raise ValueError(
                "Recommendation must identify a submitted firm and supporting facts"
            )
    elif selection.preferred_quote_id:
        raise ValueError("A clarification-only conclusion cannot name a preferred firm")
    referenced = list(selection.recommendation_fact_ids)
    referenced.extend(
        value for finding in selection.findings for value in finding.fact_ids
    )
    used = set()
    if (
        len(selection.matrix)
        > {"consultant": 5, "trade": 16, "head_contractor": 24}[profile]
    ):
        raise ValueError("Matrix exceeds this report profile")
    if not selection.matrix and any(
        fact["kind"] in {"component", "allowance", "rate"} for fact in facts
    ):
        raise ValueError(
            "Priced stages or work items must appear in the comparison matrix"
        )
    for row in selection.matrix:
        if [cell.quote_id for cell in row.cells] != quote_ids:
            raise ValueError("Every matrix row must cover the submitted firms in order")
        for cell in row.cells:
            selected = [by_id[value] for value in cell.fact_ids if value in by_id]
            labels = {_normal(fact["label"]) for fact in selected}
            if any(
                fact.get("parent_label")
                and _normal(fact["parent_label"]) in labels
                and fact.get("amount_cents") is not None
                for fact in selected
            ):
                raise ValueError(
                    f"Matrix row {row.label!r} mixes an enclosing price and its included components; use only the enclosing price"
                )
            for value in cell.fact_ids:
                if value in used:
                    raise ValueError(
                        f"Matrix fact {value} was counted twice; remove its repeated use in {row.label!r}"
                    )
                if value not in by_id or by_id[value]["quote_id"] != cell.quote_id:
                    raise ValueError(
                        "Matrix citation belongs to another firm or is unknown"
                    )
                if by_id[value]["kind"] == "total":
                    raise ValueError("Headline totals cannot be counted as work items")
                used.add(value)
                referenced.append(value)
    unknown = [value for value in referenced if value not in by_id]
    if unknown:
        raise ValueError(
            f"Review references unknown source facts {unknown[:6]}; copy the supplied fact IDs exactly"
        )
    if selection.preferred_quote_id and not any(
        by_id[value]["quote_id"] == selection.preferred_quote_id
        for value in selection.recommendation_fact_ids
    ):
        raise ValueError("Preferred firm has no supporting source evidence")


def remove_enclosed_prices(
    selection: ReviewSelection, facts: list[dict[str, Any]]
) -> None:
    """A selected enclosing price already contains explicitly parented prices."""
    by_id = {fact["id"]: fact for fact in facts}
    for row in selection.matrix:
        for cell in row.cells:
            selected = [by_id[value] for value in cell.fact_ids if value in by_id]
            prices = {
                _normal(fact["label"])
                for fact in selected
                if fact.get("amount_cents") is not None
                and fact["kind"] in {"component", "subtotal", "allowance"}
            }
            enclosed = {
                fact["id"]
                for fact in selected
                if fact.get("amount_cents") is not None
                and fact.get("parent_label")
                and _normal(fact["parent_label"]) in prices
            }
            cell.fact_ids = [value for value in cell.fact_ids if value not in enclosed]


def headline_spread(
    calculations: dict[str, dict[str, Any]],
) -> tuple[str, str, int] | None:
    """Compare only unambiguous AUD offer totals on the same GST basis."""
    if len(calculations) < 2:
        return None
    amounts = {}
    for quote_id, value in calculations.items():
        if value["conflicting_totals"] or value["currency"] != "AUD":
            return None
        amount = _inclusive(
            {
                "amount_cents": value["headline_cents"],
                "tax_basis": value["headline_basis"],
                "currency": value["currency"],
            }
        )
        if amount is None:
            return None
        amounts[quote_id] = amount
    low, high = min(amounts, key=amounts.get), max(amounts, key=amounts.get)
    return low, high, amounts[high] - amounts[low]

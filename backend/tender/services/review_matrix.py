"""An additive presentation of the selected schedule, backed by the quote ledger.

Canonical components enter amount cells. Quotes without a component schedule
can expose their standalone allowances as a partial schedule. Supporting rates,
options and repeated breakdowns remain evidence, never extra contract costs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from tender.review_schemas import ReviewSelection


@dataclass
class MatrixCell:
    amount_cents: int | None = None
    fact_ids: list[str] = field(default_factory=list)
    counted_ids: list[str] = field(default_factory=list)
    bundled_rows: list[str] = field(default_factory=list)


@dataclass
class MatrixColumn:
    currency: str
    tax_basis: str
    mixed_bases: bool
    item_total_cents: int | None
    quoted_total_cents: int | None
    difference_cents: int | None
    converted_total: bool
    partial_schedule: bool


@dataclass
class PriceMatrix:
    labels: list[str]
    rows: list[list[MatrixCell]]
    columns: list[MatrixColumn]


def _label(value: str) -> str:
    return " ".join(value.split()).casefold()


def _identity(fact: dict[str, Any]) -> tuple:
    return (
        _label(fact["label"]),
        fact["amount_cents"],
        fact["currency"],
        fact["tax_basis"],
    )


def build_price_matrix(
    selection: ReviewSelection,
    facts: list[dict[str, Any]],
    quotes: list[dict[str, Any]],
    calculations: dict[str, dict[str, Any]],
    *,
    other_label: str,
) -> PriceMatrix:
    """Assign every canonical component once without reallocating bundled prices."""
    by_id = {fact["id"]: fact for fact in facts}
    labels = [row.label for row in selection.matrix] + [other_label]
    rows = [
        [MatrixCell(fact_ids=list(cell.fact_ids)) for cell in row.cells]
        for row in selection.matrix
    ] + [[MatrixCell() for _ in quotes]]
    columns = []
    for column_index, quote in enumerate(quotes):
        calc = calculations[quote["id"]]
        own_facts = [fact for fact in facts if fact["quote_id"] == quote["id"]]
        components = [by_id[value] for value in calc["component_fact_ids"]]
        partial = not components
        if partial:
            selected_ids = {
                value for row in rows for value in row[column_index].fact_ids
            }
            candidates = [
                fact
                for fact in own_facts
                if fact["amount_cents"] is not None
                and (
                    fact["kind"] == "allowance"
                    or (fact["kind"] == "subtotal" and fact["id"] in selected_ids)
                )
            ]
            priced_labels = {
                (_label(fact["label"]), fact["document_id"]) for fact in candidates
            }
            standalone = [
                fact
                for fact in candidates
                if (_label(fact.get("parent_label") or ""), fact["document_id"])
                not in priced_labels
            ]
            components = list({_identity(fact): fact for fact in standalone}.values())
        canonical = {_identity(fact): fact for fact in components}
        by_label: dict[str, list[dict[str, Any]]] = {}
        for fact in own_facts:
            by_label.setdefault(_label(fact["label"]), []).append(fact)

        def parent_of(fact: dict[str, Any]) -> dict[str, Any] | None:
            parents = [
                parent
                for parent in by_label.get(_label(fact.get("parent_label") or ""), [])
                if parent["document_id"] == fact["document_id"]
            ]
            return parents[0] if len(parents) == 1 else None

        owners = {}
        selected_packages = {}
        # Exact prices own their schedule row; a repeated breakdown cannot take
        # a parent's price just because it happens to occur earlier in the table.
        for row_index, row in enumerate(rows[:-1]):
            for value in row[column_index].fact_ids:
                fact = by_id[value]
                if fact["kind"] in {"component", "subtotal"}:
                    selected_packages.setdefault(fact["id"], row_index)
                if fact["kind"] not in {"component", "subtotal", "allowance"}:
                    continue
                match = canonical.get(_identity(fact))
                if match:
                    owners.setdefault(match["id"], row_index)
        for fact in components:
            ancestor = parent_of(fact)
            visited = {fact["id"]}
            while ancestor and ancestor["id"] not in visited:
                visited.add(ancestor["id"])
                if ancestor["id"] in selected_packages:
                    owners[fact["id"]] = selected_packages[ancestor["id"]]
                ancestor = parent_of(ancestor)
            row_index = owners.setdefault(fact["id"], len(rows) - 1)
            cell = rows[row_index][column_index]
            cell.counted_ids.append(fact["id"])
            if fact["id"] not in cell.fact_ids:
                cell.fact_ids.append(fact["id"])

        def counted_parent(fact: dict[str, Any]) -> dict[str, Any] | None:
            visited = set()
            while fact["id"] not in visited:
                visited.add(fact["id"])
                if fact["kind"] in {"component", "subtotal", "allowance"}:
                    match = canonical.get(_identity(fact))
                    if match:
                        return match
                parent = parent_of(fact)
                if parent is None:
                    return None
                fact = parent
            return None

        bases = {(fact["currency"], fact["tax_basis"]) for fact in components}
        mixed = len(bases) > 1
        currency, basis = (
            next(iter(bases))
            if len(bases) == 1
            else (calc["currency"], calc["headline_basis"])
        )
        for row_index, row in enumerate(rows):
            cell = row[column_index]
            for value in cell.fact_ids:
                parent = counted_parent(by_id[value])
                if parent and owners[parent["id"]] != row_index:
                    name = labels[owners[parent["id"]]]
                    if name not in cell.bundled_rows:
                        cell.bundled_rows.append(name)
            if cell.counted_ids and not mixed:
                cell.amount_cents = sum(
                    by_id[value]["amount_cents"] for value in cell.counted_ids
                )

        item_total = (
            sum(fact["amount_cents"] for fact in components)
            if components and not mixed
            else None
        )
        quoted_total = None
        converted = False
        if not mixed and basis != "unknown" and not calc["conflicting_totals"]:
            matching = {
                fact["amount_cents"]
                for fact in own_facts
                if fact["kind"] == "total"
                and fact["amount_cents"] is not None
                and (fact["currency"], fact["tax_basis"]) == (currency, basis)
            }
            if len(matching) == 1:
                quoted_total = next(iter(matching))
            elif (
                not matching
                and currency == "AUD"
                and basis == "ex"
                and calc["currency"] == "AUD"
                and calc["headline_basis"] == "inc"
            ):
                # The existing reconciliation has no component basis for a
                # partial allowance/stage schedule, so its total is still gross.
                quoted_total = (
                    int(
                        (Decimal(calc["headline_cents"]) / Decimal("1.1")).quantize(
                            Decimal("1"), rounding=ROUND_HALF_UP
                        )
                    )
                    if partial and calc["headline_cents"] is not None
                    else calc["reconciliation_total_cents"]
                )
                converted = quoted_total is not None
        columns.append(
            MatrixColumn(
                currency=currency,
                tax_basis=basis,
                mixed_bases=mixed,
                item_total_cents=item_total,
                quoted_total_cents=quoted_total,
                difference_cents=(
                    quoted_total - item_total
                    if quoted_total is not None and item_total is not None
                    else None
                ),
                converted_total=converted,
                partial_schedule=partial,
            )
        )
    if not any(cell.counted_ids for cell in rows[-1]):
        labels.pop()
        rows.pop()
    return PriceMatrix(labels, rows, columns)

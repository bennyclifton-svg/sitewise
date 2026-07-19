"""Unit coverage for per-quote matrix totals and stated-total reconciliation."""

from __future__ import annotations

import uuid

from tender.services.totals import COUNTED_STATUSES, compute_quote_totals, delta_ratio

QUOTE_A = uuid.uuid4()
QUOTE_B = uuid.uuid4()


def test_counted_statuses_cover_included_and_allowances() -> None:
    assert COUNTED_STATUSES == {"included", "pc", "ps"}


def test_sums_included_and_allowance_cells_only() -> None:
    cells = [
        (QUOTE_A, "included", 100),
        (QUOTE_A, "pc", 50),
        (QUOTE_A, "ps", 25),
        (QUOTE_A, "excluded_explicit", 1_000),
        (QUOTE_A, "not_required", 1_000),
        (QUOTE_A, "silent_ambiguous", 1_000),
        (QUOTE_A, "bundled", 1_000),
        (QUOTE_A, "included", None),
    ]
    totals = compute_quote_totals(cells, [(QUOTE_A, 175, "manual")], tolerance=0.02)
    assert totals[0].computed_total_cents == 175
    assert totals[0].reconciliation == "match"
    assert totals[0].delta_cents == 0


def test_tolerance_boundary_counts_as_match() -> None:
    at_boundary = compute_quote_totals(
        [(QUOTE_A, "included", 102)], [(QUOTE_A, 100, "manual")], tolerance=0.02
    )[0]
    assert at_boundary.reconciliation == "match"

    beyond = compute_quote_totals(
        [(QUOTE_A, "included", 103)], [(QUOTE_A, 100, "manual")], tolerance=0.02
    )[0]
    assert beyond.reconciliation == "mismatch"
    assert beyond.delta_cents == 3
    assert beyond.delta_ratio == 0.03


def test_not_stated_when_quote_total_missing() -> None:
    total = compute_quote_totals(
        [(QUOTE_A, "included", 100)], [(QUOTE_A, None, None)], tolerance=0.02
    )[0]
    assert total.reconciliation == "not_stated"
    assert total.computed_total_cents == 100
    assert total.stated_total_cents is None
    assert total.delta_cents is None
    assert total.delta_ratio is None


def test_quote_with_no_cells_gets_zero_total() -> None:
    totals = compute_quote_totals(
        [], [(QUOTE_A, None, None), (QUOTE_B, 0, "extracted")], tolerance=0.02
    )
    assert totals[0].computed_total_cents == 0
    assert totals[0].reconciliation == "not_stated"
    assert totals[1].computed_total_cents == 0
    assert totals[1].reconciliation == "match"


def test_stated_zero_with_nonzero_computed_is_mismatch() -> None:
    total = compute_quote_totals(
        [(QUOTE_A, "included", 5)], [(QUOTE_A, 0, "manual")], tolerance=0.02
    )[0]
    assert total.reconciliation == "mismatch"
    assert total.delta_ratio == 1.0


def test_preserves_quote_order_and_source() -> None:
    totals = compute_quote_totals(
        [(QUOTE_B, "included", 10)],
        [(QUOTE_A, 10, "manual"), (QUOTE_B, 10, "extracted")],
        tolerance=0.0,
    )
    assert [total.quote_id for total in totals] == [QUOTE_A, QUOTE_B]
    assert totals[0].reconciliation == "mismatch"
    assert totals[1].stated_total_source == "extracted"


def test_delta_ratio_semantics() -> None:
    assert delta_ratio(0, 0) == 0.0
    assert delta_ratio(0, 10) == 1.0
    assert delta_ratio(100, 90) == 0.1

"""Unit coverage for ex-GST conserved matrix totals (I4 / Phase 3.4)."""

from __future__ import annotations

import uuid

from tender.services.mapping import UNALLOCATED_CELL_CODE
from tender.services.totals import QuoteTotalInput, compute_quote_totals, delta_ratio

QUOTE_A = uuid.uuid4()
QUOTE_B = uuid.uuid4()


def test_column_total_uses_recon_computed_ex_gst() -> None:
    totals = compute_quote_totals(
        [
            QuoteTotalInput(
                quote_id=QUOTE_A,
                stated_total_cents=110_00,
                stated_total_source="extracted",
                contract_type="lump_sum",
                computed_ex_gst_cents=100_00,
                residual_cents=0,
                recon_status="reconciled",
            )
        ],
        cell_rows=[
            (QUOTE_A, "03.01", 80_00),
            (QUOTE_A, UNALLOCATED_CELL_CODE, 5_00),
        ],
    )
    total = totals[0]
    assert total.computed_total_cents == 100_00
    assert total.basis == "ex"
    assert total.residual_cents == 0
    assert total.unallocated_cents == 5_00
    assert total.not_itemised_cents == 15_00  # 100 - 80 - 5
    assert total.stated_native_cents == 110_00
    assert total.non_comparable is False
    assert total.reconciliation == "match"


def test_cost_plus_marks_non_comparable() -> None:
    total = compute_quote_totals(
        [
            QuoteTotalInput(
                quote_id=QUOTE_A,
                stated_total_cents=200_00,
                stated_total_source="extracted",
                contract_type="cost_plus",
                computed_ex_gst_cents=180_00,
                residual_cents=0,
                recon_status="reconciled",
            )
        ],
        cell_rows=[(QUOTE_A, "03.01", 180_00)],
    )[0]
    assert total.non_comparable is True
    assert total.basis == "ex"
    assert total.computed_total_cents == 180_00


def test_residual_and_not_stated() -> None:
    residual = compute_quote_totals(
        [
            QuoteTotalInput(
                quote_id=QUOTE_A,
                stated_total_cents=100_00,
                stated_total_source="manual",
                contract_type="lump_sum",
                computed_ex_gst_cents=90_00,
                residual_cents=10_00,
                recon_status="residual",
            )
        ],
        cell_rows=[(QUOTE_A, "03.01", 90_00)],
    )[0]
    assert residual.reconciliation == "mismatch"
    assert residual.residual_cents == 10_00
    assert residual.not_itemised_cents == 0

    missing = compute_quote_totals(
        [
            QuoteTotalInput(
                quote_id=QUOTE_B,
                stated_total_cents=None,
                stated_total_source=None,
                contract_type="unknown",
                computed_ex_gst_cents=50_00,
                residual_cents=0,
                recon_status="not_stated",
            )
        ],
        cell_rows=[(QUOTE_B, "03.01", 40_00)],
    )[0]
    assert missing.reconciliation == "not_stated"
    assert missing.stated_native_cents is None
    assert missing.not_itemised_cents == 10_00


def test_fallback_without_recon_sums_cells() -> None:
    total = compute_quote_totals(
        [
            QuoteTotalInput(
                quote_id=QUOTE_A,
                stated_total_cents=100_00,
                stated_total_source="manual",
                contract_type="lump_sum",
                computed_ex_gst_cents=None,
                residual_cents=0,
                recon_status=None,
            )
        ],
        cell_rows=[
            (QUOTE_A, "03.01", 60_00),
            (QUOTE_A, UNALLOCATED_CELL_CODE, 10_00),
        ],
    )[0]
    assert total.computed_total_cents == 70_00
    assert total.unallocated_cents == 10_00
    assert total.not_itemised_cents == 0


def test_preserves_quote_order() -> None:
    totals = compute_quote_totals(
        [
            QuoteTotalInput(
                quote_id=QUOTE_A,
                stated_total_cents=10_00,
                stated_total_source="manual",
                contract_type="lump_sum",
                computed_ex_gst_cents=10_00,
                residual_cents=0,
                recon_status="reconciled",
            ),
            QuoteTotalInput(
                quote_id=QUOTE_B,
                stated_total_cents=20_00,
                stated_total_source="extracted",
                contract_type="lump_sum",
                computed_ex_gst_cents=20_00,
                residual_cents=0,
                recon_status="reconciled",
            ),
        ],
        cell_rows=[(QUOTE_B, "03.01", 20_00)],
    )
    assert [total.quote_id for total in totals] == [QUOTE_A, QUOTE_B]
    assert totals[1].stated_total_source == "extracted"


def test_delta_ratio_semantics() -> None:
    assert delta_ratio(0, 0) == 0.0
    assert delta_ratio(0, 10) == 1.0
    assert delta_ratio(100, 90) == 0.1

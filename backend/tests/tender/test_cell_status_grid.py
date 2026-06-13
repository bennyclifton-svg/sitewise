from __future__ import annotations

import uuid

from tender import worker
from tender.services import expectations


def test_cell_status_grid_unions_expected_and_mapped_cells() -> None:
    comparison_id = uuid.uuid4()
    q1 = uuid.uuid4()
    q2 = uuid.uuid4()

    drafts = expectations.build_cell_status_grid(
        comparison_id=comparison_id,
        quote_ids=[q1, q2],
        fired_rules=[
            expectations.FiredRule(
                rule_code="SITE.RETAINING.SHOULD",
                cell_code="03.05",
                severity="should",
                rationale="Sloping sites typically require retaining structures.",
            )
        ],
        mapped_items=[
            expectations.MappedCellItem(
                line_item_id=uuid.uuid4(),
                quote_id=q1,
                cell_code="03.01",
                item_status="included",
                amount_cents=4_000_000,
            ),
            expectations.MappedCellItem(
                line_item_id=uuid.uuid4(),
                quote_id=q2,
                cell_code="03.05",
                item_status="ps_allowance",
                allowance_cents=1_500_000,
            ),
        ],
    )

    by_key = {(draft.quote_id, draft.cell_code): draft for draft in drafts}

    assert by_key[(q1, "03.01")].status == "included"
    assert by_key[(q1, "03.01")].amount_cents == 4_000_000
    assert by_key[(q1, "03.01")].qa_state == "auto_pass"
    assert by_key[(q1, "03.05")].status == "silent_ambiguous"
    assert by_key[(q1, "03.05")].qa_state == "needs_review"
    assert by_key[(q1, "03.05")].queue_silence
    assert by_key[(q1, "03.05")].evidence["expected_because"] == [
        "SITE.RETAINING.SHOULD"
    ]
    assert by_key[(q2, "03.05")].status == "ps"
    assert by_key[(q2, "03.05")].amount_cents == 1_500_000
    assert not by_key[(q2, "03.05")].queue_silence


def test_cell_status_merge_is_idempotent_and_protects_reviewed_rows() -> None:
    comparison_id = uuid.uuid4()
    quote_id = uuid.uuid4()
    protected = expectations.CellStatusRowState(
        comparison_id=comparison_id,
        quote_id=quote_id,
        cell_code="03.05",
        status="bundled",
        amount_cents=None,
        bundled_into_cell="03.01",
        evidence={"operator": "confirmed"},
        confidence=0.91,
        qa_state="confirmed",
    )
    draft = expectations.CellStatusDraft(
        comparison_id=comparison_id,
        quote_id=quote_id,
        cell_code="03.05",
        status="silent_ambiguous",
        amount_cents=None,
        bundled_into_cell=None,
        evidence={"expected_because": ["SITE.RETAINING.SHOULD"]},
        confidence=None,
        qa_state="needs_review",
        queue_silence=True,
    )

    merge = expectations.merge_cell_status_drafts([protected], [draft])

    assert merge.inserts == []
    assert merge.updates == []
    assert merge.silence_jobs == []

    first = expectations.merge_cell_status_drafts([], [draft])
    inserted = [first.inserts[0].as_row_state()]
    second = expectations.merge_cell_status_drafts(inserted, [draft])

    assert len(first.inserts) == 1
    assert first.silence_jobs == [draft]
    assert second.inserts == []
    assert second.updates == []
    assert second.silence_jobs == []


def test_worker_registers_run_expectations_handler() -> None:
    assert worker.HANDLERS["run_expectations"] is expectations.run_expectations

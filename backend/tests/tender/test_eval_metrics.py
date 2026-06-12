from tender.eval.golden import (
    GoldenAnnotation,
    GoldenCellStatus,
    GoldenLineItem,
    GoldenMapping,
)
from tender.eval.metrics import evaluate_document, summarize_counts


def test_metrics_score_extraction_mapping_silence_and_impact() -> None:
    expected = GoldenAnnotation(
        line_items=(
            GoldenLineItem(
                description_raw="Site costs",
                page=2,
                amount_cents=10000,
                item_status="ps_allowance",
                mappings=(GoldenMapping(cell="03.01"),),
            ),
            GoldenLineItem(
                description_raw="Retaining walls",
                page=3,
                amount_cents=5000,
                item_status="included",
                mappings=(GoldenMapping(cell="03.05"), GoldenMapping(cell="19.01")),
            ),
        ),
        cell_status=(
            GoldenCellStatus(cell="03.05", status="bundled"),
            GoldenCellStatus(cell="19.01", status="silent_ambiguous"),
        ),
    )
    predicted = GoldenAnnotation(
        line_items=(
            GoldenLineItem(
                description_raw="Site costs",
                page=2,
                amount_cents=10000,
                item_status="ps_allowance",
                mappings=(GoldenMapping(cell="03.01"),),
            ),
            GoldenLineItem(
                description_raw="Retaining walls",
                page=3,
                amount_cents=5201,
                item_status="included",
                mappings=(GoldenMapping(cell="03.05"),),
            ),
            GoldenLineItem(description_raw="Unexpected note", page=9),
        ),
        cell_status=(
            GoldenCellStatus(cell="03.05", status="bundled"),
            GoldenCellStatus(cell="19.01", status="not_required"),
        ),
    )

    summary = summarize_counts(evaluate_document(expected, predicted))

    assert summary["extraction"]["line_item_recall"] == 1.0
    assert summary["extraction"]["line_item_precision"] == 2 / 3
    assert summary["extraction"]["amount_exact_match_rate"] == 0.5
    assert summary["extraction"]["status_accuracy"] == 1.0
    assert summary["mapping"]["cell_accuracy_at_1"] == 1.0
    assert summary["mapping"]["split_f1"] == 4 / 5
    assert summary["silence"]["bundled_precision"] == 1.0
    assert summary["silence"]["ambiguous_recall"] == 0.0
    assert summary["end_to_end"]["report_impacting_error_count"] == 2


def test_empty_metrics_have_counts_and_no_rates() -> None:
    summary = summarize_counts(evaluate_document(GoldenAnnotation(), GoldenAnnotation()))

    assert summary["extraction"]["line_item_gold_count"] == 0
    assert summary["extraction"]["line_item_recall"] is None
    assert summary["mapping"]["split_f1"] is None
    assert summary["end_to_end"]["report_impacting_check_count"] == 0


from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from tender.eval.golden import GoldenAnnotation, GoldenLineItem

SILENCE_CLASSES = ("excluded", "bundled", "ps_covered", "not_required", "ambiguous")
STATUS_ALIASES = {
    "excluded_explicit": "excluded",
    "silent_ambiguous": "ambiguous",
    "ps": "ps_covered",
}


@dataclass
class MetricCounts:
    line_gold: int = 0
    line_predicted: int = 0
    line_matched: int = 0
    amount_compared: int = 0
    amount_exact: int = 0
    status_compared: int = 0
    status_correct: int = 0
    mapping_compared: int = 0
    mapping_top1_correct: int = 0
    mapping_gold_pairs: int = 0
    mapping_predicted_pairs: int = 0
    mapping_pair_matches: int = 0
    impact_checks: int = 0
    impact_errors: int = 0
    silence_expected: Counter[str] = field(default_factory=Counter)
    silence_predicted: Counter[str] = field(default_factory=Counter)
    silence_true_positive: Counter[str] = field(default_factory=Counter)

    def add(self, other: "MetricCounts") -> None:
        self.line_gold += other.line_gold
        self.line_predicted += other.line_predicted
        self.line_matched += other.line_matched
        self.amount_compared += other.amount_compared
        self.amount_exact += other.amount_exact
        self.status_compared += other.status_compared
        self.status_correct += other.status_correct
        self.mapping_compared += other.mapping_compared
        self.mapping_top1_correct += other.mapping_top1_correct
        self.mapping_gold_pairs += other.mapping_gold_pairs
        self.mapping_predicted_pairs += other.mapping_predicted_pairs
        self.mapping_pair_matches += other.mapping_pair_matches
        self.impact_checks += other.impact_checks
        self.impact_errors += other.impact_errors
        self.silence_expected.update(other.silence_expected)
        self.silence_predicted.update(other.silence_predicted)
        self.silence_true_positive.update(other.silence_true_positive)


def evaluate_document(
    expected: GoldenAnnotation, predicted: GoldenAnnotation
) -> MetricCounts:
    counts = MetricCounts(
        line_gold=len(expected.line_items),
        line_predicted=len(predicted.line_items),
    )
    expected_by_key = _items_by_key(expected.line_items)
    predicted_by_key = _items_by_key(predicted.line_items)
    counts.line_matched = sum(
        min(len(expected_by_key[key]), len(predicted_by_key.get(key, [])))
        for key in expected_by_key
    )

    for expected_item, predicted_item in _matched_items(expected_by_key, predicted_by_key):
        if expected_item.amount_cents is not None:
            counts.amount_compared += 1
            if predicted_item.amount_cents == expected_item.amount_cents:
                counts.amount_exact += 1
            counts.impact_checks += 1
            if _amount_is_report_impacting(expected_item.amount_cents, predicted_item.amount_cents):
                counts.impact_errors += 1

        if expected_item.item_status:
            counts.status_compared += 1
            if predicted_item.item_status == expected_item.item_status:
                counts.status_correct += 1

        if expected_item.mappings:
            counts.mapping_compared += 1
            predicted_cell = predicted_item.mappings[0].cell if predicted_item.mappings else None
            if predicted_cell == expected_item.mappings[0].cell:
                counts.mapping_top1_correct += 1

    gold_pairs = _mapping_pairs(expected.line_items)
    predicted_pairs = _mapping_pairs(predicted.line_items)
    counts.mapping_gold_pairs = sum(gold_pairs.values())
    counts.mapping_predicted_pairs = sum(predicted_pairs.values())
    counts.mapping_pair_matches = sum(
        min(count, predicted_pairs.get(pair, 0)) for pair, count in gold_pairs.items()
    )

    expected_status = _cell_statuses(expected)
    predicted_status = _cell_statuses(predicted)
    for status in expected_status.values():
        if status in SILENCE_CLASSES:
            counts.silence_expected[status] += 1
    for status in predicted_status.values():
        if status in SILENCE_CLASSES:
            counts.silence_predicted[status] += 1
    for cell, status in expected_status.items():
        if status not in SILENCE_CLASSES:
            continue
        if predicted_status.get(cell) == status:
            counts.silence_true_positive[status] += 1

    for cell, expected_value in expected_status.items():
        counts.impact_checks += 1
        if predicted_status.get(cell) != expected_value:
            counts.impact_errors += 1

    return counts


def summarize_counts(counts: MetricCounts) -> dict[str, object]:
    silence: dict[str, float | int | None] = {}
    for status in SILENCE_CLASSES:
        silence[f"{status}_precision"] = _rate(
            counts.silence_true_positive[status], counts.silence_predicted[status]
        )
        silence[f"{status}_recall"] = _rate(
            counts.silence_true_positive[status], counts.silence_expected[status]
        )
        silence[f"{status}_expected_count"] = counts.silence_expected[status]
        silence[f"{status}_predicted_count"] = counts.silence_predicted[status]

    return {
        "extraction": {
            "line_item_recall": _rate(counts.line_matched, counts.line_gold),
            "line_item_precision": _rate(counts.line_matched, counts.line_predicted),
            "amount_exact_match_rate": _rate(counts.amount_exact, counts.amount_compared),
            "status_accuracy": _rate(counts.status_correct, counts.status_compared),
            "line_item_gold_count": counts.line_gold,
            "line_item_predicted_count": counts.line_predicted,
        },
        "mapping": {
            "cell_accuracy_at_1": _rate(
                counts.mapping_top1_correct, counts.mapping_compared
            ),
            "split_f1": _f1(
                counts.mapping_pair_matches,
                counts.mapping_predicted_pairs,
                counts.mapping_gold_pairs,
            ),
            "mapping_gold_pair_count": counts.mapping_gold_pairs,
            "mapping_predicted_pair_count": counts.mapping_predicted_pairs,
        },
        "silence": silence,
        "end_to_end": {
            "report_impacting_error_rate": _rate(
                counts.impact_errors, counts.impact_checks
            ),
            "report_impacting_error_count": counts.impact_errors,
            "report_impacting_check_count": counts.impact_checks,
        },
    }


def combine_counts(counts: Iterable[MetricCounts]) -> MetricCounts:
    combined = MetricCounts()
    for item in counts:
        combined.add(item)
    return combined


def _matched_items(
    expected_by_key: dict[tuple[str, int], list[GoldenLineItem]],
    predicted_by_key: dict[tuple[str, int], list[GoldenLineItem]],
) -> Iterable[tuple[GoldenLineItem, GoldenLineItem]]:
    for key, expected_items in expected_by_key.items():
        for expected_item, predicted_item in zip(expected_items, predicted_by_key.get(key, [])):
            yield expected_item, predicted_item


def _items_by_key(items: Iterable[GoldenLineItem]) -> dict[tuple[str, int], list[GoldenLineItem]]:
    by_key: dict[tuple[str, int], list[GoldenLineItem]] = defaultdict(list)
    for item in items:
        by_key[_line_key(item)].append(item)
    return by_key


def _mapping_pairs(items: Iterable[GoldenLineItem]) -> Counter[tuple[tuple[str, int], str]]:
    pairs: Counter[tuple[tuple[str, int], str]] = Counter()
    for item in items:
        key = _line_key(item)
        for mapping in item.mappings:
            pairs[(key, mapping.cell)] += 1
    return pairs


def _cell_statuses(annotation: GoldenAnnotation) -> dict[str, str]:
    return {
        item.cell: _normalize_status(item.status)
        for item in annotation.cell_status
    }


def _line_key(item: GoldenLineItem) -> tuple[str, int]:
    return (_normalize_text(item.description_raw), item.page)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _normalize_status(value: str) -> str:
    return STATUS_ALIASES.get(value, value)


def _amount_is_report_impacting(
    expected_cents: int, predicted_cents: int | None
) -> bool:
    if predicted_cents is None:
        return True
    if expected_cents == 0:
        return predicted_cents != 0
    return abs(predicted_cents - expected_cents) / abs(expected_cents) > 0.02


def _f1(true_positive: int, predicted: int, expected: int) -> float | None:
    precision = _rate(true_positive, predicted)
    recall = _rate(true_positive, expected)
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


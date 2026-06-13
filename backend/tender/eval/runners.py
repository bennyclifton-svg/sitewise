from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from app.config import settings
from tender.eval.golden import (
    GoldenAnnotation,
    GoldenCellStatus,
    GoldenDocument,
    GoldenLineItem,
    GoldenMapping,
)
from tender.seeds.load import normalize_phrase


@dataclass(frozen=True)
class MappingSynonym:
    cell_code: str
    phrase_norm: str
    embedding: tuple[float, ...] | None = None


class MappingPredictionRunner:
    """Offline T0/T1 mapping predictor over already-annotated line items."""

    def __init__(
        self,
        *,
        synonyms: Sequence[MappingSynonym] = (),
        description_embeddings: Mapping[str, Sequence[float]] | None = None,
    ) -> None:
        self.synonyms = tuple(synonyms)
        self.description_embeddings = {
            normalize_phrase(key): tuple(value)
            for key, value in (description_embeddings or {}).items()
        }
        self._exact: dict[str, set[str]] = defaultdict(set)
        for synonym in self.synonyms:
            self._exact[synonym.phrase_norm].add(synonym.cell_code)

    def predict(self, document: GoldenDocument) -> GoldenAnnotation:
        return GoldenAnnotation(
            line_items=tuple(self._predict_line_item(item) for item in document.annotation.line_items),
            cell_status=(),
        )

    def _predict_line_item(self, item: GoldenLineItem) -> GoldenLineItem:
        phrase_norm = normalize_phrase(item.description_raw)
        mappings = self._t0_mapping(phrase_norm) or self._t1_mapping(phrase_norm)
        return GoldenLineItem(
            description_raw=item.description_raw,
            page=item.page,
            qty=item.qty,
            unit=item.unit,
            amount_cents=item.amount_cents,
            item_status=item.item_status,
            allowance_cents=item.allowance_cents,
            mappings=mappings,
        )

    def _t0_mapping(self, phrase_norm: str) -> tuple[GoldenMapping, ...]:
        cells = self._exact.get(phrase_norm, set())
        if len(cells) == 1:
            return (GoldenMapping(cell=next(iter(cells))),)
        return ()

    def _t1_mapping(self, phrase_norm: str) -> tuple[GoldenMapping, ...]:
        embedding = self.description_embeddings.get(phrase_norm)
        if embedding is None:
            return ()
        scored: dict[str, float] = {}
        for synonym in self.synonyms:
            if synonym.embedding is None:
                continue
            similarity = _cosine_similarity(embedding, synonym.embedding)
            scored[synonym.cell_code] = max(scored.get(synonym.cell_code, -1.0), similarity)
        ordered = sorted(scored.items(), key=lambda item: item[1], reverse=True)
        if not ordered:
            return ()
        top_cell, top_score = ordered[0]
        runner_up = ordered[1][1] if len(ordered) > 1 else 0.0
        if top_score < settings.tender_t1_accept_sim:
            return ()
        if top_score - runner_up < settings.tender_t1_accept_margin:
            return ()
        return (GoldenMapping(cell=top_cell),)


SilenceAdjudicator = Callable[[GoldenDocument, GoldenCellStatus], str]


class SilencePredictionRunner:
    """Offline silence predictor using deterministic inputs plus a fake adjudicator."""

    def __init__(
        self,
        *,
        predictions: Mapping[tuple[str, str], str] | None = None,
        adjudicator: SilenceAdjudicator | None = None,
    ) -> None:
        self.predictions = dict(predictions or {})
        self.adjudicator = adjudicator

    def predict(self, document: GoldenDocument) -> GoldenAnnotation:
        return GoldenAnnotation(
            line_items=(),
            cell_status=tuple(
                self._predict_status(document, status)
                for status in document.annotation.cell_status
            ),
        )

    def _predict_status(
        self,
        document: GoldenDocument,
        status: GoldenCellStatus,
    ) -> GoldenCellStatus:
        outcome = self.predictions.get((document.id, status.cell))
        if outcome is None and self.adjudicator is not None:
            outcome = self.adjudicator(document, status)
        return GoldenCellStatus(
            cell=status.cell,
            status=_stored_silence_status(outcome or "ambiguous"),
            amount_cents=status.amount_cents,
        )


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _stored_silence_status(outcome: str) -> str:
    return {
        "excluded": "silent_ambiguous",
        "excluded_explicit": "excluded_explicit",
        "bundled": "bundled",
        "ps_covered": "ps",
        "ps": "ps",
        "not_required": "not_required",
        "ambiguous": "silent_ambiguous",
        "silent_ambiguous": "silent_ambiguous",
    }[outcome]

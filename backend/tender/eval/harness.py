from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from tender.eval.golden import (
    DEFAULT_MANIFEST_PATH,
    GoldenAnnotation,
    GoldenDocument,
    GoldenManifest,
    load_manifest,
)
from tender.eval.metrics import MetricCounts, combine_counts, evaluate_document, summarize_counts


class PredictionRunner(Protocol):
    def predict(self, document: GoldenDocument) -> GoldenAnnotation:
        ...


class EmptyPredictionRunner:
    def predict(self, document: GoldenDocument) -> GoldenAnnotation:
        return GoldenAnnotation()


@dataclass(frozen=True)
class DocumentEvalResult:
    document_id: str
    difficulty: str
    metrics: dict[str, object]


@dataclass(frozen=True)
class EvalRunResult:
    manifest: GoldenManifest
    summary: dict[str, object]
    documents: tuple[DocumentEvalResult, ...]


def run_eval(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    runner: PredictionRunner | None = None,
) -> EvalRunResult:
    manifest = load_manifest(manifest_path)
    predictor = runner or EmptyPredictionRunner()
    document_results: list[DocumentEvalResult] = []
    counts_by_difficulty: dict[str, list[MetricCounts]] = defaultdict(list)
    all_counts: list[MetricCounts] = []

    for document in manifest.documents:
        predicted = predictor.predict(document)
        counts = evaluate_document(document.annotation, predicted)
        all_counts.append(counts)
        counts_by_difficulty[document.difficulty].append(counts)
        document_results.append(
            DocumentEvalResult(
                document_id=document.id,
                difficulty=document.difficulty,
                metrics=summarize_counts(counts),
            )
        )

    overall = combine_counts(all_counts)
    return EvalRunResult(
        manifest=manifest,
        summary={
            "documents_evaluated": len(manifest.documents),
            "overall": summarize_counts(overall),
            "by_difficulty": {
                difficulty: summarize_counts(combine_counts(counts))
                for difficulty, counts in sorted(counts_by_difficulty.items())
            },
        },
        documents=tuple(document_results),
    )


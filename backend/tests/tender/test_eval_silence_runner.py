from __future__ import annotations

from tender.eval.golden import GoldenAnnotation, GoldenCellStatus, GoldenDocument
from tender.eval.harness import run_eval
from tender.eval.runners import SilencePredictionRunner


def test_silence_prediction_runner_uses_fake_adjudicator_offline() -> None:
    document = _document(
        GoldenAnnotation(
            cell_status=(
                GoldenCellStatus(cell="03.05", status="bundled"),
                GoldenCellStatus(cell="19.01", status="silent_ambiguous"),
            )
        )
    )
    runner = SilencePredictionRunner(
        adjudicator=lambda _document, status: {
            "03.05": "bundled",
            "19.01": "ambiguous",
        }[status.cell]
    )

    predicted = runner.predict(document)

    assert predicted.cell_status == (
        GoldenCellStatus(cell="03.05", status="bundled"),
        GoldenCellStatus(cell="19.01", status="silent_ambiguous"),
    )


def test_silence_prediction_runner_downgrades_inferred_excluded() -> None:
    document = _document(
        GoldenAnnotation(cell_status=(GoldenCellStatus(cell="03.05", status="excluded"),))
    )
    runner = SilencePredictionRunner(adjudicator=lambda _document, _status: "excluded")

    predicted = runner.predict(document)

    assert predicted.cell_status == (
        GoldenCellStatus(cell="03.05", status="silent_ambiguous"),
    )


def test_run_eval_accepts_silence_prediction_runner(tmp_path) -> None:
    golden_dir = tmp_path / "golden"
    golden_dir.mkdir()
    (golden_dir / "manifest.yaml").write_text(
        """
meta: {version: 1}
documents:
  - id: quote-001
    source: synthetic
    difficulty: easy
    ground_truth:
      line_items: []
      cell_status:
        - cell: "03.05"
          status: bundled
        - cell: "19.01"
          status: silent_ambiguous
""",
        encoding="utf-8",
    )

    result = run_eval(
        golden_dir / "manifest.yaml",
        runner=SilencePredictionRunner(
            predictions={
                ("quote-001", "03.05"): "bundled",
                ("quote-001", "19.01"): "ambiguous",
            }
        ),
    )

    assert result.summary["overall"]["silence"]["bundled_precision"] == 1.0
    assert result.summary["overall"]["silence"]["ambiguous_recall"] == 1.0


def _document(annotation: GoldenAnnotation) -> GoldenDocument:
    return GoldenDocument(
        id="quote-001",
        source="synthetic",
        difficulty="easy",
        storage_path=None,
        doc_meta={},
        annotation=annotation,
    )

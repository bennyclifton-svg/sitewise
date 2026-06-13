from __future__ import annotations

from tender.eval.golden import GoldenAnnotation, GoldenDocument, GoldenLineItem
from tender.eval.harness import run_eval
from tender.eval.runners import MappingPredictionRunner, MappingSynonym


def test_mapping_prediction_runner_maps_exact_unambiguous_synonym() -> None:
    runner = MappingPredictionRunner(
        synonyms=[
            MappingSynonym(cell_code="03.05", phrase_norm="retaining walls"),
            MappingSynonym(cell_code="19.01", phrase_norm="driveway"),
        ]
    )
    document = _document(
        GoldenAnnotation(
            line_items=(
                GoldenLineItem(description_raw=" Retaining   WALLS ", page=1),
                GoldenLineItem(description_raw="Driveway", page=2),
            )
        )
    )

    predicted = runner.predict(document)

    assert predicted.line_items[0].mappings[0].cell == "03.05"
    assert predicted.line_items[1].mappings[0].cell == "19.01"


def test_mapping_prediction_runner_leaves_ambiguous_exact_unmapped() -> None:
    runner = MappingPredictionRunner(
        synonyms=[
            MappingSynonym(cell_code="03.01", phrase_norm="site costs"),
            MappingSynonym(cell_code="20.01", phrase_norm="site costs"),
        ]
    )
    document = _document(
        GoldenAnnotation(
            line_items=(GoldenLineItem(description_raw="Site costs", page=1),)
        )
    )

    predicted = runner.predict(document)

    assert predicted.line_items[0].mappings == ()


def test_run_eval_accepts_mapping_prediction_runner(tmp_path) -> None:
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
      line_items:
        - description_raw: Retaining walls
          page: 1
          mappings:
            - cell: "03.05"
      cell_status: []
""",
        encoding="utf-8",
    )

    result = run_eval(
        golden_dir / "manifest.yaml",
        runner=MappingPredictionRunner(
            synonyms=[MappingSynonym(cell_code="03.05", phrase_norm="retaining walls")]
        ),
    )

    assert result.summary["overall"]["mapping"]["cell_accuracy_at_1"] == 1.0
    assert result.summary["overall"]["mapping"]["split_f1"] == 1.0


def _document(annotation: GoldenAnnotation) -> GoldenDocument:
    return GoldenDocument(
        id="doc-1",
        source="synthetic",
        difficulty="easy",
        storage_path=None,
        doc_meta={},
        annotation=annotation,
    )

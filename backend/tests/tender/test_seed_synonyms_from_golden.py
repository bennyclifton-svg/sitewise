"""S2: promote golden ground-truth mappings into synonym seed rows."""

from __future__ import annotations

from pathlib import Path

from tender.seeds.from_golden import (
    merge_synonym_base,
    synonym_rows_from_annotation,
    synonym_rows_from_annotations_dir,
)
from tender.seeds.load import normalize_phrase

FIXTURE_ANNOTATION = {
    "document": {
        "id": "enmore",
        "source": "real",
        "difficulty": "medium",
        "doc_type": "builder_quote",
        "state": "NSW",
        "build_type": "renovation",
        "anonymised": False,
    },
    "ground_truth": {
        "line_items": [
            {
                "description_raw": "Demolition external",
                "page": 1,
                "item_status": "included",
                "mappings": [{"cell": "02.02", "fraction": 1.0}],
            },
            {
                "description_raw": "install ducted air con to all living and bedrooms",
                "page": 2,
                "item_status": "included",
                "mappings": [{"cell": "10.09", "fraction": 1.0}],
            },
            {
                "description_raw": "split allowance across cells",
                "page": 2,
                "item_status": "included",
                "mappings": [
                    {"cell": "14.01", "fraction": 0.6},
                    {"cell": "15.11", "fraction": 0.4},
                ],
            },
            {
                "description_raw": "minor secondary only",
                "page": 2,
                "item_status": "included",
                "mappings": [{"cell": "22.04", "fraction": 0.3}],
            },
        ],
        "cell_status": [],
    },
}


def test_synonym_rows_from_annotation_uses_primary_mappings() -> None:
    rows = synonym_rows_from_annotation(FIXTURE_ANNOTATION)

    assert ("02.02", "Demolition external") in rows
    assert ("10.09", "install ducted air con to all living and bedrooms") in rows
    assert ("14.01", "split allowance across cells") in rows
    assert ("15.11", "split allowance across cells") not in rows
    assert ("22.04", "minor secondary only") not in rows


def test_merge_synonym_base_dedupes_on_normalized_phrase() -> None:
    existing = [("02.02", "partial demolition"), ("10.09", "ducted air conditioning")]
    additions = [
        ("02.02", "Demolition external"),
        ("02.02", "PARTIAL DEMOLITION"),  # already present after normalize
        ("10.09", "install ducted air con to all living and bedrooms"),
    ]

    merged = merge_synonym_base(existing, additions)

    assert merged[0] == ("02.02", "partial demolition")
    assert ("02.02", "Demolition external") in merged
    assert ("10.09", "install ducted air con to all living and bedrooms") in merged
    norms = {(code, normalize_phrase(phrase)) for code, phrase in merged}
    assert len(norms) == len(merged)


def test_synonym_rows_from_annotations_dir_reads_json_files(
    tmp_path: Path,
) -> None:
    path = tmp_path / "enmore.json"
    path.write_text(
        __import__("json").dumps(FIXTURE_ANNOTATION),
        encoding="utf-8",
    )

    rows = synonym_rows_from_annotations_dir(tmp_path)

    assert ("02.02", "Demolition external") in rows
    assert len(rows) >= 3


def test_flagship_golden_annotations_map_to_taxonomy_cells() -> None:
    import yaml

    data_dir = Path(__file__).resolve().parents[3] / "data" / "tender"
    tax = yaml.safe_load((data_dir / "taxonomy.yaml").read_text(encoding="utf-8"))
    codes = {cell["code"] for cell in tax["cells"]}
    rows = synonym_rows_from_annotations_dir(data_dir / "golden" / "annotations")

    assert len(rows) >= 100
    orphan = {code for code, _ in rows} - codes
    assert not orphan
    phrases = {phrase for _, phrase in rows}
    assert "Demolition external" in phrases
    assert "ELECTRICAN ROUGH IN" in phrases
    assert "Axon cladding and SS fixings" in phrases

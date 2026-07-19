from pathlib import Path

import pytest

from tender.eval.golden import DEFAULT_MANIFEST_PATH, load_manifest


def test_repo_manifest_loads() -> None:
    manifest = load_manifest(DEFAULT_MANIFEST_PATH)

    assert manifest.version == 1
    assert {document.id for document in manifest.documents} == {
        "enmore",
        "kaposi",
        "nexusbuilt",
    }
    assert manifest.targets["real_documents_min"] == 30


def test_manifest_loads_annotation_file(tmp_path: Path) -> None:
    golden_dir = tmp_path / "golden"
    annotation_dir = golden_dir / "annotations"
    annotation_dir.mkdir(parents=True)
    (golden_dir / "manifest.yaml").write_text(
        """
meta:
  version: 1
documents:
  - id: quote-001
    source: synthetic
    difficulty: hard
    doc_type: quote_letter
    state: NSW
    build_type: renovation
    anonymised: true
    storage_path: payloads/quote-001.pdf
    annotation_path: annotations/quote-001.yaml
""",
        encoding="utf-8",
    )
    (annotation_dir / "quote-001.yaml").write_text(
        """
ground_truth:
  line_items:
    - description_raw: Site costs
      page: 2
      amount_cents: 1500000
      item_status: ps_allowance
      allowance_cents: 1500000
      mappings:
        - cell: "03.01"
          fraction: 1.0
  cell_status:
    - cell: "03.01"
      status: ps_covered
      amount_cents: 1500000
""",
        encoding="utf-8",
    )

    manifest = load_manifest(golden_dir / "manifest.yaml")
    document = manifest.documents[0]

    assert document.id == "quote-001"
    assert document.source == "synthetic"
    assert document.difficulty == "hard"
    assert document.doc_meta["state"] == "NSW"
    assert document.annotation.line_items[0].mappings[0].cell == "03.01"
    assert document.annotation.cell_status[0].status == "ps_covered"


def test_manifest_rejects_document_without_annotation(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        """
meta:
  version: 1
documents:
  - id: quote-001
    source: real
    difficulty: easy
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing an annotation path"):
        load_manifest(manifest_path)


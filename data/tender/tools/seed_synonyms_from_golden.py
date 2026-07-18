#!/usr/bin/env python3
"""Promote golden ground-truth mappings into synonyms.base.csv (S2).

Reads data/tender/golden/annotations/*.json, appends primary mapping phrases
to synonyms.base.csv (deduped), then leaves expand_synonyms.py to regenerate
synonyms.seed.csv.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
BACKEND_DIR = HERE.parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tender.seeds.from_golden import (  # noqa: E402
    merge_synonym_base,
    synonym_rows_from_annotations_dir,
)

ANNOTATIONS = HERE / "golden" / "annotations"
BASE = HERE / "synonyms.base.csv"


def main() -> int:
    existing = _read_base(BASE)
    additions = synonym_rows_from_annotations_dir(ANNOTATIONS)
    merged = merge_synonym_base(existing, additions)
    added = len(merged) - len(existing)
    _write_base(BASE, merged)
    print(
        f"{len(additions)} golden phrases -> {added} new base rows "
        f"({len(merged)} total) -> {BASE.name}"
    )
    print("Next: python data/tender/tools/expand_synonyms.py")
    return 0


def _read_base(path: Path) -> list[tuple[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [(row["cell_code"], row["phrase"]) for row in csv.DictReader(handle)]


def _write_base(path: Path, rows: list[tuple[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cell_code", "phrase"])
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())

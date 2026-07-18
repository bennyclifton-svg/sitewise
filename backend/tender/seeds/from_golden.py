"""Promote golden ground-truth mappings into synonym seed rows (S2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tender.seeds.load import normalize_phrase

PRIMARY_FRACTION = 0.5


def synonym_rows_from_annotation(
    annotation: dict[str, Any],
    *,
    min_fraction: float = PRIMARY_FRACTION,
) -> list[tuple[str, str]]:
    """Return (cell_code, phrase) pairs from primary ground-truth mappings."""
    ground_truth = annotation.get("ground_truth") or {}
    rows: list[tuple[str, str]] = []
    for item in ground_truth.get("line_items") or []:
        phrase = str(item.get("description_raw") or "").strip()
        if not phrase:
            continue
        for mapping in item.get("mappings") or []:
            fraction = float(mapping.get("fraction", 1.0))
            if fraction < min_fraction:
                continue
            cell = str(mapping.get("cell") or "").strip()
            if not cell:
                continue
            rows.append((cell, phrase))
    return rows


def synonym_rows_from_annotations_dir(directory: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for path in sorted(directory.glob("*.json")):
        with path.open(encoding="utf-8") as handle:
            annotation = json.load(handle)
        rows.extend(synonym_rows_from_annotation(annotation))
    return rows


def merge_synonym_base(
    existing: list[tuple[str, str]],
    additions: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Append new (cell, phrase) rows; dedupe on (cell_code, phrase_norm)."""
    seen = {(code, normalize_phrase(phrase)) for code, phrase in existing}
    merged = list(existing)
    for code, phrase in additions:
        phrase = phrase.strip()
        if not phrase:
            continue
        key = (code, normalize_phrase(phrase))
        if key in seen:
            continue
        seen.add(key)
        merged.append((code, phrase))
    return merged

"""X1 Stage 8: stored document_class values match the frozen Stage 3 vocabulary."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any

import pytest

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "049_canonical_document_taxonomy.py"
)
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_LEGACY_WRITER = re.compile(
    r'document_class\s*=\s*"(?:'
    r"tep|eoi|rft|addendum|tender_submission|evaluation|trr|"
    r"planning_instrument|doctrine|reference_guide|inbox_pending|corpus_catalog"
    r')"'
)
_EXPECTED_MAPPING: dict[str, tuple[str, dict[str, str]]] = {
    "tep": ("commercial", {"procurement_stage": "tep"}),
    "eoi": ("commercial", {"procurement_stage": "eoi"}),
    "rft": ("commercial", {"procurement_stage": "rft"}),
    "addendum": ("commercial", {"procurement_stage": "addendum"}),
    "tender_submission": ("commercial", {"procurement_stage": "submission"}),
    "evaluation": ("commercial", {"procurement_stage": "evaluation"}),
    "trr": ("commercial", {"procurement_stage": "trr"}),
    "planning_instrument": ("statutory_instrument", {}),
    "doctrine": ("report", {"reference_kind": "doctrine"}),
    "reference_guide": ("report", {"reference_kind": "reference_guide"}),
    "corpus_catalog": ("schedule", {"synthetic": "true"}),
    "inbox_pending": ("unknown", {}),
}


def _load_migration() -> Any:
    spec = importlib.util.spec_from_file_location(
        "rev_049_canonical_document_taxonomy", _MIGRATION_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_mapping_matches_code_mapping() -> None:
    migration = _load_migration()
    assert migration.MAPPING == _EXPECTED_MAPPING


def test_migration_merges_metadata_instead_of_replacing() -> None:
    migration = _load_migration()
    new_class, merged = migration.apply_class_mapping(
        "doctrine",
        {"title": "Keep me", "reference_kind": "stale"},
    )
    assert new_class == "report"
    assert merged["title"] == "Keep me"
    assert merged["reference_kind"] == "doctrine"
    reverted_class, reverted = migration.revert_class_mapping(new_class, merged)
    assert reverted_class == "doctrine"
    assert reverted["title"] == "Keep me"
    assert "reference_kind" not in reverted


def test_production_writers_do_not_emit_legacy_document_class() -> None:
    hits: list[str] = []
    for root in (_BACKEND_ROOT / "app", _BACKEND_ROOT / "ingest"):
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            for line_no, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if _LEGACY_WRITER.search(line):
                    hits.append(f"{path.relative_to(_BACKEND_ROOT)}:{line_no}:{line.strip()}")
    assert hits == []


def test_upgrade_strips_legacy_class_marker() -> None:
    migration = _load_migration()
    _, merged = migration.apply_class_mapping("doctrine", {"title": "Keep me"})
    assert merged["_legacy_document_class"] == "doctrine"
    cleaned = dict(merged)
    cleaned.pop(migration.LEGACY_CLASS_MARKER)
    assert "_legacy_document_class" not in cleaned
    assert cleaned["title"] == "Keep me"
    assert cleaned["reference_kind"] == "doctrine"


def test_assert_canonical_classes_rejects_leftover_legacy() -> None:
    migration = _load_migration()

    class _Conn:
        def execute(self, _stmt, _params=None):
            return _Result([("reference_guide", 75)])

    class _Result:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    with pytest.raises(AssertionError, match="non-canonical"):
        migration.assert_canonical_classes(_Conn())

from typing import get_args
from pathlib import Path

from ingest.types import ClassificationBasis, DocumentClass, DocumentSubject
from ingest.router import REVIEW_CONFIDENCE_MIN, _chunker_for, _extractor_for
from ingest.types import Classification


def test_document_class_vocabulary_is_frozen() -> None:
    """Changing this set is a Gate-1 breaking change. Update the plan first."""
    assert set(get_args(DocumentClass)) == {
        "drawing", "specification", "report", "certificate", "correspondence",
        "contract", "commercial", "schedule", "statutory_instrument",
        "photo", "unknown",
    }


def test_document_subject_vocabulary_is_the_category_list() -> None:
    slugs = get_args(DocumentSubject)
    assert slugs[-1] == "none"
    assert "architect" in slugs
    assert "mechanical" in slugs
    assert "fire_services" in slugs
    assert "bca" in slugs
    assert "civil" in slugs
    assert "esd" in slugs
    assert "interior_design" in slugs
    assert "roof_access" in slugs
    assert "ecology" in slugs
    assert "archaeology" in slugs
    assert "civil_stormwater" not in slugs
    assert "architecture" not in slugs
    assert "services" not in slugs
    assert "planning" not in slugs


def test_basis_vocabulary_is_frozen() -> None:
    assert set(get_args(ClassificationBasis)) == {
        "user", "structural", "filename", "content", "model", "default",
    }


def test_every_class_has_a_chunker() -> None:
    """No DocumentClass may fall through to an undefined chunker."""
    for document_class in get_args(DocumentClass):
        classification = Classification(
            document_class=document_class, ingest_mode="full_text", document_metadata={}
        )
        chunker = _chunker_for(classification)
        assert chunker in {"prose", "specification", "register", "schedule"}, document_class


def test_every_class_has_an_extractor_for_pdf() -> None:
    for document_class in get_args(DocumentClass):
        classification = Classification(
            document_class=document_class, ingest_mode="full_text", document_metadata={}
        )
        assert _extractor_for(classification, ".pdf") != "unsupported", document_class


def test_frontend_vocabulary_matches_python() -> None:
    ts_path = (
        Path(__file__).resolve().parents[3]
        / "frontend"
        / "src"
        / "lib"
        / "classification.ts"
    )
    text = ts_path.read_text(encoding="utf-8")

    def _values(const_name: str) -> list[str]:
        start = text.index(f"export const {const_name}")
        block = text[start : text.index("] as const", start)]
        return [line.strip().strip('",') for line in block.splitlines() if '"' in line]

    assert _values("DOCUMENT_CLASSES") == list(get_args(DocumentClass))
    assert _values("DOCUMENT_CATEGORIES") == list(get_args(DocumentSubject))
    assert f"export const REVIEW_CONFIDENCE_MIN = {REVIEW_CONFIDENCE_MIN}" in text


def test_review_confidence_min_is_the_named_gate() -> None:
    assert REVIEW_CONFIDENCE_MIN == 0.65

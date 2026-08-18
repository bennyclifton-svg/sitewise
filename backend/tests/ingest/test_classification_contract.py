from typing import get_args
from ingest.types import ClassificationBasis, DocumentClass, DocumentSubject
from ingest.router import _chunker_for, _extractor_for
from ingest.types import Classification


def test_document_class_vocabulary_is_frozen() -> None:
    """Changing this set is a Gate-1 breaking change. Update the plan first."""
    assert set(get_args(DocumentClass)) == {
        "drawing", "specification", "report", "certificate", "correspondence",
        "contract", "commercial", "schedule", "statutory_instrument",
        "photo", "unknown",
    }


def test_document_subject_vocabulary_is_frozen() -> None:
    assert len(get_args(DocumentSubject)) == 16
    assert "none" in get_args(DocumentSubject)


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
        assert chunker in {"prose", "specification", "register"}, document_class


def test_every_class_has_an_extractor_for_pdf() -> None:
    for document_class in get_args(DocumentClass):
        classification = Classification(
            document_class=document_class, ingest_mode="full_text", document_metadata={}
        )
        assert _extractor_for(classification, ".pdf") != "unsupported", document_class

"""The triage report has to be honest about which sheets need attention.

A row that silently fell back to the filename is the case worth chasing, so it
must not be reported as clean.
"""

from scripts.triage_drawing_identity import Row


def _row(**overrides) -> Row:
    values = {
        "file_name": "E02 - LIGHTING.pdf",
        "document_number": "E02",
        "title": "LEVEL L0 GROUND - LIGHTING LAYOUT",
        "revision": "C1",
        "confidence": "high",
        "source": "title-block",
    }
    values.update(overrides)
    return Row(**values)


def test_a_fully_parsed_sheet_is_not_suspect():
    assert _row().is_suspect is False


def test_a_missing_title_is_suspect():
    assert _row(title="").is_suspect is True


def test_a_missing_document_number_is_suspect():
    assert _row(document_number="").is_suspect is True


def test_low_confidence_is_suspect():
    assert _row(confidence="low").is_suspect is True


def test_a_title_that_is_only_the_filename_stem_is_suspect():
    # "01.pdf" parsing to title "01" means nothing was read off the sheet.
    assert _row(file_name="01.pdf", title="01", document_number="221102 - SK-003").is_suspect is True


def test_a_title_echoing_the_filename_stem_is_suspect():
    assert _row(file_name="E02-EL~1.PDF", title="E02 EL 1").is_suspect is True


def test_a_missing_revision_is_suspect():
    assert _row(revision="Current").is_suspect is True

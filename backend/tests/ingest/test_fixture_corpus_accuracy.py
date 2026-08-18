from pathlib import Path

from tests.fixtures.classification import Fixture, load_fixtures
from ingest.classify import classify_entry
from ingest.types import ManifestEntry


def _classify_fixture(fixture: Fixture):
    suffix = Path(fixture.filename).suffix.lower() or ".pdf"
    entry = ManifestEntry(
        absolute_path=Path(fixture.filename),
        relative_path=fixture.filename,
        project="fixture",
        filename=fixture.filename,
        extension=suffix,
        size_bytes=len(fixture.body.encode("utf-8")),
    )
    return classify_entry(entry, extracted_text=fixture.body or None)


def test_report_fixture_corpus_accuracy(capsys) -> None:
    fixtures = load_fixtures()
    results = [_classify_fixture(fixture) for fixture in fixtures]
    correct_class = sum(
        1
        for fixture, result in zip(fixtures, results, strict=True)
        if result.document_class == fixture.expect["class"]
    )
    correct_subject = sum(
        1
        for fixture, result in zip(fixtures, results, strict=True)
        if "subject" not in fixture.expect
        or result.document_subject == fixture.expect["subject"]
    )
    unknown = sum(1 for result in results if result.document_class == "unknown")
    low_confidence = sum(1 for result in results if result.confidence < 0.65)
    print(f"class accuracy: {correct_class}/{len(fixtures)}")
    print(f"subject accuracy: {correct_subject}/{len(fixtures)}")
    print(f"unknown rate: {unknown}/{len(fixtures)}")
    print(f"low-confidence rate: {low_confidence}/{len(fixtures)}")
    assert correct_class >= 14  # ratchet: raise this number, never lower it

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from ingest.extractors.base import ExtractedDocument, PageText
from ingest.extractors.pdf_odl import (
    _run_odl,
    _text_layer_extract,
    _text_layer_only,
    _with_title_block,
    extract_pdf_odl,
)


def test_odl_failures_log_and_persist_only_exception_class(
    monkeypatch, tmp_path: Path
) -> None:
    pdf_path = tmp_path / "drawing.pdf"
    pdf_path.write_bytes(b"pdf-bytes")
    canary = "ch03-odl-provider-token-xxxxxxxxxxxxxxxxxxxxxxxx"

    def always_failing(*_args, **_kwargs):
        raise RuntimeError(canary)

    monkeypatch.setattr(
        "ingest.extractors.pdf_odl.extract_pdf_document", always_failing
    )
    warning = MagicMock()
    monkeypatch.setattr("ingest.extractors.pdf_odl.logger.warning", warning)

    document, error = _run_odl(pdf_path)

    assert document is None
    assert isinstance(error, RuntimeError)
    assert warning.call_count == 2
    assert all(call.kwargs["error_type"] == "RuntimeError" for call in warning.call_args_list)
    assert canary not in str(warning.call_args_list)

    monkeypatch.setattr(
        "ingest.extractors.pdf_odl._text_layer_extract",
        lambda _path: _fake_text_layer("usable fallback text"),
    )
    salvaged = _text_layer_only(pdf_path, error)
    assert salvaged.extraction_metadata["odl_error"] == "RuntimeError"
    assert canary not in str(salvaged.extraction_metadata)


def test_optional_pdf_fallbacks_log_only_exception_class(
    monkeypatch, tmp_path: Path
) -> None:
    pdf_path = tmp_path / "drawing.pdf"
    pdf_path.write_bytes(b"pdf-bytes")
    canary = "ch03-pdf-provider-token-xxxxxxxxxxxxxxxxxxxxxxxx"
    warning = MagicMock()
    monkeypatch.setattr("ingest.extractors.pdf_odl.logger.warning", warning)

    def fail(*_args, **_kwargs):
        raise RuntimeError(canary)

    monkeypatch.setattr(
        "ingest.extractors.pdf_odl.extract_pdf_title_block_text", fail
    )
    monkeypatch.setattr(
        "ingest.extractors.pdf_odl.extract_pdf_title_block_fields", fail
    )
    monkeypatch.setattr("ingest.extractors.pdf_odl.extract_pdf_text", fail)

    selected = _fake_text_layer("safe text")
    assert _with_title_block(pdf_path, selected) is selected
    assert _text_layer_extract(pdf_path) is None
    assert warning.call_count == 3
    assert all(call.kwargs["error_type"] == "RuntimeError" for call in warning.call_args_list)
    assert canary not in str(warning.call_args_list)


def test_extract_pdf_odl_uses_hybrid_and_normalizes_pages(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "quote.pdf"
    pdf_path.write_bytes(b"pdf-bytes")
    calls: list[tuple[bytes, bool]] = []

    def fake_extract_pdf_document(
        pdf_bytes: bytes,
        *,
        hybrid: bool,
        hybrid_url: str | None,
        hybrid_mode: str,
        hybrid_fallback: bool,
    ):
        calls.append((pdf_bytes, hybrid))
        return SimpleNamespace(
            pages=[
                SimpleNamespace(page_no=1, text="Page one text"),
                SimpleNamespace(page_no=2, text="  "),
                SimpleNamespace(page_no=3, text="Page three text"),
            ],
            hybrid_backend_available=True,
            hybrid_mode="full",
        )

    monkeypatch.setattr(
        "ingest.extractors.pdf_odl.extract_pdf_document",
        fake_extract_pdf_document,
    )
    monkeypatch.setattr(
        "ingest.extractors.pdf_odl.settings.tender_odl_hybrid_enabled",
        True,
    )
    monkeypatch.setattr("ingest.extractors.pdf_odl._text_layer_extract", lambda path: None)
    monkeypatch.setattr("ingest.extractors.pdf_odl.extract_pdf_title_block_text", lambda path: "")

    extracted = extract_pdf_odl(pdf_path)

    assert calls == [(b"pdf-bytes", True)]
    assert extracted.page_count == 3
    assert [page.page_number for page in extracted.pages] == [1, 3]
    assert extracted.normalized_content == (
        "## Page 1\n\nPage one text\n\n## Page 3\n\nPage three text"
    )
    assert extracted.extraction_metadata["pdf_extraction_source"] == "odl"
    assert extracted.extraction_metadata["odl_hybrid_requested"] is True
    assert extracted.extraction_metadata["odl_hybrid_mode"] == "full"
    assert extracted.extraction_metadata["odl_hybrid_backend_available"] is True


def test_extract_pdf_odl_appends_title_block_for_register_metadata(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "hydraulic.pdf"
    pdf_path.write_bytes(b"pdf-bytes")

    monkeypatch.setattr(
        "ingest.extractors.pdf_odl.extract_pdf_document",
        lambda *_args, **_kwargs: SimpleNamespace(
            pages=[SimpleNamespace(page_no=1, text="Hydraulic drawing body")],
            hybrid_backend_available=True,
            hybrid_mode="full",
        ),
    )
    monkeypatch.setattr("ingest.extractors.pdf_odl._text_layer_extract", lambda path: None)
    monkeypatch.setattr(
        "ingest.extractors.pdf_odl.extract_pdf_title_block_text",
        lambda path: "Title: HYDRAULICS SERVICES SPATIALS\nDrawing / Sketch No. HY-SK-01\nRev. P1",
    )

    extracted = extract_pdf_odl(pdf_path)

    assert "## Title block" in extracted.normalized_content
    assert "Drawing / Sketch No. HY-SK-01" in extracted.normalized_content
    assert extracted.extraction_metadata["pdf_title_block_extracted"] is True


def test_extract_pdf_odl_falls_back_when_odl_loses_text(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "quote.pdf"
    pdf_path.write_bytes(b"pdf-bytes")

    def fake_extract_pdf_document(
        pdf_bytes: bytes,
        *,
        hybrid: bool,
        hybrid_url: str | None,
        hybrid_mode: str,
        hybrid_fallback: bool,
    ):
        return SimpleNamespace(
            pages=[SimpleNamespace(page_no=1, text="PRICE ESTIMATE")],
            hybrid_backend_available=False,
            hybrid_mode="full",
        )

    text_layer = ExtractedDocument(
        normalized_content="## Page 1\n\n" + ("Line item $1,000\n" * 80),
        page_count=1,
        pages=[PageText(page_number=1, text="Line item $1,000")],
    )

    monkeypatch.setattr(
        "ingest.extractors.pdf_odl.extract_pdf_document",
        fake_extract_pdf_document,
    )
    monkeypatch.setattr(
        "ingest.extractors.pdf_odl._text_layer_extract",
        lambda path: text_layer,
    )

    extracted = extract_pdf_odl(pdf_path)

    assert extracted.normalized_content == text_layer.normalized_content
    assert extracted.extraction_metadata["pdf_extraction_source"] == "text_layer_fallback"
    assert extracted.extraction_metadata["odl_hybrid_backend_available"] is False
    assert extracted.extraction_metadata["odl_character_count"] == len("## Page 1\n\nPRICE ESTIMATE")


def _fake_text_layer(text: str) -> ExtractedDocument:
    return ExtractedDocument(
        normalized_content=text,
        page_count=1,
        pages=[PageText(page_number=1, text=text)],
    )


def test_extract_pdf_odl_retries_a_crashed_odl_subprocess(monkeypatch, tmp_path: Path) -> None:
    # The OpenDataLoader CLI is a Java subprocess that dies transiently; the same
    # bytes succeed on a second run, so one crash must not cost the document.
    pdf_path = tmp_path / "drawing.pdf"
    pdf_path.write_bytes(b"pdf-bytes")
    attempts: list[int] = []

    def flaky_extract_pdf_document(pdf_bytes: bytes, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("returned non-zero exit status 130")
        return SimpleNamespace(
            pages=[SimpleNamespace(page_no=1, text="Recovered page text")],
            hybrid_backend_available=True,
            hybrid_mode="full",
        )

    monkeypatch.setattr(
        "ingest.extractors.pdf_odl.extract_pdf_document", flaky_extract_pdf_document
    )
    monkeypatch.setattr("ingest.extractors.pdf_odl._text_layer_extract", lambda path: None)
    monkeypatch.setattr("ingest.extractors.pdf_odl.extract_pdf_title_block_text", lambda path: "")

    extracted = extract_pdf_odl(pdf_path)

    assert len(attempts) == 2
    assert "Recovered page text" in extracted.normalized_content
    assert extracted.extraction_metadata["pdf_extraction_source"] == "odl"


def test_extract_pdf_odl_falls_back_to_the_text_layer_when_odl_keeps_failing(
    monkeypatch, tmp_path: Path
) -> None:
    # A dead Java subprocess must not discard a document the in-process text
    # layer can read perfectly well.
    pdf_path = tmp_path / "drawing.pdf"
    pdf_path.write_bytes(b"pdf-bytes")

    def always_failing(pdf_bytes: bytes, **kwargs):
        raise RuntimeError("returned non-zero exit status 130")

    monkeypatch.setattr("ingest.extractors.pdf_odl.extract_pdf_document", always_failing)
    monkeypatch.setattr(
        "ingest.extractors.pdf_odl._text_layer_extract",
        lambda path: _fake_text_layer("E02 LEVEL L0 GROUND - LIGHTING LAYOUT"),
    )
    monkeypatch.setattr("ingest.extractors.pdf_odl.extract_pdf_title_block_text", lambda path: "")

    extracted = extract_pdf_odl(pdf_path)

    assert "LEVEL L0 GROUND - LIGHTING LAYOUT" in extracted.normalized_content
    assert extracted.extraction_metadata["pdf_extraction_source"] == "text_layer_after_odl_failure"
    assert extracted.extraction_metadata["odl_error"]


def test_extract_pdf_odl_raises_when_neither_odl_nor_text_layer_yields_text(
    monkeypatch, tmp_path: Path
) -> None:
    pdf_path = tmp_path / "drawing.pdf"
    pdf_path.write_bytes(b"pdf-bytes")

    def always_failing(pdf_bytes: bytes, **kwargs):
        raise RuntimeError("returned non-zero exit status 130")

    monkeypatch.setattr("ingest.extractors.pdf_odl.extract_pdf_document", always_failing)
    monkeypatch.setattr("ingest.extractors.pdf_odl._text_layer_extract", lambda path: None)
    monkeypatch.setattr("ingest.extractors.pdf_odl.extract_pdf_title_block_text", lambda path: "")

    try:
        extract_pdf_odl(pdf_path)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected the original ODL failure to surface")

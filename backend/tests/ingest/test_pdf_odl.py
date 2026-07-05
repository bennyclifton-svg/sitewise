from pathlib import Path
from types import SimpleNamespace

from ingest.extractors.base import ExtractedDocument, PageText
from ingest.extractors.pdf_odl import extract_pdf_odl


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

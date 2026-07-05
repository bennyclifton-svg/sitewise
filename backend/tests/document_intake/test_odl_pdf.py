import json
from pathlib import Path

from app.document_intake.odl_pdf import extract_pdf_document, extract_pages


def test_extract_pdf_document_uses_odl_markdown_with_hybrid(monkeypatch) -> None:
    calls: dict = {}

    def fake_convert(**kwargs) -> None:
        calls.update(kwargs)
        output_dir = Path(kwargs["output_dir"])
        (output_dir / "doc.json").write_text(
            json.dumps(
                {
                    "kids": [
                        {"page number": 1, "content": "First"},
                        {"page number": 1, "content": "Second"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        (output_dir / "doc.md").write_text(
            "\n\n<!-- page 1 -->\n\n|Trade|Price|\n|---|---|\n|Demo|$1,000|",
            encoding="utf-8",
        )
        (output_dir / "doc.html").write_text("<table></table>", encoding="utf-8")
        (output_dir / "doc.txt").write_text(
            "\n\n=== page 1 ===\n\nDemo\t$1,000",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        "app.document_intake.odl_pdf.opendataloader_pdf.convert",
        fake_convert,
    )
    monkeypatch.setattr(
        "app.document_intake.odl_pdf._hybrid_backend_available",
        lambda url: False,
    )

    document = extract_pdf_document(
        b"pdf-bytes",
        hybrid=True,
        hybrid_url="http://odl.local:5002",
        hybrid_mode="full",
        hybrid_fallback=True,
    )

    assert calls["format"] == "json,markdown,html,text"
    assert calls["image_output"] == "off"
    assert calls["hybrid"] == "docling-fast"
    assert calls["hybrid_mode"] == "full"
    assert calls["hybrid_url"] == "http://odl.local:5002"
    assert calls["hybrid_fallback"] is True
    assert document.hybrid_requested is True
    assert document.hybrid_backend_available is False
    assert document.hybrid_mode == "full"
    assert "|Trade|Price|\n|---|---|\n|Demo|$1,000|" in document.markdown
    assert document.html == "<table></table>"
    assert "Demo\t$1,000" in document.text
    assert document.pages[0].page_no == 1
    assert document.pages[0].text == "|Trade|Price|\n|---|---|\n|Demo|$1,000|"


def test_extract_pages_falls_back_to_json_content(monkeypatch) -> None:
    def fake_convert(**kwargs) -> None:
        output_dir = Path(kwargs["output_dir"])
        (output_dir / "doc.json").write_text(
            json.dumps(
                {
                    "kids": [
                        {"page number": 1, "content": "First"},
                        {"page number": 1, "content": "Second"},
                    ]
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(
        "app.document_intake.odl_pdf.opendataloader_pdf.convert",
        fake_convert,
    )

    pages = extract_pages(b"pdf-bytes", hybrid=False)

    assert pages[0].page_no == 1
    assert pages[0].text == "First\nSecond"

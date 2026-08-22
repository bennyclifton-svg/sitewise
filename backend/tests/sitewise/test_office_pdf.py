from pathlib import Path
from subprocess import CalledProcessError

import pytest

from app.sitewise.office_pdf import (
    OfficeConversionError,
    _safe_source_name,
    convert_html_to_pdf,
    convert_office_to_pdf,
    html_to_pdf_bytes,
)


def test_convert_office_to_pdf_runs_isolated_soffice(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(list(command))
        source = Path(command[-1])
        source.with_suffix(".pdf").write_bytes(b"%PDF-1.7 office")
        return None

    monkeypatch.setattr("app.sitewise.office_pdf.subprocess.run", fake_run)
    monkeypatch.setattr("app.sitewise.office_pdf._soffice_command", lambda: "soffice")

    payload = convert_office_to_pdf(
        source_bytes=b"xlsx-bytes",
        filename="Cost_Plan_v02.draft.xlsx",
    )

    assert payload == b"%PDF-1.7 office"
    assert calls[0][0] == "soffice"
    assert "--convert-to" in calls[0]
    assert any(item.startswith("-env:UserInstallation=") for item in calls[0])
    assert calls[0][-1].endswith("Cost_Plan_v02_draft.xlsx")


def test_convert_html_to_pdf_uses_html_suffix(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_convert(*, source_bytes: bytes, filename: str) -> bytes:
        captured["filename"] = filename
        captured["body"] = source_bytes.decode("utf-8")
        return b"%PDF-html"

    monkeypatch.setattr("app.sitewise.office_pdf.convert_office_to_pdf", fake_convert)

    payload = convert_html_to_pdf(html="<html><body>Report</body></html>")

    assert payload == b"%PDF-html"
    assert captured["filename"].endswith(".html")
    assert "Report" in captured["body"]


def test_html_to_pdf_bytes_writes_a_pdf() -> None:
    payload = html_to_pdf_bytes(
        "<html><body><h1>Project Management Plan</h1><p>Issued scope.</p></body></html>"
    )

    assert payload.startswith(b"%PDF")
    assert len(payload) > 100


def test_convert_html_to_pdf_falls_back_when_soffice_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.sitewise.office_pdf.convert_office_to_pdf",
        lambda **_kwargs: (_ for _ in ()).throw(OfficeConversionError("missing")),
    )
    monkeypatch.setattr(
        "app.sitewise.office_pdf.html_to_pdf_bytes",
        lambda html: b"%PDF-html-fallback",
    )

    payload = convert_html_to_pdf(html="<html><body>Report</body></html>")

    assert payload == b"%PDF-html-fallback"


def test_safe_source_name_strips_windows_illegal_characters() -> None:
    assert (
        _safe_source_name("Request for Tender: Structural engineer.docx")
        == "Request_for_Tender_Structural_engineer.docx"
    )


def test_convert_office_to_pdf_rejects_unknown_suffix() -> None:
    with pytest.raises(OfficeConversionError, match="unsupported office source"):
        convert_office_to_pdf(source_bytes=b"nope", filename="notes.txt")


def test_convert_office_to_pdf_maps_soffice_failure(monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise CalledProcessError(1, ["soffice"])

    monkeypatch.setattr("app.sitewise.office_pdf.subprocess.run", boom)
    monkeypatch.setattr("app.sitewise.office_pdf._soffice_command", lambda: "soffice")

    with pytest.raises(OfficeConversionError, match="conversion failed"):
        convert_office_to_pdf(source_bytes=b"xlsx", filename="plan.xlsx")

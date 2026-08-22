"""Convert Word, Excel, and HTML to PDF with the host LibreOffice install."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

_WINDOWS_SOFFICE_PATHS = (
    Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
)
_CONVERTIBLE_SUFFIXES = {".docx", ".xlsx", ".html", ".htm"}


class OfficeConversionError(RuntimeError):
    pass


def convert_office_to_pdf(*, source_bytes: bytes, filename: str) -> bytes:
    source_name = _safe_source_name(filename)
    try:
        return _run_soffice_pdf(source_bytes=source_bytes, source_name=source_name)
    except OfficeConversionError:
        raise
    except OSError as exc:
        raise OfficeConversionError("LibreOffice conversion failed") from exc


def _run_soffice_pdf(*, source_bytes: bytes, source_name: str) -> bytes:
    with tempfile.TemporaryDirectory(prefix="sitewise-office-pdf-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        source_path = tmp_path / source_name
        source_path.write_bytes(source_bytes)
        profile_path = tmp_path / "lo-profile"
        profile_path.mkdir()
        try:
            subprocess.run(
                [
                    _soffice_command(),
                    "--headless",
                    "--norestore",
                    "--nolockcheck",
                    f"-env:UserInstallation={profile_path.resolve().as_uri()}",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(tmp_path),
                    str(source_path),
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
        except FileNotFoundError as exc:
            raise OfficeConversionError("LibreOffice is not installed") from exc
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise OfficeConversionError("LibreOffice conversion failed") from exc

        output_path = source_path.with_suffix(".pdf")
        if not output_path.exists():
            candidates = list(tmp_path.glob("*.pdf"))
            if not candidates:
                raise OfficeConversionError("LibreOffice produced no PDF")
            output_path = candidates[0]
        payload = output_path.read_bytes()
    if not payload.startswith(b"%PDF"):
        raise OfficeConversionError("LibreOffice produced an invalid PDF")
    return payload


def convert_html_to_pdf(*, html: str, filename: str = "document.html") -> bytes:
    source_name = Path(filename).name or "document.html"
    if Path(source_name).suffix.lower() not in {".html", ".htm"}:
        source_name = f"{source_name}.html"
    try:
        return convert_office_to_pdf(
            source_bytes=html.encode("utf-8"),
            filename=source_name,
        )
    except OfficeConversionError:
        return html_to_pdf_bytes(html)


def html_to_pdf_bytes(html: str) -> bytes:
    """Last-resort HTML PDF when LibreOffice and WeasyPrint are unavailable."""
    import fitz

    mediabox = fitz.paper_rect("a4")
    where = mediabox + (36, 36, -36, -36)
    story = fitz.Story(html=html)
    buffer = BytesIO()
    writer = fitz.DocumentWriter(buffer)
    more = True
    while more:
        device = writer.begin_page(mediabox)
        more, _placed = story.place(where)
        story.draw(device)
        writer.end_page()
    writer.close()
    payload = buffer.getvalue()
    if not payload.startswith(b"%PDF"):
        raise OfficeConversionError("HTML PDF fallback produced an invalid PDF")
    return payload


def _safe_source_name(filename: str) -> str:
    raw = Path(filename).name or "source.docx"
    suffix = Path(raw).suffix.lower()
    if suffix not in _CONVERTIBLE_SUFFIXES:
        raise OfficeConversionError(f"unsupported office source: {raw}")
    stem = re.sub(r"[^A-Za-z0-9]+", "_", Path(raw).stem).strip("_") or "source"
    return f"{stem}{suffix}"


def _soffice_command() -> str:
    for name in ("soffice", "soffice.exe"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in _WINDOWS_SOFFICE_PATHS:
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError("soffice")

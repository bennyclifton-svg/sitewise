from pathlib import Path

from ingest.extract import extract_document
from ingest.extractors.rtf import extract_rtf
from ingest.types import Classification, IngestPlan, ManifestEntry, ProjectContext


_SIMPLE_RTF = (
    r"{\rtf1\ansi\deff0"
    r"{\fonttbl{\f0 Times New Roman;}}"
    r"\f0\fs24 Inner West Local Environmental Plan 2022\par"
    r"This is clause 4.3 Height of buildings.\par"
    r"}"
)

_UNICODE_RTF = (
    r"{\rtf1\ansi\ansicpg1252\deff0"
    r"Zone R2 Low Density Residential \u8212? caf\'e9\par"
    r"}"
)


def _write(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_bytes(body.encode("latin-1"))
    return path


def test_extract_rtf_keeps_paragraph_text(tmp_path: Path) -> None:
    path = _write(tmp_path, "iwlep2022344.rtf", _SIMPLE_RTF)

    extracted = extract_rtf(path)

    assert "Inner West Local Environmental Plan 2022" in extracted.normalized_content
    assert "clause 4.3 Height of buildings" in extracted.normalized_content
    assert r"\par" not in extracted.normalized_content
    assert extracted.page_count == 1


def test_extract_rtf_decodes_unicode_and_hex_escapes(tmp_path: Path) -> None:
    path = _write(tmp_path, "zones.rtf", _UNICODE_RTF)

    extracted = extract_rtf(path)

    assert "Zone R2 Low Density Residential" in extracted.normalized_content
    assert "\u2014" in extracted.normalized_content
    assert "café" in extracted.normalized_content


def test_extract_rtf_empty_file_returns_empty_document(tmp_path: Path) -> None:
    path = _write(tmp_path, "empty.rtf", "")

    extracted = extract_rtf(path)

    assert extracted.normalized_content == ""
    assert extracted.page_count == 0


def test_extract_document_uses_rtf_extractor(tmp_path: Path) -> None:
    path = _write(tmp_path, "iwlep2022344.rtf", _SIMPLE_RTF)
    plan = IngestPlan(
        entry=ManifestEntry(
            absolute_path=path,
            relative_path="04-projects/demo/_inbox/iwlep2022344.rtf",
            project="demo",
            filename="iwlep2022344.rtf",
            extension=".rtf",
            size_bytes=path.stat().st_size,
        ),
        context=ProjectContext(
            project="demo",
            phase="design",
            source_type="project_evidence",
        ),
        classification=Classification(
            document_class="statutory_instrument",
            ingest_mode="full_text",
            document_metadata={},
        ),
        extractor="rtf",
        chunker="prose",
    )

    extracted = extract_document(plan)

    assert extracted is not None
    assert "Inner West Local Environmental Plan 2022" in extracted.normalized_content

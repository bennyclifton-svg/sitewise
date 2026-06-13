from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from tender.services import report

COMPARISON_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
QUOTE_A = uuid.UUID("22222222-2222-2222-2222-222222222222")
QUOTE_B = uuid.UUID("33333333-3333-3333-3333-333333333333")


def test_render_report_html_uses_language_phrases_glyphs_and_watermark() -> None:
    data = _report_data()
    language = report.load_report_language_yaml(_language_path())

    artifacts = report.assemble_report_artifacts(
        data,
        language=language,
        draft=True,
        pdf_renderer=lambda html: b"%PDF-1.4 fake",
    )

    assert 'class="report draft"' in artifacts.html
    assert "DRAFT" in artifacts.html
    assert "Allowance of $2,000 for selection" in artifacts.html
    assert "✓" in artifacts.html
    assert "◷" in artifacts.html
    assert "This report is information and document analysis only." in artifacts.html
    assert artifacts.pdf_bytes.startswith(b"%PDF")


def test_rebuild_preserves_narratives_and_regenerates_tables() -> None:
    language = report.load_report_language_yaml(_language_path())
    first = report.assemble_report_artifacts(
        _report_data(pc_amount_cents=200_000),
        language=language,
        draft=True,
        pdf_renderer=lambda html: b"%PDF first",
    )
    edited_markdown = first.markdown.replace(
        "This draft compares the submitted tender documents on a like-for-like basis.",
        "Operator edited summary.",
    ).replace("$2,000", "$9,999")

    rebuilt = report.assemble_report_artifacts(
        _report_data(pc_amount_cents=300_000),
        language=language,
        previous_markdown=edited_markdown,
        draft=True,
        pdf_renderer=lambda html: b"%PDF second",
    )

    assert "Operator edited summary." in rebuilt.markdown
    assert "$3,000" in rebuilt.markdown
    assert "$9,999" not in rebuilt.markdown


def test_excluded_phrase_only_renders_with_page_reference() -> None:
    language = report.load_report_language_yaml(_language_path())
    without_page = report.assemble_report_artifacts(
        _report_data(excluded_page=None),
        language=language,
        draft=True,
        pdf_renderer=lambda html: b"%PDF no-page",
    )
    with_page = report.assemble_report_artifacts(
        _report_data(excluded_page=4),
        language=language,
        draft=True,
        pdf_renderer=lambda html: b"%PDF page",
    )

    assert "Excluded" not in without_page.html
    assert "Excluded (stated, p. 4)" in with_page.html


def test_weasyprint_renderer_produces_nonzero_pdf_when_native_libs_available() -> None:
    try:
        pdf = report.render_pdf_bytes("<html><body><p>PDF smoke test</p></body></html>")
    except report.WeasyPrintUnavailable as exc:
        pytest.skip(str(exc))

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 100


def _report_data(
    *,
    pc_amount_cents: int = 200_000,
    excluded_page: int | None = None,
) -> report.ReportData:
    status = "excluded_explicit" if excluded_page is not None else "silent_ambiguous"
    evidence = {"page_refs": [{"page": excluded_page}]} if excluded_page is not None else {}
    return report.ReportData(
        comparison_id=COMPARISON_ID,
        project_title="Walsh Residence",
        context={"state": "NSW", "build_type": "new_build"},
        quotes=[
            report.ReportQuote(
                id=QUOTE_A,
                builder_name="A Homes",
                stated_total_cents=1_000_000_00,
            ),
            report.ReportQuote(
                id=QUOTE_B,
                builder_name="B Homes",
                stated_total_cents=950_000_00,
            ),
        ],
        ledgers=[
            {
                "builder_name": "B Homes",
                "cell_name": "Cooktop",
                "adjustment_cents": 300_000,
                "provenance": "benchmark:cooktop-mid",
            }
        ],
        matrix=[
            report.ReportMatrixCell(
                code="18.01",
                name="Cooktop",
                group="Appliances",
                statuses=[
                    report.ReportCellStatus(
                        quote_id=QUOTE_A,
                        status="included",
                        amount_cents=500_000,
                    ),
                    report.ReportCellStatus(
                        quote_id=QUOTE_B,
                        status="pc",
                        amount_cents=pc_amount_cents,
                    ),
                ],
            ),
            report.ReportMatrixCell(
                code="03.05",
                name="Retaining walls",
                group="Site works",
                statuses=[
                    report.ReportCellStatus(
                        quote_id=QUOTE_A,
                        status=status,
                        amount_cents=None,
                        evidence=evidence,
                    )
                ],
            ),
        ],
        flags=[
            report.ReportFlag(
                builder_name="B Homes",
                cell_name="Cooktop",
                flag_type="low_pc_allowance",
                severity="caution",
                headline="Cooktop allowance appears low",
                detail="Allowance is below the typical market range.",
                evidence={"benchmark_id": "cooktop-mid"},
            )
        ],
        questions=[
            "B Homes: Please confirm what product/range the cooktop allowance assumes."
        ],
    )


def _language_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "tender" / "report_language.yaml"

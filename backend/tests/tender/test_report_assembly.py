from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from tender.schemas import LedgerItem, MatrixQuoteTotal, QuoteLedgerResponse
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
    assert "Matrix total" in artifacts.html
    assert "$5,000" in artifacts.html
    assert "Variance" in artifacts.html
    assert "✓" in artifacts.html
    assert "◷" in artifacts.html
    assert "This report is information and document analysis only." in artifacts.html
    assert artifacts.pdf_bytes.startswith(b"%PDF")


def test_report_includes_recon_strip_non_comparable_and_ledger_appendix() -> None:
    language = report.load_report_language_yaml(_language_path())
    artifacts = report.assemble_report_artifacts(
        _report_data(non_comparable_b=True),
        language=language,
        draft=True,
        pdf_renderer=lambda html: b"%PDF recon",
    )

    assert "Stated (native)" in artifacts.html
    assert "Counted" in artifacts.html
    assert "Residual" in artifacts.html
    assert "Cost-plus" in artifacts.html
    assert "not directly comparable" in artifacts.html
    assert "Quote ledgers" in artifacts.html
    assert "Joinery package" in artifacts.html
    assert "reprint" in artifacts.html
    assert "Unexplained difference vs stated total" in artifacts.html
    assert "\u25d1" in artifacts.html
    assert "Cabinetry" in artifacts.html
    assert "Stated (native)" in artifacts.markdown
    assert "Quote ledgers" in artifacts.markdown


def test_mixed_glyph_is_registered() -> None:
    assert report.GLYPHS["mixed"] == "\u25d1"
    assert report.glyph_for_status("mixed") == "\u25d1"


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


def test_flat_report_language_rows_rebuild_nested_sections_and_lists() -> None:
    language = report._nested_language(
        {
            "report.section_titles.cover": "Cover",
            "report.section_titles.executive_summary": "Executive summary",
            "report.labels.builder": "Builder",
            "forbidden_terms.0000": "ripoff",
            "forbidden_terms.0001": "dodgy",
        }
    )

    assert report.language_value(language, "report.section_titles") == {
        "cover": "Cover",
        "executive_summary": "Executive summary",
    }
    assert report.language_value(language, "report.labels.builder") == "Builder"
    assert language["forbidden_terms"] == ["ripoff", "dodgy"]


def test_weasyprint_renderer_produces_nonzero_pdf_when_native_libs_available() -> None:
    try:
        pdf = report.render_pdf_bytes("<html><body><p>PDF smoke test</p></body></html>")
    except report.WeasyPrintUnavailable as exc:
        pytest.skip(str(exc))

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 100


def test_draft_assembly_allows_missing_pdf_when_weasyprint_unavailable() -> None:
    language = report.load_report_language_yaml(_language_path())

    def boom(_html: str) -> bytes:
        raise report.WeasyPrintUnavailable("GTK missing")

    artifacts = report.assemble_report_artifacts(
        _report_data(),
        language=language,
        draft=True,
        pdf_renderer=boom,
        require_pdf=False,
    )

    assert "DRAFT" in artifacts.html
    assert artifacts.markdown.startswith("#")
    assert artifacts.pdf_bytes == b""


def test_assembly_still_requires_pdf_by_default() -> None:
    language = report.load_report_language_yaml(_language_path())

    def boom(_html: str) -> bytes:
        raise report.WeasyPrintUnavailable("GTK missing")

    with pytest.raises(report.WeasyPrintUnavailable, match="GTK missing"):
        report.assemble_report_artifacts(
            _report_data(),
            language=language,
            draft=False,
            pdf_renderer=boom,
        )


def _report_data(
    *,
    pc_amount_cents: int = 200_000,
    excluded_page: int | None = None,
    non_comparable_b: bool = False,
) -> report.ReportData:
    status = "excluded_explicit" if excluded_page is not None else "silent_ambiguous"
    evidence = {"page_refs": [{"page": excluded_page}]} if excluded_page is not None else {}
    child = LedgerItem(
        figure_key="joinery-child",
        page_no=4,
        description_raw="Kitchen cabinets",
        amount_cents=80_000_00,
        amount_ex_gst_cents=72_727_27,
        role="line_item",
        counted_in_total=True,
    )
    duplicate = LedgerItem(
        figure_key="joinery-reprint",
        page_no=12,
        description_raw="Joinery package",
        amount_cents=120_000_00,
        role="category",
        is_rollup=True,
        counted_in_total=False,
        duplicate_of_id=QUOTE_A,
    )
    root = LedgerItem(
        figure_key="joinery",
        page_no=3,
        description_raw="Joinery package",
        amount_cents=120_000_00,
        amount_ex_gst_cents=109_090_91,
        role="category",
        is_rollup=True,
        counted_in_total=True,
        children=[child],
    )
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
                code="PT.CABINETRY",
                name="Cabinetry",
                group="Finishes",
                statuses=[
                    report.ReportCellStatus(
                        quote_id=QUOTE_A,
                        status="included",
                        amount_cents=500_000,
                    ),
                    report.ReportCellStatus(
                        quote_id=QUOTE_B,
                        status="mixed",
                        amount_cents=pc_amount_cents,
                    ),
                ],
            ),
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
        totals=[
            MatrixQuoteTotal(
                quote_id=QUOTE_A,
                computed_total_cents=500_000,
                stated_total_cents=1_000_000_00,
                stated_native_cents=1_000_000_00,
                residual_cents=0,
                stated_total_source="manual",
                delta_cents=-99_500_000,
                delta_ratio=0.995,
                reconciliation="mismatch",
            ),
            MatrixQuoteTotal(
                quote_id=QUOTE_B,
                computed_total_cents=pc_amount_cents,
                stated_total_cents=950_000_00,
                stated_native_cents=950_000_00,
                residual_cents=12_500_00,
                stated_total_source="manual",
                non_comparable=non_comparable_b,
                delta_cents=pc_amount_cents - 950_000_00,
                delta_ratio=(950_000_00 - pc_amount_cents) / 950_000_00,
                reconciliation="mismatch",
            ),
        ],
        quote_ledgers=[
            QuoteLedgerResponse(
                quote_id=QUOTE_A,
                builder_name="A Homes",
                stated_total_cents=1_000_000_00,
                stated_basis="inc",
                status="residual",
                residual_cents=5_000_00,
                computed_ex_gst_cents=904_545_45,
                items=[
                    root,
                    duplicate,
                    LedgerItem(
                        figure_key="residual",
                        description_raw="Unexplained difference vs stated total",
                        amount_cents=5_000_00,
                        counted_in_total=True,
                    ),
                ],
            )
        ],
    )


def _language_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "tender" / "report_language.yaml"

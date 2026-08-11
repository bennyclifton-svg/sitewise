from io import BytesIO

import fitz
import pytest
from docx import Document
from docx.oxml.ns import qn
from markdown_it import MarkdownIt

from app.projects.artefact_blocks import (
    materialize_block_identity,
    strip_block_markers,
)
from app.sitewise import artifact_exports
from app.sitewise.artifact_exports import (
    _consultants_table_weights,
    render_artifact_export,
)

MARKDOWN = """# Project Management Plan

## Snapshot

The project brief sets the issued scope. [1]

```pmp-decision
{"id":"delivery","label":"Delivery model","selected":"traditional","options":[{"value":"traditional","label":"Traditional tender"}],"rationale":"Client direction"}
```

## Citation key

[1] `brief.pdf`

## Trace & QA

**Inputs to resolve**
- Tender date
"""


def _document_text(payload: bytes) -> str:
    document = Document(BytesIO(payload))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    headers = [
        paragraph.text
        for section in document.sections
        for paragraph in section.header.paragraphs
    ]
    cells = [
        cell.text
        for table in document.tables
        for row in table.rows
        for cell in row.cells
    ]
    return "\n".join([*headers, *paragraphs, *cells])


def test_docx_export_keeps_issue_content_and_selected_decisions_without_trace() -> None:
    payload = render_artifact_export(
        MARKDOWN,
        export_format="docx",
        project_title="Walsh Renovation",
        artifact_title="Project Management Plan",
        version=3,
    )

    assert payload.startswith(b"PK")
    text = _document_text(payload)
    assert "Walsh Renovation" in text
    assert "Traditional tender" in text
    assert "Citation key" in text
    assert "brief.pdf" in text
    assert "Trace & QA" not in text
    assert "Tender date" not in text

    document = Document(BytesIO(payload))
    table = document.tables[0]
    layout = table._tbl.tblPr.first_child_found_in("w:tblLayout")
    assert layout is not None
    assert layout.get(qn("w:type")) == "fixed"
    assert all(
        int(column.get(qn("w:w"))) > 0 for column in table._tbl.tblGrid.gridCol_lst
    )
    assert table.rows[0]._tr.get_or_add_trPr().find(qn("w:tblHeader")) is not None
    assert "NUMPAGES" in document.sections[0].footer._element.xml


@pytest.mark.parametrize(
    (
        "artifact_title",
        "workflow_type",
        "section_title",
        "header_cells",
        "row_cells",
    ),
    [
        (
            "Project Management Plan",
            "create_pmp",
            "Project Summary",
            ("Project", "Walsh 2"),
            ("Address", "42 Hargrave Street, Paddington"),
        ),
        (
            "Request for Proposal - Structural engineer",
            "consultant_procurement_structural_engineer",
            "Information register",
            ("Document number", "Title"),
            ("420", "Structural details"),
        ),
        (
            "Request for Tender - Mechanical",
            "trade_rft_mechanical",
            "Price schedule",
            ("Price item", "Amount"),
            ("Tender total", "$125,000"),
        ),
    ],
    ids=("pmp", "rfp", "rft"),
)
def test_materialized_tables_round_trip_through_gfm_and_docx_export(
    artifact_title: str,
    workflow_type: str,
    section_title: str,
    header_cells: tuple[str, str],
    row_cells: tuple[str, str],
) -> None:
    source = (
        f"# {artifact_title}\n\n"
        f"## {section_title}\n\n"
        f"| {header_cells[0]} | {header_cells[1]} |\n"
        "| --- | --- |\n"
        f"| {row_cells[0]} | {row_cells[1]} |\n"
    )
    stamped = materialize_block_identity(source, actor_source="ai")

    assert strip_block_markers(stamped.markdown) == source
    html = MarkdownIt("commonmark", {"html": False}).enable("table").render(
        stamped.markdown
    )
    assert html.count("<table>") == 1
    assert html.count("<th>") == 2
    assert html.count("<td>") == 2
    assert "clerk:block" not in html

    payload = render_artifact_export(
        stamped.markdown,
        export_format="docx",
        project_title="Walsh 2",
        artifact_title=artifact_title,
        version=1,
        workflow_type=workflow_type,
    )

    document = Document(BytesIO(payload))
    assert len(document.tables) == 1
    text = _document_text(payload)
    assert header_cells[1] in text
    assert row_cells[0] in text
    assert row_cells[1] in text
    assert "clerk:block" not in text


def test_pdf_export_smoke_when_native_weasyprint_libraries_are_available() -> None:
    stamped = materialize_block_identity(MARKDOWN, actor_source="ai")
    try:
        payload = render_artifact_export(
            stamped.markdown,
            export_format="pdf",
            project_title="Walsh Renovation",
            artifact_title="Project Management Plan",
            version=3,
        )
    except (ImportError, OSError, RuntimeError) as exc:
        pytest.skip(str(exc))

    assert payload.startswith(b"%PDF")
    assert len(payload) > 100
    with fitz.open(stream=payload, filetype="pdf") as document:
        text = "\n".join(page.get_text() for page in document)
    assert "The project brief sets the issued scope." in text
    assert "clerk:block" not in text


def test_consultants_table_weights_favour_status_and_citation() -> None:
    class _Cell:
        def __init__(self, text: str) -> None:
            self._text = text

        def get_text(self, *_args, **_kwargs) -> str:
            return self._text

    class _Row:
        def __init__(self, labels: list[str]) -> None:
            self._cells = [_Cell(label) for label in labels]

        def find_all(self, *_args, **_kwargs) -> list[_Cell]:
            return self._cells

    weights = _consultants_table_weights(
        [
            _Row(
                [
                    "Discipline",
                    "Firm",
                    "Fee",
                    "Status",
                    "Citation",
                ]
            )
        ],
        5,
    )

    assert weights == [14, 24, 8, 26, 28]
    assert weights[3] > weights[0]
    assert weights[4] > weights[2]
    assert _consultants_table_weights([_Row(["Item", "Status"])], 2) is None


def test_pdf_renderer_never_receives_internal_block_markers(monkeypatch) -> None:
    source = """# Request for Proposal

## Information register

| Document | Title |
| --- | --- |
| 420 | Structural details |
"""
    stamped = materialize_block_identity(source, actor_source="ai")
    rendered: dict[str, str] = {}

    def capture_pdf(html: str) -> bytes:
        rendered["html"] = html
        return b"%PDF-test"

    monkeypatch.setattr(artifact_exports, "_pdf_bytes", capture_pdf)

    payload = render_artifact_export(
        stamped.markdown,
        export_format="pdf",
        project_title="Walsh 2",
        artifact_title="Request for Proposal",
        version=1,
        workflow_type="consultant_procurement_structural_engineer",
    )

    assert payload == b"%PDF-test"
    assert "<table>" in rendered["html"]
    assert "Structural details" in rendered["html"]
    assert "clerk:block" not in rendered["html"]

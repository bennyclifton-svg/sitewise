from io import BytesIO

import pytest
from docx import Document
from docx.oxml.ns import qn

from app.sitewise.artifact_exports import render_artifact_export

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


def test_pdf_export_smoke_when_native_weasyprint_libraries_are_available() -> None:
    try:
        payload = render_artifact_export(
            MARKDOWN,
            export_format="pdf",
            project_title="Walsh Renovation",
            artifact_title="Project Management Plan",
            version=3,
        )
    except (ImportError, OSError, RuntimeError) as exc:
        pytest.skip(str(exc))

    assert payload.startswith(b"%PDF")
    assert len(payload) > 100

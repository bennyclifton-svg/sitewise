from datetime import date
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import fitz
import pytest

from app.sitewise.artifact_exports import _document_html, _docx_bytes, _markdown_html
from app.sitewise.office_pdf import html_to_pdf_bytes
from tender.review_schemas import ReviewSelection
from tender.services.report import load_report_language_yaml
from tender.services.review_facts import (
    numbered_facts,
    reconcile_submission,
    validate_selection,
)
from tender.services.review_render import render_review
from tender.services.review_layout import validate_review_layout


def review_example(profile: str, firms: int = 3):
    quotes = [
        {"id": str(i), "name": name}
        for i, name in enumerate(["Alder", "Banksia", "Cedar"][:firms])
    ]
    count = {"consultant": 3, "trade": 16, "head_contractor": 24}[profile]
    documents = []
    for quote in quotes:
        facts = [
            {
                "page_no": 1,
                "label": "Offered total",
                "excerpt": "Total $110,000.00 including GST",
                "kind": "total",
                "amount_printed": "$110,000.00",
                "tax_basis": "inc",
                "currency": "AUD",
            }
        ]
        facts += [
            {
                "page_no": 2,
                "label": f"Stage {i + 1}",
                "excerpt": f"Stage {i + 1} includes design and documentation",
                "kind": "component",
                "amount_printed": f"${(i + 1) * 1000:,.2f}",
                "tax_basis": "ex",
                "currency": "AUD",
            }
            for i in range(count)
        ]
        facts += [
            {
                "page_no": 3,
                "label": label,
                "excerpt": excerpt,
                "kind": kind,
                "amount_printed": None,
                "tax_basis": "unknown",
                "currency": "AUD",
            }
            for label, excerpt, kind in [
                (
                    "Site visits",
                    "Includes three site visits; additional visits by agreement",
                    "qualification",
                ),
                (
                    "Client supplied equipment",
                    "Client supplies equipment; installation included",
                    "owner_supply",
                ),
                ("Delivery", "Six weeks after the approved design", "programme"),
            ]
        ]
        documents.append(
            {
                "id": quote["id"],
                "quote_id": quote["id"],
                "filename": quote["name"] + ".pdf",
                "path": "/quotes/" + quote["name"] + ".pdf",
                "facts": facts,
                "page_count": 3,
            }
        )
    facts = numbered_facts(documents)
    selection = ReviewSelection(
        conclusion="single_quote" if firms == 1 else "clarification_required",
        preferred_quote_id=None,
        recommendation_fact_ids=["f1:0"],
        findings=[
            {
                "issue": issue,
                "fact_ids": [f"f{int(q['id']) + 1}:{count + 1 + i}" for q in quotes],
            }
            for i, issue in enumerate(["scope", "exclusion", "programme"])
        ],
        matrix=[
            {
                "label": f"Stage {i + 1}",
                "cells": [
                    {"quote_id": q["id"], "fact_ids": [f"f{int(q['id']) + 1}:{i + 1}"]}
                    for q in quotes
                ],
            }
            for i in range(count)
        ],
    )
    calculations = {
        q["id"]: reconcile_submission(
            [f for f in facts if f["quote_id"] == q["id"]], review_date=date(2026, 9, 6)
        )
        for q in quotes
    }
    language = load_report_language_yaml(
        Path(__file__).parents[3] / "data/tender/report_language.yaml"
    )
    validate_selection(selection, facts, [q["id"] for q in quotes], profile)
    return dict(
        package="Structural engineering"
        if profile == "consultant"
        else "Building works",
        profile=profile,
        review_date="2026-09-06",
        quotes=quotes,
        documents=documents,
        facts=facts,
        selection=selection,
        calculations=calculations,
        language=language,
    )


@pytest.mark.parametrize(
    ("profile", "pages"), [("consultant", 1), ("trade", 2), ("head_contractor", 3)]
)
def test_report_profiles_use_existing_markdown_word_pdf_exports(profile, pages):
    markdown = render_review(**review_example(profile))
    validate_review_layout(markdown, profile)
    assert "[1]" in markdown and "Citation key" in markdown
    assert markdown.count("<!-- pagebreak -->") == pages - 1
    body = _markdown_html(markdown)
    pdf = html_to_pdf_bytes(
        _document_html(
            body,
            project_title="Test project",
            artifact_title="Quote review",
            version=1,
            compact=True,
        )
    )
    with fitz.open(stream=pdf, filetype="pdf") as document:
        assert len(document) == pages
        assert "Citation key" in document[-1].get_text()
    word = _docx_bytes(
        body,
        project_title="Test project",
        artifact_title="Quote review",
        version=1,
        compact=True,
    )
    with ZipFile(BytesIO(word)) as archive:
        assert archive.read("word/document.xml").count(b'w:type="page"') == pages - 1


def test_single_submission_keeps_fee_table_without_inventing_a_ranking():
    markdown = render_review(**review_example("consultant", firms=1))
    assert "Only one firm has submitted" in markdown
    assert "Fee comparison" in markdown
    assert "| Stage 1 | $1,000.00 [1] |" in markdown


def test_matrix_rejects_cross_firm_or_repeated_evidence():
    example = review_example("consultant")
    selection = example["selection"]
    selection.matrix[1].cells[0].fact_ids = selection.matrix[0].cells[0].fact_ids
    with pytest.raises(ValueError, match="twice"):
        validate_selection(selection, example["facts"], ["0", "1", "2"], "consultant")
    selection.matrix[1].cells[0].fact_ids = ["f2:2"]
    with pytest.raises(ValueError, match="another firm"):
        validate_selection(selection, example["facts"], ["0", "1", "2"], "consultant")

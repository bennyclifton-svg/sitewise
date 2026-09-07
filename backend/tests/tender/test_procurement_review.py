from datetime import date

import fitz
import pytest

from tender.services.pdf import extract_native_pages
from tender.services.review_facts import (
    parse_printed_money,
    validate_extraction,
    reconcile_submission,
)
from tender.review_schemas import ReviewExtraction


@pytest.mark.parametrize(
    ("printed", "expected"),
    [
        ("$1,234.56", 123456),
        ("-$100.00", -10000),
        ("($42.50)", -4250),
        ("$0", 0),
        ("$9,5556.80", None),
        ("15%", None),
        ("1.234,56", None),
    ],
)
def test_money_preserves_malformed_figures(printed, expected):
    assert parse_printed_money(printed) == expected


def test_native_pdf_accounts_for_blank_and_image_only_pages():
    document = fitz.open()
    document.new_page().insert_text((50, 50), "Fee $1,200.00")
    document.new_page()
    pages = extract_native_pages(document.tobytes())
    assert [page.page_no for page in pages] == [1, 2]
    assert "$1,200.00" in pages[0].text
    assert pages[1].text == ""


def test_extraction_rejects_missing_pages_and_invented_citations():
    result = ReviewExtraction(
        coverage=[{"page_no": 1, "readable": True, "blank": False}], facts=[]
    )
    with pytest.raises(ValueError, match="coverage"):
        validate_extraction(result, {1: "fee", 2: "programme"}, set())
    result = ReviewExtraction(
        coverage=[{"page_no": 1, "readable": True, "blank": False}],
        facts=[
            {
                "page_no": 1,
                "label": "Fee",
                "excerpt": "Invented fee $99",
                "kind": "component",
                "amount_printed": "$99",
            }
        ],
    )
    with pytest.raises(ValueError, match="excerpt"):
        validate_extraction(result, {1: "Fee $100"}, set())


def test_supporting_document_totals_are_not_added_to_contract_total():
    facts = [
        {
            "id": "a",
            "kind": "total",
            "amount_cents": 110000,
            "tax_basis": "inc",
            "currency": "AUD",
            "document_id": "main",
            "label": "Total",
        },
        {
            "id": "b",
            "kind": "total",
            "amount_cents": 100000,
            "tax_basis": "ex",
            "currency": "AUD",
            "document_id": "schedule",
            "label": "Total",
        },
        {
            "id": "c",
            "kind": "allowance",
            "amount_cents": 20000,
            "tax_basis": "ex",
            "currency": "AUD",
            "document_id": "main",
            "label": "Allowance",
        },
    ]
    result = reconcile_submission(facts, review_date=date(2026, 9, 6))
    assert result["headline_cents"] == 110000
    assert result["headline_basis"] == "inc"
    assert not result["conflicting_totals"]


def test_conflicting_revision_totals_require_clarification():
    facts = [
        {
            "id": str(index),
            "kind": "total",
            "amount_cents": value,
            "tax_basis": "inc",
            "currency": "AUD",
            "document_id": str(index),
            "label": "Total",
        }
        for index, value in enumerate([10000, 12000])
    ]
    assert reconcile_submission(facts, review_date=date(2026, 9, 6))[
        "conflicting_totals"
    ]

from datetime import date

from tender.review_schemas import ReviewExtraction, ReviewSelection
from tender.llm.review_client import selection_schema
from tender.services.review_facts import (
    missing_amounts,
    numbered_facts,
    reconcile_submission,
)


def test_malformed_price_is_captured_but_never_treated_as_valid_money():
    extraction = ReviewExtraction(
        coverage=[{"page_no": 3, "readable": True, "blank": False}],
        facts=[
            {
                "page_no": 3,
                "label": "Handrail",
                "excerpt": "Handrail $9,5556.80",
                "kind": "allowance",
                "amount_printed": "$9,5556.80",
            }
        ],
    )
    assert missing_amounts(extraction, {3: "Handrail $9,5556.80"}) == []
    facts = numbered_facts(
        [{"id": "doc", "quote_id": "firm", "facts": extraction.model_dump()["facts"]}]
    )
    assert facts[0]["amount_cents"] is None
    assert reconcile_submission(facts, review_date=date(2026, 9, 6))[
        "malformed_fact_ids"
    ] == ["f1:0"]


def test_summary_continuation_excludes_detail_and_tax_without_adding_margin_twice():
    def fact(page, label, amount, kind="component", rollup=False, basis="ex"):
        return {
            "page_no": page,
            "label": label,
            "excerpt": f"{label} {amount}",
            "amount_printed": amount,
            "kind": kind,
            "is_rollup": rollup,
            "tax_basis": basis,
            "currency": "AUD",
        }

    facts = numbered_facts(
        [
            {
                "id": "doc",
                "quote_id": "firm",
                "facts": [
                    fact(1, "Repeated detailed work", "$100.00"),
                    fact(3, "Structure", "$100.00", rollup=True),
                    fact(3, "Envelope", "$200.00", rollup=True),
                    fact(4, "Completion", "$30.00"),
                    fact(4, "Sub Total", "$379.50", "subtotal"),
                    fact(4, "GST", "$37.95", basis="unknown"),
                    fact(4, "Total", "$417.45", "total", basis="inc"),
                ],
            }
        ]
    )
    result = reconcile_submission(facts, review_date=date(2026, 9, 6))
    assert len(result["component_fact_ids"]) == 3
    assert result["component_sum_cents"] == 33000
    assert result["residual_cents"] == 4950
    assert result["apparent_uplift_percent"] == "15.00"
    assert result["headline_cents"] == 41745


def test_source_references_are_constrained_at_the_provider_boundary():
    shape = selection_schema(ReviewSelection, ["f1:0", "f2:0"])
    assert shape["$defs"]["SourceReference"]["enum"] == ["f1:0", "f2:0"]
    for model in (
        shape,
        shape["$defs"]["ReviewFinding"],
        shape["$defs"]["ReviewMatrixCell"],
    ):
        field = model["properties"].get(
            "fact_ids", model["properties"].get("recommendation_fact_ids")
        )
        assert field["items"] == {"$ref": "#/$defs/SourceReference"}


def test_explicit_summary_basis_identifies_unmarked_category_totals():
    def fact(page, label, amount=None, kind="component", basis="ex"):
        return {
            "page_no": page,
            "label": label,
            "excerpt": label,
            "amount_printed": amount,
            "kind": kind,
            "tax_basis": basis,
            "currency": "AUD",
            "is_rollup": False,
        }

    facts = numbered_facts(
        [
            {
                "id": "doc",
                "quote_id": "firm",
                "facts": [
                    fact(1, "Detailed structural materials", "$100.00"),
                    fact(
                        3,
                        "Category totals are presented exclusive of GST and exclude the Builder's Margin",
                        kind="pricing_basis",
                    ),
                    fact(3, "Structure", "$100.00"),
                    fact(3, "Envelope", "$200.00"),
                    fact(4, "Completion", "$30.00"),
                    fact(4, "Total", "$417.45", kind="total", basis="inc"),
                ],
            }
        ]
    )
    result = reconcile_submission(facts, review_date=date(2026, 9, 6))
    assert result["component_sum_cents"] == 33000
    assert result["residual_cents"] == 4950
    assert len(result["component_fact_ids"]) == 3


def test_quoted_gst_reconciles_the_printed_exclusive_and_inclusive_totals():
    facts = numbered_facts(
        [
            {
                "id": "doc",
                "quote_id": "firm",
                "facts": [
                    {
                        "page_no": 1,
                        "kind": "total",
                        "label": "Quote Total",
                        "tax_basis": "ex",
                        "currency": "AUD",
                        "amount_printed": "$3,224,995.38",
                    },
                    {
                        "page_no": 1,
                        "kind": "pricing_basis",
                        "label": "Tax (GST)",
                        "parent_label": "Quote Total",
                        "tax_basis": "unknown",
                        "currency": "AUD",
                        "amount_printed": "$322,499.62",
                    },
                    {
                        "page_no": 1,
                        "kind": "total",
                        "label": "Total",
                        "tax_basis": "inc",
                        "currency": "AUD",
                        "amount_printed": "$3,547,495.00",
                    },
                ],
            }
        ]
    )
    result = reconcile_submission(facts, review_date=date(2026, 9, 6))
    assert result["headline_cents"] == 354749500
    assert not result["conflicting_totals"]

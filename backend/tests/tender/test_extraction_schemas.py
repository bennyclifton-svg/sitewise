import pytest
from pydantic import ValidationError

from tender.schemas import ExtractedLineItem, ExtractionStructuredOutput, ProjectContext


def test_project_context_matches_prd_and_normalizes_budget() -> None:
    context = _context(target_budget_cents="$850,000")

    assert context.context_version == 1
    assert context.target_budget_cents == 85000000


def test_project_context_rejects_unknown_soil_class() -> None:
    with pytest.raises(ValidationError):
        _context(soil_class="ZZ")


def test_extraction_output_normalizes_currency_text_to_integer_cents() -> None:
    output = ExtractionStructuredOutput.model_validate(
        {
            "line_items": [
                {
                    "page_no": 1,
                    "description_raw": "Kitchen PC allowance",
                    "rate_cents": "$1,200.50",
                    "amount_cents": "$12,345.67",
                    "item_status": "pc_allowance",
                    "allowance_cents": "$12,345.67",
                    "extraction_confidence": 0.91,
                    "figure_key": "p1-1",
                    "role": "pc_allowance",
                    "gst_basis": "inc",
                    "printed_text": "$12,345.67",
                }
            ],
            "page_subtotals": [
                {
                    "page_no": 1,
                    "label": "Subtotal",
                    "amount_cents": "$12,345.67",
                    "confidence": 0.9,
                }
            ],
            "quote_total_cents": "$12,345.67",
        }
    )

    assert output.line_items[0].rate_cents == 120050
    assert output.line_items[0].amount_cents == 1234567
    assert output.line_items[0].allowance_cents == 1234567
    assert output.page_subtotals[0].amount_cents == 1234567
    assert output.quote_total_cents == 1234567


def test_line_item_confidence_is_bounded() -> None:
    with pytest.raises(ValidationError):
        ExtractedLineItem.model_validate(
            {
                "page_no": 1,
                "description_raw": "Bad confidence",
                "item_status": "included",
                "extraction_confidence": 1.1,
                "figure_key": "p1-1",
                "role": "contract_component",
                "printed_text": "$0.00",
            }
        )


def test_extracted_line_item_accepts_figure_tree_fields() -> None:
    item = ExtractedLineItem.model_validate(
        {
            "page_no": 10,
            "description_raw": "Demolition",
            "amount_cents": 15912320,
            "figure_key": "p10-t1-r3",
            "parent_figure_key": None,
            "role": "contract_component",
            "gst_basis": "inc",
            "is_rollup": True,
            "duplicate_of_figure_key": None,
            "printed_text": "$159,123.20",
        }
    )
    assert item.figure_key == "p10-t1-r3"
    assert item.role == "contract_component"
    assert item.is_rollup is True
    assert item.printed_text == "$159,123.20"
    assert item.item_status is None


def test_extracted_line_item_rejects_bogus_role() -> None:
    with pytest.raises(ValidationError):
        ExtractedLineItem.model_validate(
            {
                "page_no": 1,
                "description_raw": "Bad role",
                "figure_key": "p1-1",
                "role": "bogus",
                "printed_text": "$100.00",
            }
        )


def _context(**overrides: object) -> ProjectContext:
    data = {
        "state": "NSW",
        "region": "metro",
        "build_type": "renovation",
        "dwelling_class": "class_1a",
        "storeys": 2,
        "soil_class": "H2",
        "slope_class": "steep",
        "bal_rating": "none",
        "spec_level": "mid",
    }
    data.update(overrides)
    return ProjectContext.model_validate(data)


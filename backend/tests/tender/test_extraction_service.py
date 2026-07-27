from typing import Any

from tender.llm.client import LLMExtractionResponse
from tender.schemas import ProjectContext, TenderDocumentPage
from tender.services.extraction import (
    extract_line_items,
    merge_window_figures,
    missing_census_tokens,
    window_pages,
)
from tender.services.census import census_page
from tender.schemas import ExtractionStructuredOutput
from tests.conftest import run_async


def test_window_pages_splits_with_overlap() -> None:
    pages = [_page(n, f"page {n} $1.00") for n in range(1, 8)]
    windows = window_pages(pages, size=4, overlap=1)
    assert [ [p.page_no for p in w] for w in windows ] == [
        [1, 2, 3, 4],
        [4, 5, 6, 7],
    ]


def test_merge_window_figures_prefers_later_window() -> None:
    early = ExtractionStructuredOutput.model_validate(
        {
            "line_items": [
                _line("Old", page_no=4, amount_cents=100, figure_key="p4-1"),
            ]
        }
    )
    late = ExtractionStructuredOutput.model_validate(
        {
            "line_items": [
                _line("New", page_no=4, amount_cents=100, figure_key="p4-1"),
            ]
        }
    )
    merged = merge_window_figures([early, late])
    assert len(merged) == 1
    assert merged[0].description_raw == "New"


def test_census_diff_triggers_exactly_one_reextract() -> None:
    client = FakeLLMClient(
        {
            "line_items": [
                _line("Site costs", page_no=1, amount_cents=10000, figure_key="p1-1"),
            ],
            "page_subtotals": [],
            "quote_total_cents": 30000,
        },
        reextract={
            "line_items": [
                _line("Site costs", page_no=1, amount_cents=10000, figure_key="p1-1"),
                _line("Retaining", page_no=1, amount_cents=20000, figure_key="p1-2"),
            ],
            "page_subtotals": [],
            "quote_total_cents": 30000,
        },
    )
    # Page text contains both $ amounts; first LLM call only returns one.
    result = run_async(
        extract_line_items(
            pages=[_page(1, "Site costs $100.00 Retaining $200.00 Total $300.00")],
            context=_context(),
            llm_client=client,
            stated_total_cents=30000,
        )
    )
    assert client.call_count >= 2
    assert client.reextract_calls == 1
    assert len(result.line_items) == 2


def test_extract_line_items_auto_passes_reconciled_high_confidence_items() -> None:
    client = FakeLLMClient(
        {
            "line_items": [
                _line("Site costs", page_no=1, amount_cents=10000, figure_key="p1-1"),
                _line("Retaining walls", page_no=1, amount_cents=20000, figure_key="p1-2"),
            ],
            "page_subtotals": [],
            "quote_total_cents": 30000,
        }
    )

    result = run_async(
        extract_line_items(
            pages=[_page(1, "Site $100.00 Retaining $200.00 Total $300.00")],
            context=_context(),
            llm_client=client,
            stated_total_cents=30000,
            gst_treatment="inclusive",
        )
    )

    assert result.ledger is not None
    assert result.ledger.status == "reconciled"
    assert [item.qa_state for item in result.line_items] == ["auto_pass", "auto_pass"]


def test_quote_residual_marks_items_for_review() -> None:
    client = FakeLLMClient(
        {
            "line_items": [
                _line("Site costs", page_no=1, amount_cents=30000, figure_key="p1-1")
            ],
            "page_subtotals": [],
            "quote_total_cents": 30000,
        }
    )

    result = run_async(
        extract_line_items(
            pages=[_page(1, "Site costs $300.00")],
            context=_context(),
            llm_client=client,
            stated_total_cents=50000,
            gst_treatment="inclusive",
        )
    )

    assert result.ledger is not None
    assert result.ledger.status == "residual"
    assert any(flag.flag_type == "unreconciled_residual" for flag in result.flags)
    assert result.line_items[0].qa_state == "needs_review"


def test_low_confidence_item_is_gated_without_arithmetic_flag() -> None:
    client = FakeLLMClient(
        {
            "line_items": [
                _line(
                    "Unclear handwritten note",
                    page_no=1,
                    amount_cents=1000,
                    figure_key="p1-1",
                    confidence=0.7,
                )
            ],
            "page_subtotals": [],
            "quote_total_cents": 1000,
        }
    )

    result = run_async(
        extract_line_items(
            pages=[_page(1, "note $10.00")],
            context=_context(),
            llm_client=client,
            stated_total_cents=1000,
            gst_treatment="inclusive",
        )
    )

    assert not any(flag.flag_type == "arithmetic_inconsistency" for flag in result.flags)
    assert result.line_items[0].qa_state == "needs_review"
    assert result.line_items[0].issues == ("low_extraction_confidence",)


def test_missing_census_tokens_helper() -> None:
    text = "A $10.00 B $20.00"
    tokens = census_page(text, 1)
    items = [
        ExtractionStructuredOutput.model_validate(
            {"line_items": [_line("A", page_no=1, amount_cents=1000, figure_key="p1-1")]}
        ).line_items[0]
    ]
    missing = missing_census_tokens(tokens, items)
    assert [t.cents for t in missing] == [2000]


class FakeLLMClient:
    def __init__(
        self,
        data: dict[str, Any],
        *,
        reextract: dict[str, Any] | None = None,
    ) -> None:
        self.data = data
        self.reextract = reextract
        self.schema: dict[str, Any] = {}
        self.call_count = 0
        self.reextract_calls = 0

    async def extract(
        self,
        document_pages: list[TenderDocumentPage],
        schema: dict[str, Any],
        context: ProjectContext,
        **kwargs: Any,
    ) -> LLMExtractionResponse:
        self.schema = schema
        self.call_count += 1
        if kwargs.get("reextract_hint") and self.reextract is not None:
            self.reextract_calls += 1
            payload = self.reextract
        else:
            payload = self.data
        return LLMExtractionResponse(
            data=payload,
            model="fake-model",
            prompt_version="0.2.0",
            request_id="req-1",
        )


def _line(
    description: str,
    *,
    page_no: int,
    amount_cents: int,
    figure_key: str,
    confidence: float = 0.95,
    role: str = "contract_component",
) -> dict[str, Any]:
    dollars = amount_cents / 100
    return {
        "page_no": page_no,
        "description_raw": description,
        "amount_cents": amount_cents,
        "item_status": "included",
        "extraction_confidence": confidence,
        "figure_key": figure_key,
        "role": role,
        "gst_basis": "inc",
        "printed_text": f"${dollars:,.2f}",
    }


def _page(page_no: int = 1, text: str = "Quote text") -> TenderDocumentPage:
    return TenderDocumentPage(
        document_id="doc-1", page_no=page_no, text_content=text
    )


def _context() -> ProjectContext:
    return ProjectContext.model_validate(
        {
            "state": "NSW",
            "region": "metro",
            "build_type": "new_build",
            "dwelling_class": "class_1a",
            "storeys": 1,
            "soil_class": "M",
            "slope_class": "flat",
            "bal_rating": "none",
            "spec_level": "builder_base",
        }
    )

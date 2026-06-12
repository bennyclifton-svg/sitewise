from typing import Any

from tender.llm.client import LLMExtractionResponse
from tender.schemas import ProjectContext, TenderDocumentPage
from tender.services.extraction import extract_line_items
from tests.conftest import run_async


def test_extract_line_items_auto_passes_reconciled_high_confidence_items() -> None:
    client = FakeLLMClient(
        {
            "line_items": [
                _line("Site costs", page_no=1, amount_cents=10000),
                _line("Retaining walls", page_no=1, amount_cents=20000),
            ],
            "page_subtotals": [
                {"page_no": 1, "label": "Subtotal", "amount_cents": 30000, "confidence": 0.9}
            ],
            "quote_total_cents": 30000,
        }
    )

    result = run_async(
        extract_line_items(
            pages=[_page()],
            context=_context(),
            llm_client=client,
            stated_total_cents=30000,
        )
    )

    assert result.flags == ()
    assert [item.qa_state for item in result.line_items] == ["auto_pass", "auto_pass"]
    assert "line_items" in client.schema["properties"]


def test_page_reconciliation_mismatch_marks_page_items_for_review() -> None:
    client = FakeLLMClient(
        {
            "line_items": [
                _line("Site costs", page_no=2, amount_cents=10000),
                _line("Retaining walls", page_no=2, amount_cents=20000),
                _line("Kitchen", page_no=3, amount_cents=40000),
            ],
            "page_subtotals": [
                {"page_no": 2, "label": "Subtotal", "amount_cents": 40000, "confidence": 0.9}
            ],
            "quote_total_cents": 70000,
        }
    )

    result = run_async(
        extract_line_items(pages=[_page()], context=_context(), llm_client=client)
    )

    assert len(result.flags) == 1
    assert result.flags[0].scope == "page"
    assert result.flags[0].page_no == 2
    assert result.line_items[0].qa_state == "needs_review"
    assert "page_reconciliation_mismatch" in result.line_items[0].issues
    assert result.line_items[2].qa_state == "auto_pass"


def test_quote_reconciliation_mismatch_marks_all_items_for_review() -> None:
    client = FakeLLMClient(
        {
            "line_items": [_line("Site costs", page_no=1, amount_cents=30000)],
            "page_subtotals": [],
        }
    )

    result = run_async(
        extract_line_items(
            pages=[_page()],
            context=_context(),
            llm_client=client,
            stated_total_cents=50000,
        )
    )

    assert result.flags[0].scope == "quote"
    assert result.line_items[0].qa_state == "needs_review"
    assert "quote_reconciliation_mismatch" in result.line_items[0].issues


def test_low_confidence_item_is_gated_without_arithmetic_flag() -> None:
    client = FakeLLMClient(
        {
            "line_items": [
                _line("Unclear handwritten note", page_no=1, amount_cents=1000, confidence=0.7)
            ],
            "page_subtotals": [],
        }
    )

    result = run_async(
        extract_line_items(pages=[_page()], context=_context(), llm_client=client)
    )

    assert result.flags == ()
    assert result.line_items[0].qa_state == "needs_review"
    assert result.line_items[0].issues == ("low_extraction_confidence",)


class FakeLLMClient:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.schema: dict[str, Any] = {}

    async def extract(
        self,
        document_pages: list[TenderDocumentPage],
        schema: dict[str, Any],
        context: ProjectContext,
    ) -> LLMExtractionResponse:
        self.schema = schema
        return LLMExtractionResponse(
            data=self.data,
            model="fake-model",
            prompt_version="test",
            request_id="req-1",
        )


def _line(
    description: str,
    *,
    page_no: int,
    amount_cents: int,
    confidence: float = 0.95,
) -> dict[str, Any]:
    return {
        "page_no": page_no,
        "description_raw": description,
        "amount_cents": amount_cents,
        "item_status": "included",
        "extraction_confidence": confidence,
    }


def _page() -> TenderDocumentPage:
    return TenderDocumentPage(document_id="doc-1", page_no=1, text_content="Quote text")


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


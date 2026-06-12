import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from tender.llm.openai_client import AsyncOpenAITenderClient
from tender.schemas import ProjectContext, TenderDocumentPage
from tests.conftest import run_async


def test_openai_client_requests_strict_structured_output(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("extract carefully", encoding="utf-8")
    fake_client = FakeOpenAIClient()
    client = AsyncOpenAITenderClient(
        client=fake_client,  # type: ignore[arg-type]
        model="gpt-test",
        prompt_path=prompt_path,
    )

    result = run_async(
        client.extract(
            [_page()],
            {"type": "object", "properties": {"line_items": {"type": "array"}}},
            _context(),
        )
    )

    call = fake_client.responses.kwargs
    assert call["model"] == "gpt-test"
    assert call["instructions"] == "extract carefully"
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True
    assert json.loads(call["input"])["project_context"]["state"] == "NSW"
    assert result.data == {"line_items": [], "page_subtotals": []}
    assert result.request_id == "resp-1"


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(
            id="resp-1",
            output_text=json.dumps({"line_items": [], "page_subtotals": []}),
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


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


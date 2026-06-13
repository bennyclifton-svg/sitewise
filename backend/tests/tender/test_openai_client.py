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


def test_openai_client_adjudicate_constrains_choice_enum(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("extract carefully", encoding="utf-8")
    fake_client = FakeOpenAIClient(
        output={"choice": "03.05", "confidence": 0.87, "rationale": "closest scope"}
    )
    client = AsyncOpenAITenderClient(
        client=fake_client,  # type: ignore[arg-type]
        model="gpt-test",
        prompt_path=prompt_path,
        model_overrides={"tender_model_adjudicate_small": "gpt-small-test"},
    )

    result = run_async(
        client.adjudicate(
            "Map this line item",
            ["03.01", "03.05", "none_of_these"],
            {"description": "retaining wall allowance"},
            _context(),
            prompt_version="0.1.0",
            model_key="tender_model_adjudicate_small",
        )
    )

    call = fake_client.responses.kwargs
    schema = call["text"]["format"]["schema"]
    assert call["model"] == "gpt-small-test"
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True
    assert schema["properties"]["choice"]["enum"] == [
        "03.01",
        "03.05",
        "none_of_these",
    ]
    payload = json.loads(call["input"])
    assert payload["question"] == "Map this line item"
    assert payload["choices"] == ["03.01", "03.05", "none_of_these"]
    assert payload["project_context"]["state"] == "NSW"
    assert result.choice == "03.05"
    assert result.confidence == 0.87
    assert result.model == "gpt-small-test"
    assert result.prompt_version == "0.1.0"


class FakeResponses:
    def __init__(self, output: dict[str, Any] | None = None) -> None:
        self.kwargs: dict[str, Any] = {}
        self.output = output or {"line_items": [], "page_subtotals": []}

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(
            id="resp-1",
            output_text=json.dumps(self.output),
        )


class FakeOpenAIClient:
    def __init__(self, output: dict[str, Any] | None = None) -> None:
        self.responses = FakeResponses(output)


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

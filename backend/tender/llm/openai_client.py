from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from app.config import settings
from tender.llm.client import LLMExtractionResponse
from tender.schemas import ProjectContext, TenderDocumentPage

PROMPT_VERSION = "0.1.0"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "extract_line_items_v0.1.0.md"


class AsyncOpenAITenderClient:
    def __init__(
        self,
        client: AsyncOpenAI | None = None,
        model: str | None = None,
        prompt_path: Path = PROMPT_PATH,
    ) -> None:
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = model or settings.tender_model_extract
        self.prompt_path = prompt_path

    async def extract(
        self,
        document_pages: Sequence[TenderDocumentPage],
        schema: dict[str, Any],
        context: ProjectContext,
    ) -> LLMExtractionResponse:
        response = await self.client.responses.create(
            model=self.model,
            instructions=self.prompt_path.read_text(encoding="utf-8"),
            input=_build_input(document_pages, context),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "tender_line_item_extraction",
                    "schema": schema,
                    "strict": True,
                }
            },
            temperature=0,
        )
        return LLMExtractionResponse(
            data=json.loads(_response_text(response)),
            model=self.model,
            prompt_version=PROMPT_VERSION,
            request_id=getattr(response, "id", None),
        )


def _build_input(
    document_pages: Sequence[TenderDocumentPage], context: ProjectContext
) -> str:
    pages = [
        {
            "document_id": page.document_id,
            "page_no": page.page_no,
            "text_content": page.text_content,
            "image_path": page.image_path,
        }
        for page in document_pages
    ]
    return json.dumps(
        {
            "project_context": context.model_dump(mode="json"),
            "document_pages": pages,
        },
        ensure_ascii=True,
    )


def _response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    for output in getattr(response, "output", []):
        for content in getattr(output, "content", []):
            text = getattr(content, "text", None)
            if text:
                return str(text)
    raise ValueError("OpenAI structured extraction response did not contain text")


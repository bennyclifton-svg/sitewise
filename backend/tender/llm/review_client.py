"""Bounded structured calls for procurement facts and report selection."""

from __future__ import annotations

import base64
import json
import hashlib
import re
from pathlib import Path
from typing import Any, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings
from tender.llm.schema import openai_strict_json_schema
from tender.services.telemetry import note_openai_response

VERSION = "1.0.0"
PROMPTS = Path(__file__).parent / "prompts"
T = TypeVar("T", bound=BaseModel)


def reader_signature(schema: type[BaseModel]) -> str:
    content = (PROMPTS / f"review_extract_v{VERSION}.md").read_bytes()
    content += json.dumps(schema.model_json_schema(), sort_keys=True).encode()
    content += f"native-pages-1:printed-dates-1:{VERSION}:{settings.tender_model_extract}".encode()
    return hashlib.sha256(content).hexdigest()[:40]


def selection_schema(schema: type[BaseModel], fact_ids: list[str]) -> dict[str, Any]:
    shape = openai_strict_json_schema(schema.model_json_schema())
    reference = {"type": "string"}
    # Reserve room for the schema's other enums under the provider's 1,000-value cap.
    if fact_ids and len(fact_ids) <= 950 and sum(map(len, fact_ids)) <= 15000:
        reference["enum"] = fact_ids
    else:
        reference["pattern"] = (
            "^(?:" + "|".join(re.escape(value) for value in fact_ids) + ")$"
        )
    definitions = shape.setdefault("$defs", {})
    for node in [shape, *definitions.values()]:
        for key, value in node.get("properties", {}).items():
            if key in {"fact_ids", "recommendation_fact_ids"}:
                value["items"] = {"$ref": "#/$defs/SourceReference"}
    definitions["SourceReference"] = reference
    return shape


class ReviewClient:
    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        self.client = client or AsyncOpenAI(
            api_key=settings.openai_api_key, timeout=150, max_retries=1
        )

    async def request(
        self,
        *,
        stage: str,
        payload: dict[str, Any],
        schema: type[T],
        images: dict[int, bytes] | None = None,
    ) -> T:
        if stage == "select":
            payload = {
                **payload,
                "facts": [
                    {
                        key: value
                        for key, value in fact.items()
                        if value is not None
                        and key not in {"valid_until", "issued_on", "validity_days"}
                    }
                    for fact in payload["facts"]
                ],
            }
        content: list[dict[str, Any]] = [
            {"type": "input_text", "text": json.dumps(payload, ensure_ascii=False)}
        ]
        for number, image in (images or {}).items():
            content.extend(
                [
                    {"type": "input_text", "text": f"Original PDF page {number}"},
                    {
                        "type": "input_image",
                        "image_url": "data:image/png;base64,"
                        + base64.b64encode(image).decode("ascii"),
                        "detail": "high",
                    },
                ]
            )
        model = (
            settings.tender_model_extract
            if stage == "extract"
            else settings.tender_model_adjudicate_frontier
        )
        response = await self.client.responses.create(
            model=model,
            instructions=(PROMPTS / f"review_{stage}_v{VERSION}.md").read_text(
                encoding="utf-8"
            ),
            input=[{"role": "user", "content": content}],
            text={
                "format": {
                    "type": "json_schema",
                    "name": f"procurement_review_{stage}",
                    "schema": selection_schema(
                        schema, [fact["id"] for fact in payload["facts"]]
                    )
                    if stage == "select"
                    else openai_strict_json_schema(schema.model_json_schema()),
                    "strict": True,
                }
            },
            max_output_tokens=24000 if stage == "extract" else 12000,
        )
        note_openai_response(
            response, model=model, prompt_version=f"review-{stage}-{VERSION}"
        )
        if response.status != "completed":
            raise ValueError(
                "The document analysis response was incomplete; retry this step"
            )
        return schema.model_validate_json(response.output_text)

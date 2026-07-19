from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from app.config import settings
from tender.llm.client import LLMAdjudicationResponse, LLMExtractionResponse
from tender.llm.schema import openai_strict_json_schema
from tender.schemas import ProjectContext, TenderDocumentPage
from tender.services.telemetry import note_openai_response

PROMPT_VERSION = "0.2.0"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "extract_line_items_v0.2.0.md"


class AsyncOpenAITenderClient:
    def __init__(
        self,
        client: AsyncOpenAI | None = None,
        model: str | None = None,
        prompt_path: Path = PROMPT_PATH,
        model_overrides: Mapping[str, str] | None = None,
    ) -> None:
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = model or settings.tender_model_extract
        self.prompt_path = prompt_path
        self.model_overrides = dict(model_overrides or {})

    async def extract(
        self,
        document_pages: Sequence[TenderDocumentPage],
        schema: dict[str, Any],
        context: ProjectContext,
        *,
        page_images: Sequence[bytes] | None = None,
        prior_section_headings: Sequence[str] | None = None,
        already_found: Sequence[dict[str, Any]] | None = None,
        reextract_hint: str | None = None,
    ) -> LLMExtractionResponse:
        response = await self.client.responses.create(
            model=self.model,
            instructions=self.prompt_path.read_text(encoding="utf-8"),
            input=_build_input(
                document_pages,
                context,
                page_images=page_images,
                prior_section_headings=prior_section_headings,
                already_found=already_found,
                reextract_hint=reextract_hint,
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "tender_line_item_extraction",
                    "schema": openai_strict_json_schema(schema),
                    "strict": True,
                }
            },
            temperature=0,
        )
        note_openai_response(response)
        return LLMExtractionResponse(
            data=json.loads(_response_text(response)),
            model=self.model,
            prompt_version=PROMPT_VERSION,
            request_id=getattr(response, "id", None),
        )

    async def adjudicate(
        self,
        question: str,
        choices: Sequence[str],
        evidence: dict[str, Any],
        context: ProjectContext,
        *,
        prompt_version: str,
        model_key: str,
    ) -> LLMAdjudicationResponse:
        model = self._model_for_key(model_key)
        response = await self.client.responses.create(
            model=model,
            instructions=(
                "Answer the tender mapping adjudication question using only the "
                "provided choices and evidence."
            ),
            input=_build_adjudication_input(question, choices, evidence, context),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "tender_adjudication",
                    "schema": openai_strict_json_schema(_adjudication_schema(choices)),
                    "strict": True,
                }
            },
            temperature=0,
        )
        note_openai_response(response)
        data = json.loads(_response_text(response))
        choice = str(data["choice"])
        if choice not in choices:
            raise ValueError(f"adjudication returned unknown choice: {choice}")
        return LLMAdjudicationResponse(
            choice=choice,
            confidence=float(data["confidence"]),
            rationale=str(data["rationale"]),
            model=model,
            prompt_version=prompt_version,
            request_id=getattr(response, "id", None),
        )

    async def adjudicate_many(
        self,
        question: str,
        choices: Sequence[str],
        evidence_items: Sequence[dict[str, Any]],
        context: ProjectContext,
        *,
        prompt_version: str,
        model_key: str,
    ) -> tuple[LLMAdjudicationResponse, ...]:
        if not evidence_items:
            return ()

        model = self._model_for_key(model_key)
        response = await self.client.responses.create(
            model=model,
            instructions=(
                "Answer each tender mapping adjudication question using only the "
                "provided choices and evidence. Return one decision for every "
                "input item, preserving each item's index."
            ),
            input=_build_batch_adjudication_input(
                question,
                choices,
                evidence_items,
                context,
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "tender_batch_adjudication",
                    "schema": openai_strict_json_schema(
                        _batch_adjudication_schema(choices)
                    ),
                    "strict": True,
                }
            },
            temperature=0,
        )
        note_openai_response(response)
        data = json.loads(_response_text(response))
        decisions = data.get("decisions")
        if not isinstance(decisions, list):
            raise ValueError("batch adjudication returned no decisions list")

        by_index: dict[int, dict[str, Any]] = {}
        for decision in decisions:
            if not isinstance(decision, dict):
                raise ValueError("batch adjudication returned an invalid decision")
            index = int(decision["index"])
            if index in by_index:
                raise ValueError(f"batch adjudication duplicated index: {index}")
            by_index[index] = decision

        expected = set(range(len(evidence_items)))
        if set(by_index) != expected:
            raise ValueError(
                "batch adjudication returned indexes "
                f"{sorted(by_index)}; expected {sorted(expected)}"
            )

        responses: list[LLMAdjudicationResponse] = []
        for index in range(len(evidence_items)):
            decision = by_index[index]
            choice = str(decision["choice"])
            if choice not in choices:
                raise ValueError(f"adjudication returned unknown choice: {choice}")
            responses.append(
                LLMAdjudicationResponse(
                    choice=choice,
                    confidence=float(decision["confidence"]),
                    rationale=str(decision["rationale"]),
                    model=model,
                    prompt_version=prompt_version,
                    request_id=getattr(response, "id", None),
                )
            )
        return tuple(responses)

    def _model_for_key(self, model_key: str) -> str:
        if model_key in self.model_overrides:
            return self.model_overrides[model_key]
        model = getattr(settings, model_key, None)
        if not isinstance(model, str) or not model:
            raise ValueError(f"unknown tender model config key: {model_key}")
        return model


def _build_input(
    document_pages: Sequence[TenderDocumentPage],
    context: ProjectContext,
    *,
    page_images: Sequence[bytes] | None = None,
    prior_section_headings: Sequence[str] | None = None,
    already_found: Sequence[dict[str, Any]] | None = None,
    reextract_hint: str | None = None,
) -> str | list[dict[str, Any]]:
    pages = [
        {
            "document_id": page.document_id,
            "page_no": page.page_no,
            "text_content": page.text_content,
            "image_path": page.image_path,
        }
        for page in document_pages
    ]
    payload: dict[str, Any] = {
        "project_context": context.model_dump(mode="json"),
        "document_pages": pages,
    }
    if prior_section_headings:
        payload["prior_section_headings"] = list(prior_section_headings)
    if already_found:
        payload["already_found"] = list(already_found)
    if reextract_hint:
        payload["reextract_hint"] = reextract_hint

    text = json.dumps(payload, ensure_ascii=True)
    if not page_images:
        return text

    import base64

    content: list[dict[str, Any]] = [{"type": "input_text", "text": text}]
    for image in page_images:
        b64 = base64.b64encode(image).decode("ascii")
        content.append(
            {
                "type": "input_image",
                "image_url": f"data:image/png;base64,{b64}",
            }
        )
    return [{"role": "user", "content": content}]


def _build_adjudication_input(
    question: str,
    choices: Sequence[str],
    evidence: dict[str, Any],
    context: ProjectContext,
) -> str:
    return json.dumps(
        {
            "project_context": context.model_dump(mode="json"),
            "question": question,
            "choices": list(choices),
            "evidence": evidence,
        },
        ensure_ascii=True,
    )


def _build_batch_adjudication_input(
    question: str,
    choices: Sequence[str],
    evidence_items: Sequence[dict[str, Any]],
    context: ProjectContext,
) -> str:
    return json.dumps(
        {
            "project_context": context.model_dump(mode="json"),
            "question": question,
            "choices": list(choices),
            "items": [
                {"index": index, "evidence": evidence}
                for index, evidence in enumerate(evidence_items)
            ],
        },
        ensure_ascii=True,
    )


def _adjudication_schema(choices: Sequence[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "choice": {"type": "string", "enum": list(choices)},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "rationale": {"type": "string"},
        },
        "required": ["choice", "confidence", "rationale"],
        "additionalProperties": False,
    }


def _batch_adjudication_schema(choices: Sequence[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "decisions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer", "minimum": 0},
                        "choice": {"type": "string", "enum": list(choices)},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "rationale": {"type": "string"},
                    },
                    "required": ["index", "choice", "confidence", "rationale"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["decisions"],
        "additionalProperties": False,
    }


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

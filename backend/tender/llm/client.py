from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from tender.schemas import ProjectContext, TenderDocumentPage


@dataclass(frozen=True)
class LLMExtractionResponse:
    data: dict[str, Any]
    model: str
    prompt_version: str
    request_id: str | None = None


@dataclass(frozen=True)
class LLMAdjudicationResponse:
    choice: str
    confidence: float
    rationale: str
    model: str
    prompt_version: str
    request_id: str | None = None


class TenderLLMClient(Protocol):
    async def extract(
        self,
        document_pages: Sequence[TenderDocumentPage],
        schema: dict[str, Any],
        context: ProjectContext,
    ) -> LLMExtractionResponse:
        ...

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
        ...

    async def adjudicate_many(
        self,
        question: str,
        choices: Sequence[str],
        evidence_items: Sequence[dict[str, Any]],
        context: ProjectContext,
        *,
        prompt_version: str,
        model_key: str,
    ) -> Sequence[LLMAdjudicationResponse]:
        ...

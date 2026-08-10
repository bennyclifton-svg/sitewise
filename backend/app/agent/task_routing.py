"""Choose the smallest adequate execution class for an artefact request."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel


TaskClass = Literal["DETERMINISTIC", "FAST_SEMANTIC", "REASONING", "NARRATIVE"]
RetrievalNeed = Literal["none", "targeted", "project"]


class AiTaskRoute(BaseModel):
    task_class: TaskClass
    retrieval: RetrievalNeed
    reason: str


def route_ai_task(
    request: str, *, has_structured_operation: bool = False
) -> AiTaskRoute:
    text = " ".join(request.casefold().split())
    if has_structured_operation or re.search(
        r"\b(delete|duplicate|move|set|change)\b.*\b(row|item|amount|consultant)\b",
        text,
    ):
        return AiTaskRoute(
            task_class="DETERMINISTIC",
            retrieval="none",
            reason="A validated application operation can perform this change.",
        )
    if any(term in text for term in ("reconcile", "conflict", "trade-off", "compare")):
        return AiTaskRoute(
            task_class="REASONING",
            retrieval="targeted",
            reason="The request must reconcile or compare competing project facts.",
        )
    if re.search(
        r"\b(write|rewrite|draft)\b.*\b(section|narrative|plan|background)\b", text
    ):
        return AiTaskRoute(
            task_class="NARRATIVE",
            retrieval="targeted",
            reason="The request asks for bounded narrative composition.",
        )
    return AiTaskRoute(
        task_class="FAST_SEMANTIC",
        retrieval="none",
        reason="A small semantic mapping can produce structured operations.",
    )

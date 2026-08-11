"""Choose the smallest adequate execution class for an artefact request."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel


TaskClass = Literal["DETERMINISTIC", "FAST_SEMANTIC", "REASONING", "NARRATIVE"]
RetrievalNeed = Literal["none", "targeted", "project"]
ExecutorPath = Literal["application", "fast_semantic", "reasoning", "narrative"]

TASK_CLASS_MODELS: dict[TaskClass, str] = {
    "DETERMINISTIC": "gpt-5.6-luna",
    "FAST_SEMANTIC": "gpt-5.6-luna",
    "REASONING": "gpt-5.6-sol",
    "NARRATIVE": "gpt-5.6-terra",
}


class AiTaskRoute(BaseModel):
    task_class: TaskClass
    retrieval: RetrievalNeed
    path: ExecutorPath
    model: str | None
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
            path="application",
            model=None if has_structured_operation else TASK_CLASS_MODELS["DETERMINISTIC"],
            reason="A validated application operation can perform this change.",
        )
    if any(term in text for term in ("reconcile", "conflict", "trade-off", "compare")):
        return AiTaskRoute(
            task_class="REASONING",
            retrieval="targeted",
            path="reasoning",
            model=TASK_CLASS_MODELS["REASONING"],
            reason="The request must reconcile or compare competing project facts.",
        )
    if re.search(
        r"\b(write|rewrite|draft)\b.*\b(section|narrative|plan|background)\b", text
    ):
        return AiTaskRoute(
            task_class="NARRATIVE",
            retrieval="targeted",
            path="narrative",
            model=TASK_CLASS_MODELS["NARRATIVE"],
            reason="The request asks for bounded narrative composition.",
        )
    return AiTaskRoute(
        task_class="FAST_SEMANTIC",
        retrieval="none",
        path="fast_semantic",
        model=TASK_CLASS_MODELS["FAST_SEMANTIC"],
        reason="A small semantic mapping can produce structured operations.",
    )


def task_route_telemetry(
    route: AiTaskRoute,
    *,
    latency_ms: int | None = None,
    usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Durable task-routing telemetry persisted on the agent turn."""
    return {
        "task_class": route.task_class,
        "path": route.path,
        "retrieval": route.retrieval,
        "model": route.model,
        "reason": route.reason,
        "latency_ms": latency_ms,
        "usage": usage
        or {
            "input_tokens": None,
            "output_tokens": None,
        },
    }

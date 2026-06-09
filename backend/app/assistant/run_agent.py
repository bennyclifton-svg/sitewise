import asyncio
import re

import structlog
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError

from app.config import settings

logger = structlog.get_logger(__name__)

_RETRY_AFTER_RE = re.compile(r"try again in ([0-9.]+)s", re.IGNORECASE)


def _retry_wait_seconds(exc: ModelHTTPError, attempt: int) -> float:
    body = exc.body
    if isinstance(body, dict):
        message = str(body.get("message", ""))
        match = _RETRY_AFTER_RE.search(message)
        if match:
            return float(match.group(1)) + 0.5
    return min(60.0, (2**attempt) * 5.0)


async def run_agent_with_retry(agent: Agent, *args, model: str | None = None, **kwargs):
    if model is not None:
        kwargs.setdefault("model", f"openai-chat:{model}")
    resolved_model = model or settings.openai_chat_model
    last_error: ModelHTTPError | None = None
    for attempt in range(settings.openai_rate_limit_max_retries):
        try:
            return await agent.run(*args, **kwargs)
        except ModelHTTPError as exc:
            if exc.status_code != 429:
                raise
            last_error = exc
            if attempt >= settings.openai_rate_limit_max_retries - 1:
                break
            wait_s = _retry_wait_seconds(exc, attempt)
            logger.warning(
                "openai_rate_limit_retry",
                attempt=attempt + 1,
                wait_s=wait_s,
                model=resolved_model,
            )
            await asyncio.sleep(wait_s)
    assert last_error is not None
    raise last_error

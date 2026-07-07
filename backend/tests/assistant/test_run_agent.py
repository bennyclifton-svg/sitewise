import pytest
from pydantic_ai.exceptions import ModelHTTPError

from app.assistant.run_agent import _retry_wait_seconds, run_agent_with_retry
from tests.conftest import run_async


class DummyAgent:
    def __init__(self) -> None:
        self.kwargs = None

    async def run(self, *args, **kwargs):
        self.kwargs = kwargs
        return object()


def test_retry_wait_parses_openai_message() -> None:
    exc = ModelHTTPError(
        status_code=429,
        model_name="gpt-4o-mini",
        body={
            "message": "Rate limit reached. Please try again in 3.662s.",
        },
    )
    assert _retry_wait_seconds(exc, 0) == pytest.approx(4.162, abs=0.01)


def test_retry_wait_exponential_fallback() -> None:
    exc = ModelHTTPError(status_code=429, model_name="gpt-4o-mini", body={})
    assert _retry_wait_seconds(exc, 0) == 5.0
    assert _retry_wait_seconds(exc, 2) == 20.0


def test_run_agent_with_retry_passes_provider_qualified_model() -> None:
    agent = DummyAgent()

    run_async(run_agent_with_retry(agent, "prompt", model="openai-responses:gpt-5.5"))

    assert agent.kwargs["model"] == "openai-responses:gpt-5.5"


def test_run_agent_with_retry_wraps_bare_model_as_openai_chat() -> None:
    agent = DummyAgent()

    run_async(run_agent_with_retry(agent, "prompt", model="gpt-4.1"))

    assert agent.kwargs["model"] == "openai-chat:gpt-4.1"

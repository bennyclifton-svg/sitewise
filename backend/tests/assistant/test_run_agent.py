import pytest
from pydantic_ai.exceptions import ModelHTTPError

from app.assistant.run_agent import _retry_wait_seconds


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

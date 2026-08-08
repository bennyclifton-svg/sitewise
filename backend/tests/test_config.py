import pytest
from pydantic import ValidationError

from app.config import Settings


def _settings_kwargs() -> dict[str, str]:
    return {
        "supabase_url": "https://example.supabase.co",
        "supabase_anon_key": "anon",
        "supabase_service_role_key": "service",
        "database_url": "postgresql://user:pass@localhost:5432/postgres",
        "openai_api_key": "sk-test",
    }


def test_agent_runtime_enabled_requires_turn_token_secret():
    with pytest.raises(ValidationError, match="AGENT_TURN_TOKEN_SECRET"):
        Settings(
            **_settings_kwargs(),
            agent_runtime_enabled=True,
            agent_turn_token_secret="",
        )


def test_agent_runtime_accepts_turn_token_secret():
    settings = Settings(
        **_settings_kwargs(),
        agent_runtime_enabled=True,
        agent_turn_token_secret="secret-value-at-least-32-characters",
    )

    assert settings.agent_runtime_enabled is True


def test_pmp_model_provider_is_validated():
    with pytest.raises(ValidationError, match="PMP_MODEL_PROVIDER"):
        Settings(
            **_settings_kwargs(),
            pmp_model_provider="unknown",
        )


def test_web_research_enabled_accepts_keyless_nsw_provider():
    settings = Settings(
        **_settings_kwargs(),
        agent_web_research_enabled=True,
        web_search_provider="nsw_legislation",
        brave_search_api_key=None,
    )

    assert settings.web_search_provider == "nsw_legislation"


def test_web_research_enabled_requires_key_for_brave_provider():
    with pytest.raises(ValidationError, match="BRAVE_SEARCH_API_KEY"):
        Settings(
            **_settings_kwargs(),
            agent_web_research_enabled=True,
            web_search_provider="brave",
            brave_search_api_key=None,
        )


def test_web_search_provider_is_validated():
    with pytest.raises(ValidationError, match="WEB_SEARCH_PROVIDER"):
        Settings(
            **_settings_kwargs(),
            web_search_provider="unknown",
        )

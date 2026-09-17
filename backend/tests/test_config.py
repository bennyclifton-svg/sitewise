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


def test_mailgun_settings_accept_configured_provider():
    configured = Settings(**_settings_kwargs(), _env_file=None,
                          email_provider="mailgun", mailgun_api_key="test-key")
    assert configured.email_provider == "mailgun"


def test_mailgun_settings_require_key():
    with pytest.raises(ValidationError, match="MAILGUN_API_KEY"):
        Settings(**_settings_kwargs(), _env_file=None,
                 email_provider="mailgun", mailgun_api_key="")


@pytest.mark.parametrize("environment", ["production", " Production "])
def test_production_rejects_fake_email_at_startup(environment):
    with pytest.raises(ValidationError, match="fake"):
        Settings(**_settings_kwargs(), _env_file=None,
                 environment=environment, email_provider="fake")


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


def test_web_research_enabled_requires_key_for_tavily_provider():
    with pytest.raises(ValidationError, match="TAVILY_API_KEY"):
        Settings(
            **_settings_kwargs(),
            agent_web_research_enabled=True,
            web_search_provider="tavily",
            tavily_api_key=None,
        )


def test_web_research_enabled_accepts_tavily_key():
    settings = Settings(
        **_settings_kwargs(),
        agent_web_research_enabled=True,
        web_search_provider="tavily",
        tavily_api_key="tvly-test",
    )

    assert settings.web_search_provider == "tavily"


def test_web_search_provider_is_validated():
    with pytest.raises(ValidationError, match="WEB_SEARCH_PROVIDER"):
        Settings(
            **_settings_kwargs(),
            web_search_provider="unknown",
        )


def test_validation_errors_hide_invalid_secret_input() -> None:
    secret = "ch03-invalid-database-password-xxxxxxxx"
    kwargs = _settings_kwargs()
    kwargs["database_url"] = (
        f"postgresql://user:{secret}@aws-0-region.pooler.supabase.com:6543/postgres"
    )

    with pytest.raises(ValidationError) as captured:
        Settings(**kwargs)

    assert secret not in str(captured.value)

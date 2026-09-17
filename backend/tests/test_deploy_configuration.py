from pathlib import Path

from app.config import Settings


_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOKPLOY_COMPOSE = _REPO_ROOT / "deploy" / "dokploy.compose.yml"
_API_ENV_EXAMPLE = _REPO_ROOT / "deploy" / "env" / "sitewise-api.env.example"
_COMMERCIAL_SEARCH_KEYS = ("BRAVE_SEARCH_API_KEY", "TAVILY_API_KEY")


def test_dokploy_forwards_commercial_search_provider_keys() -> None:
    compose = _DOKPLOY_COMPOSE.read_text(encoding="utf-8")

    for key in _COMMERCIAL_SEARCH_KEYS:
        assert f"  {key}: ${{{key}:-}}" in compose


def test_api_env_example_documents_commercial_search_provider_keys() -> None:
    example = _API_ENV_EXAMPLE.read_text(encoding="utf-8")

    for key in _COMMERCIAL_SEARCH_KEYS:
        assert f"{key}=" in example


def test_deployment_model_defaults_match_application_and_example():
    compose = _DOKPLOY_COMPOSE.read_text(encoding="utf-8")
    example = _API_ENV_EXAMPLE.read_text(encoding="utf-8")
    for field in ("pi_model", "pi_model_provider", "pi_model_options", "agent_queue_timeout_seconds", "openai_chat_model", "openai_chat_models"):
        key = field.upper()
        default = Settings.model_fields[field].default
        assert f"${{{key}:-{default}}}" in compose
        assert f"{key}={default}" in example
    assert "XAI_API_KEY: ${XAI_API_KEY:-}" in compose


def test_production_defaults_require_real_email_and_commit_tag():
    compose = _DOKPLOY_COMPOSE.read_text(encoding="utf-8")
    assert "ENVIRONMENT:-production" in compose
    assert "EMAIL_PROVIDER:-mailgun" in compose
    assert ":latest" not in compose
    assert compose.count("${BUILD_SHA:?BUILD_SHA must identify the selected commit}") == 4


def test_delivery_and_ci_contract():
    nginx = (_REPO_ROOT / "deploy/nginx/sitewise.conf").read_text()
    api = nginx.split("location /api/ {", 1)[1].split("}", 1)[0]
    assert "gzip off;" in api
    assert "proxy_buffering off;" in api
    assert "proxy_request_buffering off;" in api
    assert 'Cache-Control "no-cache" always' in nginx
    assert 'Cache-Control "public, max-age=31536000, immutable";' in nginx
    workflow = (_REPO_ROOT / ".github/workflows/ci.yml").read_text()
    smoke = workflow.split("  database-smoke:", 1)[1].split("  release-images:", 1)[0]
    assert "if: github.event_name" not in smoke
    assert "needs: [backend-offline, frontend, tender-seeds, database-smoke]" in workflow


def test_health_reports_selected_build_without_secrets(monkeypatch):
    from app.config import settings
    from app.main import health
    from tests.conftest import run_async

    monkeypatch.setattr(settings, "build_sha", "a" * 40)
    payload = run_async(health())
    assert payload["build_sha"] == "a" * 40
    assert not any("secret" in key or "api_key" in key for key in payload)

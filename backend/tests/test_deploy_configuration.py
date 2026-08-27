from pathlib import Path


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

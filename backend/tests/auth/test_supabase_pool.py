from unittest.mock import AsyncMock, MagicMock

from app.auth import dependencies
from tests.conftest import run_async


def test_verified_users_share_the_lifespan_http_client() -> None:
    dependencies._auth_user_cache.clear()
    client = AsyncMock()
    response = MagicMock(status_code=200)
    response.json.return_value = {
        "id": "11111111-1111-1111-1111-111111111111",
        "email": "a@example.com",
    }
    client.get.return_value = response

    first = run_async(dependencies._verified_supabase_user(client, "token"))
    second = run_async(dependencies._verified_supabase_user(client, "token"))

    assert first == second
    client.get.assert_awaited_once()


def test_auth_http_client_has_explicit_pool_limits() -> None:
    client = dependencies.create_auth_http_client()
    try:
        assert client.timeout.connect == 5.0
        assert client.timeout.pool == 5.0
        assert client._transport._pool._max_connections == 50
        assert client._transport._pool._max_keepalive_connections == 20
    finally:
        run_async(client.aclose())

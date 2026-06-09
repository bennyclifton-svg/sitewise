import httpx
import pytest

from app.billing import polar
from tests.conftest import run_async


def test_polar_post_normalizes_endpoint_and_follows_redirects(monkeypatch):
    captured = {}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured["post_kwargs"] = kwargs
            return httpx.Response(200, json={"url": "https://checkout.polar.sh/session"})

    monkeypatch.setattr(polar.settings, "polar_access_token", "polar-token")
    monkeypatch.setattr(polar.settings, "polar_environment", "sandbox")
    monkeypatch.setattr(polar.httpx, "AsyncClient", FakeAsyncClient)

    data = run_async(polar.polar_post("checkouts", {"products": ["product-id"]}))

    assert data == {"url": "https://checkout.polar.sh/session"}
    assert captured["client_kwargs"]["follow_redirects"] is True
    assert captured["url"] == "https://sandbox-api.polar.sh/v1/checkouts/"


def test_polar_post_rejects_redirect_response(monkeypatch):
    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, **kwargs):
            return httpx.Response(307)

    monkeypatch.setattr(polar.settings, "polar_access_token", "polar-token")
    monkeypatch.setattr(polar.settings, "polar_environment", "sandbox")
    monkeypatch.setattr(polar.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(polar.PolarApiError, match="Polar API returned 307"):
        run_async(polar.polar_post("checkouts", {"products": ["product-id"]}))


def test_polar_post_wraps_transport_errors(monkeypatch):
    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, **kwargs):
            raise httpx.ConnectError("connection failed")

    monkeypatch.setattr(polar.settings, "polar_access_token", "polar-token")
    monkeypatch.setattr(polar.settings, "polar_environment", "sandbox")
    monkeypatch.setattr(polar.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(polar.PolarApiError, match="Polar API request failed"):
        run_async(polar.polar_post("checkouts", {"products": ["product-id"]}))

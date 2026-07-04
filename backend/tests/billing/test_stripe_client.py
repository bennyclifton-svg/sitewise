from types import SimpleNamespace
import uuid

from app.auth.dependencies import CurrentUser
from app.billing.plans import BillingPlan
from app.billing import stripe_client
from app.config import settings
from tests.conftest import run_async


def test_create_checkout_session_uses_settings_urls(monkeypatch):
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(url="https://checkout.stripe.test/session")

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_123")
    monkeypatch.setattr(settings, "billing_provider", "stripe")
    monkeypatch.setattr(settings, "public_app_url", "https://app.example")
    monkeypatch.setattr(settings, "stripe_checkout_success_path", "/billing?success=true")
    monkeypatch.setattr(settings, "stripe_portal_return_path", "/billing")
    monkeypatch.setattr(stripe_client.stripe.checkout.Session, "create", fake_create)

    url = run_async(
        stripe_client.create_checkout_session(
            plan=BillingPlan(
                id="starter",
                name="Starter",
                description="Starter",
                price_monthly=49,
                product_id="price_123",
            ),
            user=CurrentUser(
                id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                email="a@example.com",
            ),
        )
    )

    assert url == "https://checkout.stripe.test/session"
    assert captured["api_key"] == "sk_test_123"
    assert captured["mode"] == "subscription"
    assert captured["line_items"] == [{"price": "price_123", "quantity": 1}]
    assert captured["success_url"] == "https://app.example/billing?success=true"
    assert captured["cancel_url"] == "https://app.example/billing"
    assert captured["customer_email"] == "a@example.com"
    assert captured["metadata"]["plan_id"] == "starter"


def test_create_portal_session_uses_customer_and_return_url(monkeypatch):
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return {"url": "https://billing.stripe.test/session"}

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_123")
    monkeypatch.setattr(settings, "billing_provider", "stripe")
    monkeypatch.setattr(settings, "public_app_url", "https://app.example")
    monkeypatch.setattr(settings, "stripe_portal_return_path", "/billing")
    monkeypatch.setattr(stripe_client.stripe.billing_portal.Session, "create", fake_create)

    url = run_async(stripe_client.create_portal_session(stripe_customer_id="cus_123"))

    assert url == "https://billing.stripe.test/session"
    assert captured == {
        "api_key": "sk_test_123",
        "customer": "cus_123",
        "return_url": "https://app.example/billing",
    }

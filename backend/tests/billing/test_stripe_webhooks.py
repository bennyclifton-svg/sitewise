import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.billing import stripe_webhooks
from app.config import settings
from app.database.session import get_db
from app.main import fastapi_app as app
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CUSTOMER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def test_stripe_webhook_bad_signature_returns_400_and_writes_nothing(monkeypatch):
    mock_session = AsyncMock()

    async def override_get_db():
        yield mock_session

    def fake_construct_event(payload, sig_header, secret):
        raise ValueError("bad signature")

    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    monkeypatch.setattr(
        stripe_webhooks.stripe.Webhook,
        "construct_event",
        fake_construct_event,
    )
    sync = AsyncMock()
    monkeypatch.setattr(stripe_webhooks, "sync_stripe_webhook", sync)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        response = client.post(
            "/billing/webhook/stripe",
            content=b'{"type":"checkout.session.completed"}',
            headers={"stripe-signature": "bad"},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 400
    sync.assert_not_awaited()


def test_verify_stripe_webhook_accepts_sdk_event_object(monkeypatch):
    class FakeStripeEvent:
        def _to_dict_recursive(self):
            return {
                "id": "evt_123",
                "type": "checkout.session.completed",
                "data": {"object": {"id": "cs_123"}},
            }

    def fake_construct_event(payload, sig_header, secret):
        assert payload == b"{}"
        assert sig_header == "sig"
        assert secret == "whsec_test"
        return FakeStripeEvent()

    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    monkeypatch.setattr(
        stripe_webhooks.stripe.Webhook,
        "construct_event",
        fake_construct_event,
    )

    event = stripe_webhooks.verify_stripe_webhook(b"{}", "sig")

    assert event["id"] == "evt_123"
    assert event["type"] == "checkout.session.completed"


def test_checkout_completed_upserts_customer_and_subscription(monkeypatch):
    session = AsyncMock()
    upsert_customer = AsyncMock(return_value=SimpleNamespace(id=CUSTOMER_ID))
    upsert_subscription = AsyncMock()
    monkeypatch.setattr(stripe_webhooks, "upsert_stripe_customer", upsert_customer)
    monkeypatch.setattr(stripe_webhooks, "upsert_stripe_subscription", upsert_subscription)

    result = run_async(
        stripe_webhooks.sync_stripe_webhook(
            session,
            {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "customer": "cus_123",
                        "subscription": "sub_123",
                        "customer_details": {"email": "a@example.com"},
                        "metadata": {
                            "user_id": str(USER_ID),
                            "plan_id": "starter",
                            "price_id": "price_123",
                        },
                    }
                },
            },
        )
    )

    assert result.action == "checkout_completed"
    upsert_customer.assert_awaited_once_with(
        session,
        user_id=USER_ID,
        stripe_customer_id="cus_123",
        email="a@example.com",
    )
    upsert_subscription.assert_awaited_once()
    assert upsert_subscription.await_args.kwargs["customer_id"] == CUSTOMER_ID
    assert upsert_subscription.await_args.kwargs["stripe_subscription_id"] == "sub_123"
    assert upsert_subscription.await_args.kwargs["price_id"] == "price_123"
    assert upsert_subscription.await_args.kwargs["status"] == "active"


def test_subscription_deleted_marks_subscription_inactive(monkeypatch):
    session = AsyncMock()
    customer = SimpleNamespace(id=CUSTOMER_ID)
    get_customer = AsyncMock(return_value=customer)
    upsert_subscription = AsyncMock()
    monkeypatch.setattr(stripe_webhooks, "get_stripe_customer_by_stripe_id", get_customer)
    monkeypatch.setattr(stripe_webhooks, "upsert_stripe_subscription", upsert_subscription)
    timestamp = int(datetime(2026, 7, 4, tzinfo=timezone.utc).timestamp())

    result = run_async(
        stripe_webhooks.sync_stripe_webhook(
            session,
            {
                "type": "customer.subscription.deleted",
                "data": {
                    "object": {
                        "id": "sub_123",
                        "customer": "cus_123",
                        "status": "canceled",
                        "items": {"data": [{"price": {"id": "price_123"}}]},
                        "current_period_start": timestamp,
                        "current_period_end": timestamp,
                        "cancel_at_period_end": False,
                        "canceled_at": timestamp,
                    }
                },
            },
        )
    )

    assert result.action == "subscription_synced"
    upsert_subscription.assert_awaited_once()
    assert upsert_subscription.await_args.kwargs["customer_id"] == CUSTOMER_ID
    assert upsert_subscription.await_args.kwargs["status"] == "canceled"
    assert upsert_subscription.await_args.kwargs["canceled_at"] == datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    )

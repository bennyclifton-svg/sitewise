import uuid
import hashlib
import hmac
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from fastapi.testclient import TestClient

from app.billing import stripe_webhooks
from app.config import settings
from app.database.session import get_db
from app.main import fastapi_app as app
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CUSTOMER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.mark.parametrize("tampered,age", [(True, 0), (False, 600)])
def test_real_signature_verifier_rejects_tampering_and_expired_signatures(monkeypatch, tampered, age):
    secret = "whsec_local_only"
    monkeypatch.setattr(settings, "stripe_webhook_secret", secret)
    payload = b'{"id":"evt_test","object":"event","type":"test"}'
    timestamp = int(time.time()) - age
    signature = hmac.new(secret.encode(), str(timestamp).encode() + b"." + payload, hashlib.sha256).hexdigest()
    with pytest.raises(HTTPException) as error:
        stripe_webhooks.verify_stripe_webhook(payload + (b" " if tampered else b""), f"t={timestamp},v1={signature}")
    assert error.value.status_code == 400


def test_stripe_refresh_failure_does_not_update_entitlement(monkeypatch):
    def fail(*args, **kwargs):
        raise stripe_webhooks.stripe.APIConnectionError("offline fixture")
    monkeypatch.setattr(stripe_webhooks.stripe.Subscription, "retrieve", fail)
    upsert = AsyncMock()
    monkeypatch.setattr(stripe_webhooks, "upsert_stripe_subscription", upsert)
    with pytest.raises(HTTPException) as error:
        run_async(stripe_webhooks.sync_stripe_webhook(AsyncMock(), {
            "type": "customer.subscription.updated", "data": {"object": {"id": "sub_123"}},
        }))
    assert error.value.status_code == 502
    upsert.assert_not_awaited()


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

    monkeypatch.setattr(stripe_webhooks, "get_stripe_customer_by_stripe_id", AsyncMock(return_value=SimpleNamespace(id=CUSTOMER_ID)))
    monkeypatch.setattr(stripe_webhooks, "_current_subscription", AsyncMock(return_value={
        "id": "sub_123", "customer": "cus_123", "status": "active",
        "items": {"data": [{"price": {"id": "price_123"}}]},
    }))

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

    monkeypatch.setattr(stripe_webhooks, "_current_subscription", AsyncMock(return_value={
        "id": "sub_123", "customer": "cus_123", "status": "canceled",
        "items": {"data": [{"price": {"id": "price_123"}}]},
        "canceled_at": timestamp,
    }))

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


def test_delayed_checkout_cannot_reactivate_cancelled_subscription(monkeypatch):
    session = AsyncMock()
    monkeypatch.setattr(stripe_webhooks, "upsert_stripe_customer", AsyncMock(return_value=SimpleNamespace(id=CUSTOMER_ID)))
    monkeypatch.setattr(stripe_webhooks, "get_stripe_customer_by_stripe_id", AsyncMock(return_value=SimpleNamespace(id=CUSTOMER_ID)))
    upsert = AsyncMock()
    monkeypatch.setattr(stripe_webhooks, "upsert_stripe_subscription", upsert)
    monkeypatch.setattr(stripe_webhooks.stripe.Subscription, "retrieve", lambda *a, **kw: {
        "id": "sub_123", "customer": "cus_123", "status": "canceled",
        "items": {"data": [{"price": {"id": "price_123"}}]},
    })
    event = {"type": "checkout.session.completed", "data": {"object": {
        "customer": "cus_123", "subscription": "sub_123",
        "metadata": {"user_id": str(USER_ID), "price_id": "price_123"},
    }}}
    run_async(stripe_webhooks.sync_stripe_webhook(session, event))
    run_async(stripe_webhooks.sync_stripe_webhook(session, event))
    assert [call.kwargs["status"] for call in upsert.await_args_list] == ["canceled", "canceled"]

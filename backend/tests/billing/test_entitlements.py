import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.billing import entitlements
from app.config import settings
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def test_entitlement_provider_none_is_internal(monkeypatch):
    monkeypatch.setattr(settings, "billing_provider", "none")

    state = run_async(entitlements.get_entitlement_state(AsyncMock(), USER_ID))

    assert state.plan_id == "internal"
    assert state.read_only is False
    assert state.billing_provider == "none"


def test_entitlement_provider_polar_retains_legacy_path(monkeypatch):
    customer_id = uuid.uuid4()
    monkeypatch.setattr(settings, "billing_provider", "polar")
    monkeypatch.setattr(settings, "polar_enabled", True)
    monkeypatch.setattr(settings, "polar_starter_product_id", "polar_prod_123")
    monkeypatch.setattr(
        entitlements,
        "get_polar_customer_by_user_id",
        AsyncMock(return_value=SimpleNamespace(id=customer_id)),
    )
    monkeypatch.setattr(
        entitlements,
        "get_active_polar_subscription_for_user",
        AsyncMock(return_value=SimpleNamespace(status="active", product_id="polar_prod_123")),
    )

    state = run_async(entitlements.get_entitlement_state(AsyncMock(), USER_ID))

    assert state.billing_provider == "polar"
    assert state.plan_id == "starter"
    assert state.subscription_status == "active"
    assert state.read_only is False


def test_entitlement_provider_stripe_reads_stripe_subscription(monkeypatch):
    customer_id = uuid.uuid4()
    monkeypatch.setattr(settings, "billing_provider", "stripe")
    monkeypatch.setattr(settings, "stripe_price_id", "price_123")
    monkeypatch.setattr(
        entitlements,
        "get_stripe_customer_by_user_id",
        AsyncMock(return_value=SimpleNamespace(id=customer_id)),
    )
    monkeypatch.setattr(
        entitlements,
        "get_active_stripe_subscription_for_user",
        AsyncMock(return_value=SimpleNamespace(status="trialing", price_id="price_123")),
    )

    state = run_async(entitlements.get_entitlement_state(AsyncMock(), USER_ID))

    assert state.billing_provider == "stripe"
    assert state.plan_id == "starter"
    assert state.subscription_status == "trialing"
    assert state.read_only is False
    assert state.has_customer is True


def test_entitlement_provider_stripe_without_active_subscription_is_read_only(monkeypatch):
    customer_id = uuid.uuid4()
    monkeypatch.setattr(settings, "billing_provider", "stripe")
    monkeypatch.setattr(settings, "stripe_price_id", "price_123")
    monkeypatch.setattr(
        entitlements,
        "get_stripe_customer_by_user_id",
        AsyncMock(return_value=SimpleNamespace(id=customer_id)),
    )
    monkeypatch.setattr(
        entitlements,
        "get_active_stripe_subscription_for_user",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        entitlements,
        "get_latest_stripe_subscription_for_customer",
        AsyncMock(return_value=SimpleNamespace(status="active", price_id="price_123")),
    )

    state = run_async(entitlements.get_entitlement_state(AsyncMock(), USER_ID))

    assert state.billing_provider == "stripe"
    assert state.plan_id == "starter"
    assert state.subscription_status == "active"
    assert state.read_only is True


def test_entitlement_provider_stripe_without_customer_is_read_only(monkeypatch):
    monkeypatch.setattr(settings, "billing_provider", "stripe")
    monkeypatch.setattr(
        entitlements,
        "get_stripe_customer_by_user_id",
        AsyncMock(return_value=None),
    )

    state = run_async(entitlements.get_entitlement_state(AsyncMock(), USER_ID))

    assert state.plan_id == "none"
    assert state.subscription_status == "missing"
    assert state.read_only is True
    assert state.has_customer is False

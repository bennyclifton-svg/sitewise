from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import stripe
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.stripe_billing import (
    get_stripe_customer_by_stripe_id,
    upsert_stripe_customer,
    upsert_stripe_subscription,
)


@dataclass(frozen=True, slots=True)
class StripeWebhookResult:
    action: str
    event_type: str


def verify_stripe_webhook(payload: bytes, signature: str | None) -> dict[str, Any]:
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook secret is not configured.",
        )
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature.",
        )
    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            settings.stripe_webhook_secret,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook signature.",
        ) from exc
    return _event_mapping(event)


def _event_mapping(event: Any) -> dict[str, Any]:
    if isinstance(event, dict):
        return event
    for method_name in ("to_dict_recursive", "_to_dict_recursive", "to_dict"):
        to_dict = getattr(event, method_name, None)
        if not callable(to_dict):
            continue
        converted = to_dict()
        if isinstance(converted, dict):
            return converted
    return dict(event)


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _object(event: dict[str, Any]) -> dict[str, Any]:
    data = _as_mapping(event.get("data"))
    return _as_mapping(data.get("object"))


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def _price_id(subscription: dict[str, Any]) -> str | None:
    items = _as_mapping(subscription.get("items"))
    data = items.get("data")
    if not isinstance(data, list) or not data:
        return None
    first = _as_mapping(data[0])
    price = _as_mapping(first.get("price"))
    return _string(price.get("id"))


async def _sync_checkout_completed(
    session: AsyncSession,
    event_type: str,
    checkout: dict[str, Any],
) -> StripeWebhookResult:
    metadata = _as_mapping(checkout.get("metadata"))
    user_id_text = _string(metadata.get("user_id"))
    stripe_customer_id = _string(checkout.get("customer"))
    stripe_subscription_id = _string(checkout.get("subscription"))
    price_id = _string(metadata.get("price_id")) or settings.stripe_price_id
    if not user_id_text or not stripe_customer_id or not stripe_subscription_id or not price_id:
        return StripeWebhookResult(action="ignored", event_type=event_type)

    customer_details = _as_mapping(checkout.get("customer_details"))
    customer = await upsert_stripe_customer(
        session,
        user_id=uuid.UUID(user_id_text),
        stripe_customer_id=stripe_customer_id,
        email=_string(customer_details.get("email")),
    )
    await upsert_stripe_subscription(
        session,
        customer_id=customer.id,
        stripe_subscription_id=stripe_subscription_id,
        price_id=price_id,
        status="active",
        current_period_start=None,
        current_period_end=None,
        cancel_at_period_end=False,
        canceled_at=None,
    )
    return StripeWebhookResult(action="checkout_completed", event_type=event_type)


async def _sync_subscription(
    session: AsyncSession,
    event_type: str,
    subscription: dict[str, Any],
) -> StripeWebhookResult:
    stripe_customer_id = _string(subscription.get("customer"))
    stripe_subscription_id = _string(subscription.get("id"))
    price_id = _price_id(subscription) or settings.stripe_price_id
    status_value = _string(subscription.get("status"))
    if not stripe_customer_id or not stripe_subscription_id or not price_id or not status_value:
        return StripeWebhookResult(action="ignored", event_type=event_type)

    customer = await get_stripe_customer_by_stripe_id(session, stripe_customer_id)
    if customer is None:
        metadata = _as_mapping(subscription.get("metadata"))
        user_id_text = _string(metadata.get("user_id"))
        if not user_id_text:
            return StripeWebhookResult(action="ignored", event_type=event_type)
        customer = await upsert_stripe_customer(
            session,
            user_id=uuid.UUID(user_id_text),
            stripe_customer_id=stripe_customer_id,
            email=None,
        )

    await upsert_stripe_subscription(
        session,
        customer_id=customer.id,
        stripe_subscription_id=stripe_subscription_id,
        price_id=price_id,
        status=status_value,
        current_period_start=_timestamp(subscription.get("current_period_start")),
        current_period_end=_timestamp(subscription.get("current_period_end")),
        cancel_at_period_end=bool(subscription.get("cancel_at_period_end")),
        canceled_at=_timestamp(subscription.get("canceled_at")),
    )
    return StripeWebhookResult(action="subscription_synced", event_type=event_type)


async def sync_stripe_webhook(
    session: AsyncSession,
    event: dict[str, Any],
) -> StripeWebhookResult:
    event_type = _string(event.get("type")) or "unknown"
    payload = _object(event)
    if event_type == "checkout.session.completed":
        return await _sync_checkout_completed(session, event_type, payload)
    if event_type in {
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        return await _sync_subscription(session, event_type, payload)
    return StripeWebhookResult(action="ignored", event_type=event_type)

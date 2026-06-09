from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from starlette.datastructures import Headers
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.billing import (
    get_polar_customer_by_polar_id,
    upsert_polar_customer,
    upsert_polar_subscription,
)
from app.database.user import User

SIGNATURE_TOLERANCE_SECONDS = 300


@dataclass(frozen=True, slots=True)
class WebhookSyncResult:
    action: str
    event_type: str


def _secret_bytes(secret: str) -> bytes:
    if secret.startswith("whsec_"):
        encoded = secret.removeprefix("whsec_")
        encoded += "=" * (-len(encoded) % 4)
        return base64.b64decode(encoded)
    return secret.encode()


def _signature_values(signature_header: str) -> list[str]:
    values: list[str] = []
    for chunk in signature_header.split():
        if chunk.startswith("v1,"):
            values.append(chunk.split(",", 1)[1])
        elif chunk.startswith("v1="):
            values.append(chunk.split("=", 1)[1])
    return values


def verify_polar_webhook(headers: Headers, payload: bytes) -> None:
    if not settings.polar_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Polar webhook secret is not configured.",
        )

    webhook_id = headers.get("webhook-id")
    webhook_timestamp = headers.get("webhook-timestamp")
    webhook_signature = headers.get("webhook-signature")
    if not webhook_id or not webhook_timestamp or not webhook_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Polar webhook signature headers.",
        )

    try:
        timestamp = int(webhook_timestamp)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Polar webhook timestamp.",
        ) from exc

    if abs(time.time() - timestamp) > SIGNATURE_TOLERANCE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Polar webhook timestamp is outside the allowed tolerance.",
        )

    signed_payload = f"{webhook_id}.{webhook_timestamp}.".encode() + payload
    expected = base64.b64encode(
        hmac.new(_secret_bytes(settings.polar_webhook_secret), signed_payload, hashlib.sha256).digest()
    ).decode()
    if not any(hmac.compare_digest(expected, value) for value in _signature_values(webhook_signature)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Polar webhook signature.",
        )


def parse_polar_payload(payload: bytes) -> dict[str, Any]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Polar webhook payload.",
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Polar webhook payload.",
        )
    return data


def _as_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _as_bool(value: Any) -> bool:
    return value is True


def _as_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _as_uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _nested_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def _polar_customer_id(data: dict[str, Any]) -> str | None:
    customer = _nested_dict(data, "customer")
    return (
        _as_string(data.get("customer_id"))
        or _as_string(data.get("customerId"))
        or _as_string(customer.get("id"))
    )


def _external_user_id(data: dict[str, Any]) -> uuid.UUID | None:
    customer = _nested_dict(data, "customer")
    return (
        _as_uuid(data.get("external_customer_id"))
        or _as_uuid(data.get("externalCustomerId"))
        or _as_uuid(customer.get("external_id"))
        or _as_uuid(data.get("external_id"))
    )


def _email(data: dict[str, Any]) -> str | None:
    customer = _nested_dict(data, "customer")
    return _as_string(customer.get("email")) or _as_string(data.get("email"))


def _product_id(data: dict[str, Any]) -> str | None:
    product = _nested_dict(data, "product")
    return _as_string(data.get("product_id")) or _as_string(data.get("productId")) or _as_string(product.get("id"))


def _price_id(data: dict[str, Any]) -> str | None:
    direct = _as_string(data.get("price_id")) or _as_string(data.get("priceId"))
    if direct:
        return direct
    prices = data.get("prices")
    if not isinstance(prices, list) or not prices:
        return None
    first_price = prices[0]
    return _as_string(first_price.get("id")) if isinstance(first_price, dict) else None


async def _ensure_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    email: str | None,
) -> None:
    existing = await session.get(User, user_id)
    if existing is not None:
        if email and existing.email != email:
            existing.email = email
        return
    if email:
        session.add(User(id=user_id, email=email))


async def _sync_customer_event(
    session: AsyncSession,
    event_type: str,
    data: dict[str, Any],
) -> WebhookSyncResult:
    polar_customer_id = _as_string(data.get("id"))
    user_id = _external_user_id(data)
    if not polar_customer_id or user_id is None:
        return WebhookSyncResult(action="ignored", event_type=event_type)

    await _ensure_user(session, user_id, _email(data))
    await upsert_polar_customer(
        session,
        user_id=user_id,
        polar_customer_id=polar_customer_id,
        email=_email(data),
    )
    return WebhookSyncResult(action="customer_synced", event_type=event_type)


async def _sync_subscription_event(
    session: AsyncSession,
    event_type: str,
    data: dict[str, Any],
) -> WebhookSyncResult:
    polar_subscription_id = _as_string(data.get("id"))
    polar_customer_id = _polar_customer_id(data)
    product_id = _product_id(data)
    status_value = _as_string(data.get("status"))
    status_by_event = {
        "subscription.active": "active",
        "subscription.uncanceled": "active",
        "subscription.canceled": "canceled",
        "subscription.revoked": "canceled",
        "subscription.past_due": "past_due",
    }
    subscription_status = status_by_event.get(event_type) or status_value

    if not polar_subscription_id or not polar_customer_id or not product_id or not subscription_status:
        return WebhookSyncResult(action="ignored", event_type=event_type)

    customer = await get_polar_customer_by_polar_id(session, polar_customer_id)
    if customer is None:
        user_id = _external_user_id(data)
        if user_id is None:
            return WebhookSyncResult(action="missing_customer", event_type=event_type)
        await _ensure_user(session, user_id, _email(data))
        customer = await upsert_polar_customer(
            session,
            user_id=user_id,
            polar_customer_id=polar_customer_id,
            email=_email(data),
        )

    await upsert_polar_subscription(
        session,
        customer_id=customer.id,
        polar_subscription_id=polar_subscription_id,
        product_id=product_id,
        price_id=_price_id(data),
        status=subscription_status,
        current_period_start=_as_datetime(data.get("current_period_start") or data.get("currentPeriodStart")),
        current_period_end=_as_datetime(data.get("current_period_end") or data.get("currentPeriodEnd")),
        cancel_at_period_end=_as_bool(data.get("cancel_at_period_end") or data.get("cancelAtPeriodEnd")),
        canceled_at=_as_datetime(data.get("canceled_at") or data.get("canceledAt")),
    )
    return WebhookSyncResult(action="subscription_synced", event_type=event_type)


async def sync_polar_webhook(
    session: AsyncSession,
    payload: dict[str, Any],
) -> WebhookSyncResult:
    event_type = _as_string(payload.get("type"))
    data = payload.get("data")
    if not event_type or not isinstance(data, dict):
        return WebhookSyncResult(action="ignored", event_type=event_type or "unknown")

    if event_type in {"customer.created", "customer.updated"}:
        return await _sync_customer_event(session, event_type, data)

    if event_type in {
        "subscription.created",
        "subscription.updated",
        "subscription.active",
        "subscription.canceled",
        "subscription.uncanceled",
        "subscription.revoked",
        "subscription.past_due",
    }:
        return await _sync_subscription_event(session, event_type, data)

    return WebhookSyncResult(action="ignored", event_type=event_type)

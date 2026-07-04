from __future__ import annotations

import asyncio
from typing import Any

import stripe
from fastapi import HTTPException, status

from app.auth.dependencies import CurrentUser
from app.billing.plans import BillingPlan
from app.billing.polar import absolute_app_url
from app.config import settings
from app.logging import get_logger

log = get_logger(__name__)


class StripeBillingError(RuntimeError):
    pass


def _session_url(session: Any) -> str:
    if isinstance(session, dict):
        url = session.get("url")
    else:
        url = getattr(session, "url", None)
    if not isinstance(url, str) or not url:
        raise StripeBillingError("Stripe session did not return a URL.")
    return url


def _require_stripe_secret() -> str:
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe billing is not configured.",
        )
    return settings.stripe_secret_key


async def create_checkout_session(
    *,
    plan: BillingPlan,
    user: CurrentUser,
) -> str:
    if settings.billing_provider != "stripe":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe billing is not enabled.",
        )
    if not plan.product_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe price is not configured for this plan.",
        )

    metadata = {
        "user_id": str(user.id),
        "plan_id": plan.id,
        "price_id": plan.product_id,
    }

    def create() -> Any:
        return stripe.checkout.Session.create(
            api_key=_require_stripe_secret(),
            mode="subscription",
            line_items=[{"price": plan.product_id, "quantity": 1}],
            customer_email=user.email,
            client_reference_id=str(user.id),
            success_url=absolute_app_url(settings.stripe_checkout_success_path),
            cancel_url=absolute_app_url(settings.stripe_portal_return_path),
            metadata=metadata,
            subscription_data={"metadata": metadata},
            allow_promotion_codes=True,
        )

    try:
        return _session_url(await asyncio.to_thread(create))
    except StripeBillingError:
        raise
    except Exception as exc:
        log.warning("stripe_checkout_failed", plan_id=plan.id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe checkout could not be created.",
        ) from exc


async def create_portal_session(*, stripe_customer_id: str) -> str:
    if settings.billing_provider != "stripe":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe billing is not enabled.",
        )

    def create() -> Any:
        return stripe.billing_portal.Session.create(
            api_key=_require_stripe_secret(),
            customer=stripe_customer_id,
            return_url=absolute_app_url(settings.stripe_portal_return_path),
        )

    try:
        return _session_url(await asyncio.to_thread(create))
    except StripeBillingError:
        raise
    except Exception as exc:
        log.warning("stripe_portal_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe customer portal could not be opened.",
        ) from exc


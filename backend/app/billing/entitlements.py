from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.billing.plans import get_plan_id_for_product
from app.config import settings
from app.database.billing import (
    get_active_polar_subscription_for_user,
    get_latest_polar_subscription_for_customer,
    get_polar_customer_by_user_id,
)
from app.database.stripe_billing import (
    get_active_stripe_subscription_for_user,
    get_latest_stripe_subscription_for_customer,
    get_stripe_customer_by_user_id,
)


@dataclass(frozen=True, slots=True)
class EntitlementState:
    plan_id: str
    subscription_status: str
    read_only: bool
    billing_provider: str
    billing_enabled: bool
    has_customer: bool
    polar_enabled: bool
    has_polar_customer: bool


def _internal_entitlement() -> EntitlementState:
    return EntitlementState(
        plan_id="internal",
        subscription_status="not_required",
        read_only=False,
        billing_provider="none",
        billing_enabled=False,
        has_customer=False,
        polar_enabled=False,
        has_polar_customer=False,
    )


async def get_entitlement_state(
    session: AsyncSession,
    user_id: UUID,
) -> EntitlementState:
    if settings.billing_provider == "none":
        return _internal_entitlement()

    if settings.billing_provider == "stripe":
        customer = await get_stripe_customer_by_user_id(session, user_id)
        if customer is None:
            return EntitlementState(
                plan_id="none",
                subscription_status="missing",
                read_only=True,
                billing_provider="stripe",
                billing_enabled=True,
                has_customer=False,
                polar_enabled=False,
                has_polar_customer=False,
            )

        active_subscription = await get_active_stripe_subscription_for_user(
            session,
            user_id,
        )
        latest_subscription = (
            active_subscription
            or await get_latest_stripe_subscription_for_customer(session, customer.id)
        )
        plan_id = get_plan_id_for_product(
            latest_subscription.price_id if latest_subscription else None
        )
        return EntitlementState(
            plan_id=plan_id or "unknown",
            subscription_status=latest_subscription.status if latest_subscription else "missing",
            read_only=active_subscription is None,
            billing_provider="stripe",
            billing_enabled=True,
            has_customer=True,
            polar_enabled=False,
            has_polar_customer=False,
        )

    if settings.billing_provider != "polar" and not settings.polar_enabled:
        return _internal_entitlement()

    customer = await get_polar_customer_by_user_id(session, user_id)
    if customer is None:
        return EntitlementState(
            plan_id="none",
            subscription_status="missing",
            read_only=True,
            billing_provider="polar",
            billing_enabled=True,
            has_customer=False,
            polar_enabled=True,
            has_polar_customer=False,
        )

    active_subscription = await get_active_polar_subscription_for_user(session, user_id)
    latest_subscription = active_subscription or await get_latest_polar_subscription_for_customer(
        session,
        customer.id,
    )
    plan_id = get_plan_id_for_product(latest_subscription.product_id if latest_subscription else None)

    return EntitlementState(
        plan_id=plan_id or "unknown",
        subscription_status=latest_subscription.status if latest_subscription else "missing",
        read_only=active_subscription is None,
        billing_provider="polar",
        billing_enabled=True,
        has_customer=True,
        polar_enabled=True,
        has_polar_customer=True,
    )


async def require_active_entitlement(
    session: AsyncSession,
    user: CurrentUser,
) -> None:
    entitlement = await get_entitlement_state(session, user.id)
    if entitlement.read_only:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="An active SiteWise subscription is required for this action.",
        )

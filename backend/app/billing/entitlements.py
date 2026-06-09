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


@dataclass(frozen=True, slots=True)
class EntitlementState:
    plan_id: str
    subscription_status: str
    read_only: bool
    polar_enabled: bool
    has_polar_customer: bool


async def get_entitlement_state(
    session: AsyncSession,
    user_id: UUID,
) -> EntitlementState:
    if not settings.polar_enabled:
        return EntitlementState(
            plan_id="internal",
            subscription_status="not_required",
            read_only=False,
            polar_enabled=False,
            has_polar_customer=False,
        )

    customer = await get_polar_customer_by_user_id(session, user_id)
    if customer is None:
        return EntitlementState(
            plan_id="none",
            subscription_status="missing",
            read_only=True,
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
